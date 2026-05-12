# W3 - 运行态 Stream 与语义图谱

## 新线程启动提示词

你正在接手 CodeFactoryV2 的 P1 业务知识库重构工作线 W3。仓库路径是 `E:\project\Web\智能软件生成\CodeFactoryV2`。本线目标是让单文档实时工作台以合同驱动运行态和图谱：优先走 stream，断线回退轮询；图谱表达“输入对象 -> 规则/动作依据 -> 输出对象”；选中节点/边时联动观察窗。不要提交 git，不要提交本地数据内容，不要修改策略合同生成逻辑、质量评估算法和治理发布页面。请先阅读 R0 contracts、fixtures 和单文档页现状，再按本文件边界实现。

## 目标

- 运行中优先使用 runtime stream，断线后自动回退 polling。
- 页面状态局部更新，不做整页刷新。
- 当前阶段由后端 `DocumentRuntimeSnapshot` 决定，用户点击历史阶段只能查看快照，不能把点击节点改成当前阶段。
- 图谱默认使用语义聚合视图，表达输入对象、规则/动作依据、输出对象。
- 节点/边选中后，高亮相关层级并驱动右侧观察窗。

## 边界

- 负责单文档实时工作台、runtime adapter、图谱投影 UI。
- 可以修改：
  - `apps/web/src/pages/ArchiveManagementPage.tsx`
  - `apps/web/src/pages/archiveManagementGraph.css`
  - `apps/web/src/features/p1/contracts/runtime.ts`
  - `apps/web/src/features/p1/contracts/graphProjection.ts`
  - `apps/web/src/features/p1/api/p1RefactorApi.ts`
- 可以补后端 runtime adapter 字段，但不重写策略合同或质量算法。

## 输入合同

- `DocumentRuntimeSnapshot`
- `StageSnapshot`
- `RuntimeGraphProjection`
- `RuleExecutionRecord`
- `PolicyRuntimeSnapshot`

## 输出合同

- 用户选中的 `selected_node_id`
- 用户选中的 `selected_edge_id`
- 观察窗展示所需的对象详情投影
- 图谱布局状态，但不得写回正式知识

## 禁止改动范围

- 不把用户点击阶段当作当前运行阶段。
- 不用固定 13 阶段硬编码替代 runtime 合同。
- 不将全部明细节点默认铺满画布。
- 不在图谱中伪造规则依据；没有依据时必须标识缺失。
- 不修改 `/governance` 和发布态 `/graph` 职责。
- 不提交 git，不提交本地运行数据。

## 建议实现范围

- 抽出 runtime 订阅 hook：`useP1DocumentRuntime`。
- 抽出图谱投影适配器：把 `RuntimeGraphProjection` 映射为 React Flow 节点/边。
- 默认布局使用分层 DAG：输入在左、规则依据中间、输出在右。
- 明细视图通过点击或切换展开，避免一上来线海。
- 节点文字在节点内部，状态徽标不遮挡文字。
- stream 事件和 polling 返回保持同一 payload 结构。

## 验收方式

- 断开 stream 后，页面显示“已回退轮询”，并继续更新。
- stream 恢复后，页面显示“已连接 Stream”。
- 当前阶段只能由后端推进，未到阶段灰色不可伪装成当前。
- 图谱能看出至少一个阶段的输入、规则依据、输出。
- 点击节点/边后，右侧观察窗展示该对象的规则、证据、状态、上下游影响。

## 测试命令

```powershell
cd E:\project\Web\智能软件生成\CodeFactoryV2\apps\web
npm run build
npm run test -- ArchiveManagementPolicy.test.tsx
```

```powershell
cd E:\project\Web\智能软件生成\CodeFactoryV2
$env:PYTHONPATH='apps/api'
.\.venv\Scripts\python.exe -m pytest apps/api/tests/test_p1_refactor_api.py apps/api/tests/test_archive_document_runtime_api.py
```

## 最小交付物

- 一个 runtime hook 或 adapter。
- 单文档图谱使用 R0/R1 `RuntimeGraphProjection`。
- 至少一条 stream/polling 兼容验证。
