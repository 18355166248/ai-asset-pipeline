# GPT 逐帧角色动画

在 `ai-asset-pipeline` 内维护，入口为 `$character-motion-kit`。当前选 Skill 配套本地命令，不另建后台：Codex 内置 imagegen 是实际生成器，Python 管理任务、材料、修正和导出，不伪装成能直接调用宿主生图的 HTTP 服务。内置路线不需要用户另配 API key。

## 当前候选状态（2026-10-03）

工具入口现为 `http://127.0.0.1:8770/` → `toolkit-v2.html`，可准备素材、生成制作请求、查看v23候选、试玩及下载。用户已反馈十帧“有改善，先完善工具入口”，不再把等待该方向反馈列为当前工具阻塞。v23 Godot4.7.2导入exit0、实际验证113项/8动作通过；81项Python、37项Node工具测试通过；三个ZIPCRC与manifest/atlas字节相等验证通过。证据toolkit-readiness-v23.json。素材保持draft，真实游戏/设备接入由消费项目验收。

工具入口展示 `output/mint-adventurer-collection-v23/`，v20保留旧版基线；最新补帧候选为 `output/mint-adventurer-collection-v23/`（8动作43播放位置）；v20基线为8动作41播放位置、27张不同RGBA，仍draft。起步四姿态100ms、后摆停步五帧175ms、前摆停步三帧140ms。跳跃首帧换成实际idle，40ms时长不变；五个单次动作的末帧也与实际idle相同。

v20为0次新GPT调用，复用已生成母版修正身份入口。v21新增一次真实调用，仅承重腿局部复用；随后支撑后段另试一次生成，未达到目标且有重画接缝，已拒绝且未合入。其他所有原画、duration与loop字节/数值不变，跳跃总440ms与80..340ms起落窗口保留。默认8770指向toolkit-v2.html；当前工具是Skill调用宿主GPT + 本地加工/交付，并非生图HTTP后台。

材料与直接调用见CHARACTER_MOTION_QUICKSTART.md。已有真实生图版本、失败图和派生区域保持来源记录；模型输出与用户期望可能仍有差异，每个角色需正常速度和目标游戏验收。当前示例可试玩和下载，正式美术状态仍draft。

上一轮消费预览为v10集合 `viewer/playable-v11/`：素材v10，增加显式落脚停步策略，该轮无新GPT调用或新姿态。旧playable保留直接切停步作对照。

## 要准备的素材

| 输入 | 必需性 | 要求 |
|---|---|---|
| 角色身份参考 | 必需 | 一张完整角色图，头发、脸、服饰、武器清楚；尽量与目标朝向一致。参考本身可以不透明 |
| 身份描述 | 必需 | 固定发色、眼睛、服饰、随身物件和画风，不能仅写“可爱角色” |
| 动作与相机 | 必需 | 如右侧原地步行；攻击需写前摇/命中/收招姿态，不能把 walk 当全部动作 |
| 画布/游戏尺寸/时长/锚点 | 必需 | 整套共用画布与尺寸，每帧显式 durationMs，每动作显式 loop；anchor 是统一的归一化锚点 |
| 姿态草图或关键姿态 | 推荐 | 每帧一张，完整画布，明确近远肢体与遮挡；默认提供八帧右向步行草图 |
| 已认可的生成原画 | 可选 | 修正时可作为主编辑目标，限定只改失败动作部位；保留原身份参考 |

不要求先做 GLB、切成六个关节部件或购买视频服务。完整原画逐帧由 GPT 生成；草图只是控制参考，不是最终美术。现有默认草图是一个步行试点，不能自动推断任意角色比例或生成所有动作。

## 可执行流程

仓库根目录以下示例；使用技能时解析安装路径获得仓库绝对路径。一个任务依次写入，不让两个执行器同时修改同一个 job。

```bash
.venv-cutout/bin/python src/motion_generation.py prepare \
  --reference input/my-hero.png \
  --identity '固定角色身份、服饰和画风' \
  --out input/my-hero-motion-v1
```

得到 job.json、每帧的 `*-guide.png` 和 `*-prompt.txt`。准备动作不会调用 GPT，也不会产生完成的动作帧。

Skill 读取单帧提示词，查看参考图后实际调用宿主 `image_gen`：

```text
prompt = 当前帧提示词
referenced_image_paths = [当前帧姿态草图, 角色身份参考]
transparent_background = true
```

没有草图时只有身份参考。默认先看两半周期接触与经过姿态；这四张不正确时修正它们，再补其他相位，避免批量生成同一个半步。不要只凭“生成成功”认定可用。

```bash
.venv-cutout/bin/python src/motion_generation.py import \
  --job input/my-hero-motion-v1/job.json --frame move-000 \
  --image /absolute/path/actual-generated.png

.venv-cutout/bin/python src/motion_generation.py inspect \
  --job input/my-hero-motion-v1/job.json --out output/my-inspection-v1.png

.venv-cutout/bin/python src/motion_generation.py review \
  --job input/my-hero-motion-v1/job.json --frame move-000 \
  --verdict reject --reviewer agent --reason '近侧腿/手臂没有按相位交换'
```

导入必须是实际生成的静态透明图。程序保留原字节、原尺寸、哈希、归一化画布、真实提示词与按顺序使用的参考图。只整体等比缩放画布，不按单帧 bbox 改角色比例。画布比例不匹配会拒绝；没有自动去背、裁剪或扩图。可用 `--offset dx dy` 显式平移配准，必须检查未裁掉人物，并说明所采用的脚底/骨盆锚点，不能借此掩盖比例或步态错误。

局部修正：调用 imagegen 编辑实际角色帧，保存实际修正提示词文件，再登记：

```bash
.venv-cutout/bin/python src/motion_generation.py import \
  --job input/my-hero-motion-v1/job.json --frame move-004 \
  --image /absolute/path/repaired.png --prompt /absolute/path/repair-prompt.txt \
  --reference-inputs /absolute/path/edited-character.png /absolute/path/pose-guide.png
```

记录必须与真实调用一致，不能拿准备阶段提示词代表另一次编辑。新图、新偏移或新调用素材得到新登记版本，并清空该版本审查；旧版及失败原因保留。登记版本数不等于 API 调用次数。`--reviewer user` 仅用于记录用户实际反馈，不把代理自己的判断写成用户批准。

全部帧有实际结果后导出草稿（允许未审查或失败帧供对照，不升级正式资产）：

```bash
.venv-cutout/bin/python src/motion_generation.py status --job input/my-hero-motion-v1/job.json
.venv-cutout/bin/python src/motion_generation.py pack \
  --job input/my-hero-motion-v1/job.json --out output/my-hero-motion-v1
```

包内有透明原画、atlas、manifest、Aseprite 格式导出、离线预览、真实逐帧时长、generation-review 与可搬运的生成来源。每帧检查与**完整循环检查、游戏验证**分别记录；即使所有单帧 accept，完整步态与游戏验收也不会自动变成通过。仍需在工作台正常速度、半速、接缝、切动作及目标游戏里验收。

## 其他动作

`prepare --spec /absolute/path/spec.json` 接受自定义动作，路径相对规格文件。每帧可指定相同画布大小的 guide。示例：

```json
{
  "version": 1,
  "title": "角色攻击",
  "direction": "right-facing side view",
  "canvas": [512, 512],
  "cell": [192, 256],
  "actions": [{
    "name": "attack", "loop": false,
    "frames": [
      {"pose": "重心后移、举剑前摇", "durationMs": 120, "guide": "anticipation.png"},
      {"pose": "身体前压、挥剑经过命中位置", "durationMs": 70, "guide": "strike.png"},
      {"pose": "收剑回到准备姿态", "durationMs": 150, "guide": "recover.png"}
    ]
  }]
}
```

无 guide 的自定义动作只使用文字与身份参考，姿态可控性更弱。程序不生成战斗命中窗口、碰撞或根运动。源横图集受 16384 像素限制，大任务按动作拆分；同一正式角色包仍需共用画布、锚点与比例。

## 步行试点历史（v5首轮）

`input/codex/mint-adventurer-singleframe-v5/` 首轮实际执行十一次 GPT 生图，后续同任务又有 v6 两次修正，完成八个相位；保留失败的远侧接触后通过局部编辑改正摆臂。经过与摆腿帧有实际动作变化，没有把同一帧复制成八张。近远腿、衣服轮廓和身体比例仍需要完整循环审查，最初承重与经过姿态过于接近、末帧步幅过大；另两次基于实际接触帧的编辑修正了这两个位置，但外观一致性仍未通过。

实际源图均为 1254 方形透明 PNG，而非请求的 512 方形；整画布统一缩放到 512。随后按每帧最低不透明靴底（alpha>128，已检查每帧至少一脚落地）显式平移到 y=485。`registration.json` 记录测量和位移；该方法不会自动修复跳跃、跑步、比例改变或根运动。保留配准前包 `output/mint-adventurer-singleframe-v5-raw/` 与配准后包 `output/mint-adventurer-singleframe-v5-registered/`；八帧共 800ms。

后续修正版导出到 `output/mint-adventurer-singleframe-v5-repaired/`，该轮预览服务指向该目录的 `viewer/`，提供原画、配准前与旧版对照，以及只影响显示的倍率控制。任务命令和 41 项 Python 回归通过，不代表动画审美、完整循环或游戏集成已经通过；状态仍为草稿。

## 固定区域复用（同朝向动作）

实际逐帧生成可能改变脸、发型，即使提示词要求一致也不保证像素一致。本轮按已授权的原画裁切方式，复用 move-000 的头部，让身体与四肢保留实际 GPT 原画。

材料：已打包透明 motion manifest/atlas、一张选定帧的头部原画、每帧明确的头部起伏位置。输入图集各帧必须同画布、同朝向。命令不推断头部位置，不自动去背或修正姿态；不能用于需要转头、转身、表情变化的动作。

```bash
.venv-cutout/bin/python src/motion_region_lock.py \
  --plan input/codex/mint-adventurer-singleframe-v5/head-lock-plan.json \
  --out output/my-head-lock-batch
```

plan 中 manifest 相对 plan 文件；action 指定一个动作；referenceFrame 是从零计数的参考帧；cutY 是目标图集画布中的裁切线，feather 是该线向上的接缝混合带。headOffsetY 必须逐帧明确，本例在 256 画布使用 [0,2,0,-2,0,2,0,-2]。上方用参考原画替换，下方完全保留动作原画；仅衣领带混合，不做时间插帧。透明轮廓按预乘 alpha 处理，替换时清掉旧头部，避免双轮廓和黑边。

输出 source.png/source.json、recipe.json、provenance.json 和 bundle；原始帧不改动。只导出指定动作，保留逐帧时长、loop、统一画布和 anchor。输出批次不能覆盖，来源记录包含计划、manifest 和 atlas 的 SHA256。属于现有 GPT 原画的衍生加工，不增加生图调用计数。

该轮样片 `output/mint-adventurer-singleframe-v5-head-lock/` 是 8 帧 800ms，预览服务已切到该目录 viewer。浏览器检查了相反接触帧的头颈连接，完整美术与游戏验收仍未通过：躯干/衣服还有逐帧变化；固定区域不能解决不正确的步态。Python 43 项通过，含半透明边缘、旧轮廓清除、时长/loop 保留与失败不发布。

## 候选、回退与完整动作审查

修图可能失败，使用 `import --candidate-only` 只记录实际调用，不自动替换当前帧。`status` 中 selected 为登记列表的零起始索引，和 attempt 目录编号不同。

```bash
.venv-cutout/bin/python src/motion_generation.py select \
  --job input/my-hero-motion-v1/job.json --frame move-002 --attempt-index 2

.venv-cutout/bin/python src/motion_generation.py review \
  --job input/my-hero-motion-v1/job.json --frame move-002 --attempt-index 1 \
  --verdict reject --reviewer agent --reason '实际输出仍是后踢，未使用'

.venv-cutout/bin/python src/motion_generation.py cycle-review \
  --job input/my-hero-motion-v1/job.json --action move \
  --verdict reject --reviewer agent --reason '实际循环中的服饰与躯干仍变化'
```

审查候选无需先选中它，不影响当前选定版本的结论。完整动作接受必须先逐帧接受；单帧接受不会自动批准循环。完整审查绑定逐帧内容、真实调用来源、时长、loop、画布和 anchor；换选定版本后清除，改时长后导出时剔除陈旧结论。pack 的 generation-review 保持 draft，游戏验收不会自动接受。

v6 本轮实际新增两次 GPT 调用，任务累计 13 次。第一次编辑仍后踢，记录为拒绝的候选；第二次使用明确的前摆膝姿态草图生成向前经过帧。源包 `output/mint-adventurer-passing-v6/`；固定头部衍生包 `output/mint-adventurer-passing-v6-head-lock/`，该轮服务指向后者 viewer。八帧仍为 800ms，没有衣服区域拼贴或时间插帧。固定衣服试拼会遮挡抬膝，未发布该实验。

当前完整动作审查仍为 reject，记录在 `input/codex/mint-adventurer-singleframe-v5/cycle-review-v6.json`。向前经过已明确，但躯干/衣服变化仍未解决。新的默认 prepare 草图也明确两半周期的前摆膝，既有任务的草图保持原样，避免改写真实调用历史。Python 47 项通过，包含候选不替换/可回退、候选重复导入幂等与审查失效；这不代表美术通过。

## 合成同一角色的动作集合

一个角色的多次生成任务，可以通过 `src/motion_collection.py` 合成同一图集。材料是已验证格式的透明 motion manifest/atlas，而不是视频或裸图片网格；所有输入必须相同画布、anchor，不能用自动缩放掩盖不同动作的比例差异。动作名不得重复，可用 actions 显式选择。

```json
{"version":1,"title":"我的角色","inputs":[
  {"manifest":"../../output/combat/bundle/manifest.json","actions":["idle","attack"]},
  {"manifest":"../../output/walk/bundle/manifest.json","actions":["move"]}
]}
```

manifest 路径相对配置文件。执行：

```bash
.venv-cutout/bin/python src/motion_collection.py \
  --config input/codex/mint-adventurer-collection-v2.json \
  --out output/my-character-collection
```

输出共用 atlas、透明帧、manifest、Aseprite JSON 和预览；逐帧时长、loop、alpha 保留。来源含可搬运的原 atlas/manifest、原始manifest字节与hash，以及找到的上游 generation-review/provenance 副本。组合后的 status 始终draft，源动作的接受/拒绝都保留，不把个别动作通过等同整个角色通过。完整生图原图/参考/提示词继续随原生成包保存；集合副本保证动作图集可读与组合复现，不宣称包含上游所有引用图片。

该轮 `output/mint-adventurer-collection-v2/` 收录 static idle1帧400ms、attack3帧110/80/140ms单次、move8帧800ms循环，共12源帧。本轮实际新增4次生图。浏览器已观察攻击末帧保持、开启回待机后idle；单个攻击经代理预览检查，未获得用户/完整角色/游戏批准。头部整行复用不应用于护拳动作，以免抹掉进入头部区域的手。该轮预览服务指向该集合的viewer。

未完成的效果：跨动作比例与衔接、步行衣服/躯干变化、idle呼吸、hit和jump。49项Python回归通过，仅验证命令契约与输出，不替代上述视觉检查。

## 跳跃姿态与物理位移分开

新增材料要求：腾空原画保持母版头部/躯干高度，只改腿部收起的姿态；不要在生图中同时烘焙整体起落。着地帧按脚底配准，腾空帧不能套用该方法。若已有图片确实包含整体位移，应先明确动作原点，再决定游戏如何提供高度，不能叠加两套。

工作台 profile 中可给已有的二维单次动作声明：

```json
"previewMotion": {
  "jump": {"kind":"jump-arc","heightPixels":40,"startMs":100,"endMs":320}
}
```

heightPixels 是统一素材画布坐标（本例256画布）的像素，显示时随整画布倍率缩放；起止时间在动作时长内，endMs必须晚于startMs。曲线只向验收页注入，源素材包保持不变。`examples/export-workbench/motion.mjs` 的 samplePreviewRoot 对整张姿态帧做连续平移，既不插画帧也不淡入双影。切回其他动作自动取0；实际游戏使用自己的碰撞/跳跃物理，匹配原画阶段即可，不默认复用预览曲线。

本轮新增5次真实生图，完成hit1张与jump3张选定原画，失败落地图保留后基于待机重画。五动作集合v3的预览已观察顶点40、落地0和切受击/回待机。起跳准备压缩偏大，三姿态的过渡仍需补原画；移动轨迹连续不等于肢体动画达到参考视频质量。Python50项、Node19项通过；未测浏览器FPS或正式游戏效果。

`jump-preview-trajectory.gif` 是三张原画叠加预览位移、再回idle的重复演示，20ms采样只增加显示帧，不增加生成原画数量。源图、动作包、预览效果、完整视觉接受与游戏验收分别记录。

## 跳跃五相位修正（v3任务 / v5集合）

准备80ms、蹬离60ms、腾空120ms、下降80ms、落地100ms。实际新增2次GPT调用；3张旧姿态复用原生成文件。准备图显式下移15px配准脚底，主体头顶从旧约89减到约74，仍比待机约52低22px，未达10..12px要求。下降图未按最低脚底强制配准。参考顺序、真实提示词、原图和sha在 `input/codex/mint-adventurer-jump-v3/job.json`，偏差和运行观察在同目录notes/runtime-review。

## 可操作二维消费示例

已经有实际图集时，可导出无需三维引擎的 Canvas 示例：

```bash
.venv-cutout/bin/python examples/make_sprite_playground.py \
  --manifest output/mint-adventurer-collection-v6/bundle/manifest.json \
  --out output/my-playable-v1
.venv-cutout/bin/python -m http.server 8771 --bind 127.0.0.1 --directory output/my-playable-v1
```

输入需要五动作 idle/move/attack/hit/jump、透明atlas、统一anchor及真实durationMs；jump/attack/hit需非循环。输入原始文件不改，输出仍保留draft状态。示例按住按钮或方向键走动，空格跳跃，J攻击/K受击；自动演示会走动、跳跃、攻击，再反向走回。左向只是右图镜像，不是生成的新朝向。

复用 `examples/export-workbench/sprite-controller.mjs` 时，创建 `new SpriteController(manifest, {speed:90, jumpHeight:40, launchMs:80, landMs:340})`，每帧调用update(dtSeconds, direction)，通过返回的frame坐标从atlas绘制。x/y与jumpHeight是素材像素/场景坐标，绘制整体缩放时同步缩放位移。控制器只示范运动与动作返回，不含碰撞/命中/连招取消。其他角色的launchMs/landMs必须按其起跳/落地图时间校准；若jump动作短于默认340ms会明确拒绝。原画不做像素插值，也不读取工作台previewMotion。

失焦/进入后台清理按住状态，pointercancel/lostpointercapture解除移动；这些有源码路径，尚未在手机实测。Node24项通过（新增5项消费控制器测试），Python消费示例3项通过（便携复制、越界拒绝、旧输出不覆盖）。浏览器实际观察自动走动x380→401、跳跃3/5高度38.7、结束idle及出拳。不能由此声称完整步态、键盘持续按住或移动端接受。

## 眨眼与呼吸（idle-v1 / 集合v7）

本轮实际生图1次，仅要求闭眼；模型仍改动了其他细节，因此不直接把整张新图作为下一帧。原始结果与实际提示词/参考顺序在 `input/codex/mint-adventurer-idle-v1/job.json`。加工计划 `eye-patch-plan.json` 用 `operation:rectangle-patch`、`referenceFrame:0`、`rect:[137,61,156,82]`、`feather:2`；坐标为256cell像素，输出闭眼帧只采用新图这一区域，其余使用旧待机帧。crop不是新GPT调用，空间接缝羽化不是时间淡入。

`src/motion_region_lock.py --plan <计划> --out <新目录>` 可复用该流程。必须先看眼部坐标和覆盖范围，不自动识别脸或追踪眼睛。`output/mint-adventurer-idle-v1-patched/eye-patch-check.json`验证矩形外RGBA相同；这只证明改动范围，不证明动画整体接受。`idle-blink.gif`只有2姿态，3110/90ms，无呼吸缩放。

Canvas控制器默认breathAmplitude=0.006、breathPeriod=2.4秒，对整张原画做纵向微伸展，绘制以脚底anchor为原点；切走动/攻击返回1。可设breathAmplitude=0关闭。没有切关节、没有新增呼吸原画，静态图集消费端需自行应用此modifier。浏览器观察idle倍率1.0044、出拳倍率1、高度0；工作台闭眼2/2可逐帧检查。Node25项通过，局部复用Python3项通过（包含旧流程回归与矩形外像素保留）。

## 起步与停步（transition-v1 / 集合v8）

本轮1次真实GPT生图，使用实际idle与move接触姿态作参考。同一中间原画用于move-start60ms和move-stop80ms；两条登记不是两次生成。动作集合共21帧位置，经RGBA哈希统计20张不同姿态。真实提示词/按序参考及原始文件在 `input/codex/mint-adventurer-transition-v1/job.json`。

控制器可选这两个非循环动作：idle→move-start→move，move→move-stop→idle。速度分别线性渐增/渐减，对时间分段作解析积分，跨过渡边界不丢剩余dt。短按可进入停步，再按可重入起步；攻击/受击可打断，跳跃沿原规则处理。缺过渡帧时兼容旧五动作包的直接切换。Node27项通过，新增过渡取消/重入以及一次大dt和多次小dt的位移一致性检查。

这张图的近臂较接近步行、远臂仍较接近守势；仅一个中点，不足以保证所有相位的腿部停步连续。浏览器观察工作台60ms单次末帧保持，消费示例自动进入move2/8、x398.3、root0。完整美术与移动端仍未批准。

## Godot 二维资源导出

已有 motion manifest 可直接转换为 SpriteFrames，不需要 GLB 或关节绑骨：

```bash
.venv-cutout/bin/python src/godot_sprite_export.py \
  --manifest output/mint-adventurer-collection-v8/bundle/manifest.json \
  --out output/my-godot-character-v1
godot --headless --path output/my-godot-character-v1 --editor --import
godot --headless --path output/my-godot-character-v1 --script validate.gd
```

用 Godot 打开输出 project.godot 即可预览，空格换动作、R重播、左右键翻转。接现有游戏时，只需把 hero_frames.tres 与 atlas.png 放在同一目录，给 AnimatedSprite2D 赋 sprite_frames，centered 保持 true，offset 使用 export.json 的 spriteOffset。纹理采用同目录相对引用；预览场景本身按独立项目的 res:// 根路径设计，不要直接搬到子目录后当作已接入游戏。

逐帧 durationMs 按 [Godot SpriteFrames 时长语义](https://docs.godotengine.org/en/stable/classes/class_spriteframes.html) 转为相对 duration，保持实际时间；loop 和完整帧矩形来自原包。原始 manifest/atlas 字节与 hash 保留，输出状态仍 draft。此导出不带 Canvas 控制器的呼吸、移动加减速、跳跃根位移或战斗逻辑，游戏按自己的物理与切换规则消费。

本轮未调用 GPT。v8 导出至 output/mint-adventurer-godot-v2，在 Godot 4.7.2 实际导入后通过 67 项原生检查：7动作、21帧的时长/矩形、循环、单次攻击结束、场景脚底 offset，以及 SpriteFrames/atlas 搬到项目子目录后加载。Python 3项通过，验证输入字节保留、越界图集拒绝与旧输出保护。详见 [原生检查记录](validation/godot-sprite-export-v1.md)。这些不是人眼步态、手机或完整游戏验收。

## 单相位摆腿修正（walk-fix-v8 / 集合v10）

第8帧旧图近似双脚接触地面，弱化了进入下一次前脚落地的摆腿过程。真实GPT调用1次，参考依次为现有接触帧、原步态第8帧草图、前一帧；提示词在 `input/codex/mint-adventurer-walk-fix-v8/actual-prompt.txt`。同一原图登记两版本：未配准最低脚底463，被拒绝；向下22px配准至485，头颈漂移导致整帧仍拒绝。完整记录在原任务 move-007 attempt-004/005，不是两次生图。

最终只从有效下半身取图：`lower-patch-plan-v2.json` 使用rectangle-patch、referenceImage指向旧第8帧、frameIndices=[7]、rect=[0,150,256,256]、feather=4（256cell像素）。矩形之外用旧帧；另外7帧保留输入像素。external reference必须同画布，不自动缩放；源路径与SHA记入provenance。选择接缝先看连接关系，不能拿像素范围测试代替视觉检查：y130方案有腕部接缝，y174方案割断大腿，均未用于最终v10。

`pixel-scope-check-v10.json` 证明7帧未改和第8帧y150上方未改。局部工具4项测试通过，新增外部参考/指定帧作用域的端到端检查。浏览器正常速度播放、定位0.760/0.800s第8帧，前脚离地；消费演示进入move3/8、x408.8，结束回idle、高度0、x374.9，无捕获JSerror。原始步态仍reject，源包/衍生包/游戏接受分别记录。[旧/新循环](validation/character-workbench-v1/walk-comparison-v10.gif)只由8张真实姿态按各100ms合成，不插帧，不计新增GPT原画。

## 落脚后停步（消费v11）

这套move的接触帧是零起始0/4，配置保存在 `input/codex/mint-adventurer-stop-options-v1.json`，不写入原画manifest：

```bash
.venv-cutout/bin/python examples/make_sprite_playground.py \
  --manifest output/mint-adventurer-collection-v10/bundle/manifest.json \
  --controller-options input/codex/mint-adventurer-stop-options-v1.json \
  --out output/my-stop-preview
```

配置 `{ "stopContactFrames":[0,4], "contactHoldMs":40 }`。松开时若已经在落脚帧，接停步；若在摆腿帧，保留当前原画剩余时间，顺序播放到最近接触帧，保持最多40ms，再接停步。运行时片段叫move-settle，复用原图坐标，不是新生成动作或像素插值。与位移分段积分一致地线性减速，停步图阶段速度0；短按起步取消也从当前速度减速，重新按住从当前速度回到走动，攻击/受击能打断。

本包落脚减速最多约340ms，另有80ms停步图；增加了一小段继续移动的距离，需在消费游戏按操作要求调节。其他角色必须先看近远腿落脚相位和姿态语义，不能默认使用0/4。没有提示时沿旧策略；提示必须为循环move中的不重复有效整数索引。当前仍共用一张停步图，落脚到共同中点、衣服比例仍可能跳变，不是完整连续动画。

渲染器用player.currentClip()读取运行时片段（原states里没有move-settle），已修正示例状态条，否则会读不存在动作导致播放中断。页面新增“停步演示”，从待机迈步后松开，便于反复观察。

本轮0 GPT调用。Node31项通过，含六个摆腿相位不立即切图、最近落脚选择、帧率位移一致性、重入速度连续、受击打断、短按减速与错误索引拒绝；Python消费导出3项通过。浏览器观察move-settle1/3，高度0，截图2/3，结束回idle；[动态图对照](validation/character-workbench-v1/stop-comparison-v11.gif)用同一v10图集隔20ms采样旧/新控制器，采样数量不是新增原画帧。

## 已有八帧图集的一致性编辑（torso-fix-v1 / 集合v12）

适用前提：已有近远腿相位基本正确、需要整套服饰比例修正。将已有八帧等画布原画组合为3x3透明编辑目标，最后一格空白，作为一个已有资产提交GPT编辑；不能把它等同从角色立绘直接稳定生成完整步态。请求只改衣领、躯干宽度、衣摆/腰带高度，保留相位与相机。实际模型仍重画了脸与腿部细节，因此保留旧图并重新检查，不能声称范围外像素相同。

材料与记录在 `input/codex/mint-adventurer-torso-fix-v1/`：edit-target-grid.png、actual-prompt.txt、generation-record.json（真实调用1次、参考顺序/sha）、source.png（原始1254方形结果）和明确3x3/418cell的source.json。第9格最大alpha1、没有alpha>128内容；红黄边缘最大alpha3，没有不透明彩边，未进行删色/去背处理。

选定八格经统一512画布缩放，各帧以已确认承重脚的最低不透明点作纵向平移-3..-5px至485；没有按bbox逐帧缩放、拆关节或添加插帧。registration.json记录每个格子的原始矩形、测量与位移。已保留registered-source.png/json和registered-recipe.json，可用现有加工入口复现导出：

```bash
.venv-cutout/bin/python src/asset_bundle.py \
  --recipe input/codex/mint-adventurer-torso-fix-v1/registered-recipe.json \
  --input input/codex/mint-adventurer-torso-fix-v1/registered-source.json \
  --aseprite --out output/my-torso-candidate
```

这组仍为8张不同RGBA原画、各100ms、800ms循环。pack-check.json校验帧数/时长/loop，视觉检查为代理候选改善，未批准整个角色。浏览器观察正常速度、6/8的衣领/衣摆与地面位置；新素材停步经过move-settle2/3、高度0、x409.2，结束idle、高度0、x413.3，无当前tab错误。本轮没有代码改动，未重复此前31 Node/3 Python测试；不能据素材替换宣称旧Godot验证覆盖新素材。[前后动态图](validation/character-workbench-v1/torso-comparison-v12.gif)仅采用8张真实原画和100ms时长。

## 出拳中间原画（attack-inbetween-v1 / 集合v13）

旧攻击三姿态110/80/140ms。新增屈肘前伸、折肘回收两种姿态；实际调用3次（前伸1、失败收拳1、局部修正收拳1），失败版不是第三张选定原画。第一张前伸幅度比提示词要求更大，但与伸直拳有明确肘部角度差；收拳修正使前拳仍在防守拳前方，避免提前进入紧凑守势。任务 `input/codex/mint-adventurer-attack-inbetween-v1/job.json`保留所有原始文件、提示词、真实按序参考、配准偏移与失败审查。它的attack-inbetween两姿态是材料，不是完整攻击动作。

为保住既有身份/脚底，最终仅采用明确区域的原画裁切：rect=[85,88,218,138]、feather=2，随后用原图覆盖保护框[0,0,163,100]（256cell像素）。单矩形y94方案会残留旧防守拳，y88方案会混入下巴，因此未采用。最终保护框和区域外RGBA与各自母版相同；下半身、脚底和大部分头部保持源图，接缝仍需看实际画面。没有旋转关节或时间淡入。

六帧顺序：旧蓄力70ms、前伸40ms、旧伸直拳80ms、回收45ms、旧收招35ms、旧idle60ms。共330ms，伸直拳仍从110到190ms。最后的idle是已有图复用，不新增生成帧，不加入游戏命中/伤害逻辑。旧参考3张攻击图与1张idle、原manifest字节和hash索引也随任务保存，复现不依赖旧output图片目录：

```bash
.venv-cutout/bin/python input/codex/mint-adventurer-attack-inbetween-v1/assemble_attack.py \
  --out output/my-six-pose-attack
```

脚本是本次明确裁切/时间编排示例，不能自动识别任意角色的保护框；其他角色需重新指定。原图与生成材料在任务里，输出source.png/json、recipe.json、processing.json及bundle。临时目录实际重建得到完全相同atlas字节；assembly-check.json记录7动作24帧位置/22不同RGBA姿态。

当前控制器直接加载实际v13素材，110ms为第3姿态、189ms仍第3、190ms进入第4，330ms返回idle；实际检查输出ACTUAL_ATTACK_TIMING_PASS。浏览器正常1×观察末段6/6，逐帧定位0.090/0.330s的2/6原画，可操作出拳后回idle、高度0、x380。当前是候选改善，完整美术/跳跃/战斗验收未完成；未重跑旧31项Node/3项Python或Godot原生检查。[前后动图](validation/character-workbench-v1/attack-comparison-v13.gif)按10ms采样真实原画，回收45ms边界显示最多有5ms采样差，采样数量不是生成帧数。

## 十相位跳跃候选 v14

`input/codex/mint-adventurer-jump-inbetween-v1/job/job.json` 保存4次真实调用的提示词、实际参考顺序、原始PNG与hash；两帧各第一个候选被拒绝：浅压缩画得更深、半收腿接近完整收腿。选定第二个候选作为整张原画，不裁切关节、不旋转部件。生成提示词中的坐标是约束目标，不保证模型逐像素满足。

组合顺序为浅压缩40、旧压缩40、旧蹬离60、新半收腿40、旧空中80、复用半收腿40、旧下降40、复用旧压缩40、复用浅压缩30、复用idle30ms。340ms落地后沿两级压缩恢复，410ms已显示真实idle，440ms控制器结束。10播放位置不是10次GPT生成，也不是10张不同原画；半收腿沿上升/下降反向复用未表现独立惯性，仍为候选。

复现素材（从仓库根执行）：

```bash
.venv-cutout/bin/python input/codex/mint-adventurer-jump-inbetween-v1/assemble_jump.py --out output/my-jump-candidate
.venv-cutout/bin/python src/motion_collection.py --config input/codex/mint-adventurer-collection-v14.json --out output/my-collection
```

旧原画副本与hash索引一起存于该任务目录；脚本校验旧原画和选定帧来源，不依赖原来的临时输出生成新姿态。当前候选atlas从这些材料重建后字节一致。实际SpriteController检查80ms根高度0、210ms=-40、340ms=0、440ms回idle，落地原画在340/380/410ms依次为第8/9/10帧。

正常速度对照GIF `docs/validation/character-workbench-v1/jump-comparison-v14.gif` 采用实际控制器每10ms采样的源帧与整体位移，包含1秒idle停顿；采样帧不是额外原画。浏览器工作台实际停在0.350s第8/10帧、预览高度0，截图 `jump-landing-v14.png`。消费页面点击跳跃后观察到空中第5/10帧及结束idle；无当前页面JS错误。静态截图、计时断言与浏览器示例均不代替正常速度美术批准或正式游戏测试。

## 通用原画编排命令与受击 v15

已有加工动作包不需要角色专用Python脚本才能重新编排：`src/motion_sequence.py` 读取显式配置，跨动作选取已有完整帧、复用与改时长，不自动生成或插值。输入必须是可读motion manifest、透明atlas、兼容画布与anchor。先通过GPT生成/导入/选定/pack获得新原画包，再用本命令拼动作；整套动作仍用motion_collection合并。

```bash
.venv-cutout/bin/python src/motion_sequence.py --config input/codex/mint-adventurer-hit-sequence-v1.json --out output/my-hit-sequence
```

配置的`inputs`为manifest列表，路径相对配置文件；`states`含name、显式loop和非空frames。每个frame含input（零起始输入索引）、action（源动作名）、frame（零起始源帧索引）、可选durationMs。不传时长则保留源时长；传入需正有限数。允许重复引用同一原画，拒绝越界/不存在动作/画布或anchor不兼容；不逐帧缩放。输出存在则拒绝覆盖，失败不发布半包。

输出bundle/manifest.json、atlas、透明帧、Aseprite和预览；inputs下原manifest字节、atlas副本和上游审查/processing副本保留hash；provenance列出每个输出帧的源input/action/frame、源时长与新时长。编排imageGenerationCalls=0，源任务真实GPT调用另行保留，不能把原画复用计入新生成；上游审查不会批准新编排。

本轮 `input/codex/mint-adventurer-hit-recovery-v1/job/job.json` 有一次实际GPT调用，选用完整恢复原画；源靴底约483，显式下移2px到485。三姿态选择旧hit80、新recovery50、旧idle30ms，按 `input/codex/mint-adventurer-hit-sequence-v1.json` 导出到 `output/mint-adventurer-hit-three-v1/`。实际控制器检查0/79ms旧hit，80/129ms恢复，130/159ms原idle，160ms状态idle且高度0；无新增受击延迟。

4项通用编排测试通过（含多个无效输入子场景），覆盖逐帧RGBA/半透明边缘不变、时长/循环/来源审查、搬迁后离开源包仍可读、源文件不变、覆盖与非法输入拒绝。实际候选重复编排atlas字节一致。工作台检查0.100/0.160s第2/3帧，截图hit-recovery-v15.png；消费示例点击受击后已回idle/高度0，当前页面JS错误为空。新旧GIF hit-comparison-v15.gif采用10ms源帧采样，不增加原画数量。未重跑其他历史套件或新Godot导入，未获得整套美术与游戏验收。

## v16 跨动作头部参考复用

一次GPT逐帧/图集生成可能改动眼睛、发型轮廓，动作切换时出现轻微身份跳变。此候选复用已有idle母版头部到move、move-start、move-stop，不新增GPT调用。来源`input/codex/mint-adventurer-head-consistency-v1/idle-master.png`，显式同画布加工`head-reference.png`；reference-processing.json保留源hash、清除矩形[159,89,256,100]与原因：护脸拳进入头颈接缝，不能把它一起贴到走路图中。该坐标只适用此角色/朝向，不能作为其他角色自动规则。

`motion_region_lock.py`的upper-region现支持referenceImage指定同完整画布PNG，与rectangle-patch相同，拒绝尺寸不兼容，不自动缩放。裁切99cell px、5px接缝带；move头部偏移[0,1,0,-1,0,1,0,-1]，起停[0]，人工设置小幅起伏，不是关节绑定或物理高度。偏移后的参考轮廓越界会拒绝；接缝以下直接保留源RGBA字节，包括透明像素的隐藏RGB。PNG无anchor元数据，因此仍需操作者确认同角色、同相机与同画布登记；工具不会识别脸或手。

```bash
.venv-cutout/bin/python src/motion_region_lock.py --plan input/codex/mint-adventurer-head-move-plan-v1.json --out output/my-head-move
.venv-cutout/bin/python src/motion_region_lock.py --plan input/codex/mint-adventurer-head-move-start-plan-v1.json --out output/my-head-start
.venv-cutout/bin/python src/motion_region_lock.py --plan input/codex/mint-adventurer-head-move-stop-plan-v1.json --out output/my-head-stop
```

该操作导出完整透明帧，运行时仍播原画，不逐关节变换。三个动作重建atlas字节一致，接缝以下源像素逐帧相等，时长/循环保留。5项区域加工测试通过（新增外部upper参考、身体隐藏RGB、时长/循环和外部参考裁切越界检查）。实际控制器20ms采样新旧版本，action/帧索引/x/y完全相同并最终idle。动态图identity-comparison-v16.gif为跟随角色的固定镜头姿态对照，包含起步、走路、落脚收步、停步和idle；采样不是新增原画。

浏览器工作台检查move0.020/0.800s第1/8帧，截图identity-move-v16.png；消费示例停步演示先move2/8后idle、根高度0、x413.3，当前页面JS错误为空。未重跑所有历史测试或Godot导入，不代表用户批准完整步态、全部跨动作或正式游戏。

## 一条命令生成验收交付站

素材制作/审核选帧完成后，使用通用静态交付命令；它不调用GPT，不是可远程触发宿主生图的后台。

```bash
.venv-cutout/bin/python src/motion_preview_site.py --manifest output/mint-adventurer-collection-v16/bundle/manifest.json --controller-options input/codex/mint-adventurer-stop-options-v1.json --out output/my-motion-site
.venv-cutout/bin/python -m http.server 8770 --bind 127.0.0.1 --directory output/my-motion-site
```

输出首页列真实动作数、播放位置、duration/loop/anchor及素材要求，提供workbench、playable、Godot资源预览和3个ZIP。通用输入为具有idle/move/attack/hit/jump五动作的motion manifest与atlas；attack/hit/jump及起停过渡需非循环。工作台和试玩共用显式起落配置；默认80/340ms、高度40素材px，其他原画节奏用controller-options传launchMs/landMs/jumpHeight，停步落脚需自行确认索引。短于落地窗口、无效速度/呼吸/落脚配置会拒绝并不发布半包；跳跃预览高度受工作台画布限制（不超过cell高度一半），不能静默缩放。

material/bundle的manifest与atlas保持源字节，散帧按实际atlas矩形导出，不算新原画；material/inputs携带现有来源审查副本（若存在）。完整GPT原始任务/提示词仍在生产工作区，不声称ZIP包含全部生成任务。Web试玩复制manifest时可能格式化JSON和归一atlas路径，保留字段、时长、loop和anchor；下载Web示例同时带工作台并使用包内返回链接。Godot ZIP包含独立导入/动作播放预览，未自动接入正式游戏物理或战斗。

4项交付站测试通过，覆盖原始素材hash、ZIP完整性/像素、搬迁离开输入目录后可读、HTML转义、下载Web导航、拒绝覆盖/缺动作/短跳跃/非法消费参数；当前7动作31位置Godot4.7.2导入成功并实际校验86项。下载Godot ZIP的atlas/tres/脚本/source-manifest与引擎已检验文件字节一致。当前根入口浏览器实际跳至current-v16/，试玩返回正确workbench，跳跃0.210/0.440s第5/10帧高度40，错误列表为空。证据delivery-site-v16.png/json。整套美术、正式游戏、设备与玩家验收仍未完成。

## v17 恢复实际摆臂周期（2026-10-03）

4次真实GPT调用保留原始提示词、真实参考顺序与失败版本；选2张局部手臂来源，整帧改动了脸、服饰与腿，因此整帧review为reject。前摆接触姿态复用旧v5原画，不算新生成。

`motion_sequence.py`编排旧后摆、新下垂、新半前摆、旧完整前摆，再回到下垂/后摆。`motion_region_lock.py`新增rectangle-patch的referenceManifest/referenceAction：按索引复用对应旧底图，校验帧数、画布、anchor、loop和每帧时长相同。protectedRects恢复原图小范围细节。不能把一个固定身体覆盖整个周期。

本角色显式ROI为[78,104,202,169]、feather2、保护[134,94,160,114]，仅处理相位2/3/4/5/6；坐标不是通用语义识别。矩形外、保护区及未处理相位字节保持旧v16一致。输入为mint-adventurer-arm-sequence-v1.json与mint-adventurer-arm-patch-plan-v1.json，输出arm-cycle-v1后组合collection-v17。

6项区域加工测试通过，素材重建atlas字节一致；真实Godot导入及86检查/7动画通过，3ZIP完整性通过。浏览器工作台定位440ms第5/8帧；停步演示最终idle、x413.3且未捕获JS错误。这些证明输出与消费路径工作，不批准美术连续性。共享停步手臂仍需按落脚相位调整。

## 按落脚选择停步片段

SpriteController可传stopClipsByContact对象，key为已配置stopContactFrames索引，value为manifest存在的非循环停步动作名。提前松开时先沿move-settle到该接触，再播放对应片段。短按起步无落脚相位，回退共同move-stop；未映射相位也回退。当前状态名仍move-stop，通过currentClip()读真实片段，位移坡度使用该片段实际时长，重入/受击可以打断。

导出站与控制器均拒绝缺失、循环、核心动作及非落脚索引映射；交付ZIP保留配置。该功能已实现和测试，当前v17素材尚无新前摆停步原画，默认入口仍用原配置，不能声称实际停步视觉问题已经修复。

## v18 两种停步原画与接入

前摆停步55/55/30ms，后摆停步40/45/45/30ms。旧完整前摆停步候选可仅作为第一帧局部来源，新增屈肘回收为另一局部来源；任务累计2调用，本轮新增1调用。旧下垂姿态复用于后摆恢复。整帧均reject，明确ROI[78,104,202,169]、保护[134,94,160,114]，对应旧底图范围外与末帧idle字节保持一致。前/后序列、底图与patch计划均为input/codex中stop-front/back-*-v1.json，使用通用工具复现。

配置stop-options-v2.json的映射0→move-stop、4→stop-front。真实集合控制器核对直接落脚和中途松开共4路径，均选择对应图并最终idle。浏览器停步演示结束idle/根高度0/x413.3，无捕获错误；工作台定位70ms第2/3帧截图contact-stop-v18.png。3ZIP完整性通过。仍draft，检查不证明完整游戏/移动端/美术批准。

最新Godot4.7.2真实导入通过，GODOT_SPRITE_EXPORT_PASS checks=101 animations=8；默认根入口浏览器确认current-v18。前摆停步正常1×重播结束140ms第3/3帧。

## v19 四姿态起步及短按取消

材料：half-back-v1/job保存实际提示词、参考顺序、原始1254方图与512归一化画布（0偏移）。裁切继续ROI[78,104,202,169]与保护[134,94,160,114]；非区域字节保留对应旧底图。stop-back-v2序列/底图/patch计划生成五帧停步；start-sequence-v2反向复用前三帧，再接完整真实move首帧，4×25ms。半后摆近手仅稍收，远手下降更多，不声称精确命中提示坐标。

SpriteController新增可选reverseStartOnRelease。多帧起步取消时先保留当前原画，反向已播放片段（首帧采用已消耗时长），末帧复用idle并保持contactHoldMs以内；用当前速度减速，允许重入或受击打断。不会使用尚未走过的后摆姿态，不生成插画。消费导出保存配置，非布尔值拒绝；渲染继续currentClip()。

37项Node、5项交付站和3项示例测试通过。真实集合4个短按相位、4个落脚路径通过；首次脚本误比较durationMs失败（取消片段本来改时长），修正为检查实际图集矩形后通过。起步末帧/move首帧RGBA相同，3ZIP完整性通过。浏览器65ms/3帧截图start-transition-v19.png；stop demo最终idle/高度0/x413.3，无捕获错误。整套仍draft。

Godot4.7.2真实导入与109检查/8动画通过。浏览器默认根入口确认current-v19，起步正常1×重播100ms第4/4帧结束。

## v20 跳跃首帧身份及工具入口

静态首尾检查确认attack/hit/jump/两种stop末帧都与idle完全相同。首次检查脚本对jump首帧相同的假设失败，核对有13928个可见像素不同：站立姿态是另一张重画。使用jump-entry-sequence-v1.json将第一帧换成真实idle，保留40ms，其余9帧/总440ms/loop和起落配置不变。0次新GPT调用，输出collection-v20，所有其他动作RGBA不变。

全量69项Python测试通过。二维检查记录已修正为实际0ms切原画，而非模型180ms淡入；旧19-toolkit网页记录已确认八动作全部访问且blendMs为0。材料入口与旧绿幕流程冲突已修正。新版三ZIP完整性通过，仍按目标游戏验收后采用正式资产。

最新v20真实Godot导入/109检查/8动画通过；浏览器八动作正常1×巡演与0ms二维切换记录保存。下一项检查为步行承重脚与场景移动速度匹配，当前尚未把整套视觉/正式游戏升级为通过。

## v23 裁切范围修复

v22截图暴露新帧旁残留一小块旧靴子：ROI左边74没有覆盖原鞋最左轮廓。v23用同一GPT来源，将两张补帧ROI改为 `[60,174,222,256]`，没有再次生图。原八帧与其他动作RGBA/时长/loop保持原样；新增区域外精确保留对应旧上身。仍10帧800ms，43播放位置30张不同RGBA。两张相位浏览器定位150/550ms验证，试玩载入idle；v22停步验证保留其原版本范围，本版本未重跑Godot。

当前验收页 `http://127.0.0.1:8770/compare-tool-v4/`，试玩 `http://127.0.0.1:8770/candidate-v23/playable/`，完整下载 `http://127.0.0.1:8770/candidate-v23/`。证据为walk-v23-proof.json、walk-v23-browser.png、walk-v23-comparison.gif；依然候选，不能由增加帧数宣称整体观感通过。

## v22 步行压低到经过补帧

新增3次真实内置GPT调用：第一半周期一张，另一半周期两次尝试，第一次直接跨到经过而拒绝。两张有效下身来源经过明确区域 `[74,174,222,256]` 加工，上身复用对应旧压低原画；生成整帧因身份重画仍reject，局部采用不能登记为整帧通过。第一原图登记两次只为比较offset，实际仅一次调用；最终512画布偏移 `[0,4]`、`[0,-1]` 对齐地面。第二来源脚位没有精确达到提示坐标，不宣称物理支撑点已匹配。

`mint-adventurer-walk-ten-sequence-v1.json` 将原索引1/5的100ms拆为原50ms＋新50ms；其余原姿态及时间不变。move从8到10张，仍800ms；其他动作RGBA/时长/loop未改。v22整套8动作43播放位置。新接触索引为0/5，控制器选项v4同步改为后摆/前摆停步；实际manifest的两种停步路径回到idle。默认下载仍v20，v22是候选。

同步比较 `http://127.0.0.1:8770/compare-tool-v3/`，移动试玩 `http://127.0.0.1:8770/candidate-v22/playable/`。通用比较工具新增毫秒滑块，可定位旧版没有的中间时间点；保持各自真实duration。浏览器验证150ms两侧2/3、550ms两侧6/8，1×正常播放，停步演示结束idle、y=0、x=413.3，没有捕获JS错误。77项Python套件是上一轮结果；本轮比较模块3项复跑通过，实际素材像素/时长与控制器另验，未重跑本版本Godot或做正式游戏/美术验收。

证据 `docs/validation/character-workbench-v1/walk-v22-proof.json`、`walk-v22-controller.json`、`walk-v22-browser.png`。`walk-v22-comparison.gif` 只是两个实际图集的同步展示，50/100ms精确编码合计800ms，不是新GPT帧或插值。浏览器标签保留标记被自动审批拒绝后未重试；截图和只读/播放检查已用不含标记的操作完成，页面仍可经链接打开。整体步态观感、脚掌滚动与消费端速度仍待视觉验收。

## v21 承重腿候选与步态诊断

后续支撑后段尝试：`input/codex/mint-adventurer-support-return-v1/job/` 只有phase6实际调用一次，phase7虽有计划和提示词但未执行。候选没有达到脚底目标位置，并重画上身造成水平接缝，review=reject、selected=null，未局部使用也未合入集合。不要将准备两帧登记为两次生成，不用模型画面尺寸或輪廓RMS替代姿态语义。

同步对比已抽为通用 `src/motion_compare.py`，独立复制两份真实图集、记录SHA，保留不等duration与不同帧数；非方形画布等比显示。要求同画布/anchor/循环总时长，禁止覆盖，输出原子发布。输入示例 `input/codex/mint-adventurer-compare-v1.json`，本地工具验收 `http://127.0.0.1:8770/compare-tool-v1/`。新增3项测试覆盖不同帧数/时长、便携原图与HTML转义、拒绝错相循环/锚点/缺项；全部Python unittest77项通过。浏览器确认700ms两侧8/8、100ms两侧2/2、正常速度播放与没有捕获JS错误。素材质量仍待验收。

新增一次真实宿主 GPT 生图，任务在 `input/codex/mint-adventurer-down-foot-v1/job/`。原始结果重画服饰、脚部回收过多，整帧已记录 reject。导入时显式使用512画布偏移 `[20,0]`，只将右腿来源区域 `[140,178,224,256]`（256 cell）合入 move 第2张原画；不是第二次生成，也不是整帧通过。其他原画、时长与循环属性经像素检查保持原样。

`output/mint-adventurer-collection-v21/` 是待验收候选，默认下载入口仍为 v20。对比入口 `http://127.0.0.1:8770/walk-review-v21/` 两版共用播放时钟，支持1×/0.5×和修正帧定位。候选可以进入整套工作台与移动试玩，但未做正式游戏、美术或本版本Godot运行验收。

通用诊断命令：

```bash
.venv-cutout/bin/python src/motion_stride_review.py \
  --config input/codex/mint-adventurer-stride-review-v3.json \
  --out output/new-stride-check
```

该配置作者手动指定脚底范围和支撑组；contact-region只取区域内最下两行alpha>=128的像素中心，不是固定骨骼点。90px/s下，本候选第一组轮廓标记范围从15.87降到7.59px，第二组仍为19.52px。数字只能定位问题，不能证明没有滑步。`direction`描述源图朝向，`renderScale`换算场景尺寸；拟合速度不自动写回控制器，不覆盖加减速、镜像与跳跃。

完整 Python unittest 本轮74项通过，新增5项覆盖不等时长、方向/缩放、乱序标记、空区域和非法输入。浏览器确认对比素材载入、同帧定位及诊断滑块90→130→90。证据见 `docs/validation/character-workbench-v1/walk-candidate-v21.json`，整体视觉仍待验收。
