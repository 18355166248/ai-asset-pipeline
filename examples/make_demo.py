"""生成无需模型、无需联网的机械验证样例；这些几何图形不是正式美术资产。"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from PIL import Image, ImageDraw

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from asset_bundle import build  # noqa: E402


def create_demo(out: Path) -> None:
    if out.exists():
        raise ValueError(f"样例目录已存在，请换一个路径: {out}")
    source = out / "source"
    for folder in ("mascots", "motion/idle", "motion/attack"):
        (source / folder).mkdir(parents=True)
    colors = ["#82d5be", "#ffbd83", "#a6b9ff"]
    for i, color in enumerate(colors):
        image = Image.new("RGBA", (128, 128))
        draw = ImageDraw.Draw(image)
        draw.rounded_rectangle((23, 25, 105, 109), radius=30, fill=color)
        draw.ellipse((39, 51, 47, 65), fill="#182230")
        draw.ellipse((79, 51, 87, 65), fill="#182230")
        draw.arc((53, 68, 74, 86), 0, 180, fill="#182230", width=3)
        image.save(source / "mascots" / f"candidate-{i + 1}.png")
    for state, offsets in (("idle", [0, -1, -2, -1]), ("attack", [0, -4, 9, 18, 6, 0])):
        for i, offset in enumerate(offsets):
            image = Image.new("RGBA", (96, 96))
            draw = ImageDraw.Draw(image)
            draw.rounded_rectangle((30, 24 + (offset if state == "idle" else 0), 65, 74), radius=13, fill=colors[0])
            draw.ellipse((49, 36, 53, 43), fill="#182230")
            draw.rectangle((35, 71, 42, 80), fill="#50798a")
            draw.rectangle((54, 71, 61, 80), fill="#50798a")
            draw.rounded_rectangle((58 + offset, 49, 69 + offset, 57), radius=3, fill="#ffbd83")
            image.save(source / "motion" / state / f"frame-{i + 1}.png")
    for name, kind, input_path in (("mascot", "mascot", source / "mascots"), ("motion", "character", source / "motion")):
        recipe = json.loads((ROOT / "recipes" / f"{kind}.json").read_text())
        recipe["title"] = "几何样例 · " + ("图标尺寸对比" if name == "mascot" else "待机 / 单次攻击")
        recipe["source"] = {"provider": "procedural-fixture", "note": "仅验证加工与预览，不代表 AI 出图效果或正式美术"}
        path = out / f"{name}-recipe.json"
        path.write_text(json.dumps(recipe, ensure_ascii=False, indent=2), encoding="utf-8")
        build(path, input_path, out / name)
    print(f"静态预览: {(out / 'mascot/preview.html').resolve()}")
    print(f"动作预览: {(out / 'motion/preview.html').resolve()}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", type=Path, default=ROOT / "output/toolkit-demo")
    args = parser.parse_args()
    try:
        create_demo(args.out.resolve())
    except (ValueError, OSError) as error:
        parser.exit(2, f"样例生成失败：{error}\n")
