# Community 3

> 26 nodes · cohesion 0.14

## Key Concepts

- **DocumentService** (12 connections) — `apps/api/app/documents/service.py`
- **Base** (10 connections) — `apps/api/app/db/base.py`
- **Base** (9 connections)
- **GovernanceService** (9 connections) — `apps/api/app/governance/service.py`
- **DocumentSegment** (5 connections) — `apps/api/app/db/models/document.py`
- **DocumentVersion** (5 connections) — `apps/api/app/db/models/document.py`
- **ParseRun** (5 connections) — `apps/api/app/db/models/document.py`
- **KnowledgeItem** (5 connections) — `apps/api/app/db/models/knowledge.py`
- **KnowledgeVersion** (5 connections) — `apps/api/app/db/models/knowledge.py`
- **document.py** (4 connections) — `apps/api/app/db/models/document.py`
- **Document** (4 connections) — `apps/api/app/db/models/document.py`
- **AuditLog** (4 connections) — `apps/api/app/db/models/knowledge.py`
- **CandidateItem** (4 connections) — `apps/api/app/db/models/knowledge.py`
- **.get_document_detail()** (3 connections) — `apps/api/app/documents/service.py`
- **._serialize_document_summary()** (3 connections) — `apps/api/app/documents/service.py`
- **._serialize_version_detail()** (3 connections) — `apps/api/app/documents/service.py`
- **.list_documents()** (2 connections) — `apps/api/app/documents/service.py`
- **._serialize_parse_run()** (2 connections) — `apps/api/app/documents/service.py`
- **DeclarativeBase** (1 connections)
- **.__init__()** (1 connections) — `apps/api/app/documents/service.py`
- **.upload()** (1 connections) — `apps/api/app/documents/service.py`
- **.approve()** (1 connections) — `apps/api/app/governance/service.py`
- **.__init__()** (1 connections) — `apps/api/app/governance/service.py`
- **.list_published_items()** (1 connections) — `apps/api/app/governance/service.py`
- **.publish()** (1 connections) — `apps/api/app/governance/service.py`
- *... and 1 more nodes in this community*

## Relationships

- No strong cross-community connections detected

## Source Files

- `apps/api/app/db/base.py`
- `apps/api/app/db/models/document.py`
- `apps/api/app/db/models/knowledge.py`
- `apps/api/app/documents/service.py`
- `apps/api/app/governance/service.py`

## Audit Trail

- EXTRACTED: 66 (65%)
- INFERRED: 36 (35%)
- AMBIGUOUS: 0 (0%)

---

*Part of the graphify knowledge wiki. See [[index]] to navigate.*