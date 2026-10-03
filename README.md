# ai-asset-pipeline

## 本地前端

Vite + React + React Router + shadcn/ui + Jotai。

```bash
npm ci --prefix workbench --ignore-scripts
npm run dev --prefix workbench
```

打开 http://127.0.0.1:8770/pipeline（九步引导）或 /motion（真实时序与修复候选）。构建、数据切换与清理范围见 [前端指南](docs/FRONTEND.md)。

## 基于 GPT 制作二维角色动作

从 [使用入口与所需素材](docs/CHARACTER_MOTION_QUICKSTART.md) 开始：准备完整角色参考、动作/朝向、尺寸/锚点和时长，在 Codex 调用 `$character-motion-kit`，交付试玩与通用二维素材包。当前工具留在此项目供多个游戏复用。

`character-motion-kit` 已增加逐帧生成任务：准备角色参考与姿态草图，实际调用 Codex 内置 GPT 生图，导入真实帧、局部修正、记录审查，再导出透明帧和动作图集。任务可续做，失败版本保留。当前不需要另配 API key；Python 负责材料和导出，真正生图由 Skill 调用宿主工具。

所需素材、命令及自定义攻击等动作规格见 [GPT 动作制作指南](docs/GPT_MOTION_GENERATION.md)。`src/motion_generation.py` 提供 prepare / import / review / inspect / status / pack；配套八帧真实步行试点仍处于视觉验收阶段。

现有二维包可用 `src/godot_sprite_export.py --manifest <manifest.json> --out <新目录>` 导出 Godot SpriteFrames 与独立预览项目。保留真实帧时长、循环和脚底锚点；游戏物理与动作切换由消费端接入。[原生资源验证](docs/validation/godot-sprite-export-v1.md)已通过，原画仍为待验收草稿。

## 角色整体动作工作台

默认以二维角色图集为主；GLB/部件模型检查为可选功能，不要求二维游戏转换为三维。

统一检查二维动作包、双足/四足部件模型和已有动画的 GLB：整套动作巡演、逐帧、模型过渡、缺项报告与来源记录。使用现有素材链路，不依赖消费游戏。用法、五个参考帖子的评估和边界见 [工作台指南](docs/CHARACTER_WORKBENCH.md)。

```bash
npm ci --prefix workbench
.venv-cutout/bin/python examples/make_workbench.py --out output/character-workbench
.venv-cutout/bin/python -m http.server 8771 --bind 127.0.0.1 --directory output/character-workbench/viewer
```

此处是可导出的离线预览示例，打开 `http://127.0.0.1:8771/`；模型需要自带动作，首版不自动绑骨或重定向。

## 可复用素材工具箱

新增两个 Skill 入口：`mascot-kit`（吉祥物与图标）、`character-motion-kit`（角色动作）。
共用本地配方工具，输出多尺寸 PNG 或动作图集、离线交互预览、检查报告及来源记录。
日常项目也可使用；不依赖游戏引擎。完整用法与输入格式见 [工具箱指南](docs/TOOLKIT.md)。

```bash
# 本工作区可复用已有虚拟环境；其他机器按工具箱指南安装核心依赖
.venv-cutout/bin/python examples/make_demo.py --out output/toolkit-demo
```

打开 `output/toolkit-demo/mascot/preview.html` 或 `motion/preview.html` 体验。
样例是机械验证用几何图形，不消耗模型额度，不代表 AI 生成效果。

## 原有素材后处理流程

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

## sprite-gen 动作工作层

固定版本接入、精确时序、隔离候选和人工验收门禁见 [接入说明](docs/SPRITE_GEN_INTEGRATION.md)。当前完成现有素材导入试点，未验证目标角色的真实生成成功率。
