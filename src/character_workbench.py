"""角色动作工作台：聚合现有产物，生成可搬运的本地检查项目，不调用生成 API。"""
from __future__ import annotations

import argparse
import base64
import hashlib
import json
import shutil
import struct
import tempfile
from pathlib import Path

from PIL import Image

from asset_bundle import identifier, integer, number, read_json, within, write_json
from validate_clips import check_clip, check_skeleton

ROOT = Path(__file__).resolve().parents[1]


def vector(value, label, positive=False):
    if not isinstance(value, list) or len(value) != 3:
        raise ValueError(f"{label} 必须是三元组")
    for v in value:
        number(v, label, 0.000001 if positive else -100000, 100000)


def provenance(path: Path) -> dict:
    return {"path": str(path), "sha256": hashlib.sha256(path.read_bytes()).hexdigest()}


def encode_image(path: Path) -> str:
    return "data:image/png;base64," + base64.b64encode(path.read_bytes()).decode("ascii")


def load_pivot(spec: dict, base: Path) -> tuple[dict, list[dict]]:
    library = (base / spec["library"]).resolve()
    name = identifier(spec["skeleton"])
    source = within(library, f"skeletons/{name}.json")
    skeleton = read_json(source)
    if skeleton.get("id") != name:
        raise ValueError("骨架 id 与配置不符")
    problems = check_skeleton(skeleton)
    if problems:
        raise ValueError("; ".join(problems))
    if skeleton.get("axes", {}).get("up") != "Z":
        raise ValueError("部件动作库目前只支持 Z 向上；不可默默旋转未知坐标系")
    for part in skeleton["parts"]:
        identifier(part["id"])
        vector(part["joint"], "joint")
        shape = part.get("shape")
        if shape:
            if shape.get("type") != "box" or shape.get("material") not in skeleton["materials"]:
                raise ValueError("目前仅支持有合法材质的 box 部件")
            vector(shape["size"], "size", positive=True)
            vector(shape["offset"], "offset")
    for color in skeleton["materials"].values():
        if len(color) != 4:
            raise ValueError("材质需要 RGBA")
        for v in color:
            number(v, "color", 0, 1)
    fps = number(spec.get("fps", 24), "fps", 1, 240)
    clips, sources = [], [provenance(source)]
    for clip_path in sorted(within(library, f"clips/{name}").glob("*.json")):
        clip = read_json(clip_path)
        identifier(clip["id"])
        if clip.get("skeleton") != name or type(clip.get("loop")) is not bool:
            raise ValueError("动作的骨架/loop 不符")
        problems = check_clip(clip, {p["id"] for p in skeleton["parts"]})
        if problems:
            raise ValueError("; ".join(problems))
        for tracks in clip["tracks"].values():
            for channel, keys in tracks.items():
                for frame, value in keys:
                    number(frame, "keyframe", 1, clip["end"])
                    vector(value, channel, positive=channel == "scale")
        clip.update({"fps": fps, "duration": (clip["end"] - 1) / fps})
        clips.append(clip)
        sources.append(provenance(clip_path))
    if not clips or len({c["id"] for c in clips}) != len(clips):
        raise ValueError("动作为空或 id 重复")
    return {"kind": "pivot", "skeleton": skeleton, "clips": clips}, sources


def load_sprite(spec: dict, base: Path) -> tuple[dict, list[dict]]:
    source = (base / spec["manifest"]).resolve()
    manifest = read_json(source)
    if manifest.get("kind") != "motion":
        raise ValueError("二维输入需要 asset_bundle 的 motion manifest")
    atlas = within(source.parent, manifest["atlas"])
    with Image.open(atlas) as im:
        width, height = im.size
        if im.format != "PNG":
            raise ValueError("图集需要 PNG")
    clips = []
    cell = None
    for state in manifest["states"]:
        identifier(state["name"])
        if type(state.get("loop")) is not bool or not state.get("frames"):
            raise ValueError("二维动作需要 loop 和帧")
        for frame in state["frames"]:
            for key in ("x", "y"):
                integer(frame[key], key, 16384, minimum=0)
            for key in ("w", "h", "durationMs"):
                integer(frame[key], key, 60000)
            if frame["x"] + frame["w"] > width or frame["y"] + frame["h"] > height:
                raise ValueError("帧矩形越出图集")
            size = (frame["w"], frame["h"])
            if cell is not None and size != cell:
                raise ValueError("工作台要求跨动作统一画布，不能掩盖尺寸漂移")
            cell = size
        clips.append({"id": state["name"], "loop": state["loop"], "frames": state["frames"],
                      "duration": sum(f["durationMs"] for f in state["frames"]) / 1000})
    if not clips or len({c["id"] for c in clips}) != len(clips):
        raise ValueError("动作为空或 id 重复")
    anchor = manifest.get("anchor", [0.5, 1])
    if not isinstance(anchor, list) or len(anchor) != 2:
        raise ValueError("anchor 需要两个分量")
    for v in anchor:
        number(v, "anchor", 0, 1)
    return {"kind": "sprite", "clips": clips, "atlasData": encode_image(atlas),
            "anchor": anchor, "sourceRelease": manifest.get("release", {})}, [provenance(source), provenance(atlas)]


def load_glb(spec: dict, base: Path) -> tuple[dict, list[dict]]:
    path = (base / spec["model"]).resolve()
    raw = path.read_bytes()
    if len(raw) < 20 or len(raw) > 64 * 1024 * 1024:
        raise ValueError("GLB 大小需要 20 字节..64MiB")
    magic, version, length = struct.unpack_from("<III", raw)
    chunk_length, chunk_type = struct.unpack_from("<II", raw, 12)
    if magic != 0x46546C67 or version != 2 or length != len(raw) or chunk_type != 0x4E4F534A or 20 + chunk_length > len(raw):
        raise ValueError("无效 GLB 2.0")
    model = json.loads(raw[20:20 + chunk_length])
    # 本地项目不允许模型暗中拉取网络纹理/缓冲；外部依赖先在 Blender 导出为单文件 GLB。
    if any("uri" in item for group in ("buffers", "images") for item in model.get(group, [])):
        raise ValueError("需要自包含 GLB，不能引用外部 URI")
    unsupported = set(model.get("extensionsRequired", [])) - {"KHR_materials_unlit", "KHR_texture_transform", "KHR_materials_clearcoat", "KHR_materials_ior", "KHR_materials_transmission", "KHR_materials_specular", "KHR_materials_sheen", "KHR_materials_volume", "KHR_materials_emissive_strength", "KHR_mesh_quantization"}
    if unsupported:
        raise ValueError(f"请导出未压缩 GLB，不支持扩展: {sorted(unsupported)}")
    animations = model.get("animations", [])
    names = [a.get("name") or f"animation_{i}" for i, a in enumerate(animations)]
    if len(set(names)) != len(names):
        raise ValueError("GLB 动作名称重复，请在 Blender 中重命名")
    loops = spec.get("loops", {})
    if any(type(v) is not bool for v in loops.values()) or set(loops) - set(names):
        raise ValueError("loops 必须对应 GLB 动作名并使用布尔值")
    return {"kind": "glb", "modelData": "data:model/gltf-binary;base64," + base64.b64encode(raw).decode("ascii"),
            "clips": [{"id": n, "loop": loops.get(n, False)} for n in names],
            "unclassifiedLoops": [n for n in names if n not in loops]}, [provenance(path)]


def build(profile_path: Path, out: Path, three_dir: Path | None = None) -> Path:
    profile_path, out = profile_path.resolve(), out.resolve()
    profile = read_json(profile_path)
    if profile.get("version") != 1 or not profile.get("characters"):
        raise ValueError("工作台配置需要 version:1 与非空 characters")
    if out.exists():
        raise ValueError("输出已存在，请使用新批次目录")
    three_dir = (three_dir or ROOT / "workbench/node_modules/three").resolve()
    if not (three_dir / "build/three.module.js").is_file():
        raise ValueError("先执行 npm ci --prefix workbench 安装锁定的 three.js")
    if read_json(three_dir / "package.json")["version"] != "0.184.0":
        raise ValueError("工作台要求锁定 three.js 0.184.0")
    characters, reports, sources, jobs = [], [], [provenance(profile_path)], []
    for spec in profile["characters"]:
        cid = identifier(spec["id"])
        loaders = {"pivot": load_pivot, "sprite": load_sprite, "glb": load_glb}
        if spec.get("kind") not in loaders:
            raise ValueError("kind 支持 pivot / sprite / glb")
        character, records = loaders[spec["kind"]](spec, profile_path.parent)
        sources.extend(records)
        direction = identifier(spec.get("direction", "side"))
        required = spec.get("requiredActions", [c["id"] for c in character["clips"]])
        for action in required:
            if character["kind"] == "glb":
                if not isinstance(action, str) or not 1 <= len(action) <= 128:
                    raise ValueError("GLB 动作名称需要 1..128 字符")
            else:
                identifier(action)
        directions = spec.get("requiredDirections", [direction])
        for d in directions:
            identifier(d)
        missing = [a for a in required if a not in {c["id"] for c in character["clips"]}]
        warnings = ["仍需人工确认步态、脚底和动作语义；自动检测通过不等于正式美术验收"]
        review_notes = spec.get("reviewNotes", [])
        if not isinstance(review_notes, list) or any(not isinstance(note, str) or not note.strip() for note in review_notes):
            raise ValueError("reviewNotes 必须是非空文字组成的数组")
        # 保留上游人工否决理由，避免结构校验通过后，预览把失败候选呈现为已验收素材。
        warnings.extend(review_notes)
        if character["kind"] == "sprite":
            warnings.append("二维预览保留原帧，不用淡入制造双影；此页不执行游戏命中/取消窗口")
        preview_motion = spec.get("previewMotion", {})
        if not isinstance(preview_motion, dict):
            raise ValueError("previewMotion 必须是动作名到曲线配置的对象")
        for action, curve in preview_motion.items():
            target = next((c for c in character["clips"] if c["id"] == action), None)
            if character["kind"] != "sprite" or target is None or target["loop"] or not isinstance(curve, dict) or curve.get("kind") != "jump-arc":
                raise ValueError("预览轨迹仅支持已有的二维单次动作 jump-arc")
            height = number(curve["heightPixels"], "heightPixels", 0, target["frames"][0]["h"] / 2)
            start = number(curve["startMs"], "startMs", 0, target["duration"]*1000)
            end = number(curve["endMs"], "endMs", 0, target["duration"]*1000)
            if end <= start:
                raise ValueError("预览轨迹 endMs 必须晚于 startMs")
            # 姿态原画和物理根位移分开；此曲线仅用于验收页，不写回正式动作包。
            target["previewMotion"] = {"kind": "jump-arc", "heightPixels": height, "startMs": start, "endMs": end}
            warnings.append(f"{action} 整体位移使用预览曲线；游戏需自行匹配物理轨迹，不叠加两套高度")
        if character["kind"] == "pivot":
            warnings.append("盒子部件为动作验证模型，不是蒙皮角色；浏览器插值不等同于 Blender 曲线")
        if character.get("unclassifiedLoops"):
            warnings.append("GLB 未声明 loop 的动作按单次播放: " + ", ".join(character["unclassifiedLoops"]))
        aliases = spec.get("sourceAliases", {})
        if aliases:
            warnings.append("消费游戏存在借用姿态: " + json.dumps(aliases, ensure_ascii=False))
        identity = spec.get("identity", "保持同一角色的比例、服饰、武器、配色和光照")
        character.update({"id": cid, "title": spec.get("title", cid), "direction": direction,
                          "defaultAction": spec.get("defaultAction", character["clips"][0]["id"] if character["clips"] else None)})
        if character["defaultAction"] not in {c["id"] for c in character["clips"]} and character["clips"]:
            raise ValueError("defaultAction 不存在")
        reports.append({"id": cid, "actions": len(character["clips"]), "missingActions": missing,
                        "missingDirections": [d for d in directions if d != direction], "warnings": warnings,
                        "status": "needs-assets" if missing or any(d != direction for d in directions) else "needs-manual-review"})
        # 提示词只是待办，不执行上游任务；攻击和步态的时间语义分别约束，不能都要求循环。
        for d in directions:
            for a in required:
                if d == direction and a not in missing:
                    continue
                loop = a in ("idle", "move", "walk", "run")
                jobs.append({"character": cid, "action": a, "direction": d, "status": "not-executed",
                             "provider": "choose-sprite-gen-or-scenario", "reference": spec.get("reference"),
                             "prompt": f"{identity}。固定 {d} 朝向和镜头，完整身体，共用画布与脚底基准。动作 {a}。" +
                             ("原地完成完整左右交替周期，检查末帧到首帧的速度和姿态。" if loop else "准备→发力→随挥/回弹→收招回到准备，不把单次动作重复拼成循环。")})
        characters.append(character)
    if len({c["id"] for c in characters}) != len(characters):
        raise ValueError("角色 id 重复")
    preferred = profile.get("defaultCharacter")
    if preferred is not None and preferred not in {c["id"] for c in characters}:
        raise ValueError("defaultCharacter 不存在")
    report = {"version": 1, "status": "draft", "characters": reports,
              "runtimeEvidence": None, "generationExecuted": False}
    out.parent.mkdir(parents=True, exist_ok=True)
    # 先完成全部校验，再原子发布；失败不留下半成品，也不覆盖已有资产批次。
    with tempfile.TemporaryDirectory(prefix=".workbench-", dir=out.parent) as temporary:
        stage = Path(temporary) / "project"
        stage.mkdir()
        write_json(stage / "manifest.json", {"version": 1, "title": profile.get("title", "角色动作工作台"),
                                             "defaultCharacter": preferred,
                                             "characters": characters})
        write_json(stage / "report.json", report)
        write_json(stage / "provenance.json", {"sources": sources, "renderer": "three.js 0.184.0"})
        write_json(stage / "generation-plan.json", {"jobs": jobs, "executed": False})
        for filename in ("index.html", "main.mjs", "motion.mjs"):
            shutil.copy2(ROOT / "examples" / "export-workbench" / filename, stage / filename)
        # 同一端口切换资产批次时，浏览器可能复用旧模块；内容寻址让页面、逻辑和数据保持同版。
        names = {}
        for filename in ("motion.mjs", "manifest.json", "report.json"):
            content = (stage / filename).read_bytes()
            original = Path(filename)
            names[filename] = f"{original.stem}-{hashlib.sha256(content).hexdigest()[:16]}{original.suffix}"
            (stage / names[filename]).write_bytes(content)
        main = (stage / "main.mjs").read_text(encoding="utf-8")
        for original, hashed in names.items():
            main = main.replace(original, hashed)
        main_name = f"main-{hashlib.sha256(main.encode()).hexdigest()[:16]}.mjs"
        (stage / main_name).write_text(main, encoding="utf-8")
        index = (stage / "index.html").read_text(encoding="utf-8")
        (stage / "index.html").write_text(index.replace("./main.mjs", "./" + main_name), encoding="utf-8")
        vendor = stage / "vendor"
        # 只携带本页实际依赖，避免把全部渲染器与示例的数十 MiB 带进每个资产批次。
        for relative in ("build/three.module.js", "build/three.core.js", "examples/jsm/controls/OrbitControls.js",
                         "examples/jsm/loaders/GLTFLoader.js", "examples/jsm/utils/BufferGeometryUtils.js",
                         "examples/jsm/utils/SkeletonUtils.js"):
            target = vendor / relative.replace("examples/jsm/", "addons/")
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(three_dir / relative, target)
        shutil.copy2(three_dir / "LICENSE", vendor / "LICENSE")
        (stage / "START.txt").write_text("python3 -m http.server 8770 --bind 127.0.0.1 --directory .\n打开 http://127.0.0.1:8770/\n本地资源，不上传文件。需要 HTTP 加载 ES module，不能 file:// 双击。\n", encoding="utf-8")
        stage.rename(out)
    return out


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--profile", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    try:
        print(build(args.profile, args.out))
    except (ValueError, KeyError, TypeError, OSError) as error:
        parser.exit(2, f"工作台构建失败: {error}\n")


if __name__ == "__main__":
    main()
