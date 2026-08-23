"""把序列帧打包成游戏用的动作表（sprite sheet）。

和 contact.py 的区别：contact.py 是给人看的质检表（带标签、缩略图、棋盘格底），
这里出的是给引擎读的动作表，必须严格等分、透明、无装饰——
xianxia-roguelike 的 PlayerAnimationRuntime 按 row/column 索引取帧，
格子对不齐会直接错位。

注意：整套动作用 render_clip_set.py 共用归一化渲出来时，**不要逐动作 --trim**。
各动作裁掉的空白量不同，刚统一好的尺寸基准会被重新打破，
游戏里切动作时角色又会跳一下。--trim 只适合单个动作独立出图的场合。

关键约定：裁切框跨所有帧统一算一次。
逐帧各自 autocrop 会让角色在播放时上下跳动（每帧被裁掉的空白不一样多），
这是动作表最隐蔽也最致命的坑——单看每张图都很正常，播起来就是抖的。

用法:
  python src/pack_sheet.py output/frames/apple -o output/sheets/apple.png --cols 4
  python src/pack_sheet.py output/frames/hero --cols 4 --rows 4 --cell 128 --trim
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

from PIL import Image

from utils import list_images, ensure_dir


def common_bbox(images: list[Image.Image], pad: int = 2) -> tuple[int, int, int, int]:
    """所有帧 alpha 通道的并集包围盒。

    取并集而不是逐帧各算，是为了让每一帧在格子里的相对位置保持稳定：
    角色抬手那一帧变高了，其他帧也按同一个框裁，脚底位置才不会漂。
    """
    left, top = 1 << 30, 1 << 30
    right = bottom = 0
    for image in images:
        box = image.getchannel("A").getbbox()
        if box is None:
            continue
        left = min(left, box[0])
        top = min(top, box[1])
        right = max(right, box[2])
        bottom = max(bottom, box[3])
    if right <= left or bottom <= top:
        # 全透明，退回整幅，交给调用方从渲染那头查问题。
        return 0, 0, images[0].width, images[0].height
    width, height = images[0].size
    return (max(0, left - pad), max(0, top - pad),
            min(width, right + pad), min(height, bottom + pad))


def build(src_dir: Path, out: Path, cols: int, rows: int | None,
          cell: int | None, trim: bool) -> None:
    paths = [p for p in list_images(src_dir) if p.name != "manifest.json"]
    if not paths:
        raise SystemExit(f"没找到帧图片: {src_dir}")

    frames = [Image.open(p).convert("RGBA") for p in paths]
    sizes = {f.size for f in frames}
    if len(sizes) != 1:
        raise SystemExit(f"帧尺寸不一致，无法等分打包: {sorted(sizes)}")

    if trim:
        box = common_bbox(frames)
        frames = [f.crop(box) for f in frames]

    if cell:
        # 等比缩到目标格子，再贴到透明正方形画布上居中。
        # 直接 resize 成正方形会把角色压扁。
        packed = []
        for frame in frames:
            scaled = frame.copy()
            scaled.thumbnail((cell, cell), Image.LANCZOS)
            canvas = Image.new("RGBA", (cell, cell), (0, 0, 0, 0))
            canvas.paste(scaled, ((cell - scaled.width) // 2,
                                  (cell - scaled.height) // 2), scaled)
            packed.append(canvas)
        frames = packed

    cell_w, cell_h = frames[0].size
    if rows is None:
        rows = (len(frames) + cols - 1) // cols
    capacity = cols * rows
    if len(frames) > capacity:
        raise SystemExit(f"{len(frames)} 帧放不进 {cols}x{rows} 的表")

    sheet = Image.new("RGBA", (cols * cell_w, rows * cell_h), (0, 0, 0, 0))
    for index, frame in enumerate(frames):
        row, col = divmod(index, cols)
        sheet.paste(frame, (col * cell_w, row * cell_h), frame)

    ensure_dir(out.parent)
    sheet.save(out)

    meta = {
        "sheet": out.name,
        "columns": cols,
        "rows": rows,
        "cellWidth": cell_w,
        "cellHeight": cell_h,
        "frameCount": len(frames),
        "sourceFrames": [p.name for p in paths],
        "trimmed": trim,
    }
    out.with_suffix(".json").write_text(
        json.dumps(meta, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"[pack_sheet] {len(frames)} 帧 -> {out}  "
          f"{cols}x{rows} 格 单格={cell_w}x{cell_h} 总尺寸={sheet.width}x{sheet.height}")


def main() -> None:
    ap = argparse.ArgumentParser(description="序列帧 -> 游戏动作表")
    ap.add_argument("src", type=Path, help="帧目录")
    ap.add_argument("-o", "--out", type=Path, default=None)
    ap.add_argument("--cols", type=int, default=4)
    ap.add_argument("--rows", type=int, default=None,
                    help="不给则按帧数自动算")
    ap.add_argument("--cell", type=int, default=None,
                    help="单格像素；不给则保持原始帧尺寸")
    ap.add_argument("--trim", action="store_true",
                    help="按所有帧的 alpha 并集统一裁掉四周空白")
    args = ap.parse_args()

    out = args.out or Path("output/sheets") / f"{args.src.name}.png"
    build(args.src, out, args.cols, args.rows, args.cell, args.trim)


if __name__ == "__main__":
    main()
