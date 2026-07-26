# ai-asset-pipeline

验证「网页版 GPT / Gemini 出图能否当稳定游戏素材管线」的本地后处理工具。

**分工**：生成靠你在网页手工做（6×6 一次性出图保证一致性）；本地这套负责
**切图 → 去背 → 缩放 → 质检**，把「凭感觉」变成可重复流程。

## 安装

```bash
python -m pip install -r requirements.txt
# 想要更好的 AI 去背，再装（可选，不装会自动降级）：
python -m pip install rembg onnxruntime
```

## 用法

一条命令跑完整链路：

```bash
python src/run.py input/grid.png -r 6 -c 6 --size 96 --autocrop
```

产物在 `output/<网格图名>/`：

| 目录 / 文件 | 内容 |
|---|---|
| `slices/` | 等分切出的 36 张 |
| `cutouts/` | 去背后的透明 PNG |
| `resized/` | 缩到游戏尺寸 |
| `contact_cutouts.png` | **先看这张**：一眼检查去背 + 风格一致性 |
| `contact_resized.png` | 游戏尺寸下的可读性检查 |

### 常用参数

- `--autocrop` 每格按内容自动裁掉多余背景（item 大小不一时用）
- `--gutter N` 每格四边内缩 N 像素，防切到相邻格描边
- `--size N` 游戏内目标长边像素（默认 96）
- `--square` 缩放后补成正方形画布
- `--floodfill` 强制用角落色抠图（不用 rembg）
- `--tolerance N` flood-fill 容差（背景不够纯时调大）

### 单步单独跑

```bash
python src/slice_grid.py input/grid.png -r 6 -c 6 --autocrop
python src/cutout.py     output/slices -o output/cutouts
python src/resize.py     output/cutouts --size 96
python src/contact.py    output/cutouts -o output/contact/sheet.png
```

## 验证协议（配合本工具）

1. **实验 A · 一致性**：同一提示词生 3 张 6×6，各自跑一遍，比 3 张 `contact_cutouts.png`。
2. **实验 B · 补图漂移**：隔天用「参考图 + 补 1 个新物件」出图，对比是否对得上原风格。
3. **实验 C · 尺寸+去背**：看 `contact_resized.png`，把 `resized/` 贴进大鹅工程网格跑一眼。

任一实验的一致性/去背/可读性不过关，说明 AI 生图暂不能当主力素材管线。
