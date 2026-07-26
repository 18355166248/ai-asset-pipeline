# 卡牌插画 · 五段拼接法

高质量**角色/怪物卡面插画**的一致性方案（源自《谜宫》fable 老师的经验，已工具化）。
和 `../item_grid.md` 的 6×6 网格法互补：

- **网格法** → 大量小 item（图标 / 合成块 / 三消块），一次出 36 格。
- **五段法（本目录）** → 少量大插画（角色 / 怪物 / 卡面），一张一卡、3:4、带参考图锁身份。

## 一致性 = 流程，不是万能 prompt

三步，缺一不可：

1. **动笔前把脸写死**（`character_sheet.md`）：每个露脸角色锁 6 条轴 + 1 个独占标志。
2. **每角色定一张立绘当身份证**：之后该角色所有卡都挂这张立绘做参考图。
3. **五段拼接 prompt**：画风 / 身份 / 场景 / 构图 / 约束——**四段共用逐字复制，只换场景段**。

## 文件

| 文件 | 用途 |
|---|---|
| `character_sheet.md` | 角色设定表模板（6 轴 + 独占标志 + 差异化死规矩） |
| `five_segments.md` | 五段 prompt 全文（4 段共用块可直接复制 + 场景写法三心得） |
| `../../src/gen_card.py` | 拼接生成器：给身份+场景，一行出整段可粘贴 prompt |

## 快速上手

```bash
# 1) 先给角色写好设定表 -> 生成立绘定稿（当参考图）
# 2) 拼某张卡的完整 prompt：
python ../../src/gen_card.py \
  --face "sharp pale aristocratic face with a pointed chin, narrow piercing dark-red eyes, pointed ears, high narrow nose, exposed fangs, slicked-back black hair with a widow's peak, apparent age mid-30s" \
  --scene "Scene: a moonlit gothic balcony ..." 
# 3) 把输出粘到 GPT/Gemini，并【附上该角色的立绘参考图】
```

## 实测经验（东方修仙套系验证得出，都踩过坑）

### 一、否定式约束基本无效，必须正说

模型对 "no XXX" 的执行力极差。同一件事换成正面描述实物就生效：

| 想要的效果 | ❌ 无效写法 | ✅ 有效写法 |
|---|---|---|
| 不要运动鞋 | `no sneakers, no rubber soles` | `flat cloth shoes with a soft upturned toe and a thin fabric sole` |
| 不要多余的手 | `no extra fingers` | `hands are clearly and correctly countable` |
| 不要肌肉 | `not muscular` | `slender lithe, a dancer's build, graceful and slim rather than muscular` |

### 二、镜头写「情境」，别写「参数」

三视图里的 3/4 侧视角，写 `three-quarter view rotated 45 degrees` **完全不转**；
改成 `a side-turned view in which one shoulder points toward the viewer and the far
half of the face is partly hidden` 立刻生效。模型理解情境远强于理解参数。

### 三、女性角色必须显式写性别，否则会画成男的

**最大的坑**。身份描述里若没有一个词点明性别，遇到 `handsome` / `angular face` /
`athletic` / `toned midriff` 这类词，模型会直接画成男性。

必修三处：
1. 开头显式写 **`a beautiful young woman`**（`handsome` 在英文里默认指男性，禁用）。
2. 补女性面部与体态特征：`softly tapered jaw` / `slender neck` / `long lashes` /
   `full lips` / `soft sloping shoulders`。
3. 体型词换掉：`athletic` → `slender lithe`；`toned midriff` → `flat smooth midriff`。

### 四、道具白名单能挡住模型自作主张

不写白名单时，模型会自行给角色加法杖、背包、宠物。加上
`Carry only the equipment explicitly named in the character identity above` 即可根治。

### 五、年龄/体型跨度没问题，风格能保持

22 岁剑修 / 45 岁魔头 / 70 岁圆胖丹翁，三者体型年龄差极大，画风仍是同一只手笔。
说明「四段共用块」确实在起作用，六轴差异也画得出来，不会滑向「平均脸」。

## 出图之后

不是切图，而是：裁到固定 3:4、校验脸没出「安全区」（外 8% 会被卡框盖住）、图标类再过一遍描边/色彩归一。裁切脚本可后续加。
