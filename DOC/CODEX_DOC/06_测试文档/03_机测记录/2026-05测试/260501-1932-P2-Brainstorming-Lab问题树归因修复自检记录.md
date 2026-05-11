# P2 Brainstorming Lab 问题树归因修复自检记录

记录时间：2026-05-01 19:32

## 1. 问题现象

用户在实测截图中发现：

- 问题树几乎把所有事实和正文建议都堆到一个问题节点下。
- 大量 `F-xxx` 和 `P-xxx` 直接暴露，用户难以理解其含义。
- 章节归类出现漂移，例如大量产物集中到 `用户角色`。

## 2. 根因

根因不在单纯 UI，也不主要在模型本身，而在 Brainstorming Service 的结构化归因逻辑：

```python
source_question_id = questions[0]["question_id"] if questions else None
```

旧逻辑永远把本轮新增事实和正文建议挂到第一个问题 `Q-001`，导致多轮会话后 `Q-001` 持续膨胀。

## 3. 修复内容

1. 后端改为优先选择当前第一个 `open` 问题作为本轮回答对象。
2. 新增问题写入 `target_section`，使前端优先使用后端归类，不完全依赖前端启发式猜测。
3. `confirmed_facts_delta` 生成的事实记录带上来源问题和目标章节。
4. mock 组织器解析快捷选项时优先保留选项文本语义，避免把所有 `B` 都解释成固定全局含义。
5. DeepSeek prompt 加强约束：章节白名单、只返回本轮新增事实、不要重复历史 open questions。
6. 前端将 `F/P` 的直接节点展示改为 `已确认事实` 和 `正文建议`。

## 4. 机测命令

```bash
uv run pytest apps/api/tests/test_brainstorm_api.py -q
corepack pnpm --dir apps/web test src/test/BrainstormLabPage.test.tsx
corepack pnpm --dir apps/web build
```

## 5. 机测结果

- API：`3 passed in 0.42s`
- 前端 Lab 测试：`1 passed`
- 前端构建：通过；存在既有 Vite chunk size 警告。

## 6. 浏览器检查

临时启动前端：

```bash
VITE_API_PROXY_TARGET=http://127.0.0.1:8000 corepack pnpm --dir apps/web dev --host 127.0.0.1 --port 5176
```

Playwright 操作：

1. 打开 `/p2-brainstorm-lab`。
2. 选择 `Mock Provider`。
3. 启动验证。
4. 进入 `会话管理`。
5. 发送 `A，先按计算分析工具理解`。
6. 点击 `选择 B`。

浏览器检查结果：

```text
1.1 系统目标
  Q-001 ... 已确认 · F-001 · P-001
  已确认事实 F-001：系统初步定位为空域计算分析工具
  正文建议 P-001 -> 1.1 系统目标

2.1 输入数据
  Q-002 ... 已确认 · F-002 · P-002
  已确认事实 F-002：用户选择先确认输出结果形式
  正文建议 P-002 -> 2.2 输出结果
```

浏览器断言：

```json
{
  "horizontalOverflow": false,
  "scrollWidth": 1440,
  "clientWidth": 1440,
  "failures": []
}
```

## 7. 残留问题

`Q-002` 当前仍是复合问题：`输入数据来源、计算结果形式、专家校核职责尚未确认。`

第二轮用户选择 `输出` 后，事实和正文建议已经正确挂到 `Q-002`，但该问题本身仍显示在 `2.1 输入数据` 下。这说明下一步可以继续把复合问题拆成更细的章节问题，例如：

- `Q-002 输入数据来源是什么？`
- `Q-003 输出结果形式是什么？`
- `Q-004 专家校核职责是什么？`

本轮先修复“所有产物污染 Q-001”的核心归因问题。
