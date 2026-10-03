# 本地前端

本地应用位于 workbench，采用 Vite、React、React Router、shadcn/ui、Tailwind CSS 和 Jotai。shadcn组件由官方CLI生成，源码位于 src/components/ui；components.json 已配置，可继续用CLI添加组件。

```bash
npm ci --prefix workbench --ignore-scripts
npm run dev --prefix workbench
npm run build --prefix workbench
npm test --prefix workbench
npm run preview --prefix workbench
```

dev 和 preview 使用 127.0.0.1:8770，不能同时运行。根路径跳转 /pipeline，九个步骤支持 /pipeline/1 到 /pipeline/9。已有图片直接进入 /pipeline/6。动作工作层在 /motion。旧 /toolkit.html、/engine-pilot/ 书签重定向到新React路由。

## 目录与状态

- src/pages：流水线与动作编辑器，按路由懒加载。
- src/state：Jotai 文本草稿、身份确认、验收和时序契约。兼容旧流水线文本草稿；确认和验收不持久化，改动上游清除对应状态。
- src/lib/prompts.js：复用已测试的纯请求生成和输入门禁，无DOM操作。
- src/motion-contract.ts：精确时序、重排、补帧和动作验收失效规则。
- scripts/prepare-data.mjs：仅复制指定批次的冻结原画与核验数据到 public/data/pilot。不会公开整个 output 或上游引擎。生成资源不进入Git。

切换批次：

```bash
npm run prepare:data --prefix workbench -- --run output/my-timing-v2
```

在运行中的Vite页面刷新后读取新数据。新检出没有ignored试点产物时仍可启动流水线，动作页提示准备素材。首次dev/build准备 output/sprite-gen-pilot-v1；prepare:data --run 的选择记录在不提交的 .local-source.json 中，后续启动和构建沿用当前批次。页面编辑仅是内存草稿；JSON交给Python适配层生成新批次，保留基准指纹检查、冻结原画和验收门禁。没有后端生图API，也没有自动写文件或宣称素材通过。

## 清理范围

已删除旧工具入口HTML/CSS、DOM流水线挂载脚本、engine-review.ts、motion_toolkit_site.py、sprite_gen_review_site.py，以及只验证旧HTML生成器的测试。纯Prompt校验测试迁到新模块。React项目仅保留 Vite 必需的 index.html 挂载壳，里面没有业务页面逻辑。

通用导出仍需提供独立离线预览，所以它实际引用的渲染模板移到 examples/export-workbench。其他Python图像处理、源原画、生成记录和导出模板仍有调用者，保留。历史本地HTML站点退役后不作为本地前端服务，导出示例需要独立查看时用另一个端口。删除本地UI不等于删除角色生产数据。

## 验证边界

构建包含TypeScript检查；Node测试覆盖Prompt门禁、时序和Jotai确认失效。浏览器回归应覆盖旧链接重定向、无参考图引导、已有图后处理、时长编辑、草案复制/下载和修复门禁。桌面验证不等于游戏或手机真机验收。

进一步清理：删除make_anime_pilot.py、make_fullframe_pilot.py、make_walk_pose_guide.py三份旧试点脚本；使用通用motion_compare、character_workbench及motion_generation的姿态约束流程。删除未使用的CardAction/CardFooter包装与组件variants公开导出，并启用TypeScript未使用局部变量/参数检查。原画、生成记录和已加工导出保留。
