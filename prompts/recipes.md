# 配方book · 不同游戏一行出一套

不同游戏 = 不同的「36 格装什么 + 画风 + 视角」。已预置常见小游戏类型，
一行命令出整套 prompt，粘贴到网页版即可。

```bash
python src/gen_prompt.py --list-recipes          # 看所有配方
python src/gen_prompt.py --recipe collect-animals # 出某个游戏的整套 prompt
```

## 预置配方

| 配方名 | 游戏类型 | 36 格内容 | 画风 |
|---|---|---|---|
| `food-shop` | 合成 / 抓取 | 水果蔬菜面包 36 件 | 扁平矢量 |
| `merge-chain` | 合成(2048式) | 6 条进化链 × 6 阶（种子→大树等） | 黏土3D |
| `match3-gems` | 三消 | 6 色宝石 × 6 状态（条纹/炸弹/彩虹…） | 拟真 |
| `collect-animals` | 收集 / 图鉴 | 36 只可爱动物 | 扁平矢量 |
| `collect-monsters` | 收集 / 放置 | 36 只 Q 版怪物 | 黏土3D |
| `powerups-ui` | 通用道具 / UI | 金币/道具/按钮 36 个 | 扁平矢量 |

## 换画风 / 视角 / 背景（覆盖配方默认）

配方带了推荐画风，但你随时能盖掉：
```bash
# 用怪物配方，但改成像素风、深色背景
python src/gen_prompt.py --recipe collect-monsters --style pixel --bg "#101018"
```

## 做你自己游戏的配方

编辑 `src/recipes.py`，照格式加一条（items 必须正好 36 个）：
```python
"my-space-game": {
    "desc": "太空射击 · 敌机与道具",
    "style": "flat", "view": "front view", "bg": "#0B1020",
    "items": ["small ufo", "scout ship", "...", "boss mothership"],  # 36 个
},
```
之后 `python src/gen_prompt.py --recipe my-space-game` 即可。

## 一次做多个游戏的建议流程

1. `--list-recipes` 挑一个想做的游戏类型。
2. 生成 prompt → 网页版 GPT/Gemini 出图 → 存 `input/<游戏名>.png`。
3. `python src/run.py input/<游戏名>.png -r 6 -c 6 --size 96 --autocrop`。
4. 看 `output/<游戏名>/contact_cutouts.png` 判定。
5. 换下一个配方，重复。每个游戏产物按名字分目录，互不干扰。

> 小提示：三消/宝石这类「同物件不同状态」的，把 `--view front view` 保持一致最重要；
> 图鉴/动物这类「不同物件」的，一致性主要靠画风词锁死。
