# Phase-One Rebaseline Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Rebaseline phase one into serial, decoupled `P1.1-P1.5` execution packages so the knowledge-warehouse foundation can evolve module-by-module without downstream rework when implementation technologies change.

**Architecture:** Keep phase one as a modular monolith by default, but define every module boundary with microservice-style contracts. Each node consumes only the previous node's versioned outputs, APIs, and validation projections. Internal parser, extractor, storage, and graph technologies remain replaceable as long as published contracts stay compatible.

**Tech Stack:** FastAPI, SQLAlchemy, PostgreSQL, React, Vite, Ant Design, TanStack Query, Playwright, Docling, Unstructured, LibreOffice headless, PyMuPDF, python-docx, schema-constrained extraction, Neo4j, Neo4j Bloom, versioned JSON exports

---

## Scope

This plan does not replace the detailed step-by-step implementation notes in [2026-04-11-knowledge-warehouse-foundation.md](/home/wgw/CodexProject/CodeFactoryV2/docs/superpowers/plans/2026-04-11-knowledge-warehouse-foundation.md). It rebases execution order, module boundaries, and acceptance packages so delivery aligns with the revised phase-one structure in [2026-04-11-software-factory-platform-design.md](/home/wgw/CodexProject/CodeFactoryV2/docs/superpowers/specs/2026-04-11-software-factory-platform-design.md).

## File Structure

### Planning and Governance

- Create: `docs/superpowers/plans/2026-04-12-phase-one-rebaseline.md` - phase-one execution rebaseline.
- Modify: `docs/superpowers/specs/2026-04-11-software-factory-platform-design.md` - source-of-truth phase-one structure and constraints.

### Backend Modules

- Modify: `apps/api/app/config.py` - versioned contract flags and storage backends.
- Modify: `apps/api/app/main.py` - module registration order aligned to `P1.1-P1.5`.
- Modify: `apps/api/app/api/routes/documents.py` - document intake and parse status APIs.
- Modify: `apps/api/app/api/routes/governance.py` - candidate governance and publish APIs.
- Modify: `apps/api/app/api/routes/knowledge.py` - published knowledge query APIs.
- Modify: `apps/api/app/documents/` - document intake and archival module.
- Modify: `apps/api/app/parsing/` - parsing adapters and parse-run projections.
- Modify: `apps/api/app/extraction/` - schema-driven candidate extraction module.
- Modify: `apps/api/app/governance/` - review, merge, publish, and audit workflow module.
- Modify: `apps/api/app/archive_knowledge/` - published knowledge query and detail module.
- Create or modify: `apps/api/app/integrations/neo4j/` - published graph storage adapter.

### Web Validation Platform

- Modify: `apps/web/src/App.tsx` - stage-one validation shell.
- Modify: `apps/web/src/lib/api.ts` - typed contracts for stage-one modules.
- Modify: `apps/web/src/lib/query-client.ts` - query defaults and invalidation policy.
- Modify: `apps/web/src/components/` - shared validation drawer, evidence viewer, and status panels.
- Modify: `apps/web/src/pages/DocumentsPage.tsx` - `P1.2` validation projection.
- Modify: `apps/web/src/pages/GovernancePage.tsx` - `P1.3-P1.4` validation projection.
- Modify: `apps/web/src/pages/KnowledgeGraphPage.tsx` - `P1.5` validation projection.
- Modify: `apps/web/src/pages/ProcessViewPage.tsx` - `P1.5` flow projection.

### Tests

- Modify: `apps/api/tests/` - stage-node contract tests.
- Modify: `apps/web/src/test/` - validation-platform interaction tests.
- Modify: `apps/web/e2e/knowledge-review.spec.ts` - top-level smoke scenario aligned to `P1.1-P1.5`.

## Task P1.1: Build the Validation Platform Foundation

**Files:**
- Modify: `apps/web/src/App.tsx`
- Modify: `apps/web/src/lib/api.ts`
- Modify: `apps/web/src/lib/query-client.ts`
- Modify: `apps/web/src/components/DocumentUploadForm.tsx`
- Modify: `apps/web/src/components/CandidateReviewTable.tsx`
- Modify: `apps/web/src/components/KnowledgeGraph.tsx`
- Modify: `apps/web/src/components/ProcessFlow.tsx`
- Modify: `apps/web/src/test/DocumentsPage.test.tsx`
- Modify: `apps/web/src/test/GovernancePage.test.tsx`
- Modify: `apps/web/e2e/knowledge-review.spec.ts`

- [ ] Define shared validation-shell rules: route names, common detail drawer, shared error/status states, and evidence viewer contract.
- [ ] Refactor web entrypoints so later nodes only add module-specific panels instead of inventing new page shells.
- [ ] Add smoke coverage proving the shell can host document, governance, graph, and process views without coupling their internals.
- [ ] Run `corepack pnpm --dir apps/web test -- --run DocumentsPage.test.tsx GovernancePage.test.tsx`
- [ ] Run `corepack pnpm --dir apps/web exec playwright test`
- [ ] Commit with `git commit -m "plan: align p1.1 validation platform foundation"`

## Task P1.2: Stabilize Document Intake and Structured Parsing

**Files:**
- Modify: `apps/api/app/documents/service.py`
- Modify: `apps/api/app/documents/storage.py`
- Modify: `apps/api/app/parsing/service.py`
- Modify: `apps/api/app/parsing/parsers/docx_parser.py`
- Modify: `apps/api/app/parsing/parsers/pdf_parser.py`
- Modify: `apps/api/app/parsing/parsers/doc_converter.py`
- Modify: `apps/api/app/api/routes/documents.py`
- Modify: `apps/web/src/pages/DocumentsPage.tsx`
- Modify: `apps/api/tests/test_document_upload.py`
- Modify: `apps/api/tests/test_parsing_service.py`

- [ ] Introduce a parser-adapter boundary so `Docling`, `Unstructured`, and current fallbacks can be swapped without changing downstream extractors.
- [ ] Persist parse runs, parse status, structural blocks, anchors, and parser metadata as the only published outputs of `P1.2`.
- [ ] Expose document-page validation views for raw file metadata, parse batches, block previews, and failure causes.
- [ ] Run `uv run pytest apps/api/tests/test_document_upload.py apps/api/tests/test_parsing_service.py -q`
- [ ] Run `corepack pnpm --dir apps/web test -- --run DocumentsPage.test.tsx`
- [ ] Commit with `git commit -m "plan: align p1.2 document intake and parsing"`

## Task P1.3: Implement Schema-Constrained Candidate Extraction

**Files:**
- Modify: `apps/api/app/extraction/service.py`
- Modify: `apps/api/app/extraction/rules.py`
- Modify: `apps/api/app/db/models/knowledge.py`
- Create or modify: `apps/api/app/extraction/schema.py`
- Modify: `apps/api/app/api/routes/governance.py`
- Modify: `apps/web/src/pages/GovernancePage.tsx`
- Modify: `apps/api/tests/test_extraction_service.py`
- Modify: `apps/web/src/test/GovernancePage.test.tsx`

- [ ] Define the phase-one extraction schema for entities, relations, processes, rules, metrics, evidence refs, and extraction-run metadata.
- [ ] Rework extraction so downstream governance consumes only schema-normalized candidate sets, not parser-specific intermediate structures.
- [ ] Add validation views for candidate counts, evidence anchors, confidence, extraction batch metadata, and missing-relation review.
- [ ] Run `uv run pytest apps/api/tests/test_extraction_service.py -q`
- [ ] Run `corepack pnpm --dir apps/web test -- --run GovernancePage.test.tsx`
- [ ] Commit with `git commit -m "plan: align p1.3 candidate extraction contracts"`

## Task P1.4: Separate Governance and Publish Workflows

**Files:**
- Modify: `apps/api/app/governance/service.py`
- Modify: `apps/api/app/api/routes/governance.py`
- Modify: `apps/api/app/audit/service.py`
- Modify: `apps/api/app/db/models/knowledge.py`
- Modify: `apps/web/src/pages/GovernancePage.tsx`
- Modify: `apps/api/tests/test_governance_publish.py`
- Modify: `apps/api/tests/test_auth_audit.py`

- [ ] Make governance outputs explicit: reviewed candidates, merge decisions, publish snapshots, audit events, and version labels.
- [ ] Ensure `P1.4` depends only on normalized candidate outputs from `P1.3`, not on parser or extraction implementation details.
- [ ] Expose validation views for review state transitions, merge history, publish versions, and audit trails.
- [ ] Run `uv run pytest apps/api/tests/test_governance_publish.py apps/api/tests/test_auth_audit.py -q`
- [ ] Run `corepack pnpm --dir apps/web test -- --run GovernancePage.test.tsx`
- [ ] Commit with `git commit -m "plan: align p1.4 governance and publish workflow"`

## Task P1.5: Build the Published Knowledge Store, Query, and Graph Views

**Files:**
- Modify: `apps/api/app/archive_knowledge/service.py`
- Modify: `apps/api/app/api/routes/knowledge.py`
- Create or modify: `apps/api/app/integrations/neo4j/client.py`
- Create or modify: `apps/api/app/integrations/neo4j/repository.py`
- Modify: `apps/web/src/pages/KnowledgeGraphPage.tsx`
- Modify: `apps/web/src/pages/ProcessViewPage.tsx`
- Modify: `apps/web/src/components/KnowledgeGraph.tsx`
- Modify: `apps/web/src/components/ProcessFlow.tsx`
- Modify: `apps/api/tests/test_query_service.py`
- Modify: `apps/web/src/test/KnowledgeGraphPage.test.tsx`
- Modify: `apps/web/src/test/ProcessViewPage.test.tsx`

- [ ] Introduce a published-knowledge repository boundary so the system can switch between JSON exports, PostgreSQL projections, and Neo4j-backed graph storage without changing callers.
- [ ] Make published graph/query APIs consume only `P1.4` publish snapshots and versioned knowledge contracts.
- [ ] Expose validation views that answer the core user questions: what it is, who produced it, what it contains, what it relates to, and what evidence supports it.
- [ ] Run `uv run pytest apps/api/tests/test_query_service.py -q`
- [ ] Run `corepack pnpm --dir apps/web test -- --run KnowledgeGraphPage.test.tsx ProcessViewPage.test.tsx`
- [ ] Run `curl -s http://127.0.0.1:8000/api/knowledge/archive/20161116-nas/summary`
- [ ] Commit with `git commit -m "plan: align p1.5 published knowledge store and graph"`

## Task P1.WBS: Sync GitHub Project and Issues

**Files:**
- Modify: GitHub issue `#2`
- Modify: GitHub issue `#3`
- Modify: GitHub issue `#4`
- Modify: GitHub issue `#5`
- Create: GitHub issue `P1.4`
- Create: GitHub issue `P1.5`
- Modify: GitHub Project `CodeFactoryV2 Delivery Roadmap`

- [ ] Rename and rewrite P1 child issues so they exactly match `P1.1-P1.5`.
- [ ] Update the P1 parent issue to reflect serial execution, decoupled contracts, and module-replacement constraints.
- [ ] Ensure all issues describe node outputs, validation projections, and accepted technology choices from the revised spec.
- [ ] Confirm the GitHub Project contains the updated P1 issue set and no stale P1 child titles remain.
- [ ] Commit local documentation changes with `git commit -m "docs: rebaseline p1 implementation plan"`

## Self-Review

- [ ] Confirm every `P1.1-P1.5` node has matching scope in the revised spec and at least one implementation task here.
- [ ] Confirm every downstream node depends only on previous-node outputs, not private implementation details.
- [ ] Confirm GitHub issue structure matches the same numbering and wording as the spec.
