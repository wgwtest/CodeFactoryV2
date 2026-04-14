# Long Document Formal Extraction Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 让正式知识库抽取在长文档场景下走“结构化分块 -> 分块抽取 -> 全局归并”链路，并把块级来源信息与执行统计写入现有抽取报告。

**Architecture:** 保持 `build_archive_knowledge()`、`build_knowledge_index()` 和前端消费协议不变，仅在 `ExtractionService.extract_document()` 内增加正式模式长文档分流。新增独立的 chunking/merging 组件，块内复用现有规则抽取与结构化大模型抽取，文档级统一归并为单个 `ExtractionBatch` 继续交给知识构建链路。

**Tech Stack:** Python 3.11, FastAPI backend, Pydantic v2, pytest, Docling, LlamaIndex structured LLM adapter

---

### Task 1: 锁定长文档分块规则与报告契约

**Files:**
- Create: `apps/api/tests/test_extraction_chunking.py`
- Modify: `apps/api/app/config.py`
- Modify: `apps/api/app/extraction/schema.py`

- [ ] **Step 1: 先写分块规则失败测试**

```python
def test_build_document_chunks_keeps_heading_groups_and_table_rows_separate():
    segments = [
        ParsedSegment(heading="1 总体", content="A" * 1200, anchor={"page": 1}, block_type="paragraph"),
        ParsedSegment(heading="1 总体", content="B" * 1200, anchor={"page": 1}, block_type="paragraph"),
        ParsedSegment(heading="交换表", content="| A | B |", anchor={"page": 2}, block_type="table_row"),
    ]

    chunks = build_document_chunks(segments, max_chars=1800)

    assert len(chunks) == 3
    assert chunks[0].heading == "1 总体"
    assert chunks[-1].block_types == ["table_row"]
```

- [ ] **Step 2: 运行定向测试确认当前为红**

Run: `pytest apps/api/tests/test_extraction_chunking.py::test_build_document_chunks_keeps_heading_groups_and_table_rows_separate -v`

Expected: FAIL，提示 `build_document_chunks` 或 `DocumentChunk` 尚不存在。

- [ ] **Step 3: 补充正式抽取配置与 schema**

```python
class Settings(BaseSettings):
    formal_chunk_segment_threshold: int = 120
    formal_chunk_char_threshold: int = 50000
    formal_chunk_char_limit: int = 32000
```

```python
class DocumentSourceRef(BaseModel):
    chunk_id: str
    chunk_heading: str
    segment_ids: list[str] = Field(default_factory=list)
    anchors: list[dict] = Field(default_factory=list)


class ExtractionBatch(BaseModel):
    ...
    metadata: dict = Field(default_factory=dict)
```

- [ ] **Step 4: 运行新增测试确认已转绿**

Run: `pytest apps/api/tests/test_extraction_chunking.py -v`

Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add apps/api/tests/test_extraction_chunking.py apps/api/app/config.py apps/api/app/extraction/schema.py
git commit -m "test: define chunking contract for formal extraction"
```

### Task 2: 落地分块器与文档级归并器

**Files:**
- Create: `apps/api/app/extraction/chunking.py`
- Modify: `apps/api/tests/test_extraction_service.py`
- Modify: `apps/api/app/extraction/service.py`

- [ ] **Step 1: 先写正式模式长文档分流失败测试**

```python
def test_formal_extraction_uses_chunked_path_for_long_document(monkeypatch):
    segments = [
        ParsedSegment(heading=f"第{i}章", content="领域内容 " * 200, anchor={"page": i}, block_type="paragraph")
        for i in range(1, 160)
    ]
    calls = {"chunked": 0}

    def fake_chunked(self, **kwargs):
        calls["chunked"] += 1
        return ExtractionBatch(document_id="doc-1", title="长文档", candidates=[], relations=[], metadata={})

    monkeypatch.setattr(ExtractionService, "_extract_with_chunks", fake_chunked)

    ExtractionService(formal_extraction_mode=True).extract_document(
        document_id="doc-1",
        title="长文档",
        file_path="runtime/long.pdf",
        segments=segments,
    )

    assert calls["chunked"] == 1
```

- [ ] **Step 2: 运行定向测试确认当前为红**

Run: `pytest apps/api/tests/test_extraction_service.py::test_formal_extraction_uses_chunked_path_for_long_document -v`

Expected: FAIL，提示 `_extract_with_chunks` 未被调用或方法不存在。

- [ ] **Step 3: 实现分块器与归并器最小代码**

```python
@dataclass(slots=True)
class DocumentChunk:
    chunk_id: str
    chunk_index: int
    heading: str
    segments: list[ParsedSegment]
    char_count: int
    block_types: list[str]
```

```python
def build_document_chunks(segments: list[ParsedSegment], *, max_chars: int) -> list[DocumentChunk]:
    ...
```

```python
class ExtractionService:
    def extract_document(...):
        if self._should_use_chunked_formal_extraction(segments):
            return self._extract_with_chunks(...)
        ...
```

- [ ] **Step 4: 运行 extraction 定向测试**

Run: `pytest apps/api/tests/test_extraction_service.py -v`

Expected: PASS，原有采样逻辑测试仍通过，新增正式模式分流测试通过。

- [ ] **Step 5: Commit**

```bash
git add apps/api/app/extraction/chunking.py apps/api/app/extraction/service.py apps/api/tests/test_extraction_service.py
git commit -m "feat: add chunked formal extraction flow"
```

### Task 3: 为块级结果补来源信息并扩展执行报告

**Files:**
- Modify: `apps/api/app/extraction/service.py`
- Modify: `apps/api/app/knowledge_builder.py`
- Modify: `apps/api/tests/test_archive_knowledge_rebuild.py`
- Modify: `apps/api/tests/test_extraction_service.py`

- [ ] **Step 1: 先写来源信息与报告字段失败测试**

```python
def test_chunked_formal_extraction_records_source_refs():
    batch = ...
    candidate = next(item for item in batch.candidates if item.canonical_name == "信号支援")
    assert candidate.payload["source_refs"][0]["chunk_id"] == "chunk-001"
```

```python
def test_build_knowledge_index_collects_chunking_diagnostics(tmp_path):
    ...
    assert diagnostics[0]["chunking_used"] is True
    assert diagnostics[0]["chunk_count"] == 3
```

- [ ] **Step 2: 运行定向测试确认当前为红**

Run: `pytest apps/api/tests/test_extraction_service.py::test_chunked_formal_extraction_records_source_refs apps/api/tests/test_archive_knowledge_rebuild.py::test_build_knowledge_index_collects_chunking_diagnostics -v`

Expected: FAIL，提示 `source_refs` / `chunk_count` 不存在。

- [ ] **Step 3: 扩展候选、关系归并与诊断信息**

```python
merged_payload["source_refs"] = _merge_source_refs(
    existing.payload.get("source_refs", []),
    candidate.payload.get("source_refs", []),
)
```

```python
diagnostics_collector.append(
    {
        ...
        "chunking_used": bool(batch.metadata.get("chunking_used")),
        "chunk_count": batch.metadata.get("chunk_count"),
        "chunk_candidate_count_total": batch.metadata.get("chunk_candidate_count_total"),
        "chunk_relation_count_total": batch.metadata.get("chunk_relation_count_total"),
    }
)
```

- [ ] **Step 4: 运行相关后端测试**

Run: `pytest apps/api/tests/test_extraction_service.py apps/api/tests/test_archive_knowledge_rebuild.py -v`

Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add apps/api/app/extraction/service.py apps/api/app/knowledge_builder.py apps/api/tests/test_extraction_service.py apps/api/tests/test_archive_knowledge_rebuild.py
git commit -m "feat: add chunk source refs to extraction diagnostics"
```

### Task 4: 做正式抽取回归验证

**Files:**
- Verify: `apps/api/app/archive_knowledge/builder.py`
- Verify: `.data/knowledge_output/MJ-V1-extraction-report.json`
- Verify: `.data/knowledge_output/MJ-V1-knowledge.json`

- [ ] **Step 1: 跑完整后端测试**

Run: `pytest apps/api/tests -q`

Expected: PASS

- [ ] **Step 2: 对长文档样本执行一次正式回归抽取**

Run: `PYTHONPATH=apps/api python scripts/build_archive_knowledge.py --archive-id MJ-V1 --archive-name "技术资料-V1" --source-dir DataSource/doctrine --formal`

Expected: 命令完成并刷新 `.data/knowledge_output/MJ-V1-extraction-report.json`

- [ ] **Step 3: 校验回归结果**

```bash
python - <<'PY'
import json
from pathlib import Path
report = json.loads(Path('.data/knowledge_output/MJ-V1-extraction-report.json').read_text())
doc = next(item for item in report['documents'] if 'FM_6-02' in item['title'])
print(doc['candidate_count'], doc['chunking_used'], doc['chunk_count'])
PY
```

Expected: `chunking_used=True`，`chunk_count > 1`，`candidate_count` 高于旧报告中的 `69` 候选近似水平或至少显著提升。

- [ ] **Step 4: 视验证结果决定是否提交并推送**

Run: `git status --short`

Expected: 仅包含本轮相关改动。
