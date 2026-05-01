# P2 Brainstorming Lab 实现交接

时间：2026-05-01 13:39
分支：`feat/p2-requirement-analysis-system`

## 本轮实现

- 新增独立 Brainstorming 后端模块：
  - `apps/api/app/brainstorm/models.py`
  - `apps/api/app/brainstorm/service.py`
  - `apps/api/app/api/routes/brainstorm.py`
  - API 前缀：`/api/brainstorm/*`
- 新增持久化模型：
  - `BrainstormSession`
  - 表名：`brainstorm_sessions`
- 新增独立前端 Lab：
  - 路由：`/p2-brainstorm-lab`
  - 页面：`apps/web/src/pages/BrainstormLabPage.tsx`
  - 样式：`apps/web/src/pages/BrainstormLabPage.css`
  - API 封装：`apps/web/src/lib/brainstorm.ts`
- 新增测试：
  - `apps/api/tests/test_brainstorm_api.py`
  - `apps/web/src/test/BrainstormLabPage.test.tsx`
  - `apps/web/src/test/AppRoutes.test.tsx` 中补 Lab 独立路由回归。

## 设计约束落实

- Brainstorming Lab 是独立能力验证页面，不挂在 P2 正式需求规格编辑器内。
- Brainstorming Service 以可替换组织器形式存在：
  - `BrainstormingOrchestrator`
  - `WizardOrchestrator`
  - `FormDrivenOrchestrator`
  - `RuleBasedReviewOrchestrator`
- 稳定契约明确展示：
  - 正式需求规格文档
  - 模板对象
  - 知识绑定
  - 草稿持久化
  - 检查与冻结
  - P2 -> P3 输出
- Lab 的写入策略为 `patch_suggestion_only`，页面文案显示为“只生成 document_patch 建议”。

## 自测结论

完整自测记录见：

`DOC/CODEX_DOC/06_测试文档/03_机测记录/2026-05-01-133900-P2-Brainstorming-Lab实现自检记录.md`

关键结果：

- 后端全量：`171 passed`
- 前端全量：`36 passed`，`88 passed | 4 skipped`
- 前端构建：通过
- 浏览器桌面视口：通过
- 浏览器移动视口：通过

## 试用说明

当前 worktree `.env.local` 指向 `VITE_API_PROXY_TARGET=http://127.0.0.1:8060`。如果 8060 上运行的是旧后端，会导致 `/api/brainstorm/*` 返回 404。

推荐临时试用启动方式：

```bash
uv run uvicorn app.main:app --app-dir apps/api --host 127.0.0.1 --port 8000
VITE_API_PROXY_TARGET=http://127.0.0.1:8000 corepack pnpm --dir apps/web dev --host 127.0.0.1 --port 5175
```

访问：

```text
http://127.0.0.1:5175/p2-brainstorm-lab
```

## 后续建议

- 下一步不要直接把 Lab 合入正式需求规格编辑器。
- 先做真实 LLM Provider 接入验证：
  - Provider 配置读取
  - 密钥不落前端
  - 结构化输出解析失败处理
  - 超时、重试、降级到 mock 或 WizardOrchestrator
- 真实 Provider 稳定后，再设计正式 P2 服务层如何调用 Brainstorming Service。

## 2026-05-01 后续人测修正补充

实现启动后，用户继续对 `会话管理 / CLI 式问答区` 提出交互细节意见，已形成实现修正和文档同步：

- 发送后 user 消息必须立即上屏，不能等 assistant 回复完成。
- 输入框支持多行输入：Enter 发送，Shift+Enter 换行。
- `quick_options` 不强制每轮出现；存在时才展示。
- 快捷选项改为纵向列表，以容纳较长选项。
- 推荐标签保留，但选项行本身不可点击；只有右侧“选择 X”按钮触发提交，避免误触。
- 快捷选项出现后，消息列表自动滚到底部，避免遮住最后一轮会话。

同步文档：

- `DOC/CODEX_DOC/02_设计说明/P2_需求分析系统/P2-Brainstorming能力原理验证与架构规划.md`
- `DOC/CODEX_DOC/02_设计说明/P2_需求分析系统/P2-Brainstorming-Lab状态机与v3原型草案.md`
- `DOC/CODEX_DOC/06_测试文档/03_机测记录/2026-05-01-141728-P2-Brainstorming-Lab-v3实现自检记录.md`
- `DOC/CODEX_DOC/08_原型与附图/2026-05-01-141500-CodeFactoryV2-P2-Brainstorming-Lab原型-v3/README.md`
