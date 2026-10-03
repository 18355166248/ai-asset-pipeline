# sprite-gen 动作工作层试点

第一阶段已运行真实上游的 unpack → compose → export-aseprite。固定版本 2.20.0，提交 `d993e5300b4255111e8ee0e29779caea1b3b97bd`，不是从演示视频推断生成能力。

当前入口：[动作工作层](http://127.0.0.1:8770/motion)。完整流水线在 /pipeline。本次导入薄荷冒险者已有 v23 的 move 和 idle，共 12 个播放位置；不是用户指定的绿帽护目镜角色。新增 GPT 调用 0 次，动作观感尚未验收。

## 安装与固定引擎

```bash
python3 scripts/fetch_sprite_gen.py --out vendor/sprite-gen
npm ci --prefix workbench --ignore-scripts
npm run build --prefix workbench
```

下载器依据 config/sprite-gen.lock.json 拉取 135 个源码、许可和文档文件，逐个核对 Git blob 哈希，跳过演示媒体；缓存不进入 Git。实际调用前再次核对源文件与版本。Python 使用已有 `.venv-cutout/bin/python`，需要 Pillow 和 NumPy。网络失败不会发布半成品目录。

## 导入与时序

```bash
.venv-cutout/bin/python src/sprite_gen_adapter.py import \
  --manifest output/mint-adventurer-collection-v23/bundle/manifest.json \
  --actions move idle --out output/my-import-v1
npm run prepare:data --prefix workbench -- --run output/my-import-v1
npm run dev --prefix workbench
```

所有输出目录必须不存在，不覆盖已有批次。`motion-contract.json` 保存真实原画引用、整数 durationMs、统一画布和 anchor。move 总时长 800ms，idle 3200ms。预览、应用草案、候选采纳和每次重新导出均从契约读取时长；上游统一 FPS 不会覆盖它。

页面操作：暂停 → 定位原画 → 修改毫秒数或零起始序号顺序 → 展示/复制 JSON → 把 JSON 和页面“下一步交给 Codex 执行”交给 Codex。下载仅作为便利入口，内嵌浏览器未收到文件时直接复制 JSON。

```bash
.venv-cutout/bin/python src/sprite_gen_adapter.py apply \
  --run output/my-import-v1 --plan /absolute/path/motion-plan.json \
  --out output/my-timing-v2
```

草案携带基准契约 SHA256，基准过期会拒绝。只能引用已有冻结原画；引入新图片必须走候选流程。重排、重复引用按每次引用计时；复制原画会增加总时长，不能宣称自动保持周期。改变的动作清除旧验收，其他动作保留。

## 定点修复候选

页面生成的 Prompt 包含实际批次、帧索引、前后帧路径和修复要求。先查看参考，用当前 GPT 生成并记录实际 Prompt、参考顺序、原图、耗时和候选次数，再登记：

```bash
.venv-cutout/bin/python src/sprite_gen_adapter.py candidate \
  --run output/my-import-v1 --action move --frame 2 \
  --image /absolute/path/generated.png --note '实际生成记录位置与修复要求' \
  --out output/my-candidate-v1
.venv-cutout/bin/python src/sprite_gen_adapter.py select \
  --run output/my-import-v1 --candidate output/my-candidate-v1 \
  --out output/my-selected-v2
```

candidate 不替换原画；select 应在明确选中后执行，只写新批次。候选保存原图字节、原图/像素哈希和基准动作指纹。画布错误、候选被修改、基准过期都会拒绝。没有逐帧缩放、镜像或关节重组；其他冻结 PNG 字节和 RGBA 必须保持不变。

上游图集 alpha_composite 会清除全透明像素中的隐藏 RGB。适配层只在可见 RGBA 完全不变时恢复这些隐藏值，并记录 hiddenRgbRepairs；可见像素变化直接失败，不用后处理伪造修复。坐标 anchor 是已有素材基准，不等于已核验支撑脚。近远腿、脚部接触、比例漂移和首尾连续性仍需实际动作检查。

## 检查与交付

```bash
.venv-cutout/bin/python src/sprite_gen_adapter.py review \
  --run output/my-selected-v2 --action move --verdict motion-pass \
  --evidence '实际检查记录的路径、版本与结论' --out output/my-checked-v3
.venv-cutout/bin/python src/sprite_gen_adapter.py review \
  --run output/my-checked-v3 --action move --verdict user-accept \
  --evidence '用户实际验收原话与对应版本' --out output/my-accepted-v4
.venv-cutout/bin/python src/sprite_gen_adapter.py export \
  --run output/my-accepted-v4 --out output/my-release-v5 --release
```

每个动作均需当前指纹的 motion-pass 和 user-accept，才能 --release；缺一项即拒绝。默认 export 输出草稿，approvedActions 为空。review 是本地人工证据登记，不是用户身份认证，也不是模型自动判断动作合格；不得捏造验收。修改时序或选帧后必须重新检查。输出 PNG、通用 manifest、Aseprite JSON 的原画位置与毫秒数分别核验。

## 已验证与未完成

已验证：实际导入导出 12 个位置、RGBA 不变、非等长时序不丢失；浏览器 50→75ms 后 move 800→825ms；页面输出 JSON 实际交给 apply 成功生成新批次；合成测试中的单帧隔离、旧候选/损坏冻结帧拦截、验收失效与正式导出门禁。

未完成：目标绿帽护目镜角色路径确认、该角色左侧待机与完整八阶段走路的真实 GPT 生成、真实失败帧修复、正常速度和 128px 人工验收。当前引擎适配层只调用素材处理命令；生图仍通过已有 Codex GPT 流程，不存在自动 GPT 一键生成入口，也未接入 Grok 视频或 RIFE。上述工程测试不能代替动画合格率。

本地页面已迁移到React；已删除两个旧HTML入口生成器。应用新批次后通过prepare:data更新受控静态数据，再刷新/motion，详见 [前端指南](FRONTEND.md)。
