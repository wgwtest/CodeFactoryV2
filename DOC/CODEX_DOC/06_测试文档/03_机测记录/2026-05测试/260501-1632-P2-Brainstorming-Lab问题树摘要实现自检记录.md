# P2 Brainstorming Lab 问题树摘要实现自检记录

记录时间：2026-05-01 16:32

## 1. 验证范围

- 页面：`/p2-brainstorm-lab`
- 模块：`会话管理` Tab 中的 `会话摘要 / 过程产物`
- 改动边界：保留组织器配置、CLI 问答区、当前 Turn、调用日志；仅将旧线性摘要替换为需求规格章节导向的问题树。

## 2. 关键检查点

1. 旧的 `问题工作项 / 已确认事实 / 文档修补建议` 三块线性卡片不再出现。
2. 新摘要区显示 `需求规格问题树`。
3. `Q-xxx` 问题节点、`F-xxx` 事实节点、`P-xxx` 文档建议节点能够在同一章节树下挂接。
4. 已确认问题显示 `已确认 · F-xxx · P-xxx`。
5. 未确认问题按章节启发式归类；无法落章的内容进入 `未归类澄清项`。
6. DeepSeek 返回 `1.1 系统定位` 时，前端显示归一到模板章节 `1.1 系统目标`。
7. 1440x900 浏览器视口无横向溢出。

## 3. 机测命令

```bash
corepack pnpm --dir apps/web test src/test/BrainstormLabPage.test.tsx
corepack pnpm --dir apps/web build
uv run pytest apps/api/tests/test_brainstorm_api.py -q
```

## 4. 机测结果

- `BrainstormLabPage.test.tsx`：1 个测试通过。
- `apps/web build`：TypeScript 编译和 Vite 构建通过；存在既有的大 chunk 警告。
- `apps/api/tests/test_brainstorm_api.py`：3 个测试通过。

## 5. 浏览器检查

临时启动：

```bash
VITE_API_PROXY_TARGET=http://127.0.0.1:8000 corepack pnpm --dir apps/web dev --host 127.0.0.1 --port 5176
```

Playwright 操作：

1. 打开 `http://127.0.0.1:5176/p2-brainstorm-lab`。
2. 点击 `启动验证`。
3. 进入 `会话管理`。
4. 输入并发送 `A，先按计算分析工具理解`。
5. 等待 `P-001 -> 1.1 系统目标` 出现。

浏览器检查结果：

```json
{
  "hasTree": true,
  "hasSystemGoal": true,
  "hasPatch": true,
  "hasOldLinearTitles": false,
  "horizontalOverflow": false,
  "scrollWidth": 1440,
  "clientWidth": 1440,
  "failures": []
}
```

浏览器检查过程中临时生成过截图；该截图仅用于本轮人工查看，不纳入版本材料。

## 6. 备注

- 真实 DeepSeek 链路返回的问题内容会随模型输出变化，因此本次浏览器检查只验证树形摘要的结构、章节归一、旧线性标题移除和布局稳定性。
- 左侧 Tab 中 `RequirementAnalysisOrchestrator` 在 1440x900 截图下发生换行，属于既有侧栏长英文文案问题，不属于本次会话摘要区域改动。
