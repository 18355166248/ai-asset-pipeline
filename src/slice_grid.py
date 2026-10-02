"""把一张 N×M 网格图切成单张 item。

用法:
  python src/slice_grid.py input/grid.png --rows 6 --cols 6 --autocrop
  python src/slice_grid.py input/grid.png -r 6 -c 6                 # 纯等分
"""
from __future__ import annotations

import argparse
from pathlib import Path
from PIL import Image

from utils import detect_bg_color, content_bbox, ensure_dir


def slice_grid(src: str, rows: int, cols: int, out_dir: str,
               autocrop: bool = False, thresh: int = 30, margin: int = 4,
               gutter: int = 0) -> list[Path]:
    if rows < 1 or cols < 1 or gutter < 0:
        raise ValueError("行列数必须大于 0，内缩像素不能为负")
    img = Image.open(src).convert("RGB")
    W, H = img.size
    cell_w = W / cols
    cell_h = H / rows
    # 先检查最小单元格，避免参数错误时留下半套切图。
    if W // cols <= 2 * gutter or H // rows <= 2 * gutter:
        raise ValueError("网格过密或 gutter 过大，单元格没有可用像素")
    bg = detect_bg_color(img)
    out = ensure_dir(out_dir)
    stem = Path(src).stem
    saved: list[Path] = []

    for row in range(rows):
        for col in range(cols):
            # 等分切格，gutter 用于收缩单元格避免吃到相邻格
            left = int(round(col * cell_w)) + gutter
            t = int(round(row * cell_h)) + gutter
            r = int(round((col + 1) * cell_w)) - gutter
            b = int(round((row + 1) * cell_h)) - gutter
            cell = img.crop((left, t, r, b))

            if autocrop:
                bbox = content_bbox(cell, bg, thresh=thresh, pad=margin)
                if bbox:
                    cell = cell.crop(bbox)

            idx = row * cols + col
            path = out / f"{stem}_{idx:02d}.png"
            cell.save(path)
            saved.append(path)

    print(f"[slice] {src} -> {len(saved)} 张  (bg={bg}, autocrop={autocrop})")
    print(f"[slice] 输出: {out}")
    return saved


def main() -> None:
    ap = argparse.ArgumentParser(description="网格图切单图")
    ap.add_argument("src", help="网格图路径")
    ap.add_argument("-r", "--rows", type=int, default=6)
    ap.add_argument("-c", "--cols", type=int, default=6)
    ap.add_argument("-o", "--out", default="output/slices")
    ap.add_argument("--autocrop", action="store_true",
                    help="按内容自动裁掉每格多余背景")
    ap.add_argument("--thresh", type=int, default=30, help="内容/背景差异阈值")
    ap.add_argument("--margin", type=int, default=4, help="autocrop 保留外扩像素")
    ap.add_argument("--gutter", type=int, default=0,
                    help="每格四边内缩像素，防止吃到相邻格描边")
    args = ap.parse_args()
    slice_grid(args.src, args.rows, args.cols, args.out,
               autocrop=args.autocrop, thresh=args.thresh,
               margin=args.margin, gutter=args.gutter)


if __name__ == "__main__":
    main()
