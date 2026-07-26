# 主模板 · 6×6 同风格 item 网格

> 用法：复制下面「英文模板」，替换 `{{...}}` 里的内容，粘贴到 GPT/Gemini。
> 英文对画风控制更稳；文末附中文版，可直接用中文。

---

## 英文模板（推荐）

```
Create ONE single square image containing a strict 6×6 grid (36 cells, 6 rows
by 6 columns), evenly spaced.

STYLE (identical for all 36 items):
{{STYLE}}
Keep the SAME art style across every cell: same line weight, same shading
method, same color grading, same camera angle, same lighting direction.

CONTENT — one item per cell, left-to-right, top-to-bottom:
{{ITEM_LIST_36}}

LAYOUT RULES (strict):
- Exactly 36 items, one centered item per cell, no empty cell, no duplicates.
- Each item occupies about 70% of its cell, consistent scale and margins.
- Same orientation for all items ({{VIEW}}, e.g. front view / 3-4 view).

BACKGROUND (critical):
- A single FLAT solid background color {{BG}} filling the whole image.
- Absolutely NO gradient, NO drop shadow, NO reflection, NO texture.

DO NOT include: any text, numbers, labels, captions, grid lines, cell borders,
frames, watermark, or signature.

Output: one 1:1 square image, high resolution.
```

### 变量说明

- `{{STYLE}}`：从 `style_library.md` 挑一条完整画风描述贴进来。
- `{{ITEM_LIST_36}}`：36 个物件，建议**编号列出**（GPT 更听话）：
  ```
  1. red apple   2. banana   3. watermelon   ... 36. green grapes
  ```
- `{{VIEW}}`：统一视角，`front view` 或 `3/4 top-down view`（游戏图标常用后者）。
- `{{BG}}`：一个纯平色，如 `#F2EFE9`（浅暖灰，和多数物件对比够，去背友好）。

---

## 已填好的范例（水果摊 · 可直接改）

```
Create ONE single square image containing a strict 6×6 grid (36 cells, 6 rows
by 6 columns), evenly spaced.

STYLE (identical for all 36 items):
Cute flat-vector game icon, soft rounded shapes, thick uniform outline,
2-3 flat color tones per item with simple cel shading, playful mobile-game
look. Same line weight, same shading, same color grading, same 3/4 top-down
camera angle, same soft top-left lighting across every cell.

CONTENT — one item per cell, left-to-right, top-to-bottom:
1. red apple  2. green apple  3. banana  4. orange  5. lemon  6. watermelon
7. strawberry  8. cherry  9. grapes  10. peach  11. pear  12. pineapple
13. mango  14. kiwi  15. blueberry  16. avocado  17. coconut  18. lychee
19. tomato  20. carrot  21. corn  22. broccoli  23. eggplant  24. pumpkin
25. potato  26. onion  27. chili pepper  28. mushroom  29. cucumber  30. lettuce
31. bread loaf  32. milk carton  33. egg  34. cheese wedge  35. honey jar  36. jam jar

LAYOUT RULES (strict):
- Exactly 36 items, one centered item per cell, no empty cell, no duplicates.
- Each item occupies about 70% of its cell, consistent scale and margins.
- Same 3/4 top-down orientation for all items.

BACKGROUND (critical):
- A single FLAT solid background color #F2EFE9 filling the whole image.
- Absolutely NO gradient, NO drop shadow, NO reflection, NO texture.

DO NOT include: any text, numbers, labels, captions, grid lines, cell borders,
frames, watermark, or signature.

Output: one 1:1 square image, high resolution.
```

---

## 中文版模板

```
生成一张正方形图片，内含严格的 6×6 网格（36 格，6 行 6 列），均匀分布。

画风（36 个物件完全统一）：
{{STYLE}}
所有格子保持同一画风：相同描边粗细、相同上色方式、相同配色调性、相同视角、相同光照方向。

内容——每格一个物件，从左到右、从上到下：
{{列出 36 个物件，建议编号}}

排版规则（严格）：
- 正好 36 个，每格一个居中物件，不留空格，不重复。
- 每个物件约占格子 70%，比例和留白一致。
- 所有物件统一视角（{{正视 / 俯视 3/4}}）。

背景（关键）：
- 整图使用单一纯平背景色 {{#F2EFE9}}。
- 绝对不要渐变、不要投影、不要反光、不要纹理。

不要出现：任何文字、数字、标签、说明、网格线、格子边框、外框、水印、签名。

输出：一张 1:1 正方形高清图。
```

## 常见翻车 → 处理

- **出成 36 张分开的图 / 拼图有缝** → 强调 "ONE single image"、"strict grid"，或改用 GPT。
- **背景带阴影抠不干净** → prompt 里已禁投影；仍有就本地 `--tolerance` 调大或装 rembg。
- **物件大小不一** → 保留 `--autocrop`，切图阶段按内容裁正。
- **少画/多画** → 明确 "Exactly 36"，并让它「逐格对照编号列表」。
