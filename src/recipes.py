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
        "style": "flat",
        "view": "3/4 top-down view",
        "bg": "#F2EFE9",
        "items": [
            "red apple",
            "green apple",
            "banana",
            "orange",
            "lemon",
            "watermelon",
            "strawberry",
            "cherry",
            "grapes",
            "peach",
            "pear",
            "pineapple",
            "mango",
            "kiwi",
            "blueberry",
            "avocado",
            "coconut",
            "lychee",
            "tomato",
            "carrot",
            "corn",
            "broccoli",
            "eggplant",
            "pumpkin",
            "potato",
            "onion",
            "chili pepper",
            "mushroom",
            "cucumber",
            "lettuce",
            "bread loaf",
            "milk carton",
            "egg",
            "cheese wedge",
            "honey jar",
            "jam jar",
        ],
    },
    # 合成类（进化链）——同一主题从小到大 6 阶 ×6 组，适合 2048 式合成
    "merge-chain": {
        "desc": "合成类 · 进化链（6 组各 6 阶，从小到大）",
        "style": "clay",
        "view": "isometric 3/4 view",
        "bg": "#EDE7DE",
        "items": [
            # 每行一条进化链，从最小到最大
            "tiny seed",
            "small sprout",
            "young plant",
            "flower bud",
            "blooming flower",
            "fruit tree",
            "egg",
            "hatchling",
            "baby bird",
            "young bird",
            "adult bird",
            "majestic phoenix",
            "pebble",
            "small rock",
            "boulder",
            "crystal shard",
            "gem cluster",
            "diamond",
            "spark",
            "small flame",
            "campfire",
            "bonfire",
            "fireball",
            "sun",
            "droplet",
            "puddle",
            "pond",
            "wave",
            "whirlpool",
            "ocean",
            "acorn",
            "sapling",
            "small bush",
            "young tree",
            "big tree",
            "giant ancient tree",
        ],
    },
    # 三消——6 种基础棋子 ×6 种状态（普通/条纹/包装/炸弹/彩虹/闪光）
    "match3-gems": {
        "desc": "三消 · 6 色宝石 ×6 状态",
        "style": "realistic",
        "view": "front view",
        "bg": "#20242E",
        "items": [
            "red gem normal",
            "red gem with vertical stripes",
            "red gem wrapped glow",
            "red gem with bomb core",
            "red gem rainbow shimmer",
            "red gem sparkling",
            "blue gem normal",
            "blue gem with vertical stripes",
            "blue gem wrapped glow",
            "blue gem with bomb core",
            "blue gem rainbow shimmer",
            "blue gem sparkling",
            "green gem normal",
            "green gem with vertical stripes",
            "green gem wrapped glow",
            "green gem with bomb core",
            "green gem rainbow shimmer",
            "green gem sparkling",
            "yellow gem normal",
            "yellow gem with vertical stripes",
            "yellow gem wrapped glow",
            "yellow gem with bomb core",
            "yellow gem rainbow shimmer",
            "yellow gem sparkling",
            "purple gem normal",
            "purple gem with vertical stripes",
            "purple gem wrapped glow",
            "purple gem with bomb core",
            "purple gem rainbow shimmer",
            "purple gem sparkling",
            "white gem normal",
            "white gem with vertical stripes",
            "white gem wrapped glow",
            "white gem with bomb core",
            "white gem rainbow shimmer",
            "white gem sparkling",
        ],
    },
    # 图鉴收集——36 只可爱动物
    "collect-animals": {
        "desc": "收集/图鉴 · 36 只动物",
        "style": "flat",
        "view": "front view",
        "bg": "#EAF2F8",
        "items": [
            "cat",
            "dog",
            "rabbit",
            "fox",
            "bear",
            "panda",
            "tiger",
            "lion",
            "elephant",
            "giraffe",
            "zebra",
            "monkey",
            "koala",
            "kangaroo",
            "hedgehog",
            "squirrel",
            "raccoon",
            "owl",
            "penguin",
            "seal",
            "whale",
            "dolphin",
            "octopus",
            "crab",
            "frog",
            "turtle",
            "snake",
            "chameleon",
            "parrot",
            "flamingo",
            "duck",
            "chicken",
            "pig",
            "cow",
            "sheep",
            "horse",
        ],
    },
    # 怪物图鉴——36 只 Q 版怪物
    "collect-monsters": {
        "desc": "收集/放置 · 36 只 Q 版怪物",
        "style": "clay",
        "view": "front view",
        "bg": "#1E2233",
        "items": [
            "slime blob",
            "fire imp",
            "ice sprite",
            "rock golem",
            "leaf spirit",
            "shadow ghost",
            "spiky cactus monster",
            "one-eyed blob",
            "bat creature",
            "mushroom monster",
            "electric jellyfish",
            "water droplet spirit",
            "wind fairy",
            "lava beast",
            "crystal turtle",
            "thorn vine monster",
            "cloud puff",
            "star sprite",
            "pumpkin ghost",
            "snow yeti",
            "sand scorpion",
            "coral creature",
            "flame bird",
            "moon rabbit spirit",
            "toxic frog",
            "metal beetle",
            "flower dragon",
            "ink octopus",
            "candy golem",
            "bubble fish",
            "leaf turtle",
            "spark mouse",
            "gem snail",
            "vine serpent",
            "ember fox",
            "frost owl",
        ],
    },
    # 道具 / UI——通用游戏道具与货币图标
    "powerups-ui": {
        "desc": "通用道具/UI · 36 个",
        "style": "flat",
        "view": "front view",
        "bg": "#F2EFE9",
        "items": [
            "gold coin",
            "gem/diamond",
            "heart life",
            "star",
            "key",
            "treasure chest",
            "bomb",
            "hourglass timer",
            "magnet",
            "shield",
            "lightning bolt",
            "hammer",
            "shuffle arrows",
            "rainbow ball",
            "hint bulb",
            "double coin",
            "rocket booster",
            "clock add-time",
            "potion red",
            "potion blue",
            "potion green",
            "scroll",
            "map",
            "compass",
            "trophy",
            "medal",
            "crown",
            "ribbon badge",
            "gift box",
            "balloon",
            "settings gear",
            "sound icon",
            "pause bars",
            "home house",
            "play triangle",
            "lock",
        ],
    },
    # ── Roguelike 三件套（打怪升级）：敌人 / 构筑物品 / 主角形态 ──
    # 三张一起出，就够拼一屏 demo 看效果。三张必须同画风同背景色。
    #
    # 背景色为什么是荧光品红：实测第一版用暗色 #1B1E2B，深色素材（黑炸弹、黑蜘蛛、
    # 铁链暗部）与背景明度太近，flood-fill 直接把物体啃穿。换中性亮色也不行——浅色
    # 素材（骷髅、面具）又会被啃。这批素材色域已覆盖红橙黄绿蓝紫棕灰黑，只有荧光
    # 品红是绝不会出现的空档，故按绿幕思路选它，对亮暗素材都留足色差。
    # 代价：原网格图看不出暗调氛围，且边缘可能有品红溢色（rembg 去背时无此问题）。
    # 敌人图鉴——6 个族群 ×6 阶（小怪→精英→BOSS），最后一行是 6 个 BOSS
    "rogue-enemies": {
        "desc": "Roguelike · 敌人 36 只（5 族群各 6 阶 + 1 行 BOSS）",
        "style": "handdrawn",
        "view": "side three-quarter view",
        "bg": "#FF00FF",
        "items": [
            # 每行一个族群，从最弱到最强
            "small green slime",
            "big green slime",
            "acid slime with bubbles",
            "slime with a crown",
            "split slime pair",
            "giant king slime",
            "small bat",
            "swarm bat",
            "vampire bat with red eyes",
            "stone gargoyle",
            "winged demon imp",
            "horned demon brute",
            "skeleton with rusty sword",
            "skeleton archer",
            "armored skeleton knight",
            "skeleton mage with staff",
            "bone hound",
            "bone colossus",
            "mushroom sprout creature",
            "spore mushroom monster",
            "toxic mushroom walker",
            "carnivorous plant",
            "thorn vine beast",
            "ancient treant",
            "rat scavenger",
            "goblin scout with dagger",
            "goblin brute with club",
            "orc warrior with axe",
            "orc shaman with totem",
            "orc warlord in heavy armor",
            # BOSS 行：体型更大、剪影更独特
            "boss: massive lava golem cracked with molten veins",
            "boss: frost dragon whelp with ice spines",
            "boss: shadow reaper in a tattered cloak with a scythe",
            "boss: many-eyed void horror with tentacles",
            "boss: clockwork war machine with saw arms",
            "boss: crowned lich holding a soul orb",
        ],
    },
    # 构筑物品——roguelike 的核心：武器 / 遗物 / 药水 / 技能符文 / 强化 / 诅咒
    "rogue-relics": {
        "desc": "Roguelike · 构筑物品 36 个（武器/遗物/药水/符文/强化/诅咒）",
        "style": "handdrawn",
        "view": "front view",
        "bg": "#FF00FF",
        "items": [
            # 武器
            "short sword",
            "great axe",
            "war hammer",
            "hunting bow",
            "twin daggers",
            "magic staff",
            # 防具
            "round wooden shield",
            "iron helmet",
            "leather chestplate",
            "steel gauntlet",
            "traveler cloak",
            "enchanted boots",
            # 药水 / 消耗品
            "red healing potion",
            "blue mana potion",
            "green poison flask",
            "golden elixir",
            "burning bomb flask",
            "smoke bomb",
            # 技能符文
            "fire rune stone",
            "ice rune stone",
            "lightning rune stone",
            "poison rune stone",
            "holy light rune stone",
            "shadow rune stone",
            # 遗物 / 强化
            "beating heart relic",
            "hourglass relic",
            "four-leaf clover charm",
            "ancient spell tome",
            "golden crown relic",
            "winged amulet",
            # 诅咒 / 负面
            "cracked cursed skull",
            "broken chain shackle",
            "black spider idol",
            "bleeding dagger curse",
            "hollow mask curse",
            "rotting hand curse",
        ],
    },
    # 主角动作表——同一个角色的 36 个动作/状态
    #
    # 这张只改「状态」，不改「设计」：带 bible 字段，gen_prompt 会切到 TEMPLATE_CHARACTER。
    # 初版曾把「破布→黄金甲」的等级成长塞进来，那是在改角色设计本身，和「36 格保持同一
    # 角色」直接打架（character_forms.md：别一次改太多维度）。换装成长应当单独出，
    # 用 gen_card.py 逐张出立绘，或先定稿一张再走 add_item.md 的参考图补图流程。
    "rogue-hero": {
        "desc": "Roguelike · 主角 36 动作/状态（同一角色）",
        "style": "handdrawn",
        "view": "side three-quarter view",
        "bg": "#FF00FF",
        # 角色圣经：越具体越不漂。想换主角设定就改这一段，36 格会整体跟着变。
        "bible": (
            "A young human adventurer, slim athletic build, chin-length messy dark "
            "brown hair, a red headband, light brown leather chestplate over a "
            "cream tunic, dark green trousers, worn brown boots, a small round "
            "wooden shield strapped on the left forearm, and a plain steel short "
            "sword in the right hand. Cartoon proportions with a slightly large "
            "head, no cape, no helmet, no backpack."
        ),
        "items": [
            # 基础动作
            "idle standing at rest",
            "walking",
            "running",
            "jumping upward",
            "dodge-rolling sideways",
            "crouching low",
            # 战斗动作
            "a horizontal sword slash",
            "a heavy overhead sword attack",
            "a forward thrust with the sword",
            "blocking with the shield raised",
            "a shield bash forward",
            "recovering after a swing, sword lowered",
            # 状态（增益）
            "surrounded by a blue shield bubble",
            "glowing red with rage",
            "wrapped in golden holy light",
            "speeding with wind trails",
            "with floating healing sparkles",
            "with a fire aura",
            # 状态（减益）
            "poisoned with a sickly green tint",
            "frozen inside a block of ice",
            "stunned with stars circling the head",
            "burning with flames",
            "bleeding and limping",
            "cursed with dark purple smoke",
            # 受击 / 生死
            "taking a hit and recoiling backward",
            "knocked down on one knee, low on health",
            "lying defeated on the ground",
            "getting back up from the ground",
            "panting and exhausted, hands on knees",
            "shrugging off a hit, unfazed",
            # 关卡交互
            "drinking a potion",
            "opening a treasure chest",
            "picking up a coin from the ground",
            "reading an open map",
            "sitting at a campfire resting",
            "raising a relic overhead in victory",
        ],
    },
    # ══ 仙侠 roguelike（正式方向）══
    #
    # 与上面西幻那三条的关系：西幻是拿来验证管线能不能出图的，已验证完，别换皮复用。
    # 画风统一 shuimo，和 prompts/cards/set_xianxia_shuimo.md 的 12 角色套系同源，
    # 那套已有的角色（青岚/玄冥/绯月/凌霄…）直接当本作的角色与 BOSS，不重画。
    # 背景同样用 #FF00FF 走 --chroma，理由见 prompts/README.md 的铁律 1。
    # 法宝丹药符箓——仙侠版的构筑物品，对应西幻的 rogue-relics
    "xianxia-relics": {
        "desc": "仙侠 · 法宝/丹药/符箓 36 件",
        "style": "shuimo",
        "view": "front view",
        "bg": "#FF00FF",
        "items": [
            # 法宝飞剑
            "a slender flying sword with a jade pommel",
            "a horsetail whisk (fuchen) with white strands",
            "a ruyi scepter of green jade",
            "an embroidered qiankun pouch",
            "a bronze demon-revealing mirror",
            "a luopan compass with concentric rings",
            # 丹药
            "a glowing golden immortality pill",
            "a jade-green healing elixir pill",
            "a crimson qi-gathering pill",
            "a swirling black-and-white breakthrough pill",
            "a murky purple poison pill",
            "a pill furnace (dan ding) with three legs",
            # 符箓
            "a fire talisman strip with vermilion script",
            "a thunder talisman strip crackling with sparks",
            "an ice talisman strip rimed with frost",
            "a demon-warding talisman strip",
            "an earth-escape talisman strip",
            "a golden protection talisman strip",
            # 灵材
            "a lingzhi immortal mushroom",
            "a ginseng root shaped like a small figure",
            "a lump of translucent jade marrow",
            "a beast core orb glowing from within",
            "a single iridescent dragon scale",
            "a long phoenix tail feather",
            # 法器配饰
            "a carved jade pendant on a silk cord",
            "a string of dark prayer beads",
            "a jade slip tablet inscribed with script",
            "a cluster of raw spirit stones",
            "a gourd flask with a cork stopper",
            "a small bronze incense censer with smoke",
            # 邪物诅咒
            "a blood-red jade carved with a coiled worm",
            "a sealed clay jar of gu insects",
            "a bone flute carved with tiny skulls",
            "a soul-binding chain of dark iron",
            "a cracked demonic ritual mask",
            "a tattered soul-summoning banner on a pole",
        ],
    },
    # 妖兽邪修——6 族群 ×6 阶，末行 BOSS
    "xianxia-enemies": {
        "desc": "仙侠 · 敌人 36 只（5 族群各 6 阶 + 1 行 BOSS）",
        "style": "shuimo",
        "view": "side three-quarter view",
        "bg": "#FF00FF",
        "items": [
            # 山精野怪
            "a small mountain sprite made of moss and stone",
            "a one-tailed fox spirit",
            "a three-tailed fox spirit in robes",
            "a tree demon with a face in its bark",
            "a boar demon with iron tusks",
            "a nine-tailed fox demon in flowing robes",
            # 阴魂僵尸
            "a drifting pale wisp ghost",
            "a hopping jiangshi corpse with a talisman on its forehead",
            "an armored jiangshi general",
            "a long-haired vengeful female ghost",
            "a chain-dragging shackled soul",
            "a towering corpse king with blackened claws",
            # 蛇蛟
            "a green spirit serpent",
            "a horned python demon",
            "a scaled jiao dragon with short horns",
            "a serpent woman with a coiled tail",
            "a two-headed venom serpent",
            "a storm-wreathed jiao dragon rising",
            # 虫蛊
            "a swarm of black gu insects",
            "a giant centipede demon",
            "a jade spider with a marked back",
            "a moth spirit with powdered wings",
            "a scorpion demon with a raised tail",
            "a gu queen fused with insect limbs",
            # 邪修
            "a masked cultist disciple with a dagger",
            "a blood-robed cultist channeling qi",
            "a bone-armored demonic swordsman",
            "a puppet master with strung marionettes",
            "a corpse-raising necromancer with a bell",
            "a demonic elder wreathed in black qi",
            # BOSS
            "boss: a colossal ink-black dragon coiling through clouds",
            "boss: a white-boned immortal skeleton in tattered robes",
            "boss: a many-armed demon statue come alive",
            "boss: a vast disembodied eye ringed with talismans",
            "boss: a heavenly tribulation demon formed of black lightning",
            "boss: a nine-tailed fox empress in full ceremonial robes",
        ],
    },
    # 主角动作表——用套系里的 M1 青岚·剑修当默认主角（faces/m1_qinglan.txt 同源）
    # 想换主角就把 bible 换成 set_xianxia_shuimo.md 里另一个角色的身份描述。
    "xianxia-hero": {
        "desc": "仙侠 · 主角 36 动作/状态（青岚·剑修）",
        "style": "shuimo",
        "view": "side three-quarter view",
        "bg": "#FF00FF",
        # bible 只该钉「是谁」，不该顺带钉「怎么画」。上一版写的是立绘式五官描述
        # （明亮的丹凤眼、高挺鼻梁……），那套语汇本身就在把模型往动漫立绘上拽，
        # 和 STYLE 打架。这版把五官压到最简，并显式要求用笔墨方式交代，
        # 同时把眉心朱砂痣升成 must（上一版它在 36 格里基本全丢了）。
        "bible": (
            "A young male sword cultivator, slim and upright, apparent age early "
            "20s: black hair gathered in a high topknot bound by a jade pin, "
            "flowing azure daoist robes with wide sleeves, and a slender straight "
            "jian sword. No armor, no hat. He MUST have a single small vermilion "
            "cinnabar dot in the middle of his forehead between the brows - this "
            "is his signature mark and must be clearly visible in every cell. "
            "His face is indicated with only a few economical ink strokes for the "
            "brows, eyes and mouth - do not render detailed or realistic facial "
            "features, and do not enlarge or stylize the eyes."
        ),
        "items": [
            # 基础
            "standing calmly at rest",
            "walking",
            "running",
            "leaping upward",
            "gliding on a flying sword",
            "seated cross-legged in meditation",
            # 剑招
            "a horizontal sword slash",
            "a downward sword strike",
            "a forward sword thrust",
            "drawing the sword from its scabbard",
            "sword held in a defensive guard",
            "sheathing the sword, back turned",
            # 御剑法术
            "controlling several flying swords in the air",
            "forming a hand seal with two fingers raised",
            "releasing a sword-qi arc",
            "channeling qi into a talisman strip",
            "summoning a protective qi barrier",
            "calling down a lightning strike",
            # 状态（增益）
            "wreathed in swirling azure spirit qi",
            "glowing with golden protective light",
            "surrounded by drifting sword-qi motes",
            "moving fast with trailing afterimages",
            "healing with soft green light",
            "eyes alight during a cultivation breakthrough",
            # 状态（减益）
            "poisoned, veins darkened",
            "bound by black demonic chains",
            "frozen over with frost",
            "burning with dark qi flames",
            "wounded and bleeding at the shoulder",
            "qi-deviated, hair and robes thrashing wildly",
            # 受击 / 交互
            "recoiling from a hit",
            "kneeling on one knee, exhausted",
            "lying defeated on the ground",
            "swallowing a pill",
            "opening a jade slip to read it",
            "raising a treasure overhead in victory",
        ],
    },
    # 战斗特效——飞剑拖尾、命中爆点、buff 光环这些，游戏里没有它们就只是「方块碰方块」。
    # 特效格外怕 shuimo 的晕染：半透明的雾/光在 chroma 抠图时会被连着背景一起吃掉，
    # 所以这条额外要求「实心笔触 + 硬边」，透明度交给引擎的 opacity/加色混合去做。
    "xianxia-vfx": {
        "desc": "仙侠 · 战斗特效 36 个（剑气/命中/弹道/增益/减益/环境）",
        "style": "shuimo",
        "view": "front view, flat symmetrical layout",
        "bg": "#FF00FF",
        "items": [
            # 剑气斩击
            "a horizontal crescent sword-qi slash arc",
            "a downward vertical sword-qi cleave",
            "a forward piercing sword-qi cone",
            "an expanding ring of sword-qi",
            "a fan of many small flying swords",
            "a downpour of sword-qi streaks",
            # 命中爆点
            "a small four-point impact spark",
            "a large critical-hit star burst",
            "a blocked-hit fan of deflection sparks",
            "a scatter of crimson blood droplets",
            "a shattering burst of ice shards",
            "a branching lightning impact flash",
            # 元素弹道
            "a compact fireball with a short flame tail",
            "a sharp ice spike projectile",
            "a crackling ball of lightning",
            "a curved blade of wind",
            "a ball of murky green poison mist",
            "a golden radiant light bolt",
            # 增益光环
            "a spherical protective qi barrier",
            "a trail of three fading speed afterimages",
            "a golden shield sigil ring",
            "a rising swirl of soft green healing light",
            "a ring of orbiting sword-qi motes",
            "an upward pillar of breakthrough qi",
            # 减益标记
            "rising bubbles of green poison",
            "a jagged frost crust marker",
            "a cluster of dark burning flames",
            "a loop of binding black iron chain",
            "a drooping gray weakness sigil",
            "a ring of circling stun stars",
            # 环境交互
            "a vertical pickup light beam",
            "a circular teleport formation seal",
            "a flat circular spell formation of seal script",
            "a rising wisp of spirit qi",
            "a low ring of landing dust",
            "a dense tribulation thundercloud",
        ],
    },
    # UI 图标——只放「整图直接用」的图标和角饰。
    # 刻意不含面板底 / 血条槽 / 按钮底：那些要九宫格拉伸，缩到 96px 再拉会糊，
    # 得走 SCENES 里的单图流程按实际尺寸出，见 prompts/README.md「两条产线」。
    "xianxia-ui": {
        "desc": "仙侠 · UI 图标 36 个（品阶框/功能/属性/状态/货币/装饰）",
        "style": "shuimo",
        "view": "front view, flat symmetrical layout",
        "bg": "#FF00FF",
        "items": [
            # 品阶框（空框，中间留空放物品图）
            "an empty square item frame of plain gray stone",
            "an empty square item frame of green bamboo",
            "an empty square item frame of blue jade",
            "an empty square item frame of purple lacquer",
            "an empty square item frame of gold filigree",
            "an empty square item frame wreathed in black demonic qi",
            # 功能图标
            "a settings gear shaped like a bagua trigram disc",
            "a drawstring pouch for the inventory",
            "an unrolled map scroll",
            "a pause symbol of two vertical jade bars",
            "a small bronze bell for sound",
            "a backward-curving return arrow",
            # 属性图标
            "a small sword silhouette for attack",
            "a round shield sigil for defense",
            "a running footprint for movement speed",
            "a stopwatch-like spiral for attack speed",
            "a four-point star for critical rate",
            "a droplet-shaped heart for max health",
            # 状态图标
            "a red qi-blood droplet",
            "a blue spirit-qi swirl",
            "a golden ascending step for cultivation realm",
            "a crossed pair of small swords for battle",
            "a closed lotus for meditation",
            "a cracked circle for a broken state",
            # 货币与资源
            "a single hexagonal spirit stone",
            "a small stack of three spirit stones",
            "a round copper coin with a square hole",
            "an ingot of silver",
            "a rolled jade slip tablet",
            "a folded paper talisman",
            # 装饰角饰
            "a single curling cloud-pattern corner ornament",
            "a horizontal cloud-pattern divider bar",
            "a square vermilion seal stamp, blank inside",
            "a single dry-brush ink stroke accent",
            "a small lotus blossom ornament",
            "a hanging sword tassel with a knot",
        ],
    },
    # 首领动作表——xianxia-enemies 里每只 boss 只有一格站姿，而关底首领是一局唯一的
    # 高光，静态一帧撑不住出场、蓄力、狂暴、倒地这一整套表演。所以 boss 单独占一张
    # 网格，规格对齐 xianxia-hero：带 bible 钉死身份，36 格只画同一只。
    # 身份取套系里的 B1 墨龙（prompts/cards/faces/b1_molong.txt 同源），卡面和参考图
    # 都已经出过，是当前一致性最稳的一只。换首领就换 bible。
    "xianxia-boss-molong": {
        "desc": "仙侠 · 首领 36 动作/状态（墨龙）",
        "style": "shuimo",
        "view": "side three-quarter view",
        "bg": "#FF00FF",
        "bible": (
            "A colossal ancient Chinese ink dragon with a single unbroken "
            "serpentine scaled body running continuously from its head to "
            "exactly one tail, the tail ending in a single tuft; antlered "
            "stag-like horns, a maned ridge running down its spine, long "
            "trailing whiskers, exactly four clawed legs, blank pale-white eyes "
            "with no visible pupil, scales rendered as layered wet ink washes in "
            "black and deep indigo with faint azurite highlights, an animal "
            "dragon head with no human features."
        ),
        "items": [
            # 出场
            "coiled at rest, head raised",
            "descending out of the clouds",
            "rearing up and roaring",
            "hovering in place, body slowly undulating",
            "circling in flight seen from the side",
            "landing heavily, claws braced",
            # 近身攻击
            "swiping with a front claw",
            "biting forward with jaws open",
            "lashing with its tail",
            "body-slamming forward",
            "sweeping both front claws outward",
            "coiling around to constrict",
            # 远程 / 法术
            "breathing a torrent of black ink",
            "gathering a sphere of dark qi before its jaws",
            "calling down forked lightning from above",
            "summoning a storm of rain and wind",
            "beating its whiskers to send out shockwave rings",
            "spitting a barrage of ink bolts",
            # 蓄力 / 阶段转换
            "crouched low, gathering power, qi swirling inward",
            "wreathed in a rising pillar of black qi",
            "shedding scales as its body darkens in a rage transformation",
            "eyes blazing white in an enraged state",
            "shielded behind a barrier of swirling ink",
            "splitting off small ink dragon wisps around itself",
            # 受创状态
            "recoiling from a heavy hit",
            "one horn broken, bleeding",
            "frozen over with frost across its scales",
            "bound by golden sealing chains",
            "poisoned, scales tinged sickly green",
            "staggering with its head lowered",
            # 落败
            "collapsing onto its side",
            "lying defeated, body dissolving into ink",
            "dispersing into drifting ink smoke",
            "curled up dormant with eyes closed",
            "a shed empty scale husk of its body",
            "reduced to a single floating dragon-shaped ink mote",
        ],
    },
}

# ── 场景 / 背景：单图产线，不切格不去背 ──────────────────────────────
#
# 和 RECIPES 是两回事，别混：RECIPES 出的是 6×6 网格，要经 slice → cutout → resize；
# 场景图是一张整图直接当背景贴，跑切图管线只会把它毁掉。所以字段也不一样：
# 没有 items / bg（它自己就是背景），多了 ratio 和 role。
#
# role=arena  俯视地表，直接铺在战斗区底下。游戏是竖屏俯视、敌人朝玩家直线走，
#             所以必须是「从正上方看地面」，出成横版山水远景就贴不进去。
# role=art    氛围插画，给主菜单 / 章节封面 / 结算页用，可以是正常的立绘式构图。
SCENES: dict[str, dict] = {
    "arena-qingshi": {
        "desc": "战斗场地 · 第一章 青石山道（俯视地表）",
        "role": "arena",
        "ratio": "9:16 vertical",
        "content": (
            "a mountain path of weathered gray flagstones seen from directly "
            "above, with patches of moss between the stones, scattered pine "
            "needles, a few small rocks and tufts of grass at the edges, and "
            "thin mist pooling in the cracks"
        ),
        "palette": "cool gray-green, slate blue shadows, muted moss green",
    },
    "arena-zhulin": {
        "desc": "战斗场地 · 竹林（俯视地表）",
        "role": "arena",
        "ratio": "9:16 vertical",
        "content": (
            "a bamboo grove floor seen from directly above, packed earth "
            "crossed by fallen bamboo stalks and scattered leaves, with the "
            "cut stumps of bamboo and dappled shade at the edges"
        ),
        "palette": "malachite green, warm earth brown, pale ink gray",
    },
    "arena-guimu": {
        "desc": "战斗场地 · 鬼雾乱葬岗（俯视地表）",
        "role": "arena",
        "ratio": "9:16 vertical",
        "content": (
            "a burial ground seen from directly above, cracked dry earth with "
            "toppled stone grave markers, scattered bones and torn paper "
            "talismans, and low corpse-mist creeping across the ground"
        ),
        "palette": "desaturated bone gray, sickly green mist, dark ink",
    },
    "title-xianxia": {
        "desc": "主菜单背景 · 仙山云海（氛围插画）",
        "role": "art",
        "ratio": "9:16 vertical",
        "content": (
            "towering immortal mountain peaks rising out of a sea of clouds, "
            "a distant cliff-top pavilion, a lone tiny figure on a flying "
            "sword crossing the sky, dawn light behind the peaks"
        ),
        "palette": "azurite blue, ink black, gold dawn light, white cloud",
    },
    "chapter-qingshi": {
        "desc": "章节封面 · 青石山道（氛围插画）",
        "role": "art",
        "ratio": "9:16 vertical",
        "content": (
            "a stone mountain path winding upward between pine trees into "
            "mist, a weathered stone marker beside the path, overcast sky"
        ),
        "palette": "cool gray-green, slate blue, muted moss green",
    },
    # 章节封面按 arena 一比一配套：有几张战斗场地就得有几张封面，否则第二章一进去
    # 就只能复用第一章的封面。palette 和同名 arena 保持一致，进出关不跳色。
    "chapter-zhulin": {
        "desc": "章节封面 · 竹林（氛围插画）",
        "role": "art",
        "ratio": "9:16 vertical",
        "content": (
            "a dense grove of tall bamboo receding into mist, a narrow trodden "
            "path running between the stalks, fallen leaves drifting in shafts "
            "of pale light"
        ),
        "palette": "malachite green, warm earth brown, pale ink gray",
    },
    "chapter-guimu": {
        "desc": "章节封面 · 鬼雾乱葬岗（氛围插画）",
        "role": "art",
        "ratio": "9:16 vertical",
        "content": (
            "a desolate burial ground under a bruised night sky, leaning and "
            "toppled stone grave markers stretching into fog, tattered paper "
            "talismans caught on a bare dead tree, a thin sickle moon"
        ),
        "palette": "desaturated bone gray, sickly green mist, dark ink",
    },
}


def get(name: str) -> dict | None:
    return RECIPES.get(name)


def names() -> list[str]:
    return list(RECIPES)


def get_scene(name: str) -> dict | None:
    return SCENES.get(name)


def scene_names() -> list[str]:
    return list(SCENES)
