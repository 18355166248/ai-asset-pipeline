"""批量去背 -> 透明 PNG。

优先用 rembg（AI 抠图，效果好）；未安装则降级到「角落色 flood-fill」。

用法:
  python src/cutout.py output/slices -o output/cutouts
  python src/cutout.py output/slices --tolerance 40      # flood-fill 容差
"""
from __future__ import annotations

import argparse
from pathlib import Path
import numpy as np
from PIL import Image

from utils import list_images, ensure_dir, detect_bg_color

_REMBG = None


def _get_rembg():
    global _REMBG
    if _REMBG is None:
        try:
            from rembg import remove, new_session
            _REMBG = (remove, new_session("u2net"))
        except Exception:
            _REMBG = False
    return _REMBG


def cutout_rembg(img: Image.Image) -> Image.Image:
    remove, session = _get_rembg()
    return remove(img, session=session).convert("RGBA")


def cutout_floodfill(img: Image.Image, tolerance: int = 32) -> Image.Image:
    """从四角向内扩散，把连通的近背景色像素设为透明。纯色背景下够用。"""
    rgb = img.convert("RGB")
    arr = np.asarray(rgb)
    h, w = arr.shape[:2]
    bg = np.array(detect_bg_color(rgb), dtype=np.int16)
    dist = np.abs(arr.astype(np.int16) - bg).max(axis=2)
    near_bg = dist <= tolerance

    # BFS 从四条边的近背景像素扩散，只删与边相连的背景（保留物件内部同色区域）
    visited = np.zeros((h, w), dtype=bool)
    from collections import deque
    dq: deque[tuple[int, int]] = deque()
    for x in range(w):
        for y in (0, h - 1):
            if near_bg[y, x]:
                dq.append((y, x)); visited[y, x] = True
    for y in range(h):
        for x in (0, w - 1):
            if near_bg[y, x] and not visited[y, x]:
                dq.append((y, x)); visited[y, x] = True
    while dq:
        y, x = dq.popleft()
        for dy, dx in ((1, 0), (-1, 0), (0, 1), (0, -1)):
            ny, nx = y + dy, x + dx
            if 0 <= ny < h and 0 <= nx < w and not visited[ny, nx] and near_bg[ny, nx]:
                visited[ny, nx] = True
                dq.append((ny, nx))

    rgba = np.dstack([arr, np.full((h, w), 255, dtype=np.uint8)])
    rgba[visited, 3] = 0
    return Image.fromarray(rgba, "RGBA")


def run(src_dir: str, out_dir: str, tolerance: int = 32, force_floodfill: bool = False):
    imgs = list_images(src_dir)
    if not imgs:
        print(f"[cutout] 没找到图片: {src_dir}")
        return
    out = ensure_dir(out_dir)
    use_rembg = (not force_floodfill) and bool(_get_rembg())
    mode = "rembg(AI)" if use_rembg else "floodfill(角落色)"
    print(f"[cutout] 去背方式: {mode}  共 {len(imgs)} 张")

    for p in imgs:
        img = Image.open(p).convert("RGB")
        res = cutout_rembg(img) if use_rembg else cutout_floodfill(img, tolerance)
        res.save(out / f"{p.stem}.png")
    print(f"[cutout] 输出: {out}")


def main() -> None:
    ap = argparse.ArgumentParser(description="批量去背为透明 PNG")
    ap.add_argument("src", help="待去背图片目录")
    ap.add_argument("-o", "--out", default="output/cutouts")
    ap.add_argument("--tolerance", type=int, default=32, help="flood-fill 容差")
    ap.add_argument("--floodfill", action="store_true", help="强制用 flood-fill（跳过 rembg）")
    args = ap.parse_args()
    run(args.src, args.out, tolerance=args.tolerance, force_floodfill=args.floodfill)


if __name__ == "__main__":
    main()
