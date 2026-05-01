# P2 Brainstorming Lab v3 实现自检记录

**时间：** 2026-05-01 14:17

## 修改范围

- 将 `P2 Brainstorming Lab` 左侧从业务对象自动高亮改为显式 Tab：`组织器配置`、`会话管理`、`当前 Turn`、`调用日志`。
- 将主工作区拆分为四个 Tab 视图：
  - `组织器配置`：只显示可替换组织器、启动参数、稳定契约 / 输出协议。
  - `会话管理`：只在用户显式切换后显示 CLI 式问答区和会话摘要。
  - `当前 Turn`：只显示最新 Turn 输入 / 输出对象。
  - `调用日志`：显示 Provider 调用列表和详情。
- 保证 `启动验证` 和 `发送` 只更新业务状态，不自动切换当前 Tab。

## 自检结果

1. `corepack pnpm --dir apps/web exec vitest run src/test/BrainstormLabPage.test.tsx`
   - 结果：1 passed
   - 覆盖点：默认 Tab、启动验证不跳页、发送输入不跳 Turn、显式切换会话 / Turn / 日志。

2. `corepack pnpm --dir apps/web exec vitest run src/test/AppRoutes.test.tsx`
   - 结果：11 passed
   - 覆盖点：`/p2-brainstorm-lab` 仍为独立路由，不显示 `知识仓库`。

3. `corepack pnpm --dir apps/web exec vitest run`
   - 结果：36 files passed；88 passed；4 skipped。

4. `uv run pytest apps/api/tests -q`
   - 结果：171 passed。

5. `corepack pnpm --dir apps/web build`
   - 结果：通过。
   - 备注：保留既有 Vite chunk size warning。

6. Playwright 真实浏览器自检
   - 桌面视口：1440 x 900。
   - 移动视口：390 x 844。
   - 覆盖点：
     - Lab 不显示 `知识仓库`。
     - 默认 `组织器配置` 不显示 `CLI 式问答区`。
     - 点击 `启动验证` 后仍停留在 `组织器配置`。
     - 显式点击 `会话管理` 后才显示 CLI 问答区。
     - 发送输入后仍停留在 `会话管理`。
     - 显式点击 `当前 Turn` 后才显示 Turn 详情。
     - 显式点击 `调用日志` 后才显示 Provider 日志。
     - 桌面和移动均未发现横向溢出；移动输入框宽度满足可用性要求。

## 发现并修复的问题

1. 旧实现没有真正的 Tab 角色，左侧高亮由 `session/currentTurn` 业务状态驱动。
   - 修复：新增独立 `activeTab` 状态，左侧按钮使用 `role="tab"` 和 `aria-selected`。

2. 旧实现默认在组织器配置页面同时显示 `CLI 式问答区`。
   - 修复：`CLI 式问答区` 移入 `会话管理` Tab。

3. 旧路由测试使用纯文本匹配 `组织器配置`，v3 中该文本同时存在于 Tab 和标题。
   - 修复：测试改为检查 Tab 角色和选中状态。

4. 日志和 Turn 视图中的部分文本在摘要和详情中重复，测试用唯一文本断言不稳。
   - 修复：测试改为检查重复文本至少出现一次。

## 新增问题

本轮自检未发现由本次修改引入的新失败项。

## 后续交互细节修正记录

**时间：** 2026-05-01 15:18

用户在人测中继续发现并确认以下细节问题，已同步修正到实现与设计说明：

1. **发送后 user 消息未立即上屏。**
   - 现象：点击“发送”后，必须等待 assistant 回复完成，用户输入才出现在消息流中。
   - 修正：前端增加 pending user 消息，发送后立即追加到 CLI 消息流；Provider 返回后用后端 session 覆盖为正式消息。
   - 验证：`BrainstormLabPage.test.tsx` 使用挂起 Promise 覆盖慢响应场景，断言 user 消息和“正在生成回应...”在后端返回前可见。

2. **quick_options 没有在 CLI 区展示。**
   - 现象：后端 Turn 已包含 `quick_options`，但会话管理页没有渲染选项。
   - 修正：会话管理页读取最新 `currentTurn.quick_options`，仅在存在选项时展示。
   - 设计规则：选项不是每轮强制出现；自由输入仍是主路径。

3. **快捷选项需要推荐项，但不能形成误触。**
   - 现象：初版把整个选项块做成按钮，容易误触；横向排列也不利于长选项。
   - 修正：选项改为纵向列表，每个选项一行；左侧展示推荐标签、key 和文案，右侧独立显示“选择 X”按钮。
   - 设计规则：选项行本身不可点击，只有右侧选择按钮提交。
   - 验证：单测断言点击选项行不触发 Provider 请求，点击“选择 B”才发送 `B，先确认输出`。

4. **CLI 输入框需要支持多行。**
   - 现象：单行输入无法承载多行需求描述。
   - 修正：输入框改为 `TextArea`，默认 2 行，最多 6 行；超出后内部滚动。
   - 交互规则：`Enter` 发送，`Shift+Enter` 换行。
   - 验证：单测断言输入控件为 `TEXTAREA`，并保留换行；Playwright 断言多行输入不造成横向溢出。

5. **快捷选项弹出后可能遮住最后一轮会话。**
   - 现象：选项区出现后占用输入区上方空间，消息列表没有自动滚到底部。
   - 修正：消息列表底部增加滚动锚点；消息数量、pending 状态、当前 Turn 和选项数量变化时自动滚到底部。
   - 验证：单测断言 `scrollIntoView` 被触发；Playwright 多轮对话后检查消息列表已滚到底部。

6. **会话摘要 / 过程产物缺少生命周期和来源关系。**
   - 现象：`已确认事实` 持续增长，而 `待确认问题` 像静态句子，容易让用户误解二者应当简单此消彼长；`document_patch` 的章节编号来源也不清楚。
   - 修正：后端 session 增加结构化对象：
     - `questions`：问题工作项，编号 `Q-xxx`，带 `open / confirmed` 等状态和 `resolution_fact_ids`。
     - `facts`：已确认事实，编号 `F-xxx`，带来源 Turn 和来源问题。
     - `patches`：文档修补建议，编号 `P-xxx`，带目标章节、来源事实和关联问题。
   - 前端摘要区改为展示 `问题工作项 / 已确认事实 / 文档修补建议`，每项显示编号、状态、来源和关联关系。
   - 验证：后端测试断言 `Q-001 -> F-001 -> P-001` 关系；前端测试断言摘要区显示 `Q-001/Q-002/F-001/P-001`、状态、目标章节和来源事实。

7. **会话管理布局空间分配需要调整。**
   - 现象：CLI 问答区比例较理想，但摘要区承担更多结构化对象展示，原比例偏窄。
   - 修正：会话管理 Tab 改为 CLI 区略窄、摘要区略宽。
   - 验证：Playwright 检查 session grid 实际列宽约 `466px / 516px`，摘要区宽度大于 CLI 区。

8. **右侧工作区重复 Tab 名称抬头。**
   - 现象：左侧 Tab 已经表达当前视图，右侧再显示“组织器配置 / 会话管理 / 当前 Turn / 调用日志”大抬头占用空间。
   - 修正：移除各 Tab 顶部 `WorkspaceBand`，工作区直接展示功能面板。
   - 验证：前端测试断言会话管理视图不存在重复 `h3` 抬头；Playwright 检查重复工作区抬头不存在。

### 后续修正验证命令

1. `corepack pnpm --dir apps/web exec vitest run src/test/BrainstormLabPage.test.tsx src/test/AppRoutes.test.tsx`
   - 结果：12 passed。

2. `corepack pnpm --dir apps/web build`
   - 结果：通过。
   - 备注：保留既有 Vite chunk size warning。

3. Playwright 真实浏览器自检
   - 覆盖点：
     - user 消息发送后立即可见。
     - quick_options 可见且为纵向列表。
     - 点击选项行不发送；点击“选择 B”才发送。
     - 多行输入框保留换行且不横向溢出。
    - quick_options 出现后消息列表自动滚到底部。
     - 会话摘要区显示 Q/F/P 编号和来源关系。
     - 会话管理摘要区宽度大于 CLI 区。
     - 右侧工作区不再显示重复 Tab 名称抬头。

### 同步到设计说明的结论

上述修正已纳入：

- `DOC/CODEX_DOC/02_设计说明/P2_需求分析系统/P2-Brainstorming能力原理验证与架构规划.md`
- `DOC/CODEX_DOC/02_设计说明/P2_需求分析系统/P2-Brainstorming-Lab状态机与v3原型草案.md`
