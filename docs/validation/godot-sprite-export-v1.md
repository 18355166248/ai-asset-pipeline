# Godot SpriteFrames 导出检查

日期：2026-10-03。来源：`output/mint-adventurer-collection-v8/bundle/manifest.json`。
产物：`output/mint-adventurer-godot-v2/`。本轮无 GPT 调用、无原画修改。

本机引擎：`4.7.2.stable.official.ed1daf0bf`。

```text
godot --headless --path output/mint-adventurer-godot-v2 --editor --import
exit=0
godot --headless --path output/mint-adventurer-godot-v2 --script validate.gd
GODOT_SPRITE_EXPORT_PASS checks=67 animations=7
exit=0
```

7动作的存在/循环/帧数共21检查；21帧的实际毫秒时长与 AtlasTexture 区域共42检查；真实 AnimatedSprite2D 的非循环攻击播放结束1检查；PackedScene 加载和脚底 offset 2检查；将资源与图集复制到 relocated/ 后重新 import、确认引用 relocated/atlas.png 1检查。独立输出不含额外复制时为66检查。

`tests/test_godot_sprite_export.py` 3项通过：原始 atlas/manifest 字节及 draft/anchor 元数据保留、既有批次不覆盖、源目录外图集拒绝且不发布。未重复运行此前全套 Python/Node 回归。

初次 sandbox 导入出现引擎用户配置目录写权限错误；获准在正常用户环境重试后导入与检查通过。没有修改系统配置或消费游戏。

限制：这是 headless 资源/播放契约验证，无 Godot GUI、人眼完整循环、手机或游戏战斗验证。集合仍 draft；步行躯干变化、跨动作比例与任意腿部相位停步仍未通过视觉验收。资源导出不解决这些原画问题。
