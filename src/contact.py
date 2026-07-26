"""把一个目录的图拼成质检联络表（contact sheet），一眼看风格一致性。

- 棋盘格底色，透明区域一目了然
- 每张图下标文件名
- 可把多个目录并排对比（验证「补图漂移」用）

用法:
  python src/contact.py output/cutouts -o output/contact/cutouts.png
  python src/contact.py output/slices --cols 6 --cell 160
"""
from __future__ import annotations

import argparse
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont

from utils import list_images, ensure_dir


def _checker(size: int, box: int = 8,
             a=(210, 210, 210), b=(170, 170, 170)) -> Image.Image:
    img = Image.new("RGB", (size, size), a)
    d = ImageDraw.Draw(img)
    for y in range(0, size, box):
        for x in range(0, size, box):
            if (x // box + y // box) % 2:
                d.rectangle([x, y, x + box, y + box], fill=b)
    return img


def _font(sz: int):
    for name in ("consola.ttf", "arial.ttf", "DejaVuSansMono.ttf"):
        try:
            return ImageFont.truetype(name, sz)
        except Exception:
            continue
    return ImageFont.load_default()


def build(src_dir: str, out: str, cols: int = 6, cell: int = 150,
          label: bool = True):
    imgs = list_images(src_dir)
    if not imgs:
        print(f"[contact] 没找到图片: {src_dir}")
        return
    label_h = 18 if label else 0
    pad = 6
    tile = cell + pad * 2
    rows = (len(imgs) + cols - 1) // cols
    sheet_w = cols * tile
    sheet_h = rows * (tile + label_h)
    sheet = Image.new("RGB", (sheet_w, sheet_h), (30, 30, 30))
    draw = ImageDraw.Draw(sheet)
    font = _font(11)
    checker = _checker(cell)

    for i, p in enumerate(imgs):
        r, c = divmod(i, cols)
        x = c * tile + pad
        y = r * (tile + label_h) + pad
        thumb = Image.open(p).convert("RGBA")
        thumb.thumbnail((cell, cell), Image.LANCZOS)
        bg = checker.copy()
        ox = (cell - thumb.width) // 2
        oy = (cell - thumb.height) // 2
        bg.paste(thumb, (ox, oy), thumb)
        sheet.paste(bg, (x, y))
        if label:
            draw.text((x, y + cell + 3), p.stem, fill=(200, 200, 200), font=font)

    ensure_dir(Path(out).parent)
    sheet.save(out)
    print(f"[contact] {len(imgs)} 张 -> {out}  ({sheet_w}x{sheet_h})")


def main() -> None:
    ap = argparse.ArgumentParser(description="生成质检联络表")
    ap.add_argument("src")
    ap.add_argument("-o", "--out", default="output/contact/sheet.png")
    ap.add_argument("--cols", type=int, default=6)
    ap.add_argument("--cell", type=int, default=150, help="单格像素")
    ap.add_argument("--no-label", action="store_true")
    args = ap.parse_args()
    build(args.src, args.out, cols=args.cols, cell=args.cell,
          label=not args.no_label)


if __name__ == "__main__":
    main()
