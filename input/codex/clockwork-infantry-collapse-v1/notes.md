# 发条步兵倒地 B 帧候选

- 用途：`nightwatch-tower-defense` 第一关发条步兵死亡时的第二帧；第一帧是项目原图，不由本次生成。
- 原图、编辑结果与完整提示词分别见本目录 `reference.png`、`clockwork-infantry-collapse-v1.png`、`prompt.md`；角色动作配方、逐帧和来源报告见游戏项目 `art-source/first-level-units/clockwork-infantry-collapse-v1/`。
- 资产管线报告 `needs-human-review`：第二帧源图存在低透明度触边警告。需人工复核轮廓、朝向、脚底、动态节奏与素材使用权。
- Cocos Web Mobile 构建和浏览器 QA 首波实战已证明 B 帧加载并在死亡窗口进入显示；细节和证据边界见游戏项目 `docs/poc/phase-c-infantry-collapse-regression.md`。未保存独立的游戏内截图/录屏，不能把它当作最终动作验收；清单状态保持 draft。
