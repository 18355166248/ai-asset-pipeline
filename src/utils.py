"""公共工具：背景色检测 / 内容包围盒 / 目录辅助。"""
from __future__ import annotations

from pathlib import Path
import numpy as np
from PIL import Image

IMG_EXTS = {".png", ".jpg", ".jpeg", ".webp", ".bmp"}


def list_images(folder: str | Path) -> list[Path]:
    folder = Path(folder)
    if not folder.exists():
        return []
    return sorted(p for p in folder.iterdir() if p.suffix.lower() in IMG_EXTS)


def ensure_dir(path: str | Path) -> Path:
    p = Path(path)
    p.mkdir(parents=True, exist_ok=True)
    return p


def detect_bg_color(img: Image.Image, sample: int = 8) -> tuple[int, int, int]:
    """采样四角小块，取中位数作为背景色。AI 网格图背景通常是纯色/近纯色。"""
    rgb = img.convert("RGB")
    arr = np.asarray(rgb)
    h, w = arr.shape[:2]
    s = min(sample, h // 2, w // 2)
    corners = np.concatenate([
        arr[:s, :s].reshape(-1, 3),
        arr[:s, -s:].reshape(-1, 3),
        arr[-s:, :s].reshape(-1, 3),
        arr[-s:, -s:].reshape(-1, 3),
    ])
    med = np.median(corners, axis=0)
    return tuple(int(v) for v in med)


def content_bbox(img: Image.Image, bg: tuple[int, int, int], thresh: int = 30,
                 pad: int = 2) -> tuple[int, int, int, int] | None:
    """返回与背景色差异大于 thresh 的内容包围盒 (l, t, r, b)，带 pad 外扩。"""
    arr = np.asarray(img.convert("RGB")).astype(np.int16)
    bg_arr = np.array(bg, dtype=np.int16)
    dist = np.abs(arr - bg_arr).max(axis=2)  # 每像素与背景的最大通道差
    mask = dist > thresh
    if not mask.any():
        return None
    ys, xs = np.where(mask)
    l, t, r, b = xs.min(), ys.min(), xs.max() + 1, ys.max() + 1
    h, w = mask.shape
    l = max(0, l - pad)
    t = max(0, t - pad)
    r = min(w, r + pad)
    b = min(h, b + pad)
    return int(l), int(t), int(r), int(b)


def pad_to_square(img: Image.Image, bg=(0, 0, 0, 0)) -> Image.Image:
    """把图贴到居中的正方形画布上（默认透明背景）。"""
    w, h = img.size
    side = max(w, h)
    mode = "RGBA" if img.mode == "RGBA" else "RGB"
    fill = bg if mode == "RGBA" else bg[:3]
    canvas = Image.new(mode, (side, side), fill)
    canvas.paste(img, ((side - w) // 2, (side - h) // 2),
                 img if img.mode == "RGBA" else None)
    return canvas
