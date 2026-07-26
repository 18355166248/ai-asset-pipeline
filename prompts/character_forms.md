# 角色多形态 · 6×6 网格

同一个角色的 36 种形态 / 状态 / 表情。难点是**角色身份不能漂**——先用一段
「角色圣经」把特征钉死，再让它只改状态。

---

## 英文模板

```
Create ONE single square image containing a strict 6×6 grid (36 cells),
evenly spaced. Every cell shows the SAME single character, only the pose /
state changes.

CHARACTER BIBLE (must stay identical in all 36 cells):
{{CHARACTER_DESC}}
Keep the exact same character identity, same proportions, same color palette,
same outfit, same art style, same line weight and shading in every cell.

PER-CELL VARIATION — left-to-right, top-to-bottom:
{{STATE_LIST_36}}

LAYOUT RULES (strict):
- One centered character per cell, consistent scale (~70% of cell), same
  {{VIEW}} for all.
- Same character, do NOT change its design between cells.

BACKGROUND (critical):
- Single FLAT solid color {{BG}}, NO gradient, NO shadow, NO texture.

DO NOT include: text, numbers, labels, grid lines, borders, watermark.
Output: one 1:1 square high-resolution image.
```

### 变量说明

- `{{CHARACTER_DESC}}`：把角色钉死，越具体越稳。例：
  `A chubby white goose, orange beak and feet, one small blue bow on its head,
  round black eyes, cute chibi mascot, flat-vector style, thick outline.`
- `{{STATE_LIST_36}}`：36 种变化，按你的游戏需要，例如：
  - 表情：happy, angry, crying, sleepy, surprised, dizzy ...
  - 动作：running, jumping, sitting, waving, eating, hiding ...
  - 进化/形态：baby form, adult form, golden form, ghost form ...
- `{{VIEW}}`：统一视角（如 `front view`）。
- `{{BG}}`：纯平背景色。

---

## 已填好范例（大鹅吉祥物 · 表情+动作）

```
Create ONE single square image containing a strict 6×6 grid (36 cells),
evenly spaced. Every cell shows the SAME single character, only the pose /
state changes.

CHARACTER BIBLE (identical in all 36 cells):
A chubby white cartoon goose mascot, orange beak and feet, round black eyes,
a tiny blue bow on the head. Cute chibi proportions, flat-vector style, thick
uniform outline, soft cel shading, playful mobile-game look. Keep the exact
same identity, proportions, palette and style in every cell.

PER-CELL VARIATION — left-to-right, top-to-bottom:
happy, laughing, angry, crying, sleepy, surprised, dizzy, scared, love-eyes,
winking, shy, proud, running, jumping, sitting, waving hello, thumbs up,
eating, drinking, sleeping, thinking, celebrating, waddling, flapping wings,
peeking, hiding, dancing, singing, reading, cooking, fishing, waving goodbye,
cold-shivering, hot-sweating, dizzy-with-stars, sparkling-happy

LAYOUT RULES (strict):
- One centered goose per cell, ~70% of cell, same front view for all.
- Same character design in every cell, only the state changes.

BACKGROUND (critical):
- Single FLAT solid color #EAF2F8, NO gradient, NO shadow, NO texture.

DO NOT include: text, numbers, labels, grid lines, borders, watermark.
Output: one 1:1 square high-resolution image.
```

## 保持一致的技巧

- **先出 1 张定妆照**：先让它单独画 1 个「标准角色」，满意后把那张**作为参考图**上传，
  再要 6×6（Gemini 尤其吃这套）。
- **别一次改太多维度**：一张网格只改「表情」或只改「动作」，混着改容易崩身份。
- 需要补状态时，走 `add_item.md` 的参考图补图流程。
