# P2 Brainstorming Lab 实现自检记录

时间：2026-05-01 13:39
分支：`feat/p2-requirement-analysis-system`

## 范围

- 新增独立后端能力：`/api/brainstorm/*`
- 新增独立前端页面：`/p2-brainstorm-lab`
- 验证 Brainstorming 组织器可替换、Provider 可配置、Turn 输入/输出对象可观察。
- 明确 Lab 只产生 `document_patch` 建议，不写入 P2 正式需求规格编辑器。

## 自测中发现并修复的问题

1. `/p2-brainstorm-lab` 初始落入 MainShell，页面出现“知识仓库”。
   - 修复：在 `App.tsx` 中把 `/p2-brainstorm-lab` 放到 MainShell 外独立路由。
2. 页面多个区域重复使用完全相同标题，自动化与用户定位均不清晰。
   - 修复：左侧对象树改为“组织器配置对象 / 会话对象 / Turn 对象”，主工作区保留业务标题。
3. Ant Design 中文按钮“发送”的可访问名称被拆成“发 送”。
   - 修复：给发送按钮增加 `aria-label="发送"`。
4. 当前 Turn 视图缺少 `confirmed_facts_delta`，无法直接看见本轮确认事实。
   - 修复：在当前 Turn 输入/输出对象中展示事实增量。
5. 真实浏览器联调首次 404。
   - 原因：当前 worktree `.env.local` 指向 `VITE_API_PROXY_TARGET=http://127.0.0.1:8060`，该端口旧服务没有 Brainstorming 路由；测试时显式以 `VITE_API_PROXY_TARGET=http://127.0.0.1:8000` 启动前端。
   - 结论：业务代码无路由错误；实际试用需确保前端代理指向包含本次分支代码的后端。
6. 390px 移动端输入框初始只有 176px，修复后第一次为 294px，仍低于自测底线。
   - 修复：移动端命令区改为上下布局，并收紧内边距；最终输入框和发送按钮均为 310px，无横向溢出。

## 命令验证

- `uv run pytest apps/api/tests/test_brainstorm_api.py -q`
  - 结果：`2 passed`
- `corepack pnpm --dir apps/web exec vitest run src/test/BrainstormLabPage.test.tsx`
  - 结果：`1 passed`
- `corepack pnpm --dir apps/web exec vitest run src/test/AppRoutes.test.tsx src/test/BrainstormLabPage.test.tsx`
  - 结果：`12 passed`
- `uv run pytest apps/api/tests -q`
  - 结果：`171 passed`
- `corepack pnpm --dir apps/web exec vitest run`
  - 结果：`36 passed`，`88 passed | 4 skipped`
- `corepack pnpm --dir apps/web build`
  - 结果：构建通过；保留既有 Vite 大 chunk 警告。

## 浏览器自检

启动方式：

```bash
uv run uvicorn app.main:app --app-dir apps/api --host 127.0.0.1 --port 8000
VITE_API_PROXY_TARGET=http://127.0.0.1:8000 corepack pnpm --dir apps/web dev --host 127.0.0.1 --port 5175
```

桌面视口：`1440x900`

- 打开 `/p2-brainstorm-lab`
- 验证没有“知识仓库”
- 点击“启动验证”
- 输入 `A，先按计算分析工具理解`
- 点击“发送”
- 验证出现 `当前 Turn turn-0001` 和 `系统初步定位为空域计算分析工具`
- 布局结果：无横向溢出；输入栏未被截断；截图输出到临时目录 `apps/tmp/p2-brainstorm-lab-1440.png`

移动视口：`390x844`

- 打开 `/p2-brainstorm-lab`
- 验证没有“知识仓库”
- 点击“启动验证”
- 输入 `继续`
- 点击“发送”
- 验证出现 `当前 Turn turn-0001`
- 布局结果：`bodyScrollWidth=390`，`viewportWidth=390`；输入框宽度 `310px`；发送按钮宽度 `310px`；截图输出到临时目录 `apps/tmp/p2-brainstorm-lab-390.png`

## 残留风险

- 当前 Provider 仍为 mock，DeepSeek/OpenAI 只在 Provider 列表中标记为 `not_configured`，尚未接入真实密钥和真实模型调用。
- 当前数据库迁移基线为空迁移，项目仍依赖 `Base.metadata.create_all` 建表；本次新增 `brainstorm_sessions` 模型与现有持久化方式一致。
- `.env.local` 指向的 8060 旧服务没有本次新增路由，试用本分支时需启动本分支后端，并确保 `VITE_API_PROXY_TARGET` 指向它。
