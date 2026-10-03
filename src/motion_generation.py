"""GPT 逐帧生图任务：准备素材/提示词、记录真实生成尝试、审查、导出草稿动作包。"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
import os
import shutil
import tempfile
from pathlib import Path

from PIL import Image, ImageDraw

from asset_bundle import build, identifier, integer, number, read_json, within, write_json


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def atomic_json(path, value):
    # 先落盘再替换任务索引；被中断的生成不能把可恢复任务写成半截 JSON。
    temporary = path.with_suffix(".json.tmp")
    write_json(temporary, value)
    os.replace(temporary, path)


def default_walk():
    near = [(60, 478), (30, 480), (0, 480), (-35, 478), (-60, 478), (-42, 454), (28, 438), (38, 458)]
    names = ["near-contact", "near-down", "far-passing", "far-swing", "far-contact", "far-down", "near-passing", "near-swing"]
    frames = []
    for i in range(8):
        n, f = near[i], near[(i + 4) % 8]
        diagram = {"near": n, "far": f, "bob": [0, 4, 0, -4][i % 4]}
        # 经过帧明确支撑腿与前摆膝；两脚同 x 的模糊草图容易被生图解释成后踢。
        if i in (2, 6):
            diagram.update(nearKnee=(256, 400) if i == 2 else (300, 370),
                           farKnee=(300, 370) if i == 2 else (256, 400))
        frames.append({"durationMs": 100, "pose": f"{names[i]}. Near foreground ankle x={256+n[0]}, y={n[1]}; far background ankle x={256+f[0]}, y={f[1]}. Opposite arm swing. This is anatomical limb identity, not silhouette-only matching." + (" Lifted knee passes FORWARD/right of planted leg, never a backward heel kick." if i in (2, 6) else ""),
                       "diagram": diagram})
    return {"version": 1, "title": "GPT 逐帧步行任务", "direction": "right-facing side view", "canvas": [512, 512],
            "cell": [256, 256], "anchor": [.5, 485/512], "actions": [{"name": "move", "loop": True, "frames": frames}]}


def draw_guide(spec, path):
    image = Image.new("RGB", (512, 512), "white")
    draw = ImageDraw.Draw(image)
    bob = spec["bob"]
    hip = (256, 320 + bob)
    shoulder = (256, 218 + bob)
    # 参考图只画姿态：远腿用虚线、近腿用实线，避免控制颜色混入最终皮肤。
    for side, color in (("far", "#969696"), ("near", "#333333")):
        x, y = spec[side]
        ankle = (256 + x, y)
        dx, dy = ankle[0] - hip[0], ankle[1] - hip[1]
        distance = math.hypot(dx, dy)
        bend = math.sqrt(86 ** 2 - distance ** 2 / 4)
        knee = ((hip[0] + ankle[0]) / 2 + dy / distance * bend,
                (hip[1] + ankle[1]) / 2 - dx / distance * bend)
        knee = spec.get(side + "Knee", knee)
        points = [hip, knee, ankle]
        for a, b in zip(points, points[1:]):
            if side == "near":
                draw.line([a, b], fill=color, width=12)
            else:
                for k in range(0, 16, 2):
                    draw.line([(a[0] + (b[0]-a[0])*k/16, a[1] + (b[1]-a[1])*k/16),
                               (a[0] + (b[0]-a[0])*(k+1)/16, a[1] + (b[1]-a[1])*(k+1)/16)], fill=color, width=10)
        draw.line([ankle, (ankle[0]+26, ankle[1]+5)], fill=color, width=12)
        swing = -x * .7
        draw.line([shoulder, (256+swing*.6, 265+bob), (256+swing, 306+bob)], fill=color, width=9)
    draw.rounded_rectangle((233, 195+bob, 279, 330+bob), radius=15, fill="#cccccc")
    draw.ellipse((193, 38+bob, 319, 172+bob), fill="#dddddd", outline="#777777", width=2)
    draw.polygon([(316, 98+bob), (330, 110+bob), (317, 118+bob)], fill="#777777")
    image.save(path)


def prepare(reference: Path, identity: str, out: Path, spec_path: Path | None = None):
    if out.exists():
        raise ValueError("任务目录已存在；使用原任务继续导入，或换新目录")
    if not identity.strip():
        raise ValueError("需要明确的角色身份、服饰与画风描述")
    spec = read_json(spec_path) if spec_path else default_walk()
    if spec.get("version") != 1 or not spec.get("actions"):
        raise ValueError("动作规格需要 version:1 和非空 actions")
    for key in ("canvas", "cell"):
        if not isinstance(spec.get(key), list) or len(spec[key]) != 2:
            raise ValueError(key + " 需要 [宽,高]")
        for n in spec[key]:
            integer(n, key, 4096)
    if not isinstance(spec.get("direction"), str) or not spec["direction"].strip():
        raise ValueError("需要明确相机朝向 direction")
    anchor = spec.get("anchor", [.5, 1])
    if not isinstance(anchor, list) or len(anchor) != 2:
        raise ValueError("anchor 需要 [x,y]")
    for value in anchor:
        number(value, "anchor", 0, 1)
    with Image.open(reference) as im:
        if getattr(im, "n_frames", 1) != 1:
            raise ValueError("身份参考必须是静态图片")
        im.verify()
    out.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix=".generation-", dir=out.parent) as temp:
        root = Path(temp)
        shutil.copy2(reference, root / ("reference" + reference.suffix.lower()))
        reference_record = {"path": "reference" + reference.suffix.lower(), "sha256": digest(reference)}
        job = {"version": 1, "provider": "codex-builtin-imagegen", "title": spec.get("title", "逐帧动作"),
               "identity": identity, "direction": spec["direction"], "canvas": spec["canvas"], "cell": spec["cell"],
               "reference": reference_record, "anchor": anchor, "actions": [], "frames": {}}
        for action in spec["actions"]:
            name = identifier(action["name"])
            if name in [a["name"] for a in job["actions"]] or type(action.get("loop")) is not bool or not action.get("frames"):
                raise ValueError("动作名必须唯一，loop 必须显式布尔值，frames 不得为空")
            ids = []
            for i, frame in enumerate(action["frames"]):
                fid = f"{name}-{i:03d}"
                integer(frame["durationMs"], "durationMs", 60000)
                if not isinstance(frame.get("pose"), str) or not frame["pose"].strip():
                    raise ValueError("每帧需要 pose 描述")
                guide = None
                if "guide" in frame:
                    if spec_path is None:
                        raise ValueError("自定义 guide 需要规格文件")
                    source = within(spec_path.parent, frame["guide"])
                    with Image.open(source) as im:
                        if list(im.size) != spec["canvas"]:
                            raise ValueError("姿态草图尺寸必须与任务 canvas 一致")
                        im.verify()
                    guide = fid + "-guide.png"
                    with Image.open(source) as im:
                        im.convert("RGB").save(root / guide)
                elif "diagram" in frame:
                    if spec["canvas"] != [512, 512]:
                        raise ValueError("默认步态草图使用 512 方形画布；其他尺寸请提供 guide")
                    guide = fid + "-guide.png"
                    draw_guide(frame["diagram"], root / guide)
                prompt = ("Use case: sketch-to-render. Generate ONE complete character animation frame, never a grid. "
                    + ("Image 1 is the PRIMARY pose/composition guide: solid dark limbs are NEAR, dotted pale limbs FAR. Image 2 is ONLY character design. Replace the mannequin with finished character art at the SAME coordinates. " if guide else "Image 1 is the character design reference. ")
                    + f"Character identity: {identity}. Facing/camera: {spec['direction']}. Pose: {frame['pose']} "
                    + f"Output full {spec['canvas'][0]}x{spec['canvas'][1]} canvas. Keep scale, head proportions, pelvis position and ground line fixed across frames. "
                    + "Draw connected anatomical contours and natural clothing, no cutout hinge seams. Preserve face/hair/outfit/boot details exactly. "
                    + "Use natural skin colors; guide line colors are not costume colors. No pose labels, numbers, skeleton, guide marks, ground, shadow or glow. "
                    + "Everything outside the character must be truly transparent. Keep the camera fixed. "
                    + ("This is a walk in place, not a camera turn, hop or run." if name == "move" else f"Perform only the requested {name} pose."))
                (root / (fid + "-prompt.txt")).write_text(prompt + "\n")
                job["frames"][fid] = {"pose": frame["pose"], "durationMs": frame["durationMs"], "guide": guide,
                    "guideSha256": digest(root / guide) if guide else None, "prompt": fid + "-prompt.txt",
                    "promptSha256": digest(root / (fid + "-prompt.txt")), "attempts": [], "selected": None}
                ids.append(fid)
            job["actions"].append({"name": name, "loop": action["loop"], "frames": ids})
        write_json(root / "job.json", job)
        root.rename(out)
    return out / "job.json"


def load_job(path):
    job = read_json(path)
    if job.get("version") != 1:
        raise ValueError("不支持的任务版本")
    for fid in job["frames"]:
        identifier(fid)
    # 参考、姿态和提示词改变后必须新建任务，不能拿旧的审查结论认可新的输入。
    for record in [job["reference"]] + [
        {"path": f[key], "sha256": f[key + "Sha256"]} for f in job["frames"].values()
        for key in ("guide", "prompt") if f[key]]:
        if digest(within(path.parent, record["path"])) != record["sha256"]:
            raise ValueError("任务输入已改变，需重建任务: " + record["path"])
    return job


def ingest(path, fid, image_path, offset=(0, 0), prompt_path=None, reference_paths=None, candidate_only=False):
    job = load_job(path)
    frame = job["frames"][fid]
    sha = digest(image_path)
    prompt_path = prompt_path or within(path.parent, frame["prompt"])
    prompt_sha = digest(prompt_path)
    if reference_paths is None:
        reference_paths = ([within(path.parent, frame["guide"])] if frame["guide"] else []) + [within(path.parent, job["reference"]["path"])]
    reference_hashes = [digest(p) for p in reference_paths]
    with Image.open(image_path) as im:
        if getattr(im, "n_frames", 1) != 1 or "A" not in im.getbands():
            raise ValueError("生成输出必须是单张透明 RGBA 图片")
        image = im.convert("RGBA")
    if image.getchannel("A").getbbox() is None or image.getchannel("A").getextrema()[0] != 0:
        raise ValueError("生成图片全透明或没有透明背景")
    canvas = job["canvas"]
    if abs(image.width / image.height - canvas[0] / canvas[1]) > .001:
        raise ValueError("生图画布比例不匹配；不得默默裁切角色")
    if len(offset) != 2 or any(type(n) is not int or abs(n) > min(canvas) // 4 for n in offset):
        raise ValueError("平移 offset 需要两个有限范围整数")
    resized = image.resize(canvas, Image.Resampling.LANCZOS)
    bounds = resized.getchannel("A").getbbox()
    if bounds is None or bounds[0]+offset[0] < 0 or bounds[1]+offset[1] < 0 or bounds[2]+offset[0] > canvas[0] or bounds[3]+offset[1] > canvas[1]:
        raise ValueError("平移会裁掉角色，需先修正源画布")
    # 同一结果重复登记是幂等的；修正图是新尝试，必须重新检查，不继承旧 verdict。
    for index, existing in enumerate(frame["attempts"]):
        if (existing["sha256"] == sha and existing["offset"] == list(offset)
                and existing.get("promptSha256") == prompt_sha
                and [r["sha256"] for r in existing.get("referenceInputs", [])] == reference_hashes):
            if not candidate_only and frame["selected"] != index:
                frame["selected"] = index
                job.pop("cycleReviews", None)
                atomic_json(path, job)
            return existing
    ordinal = len(frame["attempts"]) + 1
    folder = path.parent / fid / f"attempt-{ordinal:03d}"
    # 中断可能留下尚未写入索引的目录；保留证据并跳过它，使原任务仍可继续。
    while folder.exists():
        ordinal += 1
        folder = path.parent / fid / f"attempt-{ordinal:03d}"
    folder.mkdir(parents=True, exist_ok=False)
    source_name = "source" + image_path.suffix.lower()
    shutil.copy2(image_path, folder / source_name)
    shutil.copy2(prompt_path, folder / "actual-prompt.txt")
    refs = []
    for index, ref_path in enumerate(reference_paths):
        destination = folder / (f"reference-{index+1:02d}" + ref_path.suffix.lower())
        shutil.copy2(ref_path, destination)
        refs.append({"path": destination.relative_to(path.parent).as_posix(), "sha256": digest(destination)})
    normalized = Image.new("RGBA", canvas)
    normalized.paste(resized, tuple(offset))
    normalized.save(folder / "frame.png")
    record = {"sha256": sha, "original": (folder / source_name).relative_to(path.parent).as_posix(),
              "frame": (folder / "frame.png").relative_to(path.parent).as_posix(), "frameSha256": digest(folder / "frame.png"),
              "actualPrompt": (folder / "actual-prompt.txt").relative_to(path.parent).as_posix(), "promptSha256": prompt_sha,
              "referenceInputs": refs,
              "offset": list(offset), "sourceSize": list(image.size), "review": None}
    frame["attempts"].append(record)
    if not candidate_only:
        frame["selected"] = len(frame["attempts"]) - 1
        job.pop("cycleReviews", None)
    atomic_json(path, job)
    return record


def select_attempt(path, fid, index):
    job = load_job(path)
    frame = job["frames"][fid]
    if type(index) is not int or not 0 <= index < len(frame["attempts"]):
        raise ValueError("attempt-index 为实际登记列表中的零起始索引")
    attempt = frame["attempts"][index]
    if digest(within(path.parent, attempt["frame"])) != attempt["frameSha256"]:
        raise ValueError("候选帧已改变，需重新登记")
    # 失败编辑可只存候选，显式选版本再改预览；回退版本也必须重新检查完整循环。
    if frame["selected"] != index:
        frame["selected"] = index
        job.pop("cycleReviews", None)
        atomic_json(path, job)
    return attempt


def review(path, fid, verdict, reason, reviewer, attempt_index=None):
    job = load_job(path)
    frame = job["frames"][fid]
    index = frame["selected"] if attempt_index is None else attempt_index
    if index is None:
        raise ValueError("尚无实际生成帧，不能审查计划")
    if type(index) is not int or not 0 <= index < len(frame["attempts"]):
        raise ValueError("审查 attempt-index 越界")
    if verdict not in ("accept", "reject") or reviewer not in ("agent", "user") or not reason.strip():
        raise ValueError("审查必须注明 verdict、reviewer 与实际原因")
    selected = frame["attempts"][index]
    if digest(within(path.parent, selected["frame"])) != selected["frameSha256"]:
        raise ValueError("帧已改变，必须重新登记")
    selected["review"] = {"verdict": verdict, "reason": reason, "reviewer": reviewer}
    if index == frame["selected"]:
        job.pop("cycleReviews", None)
    atomic_json(path, job)


def cycle_signature(job, action, path):
    records = []
    for fid in action["frames"]:
        frame = job["frames"][fid]
        if frame["selected"] is None:
            raise ValueError("循环缺实际帧: " + fid)
        attempt = frame["attempts"][frame["selected"]]
        if digest(within(path.parent, attempt["frame"])) != attempt["frameSha256"]:
            raise ValueError("循环帧已改变: " + fid)
        records.append({"id": fid, "durationMs": frame["durationMs"], "attempt": attempt})
    payload = {"frames": records, "action": action, "canvas": job["canvas"], "anchor": job.get("anchor", [.5, 1])}
    return hashlib.sha256(json.dumps(payload, sort_keys=True).encode()).hexdigest()


def review_cycle(path, name, verdict, reason, reviewer):
    job = load_job(path)
    action = next((a for a in job["actions"] if a["name"] == name), None)
    if action is None or verdict not in ("accept", "reject") or reviewer not in ("agent", "user") or not reason.strip():
        raise ValueError("完整动作审查需要有效 action/verdict/reviewer 和实际原因")
    signature = cycle_signature(job, action, path)
    if verdict == "accept" and any(job["frames"][fid]["attempts"][job["frames"][fid]["selected"]]["review"] is None or
            job["frames"][fid]["attempts"][job["frames"][fid]["selected"]]["review"]["verdict"] != "accept" for fid in action["frames"]):
        raise ValueError("接受完整动作前需逐帧审查通过")
    # 审查绑定真实帧、逐帧时长、loop 和锚点；更换原画不能继承旧循环结论。
    job.setdefault("cycleReviews", {})[name] = {"signature": signature, "verdict": verdict, "reviewer": reviewer, "reason": reason}
    atomic_json(path, job)


def inspect_job(path, out):
    job = load_job(path)
    rows = list(job["frames"].items())
    contact = Image.new("RGB", (660, len(rows) * 240), "#253344")
    draw = ImageDraw.Draw(contact)
    for row, (fid, frame) in enumerate(rows):
        y = row * 240
        draw.text((8, y + 6), fid + " / guide", fill="white")
        if frame["guide"]:
            with Image.open(within(path.parent, frame["guide"])) as guide:
                guide.thumbnail((210, 210))
                contact.paste(guide, (8, y + 25))
        draw.text((230, y + 6), "actual selected frame", fill="white")
        verdict = "NOT GENERATED"
        if frame["selected"] is not None:
            attempt = frame["attempts"][frame["selected"]]
            actual = within(path.parent, attempt["frame"])
            if digest(actual) != attempt["frameSha256"]:
                raise ValueError("帧已改变: " + fid)
            with Image.open(actual) as im:
                im.thumbnail((210, 210))
                contact.paste(im, (230, y + 25), im)
            verdict = "UNREVIEWED" if attempt["review"] is None else attempt["review"]["reviewer"] + ": " + attempt["review"]["verdict"]
        draw.text((455, y + 25), verdict, fill="white")
        draw.text((455, y + 45), f"{frame['durationMs']}ms", fill="white")
    if out.exists():
        raise ValueError("检查图已存在，使用新文件名")
    out.parent.mkdir(parents=True, exist_ok=True)
    contact.save(out)
    return out


def pack(path, out):
    job = load_job(path)
    selected = {}
    for fid, frame in job["frames"].items():
        if frame["selected"] is None:
            raise ValueError("缺生成帧: " + fid)
        attempt = frame["attempts"][frame["selected"]]
        image_path = within(path.parent, attempt["frame"])
        if digest(image_path) != attempt["frameSha256"] or digest(within(path.parent, attempt["original"])) != attempt["sha256"]:
            raise ValueError("帧已改变，不能导出陈旧审查: " + fid)
        if digest(within(path.parent, attempt["actualPrompt"])) != attempt["promptSha256"]:
            raise ValueError("实际调用提示词已改变: " + fid)
        for ref in attempt["referenceInputs"]:
            if digest(within(path.parent, ref["path"])) != ref["sha256"]:
                raise ValueError("实际调用参考已改变: " + fid)
        selected[fid] = (image_path, attempt)
    if out.exists():
        raise ValueError("输出已存在，请使用新批次")
    if len(selected) * job["canvas"][0] > 16384:
        raise ValueError("源图集超过 16384 像素，请按动作拆分生成任务")
    out.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix=".generation-pack-", dir=out.parent) as temp:
        root = Path(temp)
        provenance = root / "generation-sources"
        provenance.mkdir()
        shutil.copy2(within(path.parent, job["reference"]["path"]), provenance / Path(job["reference"]["path"]).name)
        write_json(provenance / "spec.json", {k: job[k] for k in ("title", "identity", "direction", "canvas", "cell", "actions")})
        if (path.parent / "registration.json").exists():
            shutil.copy2(within(path.parent, "registration.json"), provenance / "registration.json")
        atlas = Image.new("RGBA", (len(selected) * job["canvas"][0], job["canvas"][1]))
        descriptor = {"frames": [], "meta": {"image": "source.png", "frameTags": []}}
        audits = []
        i = 0
        for action in job["actions"]:
            start = i
            for fid in action["frames"]:
                image_path, attempt = selected[fid]
                sources = provenance / fid
                sources.mkdir()
                files = {}
                for key in ("original", "frame", "actualPrompt"):
                    input_path = within(path.parent, attempt[key])
                    destination = sources / input_path.name
                    shutil.copy2(input_path, destination)
                    files[key] = destination.relative_to(root).as_posix()
                references = []
                for ref in attempt["referenceInputs"]:
                    destination = sources / Path(ref["path"]).name
                    shutil.copy2(within(path.parent, ref["path"]), destination)
                    references.append({"path": destination.relative_to(root).as_posix(), "sha256": ref["sha256"]})
                with Image.open(image_path) as im:
                    atlas.paste(im, (i * job["canvas"][0], 0))
                descriptor["frames"].append({"frame": {"x": i*job["canvas"][0], "y": 0, "w": job["canvas"][0], "h": job["canvas"][1]},
                                             "duration": job["frames"][fid]["durationMs"], "trimmed": False, "rotated": False})
                audits.append({"id": fid, "sha256": attempt["sha256"], "normalizedSha256": attempt["frameSha256"],
                               "promptSha256": attempt["promptSha256"], "referenceInputs": references, "sourceFiles": files,
                               "offset": attempt["offset"], "review": attempt["review"]})
                i += 1
            descriptor["meta"]["frameTags"].append({"name": action["name"], "from": start, "to": i-1, "direction": "forward"})
        atlas.save(root / "source.png")
        write_json(root / "source.json", descriptor)
        recipe = {"version": 1, "kind": "motion", "title": job["title"] + " · 草稿",
                  "cell": job["cell"], "anchor": job.get("anchor", [.5, 1]), "background": "keep", "resample": "lanczos",
                  "source": {"provider": job["provider"], "status": "draft", "referenceSha256": job["reference"]["sha256"],
                             "note": "Actual individually generated frames; operator reviews do not certify cycle semantics or game acceptance.", "frames": audits},
                  "states": [{"name": a["name"], "loop": a["loop"], "fps": 10} for a in job["actions"]]}
        write_json(root / "recipe.json", recipe)
        build(root / "recipe.json", root / "source.json", root / "bundle", aseprite=True)
        cycles = {}
        for action in job["actions"]:
            audit = job.get("cycleReviews", {}).get(action["name"])
            if audit and audit["signature"] == cycle_signature(job, action, path):
                cycles[action["name"]] = audit
        write_json(root / "generation-review.json", {"status": "draft", "frames": audits,
                    "cycleReview": cycles or "not-completed", "gameReview": "not-completed"})
        root.rename(out)
    return out / "bundle" / "manifest.json"


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    subs = parser.add_subparsers(dest="command", required=True)
    prep = subs.add_parser("prepare")
    prep.add_argument("--reference", type=Path, required=True)
    prep.add_argument("--identity", required=True)
    prep.add_argument("--spec", type=Path)
    prep.add_argument("--out", type=Path, required=True)
    for name in ("import", "select", "review", "cycle-review", "pack", "status", "inspect"):
        sub = subs.add_parser(name)
        sub.add_argument("--job", type=Path, required=True)
        if name in ("import", "select", "review"):
            sub.add_argument("--frame", required=True)
        if name == "import":
            sub.add_argument("--image", type=Path, required=True)
            sub.add_argument("--offset", type=int, nargs=2, default=[0, 0])
            sub.add_argument("--prompt", type=Path)
            sub.add_argument("--reference-inputs", type=Path, nargs="+")
            sub.add_argument("--candidate-only", action="store_true")
        elif name == "select":
            sub.add_argument("--attempt-index", type=int, required=True)
        elif name in ("review", "cycle-review"):
            if name == "cycle-review":
                sub.add_argument("--action", required=True)
            else:
                sub.add_argument("--attempt-index", type=int)
            sub.add_argument("--verdict", choices=["accept", "reject"], required=True)
            sub.add_argument("--reviewer", choices=["agent", "user"], required=True)
            sub.add_argument("--reason", required=True)
        elif name in ("pack", "inspect"):
            sub.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    try:
        if args.command == "prepare":
            result = prepare(args.reference.resolve(), args.identity, args.out.resolve(), args.spec.resolve() if args.spec else None)
        elif args.command == "import":
            result = ingest(args.job.resolve(), args.frame, args.image.resolve(), args.offset, args.prompt, args.reference_inputs, args.candidate_only)
        elif args.command == "select":
            result = select_attempt(args.job.resolve(), args.frame, args.attempt_index)
        elif args.command == "review":
            result = review(args.job.resolve(), args.frame, args.verdict, args.reason, args.reviewer, args.attempt_index)
        elif args.command == "cycle-review":
            result = review_cycle(args.job.resolve(), args.action, args.verdict, args.reason, args.reviewer)
        elif args.command == "pack":
            result = pack(args.job.resolve(), args.out.resolve())
        elif args.command == "inspect":
            result = inspect_job(args.job.resolve(), args.out.resolve())
        else:
            job = load_job(args.job.resolve())
            result = {fid: {"attempts": len(f["attempts"]), "selected": f["selected"],
                       "review": f["attempts"][f["selected"]]["review"] if f["selected"] is not None else None}
                      for fid, f in job["frames"].items()}
        print(json.dumps(result, ensure_ascii=False, default=str))
    except (ValueError, KeyError, OSError) as error:
        parser.error(str(error))


if __name__ == "__main__":
    main()
