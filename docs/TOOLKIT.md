# 视觉素材工具箱 v1

整套角色动作的二维/模型检查现可使用 [角色动作工作台](CHARACTER_WORKBENCH.md)，复用这里的 motion manifest，无需重做素材管线。

两个入口共用一套本地交付工具：`mascot-kit` 管吉祥物候选，`character-motion-kit` 管角色动作；`src/asset_bundle.py` 负责文件加工与交付。本工具不内置模型或密钥管理，也不调用付费生成 API。

## 运行

使用 Python 3.10+。只需核心依赖，不需要 rembg、Blender 或游戏引擎：

```bash
python3 -m venv .venv-toolkit
.venv-toolkit/bin/python -m pip install -r requirements-core.txt

# 不联网、不消耗模型额度的机械样例；几何图形不代表 AI 出图效果
.venv-toolkit/bin/python examples/make_demo.py --out output/toolkit-demo

# 工具行为回归
.venv-toolkit/bin/python -m unittest discover -s tests -v
```

也可使用已具备 Pillow、NumPy 的解释器。本工作区已有 `.venv-cutout/bin/python`，可直接复用，不需要重装依赖。切换工作目录后，pyenv 可能选择不同版本，运行前检查 `python3 -c 'import sys, PIL, numpy; print(sys.executable)'`。

直接打开样例下的 `mascot/preview.html` 与 `motion/preview.html`。页面内嵌本次素材，无网络依赖，不需要起服务；较大的图集会让 HTML 相应增大。支持深浅/棋盘背景、1×/2×/4×、动作选择、暂停、逐帧和播放速度。静态包还能切换导出尺寸。

## 静态包

复制 `recipes/mascot.json` 并填写来源，input 接受单图或一个图片目录（不递归）：

```bash
python3 src/asset_bundle.py --recipe recipes/mascot.json \
  --input input/my-mascots --out output/my-mascots-v1
```

`sizes` 是方形输出画布边长；保留原图比例，不裁切，居中补透明边。默认保留已有设计背景。确需去纯色背景时设 `background: "chroma"`、`tolerance: 60`，调用现有色键算法；深浅复杂背景先用合适的上游去背工具，不能把 chroma 当通用语义分割。`resample` 支持 `lanczos` 和 `nearest`。PNG/JPEG/WebP/BMP 可作静态输入，动画文件会被拒绝，避免静默只取第一帧。

这是 PNG 尺寸包，不是 SVG、ICO 或某个平台完整的 App Icon 工程。

## 动作包

输入目录示例：

```text
hero/
├── idle/frame-1.png ... frame-4.png
└── attack/frame-1.png ... frame-6.png
```

复制 `recipes/character.json`，调整 `states`、`cell`、`anchor`、来源记录：

```bash
python3 src/asset_bundle.py --recipe recipes/character.json \
  --input input/hero --out output/hero-v1
```

- `states` 的顺序就是图集行序；`directory` 相对于输入目录，默认等于动作名。
- 文件按自然数字顺序读取：frame-1、frame-2、frame-10。不要混入其他图片。
- 所有动作源画布必须同尺寸；工具对整张画布应用同一个缩放/居中变换，不逐帧裁主体。输入本身的漂移仍需人工检查。
- 每动作显式声明 `loop`；目录输入用 `fps` 计算整数毫秒时长（四舍五入），输出以实际 `durationMs` 为准。
- `anchor` 为左上原点归一化坐标，仅记录，不推断脚掌位置；其他引擎需要自行转换坐标原点。
- 输出矩形为空或缺少透明背景时拒绝打包；触边、只有一个不同姿态是警告，不自动修正或生成新帧。

## sprite-gen 输入适配

v1 对接的是 **Aseprite 导出格式**，没有复制 sprite-gen 的生成算法。上游按其安装版本文档运行 compose 和 `export-aseprite`。导出可能位于 `exports/aseprite.json`，而 PNG 在 run 根目录；将最终 JSON 与它引用的 PNG 复制到独立输入目录，使 `meta.image` 在该目录内正确解析。不要直接拷贝 `frames/` 中间缓存，否则可能遗漏选帧、像素修正和变换。

```bash
python3 src/asset_bundle.py --recipe recipes/character.json \
  --input input/hero-final/aseprite.json --aseprite --out output/hero-import-v1
```

接受 `frames` 数组或从 0 连续编号的 hash、`meta.frameTags` 的 forward 标签、完整且未旋转的帧。拒绝 trim、reverse、pingpong、越界矩形与越过输入目录的图片路径。配方列出的动作必须存在；未列出的动作不导出。保留重复矩形与每帧毫秒时长；配方 fps 不覆盖导入时长，loop 仍由配方声明。

已按公开格式编写往返测试；尚未运行真实 sprite-gen 生成或验证所有上游版本。接真实产物时先检验格式；不支持的版本直接报错，不猜测恢复。

参考：[sprite-gen](https://github.com/aldegad/sprite-gen)、[导出契约](https://github.com/aldegad/sprite-gen/blob/main/docs/engine-export.md)、[最终产物与中间缓存](https://github.com/aldegad/sprite-gen/blob/main/docs/run-contract.md)。这些是格式参考，没有将上游源代码并入本仓库。

## 每个包的内容

| 文件 | 用途 |
| --- | --- |
| `preview.html` | 独立离线预览，可对比静态尺寸和播放动作 |
| `manifest.json` | 文件清单、绝对帧矩形、逐帧时长、loop、锚点语义、草稿状态 |
| `report.json` | alpha / bbox 测量、警告和待人工检查项目 |
| `provenance.json` | 配方快照、输入绝对路径与 SHA-256、工具及 Pillow 版本 |
| `images/<size>/` | 静态包多尺寸 PNG；原文件名记录在 manifest |
| `atlas.png` / `frames/<state>/` | 动作图集与规范化透明帧 |
| `aseprite.json` | 带帧时长和标签的 Aseprite 兼容 JSON；loop 以 manifest 为准 |
| `grid.json` | 固定网格尺寸、行序与真实帧数；不是 Cocos 导入插件 |
| `contact-<state>.png` | 逐动作联络表 |

较短动作在图集中重复末帧补齐；真实播放序列没有添加补齐帧。固定列数消费者不能忽略 `frameCounts` 和原始时间语义。不会生成命中点或碰撞体。

来源哈希用于确认输入，不能保证模型重新生成同一张图。工具不复制原始素材或提示词附件，长期复现需按资产台账保存原件。预览页包含素材与 source 描述；分享前确认其中内容适合分享。

输出必须是新的目录；失败清理临时产物，不覆盖旧批次。包永远从 draft 开始，浏览器通过不能自动变成正式资产；游戏侧仍按 `CODEX_ASSET_WORKFLOW.md` 入库与验收。已有视频参考限制保持生效。

## Skill 安装与跨项目调用

Skill 源文件维护在本仓库的 `skills/`，不要复制多份修改。可通过软链安装到个人 Codex skills 目录（本机路径示例）：

```bash
ln -s /Users/xmly/Swell/code/game-workspace/ai-asset-pipeline/skills/mascot-kit ~/.codex/skills/mascot-kit
ln -s /Users/xmly/Swell/code/game-workspace/ai-asset-pipeline/skills/character-motion-kit ~/.codex/skills/character-motion-kit
```

已有同名目录时先检查，不使用 `ln -sf` 覆盖。换电脑克隆仓库后按实际位置重建链接。Skill 解析真实路径定位仓库，可在游戏或日常项目中使用。

- “用 `$mascot-kit` 给这个小工具做吉祥物候选，输出头像尺寸包。”
- “用 `$character-motion-kit` 整理这个角色的待机和攻击素材，并打开预览。”

## 第一版验证边界

自动回归覆盖 alpha 保真、自然帧排序、画布一致性、时长/loop 保留、最终导出往返、无效输入拒绝、输出隔离与 HTML 数据转义。几何样例只验证加工与预览，不代表生成质量。真实模型生成、玩家感受、Cocos/Phaser 真正导入与游戏运行仍需各自试点记录。
