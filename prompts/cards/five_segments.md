# 五段拼接 prompt

每张卡 = 5 段逐字拼接。**四段共用**（36 张原样复制），**只有场景段每张现写**。

```
[画风段] + [身份段] + [场景段] + [构图段] + [约束段]
   共用       半共用      每张写      共用       共用
```

---

## ① 画风段（36 张共用）

> 想换成非《谜宫》画风，只改这一段的风格措辞，其余不动。

```
A full-bleed 3:4 portrait fantasy card illustration. Western painted
cartoon style matching the attached character reference exactly: bold
thick dark outlines, solid dimensional color blocks, flat colors with
simple cel shading, consistent detail density. Dramatic cinematic
lighting from the single in-scene light source specified in the scene
description; the background is painted in the same style with lower
detail density than the subject so the subject reads first.
```

## ② 身份段（前缀共用 + 接角色身份描述）

前缀共用，讲清「参考图只管你是谁，不管你在干什么」：

```
The attached image defines the character's identity only: keep the
same face, species anatomy, hairstyle, clothing, colors and signature
equipment. It does NOT define the acting — do not copy the reference's
pose, expression, camera angle or framing; the scene description below
overrides all of them.
Character identity: {{把 character_sheet 里那段身份英文描述贴这里}}
```

> 露脸角色必须**附上该角色立绘做参考图**。没有脸的怪物（如龙）可省身份英文，
> 重点全放场景段的镜头。

## ③ 场景段（★ 每张卡唯一要写的）

写清「这个角色在此刻的哪个瞬间」。写法三心得见文末。模板：

```
Scene: {{地点/环境}}, {{机位与取景，用故事化语言}}. {{角色在做什么动作、
什么神态，写成一个正在发生的瞬间}}. {{可选：背景里的次要元素}}.
Light source: {{有来历的光源，说清从哪来、照哪}}.
```

## ④ 构图段（36 张共用）

最后那句「安全区」是因为卡框会在代码里叠上去：

```
Portrait 3:4 composition. The background scene fills the entire canvas edge
to edge, no borders, no vignette, no empty margins. Use the cinematic framing
specified in the scene description: like a movie still, the subject's body
may be naturally cropped by the frame, but the face and every signature
feature named in the scene description must stay fully inside the central
safe area, away from the outer 8 percent of every edge, because a card frame
will be overlaid in code.
```

## ⑤ 约束段（36 张共用）

```
No text, no letters, no numbers, no watermark, no signature, no card frame,
no UI elements, no photorealistic rendering, no depth-of-field blur, no
plastic highlights, no malformed anatomy, no extra fingers, no named or
recognizable third-party intellectual property.
```

---

## 场景段三心得

1. **光源要有来历**。别写 `dramatic lighting` 这种空话。写「闯入者手里那支火把」
   「她胸口的圣徽」——光有出处，画面才有戏。
2. **姿势、机位写进故事**。「她像给来宾引路一样朝走廊深处礼貌摆手」远胜
   `waist-up shot, 45 degrees`。模型懂「情境」远超懂「参数」。
3. **约束正着说**。想避免多手就写「双手清晰可数」，别写「不要画多手」——
   模型对否定词执行力很差。

---

## 场景段范例（直接感受写法）

**怪物·红龙**（没脸的物种，重点全在镜头）
```
Scene: the deepest treasure vault of the dungeon, seen from the
intruder's eye level. Low-angle close-up: the red dragon's huge head,
neck and one clawed forefoot dominate the frame, rising over a slope
of gold coins and goblets. Its half-open yellow eye with a narrowed
pupil stares straight at the viewer; a thin wisp of smoke rises from
one nostril. A few coins slide down the pile beneath its claw.
Light source: warm torch light from the lower front, as if from the
intruder's own torch.
```

**角色·死灵法师**（人设：对活人不耐烦，对死者彬彬有礼）
```
Scene: a green-lit crypt corridor. The necromancer stands at the side of the
corridor with courtly poise, one hand holding an open roster book with wisps
of green soul-fire floating above its pages like candle flames, the other
hand gesturing politely down the corridor as if ushering guests through. Her
skull-topped staff rests in the crook of her arm. Deeper in the corridor
behind her, a few vague skeletal silhouettes walk away in an orderly line
into the darkness. Light source: the green soul-fire, lighting her gaunt face
from the lower front.
```

**角色·牧师**（别人举火把，她自己就是那点光）
```
Scene: the threshold where a lit dungeon camp gives way to a pitch-dark
corridor, chest-up framing in three-quarter view. The priestess walks calmly
forward into the darkness, ahead of everyone, her thumb mid-count on a string
of worn prayer beads held at her chest. Her cleric veil frames her oval face;
her soft narrow eyes look ahead into the dark with a faint serene smile,
utterly unafraid. The golden sun emblem on her chest gives off a gentle glow
that lights the first step of the darkness before her. Behind her at the
frame edge, warm torchlight of the camp she is leaving recedes. Light source:
the soft golden glow of her sun emblem from her chest, with warm torchlight
falling off behind her.
```
