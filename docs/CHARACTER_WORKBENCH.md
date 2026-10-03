# 角色整体动作工作台

2026-10-02。结论：扩展已有独立仓库 `ai-asset-pipeline`，把工具、上游生成服务和游戏消费端分开。首版已经实现本地工作台，游戏继续持有战斗时间、碰撞和取消窗口。

主线是二维角色：参考图 → 同角色动作帧 → 透明 PNG → 图集/时长/锚点 → 游戏。默认示例和首屏均为二维；无需 GLB、绑骨或 WebGL。模型检查作为可选功能保留，仅在选择模型时加载三维库。

## 最新八方向参考与二次元样片

新增 [Sprite-gen + Grok 帖子](https://x.com/aldegadwildkim/status/2105936385937195463?s=46)的视频实际可以播放。约 9 秒的展示里同时有八个朝向，侧面步态、身体起伏和头发摆动连续；这不是逐帧测量或全套游戏动作验收。正文没有公开该视频的帧率和导出参数。

作者的[官方管线](https://github.com/aldegad/sprite-gen/blob/main/docs/video-pipeline.md)将静态角色图交给 Grok 生成连续运动，再去背和选择完整周期。不能把“GPT 生八个姿势然后切图”视为等价实现。

本次已用内置 imagegen 生成可爱二次元参考图和两版八帧步行。两版均未可靠完成左右脚交替，保留为拒绝候选；没有发布到游戏。见[提示词与结论](../input/codex/mint-adventurer-motion-v1/notes.md)。早期专用展示脚本已退役，比较预览统一使用 `src/motion_compare.py`。工作台 `reviewNotes` 字段把人工失败原因带到页面，防止结构检查通过掩盖动作问题。

该历史样片保存在 `output/mint-adventurer-pilot-v1/viewer`；当前本地8770入口是React流水线，见 [前端指南](FRONTEND.md)。连续视频生成入口尚未接入。

## 五个帖子能带来什么

本次读到了五帖原文、可见回复及关联的官方项目资料；X 视频在浏览器内无法播放，因此以下判断不以视频视觉效果作为实测证明。

| 来源 | 读到的能力 | 可以抽离的功能 | 不能据此推断的能力 |
|---|---|---|---|
| [Kiki / Mayz](https://x.com/mayz1169/status/2103139749540339890) | GPT Image 2.5 的 16 格姿态板，接 Grok 做舞蹈；回复给出逐格时序 | 同一角色姿态分镜、动作意图和参考图管理 | 视频天然能控制游戏命中，或已输出骨架 |
| [Ryan](https://x.com/7998l201/status/2105843660340560056) | Muse 的九个同模特姿态，沿成功快照续生成 | 身份约束、批次记录、上游会话恢复信息 | 九个姿态是连续动画；其快照参数适用于其他服务 |
| [Itachi](https://x.com/itachi_ai_/status/2105490806379561071) | Grok 制作的编号姿态参考图 | 动作参考与人工验收清单 | 图片就是可编辑 3D 模型或骨架文件 |
| [Aldegad](https://x.com/aldegadwildkim/status/2105728101447876959) / [sprite-gen](https://github.com/aldegad/sprite-gen) | 帖子讨论 2.15.0 正面步行；当前仓库有生成、透明处理、方向检查、选帧、compose 与引擎导出 | 复用上游生产，不重写整套生成器；接其最终 Aseprite 导出 | 所有角色、方向都会成功；当前 main 的所有能力都属于 2.15.0 |
| [Emmanuel](https://x.com/emmanuel_2m/status/2105256136006095205) / [Scenario Iso Cycles](https://www.scenario.com/explorations/iso-cycles/) | 等距角色八方向、四动作、每动作八帧的演示与制作过程 | 角色×动作×方向矩阵、首尾约束、循环选段、统一画布 | 可以对任意模型自动绑骨，或可以不验收直接替换游戏角色 |

Scenario 的制作说明包含固定方向参考、原地运动、攻击回到准备姿态，以及接缝差异与相邻帧运动量的相对评分。五个方向生成、三个方向镜像能减少任务量，但非对称武器、服饰不能默认翻转。sprite-gen 的方向记录/检查也不等于生成结果始终正确。这些是生产流程的参考，首版没有调用两家的生成服务。

## 项目和工具边界

建议抽成六项能力，共用一份角色配置，而不是做六个独立项目：

1. **角色身份与来源**：参考图、比例、服饰、武器、方向、输入哈希。首版保存配置与来源；身份是否一致仍由人检查。
2. **动作需求矩阵**：哪些动作/方向已有，哪些是借用姿态，哪些缺失。首版生成缺项报告与待生成提示词。
3. **上游生成适配**：sprite-gen、Scenario 或宿主生图工具。现有二维 Aseprite 适配继续复用；本次没有安装 sprite-gen，也没有配置 Scenario 账号或消耗生成额度。
4. **素材加工交付**：透明帧、统一画布、图集、逐帧时长。现有 `asset_bundle.py` 已有这条链路。
5. **整体动作检查**：二维、部件模型、GLB 的整套播放、逐帧、切换、模型过渡、巡演。此次新增的工作台负责这一项。
6. **游戏接入与验收**：引擎动作名映射、锚点、战斗时序、场景实测。保留在各消费项目，先以 Frontier 为试点。

`ai-asset-pipeline` 已是独立 Git 仓库，既有素材加工和动作库，也有已安装的 Skill 入口。继续扩展能复用现有数据，避免每个游戏复制一套工具。若以后做多人在线任务、账号和队列，再考虑独立服务；当前本地工具不需要新服务项目。

**Skill 是使用流程，CLI 是可重复执行的工具，工作台是可查看的结果，上游服务负责生成。** 三者可以共存。此次沿用 `character-motion-kit`，增加工作台入口，没有再安装一个名称相近的 Skill。

## 首版已实现

| 输入 | 支持 | 限制 |
|---|---|---|
| `asset_bundle` motion manifest | 原画播放、精确逐帧时长、循环/单次、锚点、缺动作提示 | 每动作统一画布；每个输入声明一个方向；不补帧或图像交叉淡入 |
| `animation-library` | 双足 8 动作、四足 4 动作；全身部件层级、保形插值、周期接缝、四元数过渡 | 当前为盒子部件枢轴模型，不是蒙皮骨骼；Z 向上；插值与 Blender 贝塞尔不完全相同 |
| 自包含 GLB 2.0 | 读取模型原有全部动画、选择/循环/单次、过渡、镜头、进度、暂停、逐帧 | 64MiB 上限；未压缩且无外部纹理/缓冲 URI；没有动画会显示缺项；不自动绑骨、重定向或生成动作 |

切动作时，部件模型从当前屏幕上的混合姿态继续过渡；循环采用周期邻点计算切线，减少接缝速度突变。GLB 使用 three.js AnimationMixer 保留原动画。二维保留原帧，避免淡入出现两套肢体。

构建输出 `manifest.json`、`report.json`、`provenance.json`、`generation-plan.json` 和可搬运的本地网页，附锁定版本的 three.js 和 MIT 许可证。构建失败不发布半成品，不覆盖旧批次。缺项计划里的任务均为 `not-executed`，不是已经生成的资产。

网页支持整套动作巡演、速度、四个视角、暂停、逐帧、进度定位、模型过渡时长和生成检查记录。记录提供保存链接与可复制文本。切到后台会暂停，回前台由用户继续。模型文件只在本地读取。检查记录表示看过什么，不自动批准正式资产。

## 如何使用

### 新步态试点（2026-10-02）

v3 六部件二维 IK 已烘焙 48 帧，脚轨迹和骨长检查通过，但用户拒绝其关节机械感。[失败记录](../input/codex/mint-adventurer-walk-v3/notes.md)说明了数学连续与视觉质量的差别。保留工具与便携导出作实验，不默认推荐为正式角色生产路线。

v4 改为完整角色十二张原画；[制作及已知问题](../input/codex/mint-adventurer-fullframe-v4/notes.md)记录了真实生图、颜色修正、行裁框与脚底平移配准。关节拼接消失，但比例/轮廓和腿身份仍待验收，没有发布到游戏。

```bash
.venv-cutout/bin/python src/character_workbench.py --profile <已加工素材配置.json> --out output/my-fullframe-review
.venv-cutout/bin/python -m http.server 8771 --bind 127.0.0.1 --directory output/my-fullframe-review/viewer
```

默认播放完整原画；素材选择里保留用户未通过的关节版和旧八帧版。12 帧 / 800ms；没有插帧或复制帧伪装帧率。短期先验收美术方向，不能据此补齐整套动作。可控的骨骼生产还需要[网格权重变形与关键帧修形](https://esotericsoftware.com/spine-meshes)；参考帖子的连续视频路线则需要真实的视频生成来源。

在仓库根目录执行；本机已有 `.venv-cutout`，其他机器按 [工具箱指南](TOOLKIT.md) 安装 Python 核心依赖。

```bash
npm ci --prefix workbench

# 二维流程样例，不依赖某个游戏；几何样例不代表正式美术
.venv-cutout/bin/python examples/make_workbench.py --out output/my-workbench-v1

# 已有二维动作包
.venv-cutout/bin/python examples/make_workbench.py \
  --out output/my-hero-workbench-v1 --motion-pack output/my-motion-pack/manifest.json

# 只有需要模型检查时才加 --models

# 加入 Frontier 原有角色，读取游戏文件但不写回游戏
.venv-cutout/bin/python examples/make_workbench.py \
  --out output/frontier-workbench-v1 --frontier ../frontier-brawler

.venv-cutout/bin/python -m http.server 8771 --bind 127.0.0.1 \
  --directory output/frontier-workbench-v1/viewer
```

打开 `http://127.0.0.1:8770/`。本页资源全部本地化，使用 ES modules，需要 HTTP，不能直接双击 HTML。普通二维单包仍可用原有离线 `preview.html`。

二维优先的本次演示目录是 `output/character-workbench-2d-v1/viewer-checked`，默认显示 Frontier 原画，三维模型检查折叠为可选入口。

自定义配置复制 [workbench.json](../recipes/workbench.json)。路径相对配置文件；已有图集可以加入：

```json
{
  "id": "my-hero", "title": "我的角色", "kind": "sprite",
  "manifest": "hero-pack/manifest.json", "direction": "SE",
  "requiredActions": ["idle", "walk", "run", "attack"],
  "requiredDirections": ["SE", "NE", "E", "S", "N"],
  "reference": "hero-reference.png",
  "identity": "固定角色服饰、配色、武器和比例"
}
```

首版单个 sprite 输入只声明一个方向，其他方向列为缺项；已有不同方向可分别作为检查项加入 characters。当前不自动生成、翻转或合成多方向包。

模型输入示例；动作名必须与 GLB 内实际名字一致：

```json
{
  "id": "my-model", "kind": "glb", "model": "hero.glb",
  "loops": {"Idle": true, "Walk": true, "Attack": false},
  "defaultAction": "Idle", "requiredActions": ["Idle", "Walk", "Attack"]
}
```

GLB 无循环元数据，必须明确 loops；未声明的默认单次播放。也可在页面点“打开自己的 GLB”，选择本地文件，并切换“GLB 当前动作循环”；这些临时调整写入下载检查记录，不修改源文件。没有自动检测攻击命中或脚步触地。

```bash
.venv-cutout/bin/python src/character_workbench.py \
  --profile input/my-character/profile.json --out output/my-character-review-v1
```

部件库 fps 默认 24，明确记录在配置里，周期为 `(end - 1) / fps`；重复闭合末帧不额外停留。GLB 用源文件的实际动画时长，Blender 导出可能保留起始时间偏移，因此不强行改成部件预览长度。游戏 60Hz 时间由消费端持有。

## Frontier 的首个实际发现

当前 Godot 首阶段主角使用 6 行×4 张原画。实际需要的 `slash3 / skill / execute / jump / airSlash` 缺少专属原画；现有游戏通过借用 `slash2` 或 `move` 姿态及时间采样保持可玩。示例只统计当前首阶段可达主角动作，不把同一数据文件里的敌人和其他职业动作全部算成主角缺口。

工作台按动作总长均分原画用于美术检查，**不执行 Godot 的阶段采样、重心形变、跳跃高度或命中窗口**。因此这次没有替换游戏资产，也没有把模型预览视为新的游戏效果。

推荐下一个美术试点先补专属 `jump / airSlash`，再补 `skill / execute / slash3`；每次固定同一角色参考，只重做失败动作。在既有 Godot motion lab 验证后才采用。若选择完整 3D 路线，应先提供一个已绑定模型，验证同骨架的待机、步行、攻击三动作，再做跨骨架重定向；姿态参考图不能替代骨架。

## 验证与下一步

本次自动验证：26 项 Python 回归、17 项 Node 动画采样测试；原库 12 动作校验；Blender 5.2 `move` GLB 实际导出并通过 43 个关键帧数值对照。顺带修复了旧导出脚本对 Blender 4.4+ 分层 Action/5.0+ 移除旧接口的兼容问题，依据 [Blender 官方迁移说明](https://developer.blender.org/docs/release_notes/4.4/upgrading/slotted_actions/)。

```bash
.venv-cutout/bin/python -m unittest discover -s tests -v
npm test --prefix workbench
.venv-cutout/bin/python src/validate_clips.py
```

浏览器走查记录见 [首版验收](validation/character-workbench-v1.md)。桌面预览不等同于玩家、移动设备、任意第三方蒙皮模型或正式游戏接入验收。

后续按真实需求推进：先获得人工认可的二维完整动作，再补 Frontier 的缺失动作并验证游戏效果；sprite-gen/Scenario 的上游适配需实际账号与来源；GLB 映射按有模型的需求独立推进。已实际生成二维候选，均没有升级为正式角色美术。
