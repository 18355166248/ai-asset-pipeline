# 工具箱 v1 验证记录

日期：2026-09-27。

## 本地加工与 Skill

- 11 项 unittest：半透明 alpha、自然帧顺序、尺寸包比例及输入保留、小尺寸主体消失拦截、统一画布约束、透明输入约束、禁止覆盖、Aseprite 时长/loop/像素往返、导出路径/trim/越界拒绝、HTML 数据转义、无效配方、补齐不增加真实帧数（部分检查合并在同一测试方法）。
- 新 Python 文件通过 Ruff；两个 Skill 通过 skill-creator 的 quick_validate。
- 几何样例：3 个静态候选，各 4 个尺寸；4 帧 idle、6 帧 attack。
- 真实静态输入：已有 `output/frontier-equipment-icons-v3/cutouts` 的 4 张图标，各导出 32/64/128/256 px。原图未修改。

复现命令（仓库根目录）：

```bash
.venv-cutout/bin/python -m unittest discover -s tests -v
.venv-cutout/bin/python examples/make_demo.py --out output/toolkit-demo-recheck
```

样例生成目录不提交，可重跑。首次本地验收输出在 `output/toolkit-demo-v1/`。

## 浏览器交互

通过仅绑定 127.0.0.1 的临时静态服务访问生成的独立 HTML：

- idle 可播放，帧号随时间变化。
- 切到 attack 后，播放到第 6 / 6 帧自动暂停，没有被改成循环。
- 下一帧可手动步进，末帧后从首帧开始，仍处于暂停状态。
- 速度控件可切到 0.25×，倍率可切到 4× 后恢复 1×。
- 深色/浅色背景切换可见；真实图标从 32 切换为 64 px，四张图均正常显示。
- 桌面截图目视检查了动作面板及真实图标网格。

## 尚未验证

- 新的 AI 吉祥物/角色生成质量与模型用量；几何样例不是生成效果证明。
- 真实 sprite-gen 安装、生成及各版本最终导出；当前验证是兼容格式的本地往返。
- Cocos/Phaser 导入、游戏内脚底与命中窗口、真机表现。
- 视频抽帧作为正式资产；仍遵循原项目的 reference-only 限制。

上述未验证项不阻止本地素材工具使用，但不得据此宣称引擎接入完成或资产可发布。

## Frontier Brawler 实战补充

同日使用 Godot 实际姿态采样器导出的 Aseprite 兼容 JSON 完成 before / after 打包，
覆盖 idle、move、slash、slash2、slash3，保留逐姿态时长和循环属性。
输出位于 `../frontier-brawler/output/motion-review-{before,after}-v1/`。
攻击的第五个播放条目是复用准备姿态，不是新增原画；预览没有角色高度、地面位移或命中特效。

Godot 消费端仍使用原四列图集，本轮修正的是姿态采样与跳劈高度，不是通用 manifest 运行时导入器。
游戏 54 项检查和实际 OpenGL 对照渲染通过；工具库 11 项回归通过。
50 单位真实渲染复验 1441 个样本，平均约 8.333 ms、P95 约 8.333 ms，仅 Apple M2 桌面。

两轮内置 image_gen 移动候选因重复半步态被拒绝，正式图集未替换。
character-motion-kit 和报告清单新增左右腿交替检查，避免把不同像素或更多帧误认为有效步态。
证据与设计记录位于 `../frontier-brawler/docs/experiments/hero-motion-2026-09-27/`。
