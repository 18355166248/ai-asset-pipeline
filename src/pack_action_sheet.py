"""把多个动作拼成引擎用的「一行一动作」动作表。

和 pack_sheet.py 的区别：那个把**一个**动作的帧铺成网格；
这个把**多个**动作按行叠起来，每行一个动作——这是游戏引擎常见的排布。

xianxia-roguelike 的 PlayerAnimationRuntime 就是这么读的：
row 0=idle、1=move、2=slash、3=hit，每行 4 帧，按 (row, column) 取格。
行序错了不会报错，只会让角色在待机时播受击动作。

各行帧数不足时**重复末帧补齐**，不是留空：留空会让引擎取到全透明格，
表现为动作播到一半人不见了。

用法:
  python src/pack_action_sheet.py \
      --rows idle=output/frames/hero_idle move=output/frames/hero_move \
             slash=output/frames/hero_slash hit=output/frames/hero_hit \
      -o output/sheets/qinglan-actions.png --cols 4 --cell 96
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from PIL import Image

from utils import list_images, ensure_dir

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")


def sample_row(paths: list[Path], cols: int) -> list[Path]:
    """把一个动作的帧均匀采样/补齐到 cols 张。"""
    if not paths:
        raise SystemExit("空的动作目录")
    if len(paths) == cols:
        return paths
    if len(paths) > cols:
        # 均匀取样，保留动作的时间分布（快的部分自然被压缩）。
        return [paths[round(i * (len(paths) - 1) / (cols - 1))] for i in range(cols)]
    # 帧不够就重复末帧补齐，不留空格。
    return paths + [paths[-1]] * (cols - len(paths))


def build(rows: list[tuple[str, Path]], out: Path, cols: int,
          cell: int | None) -> None:
    cells: list[list[Image.Image]] = []
    report: list[dict] = []

    for name, directory in rows:
        paths = [p for p in list_images(directory) if p.suffix.lower() == ".png"]
        chosen = sample_row(paths, cols)
        images = [Image.open(p).convert("RGBA") for p in chosen]
        cells.append(images)
        report.append({"clip": name, "sourceDir": str(directory),
                       "available": len(paths), "used": len(chosen)})

    sizes = {img.size for row in cells for img in row}
    if len(sizes) != 1:
        raise SystemExit(
            f"各动作的帧尺寸不一致，无法等分打包: {sorted(sizes)}。"
            f"整套动作要用 render_clip_set.py 渲，才会共用同一套归一化。")

    if cell:
        resized = []
        for row in cells:
            packed = []
            for img in row:
                scaled = img.copy()
                scaled.thumbnail((cell, cell), Image.LANCZOS)
                canvas = Image.new("RGBA", (cell, cell), (0, 0, 0, 0))
                canvas.paste(scaled, ((cell - scaled.width) // 2,
                                      (cell - scaled.height) // 2), scaled)
                packed.append(canvas)
            resized.append(packed)
        cells = resized

    cell_w, cell_h = cells[0][0].size
    sheet = Image.new("RGBA", (cols * cell_w, len(cells) * cell_h), (0, 0, 0, 0))
    for r, row in enumerate(cells):
        for c, img in enumerate(row):
            sheet.paste(img, (c * cell_w, r * cell_h), img)

    ensure_dir(out.parent)
    sheet.save(out)
    out.with_suffix(".json").write_text(json.dumps({
        "sheet": out.name,
        "columns": cols,
        "rows": len(cells),
        "cellWidth": cell_w,
        "cellHeight": cell_h,
        "rowOrder": [r["clip"] for r in report],
        "detail": report,
    }, ensure_ascii=False, indent=2), encoding="utf-8")

    print(f"[pack_action_sheet] {len(cells)}x{cols} 格 单格={cell_w}x{cell_h} "
          f"总尺寸={sheet.width}x{sheet.height} -> {out}")
    for index, item in enumerate(report):
        note = "" if item["available"] >= cols else f"（只有 {item['available']} 帧，重复末帧补齐）"
        print(f"    row {index} = {item['clip']}{note}")


def main() -> None:
    ap = argparse.ArgumentParser(description="多动作 -> 一行一动作的动作表")
    ap.add_argument("--rows", nargs="+", required=True,
                    help="按行序给出 名字=帧目录")
    ap.add_argument("-o", "--out", type=Path, required=True)
    ap.add_argument("--cols", type=int, default=4)
    ap.add_argument("--cell", type=int, default=None)
    args = ap.parse_args()

    rows = []
    for spec in args.rows:
        if "=" not in spec:
            raise SystemExit(f"行格式应为 名字=目录，收到 {spec}")
        name, directory = spec.split("=", 1)
        rows.append((name, Path(directory)))

    build(rows, args.out, args.cols, args.cell)


if __name__ == "__main__":
    main()
