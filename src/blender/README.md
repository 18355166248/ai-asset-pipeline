# 3D → 序列帧（管线上游）

把 3D 模型渲成透明背景的动作表，供 2D 游戏（Cocos）当序列帧用。

## 为什么加这一段

原来的管线是「AI 出网格图 → 切图 → 去背 → 缩放」，静态道具很好使
（36 法宝一次出图全部可用），但**角色动作序列帧做不出来**：
逐张出图保不住跨帧一致性，实测主角 36 动作「画风跑成动漫」而废弃。

这一段换了个来源：同一个 3D 模型换姿态/换角度渲。
**风格漂移在结构上不可能发生**，因为每一帧都是同一个模型。
附带好处是渲染直接带 alpha，不需要 chroma-key / rembg，也就没有抠坏某一格的可能。

下游仍然接现有的 `slice_grid.py` / `resize.py` / `contact.py`，只是不再需要 `cutout.py`。

## 用法

```bash
BLENDER="C:/Program Files/Blender Foundation/Blender 4.5/blender.exe"

# 8 方向静态图（不需要绑骨，现在就能跑）
"$BLENDER" --background --python src/blender/render_frames.py -- \
    --model path/to/model.glb --out output/frames/model \
    --mode turntable --frames 8 --view topdown --size 256

# 播放模型自带动画（需要模型已绑骨 + K 好动作）
"$BLENDER" --background --python src/blender/render_frames.py -- \
    --model hero.glb --out output/frames/hero \
    --mode animation --frames 8 --view side

# 打包成动作表
python src/pack_sheet.py output/frames/hero -o output/sheets/hero.png \
    --cols 4 --cell 96 --trim
```

`--view` 三个预设对应实际战场机位：

| 预设 | 仰角 | 用途 |
| --- | ---: | --- |
| `audit` | 44° | catch-the-goose 既有质检机位，和旧模型对比用 |
| `topdown` | 58° | xianxia-roguelike 竖屏俯视战场 |
| `side` | 12° | 横版闯关 |

## 机位：横版用 62° 方位角

`--view side` 的方位角定在 62°，是实测比出来的：

| 方位角 | 效果 |
| ---: | --- |
| 0° | 正面。四肢朝镜头前后摆，透视全压缩掉了，走路几乎看不出来 |
| 62° | **3/4。身体有宽度、摆幅也读得全** |
| 90° | 纯侧面。摆幅最大，但身体只剩一条窄边，没有体积感 |

横版动作游戏（DNF 那类）用的就是 3/4，不是纯侧面。

## 动作调参的三件事

手感不来自帧数，来自这三样，缺一件就"像在滑"：

1. **重心起伏** —— 走路时 `root` 上下颠，触地最低、过渡帧最高。只转腿不颠髋 = 滑步。
2. **跟随延迟** —— 小臂比大臂晚 2~3 帧到达极值。同步到位的肢体没有重量。
3. **蓄力与收招** —— 挥砍的帧数分配就是打击感：前摇 8 帧（慢）→ 挥出 3 帧（快）
   → 定格 4 帧 → 收招 9 帧。挥出只占 3 帧所以显得快，定格让力道落地。

另外**挤压拉伸**（`scale` 通道）是小尺寸下最有效的力道提示，命中帧压扁一点即可。

插值上，循环动作用 `auto_smoothing = "CONT_ACCEL"`：首尾姿态相同还不够，
接缝处的**速度**也要连续，否则每圈都顿一下。所有关键帧用 `AUTO_CLAMPED` 句柄防过冲——
过冲会让挥砍的定格帧先荡过去再荡回来，力道就散了。

## 必须知道的坑

### 1. 归一化必须跨帧算一次

逐帧各自归一化会让角色在动作表里抖动、忽大忽小。
`render_frames.py` 的做法是先遍历全部帧取包围盒并集，据此定死一套缩放和位移，
渲染时只改帧号和旋转。`pack_sheet.py` 的 `--trim` 同理，用所有帧 alpha 的**并集**裁切，
不逐帧 autocrop——否则角色抬手那一帧被裁得多，播起来脚底就在漂。

这类问题单看每张图都正常，只有播放时才暴露。

### 2. glTF 导入的对象 rotation_mode 是 QUATERNION

给它 `keyframe_insert("rotation_euler")` 会把关键帧打到一个 Blender 根本不求值的通道上：

- 物体不动
- 导出的 glb 里 0 条动画
- **全程没有任何报错**，`export_scene.gltf` 照样返回 `FINISHED`

K 动作前必须先 `obj.rotation_mode = "XYZ"`，或者直接对 `rotation_quaternion` 打帧。

### 3. 导出动画默认会按对象拆成 N 条

`bpy.ops.export_scene.gltf` 的默认设置下，11 个部件会导出成 **11 条独立动画**。
重新导入时只有一条是激活的，其余进 NLA 静默不播——表现是「角色几乎不动」，
而导出和导入全程不报错。

要合成一条，两个开关缺一不可：

```python
export_animation_mode="SCENE",          # 按场景导，不按 action 导
export_anim_scene_split_object=False,   # 默认 True！SCENE 模式下仍会按对象再拆
```

只设 `export_animation_mode="SCENE"` 不够，这是我卡最久的一个。
验收方法是数导出文件里的 `animations` 条数，应该等于 1。

### 4. 循环与一次性动作的采样方式不同

`--loop` 开着时采 `[first, last)`，因为末帧与首帧同姿态，包含它会多出重复帧、播放时卡一下；
不开时采 `[first, last]` 闭区间，否则挥砍的收招、受击的站稳会被截掉最后一下。

同理，`--mode animation` 不能靠 `scene.frame_start/frame_end` 判断有没有动画——
Blender 默认就是 1-250，跟模型无关。信它的话静态模型会渲出 N 张姿态相同的图
（而且因为 EEVEE 采样抖动，每张哈希还不一样，很难一眼看出问题）。
脚本改成从对象的 action 里取真实帧范围，没有动画就明确拒绝。

## 现状与下一步

已验证（用 `catch-the-goose` 的 `apple.glb`）：

- ✅ turntable 出 8 方向，跨帧位置稳定
- ✅ 部件建父子层级后能正确导出到 glTF 节点树
- ✅ 枢轴动画（转叶子，果体不动）→ animation 模式渲染 → 打包，全链路通

- ✅ **导出端层级已修**（catch-the-goose `gen_fruits.py` / `gen_antique_theme_v2.py`）。
  `apple.glb` 现在是 `fruit-body → stem → leaf`；只给 stem 打关键帧，
  叶片被层级带着走，果体不动。网格数、材质数、三角面、包围盒与旧版完全一致，
  渲染逐像素对比最大通道差 2/255（EEVEE 采样噪声），无视觉回归。

待办：

1. **部件原点要落到关节上** —— 当前 `normalize_export_parts` 对每个部件都做
   `transform_apply`，几何被烘进网格、**所有原点都在世界原点**。
   于是转 stem 实际是绕苹果中心转，不是绕它和果体的连接点转。
   苹果碰巧看着还行（果柄本来就在顶端），但角色的手臂绕身体中心转会直接穿帮。

   规格里 `actionProfile.pivot` 就是为这件事准备的，但目前 `apple-sculpt-spec.json`
   里全是默认值（`mode: center`、`localPosition: [0,0,0]`、`confidence: 0.5`），
   没有真实关节数据。做动作前必须先把这批 pivot 填成真值。

2. 定动作 JSON 格式（clip → 部件 → 关键帧），把手 K 换成可重复脚本
3. 第一个真角色：按 v2 规范建模，四肢作为独立枢轴部件

## 规格数据的一个已知问题

`apple-sculpt-spec.json` 里 `componentTree` 的 `parent` 和 `attachment.parentSocket`
互相矛盾：三个宏部件的 `parent` 都写成 `root`（扁平默认值，confidence 0.5），
但 `stem.attachment.parentSocket` 是 `crown-socket`（在果体上）、
`leaf.attachment.parentSocket` 是 `stem-base-socket`（在果柄上）——
真实连接链是 果体 → 果柄 → 叶片。

生成脚本按 socket 建层级，不按 `parent` 字段。古玩三件的 spec 没有这个矛盾
（`parent` 与 `parentSocket` 一致），所以只有 apple 需要这条说明。
