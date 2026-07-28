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
                dq.append((y, x))
                visited[y, x] = True
    for y in range(h):
        for x in (0, w - 1):
            if near_bg[y, x] and not visited[y, x]:
                dq.append((y, x))
                visited[y, x] = True
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


def cutout_chroma(
    img: Image.Image, tolerance: int = 60, despill: bool = True
) -> Image.Image:
    """绿幕式抠图：按颜色全局判定，不看连通性。

    专配高饱和背景色（如 #FF00FF）。相比 flood-fill 的两个好处：
    封闭区域（弓弦内、把手环内）也能抠掉；深色物件不会因与背景明度接近被啃穿。
    tolerance 外再留一段过渡带做半透明软边，避免锯齿。
    """
    rgb = img.convert("RGB")
    # 必须 float32：三通道差的平方和最大 195075，int16 会溢出成负数，sqrt 出 NaN
    arr = np.asarray(rgb).astype(np.float32)
    bg = np.array(detect_bg_color(rgb), dtype=np.float32)
    dist = np.sqrt(((arr - bg) ** 2).sum(axis=2))

    soft = tolerance * 1.8  # 过渡带外沿：dist 超过它就是纯不透明
    alpha = np.clip((dist - tolerance) / max(soft - tolerance, 1e-6), 0, 1)
    out = arr.astype(np.uint8)

    if despill:
        # 去溢色：背景色主导通道若在边缘像素上偏高，压到另两通道的均值
        ch = int(np.argmax(bg))
        others = [i for i in range(3) if i != ch]
        edge = (alpha > 0) & (alpha < 1)
        cap = out[..., others].mean(axis=2)
        over = edge & (out[..., ch] > cap)
        out[..., ch] = np.where(over, cap, out[..., ch]).astype(np.uint8)

    rgba = np.dstack([out, (alpha * 255).astype(np.uint8)])
    return Image.fromarray(rgba, "RGBA")


def run(
    src_dir: str,
    out_dir: str,
    tolerance: int = 32,
    force_floodfill: bool = False,
    chroma: bool = False,
):
    imgs = list_images(src_dir)
    if not imgs:
        print(f"[cutout] 没找到图片: {src_dir}")
        return
    out = ensure_dir(out_dir)
    # chroma 显式指定时最优先：它是给高饱和背景（绿幕式）用的确定性算法，不该被 rembg 抢走
    use_rembg = (not chroma) and (not force_floodfill) and bool(_get_rembg())
    mode = (
        "chroma(绿幕式)"
        if chroma
        else ("rembg(AI)" if use_rembg else "floodfill(角落色)")
    )
    print(f"[cutout] 去背方式: {mode}  共 {len(imgs)} 张")

    for p in imgs:
        img = Image.open(p).convert("RGB")
        if chroma:
            res = cutout_chroma(img, tolerance if tolerance != 32 else 60)
        elif use_rembg:
            res = cutout_rembg(img)
        else:
            res = cutout_floodfill(img, tolerance)
        res.save(out / f"{p.stem}.png")
    print(f"[cutout] 输出: {out}")


def main() -> None:
    ap = argparse.ArgumentParser(description="批量去背为透明 PNG")
    ap.add_argument("src", help="待去背图片目录")
    ap.add_argument("-o", "--out", default="output/cutouts")
    ap.add_argument("--tolerance", type=int, default=32, help="flood-fill 容差")
    ap.add_argument(
        "--floodfill", action="store_true", help="强制用 flood-fill（跳过 rembg）"
    )
    ap.add_argument(
        "--chroma",
        action="store_true",
        help="绿幕式抠图（配 #FF00FF 等高饱和背景，容差默认 60）",
    )
    args = ap.parse_args()
    run(
        args.src,
        args.out,
        tolerance=args.tolerance,
        force_floodfill=args.floodfill,
        chroma=args.chroma,
    )


if __name__ == "__main__":
    main()
