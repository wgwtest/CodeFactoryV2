# P3 Design Lab v2 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build the first usable `/p3-design-lab` slice that consumes only P2 authoring frozen packages and produces a software design document, design baseline, and P4 workorder projection preview.

**Architecture:** Add a new `software_design_v2` backend module and `/api/software-design-v2/*` router, separate from the old P3 order service. Add a React page at `/p3-design-lab` that follows the approved three-zone layout: left-top frozen requirements document, left-bottom CLI/configuration, right-side software design output.

**Tech Stack:** FastAPI, SQLAlchemy JSON columns, Pydantic, pytest, React 18, Ant Design 5, Vitest, Testing Library, Playwright screenshots.

---

### Task 1: Backend Software Design v2 API

**Files:**
- Create: `apps/api/tests/test_software_design_v2_api.py`
- Create: `apps/api/app/software_design_v2/models.py`
- Create: `apps/api/app/software_design_v2/service.py`
- Create: `apps/api/app/api/routes/software_design_v2.py`
- Modify: `apps/api/app/main.py`

- [ ] **Step 1: Write failing API tests for P2 frozen package input, session generation, turn, and check.**
- [ ] **Step 2: Run `uv run pytest apps/api/tests/test_software_design_v2_api.py -q` and verify the route is missing.**
- [ ] **Step 3: Implement the new v2 service and router without reading old `/requirements/specs`.**
- [ ] **Step 4: Run the backend test and verify it passes.**

### Task 2: Frontend P3 Design Lab

**Files:**
- Create: `apps/web/src/test/P3DesignLabPage.test.tsx`
- Create: `apps/web/src/lib/softwareDesignV2.ts`
- Modify: `apps/web/src/lib/api.ts`
- Create: `apps/web/src/pages/P3DesignLabPage.tsx`
- Create: `apps/web/src/pages/P3DesignLabPage.css`
- Modify: `apps/web/src/App.tsx`

- [ ] **Step 1: Write failing page test for `/p3-design-lab` layout and API flow.**
- [ ] **Step 2: Run the Vitest file and verify the page route is missing.**
- [ ] **Step 3: Implement the API client, route, page, and CSS.**
- [ ] **Step 4: Run the frontend test and verify it passes.**

### Task 3: Verification And Screenshot Self-Check

**Files:**
- No code files unless verification reveals a defect.

- [ ] **Step 1: Run backend and frontend focused tests.**
- [ ] **Step 2: Start isolated P3 worktree API and web ports.**
- [ ] **Step 3: Capture `/p3-design-lab` screenshot at 1920x1080.**
- [ ] **Step 4: Inspect screenshot for blank panels, overlap, unreadable text, and incorrect layout.**

