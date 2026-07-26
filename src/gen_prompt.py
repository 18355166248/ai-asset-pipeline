"""填空生成「可直接粘贴到 GPT/Gemini」的 6×6 网格提示词。

例:
  python src/gen_prompt.py --style flat --bg "#F2EFE9" --view "3/4 top-down" \
    --items "苹果,香蕉,西瓜, ...(36个，逗号或换行分隔)"

  # 从文件读物件列表（一行一个）
  python src/gen_prompt.py --style clay --items-file my_items.txt

  # 用预置游戏配方（不同游戏一行出一套）
  python src/gen_prompt.py --recipe collect-animals
  python src/gen_prompt.py --list-recipes

  # 只想看某个画风词
  python src/gen_prompt.py --list-styles
"""
from __future__ import annotations

import argparse
import sys

import recipes as _recipes

STYLES = {
    "flat": ("Cute flat-vector game icon, soft rounded shapes, thick uniform "
             "outline, 2-3 flat color tones per item with simple cel shading, "
             "clean and playful mobile-game look, soft top-left lighting."),
    "clay": ("Cute 3D cartoon render, soft clay-like material, rounded chunky "
             "shapes, glossy but not reflective, gentle studio lighting, "
             "isometric 3/4 view, playful mobile game asset look."),
    "handdrawn": ("Hand-drawn cartoon style, slightly wobbly ink outline, warm "
                  "gouache-like flat coloring, cozy storybook game look, even "
                  "soft lighting."),
    "pixel": ("Clean pixel-art game sprite, limited cohesive palette, crisp "
              "pixels, subtle dithering for shading, consistent top-left light, "
              "retro 16-bit look, no anti-aliased edges."),
    "line": ("Minimal line-icon style, uniform rounded stroke, single accent "
             "fill color, flat and geometric, modern clean UI look, no gradient."),
    "realistic": ("Semi-realistic glossy game icon, soft rendered volume, rich "
                  "clean colors, smooth gradients inside the item only, studio "
                  "product lighting, 3/4 view, polished casual-game look."),
}

TEMPLATE = """Create ONE single square image containing a strict {rows}x{cols} grid \
({n} cells, {rows} rows by {cols} columns), evenly spaced.

STYLE (identical for all {n} items):
{style}
Keep the SAME art style across every cell: same line weight, same shading \
method, same color grading, same camera angle, same lighting direction.

CONTENT - one item per cell, left-to-right, top-to-bottom:
{items}

LAYOUT RULES (strict):
- Exactly {n} items, one centered item per cell, no empty cell, no duplicates.
- Each item occupies about 70% of its cell, consistent scale and margins.
- Same orientation for all items ({view}).

BACKGROUND (critical):
- A single FLAT solid background color {bg} filling the whole image.
- Absolutely NO gradient, NO drop shadow, NO reflection, NO texture.

DO NOT include: any text, numbers, labels, captions, grid lines, cell borders, \
frames, watermark, or signature.

Output: one 1:1 square image, high resolution."""


def parse_items(args) -> list[str]:
    raw = ""
    if args.items_file:
        with open(args.items_file, encoding="utf-8") as f:
            raw = f.read()
        parts = [x.strip() for x in raw.replace(",", "\n").splitlines()]
    else:
        parts = [x.strip() for x in (args.items or "").replace("\n", ",").split(",")]
    return [p for p in parts if p]


def numbered(items: list[str], cols: int) -> str:
    lines, row = [], []
    for i, it in enumerate(items, 1):
        row.append(f"{i}. {it}")
        if i % cols == 0:
            lines.append("  ".join(row)); row = []
    if row:
        lines.append("  ".join(row))
    return "\n".join(lines)


def main() -> None:
    ap = argparse.ArgumentParser(description="生成 6×6 网格提示词")
    ap.add_argument("--style", default="flat",
                    help=f"画风键: {', '.join(STYLES)}（或直接写整段英文画风）")
    ap.add_argument("--bg", default="#F2EFE9", help="纯平背景色")
    ap.add_argument("--view", default="front view",
                    help="统一视角，如 'front view' / '3/4 top-down view'")
    ap.add_argument("--rows", type=int, default=6)
    ap.add_argument("--cols", type=int, default=6)
    ap.add_argument("--items", help="逗号/换行分隔的物件")
    ap.add_argument("--items-file", help="物件列表文件（一行一个）")
    ap.add_argument("--recipe", help="用预置游戏配方（见 --list-recipes）")
    ap.add_argument("--list-styles", action="store_true")
    ap.add_argument("--list-recipes", action="store_true")
    args = ap.parse_args()

    if args.list_styles:
        for k, v in STYLES.items():
            print(f"\n[{k}]\n{v}")
        return

    if args.list_recipes:
        print("可用配方（--recipe NAME）：")
        for k in _recipes.names():
            r = _recipes.get(k)
            print(f"  {k:18} {r['desc']}  [style={r['style']}, view={r['view']}]")
        return

    # 配方优先：把 style/view/bg/items 一并带出（命令行显式参数仍可覆盖）
    if args.recipe:
        r = _recipes.get(args.recipe)
        if not r:
            print(f"⚠ 无此配方: {args.recipe}，用 --list-recipes 查看", file=sys.stderr)
            return
        if args.style == "flat":       # 未手动改画风时用配方的
            args.style = r["style"]
        if args.view == "front view":  # 未手动改视角时用配方的
            args.view = r["view"]
        if args.bg == "#F2EFE9":       # 未手动改背景时用配方的
            args.bg = r["bg"]
        if not args.items and not args.items_file:
            args.items = ",".join(r["items"])

    style = STYLES.get(args.style, args.style)
    items = parse_items(args)
    n = args.rows * args.cols
    if not items:
        print("⚠ 未提供物件（--items 或 --items-file）。"
              f"仍生成模板，请手动填 {n} 个物件占位。", file=sys.stderr)
        items_block = f"{{在此列出 {n} 个物件，编号 1-{n}}}"
    else:
        if len(items) != n:
            print(f"⚠ 物件数 {len(items)} ≠ {n}（{args.rows}×{args.cols}），"
                  "请补齐或调整行列。", file=sys.stderr)
        items_block = numbered(items, args.cols)

    print(TEMPLATE.format(rows=args.rows, cols=args.cols, n=n, style=style,
                          items=items_block, view=args.view, bg=args.bg))


if __name__ == "__main__":
    main()
