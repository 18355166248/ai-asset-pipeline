"""填空生成「可直接粘贴到 GPT/Gemini」的 6×6 网格提示词。

例:
  python src/gen_prompt.py --style flat --bg "#F2EFE9" --view "3/4 top-down" \
    --items "苹果,香蕉,西瓜, ...(36个，逗号或换行分隔)"

  # 从文件读物件列表（一行一个）
  python src/gen_prompt.py --style clay --items-file my_items.txt

  # 用预置游戏配方（不同游戏一行出一套）
  python src/gen_prompt.py --recipe collect-animals
  python src/gen_prompt.py --list-recipes

  # 只想看某个画风词
  python src/gen_prompt.py --list-styles
"""

from __future__ import annotations

import argparse
import sys

import recipes as _recipes

STYLES = {
    "flat": (
        "Cute flat-vector game icon, soft rounded shapes, thick uniform "
        "outline, 2-3 flat color tones per item with simple cel shading, "
        "clean and playful mobile-game look, soft top-left lighting."
    ),
    "clay": (
        "Cute 3D cartoon render, soft clay-like material, rounded chunky "
        "shapes, glossy but not reflective, gentle studio lighting, "
        "isometric 3/4 view, playful mobile game asset look."
    ),
    "handdrawn": (
        "Hand-drawn cartoon style, slightly wobbly ink outline, warm "
        "gouache-like flat coloring, cozy storybook game look, even "
        "soft lighting."
    ),
    # 网格版水墨。与 gen_card.py 的 shuimo 预设是两回事：那版是给「带参考图的 3:4
    # 卡面」写的，含 "matching the attached reference" 和宣纸底，网格出图两者都不适用。
    # 这版刻意收紧了晕染和飞白——墨色洇开的柔边在去背时会被判成背景，抠完剩一圈毛刺。
    #
    # 实测教训：只写 "ink-wash painting style" 会被模型无视，仙侠/剑修这些词在训练数据里
    # 和日漫立绘绑得太死，一句风格形容词压不过语义拉力，出来就是赛璐璐动漫图。
    # 所以这里改成描述**作画媒介和物理过程**（毛笔、宣纸、笔触堆形），模型对这类
    # 描述的响应远强于风格标签；负面清单在 STYLE_NEGATIVES 里另配。
    "shuimo": (
        "The image must look like a traditional Chinese ink-wash painting "
        "(shuimo) executed with a soft animal-hair brush on absorbent xuan rice "
        "paper. Every form is built out of visible calligraphic brush strokes of "
        "varying width, pressure and ink density - NOT from a uniform outline "
        "filled in with flat color. Black ink dominates the image; color is "
        "sparse and restrained, only thin mineral-pigment washes (azurite blue, "
        "malachite green, cinnabar red, gold) laid over the ink. Faces and hands "
        "are suggested with a few economical strokes, not rendered in detail. "
        "Keep every edge crisp and fully opaque - no bleeding wash beyond the "
        "outline, no faded dry-brush edges, no splatter."
    ),
    # 场景专用水墨。上面那版为了抠图把晕染和飞白全禁了——那是网格素材的代价，
    # 背景图不进 cutout，禁它反而丢掉水墨最该有的东西，这里放开。
    "shuimo-scene": (
        "The image must look like a traditional Chinese ink-wash landscape "
        "painting (shuimo) brushed onto xuan rice paper. Forms are built from "
        "layered ink washes and calligraphic brushwork of varying weight, with "
        "soft bleeding edges, dry-brush flying-white texture and large areas of "
        "deliberately empty paper. Black ink dominates; color is sparse and "
        "restrained, only thin mineral-pigment washes (azurite blue, malachite "
        "green, cinnabar red, gold) over the ink. Visible rice-paper grain, "
        "atmospheric and airy."
    ),
    "pixel": (
        "Clean pixel-art game sprite, limited cohesive palette, crisp "
        "pixels, subtle dithering for shading, consistent top-left light, "
        "retro 16-bit look, no anti-aliased edges."
    ),
    "line": (
        "Minimal line-icon style, uniform rounded stroke, single accent "
        "fill color, flat and geometric, modern clean UI look, no gradient."
    ),
    "realistic": (
        "Semi-realistic glossy game icon, soft rendered volume, rich "
        "clean colors, smooth gradients inside the item only, studio "
        "product lighting, 3/4 view, polished casual-game look."
    ),
}

# 画风负面清单。和 STYLES 是一对：STYLES 说「要什么媒介」，这里说「不许滑向什么」。
# 只有正面描述时，模型会朝训练数据里该题材最常见的画法回归——仙侠题材就是日漫立绘。
# 键对不上时取空串，即该画风不需要负面约束。
STYLE_NEGATIVES = {
    "shuimo": (
        "This is NOT anime, NOT manga, NOT Chinese donghua character art, NOT a "
        "cel-shaded illustration, NOT a mobile-gacha character portrait, NOT a "
        "modern digital painting, NOT 3D, NOT photorealistic. Do not use flat "
        "cel shading, airbrushed gradients, glossy highlights, rim lighting, or "
        "clean uniform lineart filled with solid color. No large glossy anime "
        "eyes, no rendered skin shading, no lip gloss, no detailed hair "
        "strand-by-strand rendering. If the result could be mistaken for a "
        "character illustration from a mobile game, it is wrong - it must read "
        "as brush and ink on paper."
    ),
    "shuimo-scene": (
        "This is NOT anime, NOT a digital matte painting, NOT 3D, NOT "
        "photorealistic, NOT a concept-art speedpaint. Do not use airbrushed "
        "gradients, lens flare, volumetric god rays, or saturated fantasy "
        "colors. It must read as brush and ink on paper."
    ),
}

TEMPLATE = """Create ONE single square image containing a strict {rows}x{cols} grid \
({n} cells, {rows} rows by {cols} columns), evenly spaced.

RENDERING MEDIUM (most important instruction - read before anything else):
{style}
{negative}

STYLE CONSISTENCY (identical for all {n} items):
Keep the SAME art style across every cell: same line weight, same shading \
method, same color grading, same camera angle, same lighting direction.

CONTENT - one item per cell, left-to-right, top-to-bottom:
{items}

LAYOUT RULES (strict):
- Exactly {n} items, one centered item per cell, no empty cell, no duplicates.
- Each item occupies about 70% of its cell, consistent scale and margins.
- Same orientation for all items ({view}).
- Every item stays fully INSIDE its own cell with a clear margin. Nothing may \
cross, overlap or touch a cell boundary - no effect, glow, tail or trailing \
element may extend into a neighbouring cell.

BACKGROUND (critical):
- A single FLAT solid background color {bg} filling the whole image.
- Absolutely NO gradient, NO drop shadow, NO reflection, NO texture.

DO NOT include: any text, numbers, labels, captions, grid lines, cell borders, \
frames, watermark, or signature.

FINAL CHECK before you output: re-read the RENDERING MEDIUM section above and \
confirm the image matches it. The medium matters more than the subject matter.

Output: one 1:1 square image, high resolution."""

# 同一角色的 {n} 种状态（配方带 bible 字段时用这套，见 prompts/character_forms.md）。
# 与 TEMPLATE 的区别：先用「角色圣经」把身份钉死，每格只准改状态、不准改设计。
TEMPLATE_CHARACTER = """Create ONE single square image containing a strict {rows}x{cols} \
grid ({n} cells, {rows} rows by {cols} columns), evenly spaced. Every cell shows the \
SAME single character; only the pose / state changes.

RENDERING MEDIUM (most important instruction - read before anything else):
{style}
{negative}
The character description below tells you WHAT is depicted; this section tells you \
HOW it must be painted. When the two seem to pull in different directions, this \
section wins.

CHARACTER BIBLE (must stay identical in all {n} cells):
{bible}

CONSISTENCY (identical for all {n} cells):
Keep the exact same character identity, same proportions, same color palette, same \
outfit, same equipment, same art style, same line weight and shading in every cell.

PER-CELL VARIATION - left-to-right, top-to-bottom:
{items}

LAYOUT RULES (strict):
- Exactly {n} cells, one centered character per cell, no empty cell.
- The character occupies about 70% of its cell, consistent scale and margins.
- Same orientation for all cells ({view}).
- Same character design in every cell - only the state changes. Do NOT redesign the \
outfit, hair, body type or equipment between cells.
- The character and every effect around it stay fully INSIDE their own cell with a \
clear margin. Nothing may cross, overlap or touch a cell boundary - no weapon, \
sword-qi arc, lightning bolt, aura or trailing element may extend into a \
neighbouring cell. Shrink the pose rather than let it spill over.

BACKGROUND (critical):
- A single FLAT solid background color {bg} filling the whole image.
- Absolutely NO gradient, NO drop shadow, NO reflection, NO texture.

DO NOT include: any text, numbers, labels, captions, grid lines, cell borders, \
frames, watermark, or signature.

FINAL CHECK before you output: re-read the RENDERING MEDIUM section above and \
confirm the image matches it. The medium matters more than the subject matter - a \
correctly painted ink-wash figure in a slightly wrong pose is acceptable, an \
anime-styled figure in a perfect pose is not.

Output: one 1:1 square image, high resolution."""


# ── 场景单图模板 ──────────────────────────────────────────────────
# 和上面两个网格模板的根本区别：这里的图**自己就是背景**，所以那条「单一纯平背景色
# + 禁止渐变投影」的铁律在这里完全反过来——不写 bg，也不进 cutout。

# 战斗场地：俯视地表。约束里最要紧的是「中间要平」——中央是角色和敌人跑动的地方，
# 底图一旦有高对比的花纹或强光影，小精灵图叠上去就糊成一团认不出来。
TEMPLATE_SCENE_ARENA = """Create ONE single {ratio} image: a game battle-arena \
ground texture.

VIEW (critical):
- Straight top-down orthographic view, camera pointing directly down at the ground.
- This is the FLOOR seen from above - not a landscape, not a horizon, no sky, \
no vanishing point, no side view.

RENDERING MEDIUM (most important instruction):
{style}
{negative}

CONTENT:
{content}
Color palette: {palette}.

READABILITY (critical - game sprites will be drawn on top):
- Keep the central 70% of the image visually calm: low contrast, few details, \
no bright highlights and no busy patterns there.
- Push all the larger detail and darker values toward the outer edges.
- Even ambient lighting with no strong directional shadows - the characters \
carry their own shading.
- Nothing in the image should read as a character or a pickup item.

DO NOT include: any character, creature, person, UI element, health bar, icon, \
text, numbers, watermark, signature, frame or border.

Output: one {ratio} image, high resolution."""

# 氛围插画：主菜单 / 章节封面 / 结算页。上三分之一要留白给标题压字。
TEMPLATE_SCENE_ART = """Create ONE single {ratio} illustration for a mobile game \
screen.

RENDERING MEDIUM (most important instruction):
{style}
{negative}

CONTENT:
{content}
Color palette: {palette}.

COMPOSITION:
- Vertical mobile composition, the main subject sitting in the middle band.
- Keep the top third quiet and uncluttered - a game title will be placed there.
- Keep the bottom fifth quiet as well - buttons will be placed there.
- Atmospheric depth, clear silhouette reading even at phone size.

DO NOT include: any text, numbers, logo, UI element, button, watermark, \
signature, frame or border.

Output: one {ratio} image, high resolution."""


def parse_items(args) -> list[str]:
    raw = ""
    # 配方直接给列表，不走逗号串：条目本身可能含逗号（如 "recovering after a swing,
    # sword lowered"），join 再 split 会把一条切成两条，36 格悄悄变 40 格。
    if getattr(args, "recipe_items", None):
        return list(args.recipe_items)
    if args.items_file:
        with open(args.items_file, encoding="utf-8") as f:
            raw = f.read()
        parts = [x.strip() for x in raw.replace(",", "\n").splitlines()]
    else:
        parts = [x.strip() for x in (args.items or "").replace("\n", ",").split(",")]
    return [p for p in parts if p]


def numbered(items: list[str], cols: int) -> str:
    lines, row = [], []
    for i, it in enumerate(items, 1):
        row.append(f"{i}. {it}")
        if i % cols == 0:
            lines.append("  ".join(row))
            row = []
    if row:
        lines.append("  ".join(row))
    return "\n".join(lines)


def main() -> None:
    ap = argparse.ArgumentParser(description="生成 6×6 网格提示词")
    ap.add_argument(
        "--style",
        default="flat",
        help=f"画风键: {', '.join(STYLES)}（或直接写整段英文画风）",
    )
    ap.add_argument("--bg", default="#F2EFE9", help="纯平背景色")
    ap.add_argument(
        "--view",
        default="front view",
        help="统一视角，如 'front view' / '3/4 top-down view'",
    )
    ap.add_argument("--rows", type=int, default=6)
    ap.add_argument("--cols", type=int, default=6)
    ap.add_argument("--items", help="逗号/换行分隔的物件")
    ap.add_argument("--items-file", help="物件列表文件（一行一个）")
    ap.add_argument("--recipe", help="用预置游戏配方（见 --list-recipes）")
    ap.add_argument("--scene", help="出场景/背景单图（见 --list-scenes），不走切图管线")
    ap.add_argument(
        "--bible", help="角色圣经：36 格是同一角色的不同状态时用，把身份钉死"
    )
    ap.add_argument("--list-styles", action="store_true")
    ap.add_argument("--list-recipes", action="store_true")
    ap.add_argument("--list-scenes", action="store_true")
    args = ap.parse_args()

    if args.list_styles:
        for k, v in STYLES.items():
            print(f"\n[{k}]\n{v}")
        return

    if args.list_scenes:
        print("可用场景（--scene NAME）：")
        for k in _recipes.scene_names():
            s = _recipes.get_scene(k)
            print(f"  {k:18} {s['desc']}  [role={s['role']}, {s['ratio']}]")
        return

    if args.scene:
        s = _recipes.get_scene(args.scene)
        if not s:
            print(f"⚠ 无此场景: {args.scene}，用 --list-scenes 查看", file=sys.stderr)
            return
        # 场景默认走放开晕染的 shuimo-scene，与角色/敌人/物品同源；--style 仍可覆盖
        style_key = args.style if args.style != "flat" else "shuimo-scene"
        tpl = TEMPLATE_SCENE_ARENA if s["role"] == "arena" else TEMPLATE_SCENE_ART
        print(
            tpl.format(
                ratio=s["ratio"],
                style=STYLES.get(style_key, style_key),
                negative=STYLE_NEGATIVES.get(style_key, ""),
                content=s["content"],
                palette=s["palette"],
            )
        )
        return

    if args.list_recipes:
        print("可用配方（--recipe NAME）：")
        for k in _recipes.names():
            r = _recipes.get(k)
            print(f"  {k:18} {r['desc']}  [style={r['style']}, view={r['view']}]")
        return

    # 配方优先：把 style/view/bg/items 一并带出（命令行显式参数仍可覆盖）
    if args.recipe:
        r = _recipes.get(args.recipe)
        if not r:
            print(f"⚠ 无此配方: {args.recipe}，用 --list-recipes 查看", file=sys.stderr)
            return
        if args.style == "flat":  # 未手动改画风时用配方的
            args.style = r["style"]
        if args.view == "front view":  # 未手动改视角时用配方的
            args.view = r["view"]
        if args.bg == "#F2EFE9":  # 未手动改背景时用配方的
            args.bg = r["bg"]
        if not args.items and not args.items_file:
            args.recipe_items = r["items"]
        if not args.bible:
            args.bible = r.get("bible")

    style = STYLES.get(args.style, args.style)
    # 自定义画风（--style 直接写英文段落）没有对应负面清单，取空串
    negative = STYLE_NEGATIVES.get(args.style, "")
    items = parse_items(args)
    n = args.rows * args.cols
    if not items:
        print(
            "⚠ 未提供物件（--items 或 --items-file）。"
            f"仍生成模板，请手动填 {n} 个物件占位。",
            file=sys.stderr,
        )
        items_block = f"{{在此列出 {n} 个物件，编号 1-{n}}}"
    else:
        if len(items) != n:
            print(
                f"⚠ 物件数 {len(items)} ≠ {n}（{args.rows}×{args.cols}），"
                "请补齐或调整行列。",
                file=sys.stderr,
            )
        items_block = numbered(items, args.cols)

    tpl = TEMPLATE_CHARACTER if args.bible else TEMPLATE
    print(
        tpl.format(
            rows=args.rows,
            cols=args.cols,
            n=n,
            style=style,
            negative=negative,
            items=items_block,
            view=args.view,
            bg=args.bg,
            bible=args.bible,
        )
    )


if __name__ == "__main__":
    main()
