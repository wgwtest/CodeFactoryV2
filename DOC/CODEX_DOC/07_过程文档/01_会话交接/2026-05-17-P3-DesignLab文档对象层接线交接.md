# 2026-05-17 P3 Design Lab 文档对象层接线交接

## 1. 本轮目标

把 P3 Design Lab 的 `需规` 与 `软设文档` 从纯 Canvas 标签升级成可执行文档对象，同时保留 Canvas 作为滑窗与位置投影层。

## 2. 已完成事项

- 在 `DesignMorphCanvasPlatform` 中新增文档对象层。
- 为 `需规` 和 `软设文档` 增加 `A4 / 编辑区` 视图模式。
- 为文档对象增加紧凑标题栏、滚动容器、A4 纸面和缩放拖拽锚点。
- 将 `P3DesignMorphAdapter` 接入真实文档视图模型。
- 为 `P3DesignLabWorkbenchAdapter` 提供需规章节到标准文档章节的转换帮助函数。
- 补齐对象层测试，并让 `P3DesignMorphModel` 测试覆盖文档对象数据。
- 补齐对象层样式。

## 3. 主要改动文件

- `apps/web/src/components/stageWorkbench/DesignMorphCanvasPlatform.tsx`
- `apps/web/src/components/stageWorkbench/design-morph-canvas.css`
- `apps/web/src/pages/adapters/p3DesignLabWorkbenchAdapter.ts`
- `apps/web/src/pages/adapters/p3DesignMorphAdapter.ts`
- `apps/web/src/test/DesignMorphCanvasPlatform.test.tsx`
- `apps/web/src/test/P3DesignMorphModel.test.ts`

## 4. 已执行验证

- `corepack pnpm --dir apps/web exec vitest run src/test/DesignMorphCanvasPlatform.test.tsx src/test/P3DesignMorphModel.test.ts`
- `corepack pnpm --dir apps/web build`
- `git diff --check`
- 浏览器运行态截图：`/tmp/p3-design-lab-runtime.png`

## 5. 运行态结果

- P3 API 健康检查可达。
- P3 页面可达：`http://127.0.0.1:5174/p3-design-lab`
- P2 页面可达：`http://127.0.0.1:5183/p2-requirement-analysis-lab`
- platform 页面可达：`http://127.0.0.1:5191/portal`
- 截图中对象层已显示 `需规` 与 `软设文档` 的真实文档内容。

## 6. 当前状态

- 当前状态：`已自测，待用户确认`
