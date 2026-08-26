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
- `--chroma` **绿幕式抠图**（配 `#FF00FF` 这类高饱和背景，见下）
- `--floodfill` 强制用角落色抠图（不用 rembg）
- `--tolerance N` 抠图容差（flood-fill 默认 32，chroma 默认 60）

### 三种抠图方式怎么选

| 方式 | 原理 | 失手的地方 |
|---|---|---|
| `--chroma` | 全局色距，不看连通性 | 背景色与素材撞色时；需要出图时就用高饱和背景 |
| 默认 rembg | AI 语义分割，猜「什么是主体」 | **猜错就是灾难**：实测一格法术书被整个吃掉，只剩一只眼睛 |
| `--floodfill` | 从四角向内扩散 | 深色物件遇深背景被啃穿；封闭区域（弓弦内）够不着 |

**结论：能控制出图背景色就用 `--chroma`**，它是确定性的，不会像 rembg 那样偶发地毁掉某一格。
rembg 只在背景已经脏了（渐变、投影）时才值得一试。

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

## Codex 生图接入规范

Codex 图片生成可以作为原始素材上游；本仓库仍是**唯一的确定性加工与验收出口**。
不接入任何特定付费生成 API，也不把生成器的输出直接发布到游戏。

完整的目录约定、元数据模板、验收闸门和发布规则见
[docs/CODEX_ASSET_WORKFLOW.md](docs/CODEX_ASSET_WORKFLOW.md)。新资产以
[assets-manifest.example.json](assets-manifest.example.json) 为台账模板：记录来源、
提示词、参考图、目标尺寸、验证报告和发布状态，避免后续只剩一张 PNG 而无法复现。
