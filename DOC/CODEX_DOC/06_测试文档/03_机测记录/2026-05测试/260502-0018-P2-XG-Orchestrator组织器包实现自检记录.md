# P2 XG-Orchestrator 组织器包实现自检记录

**时间：** 2026-05-02 00:18:33

## 1. 本轮目标

把 P2 Brainstorming Lab 的组织器从硬编码列表推进为 skill-like package 形态，并首版接入两个 XG 组织器：

- `xg-brainstorming-orchestrator`
- `xg-strong-rule-orchestrator`

## 2. 改动摘要

- 新增 `orchestrators/xg/` 包目录。
- 新增两个组织器包，均包含 `manifest.json / ORCHESTRATOR.md / contract.schema.json / policy.md / prompt.md / examples / tests`。
- 新增后端 `OrchestratorRegistry`，从包目录读取并校验组织器。
- `/api/brainstorm/orchestrators` 改为返回注册器结果。
- 默认组织器改为 `xg-brainstorming-orchestrator`。
- `xg-strong-rule-orchestrator` 支持创建会话并运行符合新版 Turn 协议的一轮输出。
- Provider 仍保持独立，不与 Orchestrator 混同。

## 3. 已执行验证

```bash
uv run pytest apps/api/tests/test_brainstorm_api.py -q
```

结果：

```text
7 passed
```

```bash
corepack pnpm --dir apps/web test src/test/BrainstormLabPage.test.tsx
```

结果：

```text
2 passed
```

```bash
corepack pnpm --dir apps/web test src/test/AppRoutes.test.tsx
```

结果：

```text
11 passed
```

```bash
corepack pnpm --dir apps/web build
```

结果：

```text
✓ built in 4.13s
```

说明：构建存在既有 Vite CJS API deprecation 和 chunk size 警告，未阻断构建。

```bash
uv run python -m py_compile apps/api/app/brainstorm/orchestrators.py apps/api/app/brainstorm/service.py apps/api/app/brainstorm/models.py apps/api/app/db/models/requirements.py
```

结果：通过。

```bash
git diff --check
```

结果：通过。

```bash
rg -n "<本地 DeepSeek 明文 API Key>" -g '!**/.env'
```

结果：未发现明文 API Key。

## 4. 风险与后续

- 当前 `local_runner` 强规则组织器仍由 Host 内置受控路径执行，尚未做任意 runner 动态加载。
- `contract.schema.json` 首版是声明性约束，后续可升级为完整 JSON Schema 校验。
- 前端当前展示组织器包名称和描述，尚未单独展开包路径、契约和 mode 的详情面板。
