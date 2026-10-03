# 角色动作工作台首版验收

日期：2026-10-02。产物：`output/character-workbench-v1/workbench`；本机预览 `http://127.0.0.1:8770/`。本次未写回 Frontier，也未提交或推送。

## 最新试点：关节版拒绝，完整原画待验收

本地 8770 已切到 `output/mint-adventurer-fullframe-v4/viewer`。v3 六部件二维 IK 的 48 帧连续轨迹被用户拒绝：关节和遮挡的机械感仍明显。v4 实际完整绘制十二姿态，再做一次皮肤色定向清理；没有 GLB、视频生成、光流插帧或源帧淡入。

v4 导入修正实际不均匀行距，显式脚底锚点平移配准，不逐帧缩放。12 帧 / 800ms。膝肘硬切接缝消失，但身体/服饰轮廓仍有漂移，腿身份和完整步态尚未可靠确认，**未通过正式动作验收**。该版提供给用户做方向验收；仍缺 idle / attack / hit / jump。

当前实际回归：Python 33 项、Node 18 项通过。cutout 的 6 项仅证明轨迹连续、骨长与导出合同，不证明生成画面正确。v4 成功构建完整包；report `needs-human-review`，没有裁切边界警告。GIF 12 帧合计 800ms；WebP 与图集保留 66/67ms 的逐帧时间。

浏览器确认默认完整原画 v4、0.000s 第 1/12、0.400s 第 7/12，前进一帧到 0.467s 第 8/12，以及 0.5× / 1× 和新旧版对照。见[首个接触姿态](character-workbench-v1/fullframe-v4-contact-near.png)、[半周期姿态](character-workbench-v1/fullframe-v4-contact-far.png)。本轮未改前端动画算法，也未替换游戏或提交。

## 此前八帧样片

当时服务切到 `output/mint-adventurer-pilot-v1/viewer`。三次内置 imagegen 调用产生参考图、步态 v1、一次定向修正 v2。两版步態仍缺可靠左右腿交替，**拒绝作为正式动作**；预览中明确显示失败与动作缺项，未修改游戏。

新增 `reviewNotes` 传递人工失败原因，工作台定向 Python 检查 8 项通过；新增样片脚本与构建模块语法检查、`git diff --check` 通过。浏览器确认默认 v2、暂停、逐帧从原画 3/8 到 4/8，以及失败说明可见。见[完整样片页面](character-workbench-v1/anime-pilot-v2.jpg)。此轮未修改前端动画代码，未重新执行早期 Blender/Node 全套检查。

新增 X 参考视频实际播放成功，约 9 秒、720×1078、八方向同时展示。已观察不同时间画面，[页面证据](character-workbench-v1/latest-sprite-gen-post.jpg)。未下载远程媒体，未测得视频帧率或循环接缝误差。

此前二维主线修正：服务当时指向 `output/character-workbench-2d-v1/viewer-checked`，默认显示 Frontier 二维图集；模型入口折叠，三维模块按需加载。默认示例改成二维，模型库由 `--models` 显式加入。该轮 Node 18 项、Python 26 项通过。浏览器确认 `slash2` 原画 2/4，见 [二维首屏](character-workbench-v1/2d-default.jpg)；初始 HTTP 请求只有页面、main/motion 和配置，不加载 three.js。

## 自动检查

| 检查 | 结果 |
|---|---|
| Python 素材及工作台回归 | 26 项通过，覆盖时长、loop、无效 GLB、外部 URI 拒绝、帧越界、缺项计划、失败不发布与不覆盖 |
| Node 动画测试 | 17 项通过，覆盖 12 动作全身采样、非均匀时长、插值不超调、周期接缝速度、旋转顺序与最短弧 |
| 原动作库校验 | 双足 8 + 四足 4 动作通过 |
| Blender 5.2 实际导出 | `move`，11 网格部件合并为 1 条 Scene 动画，导出成功 |
| GLB 与原动作库对照 | 43 个关键帧通过；使用现有 `verify_rig_export.verify`，24fps，角度容差 1 度 |
| Skill 校验 | `quick_validate.py` 通过；校验用 PyYAML 安装在现有虚拟环境中 |
| 文件检查 | Python 编译、Node 语法、`git diff --check` 通过 |

## 桌面浏览器走查

通过 Codex 内嵌浏览器实际操作，并保存可见页面证据：

- 双足整套巡演多轮；[检查记录](character-workbench-v1/review.json) 实际包含全部 8 个动作，单次动作与循环动作均出现。
- 双足快速 `slash2 → dash → hit → move` 打断、暂停；[画面](character-workbench-v1/humanoid.jpg)。
- 四足 `pounce`、暂停与部件层级显示；[画面](character-workbench-v1/quadruped.jpg)。
- Frontier `slash2` 逐帧到 2/4；显示六个源动作以及五个真实缺项；[画面](character-workbench-v1/frontier.jpg)。
- GLB 实际加载、循环、暂停、逐帧；[画面](character-workbench-v1/glb.jpg)。另通过文件选择器打开本地 GLB，开启循环，切到其他模型后再切回仍可播放。
- 浏览器未捕获 JavaScript error。旧 shadow 类型的弃用提示已改用当前 PCFShadowMap。
- 检查记录可生成并从可见文本保存。内嵌浏览器没有返回 blob 链接的下载完成事件，未认定“文件下载已完成”；页面提供真实保存链接和可复制 JSON 作为交付入口。

## 已知边界

盒子模型是部件动作管线验证件。此次仅实际验证了一个 Blender 导出的 GLB 动作，没有以此声称任意第三方蒙皮模型、多动画混合或跨骨架重定向都已验证。动画采样的连续性也不等于步态美术、脚掌接触或玩家手感已经通过验收。

Frontier 源图预览均分四张原画，不执行 Godot 中的阶段采样、重心形变、跳跃高度、命中或取消窗口；五个缺失动作只是待生成计划。这次没有调用生成 API、安装上游 sprite-gen 或替换正式角色资产。

移动设备、目标游戏接入、新美术一致性仍需对应场景的后续验收。

## 2026-10-03 GPT 单帧 v5 更新

实际内置生图 11 次，八帧、800ms，重画承重和接缝前相位。当前包 `output/mint-adventurer-singleframe-v5-repaired/`；[材料与步骤](../GPT_MOTION_GENERATION.md)。Python 41、Node 18 通过，版本化模块/配置回归通过；浏览器已确认 1/1.5 倍实际显示变化、播放/暂停与逐帧定位。[浏览器证据](character-workbench-v1/singleframe-v5-repaired.png)。

未通过整体视觉验收：脸型、衣服和身体高度仍变化，远侧承重与经过较接近。未接入正式游戏。前文“没有调用生成 API”仅描述此前工作台构建轮次，本轮确实调用了内置生图。

## 2026-10-03 固定头部衍生对照

新增显式原画区域复用命令，该轮服务指向 `output/mint-adventurer-singleframe-v5-head-lock/viewer`。头部只来自同一原画，身体/肢体仍为真实 GPT 八帧。无新生图调用。浏览器检查了第 5/8 帧及倍率，衣领连接未见明显断层；[证据](character-workbench-v1/head-lock-v5.png)。躯干衣服变化和完整步态仍待优化，尚未集成游戏。Python 43 项通过。

## 2026-10-03 待机/攻击与动作集合

实际4次生图产出静态idle1帧、attack3帧110/80/140ms。合并v6 move8帧，该轮服务指向 `output/mint-adventurer-collection-v2/viewer`。来源原manifest/atlas与审查副本保留，三动作共12源帧；集合仍draft。浏览器attack末帧3/3保持，开启回idle后显示idle；[出拳证据](character-workbench-v1/collection-attack-v1.png)。单个攻击经代理预览检查，未批准整套、用户美术或游戏接入。仍缺hit/jump/呼吸与完整一致性。Python49项通过，包括时长/loop/alpha保留、搬动集合后来源可读、原始manifest校验及失败不发布。

## 2026-10-03 五动作与跳跃位移预览

新增5次GPT调用，受击1张、跳跃3张选定原画，失败落地图保留。五动作16源帧，该轮服务为 `output/mint-adventurer-collection-v3/viewer`。跳跃整体位移为预览曲线40素材画布px、100..320ms，不写回素材manifest。浏览器[顶点](character-workbench-v1/collection-jump-v3.png)、[落地](character-workbench-v1/collection-land-v3.png)、[受击](character-workbench-v1/collection-hit-v3.png)已观察；开启回idle成功。原画只有3姿态，起跳压缩较大，过渡/全套一致性/idle呼吸与游戏验证仍待完成。Python50、Node19通过，不是FPS或完整美术接受。

## 2026-10-03 起跳过渡 v4

新增1次真实GPT生图，复用三张已有原画，jump4张80/60/180/120ms，共17源帧。该轮服务为 `output/mint-adventurer-collection-v4/viewer`。浏览器已定位2/4原画，0.111s预览高度18.2素材px；[起跳证据](character-workbench-v1/collection-takeoff-v4.png)。仍有准备姿态高度变化和收腿到落地跳变，候选未通过完整视觉验收。

## 2026-10-03 五相位跳跃 v5

本轮实际新增2次GPT调用，准备修正/下降过渡，3张复用。18源帧，jump5张440ms。该轮服务为 `output/mint-adventurer-collection-v5/viewer`；浏览器正常速度观察0.215s原画3/5高度39.9、终点5/5高度0。[下降姿态证据](character-workbench-v1/collection-descent-v5.png)。准备下压减轻但未达提示词要求，未通过完整美术或游戏接受。本轮仅素材/配置变更，未重复运行此前50 Python/19 Node测试。

## 2026-10-03 步行v7与消费示例

实际局部生图2次修正承重相位服饰，8帧800ms保留；完整步态仍reject。当前服务 `output/mint-adventurer-collection-v6/viewer`，`/playable/`为可操作Canvas。浏览器[走动](character-workbench-v1/playable-move-v6.png)观察原画3/8、x401，[跳跃](character-workbench-v1/playable-jump-v6.png)观察3/5高度38.7；自动演示结束idle、出拳3/3，未捕获JSerror。Node24项/Python消费示例3项通过；此前Python50项本轮未重复。未证明连续键盘按住、手机触摸、完整战斗或美术通过。

## 2026-10-03 眨眼与呼吸v7

真实GPT生图1次，眼部裁切后19源帧。idle2姿态3110/90ms。当前服务 `output/mint-adventurer-collection-v7/viewer`，工作台[闭眼2/2](character-workbench-v1/idle-blink-v7.png)，可操作端[呼吸](character-workbench-v1/idle-breath-v7.png)观察idle倍率1.0044、高度0，出拳回倍率1。矩形外RGBA一致；呼吸是0.6%整帧缩放而非新原画。Node25项/Python局部复用3项通过（旧路径回归及矩形范围）；非完整游戏/美术接受。

## 2026-10-03 起停过渡v8

本轮1次GPT生成中间姿态，复用为60ms起步/80ms停步，21帧位置/20不同RGBA图。当前服务 `output/mint-adventurer-collection-v8/viewer`。工作台[起步](character-workbench-v1/move-start-v8.png)观察1/1、60ms末帧，消费示例自动进入move2/8、x398.3、root0、呼吸1。Node27项通过，含短按取消/重入、攻击打断和跨过渡边界积分。单中点未覆盖所有腿部相位，美术/手机/完整游戏未通过。

## 2026-10-03 循环末尾摆腿 v10

真实GPT调用1次，修正第8帧前脚离地。原图与脚底下移22px版本登记为move-007 attempt-004/005；整帧因配准/头颈漂移拒绝。显式旧上身复用的y130和y174方案分别出现腕部接缝和大腿断层，v9未作为最终候选。v10采用y150下半身矩形/4px羽化，保留另外7帧和第8帧矩形外像素；证明见 `input/codex/mint-adventurer-walk-fix-v8/pixel-scope-check-v10.json`。

服务现为 `output/mint-adventurer-collection-v10/viewer`。浏览器观察正常1×循环，第8帧0.760/0.800s的[完整画面](character-workbench-v1/move-swing-v10.png)前脚离地；可操作端自动进入move3/8、x408.8，再回idle、高度0、x374.9，未捕获JSerror。此轮局部工具Python4项通过，未重复其他Python/Node或Godot验证。源完整循环仍reject，躯干变化、任意相位停步与完整美术仍待完善。[八帧前后对照](character-workbench-v1/walk-comparison-v10.gif)保留100ms真实帧时长，不插帧。

## 2026-10-03 落脚停步消费v11

素材保持v10，无GPT调用。新增控制器可选落脚索引0/4、保持40ms；释放摆腿时复用原画剩余相位直到落脚，再接80ms停步图。落脚减速最长约340ms，位移比立即停多一小段。短按/重入使用当前速度，修复取消起步时突然从满速减速的问题。

Node31项全部通过，新增6摆腿相位、落脚索引、不同dt位移、打断、速度连续与配置拒绝检查；Python消费导出3项通过。`/playable-v11/` 浏览器观察move-settle1/3、x407.1，第二次演示截图[2/3、x446.0、高度0](character-workbench-v1/stop-playable-v11.png)。渲染状态条使用currentClip()，运行时片段不从原states查询。最终实际读取idle1/2、高度0、x446.6、呼吸1.0028。

首次消费试跑记录到读取undefined.frames错误（2026-10-03T04:15:59.409Z），原因正是状态条查询原states中的运行时片段。修复为currentClip()后重新加载，两次停步都实际经过move-settle并回idle；该tab日志仍保留修复前的一条错误，未出现第二条。本轮未进行手机/完整战斗/美术批准。

[停步前后动图](character-workbench-v1/stop-comparison-v11.gif)使用同一真实v10素材、两版本控制器，20ms显示采样；对应JSON为 `input/codex/mint-adventurer-stop-runtime-v1.json`。旧控制器松开立即move-stop；新控制器先move-settle，约190ms后move-stop，再回idle。完整躯干/服饰一致性及落脚到共同停步图的美术衔接仍未通过。

## 2026-10-03 躯干一致性编辑v12

1次实际GPT调用编辑已有八帧3x3透明目标，不是8次生成。source.png原始1254x1254，3x3各418px；空格无不透明角色，alpha最大1，红黄色边缘alpha最大3（非不透明色边）。模型重画全部细节，八个定性步态相位保留，不能声称像素或关节位置不变。

统一画布512缩放，承重脚底注册至485，各帧平移-3..-5px；原格子矩形/偏移/原始hash/实际提示词与参考顺序在 `input/codex/mint-adventurer-torso-fix-v1/`。保留raw、注册后的完整原画与明确Aseprite输入。8帧800ms循环，7动作集合仍draft。

浏览器 `/torso-v12/viewer/` 正常速度观察步行，并定位6/8、0.560/0.800s的[完整衣领/衣摆画面](character-workbench-v1/torso-consistency-v12.png)。角色菜单提供旧v10；可操作示例使用新素材和v11停步，观察move-settle2/3、高度0、x409.2，最终idle1/2、高度0、x413.3，当前tab未捕获错误。[动态图对照](character-workbench-v1/torso-comparison-v12.gif)保留原100ms，不插帧。

代理结论是候选的服饰一致性改善；跨动作身份、待机/攻击到步行、共同停步图的连接与完整游戏验收仍待完成。本轮素材/文档变更，无代码变更，未重复旧31 Node/3 Python或Godot检查。

## 2026-10-03 六姿态出拳v13

实际GPT调用3次，前伸1、失败收拳1、针对前拳修正1；选2张新原画。任务所有实际参考/提示词/hash/原始版本保留。两张采用显式手臂区域裁切并保护母版头部框，矩形外和保护框字节不变。y94单矩形留下旧拳、y88未保护框会混入下巴，均未采用；最终参考图与本次复现脚本随input任务保存。

输出六姿态70/40/80/45/35/60ms，非循环330ms；伸直拳110..190ms不变，末帧复用idle。临时目录重建与输出atlas字节相同；7动作24帧位置、22不同RGBA姿态。实际控制器检查110/189ms为伸直拳、190ms进入回收、330ms返回idle，ACTUAL_ATTACK_TIMING_PASS。这个检查不证明游戏命中窗口或视觉批准。

当前浏览器 `/attack-v13/viewer/` 正常1×观察6/6末段，冻结到0.090/0.330s、2/6的[中间姿态](character-workbench-v1/attack-inbetween-v13.png)。消费示例出拳后回idle1/2、高度0、x380；来源pose间的肩部/保护框接缝、跳跃与跨动作仍待完整美术/游戏检查。[动态对照](character-workbench-v1/attack-comparison-v13.gif)是10ms采样原画，非新生成帧；45ms边界有至多5ms显示采样误差。本轮未重复此前31项Node/3项Python或Godot检查。

## v14 整帧跳跃与落地恢复（2026-10-03）

4次真实GPT调用，2张选定，2张失败保留。最新集合7动作29帧位置23不同RGBA图，draft。跳跃10位置/7原画，40/40/60/40/80/40/40/40/30/30ms，总440ms；80..340ms整体位移不变。压缩原画复用于落地，浅压缩随后接真实idle，不把复用当新增绘制。

实际控制器窗口/高度检查通过，素材从保存输入重建atlas字节一致。工作台正常速度重播结束0.440s第10/10帧；手动定位0.350s第8/10帧高度0并截图。消费端点击跳跃观察空中第5/10帧，高度36px，结束idle/根高度0；当前页面JS错误列表为空。证据：jump-landing-v14.png、jump-comparison-v14.gif、任务assembly-check.json/runtime-samples.json。没有重跑整套历史测试或新版Godot导入，也没有批准整套美术/游戏。

## v15 受击恢复与通用编排（2026-10-03）

一次真实GPT调用补恢复原画；旧hit80、新恢复50、旧idle30ms，总160ms。当前集合7动作31播放位置24不同RGBA图，draft。src/motion_sequence.py的4项测试通过；实际候选重建atlas字节一致。控制器0..80ms立即受击，80..130ms恢复，130..160ms原idle，160ms状态idle/高度0。浏览器工作台定位0.100s第2/3帧，消费端点击受击后返回idle；当前页面错误列表为空。证据hit-recovery-v15.png、hit-comparison-v15.gif、任务assembly-check.json。没有批准完整美术、跨动作或正式游戏。

## v16 走路与待机头部一致性（2026-10-03）

0次新GPT调用，复用已生成idle头部至move/start/stop；保留身体原画与时长/循环。人工清除参考护脸拳进入接缝的小角，99px裁切/5px羽化，走路头部0/1/0/-1px重复起伏。当前集合7动作31位置24不同RGBA，draft。5项区域加工测试通过，三动作接缝以下字节相同、重复导出atlas字节相同；实际控制器新旧action/帧/x/y相同且最终idle。

浏览器move0.020/0.800s第1/8帧截图identity-move-v16.png；停步演示move2/8后idle/高度0/x413.3，错误列表为空。动态对照identity-comparison-v16.gif为跟随角色固定镜头，20ms源帧采样。没有批准完整美术、剩余跨动作或正式游戏。

## 统一交付入口与最新Godot导入（2026-10-03）

默认8770根首页从旧v10改指current-v16，旧首页保留legacy-v10.html。src/motion_preview_site.py一次导出实际v16素材、工作台、消费示例与3ZIP；0次新GPT调用。4项交付站测试通过，真实Godot4.7.2导入与86项/7动画检查通过；下载Godot关键文件与被检查文件字节一致。浏览器从根入口跳至current-v16、试玩返回workbench正确，跳跃0.210/0.440s第5/10帧高度40，错误列表为空。证据delivery-site-v16.png/json。未批准完整美术或正式游戏。

## v17 前景手臂周期（2026-10-03）

旧v16近侧手臂一直后摆，本轮4次真实GPT调用，2张局部来源、复用旧v5完整前摆1张。新整帧均reject，仅明确手臂ROI用于派生候选。800ms/8位置不变，5相位修正，7动作31位置24不同RGBA仍draft。

6项region测试通过；ROI外/保护框/未处理相位字节一致，重复atlas一致，3ZIP完整性通过。真实Godot4.7.2导入成功，GODOT_SPRITE_EXPORT_PASS checks=86 animations=7。浏览器440ms/5帧可见前摆；停步示例最终idle/高度0/x413.3，错误列表为空。证据arm-cycle-v17.png、arm-cycle-comparison-v17.gif与input任务assembly-check.json。

尚未批准完整步态、美术或正式游戏：共享move-stop的手臂不能同时匹配前后摆的两个接触相位；需要继续优化跨动作连接。历史测试未全量重跑。

## 按接触帧选择停步动作（2026-10-03）

新增可选stopClipsByContact，保留move-stop状态/currentClip返回对应实际片段；未映射落脚与起步短按回退共同图。直接落脚与经过move-settle两条路径均测试；跨片段大/小dt距离一致、重新移动及受击打断通过。34项Node测试、5项交付站及3项示例Python测试通过，diff检查通过。暂未替换v17入口，该逻辑测试不证明新停步姿态视觉通过。

一次真实GPT调用补前摆停步候选，原始1254方图按固定画布归一化，0偏移；提示词与3张实际参考按顺序归档。候选仍接近完整前摆，整帧身份/服饰/腿部重画，整帧reject；仅保留可能的局部来源，未作为新版停步发布，也未接受派生循环。任务mint-adventurer-contact-stop-v1，输出contact-stop-source-v1。

## v18 两种落脚停步（2026-10-03）

本轮1次真实GPT修正，停步job累计2调用。新增屈肘回收；旧首次候选虽整帧reject，仅部分用于前摆恢复第一帧。前摆55/55/30ms，后摆40/45/45/30ms，复用下垂原画与真实idle。明确ROI外/保护框字节相同，末帧完整idle相同；8动作37位置仍draft。

真实集合控制器4条直接落脚/中途松开路径选择正确对应停步并返回idle。浏览器stop demo最终idle/高度0/x413.3、无捕获错误；工作台70ms/2帧截图contact-stop-v18.png。3ZIP完整性通过。默认入口current-v18，保留v17。裁切边缘、原图小噪点、剩余跨动作与正式游戏仍待验收。

Godot4.7.2真实导入与101检查/8动画通过；新集合28张不同RGBA。浏览器根入口确认current-v18，前摆停步1×重播140ms第3/3帧结束。

## v19 起步和短按恢复（2026-10-03）

1次真实GPT调用，整帧reject，仅手臂候选ROI复用。原画未准确达到指定坐标。四姿态起步100ms，最后一帧与move首帧RGBA相同；后摆停步五帧175ms。8动作41位置28不同RGBA仍draft。reverseStartOnRelease显式启用，取消仅复用已走过帧，末段真实idle；反向复用不是新GPT原画。

37 Node、5交付站、3示例测试通过；实际4短按和4落脚路径通过。首个脚本误将运行时帧时长也要求相同而失败，修正为真实原画坐标匹配后通过。ROI外/保护框不变、3ZIP完整性通过。浏览器65ms第3/4帧截图start-transition-v19.png；stop demo最终idle/根高度0/x413.3、无捕获错误。默认current-v19。细小噪点、原画接缝、剩余跨动作与正式游戏仍待检查。

Godot4.7.2真实导入与109检查/8动画通过。浏览器默认根入口确认current-v19，起步正常1×重播100ms第4/4帧结束。

## v20 跳跃入口与本地工具复核（2026-10-03）

0次新GPT调用。首尾检查首次误认jump首帧等于idle而失败，确认13928可见像素不同；用真实idle替换第一帧，保留40ms，其余全部RGBA/duration/loop相同。五个单次动作末帧与idle相同。8动作41位置27不同RGBA仍draft。全量Python69通过，三ZIP完整性通过。

二维记录误填模型180ms已改成真实0ms，19-toolkit的八动作整套访问与0ms记录保存tour-record-v19-toolkit.json。新的材料/调用/输出说明见CHARACTER_MOTION_QUICKSTART.md。当前工作流可制作、修正和交付；正式美术/游戏/移动设备验收不由测试自动批准。

最新v20：Godot4.7.2真实导入/109检查/8动画通过；正常1×整套巡演访问八动作，二维blendMs=0，无捕获JS错误。tour-record-v20.json、delivery-v20.png保存实际浏览器证据。仍需核对承重脚原画与消费移动速度的关系，未将全套视觉或正式游戏标成通过。

### v21 待验收：承重腿局部候选

- 一次真实 GPT 调用；整帧拒绝，仅显式登记偏移后提取右腿 ROI。仅 move 索引1修改2439像素，ROI外及其他动作逐帧RGBA相同，8×100ms循环不变。
- 新通用 stride-review 仅测作者选择的点/接触轮廓；人工支撑分组并非自动腿部识别，拟合结果不自动调整速度。
- Python unittest 74通过。对比页实际加载两版图集，1×播放与第2张同相位定位可用；诊断速度滑块90→130→90更新指标。最初 Image.decode 在当前IAB未完成，改为onload/onerror后实际显示成功。
- 截图 `character-workbench-v1/walk-review-v21.png`、`character-workbench-v1/stride-review-v21.png`；像素证据 `character-workbench-v1/walk-candidate-v21.json`。保留默认v20，v21仅为候选；第二支撑组、整套步态、实际游戏验收未通过，Godot本轮未重跑。
