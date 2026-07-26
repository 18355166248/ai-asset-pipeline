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

## 出图之后

不是切图，而是：裁到固定 3:4、校验脸没出「安全区」（外 8% 会被卡框盖住）、图标类再过一遍描边/色彩归一。裁切脚本可后续加。
