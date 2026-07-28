"""一条命令跑完整链路：切图 -> 去背 -> 缩放 -> 两张质检联络表。

用法:
  python src/run.py input/grid.png                       # 默认 6x6, 96px
  python src/run.py input/grid.png -r 6 -c 6 --size 128 --autocrop
  python src/run.py input/grid.png --floodfill           # 不用 rembg

产物（以网格图名 <stem> 归档到 output/<stem>/）:
  slices/    等分切图
  cutouts/   去背透明 PNG
  resized/   缩到游戏尺寸
  contact_cutouts.png  / contact_resized.png   质检表
"""

from __future__ import annotations

import argparse
from pathlib import Path

import slice_grid
import cutout
import resize
import contact
from utils import ensure_dir


def main() -> None:
    ap = argparse.ArgumentParser(description="AI 素材后处理全流程")
    ap.add_argument("src", help="网格图路径")
    ap.add_argument("-r", "--rows", type=int, default=6)
    ap.add_argument("-c", "--cols", type=int, default=6)
    ap.add_argument("--size", type=int, default=96, help="游戏内目标长边像素")
    ap.add_argument("--autocrop", action="store_true", help="切图按内容裁背景")
    ap.add_argument("--gutter", type=int, default=0, help="每格内缩像素")
    ap.add_argument("--square", action="store_true", help="缩放补正方形")
    ap.add_argument("--floodfill", action="store_true", help="去背强制用 flood-fill")
    ap.add_argument(
        "--chroma", action="store_true", help="去背用绿幕式（配 #FF00FF 等高饱和背景）"
    )
    ap.add_argument("--tolerance", type=int, default=32)
    args = ap.parse_args()

    stem = Path(args.src).stem
    base = ensure_dir(Path("output") / stem)
    d_slices = str(base / "slices")
    d_cut = str(base / "cutouts")
    d_resized = str(base / "resized")

    print(f"\n===== 处理 {args.src}  ({args.rows}x{args.cols}) =====")
    slice_grid.slice_grid(
        args.src,
        args.rows,
        args.cols,
        d_slices,
        autocrop=args.autocrop,
        gutter=args.gutter,
    )
    cutout.run(
        d_slices,
        d_cut,
        tolerance=args.tolerance,
        force_floodfill=args.floodfill,
        chroma=args.chroma,
    )
    resize.run(d_cut, d_resized, args.size, square=args.square)
    contact.build(d_cut, str(base / "contact_cutouts.png"), cols=args.cols)
    contact.build(d_resized, str(base / "contact_resized.png"), cols=args.cols)

    print(f"\n[完成] 全部产物在: {base.resolve()}")
    print("       先看 contact_cutouts.png 检查去背 & 一致性")


if __name__ == "__main__":
    main()
