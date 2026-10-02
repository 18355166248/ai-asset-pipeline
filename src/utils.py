"""公共工具：背景色检测 / 内容包围盒 / 目录辅助。"""
from __future__ import annotations

from pathlib import Path
import re
import numpy as np
from PIL import Image

IMG_EXTS = {".png", ".jpg", ".jpeg", ".webp", ".bmp"}


def natural_key(path: Path):
    """按数字帧号排序，避免 frame-10 排在 frame-2 之前。"""
    return [int(part) if part.isdigit() else part.lower()
            for part in re.split(r"(\d+)", path.name)]


def list_images(folder: str | Path) -> list[Path]:
    folder = Path(folder)
    if not folder.is_dir():
        return []
    return sorted((p for p in folder.iterdir()
                   if p.is_file() and p.suffix.lower() in IMG_EXTS), key=natural_key)


def ensure_dir(path: str | Path) -> Path:
    p = Path(path)
    p.mkdir(parents=True, exist_ok=True)
    return p


def detect_bg_color(img: Image.Image, sample: int = 8) -> tuple[int, int, int]:
    """采样四角小块，取中位数作为背景色。AI 网格图背景通常是纯色/近纯色。"""
    rgb = img.convert("RGB")
    arr = np.asarray(rgb)
    h, w = arr.shape[:2]
    if sample < 1:
        raise ValueError("背景采样尺寸必须大于 0")
    s = max(1, min(sample, h // 2, w // 2))
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
    left, top, right, bottom = xs.min(), ys.min(), xs.max() + 1, ys.max() + 1
    h, w = mask.shape
    left = max(0, left - pad)
    top = max(0, top - pad)
    right = min(w, right + pad)
    bottom = min(h, bottom + pad)
    return int(left), int(top), int(right), int(bottom)


def pad_to_square(img: Image.Image, bg=(0, 0, 0, 0)) -> Image.Image:
    """把图贴到居中的正方形画布上（默认透明背景）。"""
    w, h = img.size
    side = max(w, h)
    mode = "RGBA" if img.mode == "RGBA" else "RGB"
    fill = bg if mode == "RGBA" else bg[:3]
    canvas = Image.new(mode, (side, side), fill)
    # 透明画布直接复制 RGBA；再传 alpha mask 会让半透明边缘被重复衰减。
    canvas.paste(img, ((side - w) // 2, (side - h) // 2))
    return canvas


def thumbnail_square(img: Image.Image, size: int) -> Image.Image:
    """等比缩小并居中到透明方格；保留旧入口不放大小图的约定。"""
    if size < 1:
        raise ValueError("目标尺寸必须大于 0")
    scaled = img.convert("RGBA")
    scaled.thumbnail((size, size), Image.Resampling.LANCZOS)
    canvas = Image.new("RGBA", (size, size))
    canvas.paste(scaled, ((size - scaled.width) // 2, (size - scaled.height) // 2))
    return canvas
