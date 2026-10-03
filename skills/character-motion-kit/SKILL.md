---
name: character-motion-kit
description: 基于 GPT 生图逐帧制作、修正二维角色动作，或整理已有动作图集与检查已有动画模型。记录素材、真实生成版本和时长，导出草稿与验收预览。
---

# 角色动作素材包

解析当前 SKILL.md 的真实路径（可能由软链安装），向上两级得到 `ai-asset-pipeline` 根目录。所有仓库命令使用绝对路径。参考 [工具箱契约](../../docs/TOOLKIT.md)；在本游戏工作区内同时遵循 [现有资产工作流](../../docs/CODEX_ASSET_WORKFLOW.md)，不把视频抽帧默认升级为正式资产。

## 整套动作与模型检查

用户要求整体动画、跨动作衔接或模型预览时，阅读 [角色动作工作台](../../docs/CHARACTER_WORKBENCH.md)。复用已有 motion manifest、`animation-library` 或自带动画的自包含 GLB，生成本地检查项目。二维单包加工继续走下文，不强制先建工作台。

用 `src/character_workbench.py --profile <配置> --out <新批次>` 构建。默认优先二维角色，不把二维素材任务扩成 GLB/绑骨任务。缺依赖时在仓库执行 `npm ci --prefix workbench`，用本地 HTTP 服务打开输出页。[配置样例](../../recipes/workbench.json) 是二维动作包；[示例脚本](../../examples/make_workbench.py) 的 `--frontier` 可只读接入当前 Godot 原画，`--motion-pack` 可接其他二维包。用户需要模型检查时才加入 `--models` 或使用 [模型配置](../../recipes/workbench-models.json)。

部件库是枢轴模型，不是蒙皮骨架；GLB 不带动画时明确列为缺项，不声称可自动制作动作。GLB 不携带循环语义，按实际 clip 名显式配置 loops。模型过渡用于检查，游戏命中和取消窗口由消费项目决定。`generation-plan.json` 仅是待办，不能报告为已执行上游生成或已补齐缺失动作。

## 选择输入路径

第一次使用或材料需求不明确时，阅读 [使用入口与所需素材](../../docs/CHARACTER_MOTION_QUICKSTART.md)。确认角色参考、动作/朝向、画布/cell/anchor和时间；不把旧2×2绿幕网格约定套到当前透明逐帧路线。

用户要本地可操作入口时，使用 `npm run dev --prefix workbench`，打开 `/pipeline` 九步制作流水线或 `/motion` 动作工作层。框架为Vite + React + React Router + shadcn/ui + Jotai，操作与数据逻辑写在TS/TSX，不再生成HTML业务页面。已有图片可以直接第6步处理；入口仅整理请求，不调用生图、不伪造文件检查或验收。`npm run prepare:data --prefix workbench -- --run <批次目录>`更新冻结试点资源。详情见 `docs/FRONTEND.md`。

用户要求以当前 GPT 生图生产动作时，阅读 [GPT 逐帧角色动画](../../docs/GPT_MOTION_GENERATION.md)，用 `src/motion_generation.py` 创建可续做任务。复用宿主内置 imagegen，先实际查看身份参考与各帧姿态草图；不把计划当生成，不改走 GLB。导入/局部修正需保存实际提示词与真实参考顺序。身份、相机和整套比例固定；每次优先修正失败相位，不无限重抽整张图集。修正输出先以 `import --candidate-only` 登记，实际查看后用 `select --attempt-index` 选择；失败候选可用 review 的同名参数记录原因。正常速度完整检查后用 `cycle-review` 留结论；导出仍是草稿。单帧接受不代表完整步态接受，代理判断也不是用户批准。

已有相位基本正确而整套衣领/躯干/衣摆漂移时，可按GPT指南试一次“编辑既有图集”的一致性修正：保留原格子/原画作为对照，一个图集编辑记录为一次真实调用。实际输出可能重画脸和腿，即使提示词要求保留也不能报告像素不变。确认行列、空格、近远腿和落脚，再给出显式Aseprite矩形加工；不能按图片不同就认定完整步态通过，也不把裁切八格登记成八次GPT调用。行列或相位被改乱则拒绝，继续针对具体失败位置处理。

同朝向动作的头部逐帧变化时，若用户已授权裁切原画，可复用同一头部区域：阅读上文文档的固定区域复用章节，使用 `src/motion_region_lock.py`，逐帧明确裁切线、接缝带与起伏。它不会自动识别头部，不适用于转头/转身，不把衍生图登记成新 GPT 生图。先看衣领接缝和完整循环，再考虑推广到其他动作。

upper-region也可用referenceImage指定同画布外部PNG，便于跨动作复用身份母版；referenceFrame仍需有效。工具拒绝尺寸/轮廓位移越界，接缝以下保留源字节。母版护脸手、武器或头饰可能进入裁切带，须先显式检查并准备裁切参考，记录加工范围/hash，不能自动整行带入造成多出的手；PNG没有anchor，不能以尺寸相同认定登记正确。v16给出本角色示例，坐标不能推广为通用识别规则。

眨眼等固定位置的小范围变化，可在同一工具的计划中使用 `operation:rectangle-patch`、`rect:[left,top,right,bottom]`、`referenceFrame` 和 `feather`。坐标为实际动作包cell像素；矩形之外保留参考帧，不自动跟踪脸。先检查闭眼画面是否覆盖原眼，避免裁切过小残留双眼或过大带入脸型变化。可操作示例的呼吸是整张原画围绕anchor的微小缩放，默认0.6%/2.4秒；用控制器breathAmplitude=0关闭，不能称作新增GPT帧。

仅修一个相位时，可显式设置frameIndices（零起始，缺省处理全部帧）；未指定的帧保持原像素。rectangle-patch可用referenceImage指定同画布旧帧，矩形外复用它，矩形内采用本次候选；保留路径/hash，不自动缩放。先看接缝是否穿过关节、武器或手指，避免为了固定上身把大腿割成断层。像素范围检查只证明未改区域，不证明拼接自然。完整候选失败时可只复用有效部位，须记录原图拒绝与派生用途，不能把它升级为整帧通过。

1. **已有透明帧**：直接加工。帧放在各动作子目录；命名按自然数字顺序读取，frame-2 在 frame-10 前。整套动作共用源画布、角色比例和基准线。不要逐帧裁切缩放来掩盖漂移。
2. **已有 sprite-gen 产物**：要求 compose 后的最终图集，再执行该版本的 export-aseprite，读取其 JSON。不要读取 `frames/` 缓存，因为用户在选帧界面里的修改可能尚未烘焙到那里。
3. **需要新生成**：先确定角色参考、动作集合、朝向和目标显示尺寸。若存在已安装的 sprite-gen，阅读其本地 Skill 与当前版本文档，调用上游生成与 compose 流程；不要假设工具已经安装。若不存在，可用宿主已有生图工具遵循目标项目的素材规范生成参考或源网格，再走项目现有加工链路。明确实际采用的路线，不声称使用了未运行的 sprite-gen。

首个试点默认只做 idle 和 attack；用户要求其他动作时保留。身份一致性由参考约束并人工确认；失败的动作记录原因、保留原始输入，修正该动作，不把整套无限重抽。

攻击补中间原画时先明确总时长与伸直/接触姿态的边界，沿真实前后姿态约束屈肘位置；不能仅凭帧数增加就认定更连续。新增原画可能已提前回到守势，需要拒绝并针对前拳修正。分配帧时长时保留目标动作窗口；末帧可复用idle做收招连接，但要记录复用而非新增生成。参见GPT指南的六姿态示例；其中裁切/保护框为人工指定，适用该角色，不自动套到其他角色。渲染采样/GIF帧不等于GPT原画。

步行补中间原画时，同时查看真实前后帧，明确该时刻抬脚是否已经越过承重脚。模型直接跳到后姿态时必须拒绝，不能以两张图不同认定补帧有效。整帧重画身份时，只有已验证有效的下身才能显式局部使用，继续检查腰腿连接。将原100ms段拆为50ms原姿态＋50ms新姿态可保留总时长；插入原画后，必须重新核对stopContactFrames与stopClipsByContact，避免旧索引落到摆腿帧。重复登记同一生成原图的不同offset不是多次GPT调用。

## 打包

修改动作后，可用 `src/motion_compare.py --config <比较配置> --out <新目录>` 导出独立同步比较页。配置version=1、action、两个inputs（manifest与label），可选title/note。双方必须是同画布、同anchor、同总时长的循环动作，帧数与逐帧duration可不同。复制真实图集并保存SHA，按共享真实毫秒时钟各自选帧，支持1×/0.5×和参考帧定位；不插帧、不拉伸非方形画布、不依赖原来源目录或其他网页。示例 `input/codex/mint-adventurer-compare-v1.json`。比较页用于人工验收，不能由显示成功自动批准美术。

步行素材与游戏移动速度不匹配时，使用 `src/motion_stride_review.py --config <人工标记配置> --out <新检查目录>`。配置需显式给出 manifest、循环 action、speed、renderScale、direction（源图朝向 1 或 -1）与 observations。`markerKind:fixed-point` 使用作者指定 point；`contact-region` 使用作者指定 rect 内最下两行的透明度轮廓中心。每个支撑组至少两个不同时间的标记。工具输出原画标记图、轨迹图及速度滑块，保留源 hash，禁止覆盖旧目录。

轮廓中心会随脚掌滚动变化，工具不识别近远腿、不认定脚掌固定，也不自动修改游戏速度。拟合速度仅用于诊断；恒速结果不覆盖起停、跳跃和镜像。人工框和分组须先检查，不能用 RMS 降低替代正常速度的步态验收。示例见 `input/codex/mint-adventurer-stride-review-v2.json`。

复制 [动作配方](../../recipes/character.json) 到本次目录。逐动作明确 name、loop，以及目录输入的 fps；cell 是统一输出画布，anchor 是从左上角计量的归一化锚点元数据，不是自动脚底对齐。

```bash
# 已有透明帧
python3 <pipeline-root>/src/asset_bundle.py \
  --recipe <本次配方.json> --input <动作目录> --out <新的素材包目录>

# 上游最终 Aseprite 导出；与 PNG 放同目录，meta.image 指向同目录下的 PNG
python3 <pipeline-root>/src/asset_bundle.py \
  --recipe <本次配方.json> --input <最终导出/aseprite.json> \
  --aseprite --out <新的素材包目录>
```

使用具有 Pillow、NumPy 的 Python 3.10+；优先检查仓库的 `.venv-cutout/bin/python` 或 `.venv-toolkit/bin/python`，用可用者替换命令中的 python3。导入时保留上游逐帧 duration，配方 fps 不覆盖它；loop 由配方显式指定，因为 Aseprite 标签不携带此语义。当前适配器接受 forward、未 trim、未旋转的完整帧；其他格式报错后按上游导出契约处理，不猜网格或偷偷丢弃时长。

同一角色有多个已加工的动作包时，阅读上述 GPT 文档的集合章节，用 `src/motion_collection.py --config <集合配置> --out <新批次>` 合并。画布和 anchor 必须一致，动作名不能重复；保留 duration/loop 与上游审查，不自动升级整套状态。先生成整套预览，再检查切动作和单次结束回 idle。

跨动作选帧、复用或重排时长，用 `src/motion_sequence.py --config <编排配置> --out <新批次>`，不必每个角色另写组帧脚本。配置inputs列motion manifest；states明确name/loop/frames，每帧用input/action/frame索引及可选durationMs。缺省保留源时长；拒绝不兼容画布/anchor和越界，不缩放。输出保留RGBA、每个帧来源/原时长/新时长与源包审查副本，仍draft，编排本身0次生图。受击可立即显示冲击原画、补恢复原画、末帧复用idle；保持总时长与玩法反馈窗口，不能为了过渡延迟反馈。详细配置见GPT指南v15。

跳跃作图时区分原画收腿姿态与游戏整体位移。不要把腾空帧按最低脚底强制对齐地面；工作台可用 profile 的 previewMotion 作起落预览，曲线不写入源素材包。阅读 GPT 文档对应章节，实际游戏匹配自己的物理高度，避免重复叠加。

跳跃落地直接接idle时，先检查是否缺压缩吸收与恢复原画。可显式复用起跳压缩作短落地吸收、补浅压缩再接真实idle，并保留蹬离/着地时间。补收腿中间画时检查膝盖和脚底相对前后姿态的位置，模型可能仍画成深蹲或完整收腿；失败候选要保留并拒绝，不能凭新增帧数声称连续。反向复用空中姿态只提供过渡，不表示新增下降惯性原画；参见v14示例。整帧编辑会改变局部脸型/衣服，须正常速度检查。

需要验证消费端时，可用 `examples/make_sprite_playground.py --manifest <实际包/bundle/manifest.json> --out <新目录>` 导出可操作 Canvas 示例。示例需要 idle/move/attack/hit/jump 五动作；后三者为单次。直接读取原始帧时长与 anchor，不读取工作台 previewMotion。默认跳跃80ms蹬离、340ms着地、40素材px高度；其他节奏需在消费端传入 `SpriteController` 的 launchMs/landMs/jumpHeight，不能把示例默认值当所有素材的正确节奏。浏览器点击与自动演示只是消费示例，不等于手机触摸或正式游戏战斗验证。

可选 move-start/move-stop 单次原画用于起停过渡；控制器自动接到move/idle并按时长渐变移动速度，短按可取消、重新按住可重入。缺少这两动作时保留直接切换。可复用一张中间原画作反向衔接，但要明确一次生图、两帧位置；共同停步姿态不能证明任意步行相位的腿部都连续，仍需检查。

素材明确落脚相位后，可给SpriteController配置stopContactFrames（move的零起始索引）与contactHoldMs（默认40）。松开先沿原画剩余相位减速到最近落脚，再接停步；不猜脚掌、不插画帧。缺配置保留直接切换。prepareSettle生成运行时move-settle片段，渲染器通过currentClip()读取实际片段，不能假设所有运行时动作都在原manifest.states中。消费示例导出时用--controller-options <JSON>独立保存配置；其余角色需自己确认落脚和允许的停步距离/时长，不能照搬[0,4]。短按松开与再次移动使用当前速度起始，避免重新跳到满速/零速。

Godot 二维消费端可运行 `src/godot_sprite_export.py --manifest <实际包/manifest.json> --out <新目录>`。将输出 `hero_frames.tres` 与 `atlas.png` 一起放入目标项目，同目录相对引用可搬动；给 AnimatedSprite2D 指定该 SpriteFrames，并按 `export.json` 的 spriteOffset 设置 offset（centered=true）。保持真实逐帧时长与 loop；不自动接入物理、呼吸、起停速度或战斗。输出 project.godot 是独立预览，空格换动作/R重播/左右翻转。可先 editor --import，再 --headless --script validate.gd 实际检查，详见 GPT 指南。导入通过只证明资源可用，不能自动批准美术或游戏。

## 检查和交付

需要可直接打开、下载与带走的整套验收入口时，用 `src/motion_preview_site.py --manifest <实际包/manifest.json> --out <新目录> [--controller-options <JSON>]`。输出首页、工作台、可操作示例、游戏素材/Godot预览/Web示例ZIP，统一起落配置并保留来源hash与草稿状态。需要五核心动作，单次/起落窗口/落脚索引需匹配素材；非法参数或输出已存在会拒绝。只打包已有原画，不执行生图；完整GPT任务仍留在生产工作区。Web下载自带工作台和包内返回链接；Godot导入预览不包含完整游戏战斗。用本地HTTP服务打开输出根目录，不让用户仍留在上一版首页；更新既有入口前保留旧页与对照。

- 播放 preview.html：1×、深浅背景、逐帧、正常速度；攻击应播放到末帧停止，idle 按配置循环。
- 检查身份、朝向、尺寸、脚底漂移、触边、循环接缝。bbox 只作测量，不证明脚掌接触或步态正确。
- 走/跑必须逐帧确认左右腿交替的落地、承重、经过、蹬离，以及末帧到首帧的接缝；八张不同图片可能只是同一个半步态的重复，像素不重复不等于步态完整。
- 消费游戏动作不连贯时，先核对实际播放时长、命中/取消窗口和高度衔接，再决定是否重画；离线图集预览不能替代游戏内动作切换。复用姿态延长收招不算新增原画。
- 交付 atlas.png、manifest.json、aseprite.json、grid.json、透明帧和预览页。真实帧数以 manifest 为准，grid 末帧补齐不代表新增动作帧。
- Cocos 等消费端必须核对行序、帧数、坐标原点、锚点和时间语义；这些导出不是已完成的引擎插件。游戏中验证并保存证据后才能更新正式资产状态。命中窗口、碰撞和数值继续由游戏决定。

矩形修正多个相位时，可使用referenceManifest（可选referenceAction）逐帧保留对应旧底图，工具要求相同帧数、画布、anchor、loop与时长。protectedRects恢复对应底图细节。不可用一张固定底图覆盖整周期而冻结手臂或身体；须检查完整前后摆、遮挡和两个落脚相位。整帧生成失败而仅局部有效时，记录整帧reject及明确派生区域，分别验收派生循环和起停衔接。

两种落脚手臂/腿不同的角色，可配置stopClipsByContact，如{"0":"move-stop","4":"stop-front"}：key必须在stopContactFrames中，value指向素材包已有的单次停步动作。控制器对外状态仍move-stop，currentClip()返回实际片段；渲染器不可按状态名直接读共享帧。未映射落脚、起步短按取消均回退共同move-stop，缺共同图则idle。必须先补真实对应姿态并正常速度检查，映射逻辑测试不能证明停步美术自然。

多帧起步已确认姿态可反向复用时，可显式启用reverseStartOnRelease=true。短按取消只撤回已播放的起步帧并接实际idle，维持当前速度减速；缺省false，单帧起步仍共同停步。反向播放不代表新画了制动惯性，必须检查手臂/腿部适用性。起步末帧尽量采用真实move首帧并核对RGBA相同，避免进入循环时再切一次图；保持输入响应，记录起步总时长变化。

### 固定引擎工作层

本项目已有固定版本 sprite-gen 适配层，已有素材接入优先阅读 `docs/SPRITE_GEN_INTEGRATION.md`，使用 `src/sprite_gen_adapter.py` 的 import/apply/candidate/select/review/export。显式 durationMs 是时序真值；修改后重新生成批次并清除受影响动作旧验收。当前只验证素材处理，不得声称新角色已生成或通过用户验收。
