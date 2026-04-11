# Archive Document Drilldown Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add searchable archive documents plus a right-side drilldown drawer that shows document-scoped knowledge items and evidence.

**Architecture:** Extend the existing archive JSON service with one document-detail endpoint that aggregates only the knowledge items linked to a single document. Keep document search on the current React page as client-side filtering, and reuse the existing Ant Design table/drawer patterns already used in the graph explorer.

**Tech Stack:** FastAPI, pytest, React 18, TypeScript, Ant Design, Vitest

---

## File Structure

- Modify: `apps/api/app/archive_knowledge/service.py` - add document detail aggregation.
- Modify: `apps/api/app/api/routes/knowledge.py` - expose the document detail route.
- Modify: `apps/api/tests/test_archive_knowledge_api.py` - cover the new API contract and 404 case.
- Modify: `apps/web/src/lib/api.ts` - add document detail types.
- Modify: `apps/web/src/pages/DocumentsPage.tsx` - add search, clickable title, drawer, and grouped knowledge display.
- Modify: `apps/web/src/test/DocumentsPage.test.tsx` - cover search and drawer behavior.
