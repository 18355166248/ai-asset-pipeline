# 补图 · 给已有套系再加物件（保持一致）

素材管线真正的死穴：一周后要往老套系里加几个新物件，风格必须对得上。
**核心手法 = 上传已有成品做参考图 + 只描述新增物**。Gemini 在这块最强。

---

## 流程

1. 从已有套系里挑 2–4 张**最有代表性**的成品（能体现描边/上色/视角/配色）。
2. 上传为参考图。
3. 用下面的模板，只描述**要新增的物件**，反复强调「match the reference exactly」。

---

## 英文模板（配参考图使用）

```
Here are reference images of an existing game-icon set (attached).

Create new items in the EXACTLY SAME style as the references: same line weight,
same outline, same shading method, same color grading, same camera angle, same
lighting, same overall proportions and level of detail.

NEW ITEMS to draw ({{N}} items, one per cell in a {{ROWS}}×{{COLS}} grid):
{{NEW_ITEM_LIST}}

RULES:
- Match the reference style precisely — they must look like they belong to the
  same set, drawn by the same artist.
- One centered item per cell, ~70% of cell, consistent scale.
- Single FLAT solid background color {{BG}} (same as references), NO gradient,
  NO shadow, NO texture.
- No text, numbers, labels, grid lines, borders, watermark.

Output: one 1:1 square high-resolution image.
```

### 变量

- `{{N}}` / `{{ROWS}}×{{COLS}}`：这次补几个（补图常用 3×3=9 或 2×3=6 的小网格）。
- `{{NEW_ITEM_LIST}}`：只列新增物件。
- `{{BG}}`：**和原套系完全相同**的背景色（很关键，去背和拼图才统一）。

---

## 只补 1 个（单图）

```
Reference image attached: an existing game icon.
Draw ONE new icon: {{NEW_ITEM}}, in the EXACTLY SAME style as the reference —
same outline, shading, palette, angle, lighting, proportions.
Single flat {{BG}} background, no gradient, no shadow, no text.
Output: one square icon.
```

## 验证补图是否对得上

补出来的图，和原套系一起丢进管线，用联络表并排看：
```bash
python ../src/run.py input/new_batch.png -r 3 -c 3 --size 96 --autocrop
# 然后把 output 里新老 cutouts 放一起，再拼一张对比联络表：
python ../src/contact.py output/合并目录 -o output/对比.png
```
新老放一起肉眼无违和 = 补图漂移可控（实验 B 通过）。
