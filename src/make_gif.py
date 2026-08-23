"""把序列帧拼成循环 GIF，用来直接看动作效果。

动作表是给引擎读的，人眼看不出来播起来是什么样。
质检必须看动的东西——抖动、脚底漂移、关节穿帮这些问题，
静态并排看全都发现不了。

游戏尺寸的预览尤其重要：96px 下看着能接受的动作，
放大到 256px 可能很粗糙；反过来也成立，所以两个尺寸都要看。

用法:
  python src/make_gif.py output/frames/hero -o output/preview/hero.gif --fps 12
  python src/make_gif.py output/frames/hero -o output/preview/hero_96.gif --size 96 --scale 3
"""
from __future__ import annotations

import argparse
from pathlib import Path

from PIL import Image

from utils import list_images, ensure_dir


def build(src_dir: Path, out: Path, fps: int, size: int | None, scale: int,
          background: tuple[int, int, int] | None, pingpong: bool) -> None:
    paths = [p for p in list_images(src_dir) if p.suffix.lower() == ".png"]
    if not paths:
        raise SystemExit(f"没找到帧图片: {src_dir}")

    frames = [Image.open(p).convert("RGBA") for p in paths]

    if size:
        # 先缩到游戏尺寸，再整数倍放大——模拟素材在游戏里的真实分辨率，
        # 同时让 GIF 在屏幕上看得清。直接渲小图会看不出锯齿和可读性问题。
        resized = []
        for frame in frames:
            small = frame.copy()
            small.thumbnail((size, size), Image.LANCZOS)
            canvas = Image.new("RGBA", (size, size), (0, 0, 0, 0))
            canvas.paste(small, ((size - small.width) // 2,
                                 (size - small.height) // 2), small)
            resized.append(canvas)
        frames = resized

    if scale > 1:
        # 最近邻放大，保留像素级真相；用插值会把问题磨平。
        frames = [f.resize((f.width * scale, f.height * scale), Image.NEAREST)
                  for f in frames]

    # GIF 不支持半透明，只有全透或全不透。给个底色比留透明干净，
    # 否则边缘半透明像素会被强行判成不透明，看着像描边。
    fill = background or (24, 24, 28)
    flat = []
    for frame in frames:
        canvas = Image.new("RGB", frame.size, fill)
        canvas.paste(frame, (0, 0), frame)
        flat.append(canvas)

    if pingpong and len(flat) > 2:
        flat = flat + flat[-2:0:-1]

    ensure_dir(out.parent)
    duration = max(1, round(1000 / fps))
    flat[0].save(out, save_all=True, append_images=flat[1:], loop=0,
                 duration=duration, optimize=True)
    print(f"[make_gif] {len(flat)} 帧 -> {out}  "
          f"{flat[0].width}x{flat[0].height} @ {fps}fps")


def main() -> None:
    ap = argparse.ArgumentParser(description="序列帧 -> 循环 GIF 预览")
    ap.add_argument("src", type=Path)
    ap.add_argument("-o", "--out", type=Path, default=None)
    ap.add_argument("--fps", type=int, default=12)
    ap.add_argument("--size", type=int, default=None,
                    help="先缩到游戏尺寸再放大，检查真实分辨率下的可读性")
    ap.add_argument("--scale", type=int, default=1, help="最近邻整数倍放大")
    ap.add_argument("--bg", default=None, help="底色，如 #1a1a1c")
    ap.add_argument("--pingpong", action="store_true",
                    help="来回播，非循环动作用这个看得清")
    args = ap.parse_args()

    background = None
    if args.bg:
        value = args.bg.lstrip("#")
        background = tuple(int(value[i:i + 2], 16) for i in (0, 2, 4))

    out = args.out or Path("output/preview") / f"{args.src.name}.gif"
    build(args.src, out, args.fps, args.size, args.scale, background, args.pingpong)


if __name__ == "__main__":
    main()
