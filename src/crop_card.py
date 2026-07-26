"""卡面后处理：裁到统一 3:4 + 安全区校验 + 输出游戏可用尺寸。

卡框会在代码里叠加，盖住外 8%。所以主体（脸、标志）必须留在中央安全区内，
否则上框后会被切掉。本脚本自动检测并报警。

用法:
  python src/crop_card.py cards_raw -o output/cards
  python src/crop_card.py cards_raw --size 768x1024 --safe 8
  python src/crop_card.py cards_raw --preview        # 额外输出带安全区标线的校验图
"""
from __future__ import annotations

import argparse
from pathlib import Path
import numpy as np
from PIL import Image, ImageDraw

from utils import list_images, ensure_dir


def crop_to_ratio(img: Image.Image, ratio: float) -> Image.Image:
    """居中裁到目标宽高比（ratio = w/h）。只裁不拉伸。"""
    w, h = img.size
    cur = w / h
    if abs(cur - ratio) < 1e-3:
        return img
    if cur > ratio:          # 太宽，裁左右
        new_w = round(h * ratio)
        off = (w - new_w) // 2
        return img.crop((off, 0, off + new_w, h))
    new_h = round(w / ratio)  # 太高，裁上下
    off = (h - new_h) // 2
    return img.crop((0, off, w, off + new_h))


def subject_bbox(img: Image.Image, thresh: int = 18) -> tuple[int, int, int, int] | None:
    """粗估主体范围：找与四角背景色差异大的像素。用于安全区校验。"""
    rgb = np.asarray(img.convert("RGB")).astype(np.int16)
    h, w = rgb.shape[:2]
    s = max(4, min(h, w) // 40)
    corners = np.concatenate([
        rgb[:s, :s].reshape(-1, 3), rgb[:s, -s:].reshape(-1, 3),
        rgb[-s:, :s].reshape(-1, 3), rgb[-s:, -s:].reshape(-1, 3),
    ])
    bg = np.median(corners, axis=0)
    mask = np.abs(rgb - bg).max(axis=2) > thresh
    if not mask.any():
        return None
    ys, xs = np.where(mask)
    return int(xs.min()), int(ys.min()), int(xs.max()) + 1, int(ys.max()) + 1


def check_safe(img: Image.Image, safe_pct: float) -> tuple[bool, str]:
    """主体是否越过安全区（外 safe_pct% 会被卡框盖住）。"""
    w, h = img.size
    mx, my = w * safe_pct / 100, h * safe_pct / 100
    bbox = subject_bbox(img)
    if bbox is None:
        return True, "主体检测失败（可能满幅出血），跳过校验"
    l, t, r, b = bbox
    bad = []
    if l < mx: bad.append(f"左({l}<{mx:.0f})")
    if t < my: bad.append(f"上({t}<{my:.0f})")
    if r > w - mx: bad.append(f"右({r}>{w - mx:.0f})")
    if b > h - my: bad.append(f"下({b}>{h - my:.0f})")
    # 满幅出血的卡面主体本就顶边，这里只在「四边都越界」时视为正常
    if len(bad) == 4:
        return True, "四边均满幅（出血构图），跳过"
    return (not bad), ("越界: " + " ".join(bad) if bad else "安全区 OK")


def draw_preview(img: Image.Image, safe_pct: float) -> Image.Image:
    """输出带安全区标线的校验图：红框内为安全区，框外会被卡框盖掉。"""
    prev = img.convert("RGB").copy()
    d = ImageDraw.Draw(prev, "RGBA")
    w, h = prev.size
    mx, my = w * safe_pct / 100, h * safe_pct / 100
    d.rectangle([0, 0, w, my], fill=(255, 0, 0, 70))
    d.rectangle([0, h - my, w, h], fill=(255, 0, 0, 70))
    d.rectangle([0, my, mx, h - my], fill=(255, 0, 0, 70))
    d.rectangle([w - mx, my, w, h - my], fill=(255, 0, 0, 70))
    d.rectangle([mx, my, w - mx, h - my], outline=(0, 255, 0, 255), width=3)
    bbox = subject_bbox(img)
    if bbox:
        d.rectangle(list(bbox), outline=(0, 128, 255, 255), width=2)
    return prev


def run(src_dir: str, out_dir: str, size: tuple[int, int], safe_pct: float,
        preview: bool):
    imgs = list_images(src_dir)
    if not imgs:
        print(f"[crop] 没找到图片: {src_dir}")
        return
    out = ensure_dir(out_dir)
    prev_dir = ensure_dir(Path(out_dir) / "_safecheck") if preview else None
    tw, th = size
    ratio = tw / th
    warned = []

    for p in imgs:
        img = Image.open(p).convert("RGB")
        img = crop_to_ratio(img, ratio)
        img = img.resize((tw, th), Image.LANCZOS)
        ok, msg = check_safe(img, safe_pct)
        flag = "OK  " if ok else "WARN"
        print(f"[{flag}] {p.name:32} {msg}")
        if not ok:
            warned.append(p.name)
        img.save(out / f"{p.stem}.png")
        if prev_dir:
            draw_preview(img, safe_pct).save(prev_dir / f"{p.stem}_safe.png")

    print(f"\n[crop] {len(imgs)} 张 -> {tw}x{th}  输出: {out}")
    if warned:
        print(f"[crop] ⚠ {len(warned)} 张主体越过安全区，上卡框会被切:")
        for n in warned:
            print(f"        - {n}")
        if prev_dir:
            print(f"        对照 {prev_dir} 里的标线图确认")
    else:
        print("[crop] 全部通过安全区校验")


def parse_size(s: str) -> tuple[int, int]:
    w, _, h = s.lower().partition("x")
    return int(w), int(h)


def main() -> None:
    ap = argparse.ArgumentParser(description="卡面裁切 + 安全区校验")
    ap.add_argument("src", help="卡面原图目录")
    ap.add_argument("-o", "--out", default="output/cards")
    ap.add_argument("--size", default="768x1024", help="目标尺寸，默认 768x1024 (3:4)")
    ap.add_argument("--safe", type=float, default=8.0, help="安全区边距百分比，默认 8")
    ap.add_argument("--preview", action="store_true", help="额外输出带安全区标线的校验图")
    args = ap.parse_args()
    run(args.src, args.out, parse_size(args.size), args.safe, args.preview)


if __name__ == "__main__":
    main()
