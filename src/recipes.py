"""按游戏类型预置的 36 格配方。每个配方 = 画风 + 视角 + 背景 + 36 个内容。

被 gen_prompt.py 用 --recipe NAME 调用。想加自己的游戏，照格式往 RECIPES 里加一条即可。
"""
from __future__ import annotations

# style 用 gen_prompt.STYLES 里的键（flat/clay/handdrawn/pixel/line/realistic）
# items 必须正好 36 个
RECIPES: dict[str, dict] = {

    # 合成类（食物摊）——36 个同风格食材，可做合成盘 / 抓取盘
    "food-shop": {
        "desc": "合成/抓取类 · 食物摊 36 件",
        "style": "flat", "view": "3/4 top-down view", "bg": "#F2EFE9",
        "items": [
            "red apple", "green apple", "banana", "orange", "lemon", "watermelon",
            "strawberry", "cherry", "grapes", "peach", "pear", "pineapple",
            "mango", "kiwi", "blueberry", "avocado", "coconut", "lychee",
            "tomato", "carrot", "corn", "broccoli", "eggplant", "pumpkin",
            "potato", "onion", "chili pepper", "mushroom", "cucumber", "lettuce",
            "bread loaf", "milk carton", "egg", "cheese wedge", "honey jar", "jam jar",
        ],
    },

    # 合成类（进化链）——同一主题从小到大 6 阶 ×6 组，适合 2048 式合成
    "merge-chain": {
        "desc": "合成类 · 进化链（6 组各 6 阶，从小到大）",
        "style": "clay", "view": "isometric 3/4 view", "bg": "#EDE7DE",
        "items": [
            # 每行一条进化链，从最小到最大
            "tiny seed", "small sprout", "young plant", "flower bud", "blooming flower", "fruit tree",
            "egg", "hatchling", "baby bird", "young bird", "adult bird", "majestic phoenix",
            "pebble", "small rock", "boulder", "crystal shard", "gem cluster", "diamond",
            "spark", "small flame", "campfire", "bonfire", "fireball", "sun",
            "droplet", "puddle", "pond", "wave", "whirlpool", "ocean",
            "acorn", "sapling", "small bush", "young tree", "big tree", "giant ancient tree",
        ],
    },

    # 三消——6 种基础棋子 ×6 种状态（普通/条纹/包装/炸弹/彩虹/闪光）
    "match3-gems": {
        "desc": "三消 · 6 色宝石 ×6 状态",
        "style": "realistic", "view": "front view", "bg": "#20242E",
        "items": [
            "red gem normal", "red gem with vertical stripes", "red gem wrapped glow",
            "red gem with bomb core", "red gem rainbow shimmer", "red gem sparkling",
            "blue gem normal", "blue gem with vertical stripes", "blue gem wrapped glow",
            "blue gem with bomb core", "blue gem rainbow shimmer", "blue gem sparkling",
            "green gem normal", "green gem with vertical stripes", "green gem wrapped glow",
            "green gem with bomb core", "green gem rainbow shimmer", "green gem sparkling",
            "yellow gem normal", "yellow gem with vertical stripes", "yellow gem wrapped glow",
            "yellow gem with bomb core", "yellow gem rainbow shimmer", "yellow gem sparkling",
            "purple gem normal", "purple gem with vertical stripes", "purple gem wrapped glow",
            "purple gem with bomb core", "purple gem rainbow shimmer", "purple gem sparkling",
            "white gem normal", "white gem with vertical stripes", "white gem wrapped glow",
            "white gem with bomb core", "white gem rainbow shimmer", "white gem sparkling",
        ],
    },

    # 图鉴收集——36 只可爱动物
    "collect-animals": {
        "desc": "收集/图鉴 · 36 只动物",
        "style": "flat", "view": "front view", "bg": "#EAF2F8",
        "items": [
            "cat", "dog", "rabbit", "fox", "bear", "panda",
            "tiger", "lion", "elephant", "giraffe", "zebra", "monkey",
            "koala", "kangaroo", "hedgehog", "squirrel", "raccoon", "owl",
            "penguin", "seal", "whale", "dolphin", "octopus", "crab",
            "frog", "turtle", "snake", "chameleon", "parrot", "flamingo",
            "duck", "chicken", "pig", "cow", "sheep", "horse",
        ],
    },

    # 怪物图鉴——36 只 Q 版怪物
    "collect-monsters": {
        "desc": "收集/放置 · 36 只 Q 版怪物",
        "style": "clay", "view": "front view", "bg": "#1E2233",
        "items": [
            "slime blob", "fire imp", "ice sprite", "rock golem", "leaf spirit", "shadow ghost",
            "spiky cactus monster", "one-eyed blob", "bat creature", "mushroom monster",
            "electric jellyfish", "water droplet spirit", "wind fairy", "lava beast",
            "crystal turtle", "thorn vine monster", "cloud puff", "star sprite",
            "pumpkin ghost", "snow yeti", "sand scorpion", "coral creature",
            "flame bird", "moon rabbit spirit", "toxic frog", "metal beetle",
            "flower dragon", "ink octopus", "candy golem", "bubble fish",
            "leaf turtle", "spark mouse", "gem snail", "vine serpent",
            "ember fox", "frost owl",
        ],
    },

    # 道具 / UI——通用游戏道具与货币图标
    "powerups-ui": {
        "desc": "通用道具/UI · 36 个",
        "style": "flat", "view": "front view", "bg": "#F2EFE9",
        "items": [
            "gold coin", "gem/diamond", "heart life", "star", "key", "treasure chest",
            "bomb", "hourglass timer", "magnet", "shield", "lightning bolt", "hammer",
            "shuffle arrows", "rainbow ball", "hint bulb", "double coin", "rocket booster", "clock add-time",
            "potion red", "potion blue", "potion green", "scroll", "map", "compass",
            "trophy", "medal", "crown", "ribbon badge", "gift box", "balloon",
            "settings gear", "sound icon", "pause bars", "home house", "play triangle", "lock",
        ],
    },
}


def get(name: str) -> dict | None:
    return RECIPES.get(name)


def names() -> list[str]:
    return list(RECIPES)
