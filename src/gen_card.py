"""卡牌插画五段拼接生成器（《谜宫》fable 法）。

四段共用块内置，逐字复制；你只提供【身份描述】和【场景段】，一行出整段可粘贴 prompt。

例:
  python src/gen_card.py \
    --face "sharp pale aristocratic face with a pointed chin, narrow piercing dark-red eyes, pointed ears, high narrow nose, exposed fangs, slicked-back black hair with a widow's peak, apparent age mid-30s" \
    --scene "Scene: a moonlit gothic balcony, low-angle chest-up view. The vampire lord turns his head toward the viewer with a slow cold smile ... Light source: pale moonlight from the upper left."

  # 场景从文件读（推荐，长场景好写）
  python src/gen_card.py --face-file faces/necromancer.txt --scene-file scenes/necromancer.txt

  # 没脸的怪物（省身份段）
  python src/gen_card.py --no-identity --scene-file scenes/dragon.txt

  # 换画风：只改画风段的风格措辞
  python src/gen_card.py --scene-file s.txt --style "Japanese cel-anime style, clean thin outlines, soft gradient shading"
"""
from __future__ import annotations

import argparse
import sys

# ① 画风段（预设可选，也可 --style 传整段自定义措辞）
STYLE_PRESETS = {
    "western": (
        "Western painted cartoon style matching the attached character reference "
        "exactly: bold thick dark outlines, solid dimensional color blocks, flat "
        "colors with simple cel shading, consistent detail density"),
    "shuimo": (
        "Traditional Chinese ink-wash and colored-ink painting style (shuimo/caimo) "
        "matching the attached character reference exactly: flowing calligraphic "
        "brush outlines of varied weight, soft ink tonal gradients, restrained "
        "mineral-pigment washes (azurite blue, malachite green, cinnabar red) over "
        "black ink, subtle flying-white dry-brush texture, on aged rice-paper; the "
        "subject carries finer brushwork and slightly richer color so it reads first"),
    "gongbi": (
        "Chinese gongbi fine-line painting style matching the attached character "
        "reference exactly: precise even ink outlines, layered translucent mineral "
        "color washes, rich ornamental detail, elegant flat depth on silk"),
    "anime": (
        "Japanese cel-anime illustration style matching the attached character "
        "reference exactly: clean thin outlines, soft gradient cel shading, luminous "
        "color, consistent detail density"),
}
STYLE_DEFAULT = STYLE_PRESETS["western"]

STYLE_SEG = ("A full-bleed 3:4 portrait fantasy card illustration. {style}. "
             "Dramatic cinematic lighting from the single in-scene light source "
             "specified in the scene description; the background is painted in the "
             "same style with lower detail density than the subject so the subject "
             "reads first.")

# 立绘定稿段：先出这一张，锁定当参考图（无场景、无戏、全身可见）
REFERENCE_SEG = (
    "A full-body character reference sheet, front view, neutral standing A-pose. "
    "{style}. Even soft lighting, plain aged rice-paper background. The character "
    "stands calmly, showing the complete costume, hairstyle and signature equipment "
    "clearly; the whole body and the full face are visible and uncropped. This is an "
    "identity turnaround, not a dramatic scene.\n"
    "Character identity: {face}")

# 妖兽版立绘段（无衣饰发型可言，改说体型与解剖特征）
REFERENCE_SEG_BEAST = (
    "A full-body creature reference sheet, side three-quarter view, neutral resting "
    "stance. {style}. Even soft lighting, plain aged rice-paper background. The "
    "creature is shown calmly and completely, displaying its full silhouette, "
    "anatomy, scales or fur, horns and every signature feature clearly; the whole "
    "body is visible and uncropped. This is an identity turnaround, not a dramatic "
    "scene.\n"
    "Creature identity: {face}")

# ② 身份段前缀（共用）
IDENTITY_PREAMBLE = (
    "The attached image defines the character's identity only: keep the same face, "
    "species anatomy, hairstyle, clothing, colors and signature equipment. It does "
    "NOT define the acting - do not copy the reference's pose, expression, camera "
    "angle or framing; the scene description below overrides all of them.")

# ④ 构图段（共用）。水墨的「留白」用渐隐雾气表达，仍需铺满出血，别留纯白空边。
COMPOSITION_SEG = (
    "Portrait 3:4 composition. The scene fills the entire canvas edge to edge, no "
    "borders, no hard vignette. Any negative space is expressed as soft graded mist "
    "or atmosphere, not blank empty margins. Use the cinematic framing specified in "
    "the scene description: like a still from a hanging-scroll painting, the "
    "subject's body may be naturally cropped by the frame, but the face and every "
    "signature feature named in the scene description must stay fully inside the "
    "central safe area, away from the outer 8 percent of every edge, because a card "
    "frame will be overlaid in code.")

# ⑤ 约束段（共用；否定项正说，如「双手清晰可数」）
CONSTRAINTS_SEG = (
    "No text, no letters, no numbers, no seals, no watermark, no signature, no card "
    "frame, no UI elements. No photorealistic rendering, no 3D render, no depth-of-"
    "field blur, no plastic highlights. Hands are clearly and correctly countable; "
    "anatomy is natural and well-formed. No named or recognizable third-party "
    "intellectual property.")


def _read(val: str | None, path: str | None) -> str | None:
    if path:
        with open(path, encoding="utf-8") as f:
            return f.read().strip()
    return val.strip() if val else None


def build_card(face: str | None, scene: str, style: str, no_identity: bool) -> str:
    parts = [STYLE_SEG.format(style=style)]
    if not no_identity:
        seg = IDENTITY_PREAMBLE
        if face:
            seg += f"\nCharacter identity: {face}"
        parts.append(seg)
    parts.append(scene)
    parts.append(COMPOSITION_SEG)
    parts.append(CONSTRAINTS_SEG)
    return "\n\n".join(parts)


def build_reference(face: str, style: str, beast: bool = False) -> str:
    # 立绘阶段没有参考图，剥掉画风预设里为卡面写的「照参考图」那句
    style = style.replace(" matching the attached character reference exactly:", ":")
    seg = REFERENCE_SEG_BEAST if beast else REFERENCE_SEG
    constraints = CONSTRAINTS_SEG
    if beast:  # 妖兽无手，去掉「双手可数」，改说四肢与爪
        constraints = constraints.replace(
            "Hands are clearly and correctly countable; anatomy is natural and "
            "well-formed.",
            "Limbs and claws are clearly and correctly countable; creature anatomy "
            "is natural and well-formed.")
    return "\n\n".join([seg.format(style=style, face=face), constraints])


def main() -> None:
    ap = argparse.ArgumentParser(description="卡牌插画五段拼接生成器")
    ap.add_argument("--face", help="角色身份英文描述（来自 character_sheet）")
    ap.add_argument("--face-file", help="身份描述文件")
    ap.add_argument("--scene", help="场景段（Scene: ... Light source: ...）")
    ap.add_argument("--scene-file", help="场景段文件")
    ap.add_argument("--style-preset", default="western",
                    choices=list(STYLE_PRESETS), help="画风预设")
    ap.add_argument("--style", help="自定义画风整段（覆盖 --style-preset）")
    ap.add_argument("--reference", action="store_true",
                    help="立绘定稿模式：先出这一张当参考图（需 --face）")
    ap.add_argument("--beast", action="store_true",
                    help="妖兽立绘：改说体型解剖，不提衣饰发型")
    ap.add_argument("--no-identity", action="store_true", help="无脸怪物，省身份段")
    args = ap.parse_args()

    style = args.style or STYLE_PRESETS[args.style_preset]
    face = _read(args.face, args.face_file)

    # 立绘定稿模式
    if args.reference:
        if not face:
            print("⚠ 立绘模式需要 --face / --face-file", file=sys.stderr)
            sys.exit(1)
        print(build_reference(face, style, beast=args.beast))
        print("\n" + "-" * 60)
        print("↑ 这是【立绘定稿】prompt，先出这张、满意后存档，作为该角色后续所有卡的参考图")
        return

    # 卡面模式
    scene = _read(args.scene, args.scene_file)
    if not scene:
        print("⚠ 卡面模式必须提供 --scene 或 --scene-file", file=sys.stderr)
        sys.exit(1)
    if not args.no_identity and not face:
        print("⚠ 未提供身份描述（--face / --face-file）。露脸角色强烈建议提供；"
              "确为无脸怪物请加 --no-identity。", file=sys.stderr)

    print(build_card(face, scene, style, args.no_identity))
    if not args.no_identity:
        print("\n" + "-" * 60)
        print("↑ 复制以上 prompt，并【附上该角色的立绘参考图】再发给 GPT/Gemini")


if __name__ == "__main__":
    main()
