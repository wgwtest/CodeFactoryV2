# Knowledge Graph Dual View Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 为知识图谱页面增加“列表视图 / 图谱视图”切换，让用户既能列表检索实体，也能在全局拓扑中点击节点后复用现有抽屉查看详情。

**Architecture:** 继续保留 `KnowledgeGraph` 作为实体区主容器，在其中增加视图模式状态。列表视图继续使用现有表格；图谱视图新增独立的 `KnowledgeTopologyGraph` 组件，消费已有 `ArchiveKnowledgeGraph` 数据并在节点点击时回调现有详情抽屉。搜索框继续保留，并在图谱视图中用于收缩为“命中节点 + 一度邻居”的子图，避免 1305 个实体全量裸铺影响可读性。

**Tech Stack:** React 18, Ant Design 5, Cytoscape, Vitest, Testing Library

---

### Task 1: 先锁定测试期望

**Files:**
- Modify: `apps/web/src/test/KnowledgeGraphPage.test.tsx`

- [ ] **Step 1: 写出失败测试，覆盖双视图切换**

```tsx
expect(await screen.findByRole("radio", { name: "列表视图" })).toBeChecked();
expect(screen.getByRole("radio", { name: "图谱视图" })).toBeInTheDocument();
fireEvent.click(screen.getByRole("radio", { name: "图谱视图" }));
expect(await screen.findByText("全局拓扑图")).toBeInTheDocument();
```

- [ ] **Step 2: 运行单测确认先红**

Run: `corepack pnpm --dir apps/web test -- KnowledgeGraphPage.test.tsx`
Expected: FAIL，提示缺少视图切换或缺少图谱视图标题。

### Task 2: 实现图谱视图组件

**Files:**
- Create: `apps/web/src/components/KnowledgeTopologyGraph.tsx`
- Modify: `apps/web/src/components/KnowledgeGraph.tsx`
- Test: `apps/web/src/test/KnowledgeGraphPage.test.tsx`

- [ ] **Step 1: 新建图谱组件，消费全局节点边数据**

```tsx
type KnowledgeTopologyGraphProps = {
  graph: ArchiveKnowledgeGraph;
  entities: ArchiveKnowledgeEntity[];
  query: string;
  selectedEntityId: string | null;
  onSelectEntity: (id: string) => void;
};
```

- [ ] **Step 2: 用 Cytoscape 渲染全局拓扑**

```tsx
const cy = cytoscape({
  container,
  elements,
  layout: { name: "cose", fit: true, padding: 36, animate: false },
  style: [...]
});
cy.on("tap", "node", (event) => onSelectEntity(event.target.id()));
```

- [ ] **Step 3: 图谱视图保留搜索联动**

```tsx
const filtered = buildTopologySubgraph(graph, entities, query);
```

### Task 3: 在实体区加双视图切换

**Files:**
- Modify: `apps/web/src/components/KnowledgeGraph.tsx`
- Test: `apps/web/src/test/KnowledgeGraphPage.test.tsx`

- [ ] **Step 1: 增加 `viewMode` 状态**

```tsx
const [viewMode, setViewMode] = useState<"list" | "graph">("list");
```

- [ ] **Step 2: 在右上角新增切换控件**

```tsx
<Segmented
  value={viewMode}
  onChange={(value) => setViewMode(value as "list" | "graph")}
  options={[
    { label: "列表视图", value: "list" },
    { label: "图谱视图", value: "graph" },
  ]}
/>
```

- [ ] **Step 3: 列表和图谱按模式渲染**

```tsx
{viewMode === "list" ? <Table ... /> : <KnowledgeTopologyGraph ... />}
```

### Task 4: 回归验证

**Files:**
- Verify: `apps/web/src/test/KnowledgeGraphPage.test.tsx`
- Verify: `apps/web/src/test/*.test.tsx`

- [ ] **Step 1: 跑目标单测**

Run: `corepack pnpm --dir apps/web test -- KnowledgeGraphPage.test.tsx`
Expected: PASS

- [ ] **Step 2: 跑全量前端测试**

Run: `corepack pnpm --dir apps/web test`
Expected: PASS，全部前端测试通过。
