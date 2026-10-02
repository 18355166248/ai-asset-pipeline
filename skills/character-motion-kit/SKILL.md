---
name: character-motion-kit
description: 将同一角色的待机、攻击等二维动作整理成可复用图集，衔接已安装的 sprite-gen 最终导出或已有透明序列帧，保留帧顺序、逐帧时长、循环属性并生成离线预览和验收记录。用于角色素材生产与交付，不负责游戏战斗逻辑或命中判定。
---

# 角色动作素材包

解析当前 SKILL.md 的真实路径（可能由软链安装），向上两级得到 `ai-asset-pipeline` 根目录。所有仓库命令使用绝对路径。参考 [工具箱契约](../../docs/TOOLKIT.md)；在本游戏工作区内同时遵循 [现有资产工作流](../../docs/CODEX_ASSET_WORKFLOW.md)，不把视频抽帧默认升级为正式资产。

## 选择输入路径

1. **已有透明帧**：直接加工。帧放在各动作子目录；命名按自然数字顺序读取，frame-2 在 frame-10 前。整套动作共用源画布、角色比例和基准线。不要逐帧裁切缩放来掩盖漂移。
2. **已有 sprite-gen 产物**：要求 compose 后的最终图集，再执行该版本的 export-aseprite，读取其 JSON。不要读取 `frames/` 缓存，因为用户在选帧界面里的修改可能尚未烘焙到那里。
3. **需要新生成**：先确定角色参考、动作集合、朝向和目标显示尺寸。若存在已安装的 sprite-gen，阅读其本地 Skill 与当前版本文档，调用上游生成与 compose 流程；不要假设工具已经安装。若不存在，可用宿主已有生图工具遵循目标项目的素材规范生成参考或源网格，再走项目现有加工链路。明确实际采用的路线，不声称使用了未运行的 sprite-gen。

首个试点默认只做 idle 和 attack；用户要求其他动作时保留。身份一致性由参考约束并人工确认；失败的动作记录原因、保留原始输入，修正该动作，不把整套无限重抽。

## 打包

复制 [动作配方](../../recipes/character.json) 到本次目录。逐动作明确 name、loop，以及目录输入的 fps；cell 是统一输出画布，anchor 是从左上角计量的归一化锚点元数据，不是自动脚底对齐。

```bash
# 已有透明帧
python3 <pipeline-root>/src/asset_bundle.py \
  --recipe <本次配方.json> --input <动作目录> --out <新的素材包目录>

# 上游最终 Aseprite 导出；与 PNG 放同目录，meta.image 指向同目录下的 PNG
python3 <pipeline-root>/src/asset_bundle.py \
  --recipe <本次配方.json> --input <最终导出/aseprite.json> \
  --aseprite --out <新的素材包目录>
```

使用具有 Pillow、NumPy 的 Python 3.10+；优先检查仓库的 `.venv-cutout/bin/python` 或 `.venv-toolkit/bin/python`，用可用者替换命令中的 python3。导入时保留上游逐帧 duration，配方 fps 不覆盖它；loop 由配方显式指定，因为 Aseprite 标签不携带此语义。当前适配器接受 forward、未 trim、未旋转的完整帧；其他格式报错后按上游导出契约处理，不猜网格或偷偷丢弃时长。

## 检查和交付

- 播放 preview.html：1×、深浅背景、逐帧、正常速度；攻击应播放到末帧停止，idle 按配置循环。
- 检查身份、朝向、尺寸、脚底漂移、触边、循环接缝。bbox 只作测量，不证明脚掌接触或步态正确。
- 走/跑必须逐帧确认左右腿交替的落地、承重、经过、蹬离，以及末帧到首帧的接缝；八张不同图片可能只是同一个半步态的重复，像素不重复不等于步态完整。
- 消费游戏动作不连贯时，先核对实际播放时长、命中/取消窗口和高度衔接，再决定是否重画；离线图集预览不能替代游戏内动作切换。复用姿态延长收招不算新增原画。
- 交付 atlas.png、manifest.json、aseprite.json、grid.json、透明帧和预览页。真实帧数以 manifest 为准，grid 末帧补齐不代表新增动作帧。
- Cocos 等消费端必须核对行序、帧数、坐标原点、锚点和时间语义；这些导出不是已完成的引擎插件。游戏中验证并保存证据后才能更新正式资产状态。命中窗口、碰撞和数值继续由游戏决定。
