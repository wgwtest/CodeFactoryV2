# P2/P1 Scenario Data Generator Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a deterministic P1/P2 scenario data generator that can materialize mock P1 published knowledge, create a P2 authoring document, drive scripted brainstorming turns, auto-complete gaps, and freeze a P3-consumable package.

**Architecture:** Add a focused scenario subsystem under `app.requirement_authoring` with fixture registry, mock P1 projector, and brainstorming contract. Extend the existing requirement-authoring API and service instead of creating a parallel simulator, then add a compact scenario control inside the existing P2 workbench.

**Tech Stack:** FastAPI, SQLAlchemy, Pydantic, existing JSON P1 knowledge format, React 18, Ant Design, Vitest, pytest.

---

## File Structure

- Create `apps/api/app/requirement_authoring/scenario_models.py`
  - Pydantic contracts for scenario summaries, materialization requests, brainstorming responses, scenario turns, and auto-complete responses.
- Create `apps/api/app/requirement_authoring/scenario_fixtures.py`
  - Deterministic `airspace-collaboration` scenario pack with P1 knowledge seed, P2 authoring seed, scripted responses, and expected output markers.
- Create `apps/api/app/requirement_authoring/scenario_projector.py`
  - Converts a scenario pack into P1 published-knowledge JSON and writes it to the configured knowledge output root.
- Create `apps/api/tests/test_requirement_authoring_scenarios.py`
  - Backend acceptance tests for scenario listing, materialization, scenario turns, auto-complete, gap check, freeze, and mock P1 readability.
- Modify `apps/api/app/requirement_authoring/service.py`
  - Add scenario listing, materialization, scenario turn handling, auto-complete, field patch validation, and scenario metadata in `semantic_state`.
- Modify `apps/api/app/api/routes/requirement_authoring.py`
  - Add `/scenarios`, `/scenarios/{scenario_id}/materialize`, `/documents/{document_id}/scenario-turns`, and `/documents/{document_id}/auto-complete`.
- Modify `apps/web/src/lib/api.ts`
  - Add frontend types for scenario summary, materialization response, scenario turn input, and auto-complete result.
- Modify `apps/web/src/lib/requirementAuthoring.ts`
  - Add API client functions for scenario list, materialize, scenario turn, and auto-complete.
- Modify `apps/web/src/pages/RequirementAuthoringPage.tsx`
  - Add a small scenario-data control in the settings popover, route selected scenario materialization into the existing document state, and use scenario-turn endpoint for scenario-bound documents.
- Modify `apps/web/src/pages/RequirementAuthoringPage.css`
  - Style the scenario control and mock source marker without changing the accepted two-panel layout.
- Modify `apps/web/src/test/RequirementAuthoringPage.test.tsx`
  - Extend the existing workbench test to cover scenario materialization, scenario source marker, scripted turn, auto-complete, and freeze.

## Task 1: Backend Scenario Contracts And Fixture Registry

**Files:**
- Create: `apps/api/app/requirement_authoring/scenario_models.py`
- Create: `apps/api/app/requirement_authoring/scenario_fixtures.py`
- Test: `apps/api/tests/test_requirement_authoring_scenarios.py`

- [ ] **Step 1: Write the failing scenario registry API test**

Add this test file:

```python
from fastapi.testclient import TestClient

from app.main import create_app


def test_requirement_authoring_lists_deterministic_scenarios() -> None:
    client = TestClient(create_app())

    response = client.get("/api/requirement-authoring/scenarios")

    assert response.status_code == 200
    payload = response.json()
    assert payload["default_scenario_id"] == "airspace-collaboration"
    assert [item["scenario_id"] for item in payload["items"]] == ["airspace-collaboration"]
    assert payload["items"][0]["scenario_name"] == "空域协同规划软件"
    assert payload["items"][0]["source_mode"] == "mock_p1"
```

- [ ] **Step 2: Run the test to verify it fails**

Run:

```bash
uv run pytest apps/api/tests/test_requirement_authoring_scenarios.py::test_requirement_authoring_lists_deterministic_scenarios -q
```

Expected: FAIL with `404` because `/api/requirement-authoring/scenarios` is not registered.

- [ ] **Step 3: Add scenario Pydantic models**

Create `apps/api/app/requirement_authoring/scenario_models.py`:

```python
from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


SourceMode = Literal["mock_p1", "live_p1"]
BrainstormingMode = Literal["mock_rule", "llm_assisted", "disabled"]


class RequirementAuthoringScenarioSummary(BaseModel):
    scenario_id: str
    scenario_name: str
    version: str
    domain: str
    default_template_code: str
    source_mode: SourceMode = "mock_p1"
    description: str


class RequirementAuthoringScenarioCatalog(BaseModel):
    default_scenario_id: str
    items: list[RequirementAuthoringScenarioSummary]


class RequirementAuthoringScenarioMaterialize(BaseModel):
    model_config = ConfigDict(extra="forbid")

    layout_ratio: Literal["2:3", "1:1"] = "2:3"
    title: str | None = None


class RequirementAuthoringScenarioTurnWrite(BaseModel):
    model_config = ConfigDict(extra="forbid")

    content: str
    mode: BrainstormingMode = "mock_rule"


class BrainstormingQuestion(BaseModel):
    question_id: str
    prompt: str
    suggested_replies: list[str] = Field(default_factory=list)


class BrainstormingSourceRef(BaseModel):
    archive_id: str
    item_id: str
    evidence_id: str


class BrainstormingClausePatch(BaseModel):
    clause_id: str
    content: str


class BrainstormingResponse(BaseModel):
    assistant_message: str
    field_patches: dict[str, str] = Field(default_factory=dict)
    clause_patches: list[BrainstormingClausePatch] = Field(default_factory=list)
    next_questions: list[BrainstormingQuestion] = Field(default_factory=list)
    source_refs: list[BrainstormingSourceRef] = Field(default_factory=list)
    confidence: float = Field(ge=0, le=1, default=1)
    blocking_risks: list[str] = Field(default_factory=list)
```

- [ ] **Step 4: Add the deterministic scenario fixture**

Create `apps/api/app/requirement_authoring/scenario_fixtures.py`:

```python
from __future__ import annotations

from copy import deepcopy


DEFAULT_SCENARIO_ID = "airspace-collaboration"

AIRSPACE_COLLABORATION_SCENARIO: dict = {
    "scenario_id": "airspace-collaboration",
    "scenario_name": "空域协同规划软件",
    "version": "1.0.0",
    "domain": "空域协同规划",
    "default_template_code": "81433",
    "description": "围绕空域申请、冲突校核、协同会签和异常处置生成完整 P2 闭环。",
    "p1_knowledge_seed": {
        "archive_id": "mock-airspace-p1",
        "archive_name": "模拟 P1 空域协同知识库",
        "publication": {
            "version_label": "mock-airspace-v1",
            "published_at": "2026-04-30T00:00:00+08:00",
            "publisher": "p2-scenario-generator",
        },
        "documents": [
            {"id": "doc-airspace-rule", "title": "空域协同规划业务规则", "source": "scenario_pack"},
            {"id": "doc-airspace-flow", "title": "空域任务规划与冲突处置流程", "source": "scenario_pack"},
        ],
        "entities": [
            {
                "id": "entity-collaboration-task",
                "name": "协同任务",
                "category": "domain_object",
                "aliases": ["空域协同任务"],
                "document_ids": ["doc-airspace-flow"],
                "review_status": "approved",
                "evidence": [{"document_id": "doc-airspace-flow", "evidence_id": "ev-task-001", "excerpt": "协同任务承载申请、校核、会签和发布全过程。"}],
            },
            {
                "id": "entity-conflict-window",
                "name": "冲突窗口",
                "category": "domain_object",
                "aliases": ["空域冲突窗口"],
                "document_ids": ["doc-airspace-rule"],
                "review_status": "approved",
                "evidence": [{"document_id": "doc-airspace-rule", "evidence_id": "ev-conflict-001", "excerpt": "发现冲突窗口后，不得直接发布规划方案。"}],
            },
        ],
        "processes": [
            {
                "id": "process-collaboration-planning",
                "name": "协同规划与冲突处置",
                "category": "domain_process",
                "aliases": ["协同规划闭环"],
                "document_ids": ["doc-airspace-flow"],
                "review_status": "approved",
                "evidence": [{"document_id": "doc-airspace-flow", "evidence_id": "ev-process-001", "excerpt": "流程包括任务创建、冲突校核、方案会签、结果发布和异常回退。"}],
            }
        ],
        "events": [
            {
                "id": "event-timeout-escalation",
                "name": "会签超时提醒",
                "category": "control_event",
                "aliases": ["超时提醒"],
                "document_ids": ["doc-airspace-rule"],
                "review_status": "approved",
                "evidence": [{"document_id": "doc-airspace-rule", "evidence_id": "ev-timeout-001", "excerpt": "会签超时后系统应提醒责任人并保留人工确认入口。"}],
            }
        ],
        "relations": [
            {"from": "process-collaboration-planning", "to": "entity-collaboration-task", "type": "describes"},
            {"from": "process-collaboration-planning", "to": "entity-conflict-window", "type": "operational_exchange"},
            {"from": "event-timeout-escalation", "to": "process-collaboration-planning", "type": "scoped_by"},
        ],
    },
    "p2_authoring_seed": {
        "title": "空域协同规划软件需求规格说明",
        "layout_ratio": "2:3",
        "initial_fields": {
            "application_name": "空域协同规划软件",
            "domain_scope": "空域协同规划",
            "target_users": "运行协调员、规划审核员、体系架构师",
            "main_process": "协同规划与冲突处置",
        },
        "quick_inputs": ["可以", "加超时", "更正式", "补验收", "自动补齐"],
    },
    "conversation_seed": {
        "assistant_opening": "我已装载模拟 P1 空域协同知识库，将按标准规格骨架持续补齐。你可以直接回：可以 / 加超时 / 更正式 / 补验收 / 自动补齐。",
        "field_patch_rules": {
            "可以": {"normal_flow": "系统应支持创建协同任务、执行冲突校核、组织方案会签、发布规划结果并形成处置记录。"},
            "加超时": {"exception_flow": "系统应在方案会签超时后提醒责任人，并允许人工确认后继续处理。"},
            "更正式": {"normal_flow": "系统应支持协同任务创建、冲突窗口识别、方案会签、结果发布与过程留痕，并保证关键状态可追溯。"},
            "补验收": {"acceptance_criteria": "验收时应验证协同任务可创建、冲突窗口可识别、会签超时可提醒、规划结果可发布且关键过程可追溯。"},
        },
        "auto_complete_fields": {
            "normal_flow": "系统应支持协同任务创建、冲突窗口识别、方案会签、结果发布与过程留痕，并保证关键状态可追溯。",
            "exception_flow": "系统应在方案会签超时后提醒责任人，并允许人工确认后继续处理；发现冲突窗口时不得直接发布规划方案。",
            "non_functional": "系统应保证关键告警 2 分钟内反馈，关键操作、会签结果和异常处置过程可审计追溯。",
            "acceptance_criteria": "验收时应验证协同任务可创建、冲突窗口可识别、会签超时可提醒、规划结果可发布且关键过程可追溯。",
        },
    },
    "expected_output": {
        "required_fields": ["application_name", "domain_scope", "target_users", "main_process", "normal_flow", "exception_flow", "non_functional", "acceptance_criteria"],
        "required_fragments": ["空域协同规划软件", "协同规划与冲突处置", "会签超时", "关键过程可追溯"],
    },
}

SCENARIOS = {DEFAULT_SCENARIO_ID: AIRSPACE_COLLABORATION_SCENARIO}


def list_scenario_summaries() -> list[dict]:
    return [
        {
            "scenario_id": scenario["scenario_id"],
            "scenario_name": scenario["scenario_name"],
            "version": scenario["version"],
            "domain": scenario["domain"],
            "default_template_code": scenario["default_template_code"],
            "source_mode": "mock_p1",
            "description": scenario["description"],
        }
        for scenario in SCENARIOS.values()
    ]


def get_scenario(scenario_id: str) -> dict | None:
    scenario = SCENARIOS.get(scenario_id)
    if scenario is None:
        return None
    return deepcopy(scenario)
```

- [ ] **Step 5: Wire the catalog route**

Modify `apps/api/app/requirement_authoring/service.py` imports and add this method:

```python
from app.requirement_authoring.scenario_fixtures import DEFAULT_SCENARIO_ID, list_scenario_summaries
from app.requirement_authoring.scenario_models import RequirementAuthoringScenarioCatalog, RequirementAuthoringScenarioSummary


    def list_scenarios(self) -> dict:
        return RequirementAuthoringScenarioCatalog(
            default_scenario_id=DEFAULT_SCENARIO_ID,
            items=[RequirementAuthoringScenarioSummary.model_validate(item) for item in list_scenario_summaries()],
        ).model_dump(mode="json")
```

Modify `apps/api/app/api/routes/requirement_authoring.py`:

```python
@router.get("/scenarios")
def list_requirement_authoring_scenarios(
    service: RequirementAuthoringService = Depends(get_requirement_authoring_service),
):
    return service.list_scenarios()
```

- [ ] **Step 6: Run the scenario catalog test**

Run:

```bash
uv run pytest apps/api/tests/test_requirement_authoring_scenarios.py::test_requirement_authoring_lists_deterministic_scenarios -q
```

Expected: `1 passed`.

- [ ] **Step 7: Commit Task 1**

```bash
git add apps/api/app/requirement_authoring/scenario_models.py apps/api/app/requirement_authoring/scenario_fixtures.py apps/api/app/requirement_authoring/service.py apps/api/app/api/routes/requirement_authoring.py apps/api/tests/test_requirement_authoring_scenarios.py
git commit -m "添加P2场景包注册表"
```

## Task 2: Materialize Mock P1 Knowledge And Seed P2 Document

**Files:**
- Create: `apps/api/app/requirement_authoring/scenario_projector.py`
- Modify: `apps/api/app/requirement_authoring/service.py`
- Modify: `apps/api/app/api/routes/requirement_authoring.py`
- Test: `apps/api/tests/test_requirement_authoring_scenarios.py`

- [ ] **Step 1: Add the failing materialization test**

Append this test:

```python
def test_requirement_authoring_materializes_mock_p1_and_p2_document() -> None:
    client = TestClient(create_app())

    response = client.post(
        "/api/requirement-authoring/scenarios/airspace-collaboration/materialize",
        json={"layout_ratio": "2:3"},
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["scenario"]["scenario_id"] == "airspace-collaboration"
    assert payload["mock_archive"]["archive_id"] == "mock-airspace-p1"
    assert payload["document"]["title"] == "空域协同规划软件需求规格说明"
    assert payload["document"]["archive_ids"] == ["mock-airspace-p1"]
    assert payload["document"]["semantic_state"]["scenario"]["scenario_id"] == "airspace-collaboration"
    assert payload["document"]["semantic_state"]["fields"]["application_name"] == "空域协同规划软件"
    assert payload["document"]["semantic_state"]["fields"]["normal_flow"] == ""

    summary = client.get("/api/knowledge/archive/mock-airspace-p1/summary")
    assert summary.status_code == 200
    assert summary.json()["archive_id"] == "mock-airspace-p1"
    assert summary.json()["entity_count"] == 2
    assert summary.json()["process_count"] == 1
```

- [ ] **Step 2: Run the materialization test to verify it fails**

Run:

```bash
uv run pytest apps/api/tests/test_requirement_authoring_scenarios.py::test_requirement_authoring_materializes_mock_p1_and_p2_document -q
```

Expected: FAIL with `404` because the materialize endpoint does not exist.

- [ ] **Step 3: Create the P1 mock knowledge projector**

Create `apps/api/app/requirement_authoring/scenario_projector.py`:

```python
from __future__ import annotations

import json
from pathlib import Path


class ScenarioP1Projector:
    def __init__(self, output_root: str | Path) -> None:
        self.output_root = Path(output_root)

    def materialize(self, scenario: dict) -> dict:
        seed = scenario["p1_knowledge_seed"]
        archive_id = seed["archive_id"]
        payload = self._build_payload(seed)
        self.output_root.mkdir(parents=True, exist_ok=True)
        output_path = self.output_root / f"{archive_id}-knowledge.json"
        output_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
        return {
            "archive_id": archive_id,
            "archive_name": seed["archive_name"],
            "output_path": str(output_path),
            "entity_count": len(payload["entities"]),
            "process_count": len(payload["processes"]),
            "event_count": len(payload["events"]),
        }

    def _build_payload(self, seed: dict) -> dict:
        return {
            "summary": {
                "name": seed["archive_name"],
                "entity_count": len(seed.get("entities", [])),
                "event_count": len(seed.get("events", [])),
                "process_count": len(seed.get("processes", [])),
                "relation_count": len(seed.get("relations", [])),
                "document_count": len(seed.get("documents", [])),
            },
            "publication": seed.get("publication"),
            "documents": seed.get("documents", []),
            "entities": seed.get("entities", []),
            "events": seed.get("events", []),
            "processes": seed.get("processes", []),
            "relations": seed.get("relations", []),
        }
```

- [ ] **Step 4: Add scenario materialization service methods**

Modify imports in `apps/api/app/requirement_authoring/service.py`:

```python
from app.config import settings
from app.requirement_authoring.scenario_fixtures import DEFAULT_SCENARIO_ID, get_scenario, list_scenario_summaries
from app.requirement_authoring.scenario_models import (
    RequirementAuthoringScenarioCatalog,
    RequirementAuthoringScenarioMaterialize,
    RequirementAuthoringScenarioSummary,
)
from app.requirement_authoring.scenario_projector import ScenarioP1Projector
```

Add these methods to `RequirementAuthoringService`:

```python
    def materialize_scenario(self, scenario_id: str, payload: RequirementAuthoringScenarioMaterialize) -> dict:
        self._ensure_default_templates()
        scenario = get_scenario(scenario_id)
        if scenario is None:
            raise ValueError("scenario not found")

        mock_archive = ScenarioP1Projector(settings.knowledge_output_root).materialize(scenario)
        template = self._get_template_by_code(scenario["default_template_code"])
        if template is None:
            raise ValueError("scenario template not found")

        seed = scenario["p2_authoring_seed"]
        fields = self._initial_fields()
        fields.update({key: str(value) for key, value in seed["initial_fields"].items()})
        semantic_state = self._build_semantic_state(fields, template)
        semantic_state["scenario"] = {
            "scenario_id": scenario["scenario_id"],
            "scenario_name": scenario["scenario_name"],
            "mode": "mock_rule",
            "mock_archive_id": mock_archive["archive_id"],
        }
        document = RequirementAuthoringDocument(
            title=(payload.title or seed["title"]).strip(),
            template_id=template.id,
            status="draft",
            layout_ratio=payload.layout_ratio,
            archive_ids=[mock_archive["archive_id"]],
            semantic_state=semantic_state,
            document=self._render_document(template.payload, fields),
            conversation=[
                {
                    "id": "msg-1",
                    "role": "assistant",
                    "content": scenario["conversation_seed"]["assistant_opening"],
                    "created_at": self._now(),
                }
            ],
            annotations=self._build_annotations(template.payload, fields),
            check_result=self._empty_check_result(),
            frozen_package=None,
        )
        self.session.add(document)
        self.session.commit()
        self.session.refresh(document)
        return {
            "scenario": {
                "scenario_id": scenario["scenario_id"],
                "scenario_name": scenario["scenario_name"],
                "version": scenario["version"],
            },
            "mock_archive": mock_archive,
            "document": self._serialize_document_detail(document),
        }

    def _get_template_by_code(self, template_code: str) -> RequirementAuthoringTemplate | None:
        return self.session.scalars(
            select(RequirementAuthoringTemplate).where(RequirementAuthoringTemplate.template_code == template_code)
        ).first()
```

- [ ] **Step 5: Add the materialization route**

Modify `apps/api/app/api/routes/requirement_authoring.py` imports:

```python
from app.requirement_authoring.models import (
    RequirementAuthoringClausePatch,
    RequirementAuthoringDocumentCreate,
    RequirementAuthoringFormPatch,
    RequirementAuthoringMessageWrite,
    RequirementAuthoringTemplateWrite,
)
from app.requirement_authoring.scenario_models import RequirementAuthoringScenarioMaterialize
```

Add route:

```python
@router.post("/scenarios/{scenario_id}/materialize")
def materialize_requirement_authoring_scenario(
    scenario_id: str,
    payload: RequirementAuthoringScenarioMaterialize,
    service: RequirementAuthoringService = Depends(get_requirement_authoring_service),
):
    try:
        return service.materialize_scenario(scenario_id, payload)
    except ValueError as exc:
        raise _bad_request(exc) from exc
```

- [ ] **Step 6: Run the materialization test**

Run:

```bash
uv run pytest apps/api/tests/test_requirement_authoring_scenarios.py::test_requirement_authoring_materializes_mock_p1_and_p2_document -q
```

Expected: `1 passed`.

- [ ] **Step 7: Commit Task 2**

```bash
git add apps/api/app/requirement_authoring/scenario_projector.py apps/api/app/requirement_authoring/service.py apps/api/app/api/routes/requirement_authoring.py apps/api/tests/test_requirement_authoring_scenarios.py
git commit -m "物化P2模拟场景数据"
```

## Task 3: Scenario Turns And Auto-Complete

**Files:**
- Modify: `apps/api/app/requirement_authoring/service.py`
- Modify: `apps/api/app/api/routes/requirement_authoring.py`
- Test: `apps/api/tests/test_requirement_authoring_scenarios.py`

- [ ] **Step 1: Add the failing scenario turn and auto-complete test**

Append this test:

```python
def test_requirement_authoring_scenario_turns_auto_complete_and_freeze() -> None:
    client = TestClient(create_app())
    materialized = client.post(
        "/api/requirement-authoring/scenarios/airspace-collaboration/materialize",
        json={"layout_ratio": "2:3"},
    ).json()
    document_id = materialized["document"]["document_id"]

    turn = client.post(
        f"/api/requirement-authoring/documents/{document_id}/scenario-turns",
        json={"content": "加超时", "mode": "mock_rule"},
    )
    assert turn.status_code == 200
    turn_payload = turn.json()
    assert turn_payload["brainstorming"]["field_patches"]["exception_flow"]
    assert "会签超时" in turn_payload["document"]["document"]["sections"][2]["clauses"][2]["content"]
    assert turn_payload["document"]["conversation"][-1]["role"] == "assistant"

    checked = client.post(f"/api/requirement-authoring/documents/{document_id}/check")
    assert checked.status_code == 200
    assert checked.json()["check_result"]["blocking_count"] > 0

    completed = client.post(f"/api/requirement-authoring/documents/{document_id}/auto-complete")
    assert completed.status_code == 200
    assert completed.json()["document"]["check_result"]["blocking_count"] == 0
    assert completed.json()["document"]["status"] == "ready_to_freeze"

    frozen = client.post(f"/api/requirement-authoring/documents/{document_id}/freeze")
    assert frozen.status_code == 200
    assert frozen.json()["frozen_package"]["p3_consumable"] is True
    structured_spec = frozen.json()["frozen_package"]["structured_spec"]
    assert structured_spec["application"]["name"] == "空域协同规划软件"
    assert structured_spec["processes"][0]["name"] == "协同规划与冲突处置"
    assert "会签超时" in structured_spec["rules"][0]["description"]
```

- [ ] **Step 2: Run the test to verify it fails**

Run:

```bash
uv run pytest apps/api/tests/test_requirement_authoring_scenarios.py::test_requirement_authoring_scenario_turns_auto_complete_and_freeze -q
```

Expected: FAIL with `404` because `/scenario-turns` and `/auto-complete` are not registered.

- [ ] **Step 3: Add mock-rule brainstorming response builder**

Modify `apps/api/app/requirement_authoring/service.py` imports:

```python
from app.requirement_authoring.scenario_models import (
    BrainstormingResponse,
    RequirementAuthoringScenarioCatalog,
    RequirementAuthoringScenarioMaterialize,
    RequirementAuthoringScenarioSummary,
    RequirementAuthoringScenarioTurnWrite,
)
```

Add these methods:

```python
    def apply_scenario_turn(self, document_id: str, payload: RequirementAuthoringScenarioTurnWrite) -> dict | None:
        document = self.session.get(RequirementAuthoringDocument, document_id)
        if document is None:
            return None
        if document.status == "frozen":
            raise ValueError("document is frozen")

        scenario_meta = document.semantic_state.get("scenario", {})
        scenario = get_scenario(scenario_meta.get("scenario_id", ""))
        if scenario is None:
            raise ValueError("scenario not found")
        if payload.mode != "mock_rule":
            raise ValueError("scenario turn mode is not available")

        brainstorming = self._build_mock_brainstorming_response(scenario, payload.content)
        template = self._get_document_template(document)
        fields = dict(document.semantic_state.get("fields", {}))
        fields.update(brainstorming.field_patches)
        self._write_document_state(document, template, fields)
        document.semantic_state = {**document.semantic_state, "scenario": scenario_meta}
        conversation = list(document.conversation)
        next_index = len(conversation) + 1
        conversation.extend(
            [
                {"id": f"msg-{next_index}", "role": "user", "content": payload.content.strip(), "created_at": self._now()},
                {"id": f"msg-{next_index + 1}", "role": "assistant", "content": brainstorming.assistant_message, "created_at": self._now()},
            ]
        )
        document.conversation = conversation
        document.status = "draft"
        self.session.commit()
        self.session.refresh(document)
        return {"brainstorming": brainstorming.model_dump(mode="json"), "document": self._serialize_document_detail(document)}

    def auto_complete_scenario_document(self, document_id: str) -> dict | None:
        document = self.session.get(RequirementAuthoringDocument, document_id)
        if document is None:
            return None
        if document.status == "frozen":
            raise ValueError("document is frozen")
        scenario_meta = document.semantic_state.get("scenario", {})
        scenario = get_scenario(scenario_meta.get("scenario_id", ""))
        if scenario is None:
            raise ValueError("scenario not found")

        template = self._get_document_template(document)
        fields = dict(document.semantic_state.get("fields", {}))
        fields.update(scenario["conversation_seed"]["auto_complete_fields"])
        self._write_document_state(document, template, fields)
        document.semantic_state = {**document.semantic_state, "scenario": scenario_meta}
        document.conversation = [
            *document.conversation,
            {
                "id": f"msg-{len(document.conversation) + 1}",
                "role": "assistant",
                "content": "已按当前场景补齐剩余关键字段，可以执行缺口检查并冻结版本。",
                "created_at": self._now(),
            },
        ]
        self.session.commit()
        self.session.refresh(document)
        checked = self.run_check(document.id)
        return {"document": checked}

    def _build_mock_brainstorming_response(self, scenario: dict, content: str) -> BrainstormingResponse:
        normalized = content.strip()
        rules = scenario["conversation_seed"]["field_patch_rules"]
        field_patches = rules.get(normalized)
        if field_patches is None and normalized not in {"可以", "加超时", "更正式", "补验收", "自动补齐"}:
            field_patches = {"normal_flow": normalized}
        if field_patches is None:
            field_patches = rules["可以"]
        return BrainstormingResponse(
            assistant_message=self._build_scenario_assistant_message(normalized, field_patches),
            field_patches=field_patches,
            next_questions=[
                {
                    "question_id": "q-next-gap",
                    "prompt": "继续补齐异常流程、非功能要求或验收准则？",
                    "suggested_replies": ["加超时", "补验收", "自动补齐"],
                }
            ],
            source_refs=[
                {
                    "archive_id": scenario["p1_knowledge_seed"]["archive_id"],
                    "item_id": "process-collaboration-planning",
                    "evidence_id": "ev-process-001",
                }
            ],
            confidence=0.92,
            blocking_risks=[],
        )

    def _build_scenario_assistant_message(self, content: str, field_patches: dict[str, str]) -> str:
        if "exception_flow" in field_patches:
            return "已补入会签超时和人工确认约束，保持异常补偿策略克制。"
        if "acceptance_criteria" in field_patches:
            return "已补入验收准则，重点覆盖可创建、可识别、可提醒、可追溯。"
        if content == "更正式":
            return "已把核心流程改写为更标准的需求规格表达。"
        return "已按模拟 P1 知识补入核心流程草稿，你可以继续短答。"
```

- [ ] **Step 4: Add scenario turn and auto-complete routes**

Modify `apps/api/app/api/routes/requirement_authoring.py` import:

```python
from app.requirement_authoring.scenario_models import (
    RequirementAuthoringScenarioMaterialize,
    RequirementAuthoringScenarioTurnWrite,
)
```

Add routes:

```python
@router.post("/documents/{document_id}/scenario-turns")
def append_requirement_authoring_scenario_turn(
    document_id: str,
    payload: RequirementAuthoringScenarioTurnWrite,
    service: RequirementAuthoringService = Depends(get_requirement_authoring_service),
):
    try:
        result = service.apply_scenario_turn(document_id, payload)
    except ValueError as exc:
        raise _bad_request(exc) from exc
    if result is None:
        raise _not_found("Requirement authoring document not found")
    return result


@router.post("/documents/{document_id}/auto-complete")
def auto_complete_requirement_authoring_document(
    document_id: str,
    service: RequirementAuthoringService = Depends(get_requirement_authoring_service),
):
    try:
        result = service.auto_complete_scenario_document(document_id)
    except ValueError as exc:
        raise _bad_request(exc) from exc
    if result is None:
        raise _not_found("Requirement authoring document not found")
    return result
```

- [ ] **Step 5: Run the scenario lifecycle test**

Run:

```bash
uv run pytest apps/api/tests/test_requirement_authoring_scenarios.py -q
```

Expected: all scenario tests pass.

- [ ] **Step 6: Commit Task 3**

```bash
git add apps/api/app/requirement_authoring/service.py apps/api/app/api/routes/requirement_authoring.py apps/api/tests/test_requirement_authoring_scenarios.py
git commit -m "接入P2场景问答闭环"
```

## Task 4: Frontend API Types And Workbench Scenario Controls

**Files:**
- Modify: `apps/web/src/lib/api.ts`
- Modify: `apps/web/src/lib/requirementAuthoring.ts`
- Modify: `apps/web/src/pages/RequirementAuthoringPage.tsx`
- Modify: `apps/web/src/pages/RequirementAuthoringPage.css`
- Test: `apps/web/src/test/RequirementAuthoringPage.test.tsx`

- [ ] **Step 1: Extend the frontend test with scenario controls**

Modify `apps/web/src/test/RequirementAuthoringPage.test.tsx` so the mocked GET handler includes scenarios:

```typescript
if (url === "/requirement-authoring/scenarios") {
  return Promise.resolve({
    data: {
      default_scenario_id: "airspace-collaboration",
      items: [
        {
          scenario_id: "airspace-collaboration",
          scenario_name: "空域协同规划软件",
          version: "1.0.0",
          domain: "空域协同规划",
          default_template_code: "81433",
          source_mode: "mock_p1",
          description: "围绕空域申请、冲突校核、协同会签和异常处置生成完整 P2 闭环。",
        },
      ],
    },
  });
}
```

Add POST handlers:

```typescript
if (url === "/requirement-authoring/scenarios/airspace-collaboration/materialize") {
  document = {
    ...document,
    title: "空域协同规划软件需求规格说明",
    archive_ids: ["mock-airspace-p1"],
    semantic_state: {
      ...document.semantic_state,
      scenario: { scenario_id: "airspace-collaboration", scenario_name: "空域协同规划软件", mock_archive_id: "mock-airspace-p1" },
      fields: {
        ...document.semantic_state.fields,
        application_name: "空域协同规划软件",
        domain_scope: "空域协同规划",
      },
    },
  };
  return Promise.resolve({ data: { scenario: { scenario_id: "airspace-collaboration" }, mock_archive: { archive_id: "mock-airspace-p1" }, document } });
}
if (url === "/requirement-authoring/documents/doc-1/scenario-turns") {
  document = {
    ...document,
    document: {
      ...document.document,
      sections: document.document.sections.map((section) =>
        section.section_id === "3"
          ? {
              ...section,
              clauses: section.clauses.map((clause) =>
                clause.clause_id === "REQ-3.3" ? { ...clause, content: "系统应在方案会签超时后提醒责任人。" } : clause,
              ),
            }
          : section,
      ),
    },
    conversation: [...document.conversation, { id: "msg-scenario", role: "assistant", content: "已补入会签超时和人工确认约束。" }],
  };
  return Promise.resolve({ data: { brainstorming: { field_patches: { exception_flow: "系统应在方案会签超时后提醒责任人。" } }, document } });
}
if (url === "/requirement-authoring/documents/doc-1/auto-complete") {
  document = { ...document, status: "ready_to_freeze", check_result: { blocking_count: 0, warning_count: 0, passed_count: 8, items: [] } };
  return Promise.resolve({ data: { document } });
}
```

Add expectations after rendering:

```typescript
fireEvent.click(screen.getByRole("button", { name: "设置" }));
expect(await screen.findByText("场景数据")).toBeInTheDocument();
fireEvent.click(screen.getByRole("button", { name: "生成模拟闭环" }));
expect(await screen.findByText("模拟 P1 知识源")).toBeInTheDocument();
expect(await screen.findByText("mock-airspace-p1")).toBeInTheDocument();

fireEvent.change(input, { target: { value: "加超时" } });
fireEvent.click(screen.getByRole("button", { name: "发送" }));
expect(await screen.findByText("系统应在方案会签超时后提醒责任人。")).toBeInTheDocument();

fireEvent.click(screen.getByRole("button", { name: "自动补齐" }));
expect(await screen.findByText("阻断项 0")).toBeInTheDocument();
```

- [ ] **Step 2: Run the frontend test to verify it fails**

Run:

```bash
corepack pnpm --dir apps/web test src/test/RequirementAuthoringPage.test.tsx
```

Expected: FAIL because scenario API helpers and UI controls do not exist.

- [ ] **Step 3: Add frontend scenario types**

Modify `apps/web/src/lib/api.ts` after requirement authoring document types:

```typescript
export type RequirementAuthoringScenarioSummary = {
  scenario_id: string;
  scenario_name: string;
  version: string;
  domain: string;
  default_template_code: string;
  source_mode: "mock_p1" | "live_p1";
  description: string;
};

export type RequirementAuthoringScenarioCatalog = {
  default_scenario_id: string;
  items: RequirementAuthoringScenarioSummary[];
};

export type RequirementAuthoringScenarioMaterializeInput = {
  layout_ratio?: RequirementAuthoringLayoutRatio;
  title?: string | null;
};

export type RequirementAuthoringScenarioMaterializeResult = {
  scenario: { scenario_id: string; scenario_name?: string; version?: string };
  mock_archive: { archive_id: string; archive_name?: string; output_path?: string };
  document: RequirementAuthoringDocumentDetail;
};

export type RequirementAuthoringScenarioTurnResult = {
  brainstorming: {
    assistant_message?: string;
    field_patches?: Record<string, string>;
    confidence?: number;
  };
  document: RequirementAuthoringDocumentDetail;
};

export type RequirementAuthoringAutoCompleteResult = {
  document: RequirementAuthoringDocumentDetail;
};
```

- [ ] **Step 4: Add frontend API helpers**

Modify `apps/web/src/lib/requirementAuthoring.ts` imports and add functions:

```typescript
import type {
  RequirementAuthoringAutoCompleteResult,
  RequirementAuthoringDocumentCreateInput,
  RequirementAuthoringDocumentDetail,
  RequirementAuthoringDocumentSummary,
  RequirementAuthoringScenarioCatalog,
  RequirementAuthoringScenarioMaterializeInput,
  RequirementAuthoringScenarioMaterializeResult,
  RequirementAuthoringScenarioTurnResult,
  RequirementAuthoringTemplate,
  RequirementAuthoringTemplateWriteInput,
} from "./api";

export function getRequirementAuthoringScenarios() {
  return api.get<RequirementAuthoringScenarioCatalog>("/requirement-authoring/scenarios");
}

export function materializeRequirementAuthoringScenario(
  scenarioId: string,
  payload: RequirementAuthoringScenarioMaterializeInput,
) {
  return api.post<RequirementAuthoringScenarioMaterializeResult>(
    `/requirement-authoring/scenarios/${scenarioId}/materialize`,
    payload,
  );
}

export function appendRequirementAuthoringScenarioTurn(documentId: string, content: string) {
  return api.post<RequirementAuthoringScenarioTurnResult>(`/requirement-authoring/documents/${documentId}/scenario-turns`, {
    content,
    mode: "mock_rule",
  });
}

export function autoCompleteRequirementAuthoringDocument(documentId: string) {
  return api.post<RequirementAuthoringAutoCompleteResult>(`/requirement-authoring/documents/${documentId}/auto-complete`);
}
```

- [ ] **Step 5: Add scenario state and behavior to the workbench**

Modify `apps/web/src/pages/RequirementAuthoringPage.tsx` imports:

```typescript
import type {
  RequirementAuthoringAnnotation,
  RequirementAuthoringDocumentDetail,
  RequirementAuthoringLayoutRatio,
  RequirementAuthoringScenarioSummary,
  RequirementAuthoringTemplate,
  RequirementAuthoringTemplateField,
} from "../lib/api";
import {
  appendRequirementAuthoringMessage,
  appendRequirementAuthoringScenarioTurn,
  autoCompleteRequirementAuthoringDocument,
  createRequirementAuthoringDocument,
  freezeRequirementAuthoringDocument,
  getRequirementAuthoringDocuments,
  getRequirementAuthoringScenarios,
  getRequirementAuthoringTemplates,
  materializeRequirementAuthoringScenario,
  patchRequirementAuthoringFormFields,
  runRequirementAuthoringCheck,
} from "../lib/requirementAuthoring";
```

Add state:

```typescript
const [scenarios, setScenarios] = useState<RequirementAuthoringScenarioSummary[]>([]);
const [selectedScenarioId, setSelectedScenarioId] = useState<string | null>(null);
```

Update load Promise:

```typescript
const [templatesResponse, documentsResponse, scenariosResponse] = await Promise.all([
  getRequirementAuthoringTemplates(),
  getRequirementAuthoringDocuments(),
  getRequirementAuthoringScenarios(),
]);
setScenarios(scenariosResponse.data.items);
setSelectedScenarioId(scenariosResponse.data.default_scenario_id);
```

Add helpers:

```typescript
const currentScenarioMeta = currentDocument?.semantic_state.scenario as
  | { scenario_id?: string; scenario_name?: string; mock_archive_id?: string }
  | undefined;

async function handleMaterializeScenario() {
  if (!selectedScenarioId) {
    return;
  }
  try {
    setSubmitting(true);
    const response = await materializeRequirementAuthoringScenario(selectedScenarioId, { layout_ratio: ratio });
    setCurrentDocument(response.data.document);
    setRatio(response.data.document.layout_ratio);
    setError(null);
  } catch (scenarioError) {
    setError(scenarioError instanceof Error ? scenarioError.message : "生成模拟场景失败");
  } finally {
    setSubmitting(false);
  }
}

async function handleAutoComplete() {
  if (!currentDocument) {
    return;
  }
  try {
    setSubmitting(true);
    const response = await autoCompleteRequirementAuthoringDocument(currentDocument.document_id);
    setCurrentDocument(response.data.document);
    setError(null);
  } catch (autoCompleteError) {
    setError(autoCompleteError instanceof Error ? autoCompleteError.message : "自动补齐失败");
  } finally {
    setSubmitting(false);
  }
}
```

Update `handleSend`:

```typescript
const response = currentDocument.semantic_state.scenario
  ? await appendRequirementAuthoringScenarioTurn(currentDocument.document_id, normalized)
  : await appendRequirementAuthoringMessage(currentDocument.document_id, normalized);
setCurrentDocument("document" in response.data ? response.data.document : response.data);
```

Add scenario controls to `settingsContent`:

```tsx
<Text strong>场景数据</Text>
<Segmented
  block
  value={selectedScenarioId ?? undefined}
  options={scenarios.map((item) => ({ label: item.scenario_name, value: item.scenario_id }))}
  onChange={(value) => setSelectedScenarioId(String(value))}
/>
<Button block loading={submitting} disabled={!selectedScenarioId} onClick={() => void handleMaterializeScenario()}>
  生成模拟闭环
</Button>
```

Add an action button near check/freeze:

```tsx
<Button disabled={!currentDocument?.semantic_state.scenario} loading={submitting} onClick={() => void handleAutoComplete()}>
  自动补齐
</Button>
```

Add source marker near alerts:

```tsx
{currentScenarioMeta?.mock_archive_id ? (
  <Alert
    type="info"
    showIcon
    className="requirement-authoring-scenario-source"
    message="模拟 P1 知识源"
    description={currentScenarioMeta.mock_archive_id}
  />
) : null}
```

- [ ] **Step 6: Add minimal scenario styles**

Modify `apps/web/src/pages/RequirementAuthoringPage.css`:

```css
.requirement-authoring-scenario-source {
  margin-bottom: 12px;
}
```

- [ ] **Step 7: Run the frontend targeted test**

Run:

```bash
corepack pnpm --dir apps/web test src/test/RequirementAuthoringPage.test.tsx
```

Expected: `1 passed`.

- [ ] **Step 8: Commit Task 4**

```bash
git add apps/web/src/lib/api.ts apps/web/src/lib/requirementAuthoring.ts apps/web/src/pages/RequirementAuthoringPage.tsx apps/web/src/pages/RequirementAuthoringPage.css apps/web/src/test/RequirementAuthoringPage.test.tsx
git commit -m "接入P2场景发生器前端入口"
```

## Task 5: Full Verification And Acceptance Guardrails

**Files:**
- Modify only if tests expose integration issues in files touched by Tasks 1-4.

- [ ] **Step 1: Run full backend tests**

Run:

```bash
uv run pytest apps/api/tests -q
```

Expected: all backend tests pass. At current baseline this means `162+` tests pass; the exact count will increase after adding scenario tests.

- [ ] **Step 2: Run full frontend tests**

Run:

```bash
corepack pnpm --dir apps/web test
```

Expected: all frontend tests pass. At current baseline this means `32+` test files pass and `79+` tests pass, with the existing skipped tests unchanged.

- [ ] **Step 3: Run frontend production build**

Run:

```bash
corepack pnpm --dir apps/web build
```

Expected: build exits 0. Existing Vite CJS and chunk-size warnings may remain.

- [ ] **Step 4: Manual browser acceptance**

Run services if they are not already running:

```bash
uv run uvicorn app.main:app --app-dir apps/api --host 127.0.0.1 --port 8020
VITE_WEB_PORT=5174 VITE_API_PROXY_TARGET=http://127.0.0.1:8020 corepack pnpm --dir apps/web dev --host 127.0.0.1 --port 5174
```

Open:

```text
http://127.0.0.1:5174/requirement-authoring
```

Acceptance path:

1. Click `设置`.
2. Choose `空域协同规划软件`.
3. Click `生成模拟闭环`.
4. Confirm the page shows `模拟 P1 知识源` and `mock-airspace-p1`.
5. Enter `加超时` in question mode and send.
6. Confirm the right document contains `会签超时`.
7. Click `自动补齐`.
8. Click `缺口检查`.
9. Confirm `阻断项 0`.
10. Click `冻结版本`.
11. Confirm `P3 可消费`.

- [ ] **Step 5: Commit verification fixes if needed**

If any implementation fixes were required during verification:

```bash
git add apps/api/app/requirement_authoring/scenario_models.py apps/api/app/requirement_authoring/scenario_fixtures.py apps/api/app/requirement_authoring/scenario_projector.py apps/api/app/requirement_authoring/service.py apps/api/app/api/routes/requirement_authoring.py apps/api/tests/test_requirement_authoring_scenarios.py apps/web/src/lib/api.ts apps/web/src/lib/requirementAuthoring.ts apps/web/src/pages/RequirementAuthoringPage.tsx apps/web/src/pages/RequirementAuthoringPage.css apps/web/src/test/RequirementAuthoringPage.test.tsx
git commit -m "修正P2场景发生器验收问题"
```

If no files changed, skip this commit step.

## Self-Review

Spec coverage:

- Scenario pack registry is covered by Task 1.
- Mock P1 published knowledge is covered by Task 2.
- P2 authoring document materialization is covered by Task 2.
- Mock-rule brainstorming contract and scenario turns are covered by Task 3.
- Auto-complete, gap check, and freeze are covered by Task 3.
- Frontend scenario control in the existing P2 workbench is covered by Task 4.
- Full P2 closed-loop acceptance is covered by Task 5.
- Real LLM invocation is intentionally outside the first implementation batch; the response contract and `mock_rule` path are implemented now so `llm_assisted` can replace only the decision engine in a later spec.

Type consistency:

- Backend route payloads use `RequirementAuthoringScenarioMaterialize` and `RequirementAuthoringScenarioTurnWrite`.
- Backend structured output uses `BrainstormingResponse`.
- Frontend scenario materialization response uses `RequirementAuthoringScenarioMaterializeResult`.
- Frontend scenario turn response uses `RequirementAuthoringScenarioTurnResult`.

Execution notes:

- Keep the current P2 worktree. Do not remove it after implementation unless the user explicitly approves removal.
- Do not touch unrelated `DOC/CODEX_DOC` work in the main worktree.
- If full merge to `main` is requested later and main has dirty docs, preserve those changes and use a non-destructive integration strategy.
