"""配方驱动的素材交付入口：静态尺寸包、动作图集、离线预览与来源记录。"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
import re
import tempfile
from pathlib import Path

from PIL import Image

import contact
from bundle_preview import write_preview
from cutout import cutout_chroma
from utils import IMG_EXTS

ROOT = Path(__file__).resolve().parents[1]
VERSION = "1.0"


def read_json(path: Path) -> dict:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"JSON 顶层必须是对象: {path}")
    return value


def write_json(path: Path, value: dict) -> None:
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def integer(value, label: str, maximum: int = 16384, minimum: int = 1) -> int:
    if type(value) is not int or not minimum <= value <= maximum:
        raise ValueError(f"{label} 必须是 {minimum}..{maximum} 的整数")
    return value


def number(value, label: str, minimum: float, maximum: float) -> float:
    if type(value) not in (int, float) or not math.isfinite(value) or not minimum <= value <= maximum:
        raise ValueError(f"{label} 必须在 {minimum}..{maximum} 之间")
    return float(value)


def identifier(value) -> str:
    if not isinstance(value, str) or not re.fullmatch(r"[a-zA-Z0-9][a-zA-Z0-9_-]{0,63}", value):
        raise ValueError("动作名必须是 1..64 位英文字母、数字、下划线或连字符")
    return value


def within(root: Path, relative: str) -> Path:
    if not isinstance(relative, str) or not relative:
        raise ValueError("输入相对路径不能为空")
    path = (root / relative).resolve()
    if not path.is_relative_to(root.resolve()):
        raise ValueError(f"输入路径越过素材目录: {relative}")
    return path


def natural_key(path: Path):
    return [int(part) if part.isdigit() else part.lower() for part in re.split(r"(\d+)", path.name)]


def image_paths(directory: Path) -> list[Path]:
    if not directory.is_dir():
        raise ValueError(f"找不到图片目录: {directory}")
    paths = sorted((p for p in directory.iterdir() if p.is_file() and p.suffix.lower() in IMG_EXTS), key=natural_key)
    if not paths:
        raise ValueError(f"目录中没有图片: {directory}")
    return paths


def load_image(path: Path, recipe: dict) -> Image.Image:
    with Image.open(path) as source:
        if getattr(source, "n_frames", 1) != 1:
            raise ValueError(f"请先导出静态帧，不能默默丢弃动图帧: {path}")
        image = source.convert("RGBA")
    if recipe.get("background", "keep") == "chroma":
        if min(image.size) < 2:
            raise ValueError("chroma 输入长宽至少为 2 像素")
        # 复用现有去背算法；已有 alpha 与新蒙版相乘，避免透明区域被重新填实。
        import numpy as np
        cut = cutout_chroma(image, recipe.get("tolerance", 60))
        alpha = np.asarray(image.getchannel("A"), dtype=np.uint16)
        mask = np.asarray(cut.getchannel("A"), dtype=np.uint16)
        cut.putalpha(Image.fromarray(((alpha * mask) // 255).astype("uint8")))
        image = cut
    return image


def resampler(recipe: dict):
    return Image.Resampling.NEAREST if recipe.get("resample") == "nearest" else Image.Resampling.LANCZOS


def fit_canvas(image: Image.Image, cell: tuple[int, int], sample) -> Image.Image:
    # 整张画布统一等比变换，不按每帧主体 bbox 重定位；相同源画布得到相同变换。
    scale = min(cell[0] / image.width, cell[1] / image.height)
    size = (max(1, round(image.width * scale)), max(1, round(image.height * scale)))
    resized = image.resize(size, sample)
    canvas = Image.new("RGBA", cell)
    # RGBA 到空白 RGBA 直接复制，不能再把源 alpha 当 mask，否则半透明边缘会被乘两次。
    canvas.paste(resized, ((cell[0] - size[0]) // 2, (cell[1] - size[1]) // 2))
    return canvas


def validate_recipe(recipe: dict) -> None:
    if recipe.get("version") != 1 or recipe.get("kind") not in ("static", "motion"):
        raise ValueError("配方需要 version: 1 和 kind: static / motion")
    if not isinstance(recipe.get("title"), str) or not recipe["title"].strip():
        raise ValueError("配方 title 不能为空")
    if not isinstance(recipe.get("source", {}), dict):
        raise ValueError("source 必须是来源记录对象")
    if recipe.get("background", "keep") not in ("keep", "chroma"):
        raise ValueError("background 只支持 keep / chroma")
    if recipe.get("resample", "lanczos") not in ("nearest", "lanczos"):
        raise ValueError("resample 只支持 nearest / lanczos")
    integer(recipe.get("tolerance", 60), "tolerance", 255)
    if recipe["kind"] == "static":
        sizes = recipe.get("sizes")
        if not isinstance(sizes, list) or not sizes:
            raise ValueError("静态配方需要非空 sizes")
        for size in sizes:
            integer(size, "size", 4096)
        if len(sizes) != len(set(sizes)):
            raise ValueError("sizes 不能重复")
        return
    cell = recipe.get("cell")
    if not isinstance(cell, list) or len(cell) != 2:
        raise ValueError("motion.cell 必须是 [宽, 高]")
    for n in cell:
        integer(n, "cell", 4096)
    anchor = recipe.get("anchor", [0.5, 1])
    if not isinstance(anchor, list) or len(anchor) != 2:
        raise ValueError("anchor 必须是 [x, y]，范围 0..1")
    for n in anchor:
        number(n, "anchor", 0, 1)
    states = recipe.get("states")
    if not isinstance(states, list) or not states:
        raise ValueError("动作配方需要非空 states")
    names = []
    for state in states:
        if not isinstance(state, dict):
            raise ValueError("state 必须是对象")
        names.append(identifier(state.get("name")))
        number(state.get("fps", 8), "fps", 1, 240)
        if type(state.get("loop")) is not bool:
            raise ValueError("每个动作必须显式声明 loop: true / false")
    if len(set(names)) != len(names):
        raise ValueError("动作名称不能重复")


def inspect(image: Image.Image, label: str, warnings: list[str], motion: bool = False) -> dict:
    alpha = image.getchannel("A")
    bbox = alpha.getbbox()
    if bbox is None:
        raise ValueError(f"全透明素材: {label}")
    if motion and alpha.getextrema()[0] != 0:
        raise ValueError(f"动作帧缺少透明背景: {label}；先去背或显式使用 chroma 配方")
    if motion and (bbox[0] == 0 or bbox[1] == 0 or bbox[2] == image.width or bbox[3] == image.height):
        warnings.append(f"{label} 主体触及画布边缘，请检查裁切")
    return {"label": label, "bbox": list(bbox), "alphaRange": list(alpha.getextrema())}


def static_bundle(source: Path, root: Path, recipe: dict, report: dict, inputs: set[Path]) -> dict:
    paths = [source] if source.is_file() else image_paths(source)
    entries = []
    for i, path in enumerate(paths):
        inputs.add(path)
        image = load_image(path, recipe)
        report["measurements"].append(inspect(image, path.name, report["warnings"]))
        for size in recipe["sizes"]:
            directory = root / "images" / str(size)
            directory.mkdir(parents=True, exist_ok=True)
            out = directory / f"{i + 1:03d}.png"
            fitted = fit_canvas(image, (size, size), resampler(recipe))
            # 小尺寸重采样可能把细小主体完全抹掉，不能只检查原图就声称产物可用。
            report["measurements"].append(inspect(fitted, f"{path.name} @ {size}px", report["warnings"]))
            fitted.save(out)
            entries.append({"name": path.name, "path": out.relative_to(root).as_posix(), "width": size, "height": size})
    report["manualChecks"] = ["目标尺寸下的轮廓和主体特征是否清楚", "浅色与深色背景的边缘、背景及配色", "候选是否符合项目风格；自动检查不判断审美"]
    return {"images": entries}


def directory_states(source: Path, recipe: dict, inputs: set[Path]) -> list[dict]:
    states = []
    for spec in recipe["states"]:
        directory = within(source, spec.get("directory", spec["name"]))
        paths = image_paths(directory)
        inputs.update(paths)
        frames = [load_image(path, recipe) for path in paths]
        states.append({"name": spec["name"], "loop": spec["loop"], "images": frames,
                       "durations": [round(1000 / spec.get("fps", 8))] * len(frames),
                       "sourceFrames": [p.relative_to(source).as_posix() for p in paths]})
    return states


def aseprite_states(path: Path, recipe: dict, inputs: set[Path]) -> list[dict]:
    data = read_json(path)
    meta = data.get("meta", {})
    if not isinstance(meta, dict):
        raise ValueError("Aseprite meta 必须是对象")
    atlas_path = within(path.parent, meta.get("image"))
    inputs.update((path, atlas_path))
    atlas = load_image(atlas_path, {"background": "keep"})
    records = data.get("frames")
    if isinstance(records, dict):
        # sprite-gen json-hash 的键是帧索引；不得把 10 排在 2 之前。
        if not all(str(key).isdigit() for key in records):
            raise ValueError("hash 帧格式只接受连续数字索引；请上游导出 json-array")
        keys = sorted(records, key=int)
        if [int(key) for key in keys] != list(range(len(keys))):
            raise ValueError("hash 帧索引必须从 0 连续递增")
        records = [records[key] for key in keys]
    if not isinstance(records, list) or not records:
        raise ValueError("Aseprite 导出缺少 frames")
    tags = meta.get("frameTags", [])
    if not isinstance(tags, list) or any(not isinstance(tag, dict) for tag in tags):
        raise ValueError("frameTags 格式错误")
    if len({tag.get("name") for tag in tags}) != len(tags):
        raise ValueError("frameTags 动作名重复")
    states = []
    for spec in recipe["states"]:
        matches = [t for t in tags if t.get("name") == spec["name"]]
        if len(matches) != 1:
            raise ValueError(f"找不到动作标签: {spec['name']}")
        tag = matches[0]
        if tag.get("direction", "forward") != "forward":
            raise ValueError("只接受 forward 标签；请在上游烘焙 reverse / pingpong 顺序")
        start = integer(tag.get("from"), "tag.from", len(records) - 1, 0)
        end = integer(tag.get("to"), "tag.to", len(records) - 1, start)
        frames, durations = [], []
        for entry in records[start:end + 1]:
            if not isinstance(entry, dict) or entry.get("rotated") or entry.get("trimmed"):
                raise ValueError("当前适配器只接受未旋转、未 trim 的完整帧")
            rect = entry.get("frame", {})
            if not isinstance(rect, dict):
                raise ValueError("Aseprite frame 必须是矩形对象")
            x = integer(rect.get("x"), "frame.x", atlas.width - 1, 0)
            y = integer(rect.get("y"), "frame.y", atlas.height - 1, 0)
            w = integer(rect.get("w"), "frame.w", atlas.width)
            h = integer(rect.get("h"), "frame.h", atlas.height)
            if x + w > atlas.width or y + h > atlas.height:
                raise ValueError("帧矩形越过图集边界")
            frames.append(atlas.crop((x, y, x + w, y + h)))
            durations.append(integer(entry.get("duration"), "duration", 60000))
        states.append({"name": spec["name"], "loop": spec["loop"], "images": frames,
                       "durations": durations, "sourceFrames": list(range(start, end + 1))})
    return states


def motion_bundle(source: Path, root: Path, recipe: dict, report: dict, inputs: set[Path], aseprite: bool) -> dict:
    states = aseprite_states(source, recipe, inputs) if aseprite else directory_states(source, recipe, inputs)
    sizes = {frame.size for state in states for frame in state["images"]}
    if len(sizes) != 1:
        raise ValueError(f"整套动作的源画布必须一致，禁止逐帧缩放掩盖漂移: {sorted(sizes)}")
    cols = max(len(s["images"]) for s in states)
    cell = tuple(recipe["cell"])
    width, height = cols * cell[0], len(states) * cell[1]
    if width > 16384 or height > 16384 or width * height > 64_000_000:
        raise ValueError("图集过大，请减少帧数或目标尺寸")
    atlas = Image.new("RGBA", (width, height))
    output_states, aseprite_frames, tags = [], [], []
    for row, state in enumerate(states):
        directory = root / "frames" / state["name"]
        directory.mkdir(parents=True)
        rects, hashes = [], []
        start = len(aseprite_frames)
        for i, (image, duration) in enumerate(zip(state["images"], state["durations"])):
            label = f"{state['name']} / {i + 1}"
            inspect(image, label + " 源帧", report["warnings"], motion=True)
            frame = fit_canvas(image, cell, resampler(recipe))
            report["measurements"].append(inspect(frame, label, report["warnings"], motion=True))
            hashes.append(hashlib.sha256(frame.tobytes()).hexdigest())
            frame.save(directory / f"{i:04d}.png")
            atlas.paste(frame, (i * cell[0], row * cell[1]))
            rect = {"x": i * cell[0], "y": row * cell[1], "w": cell[0], "h": cell[1]}
            rects.append({**rect, "durationMs": duration})
            aseprite_frames.append({"filename": str(len(aseprite_frames)), "frame": rect,
                                    "rotated": False, "trimmed": False,
                                    "spriteSourceSize": {"x": 0, "y": 0, "w": cell[0], "h": cell[1]},
                                    "sourceSize": {"w": cell[0], "h": cell[1]}, "duration": duration})
        if len(set(hashes)) == 1:
            report["warnings"].append(f"{state['name']} 只有一个不同姿态，不能据此认定动作有效")
        # 补齐格子仅用于固定网格消费者；真实帧数和时长保留在 manifest，不能当作新增帧。
        for col in range(len(state["images"]), cols):
            atlas.paste(frame, (col * cell[0], row * cell[1]))
        contact.build(str(directory), str(root / f"contact-{state['name']}.png"), cols=min(8, len(rects)), cell=128)
        output_states.append({"name": state["name"], "loop": state["loop"], "frames": rects,
                              "sourceFrames": state["sourceFrames"]})
        tags.append({"name": state["name"], "from": start, "to": len(aseprite_frames) - 1, "direction": "forward"})
    atlas.save(root / "atlas.png")
    write_json(root / "aseprite.json", {"frames": aseprite_frames, "meta": {"image": "atlas.png", "size": {"w": width, "h": height}, "frameTags": tags}})
    write_json(root / "grid.json", {"sheet": "atlas.png", "columns": cols, "rows": len(states),
                                    "cellWidth": cell[0], "cellHeight": cell[1],
                                    "rowOrder": [s["name"] for s in states],
                                    "frameCounts": {s["name"]: len(s["images"]) for s in states},
                                    "padding": "repeat-last; use manifest for timing and true frame counts"})
    report["manualChecks"] = ["角色身份、朝向及跨动作尺寸是否一致", "脚底是否漂移、武器是否裁切；bbox 不是接触点证明", "走跑时左右腿是否交替落地、承重、经过和蹬离；不同图片不等于完整步态", "循环接缝和单次动作的前摇、命中、收招", "在目标游戏运行后另存证据；此处未验证碰撞或命中窗口"]
    return {"atlas": "atlas.png", "anchor": recipe.get("anchor", [0.5, 1]),
            "anchorConvention": "normalized-from-top-left; metadata only, no automatic foot alignment",
            "states": output_states, "exports": ["aseprite.json", "grid.json"]}


def build(recipe_path: Path, source: Path, out: Path, aseprite: bool = False) -> Path:
    recipe_path, source, out = recipe_path.resolve(), source.resolve(), out.resolve()
    recipe = read_json(recipe_path)
    validate_recipe(recipe)
    if not source.exists():
        raise ValueError(f"输入不存在: {source}")
    if out.exists():
        raise ValueError(f"输出已存在，请选择新批次目录: {out}")
    if source.is_dir() and out.is_relative_to(source):
        raise ValueError("输出目录不能放进输入素材目录")
    if aseprite and (recipe["kind"] != "motion" or recipe.get("background", "keep") != "keep"):
        raise ValueError("Aseprite 输入要求 motion 配方和 background: keep，保留上游最终 alpha")
    report = {"status": "needs-human-review", "warnings": [], "measurements": [], "manualChecks": []}
    inputs = {recipe_path}
    out.parent.mkdir(parents=True, exist_ok=True)
    # 所有阶段先写临时目录，失败不留下看似完成的素材包，也不覆盖历史批次。
    with tempfile.TemporaryDirectory(prefix=".asset-bundle-", dir=out.parent) as tmp:
        stage = Path(tmp) / "bundle"
        stage.mkdir()
        content = static_bundle(source, stage, recipe, report, inputs) if recipe["kind"] == "static" else motion_bundle(source, stage, recipe, report, inputs, aseprite)
        manifest = {"version": 1, "toolVersion": VERSION, "kind": recipe["kind"], "title": recipe["title"],
                    "source": recipe.get("source", {}), "release": {"status": "draft", "runtimeEvidence": None}, **content}
        provenance = {"toolVersion": VERSION, "inputMode": "aseprite" if aseprite else "files", "recipe": recipe,
                      "sourceRoot": str(source), "inputs": [{"path": str(p), "sha256": hashlib.sha256(p.read_bytes()).hexdigest()} for p in sorted(inputs)],
                      "reproduce": {"recipe": str(recipe_path), "input": str(source), "aseprite": aseprite},
                      "environment": {"pillow": Image.__version__}}
        write_json(stage / "manifest.json", manifest)
        write_json(stage / "report.json", report)
        write_json(stage / "provenance.json", provenance)
        write_preview(stage, manifest, report)
        stage.rename(out)
    return out


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--recipe", type=Path, required=True)
    parser.add_argument("--input", type=Path, required=True, help="图片/图片目录；动作目录；或 --aseprite 的最终 JSON")
    parser.add_argument("--out", type=Path, required=True, help="新的批次目录，拒绝覆盖")
    parser.add_argument("--aseprite", action="store_true", help="读取上游 compose 后的 Aseprite JSON，保留每帧时长")
    args = parser.parse_args()
    try:
        result = build(args.recipe, args.input, args.out, args.aseprite)
    except (ValueError, OSError, KeyError, TypeError) as error:
        parser.exit(2, f"素材打包失败：{error}\n")
    print(f"素材包：{result}\n预览：{result / 'preview.html'}\n状态：草稿，待人工和消费项目验收")


if __name__ == "__main__":
    main()
