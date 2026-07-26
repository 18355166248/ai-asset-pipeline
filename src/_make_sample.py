"""生成一张假的 6x6 网格图用于自测（无需真的 AI 出图）。"""
from PIL import Image, ImageDraw
import random
from pathlib import Path

random.seed(7)
CELL, ROWS, COLS = 200, 6, 6
BG = (235, 232, 225)  # 近纯色背景，模拟 AI 网格底
img = Image.new("RGB", (CELL * COLS, CELL * ROWS), BG)
d = ImageDraw.Draw(img)

for r in range(ROWS):
    for c in range(COLS):
        cx, cy = c * CELL + CELL // 2, r * CELL + CELL // 2
        rad = random.randint(45, 75)
        col = (random.randint(40, 220), random.randint(40, 220), random.randint(40, 220))
        shape = (r * COLS + c) % 3
        if shape == 0:
            d.ellipse([cx - rad, cy - rad, cx + rad, cy + rad], fill=col)
        elif shape == 1:
            d.rectangle([cx - rad, cy - rad, cx + rad, cy + rad], fill=col)
        else:
            d.polygon([(cx, cy - rad), (cx - rad, cy + rad), (cx + rad, cy + rad)], fill=col)

out = Path("input/sample_grid.png")
out.parent.mkdir(exist_ok=True)
img.save(out)
print(f"sample -> {out.resolve()}")
