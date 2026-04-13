# Process View Upgrade Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 将当前“流程视图”从静态流程清单升级为可检索、可下钻、可查看关系链路与证据的发布态流程工作台。

**Architecture:** 继续保留 `ProcessViewPage` 作为发布态流程页入口，列表数据仍从 `getArchiveProcesses()` 读取，不新造流程专用后端模型。前端在 `ProcessFlow` 内部补充搜索、选中流程、详情抽屉与关系邻域加载逻辑，并复用现有 `ValidationDrawer`、`EvidenceList`、`KnowledgeNeighborhoodGraph` 组件，让流程详情层级与实体详情对齐。

**Tech Stack:** React 18, TypeScript, Ant Design 5, Vitest, Testing Library

---

### Task 1: 先锁定流程页升级后的用户行为

**Files:**
- Modify: `apps/web/src/test/ProcessViewPage.test.tsx`

- [ ] **Step 1: 写失败测试，覆盖流程检索与详情抽屉**

```tsx
fireEvent.change(screen.getByPlaceholderText("搜索流程名称或证据摘录"), {
  target: { value: "路线图" },
});
expect(await screen.findByDisplayValue("路线图")).toBeInTheDocument();
fireEvent.click(screen.getByRole("button", { name: "查看链路" }));
expect(await screen.findByText("流程详情")).toBeInTheDocument();
expect(await screen.findByText("这是什么")).toBeInTheDocument();
expect(await screen.findByText("业务关系结构")).toBeInTheDocument();
expect(await screen.findByText("关系邻域")).toBeInTheDocument();
```

- [ ] **Step 2: 运行单测确认先红**

Run: `corepack pnpm --dir apps/web test -- ProcessViewPage.test.tsx`
Expected: FAIL，提示流程页缺少搜索框、缺少“查看链路”操作或缺少详情抽屉内容。

### Task 2: 实现流程列表的检索与链路入口

**Files:**
- Modify: `apps/web/src/components/ProcessFlow.tsx`
- Modify: `apps/web/src/pages/ProcessViewPage.tsx`
- Test: `apps/web/src/test/ProcessViewPage.test.tsx`

- [ ] **Step 1: 在 `ProcessFlow` 增加关键字筛选状态**

```tsx
const [searchValue, setSearchValue] = useState("");
const deferredSearchValue = useDeferredValue(searchValue);
const filteredProcesses = processes.filter((item) => {
  const query = deferredSearchValue.trim().toLowerCase();
  if (!query) {
    return true;
  }
  return [item.name, ...item.evidence.map((entry) => entry.excerpt)].join(" ").toLowerCase().includes(query);
});
```

- [ ] **Step 2: 在列表顶部补充状态说明与搜索框**

```tsx
<Input.Search
  allowClear
  placeholder="搜索流程名称或证据摘录"
  value={searchValue}
  onChange={(event) => setSearchValue(event.target.value)}
/>
```

- [ ] **Step 3: 为每个流程项提供“查看链路”动作**

```tsx
<Button type="link" onClick={() => setSelectedProcessId(record.id)}>
  查看链路
</Button>
```

### Task 3: 复用已发布知识详情接口补齐流程详情抽屉

**Files:**
- Modify: `apps/web/src/components/ProcessFlow.tsx`
- Test: `apps/web/src/test/ProcessViewPage.test.tsx`

- [ ] **Step 1: 在 `ProcessFlow` 中按选中流程加载详情与邻域**

```tsx
const [selectedProcessId, setSelectedProcessId] = useState<string | null>(null);
const [detail, setDetail] = useState<ArchiveKnowledgeItemDetail | null>(null);
const [itemGraph, setItemGraph] = useState<ArchiveKnowledgeItemGraph | null>(null);

const [detailResponse, graphResponse] = await Promise.all([
  getArchiveItemDetail(activeProcessId),
  getArchiveItemGraph(activeProcessId),
]);
```

- [ ] **Step 2: 复用现有详情组件结构，展示流程解释、证据、关联文档、业务关系结构与关系邻域**

```tsx
<ValidationDrawer title="流程详情" ...>
  <EvidenceList title="证据摘录" items={detail.evidence} />
  <KnowledgeNeighborhoodGraph graph={itemGraph} />
</ValidationDrawer>
```

- [ ] **Step 3: 在关系结构中显式展示流程关联实体、事件和约束**

```tsx
{detail.relationship_sections.map((section) => (
  <List
    dataSource={section.items}
    renderItem={(item) => (
      <List.Item>
        <Tag>{itemTypeLabels[item.item_type] ?? item.item_type}</Tag>
        <Tag color="blue">{item.relation_label}</Tag>
        <Typography.Text>{item.name}</Typography.Text>
      </List.Item>
    )}
  />
))}
```

### Task 4: 回写阶段一设计基线并完成验证

**Files:**
- Modify: `docs/superpowers/specs/2026-04-11-software-factory-platform-design.md`
- Verify: `apps/web/src/test/ProcessViewPage.test.tsx`
- Verify: `corepack pnpm --dir apps/web test`

- [ ] **Step 1: 将 `P1.5.3` 的当前实现回写到总设计文档**

```md
- 流程页已升级为“流程清单 + 详情抽屉 + 关系邻域”形态
- 当前流程详情已支持“这是什么、证据摘录、关联文档、业务关系结构、关系邻域”
- 当前仍未进入步骤级 BPMN/时序编排，后续增强应建立在新增步骤级结构化数据之上
```

- [ ] **Step 2: 跑目标单测**

Run: `corepack pnpm --dir apps/web test -- ProcessViewPage.test.tsx`
Expected: PASS

- [ ] **Step 3: 跑全量前端测试**

Run: `corepack pnpm --dir apps/web test`
Expected: PASS，全量前端测试通过。
