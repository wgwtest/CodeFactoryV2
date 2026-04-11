# Archive Knowledge Review Editing Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Upgrade the current archive knowledge governance page into a real review-and-edit workflow that can rename, recategorize, alias-edit, approve, reject, batch-approve, and merge archive knowledge items with immediate effect on the archive documents and graph views.

**Architecture:** Keep the original extracted archive JSON immutable and introduce a curated JSON file that the app prefers for reads and writes. Extend the archive knowledge API with mutation endpoints, then rebuild the governance page into a filterable review workspace with an editor drawer and merge action; public archive pages continue to read through the same service so changes become visible immediately.

**Tech Stack:** FastAPI, pytest, React 18, TypeScript, Ant Design, Vitest

---

## File Structure

- Modify: `apps/api/app/archive_knowledge/service.py`
- Modify: `apps/api/app/api/routes/knowledge.py`
- Modify: `apps/api/tests/test_archive_knowledge_api.py`
- Modify: `apps/web/src/App.tsx`
- Modify: `apps/web/src/lib/api.ts`
- Modify: `apps/web/src/components/CandidateReviewTable.tsx`
- Modify: `apps/web/src/pages/GovernancePage.tsx`
- Modify: `apps/web/src/test/GovernancePage.test.tsx`

### Task 1: Define backend behavior with failing archive API tests

**Files:**
- Modify: `apps/api/tests/test_archive_knowledge_api.py`
- Test: `apps/api/tests/test_archive_knowledge_api.py`

- [ ] **Step 1: Write failing tests for archive review mutations and curated-read preference**

Add tests that assert:

```python
updated = client.patch(
    "/api/knowledge/archive/20161116-nas/items/entity-ov1",
    json={"name": "OV-1 修正版", "category": "architecture_concept", "aliases": ["运行概念图", "OV-1"]},
)
assert updated.status_code == 200
assert updated.json()["name"] == "OV-1 修正版"

review = client.post(
    "/api/knowledge/archive/20161116-nas/items/entity-nas/review",
    json={"review_status": "rejected"},
)
assert review.status_code == 200

graph = client.get("/api/knowledge/archive/20161116-nas/graph")
assert all(node["id"] != "entity-nas" for node in graph.json()["nodes"])

batch = client.post(
    "/api/knowledge/archive/20161116-nas/reviews/batch-approve",
    json={"item_ids": ["entity-ov1", "event-far-term"]},
)
assert batch.status_code == 200
assert batch.json() == {"updated_count": 2}

merged = client.post(
    "/api/knowledge/archive/20161116-nas/items/merge",
    json={"primary_item_id": "entity-ov1", "secondary_item_id": "entity-nas-duplicate"},
)
assert merged.status_code == 200
assert merged.json()["aliases"] == ["远期顶层运行概念图", "运行概念图", "国家空域系统（重复）"]
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd /home/wgw/CodexProject/CodeFactoryV2/.worktrees/knowledge-warehouse-foundation && PYTHONPATH=apps/api .venv/bin/pytest apps/api/tests/test_archive_knowledge_api.py -q`

Expected: FAIL with missing route or missing method errors for archive mutation APIs.

- [ ] **Step 3: Write minimal backend implementation**

Implement archive mutation support in:

```python
class ArchiveKnowledgeService:
    def _resolve_read_path(self, archive_id: str) -> Path:
        curated = self.output_root / f"{archive_id}-knowledge-curated.json"
        base = self.output_root / f"{archive_id}-knowledge.json"
        return curated if curated.exists() else base

    def _resolve_edit_path(self, archive_id: str) -> Path:
        return self.output_root / f"{archive_id}-knowledge-curated.json"
```

and add mutation routes like:

```python
@router.patch("/archive/{archive_id}/items/{item_id}")
def update_archive_item(...):
    detail = service.update_item(archive_id, item_id, payload)
    if detail is None:
        raise HTTPException(status_code=404, detail="Archive item not found")
    return detail
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd /home/wgw/CodexProject/CodeFactoryV2/.worktrees/knowledge-warehouse-foundation && PYTHONPATH=apps/api .venv/bin/pytest apps/api/tests/test_archive_knowledge_api.py -q`

Expected: PASS

- [ ] **Step 5: Commit**

```bash
cd /home/wgw/CodexProject/CodeFactoryV2/.worktrees/knowledge-warehouse-foundation
git add apps/api/app/archive_knowledge/service.py apps/api/app/api/routes/knowledge.py apps/api/tests/test_archive_knowledge_api.py
git commit -m "feat: add editable archive knowledge review api"
```

### Task 2: Define frontend review workspace behavior with failing tests

**Files:**
- Modify: `apps/web/src/test/GovernancePage.test.tsx`
- Modify: `apps/web/src/lib/api.ts`
- Test: `apps/web/src/test/GovernancePage.test.tsx`

- [ ] **Step 1: Write failing tests for renamed page, filters, drawer editing, batch approve, and merge**

Add tests that assert:

```tsx
expect(await screen.findByText("知识审核发布")).toBeInTheDocument();
expect(screen.getByLabelText("审核状态")).toHaveValue("pending");
await user.click(screen.getByRole("button", { name: "查看 / 编辑" }));
expect(await screen.findByText("应用修改")).toBeInTheDocument();
await user.click(screen.getByRole("button", { name: "批量通过" }));
expect(postMock).toHaveBeenCalledWith("/knowledge/archive/20161116-nas/reviews/batch-approve", {
  item_ids: ["entity-ov1"],
});
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd /home/wgw/CodexProject/CodeFactoryV2/.worktrees/knowledge-warehouse-foundation/apps/web && npm test -- GovernancePage.test.tsx`

Expected: FAIL because the current page still renders “候选知识审核队列”, has no filters, no editor drawer, and no mutation actions.

- [ ] **Step 3: Write minimal frontend API contracts**

Add types and helpers in `apps/web/src/lib/api.ts` for:

```ts
export type ArchiveReviewStatus = "pending" | "approved" | "rejected";
export type ArchiveReviewCandidate = { ...; review_status: ArchiveReviewStatus };
export type ArchiveKnowledgeItemUpdateInput = { name: string; category: string; aliases: string[] };
export type ArchiveKnowledgeMergeInput = { primary_item_id: string; secondary_item_id: string };
```

- [ ] **Step 4: Run test to verify it still fails for UI behavior only**

Run: `cd /home/wgw/CodexProject/CodeFactoryV2/.worktrees/knowledge-warehouse-foundation/apps/web && npm test -- GovernancePage.test.tsx`

Expected: FAIL with missing UI controls or text expectations, not missing TypeScript symbols.

- [ ] **Step 5: Commit**

```bash
cd /home/wgw/CodexProject/CodeFactoryV2/.worktrees/knowledge-warehouse-foundation
git add apps/web/src/lib/api.ts apps/web/src/test/GovernancePage.test.tsx
git commit -m "test: define archive review workspace behavior"
```

### Task 3: Implement the review workspace UI

**Files:**
- Modify: `apps/web/src/App.tsx`
- Modify: `apps/web/src/components/CandidateReviewTable.tsx`
- Modify: `apps/web/src/pages/GovernancePage.tsx`
- Test: `apps/web/src/test/GovernancePage.test.tsx`

- [ ] **Step 1: Implement renamed navigation and page framing**

Change the app shell text to:

```tsx
{ key: "/governance", label: <Link to="/governance">知识审核发布</Link> }
```

and page title copy to:

```tsx
<Typography.Title level={3}>知识审核发布</Typography.Title>
<Typography.Paragraph>
  审核机器抽取出的候选知识，并将修正直接应用到当前知识库。
</Typography.Paragraph>
```

- [ ] **Step 2: Implement filters, selection, and batch approve**

In `GovernancePage.tsx`, add local state for:

```tsx
const [query, setQuery] = useState("");
const [itemTypeFilter, setItemTypeFilter] = useState<"all" | "entity" | "event" | "process">("all");
const [reviewStatusFilter, setReviewStatusFilter] = useState<"all" | "pending" | "approved" | "rejected">("pending");
const [selectedRowKeys, setSelectedRowKeys] = useState<React.Key[]>([]);
```

and call the batch API with:

```tsx
await api.post(`/knowledge/archive/${archiveId}/reviews/batch-approve`, {
  item_ids: selectedRowKeys,
});
```

- [ ] **Step 3: Implement editor drawer with apply / approve / reject / merge**

Render a right-side drawer that loads `GET /knowledge/archive/${archiveId}/items/${itemId}` and contains:

```tsx
<Input value={draftName} onChange={(event) => setDraftName(event.target.value)} />
<Select value={draftCategory} options={categoryOptions} />
<Select mode="tags" value={draftAliases} onChange={setDraftAliases} />
<Button type="primary" onClick={handleApplyChanges}>应用修改</Button>
<Button onClick={() => handleReview("approved")}>通过</Button>
<Button danger onClick={() => handleReview("rejected")}>驳回</Button>
<Select value={mergeTargetId} options={mergeOptions} />
<Button onClick={handleMerge}>合并到当前项</Button>
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd /home/wgw/CodexProject/CodeFactoryV2/.worktrees/knowledge-warehouse-foundation/apps/web && npm test -- GovernancePage.test.tsx`

Expected: PASS

- [ ] **Step 5: Commit**

```bash
cd /home/wgw/CodexProject/CodeFactoryV2/.worktrees/knowledge-warehouse-foundation
git add apps/web/src/App.tsx apps/web/src/components/CandidateReviewTable.tsx apps/web/src/pages/GovernancePage.tsx apps/web/src/test/GovernancePage.test.tsx
git commit -m "feat: add archive knowledge review workspace"
```

### Task 4: Verify public archive pages reflect edits

**Files:**
- Modify: `apps/api/tests/test_archive_knowledge_api.py`
- Test: `apps/api/tests/test_archive_knowledge_api.py`
- Test: `apps/web/src/test/GovernancePage.test.tsx`

- [ ] **Step 1: Extend tests for visibility side effects**

Add backend assertions like:

```python
document_detail = client.get("/api/knowledge/archive/20161116-nas/documents/doc-1")
assert all(item["id"] != "entity-nas" for item in document_detail.json()["knowledge_items"])

search = client.get("/api/knowledge/archive/20161116-nas/search?query=国家空域系统")
assert search.json() == []
```

after rejecting `entity-nas`.

- [ ] **Step 2: Run focused backend and frontend tests**

Run:

```bash
cd /home/wgw/CodexProject/CodeFactoryV2/.worktrees/knowledge-warehouse-foundation
PYTHONPATH=apps/api .venv/bin/pytest apps/api/tests/test_archive_knowledge_api.py -q
cd apps/web
npm test -- GovernancePage.test.tsx DocumentsPage.test.tsx KnowledgeGraphPage.test.tsx AppRoutes.test.tsx
```

Expected: all targeted tests PASS.

- [ ] **Step 3: Manually verify the live app**

Open:

```text
http://127.0.0.1:5173/governance
http://127.0.0.1:5173/documents
http://127.0.0.1:5173/graph
```

Verify:

1. Navigation shows “知识审核发布”.
2. Rejecting an item removes it from graph and document knowledge sections after reload.
3. Renaming or merging an item updates the graph entity label and document drilldown text after reload.

- [ ] **Step 4: Commit**

```bash
cd /home/wgw/CodexProject/CodeFactoryV2/.worktrees/knowledge-warehouse-foundation
git add apps/api/tests/test_archive_knowledge_api.py apps/web/src/test/GovernancePage.test.tsx
git commit -m "test: verify archive review edits affect public views"
```
