"""批量缩放到目标像素（游戏内实际尺寸），LANCZOS 高质量。

用法:
  python src/resize.py output/cutouts --size 96 -o output/resized
  python src/resize.py output/cutouts --size 128 --square    # 缩放后补成正方形
"""
from __future__ import annotations

import argparse
from PIL import Image

from utils import list_images, ensure_dir, pad_to_square


def run(src_dir: str, out_dir: str, size: int, square: bool = False):
    imgs = list_images(src_dir)
    if not imgs:
        print(f"[resize] 没找到图片: {src_dir}")
        return
    out = ensure_dir(out_dir)
    for p in imgs:
        img = Image.open(p)
        img = img.convert("RGBA") if p.suffix.lower() == ".png" else img.convert("RGB")
        w, h = img.size
        scale = size / max(w, h)
        img = img.resize((max(1, round(w * scale)), max(1, round(h * scale))),
                         Image.LANCZOS)
        if square:
            img = pad_to_square(img)
        img.save(out / f"{p.stem}.png")
    print(f"[resize] {len(imgs)} 张 -> {size}px{' 正方形' if square else ''}  输出: {out}")


def main() -> None:
    ap = argparse.ArgumentParser(description="批量缩放到目标像素")
    ap.add_argument("src")
    ap.add_argument("-o", "--out", default="output/resized")
    ap.add_argument("--size", type=int, default=96, help="长边目标像素")
    ap.add_argument("--square", action="store_true", help="缩放后补成正方形画布")
    args = ap.parse_args()
    run(args.src, args.out, args.size, square=args.square)


if __name__ == "__main__":
    main()
