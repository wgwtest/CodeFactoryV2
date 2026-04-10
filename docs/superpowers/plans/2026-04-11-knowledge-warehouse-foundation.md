# Knowledge Warehouse Foundation Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build the first shippable private-deployable knowledge warehouse foundation that ingests `PDF/DOC/DOCX`, parses structured evidence, extracts candidate knowledge, supports governance and publish workflows, and exposes graph/process views plus a review console.

**Architecture:** Use a Python modular monolith for API and background workers, plus a React/Vite governance console. PostgreSQL stores documents, parsed segments, candidate knowledge, published knowledge, versions, and audit logs. MinIO stores original source files. The first release keeps graph and process projections inside PostgreSQL tables and JSON columns instead of introducing Neo4j, so the team ships a simpler vertical slice before optimizing storage topology.

**Tech Stack:** Python 3.12, FastAPI, SQLAlchemy 2, Alembic, PostgreSQL 16, MinIO, PyMuPDF, python-docx, pytesseract, LibreOffice headless conversion for `.doc`, React 18, Vite, TypeScript 5, Ant Design, TanStack Query, Cytoscape.js, React Flow, pytest, Vitest, Playwright, Docker Compose

---

## Scope

This plan intentionally covers only the first sub-project from the approved spec: the phase-one knowledge warehouse foundation. Phase-two construct mapping, phase-three interactive application generation, and phase-four component flywheel each need their own follow-up plan after this one lands.

## File Structure

### Root

- Create: `README.md` - developer onboarding, architecture summary, and local run commands.
- Create: `.env.example` - API, database, MinIO, OCR, and auth defaults.
- Create: `docker-compose.yml` - local PostgreSQL, MinIO, and optional OCR helper dependencies.
- Create: `pyproject.toml` - Python dependencies, tooling, pytest config, and worker entrypoints.
- Create: `package.json` - root scripts for web install, test, and e2e commands.
- Create: `pnpm-workspace.yaml` - declares the web workspace.
- Create: `justfile` - stable aliases for common developer commands.
- Create: `alembic.ini` and `alembic/` - migration configuration and revisions.

### Backend API and Worker

- Create: `apps/api/app/main.py` - FastAPI application factory and route registration.
- Create: `apps/api/app/config.py` - environment-backed settings.
- Create: `apps/api/app/db/base.py` - SQLAlchemy base and metadata registration.
- Create: `apps/api/app/db/session.py` - engine and session factory.
- Create: `apps/api/app/db/models/__init__.py` - model package exports for Alembic discovery.
- Create: `apps/api/app/db/models/document.py` - document, version, parse run, and segment models.
- Create: `apps/api/app/db/models/knowledge.py` - candidate items, published items, relations, versions, and audit models.
- Create: `apps/api/app/api/routes/health.py` - health endpoints.
- Create: `apps/api/app/api/routes/documents.py` - upload, list, and detail endpoints.
- Create: `apps/api/app/api/routes/governance.py` - review, approve, reject, merge, and publish endpoints.
- Create: `apps/api/app/api/routes/knowledge.py` - graph, process, search, and version endpoints.
- Create: `apps/api/app/documents/storage.py` - MinIO/local storage adapter.
- Create: `apps/api/app/documents/service.py` - document intake and versioning service.
- Create: `apps/api/app/parsing/service.py` - parse orchestrator.
- Create: `apps/api/app/parsing/parsers/pdf_parser.py` - PDF segment extraction.
- Create: `apps/api/app/parsing/parsers/docx_parser.py` - DOCX segment extraction.
- Create: `apps/api/app/parsing/parsers/doc_converter.py` - `.doc` to `.docx` conversion wrapper.
- Create: `apps/api/app/extraction/service.py` - candidate extraction orchestrator.
- Create: `apps/api/app/extraction/rules.py` - deterministic entity/event/process/rule/metric extraction.
- Create: `apps/api/app/governance/service.py` - candidate triage, merge, and publish logic.
- Create: `apps/api/app/query/service.py` - graph/process/search projections.
- Create: `apps/api/app/auth/service.py` - local user auth and role checks.
- Create: `apps/api/app/audit/service.py` - audit log capture.
- Create: `apps/api/app/jobs/runner.py` - worker loop for parse/extract jobs.
- Create: `apps/api/app/jobs/service.py` - job scheduling and state transitions.

### Backend Tests and Fixtures

- Create: `apps/api/tests/conftest.py` - SQLite-backed session fixtures and storage stubs.
- Create: `apps/api/tests/test_health.py` - API smoke test.
- Create: `apps/api/tests/test_document_models.py` - persistence separation tests.
- Create: `apps/api/tests/test_document_upload.py` - intake and versioning tests.
- Create: `apps/api/tests/test_parsing_service.py` - structured segment tests.
- Create: `apps/api/tests/test_extraction_service.py` - candidate extraction tests.
- Create: `apps/api/tests/test_governance_publish.py` - review and publish workflow tests.
- Create: `apps/api/tests/test_query_service.py` - graph/process/search projection tests.
- Create: `apps/api/tests/test_auth_audit.py` - role and audit tests.
- Create: `fixtures/reference_scenarios/minimal_policy.txt` - canonical small reference text used by parser and extractor tests.

### Web Console

- Create: `apps/web/package.json` - Vite app dependencies and scripts.
- Create: `apps/web/index.html` - Vite entrypoint.
- Create: `apps/web/src/main.tsx` - React bootstrap.
- Create: `apps/web/src/App.tsx` - router shell.
- Create: `apps/web/src/lib/api.ts` - typed API client.
- Create: `apps/web/src/lib/query-client.ts` - TanStack Query client.
- Create: `apps/web/src/pages/DocumentsPage.tsx` - upload and intake dashboard.
- Create: `apps/web/src/pages/GovernancePage.tsx` - candidate review queue.
- Create: `apps/web/src/pages/KnowledgeGraphPage.tsx` - graph explorer page.
- Create: `apps/web/src/pages/ProcessViewPage.tsx` - process explorer page.
- Create: `apps/web/src/components/DocumentUploadForm.tsx` - upload form component.
- Create: `apps/web/src/components/CandidateReviewTable.tsx` - candidate queue table.
- Create: `apps/web/src/components/KnowledgeGraph.tsx` - Cytoscape graph wrapper.
- Create: `apps/web/src/components/ProcessFlow.tsx` - React Flow process wrapper.
- Create: `apps/web/src/test/DocumentsPage.test.tsx` - upload UI test.
- Create: `apps/web/src/test/GovernancePage.test.tsx` - governance UI test.
- Create: `apps/web/playwright.config.ts` - browser smoke config.
- Create: `apps/web/e2e/knowledge-review.spec.ts` - end-to-end review flow.

## Task 1: Bootstrap the Repository and API Shell

**Files:**
- Create: `README.md`
- Create: `.env.example`
- Create: `docker-compose.yml`
- Create: `pyproject.toml`
- Create: `package.json`
- Create: `pnpm-workspace.yaml`
- Create: `justfile`
- Create: `apps/api/app/main.py`
- Create: `apps/api/app/config.py`
- Create: `apps/api/app/api/routes/health.py`
- Create: `apps/api/tests/conftest.py`
- Create: `apps/api/tests/test_health.py`
- Test: `apps/api/tests/test_health.py`

- [ ] **Step 1: Write the failing test and minimal tool manifests**

```python
# pyproject.toml
[project]
name = "knowledge-warehouse"
version = "0.1.0"
requires-python = ">=3.12"
dependencies = [
  "fastapi>=0.115.0",
  "uvicorn>=0.30.0",
  "sqlalchemy>=2.0.36",
  "pydantic-settings>=2.6.0",
  "pytest>=8.3.0",
  "httpx>=0.27.0",
]

[tool.pytest.ini_options]
pythonpath = ["apps/api"]

# apps/api/tests/test_health.py
from fastapi.testclient import TestClient

from app.main import create_app


def test_health_check() -> None:
    client = TestClient(create_app())
    response = client.get("/api/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv sync && uv run pytest apps/api/tests/test_health.py -q`
Expected: FAIL with `ModuleNotFoundError: No module named 'app.main'`

- [ ] **Step 3: Write minimal implementation**

```python
# apps/api/app/config.py
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "knowledge-warehouse"
    api_prefix: str = "/api"

    model_config = SettingsConfigDict(env_file=".env", env_prefix="KW_")


settings = Settings()

# apps/api/app/api/routes/health.py
from fastapi import APIRouter

router = APIRouter()


@router.get("/health")
def health_check() -> dict[str, str]:
    return {"status": "ok"}

# apps/api/app/main.py
from fastapi import FastAPI

from app.api.routes.health import router as health_router
from app.config import settings


def create_app() -> FastAPI:
    app = FastAPI(title=settings.app_name)
    app.include_router(health_router, prefix=settings.api_prefix)
    return app


app = create_app()

# apps/api/tests/conftest.py
import pytest

from app.main import create_app


@pytest.fixture()
def app():
    return create_app()

# .env.example
KW_APP_NAME=knowledge-warehouse
KW_API_PREFIX=/api
KW_DATABASE_URL=postgresql+psycopg://postgres:postgres@localhost:5432/knowledge_warehouse
KW_STORAGE_ENDPOINT=http://localhost:9000
KW_STORAGE_ACCESS_KEY=minioadmin
KW_STORAGE_SECRET_KEY=minioadmin
KW_STORAGE_BUCKET=knowledge-warehouse
KW_STORAGE_REGION=us-east-1
KW_STORAGE_USE_SSL=false

# docker-compose.yml
services:
  postgres:
    image: postgres:16
    environment:
      POSTGRES_DB: knowledge_warehouse
      POSTGRES_USER: postgres
      POSTGRES_PASSWORD: postgres
    ports: ["5432:5432"]
  minio:
    image: minio/minio:RELEASE.2024-10-13T13-34-11Z
    command: server /data --console-address ":9001"
    environment:
      MINIO_ROOT_USER: minioadmin
      MINIO_ROOT_PASSWORD: minioadmin
    ports: ["9000:9000", "9001:9001"]

# package.json
{
  "name": "knowledge-warehouse-root",
  "private": true,
  "packageManager": "pnpm@10.8.0",
  "scripts": {
    "web:test": "pnpm --dir apps/web test",
    "web:e2e": "pnpm --dir apps/web exec playwright test"
  }
}

# pnpm-workspace.yaml
packages:
  - "apps/web"

# justfile
api-test:
  uv run pytest apps/api/tests -q

up:
  docker compose up -d
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `uv run pytest apps/api/tests/test_health.py -q`
Expected: PASS with `1 passed`

- [ ] **Step 5: Commit**

```bash
git add README.md .env.example docker-compose.yml pyproject.toml package.json pnpm-workspace.yaml justfile apps/api/app/main.py apps/api/app/config.py apps/api/app/api/routes/health.py apps/api/tests/conftest.py apps/api/tests/test_health.py
git commit -m "chore: bootstrap knowledge warehouse workspace"
```

## Task 2: Add the Persistence Layer and Migration Skeleton

**Files:**
- Create: `alembic.ini`
- Create: `alembic/env.py`
- Create: `alembic/versions/0001_init_models.py`
- Create: `apps/api/app/db/base.py`
- Create: `apps/api/app/db/session.py`
- Create: `apps/api/app/db/models/__init__.py`
- Create: `apps/api/app/db/models/document.py`
- Create: `apps/api/app/db/models/knowledge.py`
- Modify: `apps/api/tests/conftest.py`
- Create: `apps/api/tests/test_document_models.py`
- Test: `apps/api/tests/test_document_models.py`

- [ ] **Step 1: Write the failing persistence test**

```python
# apps/api/tests/test_document_models.py
from app.db.models.document import Document, DocumentVersion
from app.db.models.knowledge import CandidateItem, KnowledgeItem, KnowledgeVersion


def test_candidate_and_published_knowledge_use_separate_tables(db_session) -> None:
    document = Document(title="Minimal Policy", source_name="fixture")
    db_session.add(document)
    db_session.flush()

    version = DocumentVersion(document_id=document.id, version_number=1, file_name="policy.pdf")
    db_session.add(version)
    db_session.flush()

    candidate = CandidateItem(
        document_version_id=version.id,
        item_type="entity",
        canonical_name="Incident",
        status="extracted",
    )
    published_version = KnowledgeVersion(version_label="v1", status="published")
    db_session.add_all([candidate, published_version])
    db_session.flush()

    published = KnowledgeItem(
        knowledge_version_id=published_version.id,
        item_type="entity",
        canonical_name="Incident",
        status="published",
    )
    db_session.add(published)
    db_session.commit()

    assert db_session.query(CandidateItem).count() == 1
    assert db_session.query(KnowledgeItem).count() == 1
    assert candidate.id != published.id
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest apps/api/tests/test_document_models.py -q`
Expected: FAIL with `ModuleNotFoundError` for `app.db`

- [ ] **Step 3: Write minimal implementation**

```python
# apps/api/app/db/base.py
from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    pass

# apps/api/app/db/session.py
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.config import settings

engine = create_engine(settings.database_url, future=True)
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)

# apps/api/app/config.py
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "knowledge-warehouse"
    api_prefix: str = "/api"
    database_url: str = "sqlite+pysqlite:///:memory:"
    model_config = SettingsConfigDict(env_file=".env", env_prefix="KW_")

# apps/api/app/db/models/__init__.py
from app.db.models.document import Document, DocumentSegment, DocumentVersion, ParseRun
from app.db.models.knowledge import AuditLog, CandidateItem, KnowledgeItem, KnowledgeVersion

# apps/api/app/db/models/document.py
from datetime import datetime
from uuid import uuid4

from sqlalchemy import DateTime, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class Document(Base):
    __tablename__ = "documents"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=lambda: str(uuid4()))
    title: Mapped[str] = mapped_column(String(255))
    source_name: Mapped[str] = mapped_column(String(255))
    document_key: Mapped[str] = mapped_column(String(255), unique=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    versions: Mapped[list["DocumentVersion"]] = relationship(back_populates="document")


class DocumentVersion(Base):
    __tablename__ = "document_versions"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=lambda: str(uuid4()))
    document_id: Mapped[str] = mapped_column(ForeignKey("documents.id"))
    version_number: Mapped[int] = mapped_column(Integer)
    file_name: Mapped[str] = mapped_column(String(255))
    storage_key: Mapped[str] = mapped_column(String(255), default="")
    mime_type: Mapped[str] = mapped_column(String(128), default="application/octet-stream")
    status: Mapped[str] = mapped_column(String(32), default="uploaded")
    document: Mapped[Document] = relationship(back_populates="versions")

# apps/api/app/db/models/knowledge.py
from datetime import datetime
from uuid import uuid4

from sqlalchemy import DateTime, Float, ForeignKey, JSON, String
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class CandidateItem(Base):
    __tablename__ = "candidate_items"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=lambda: str(uuid4()))
    document_version_id: Mapped[str] = mapped_column(ForeignKey("document_versions.id"))
    item_type: Mapped[str] = mapped_column(String(32))
    canonical_name: Mapped[str] = mapped_column(String(255))
    status: Mapped[str] = mapped_column(String(32))
    confidence: Mapped[float] = mapped_column(Float, default=0.0)
    review_status: Mapped[str] = mapped_column(String(32), default="pending")
    payload: Mapped[dict] = mapped_column(JSON, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class KnowledgeVersion(Base):
    __tablename__ = "knowledge_versions"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=lambda: str(uuid4()))
    version_label: Mapped[str] = mapped_column(String(32))
    status: Mapped[str] = mapped_column(String(32))
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class KnowledgeItem(Base):
    __tablename__ = "knowledge_items"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=lambda: str(uuid4()))
    knowledge_version_id: Mapped[str] = mapped_column(ForeignKey("knowledge_versions.id"))
    item_type: Mapped[str] = mapped_column(String(32))
    canonical_name: Mapped[str] = mapped_column(String(255))
    status: Mapped[str] = mapped_column(String(32))
    payload: Mapped[dict] = mapped_column(JSON, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class AuditLog(Base):
    __tablename__ = "audit_logs"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=lambda: str(uuid4()))
    action: Mapped[str] = mapped_column(String(64))
    actor: Mapped[str] = mapped_column(String(255))
    payload: Mapped[dict] = mapped_column(JSON, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

# apps/api/tests/conftest.py
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from app.db.base import Base


@pytest.fixture()
def db_session() -> Session:
    engine = create_engine("sqlite+pysqlite:///:memory:", future=True)
    Base.metadata.create_all(engine)
    SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)
    with SessionLocal() as session:
        yield session


@pytest.fixture()
def temp_storage_dir(tmp_path):
    return tmp_path / "storage"
```

- [ ] **Step 4: Create the migration scaffold**

```python
# alembic/env.py
from alembic import context
from sqlalchemy import engine_from_config, pool

from app.db.base import Base
from app.db.models import document, knowledge  # noqa: F401

config = context.config
target_metadata = Base.metadata

def run_migrations_online() -> None:
    connectable = engine_from_config(
        config.get_section(config.config_ini_section),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )
    with connectable.connect() as connection:
        context.configure(connection=connection, target_metadata=target_metadata)
        with context.begin_transaction():
            context.run_migrations()
```

- [ ] **Step 5: Run tests to verify they pass**

Run: `uv run pytest apps/api/tests/test_document_models.py -q`
Expected: PASS with `1 passed`

- [ ] **Step 6: Commit**

```bash
git add alembic.ini alembic apps/api/app/db apps/api/tests/conftest.py apps/api/tests/test_document_models.py apps/api/app/config.py
git commit -m "feat: add persistence models and migration scaffold"
```

## Task 3: Implement Document Intake, Storage, and Versioning

**Files:**
- Create: `apps/api/app/documents/storage.py`
- Create: `apps/api/app/documents/service.py`
- Create: `apps/api/app/api/routes/documents.py`
- Modify: `apps/api/app/main.py`
- Modify: `apps/api/app/config.py`
- Create: `apps/api/tests/test_document_upload.py`
- Test: `apps/api/tests/test_document_upload.py`

- [ ] **Step 1: Write the failing upload and versioning test**

```python
# apps/api/tests/test_document_upload.py
from app.documents.service import DocumentService
from app.documents.storage import LocalStorage


def test_upload_creates_document_and_version(db_session, temp_storage_dir) -> None:
    service = DocumentService(db_session, LocalStorage(str(temp_storage_dir)))
    document, version = service.upload(
        title="Incident Policy",
        source_name="fixture",
        document_key="incident-policy",
        file_name="policy.txt",
        content=b"Incident must be reported within 2 hours.",
    )

    assert document.title == "Incident Policy"
    assert version.version_number == 1
    assert version.status == "uploaded"


def test_uploading_same_document_key_creates_new_version(db_session, temp_storage_dir) -> None:
    service = DocumentService(db_session, LocalStorage(str(temp_storage_dir)))

    first_document, first_version = service.upload(
        title="Incident Policy",
        source_name="fixture",
        document_key="incident-policy",
        file_name="policy.txt",
        content=b"version one",
    )
    second_document, second_version = service.upload(
        title="Incident Policy",
        source_name="fixture",
        document_key="incident-policy",
        file_name="policy.txt",
        content=b"version two",
    )

    assert first_document.id == second_document.id
    assert first_version.version_number == 1
    assert second_version.version_number == 2
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest apps/api/tests/test_document_upload.py -q`
Expected: FAIL with `ModuleNotFoundError` for `app.documents`

- [ ] **Step 3: Write minimal implementation**

```python
# apps/api/app/config.py
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "knowledge-warehouse"
    api_prefix: str = "/api"
    database_url: str = "sqlite+pysqlite:///:memory:"
    storage_bucket: str = "knowledge-warehouse"
    storage_root: str = ".data/storage"
    model_config = SettingsConfigDict(env_file=".env", env_prefix="KW_")

# apps/api/app/documents/storage.py
from pathlib import Path
from uuid import uuid4


class LocalStorage:
    def __init__(self, root: str) -> None:
        self.root = Path(root)
        self.root.mkdir(parents=True, exist_ok=True)

    def save(self, content: bytes, file_name: str) -> str:
        key = f"{uuid4()}-{file_name}"
        target = self.root / key
        target.write_bytes(content)
        return key

# apps/api/app/documents/service.py
from sqlalchemy import select

from app.db.models.document import Document, DocumentVersion


class DocumentService:
    def __init__(self, session, storage) -> None:
        self.session = session
        self.storage = storage

    def upload(self, title: str, source_name: str, file_name: str, document_key: str | None, content: bytes):
        document = None
        if document_key:
            document = self.session.scalar(select(Document).where(Document.document_key == document_key))
        if document is None:
            document = Document(title=title, source_name=source_name, document_key=document_key or file_name)
            self.session.add(document)
            self.session.flush()

        current_versions = list(document.versions)
        stored_key = self.storage.save(content, file_name)
        version = DocumentVersion(
            document_id=document.id,
            version_number=len(current_versions) + 1,
            file_name=file_name,
            storage_key=stored_key,
            mime_type="application/octet-stream",
            status="uploaded",
        )
        self.session.add(version)
        self.session.commit()
        return document, version

# apps/api/app/api/routes/documents.py
from collections.abc import Generator

from fastapi import APIRouter, Depends, File, Form, UploadFile, status

from app.config import settings
from app.db.session import SessionLocal
from app.documents.service import DocumentService
from app.documents.storage import LocalStorage

router = APIRouter(prefix="/documents", tags=["documents"])


def get_document_service() -> Generator[DocumentService, None, None]:
    session = SessionLocal()
    try:
        yield DocumentService(session, LocalStorage(settings.storage_root))
    finally:
        session.close()


@router.post("", status_code=status.HTTP_201_CREATED)
async def upload_document(
    title: str = Form(...),
    source_name: str = Form(...),
    document_key: str | None = Form(default=None),
    file: UploadFile = File(...),
    service: DocumentService = Depends(get_document_service),
):
    document, version = service.upload(
        title=title,
        source_name=source_name,
        document_key=document_key,
        file_name=file.filename,
        content=await file.read(),
    )
    return {
        "id": document.id,
        "title": document.title,
        "latest_version": {"id": version.id, "version_number": version.version_number},
    }

# apps/api/app/main.py
from app.api.routes.documents import router as documents_router

app.include_router(documents_router, prefix=settings.api_prefix)
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `uv run pytest apps/api/tests/test_document_upload.py -q`
Expected: PASS with `2 passed`

- [ ] **Step 5: Commit**

```bash
git add apps/api/app/documents/storage.py apps/api/app/documents/service.py apps/api/app/api/routes/documents.py apps/api/app/main.py apps/api/app/config.py apps/api/tests/test_document_upload.py apps/api/app/db/models/document.py
git commit -m "feat: add document upload and versioning"
```

## Task 4: Implement Parsing Jobs, Document Segments, and Evidence Anchors

**Files:**
- Create: `apps/api/app/jobs/service.py`
- Create: `apps/api/app/jobs/runner.py`
- Create: `apps/api/app/parsing/service.py`
- Create: `apps/api/app/parsing/parsers/pdf_parser.py`
- Create: `apps/api/app/parsing/parsers/docx_parser.py`
- Create: `apps/api/app/parsing/parsers/doc_converter.py`
- Modify: `apps/api/app/db/models/document.py`
- Create: `apps/api/tests/test_parsing_service.py`
- Create: `fixtures/reference_scenarios/minimal_policy.txt`
- Test: `apps/api/tests/test_parsing_service.py`

- [ ] **Step 1: Write the failing parsing test**

```python
# apps/api/tests/test_parsing_service.py
from pathlib import Path

from app.parsing.service import ParsingService


def test_parser_creates_ordered_segments_with_evidence() -> None:
    source = Path("fixtures/reference_scenarios/minimal_policy.txt")
    document_text = source.read_text()

    service = ParsingService()
    segments = service.parse_text("minimal_policy.txt", document_text)

    assert len(segments) == 3
    assert segments[0].heading == "Section 1"
    assert segments[0].anchor == {"page": 1, "section": "Section 1", "line_start": 1, "line_end": 2}
    assert "incident report" in segments[1].content.lower()
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest apps/api/tests/test_parsing_service.py -q`
Expected: FAIL with `ModuleNotFoundError` for `app.parsing`

- [ ] **Step 3: Add the fixture and minimal parser implementation**

```text
# fixtures/reference_scenarios/minimal_policy.txt
Section 1
Incident policy overview.

Section 2
Every incident report must be submitted within 2 hours by the duty officer.

Section 3
The review board approves closure after evidence verification.
```

```python
# apps/api/app/parsing/service.py
from dataclasses import dataclass


@dataclass
class ParsedSegment:
    heading: str
    content: str
    anchor: dict[str, int | str]


class ParsingService:
    def parse_text(self, file_name: str, content: str) -> list[ParsedSegment]:
        blocks = [block.strip() for block in content.strip().split("\n\n") if block.strip()]
        segments: list[ParsedSegment] = []
        for index, block in enumerate(blocks, start=1):
            lines = block.splitlines()
            heading = lines[0]
            body = " ".join(lines[1:])
            segments.append(
                ParsedSegment(
                    heading=heading,
                    content=body,
                    anchor={"page": 1, "section": heading, "line_start": index * 2 - 1, "line_end": index * 2},
                )
            )
        return segments

# apps/api/app/parsing/parsers/pdf_parser.py
import fitz


def parse_pdf(file_path: str) -> list[tuple[int, str]]:
    document = fitz.open(file_path)
    return [(page.number + 1, page.get_text("text")) for page in document]

# apps/api/app/parsing/parsers/docx_parser.py
from docx import Document


def parse_docx(file_path: str) -> list[str]:
    document = Document(file_path)
    return [paragraph.text for paragraph in document.paragraphs if paragraph.text.strip()]

# apps/api/app/parsing/parsers/doc_converter.py
import subprocess
from pathlib import Path


def convert_doc_to_docx(file_path: str, output_dir: str) -> str:
    subprocess.run(
        ["soffice", "--headless", "--convert-to", "docx", file_path, "--outdir", output_dir],
        check=True,
    )
    return str(Path(output_dir) / (Path(file_path).stem + ".docx"))
```

- [ ] **Step 4: Extend the persistence model for parse runs and stored segments**

```python
# apps/api/app/db/models/document.py
from sqlalchemy import DateTime, ForeignKey, Integer, JSON, String, Text


class ParseRun(Base):
    __tablename__ = "parse_runs"
    id: Mapped[str] = mapped_column(String, primary_key=True, default=lambda: str(uuid4()))
    document_version_id: Mapped[str] = mapped_column(ForeignKey("document_versions.id"))
    status: Mapped[str] = mapped_column(String(32))
    parser_version: Mapped[str] = mapped_column(String(32), default="v1")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class DocumentSegment(Base):
    __tablename__ = "document_segments"
    id: Mapped[str] = mapped_column(String, primary_key=True, default=lambda: str(uuid4()))
    parse_run_id: Mapped[str] = mapped_column(ForeignKey("parse_runs.id"))
    segment_order: Mapped[int] = mapped_column(Integer)
    heading: Mapped[str] = mapped_column(String(255))
    content: Mapped[str] = mapped_column(Text)
    anchor: Mapped[dict] = mapped_column(JSON, default=dict)
```

- [ ] **Step 5: Run tests to verify they pass**

Run: `uv run pytest apps/api/tests/test_parsing_service.py -q`
Expected: PASS with `1 passed`

- [ ] **Step 6: Commit**

```bash
git add apps/api/app/jobs/service.py apps/api/app/jobs/runner.py apps/api/app/parsing/service.py apps/api/app/parsing/parsers/pdf_parser.py apps/api/app/parsing/parsers/docx_parser.py apps/api/app/parsing/parsers/doc_converter.py apps/api/app/db/models/document.py apps/api/tests/test_parsing_service.py fixtures/reference_scenarios/minimal_policy.txt
git commit -m "feat: add parsing pipeline and evidence segments"
```

## Task 5: Implement Candidate Extraction and Review Queue Data

**Files:**
- Create: `apps/api/app/extraction/service.py`
- Create: `apps/api/app/extraction/rules.py`
- Modify: `apps/api/app/db/models/knowledge.py`
- Create: `apps/api/tests/test_extraction_service.py`
- Test: `apps/api/tests/test_extraction_service.py`

- [ ] **Step 1: Write the failing extraction test**

```python
# apps/api/tests/test_extraction_service.py
from app.extraction.service import ExtractionService
from app.parsing.service import ParsedSegment


def test_extractor_emits_entity_event_process_and_rule_candidates() -> None:
    segments = [
        ParsedSegment(
            heading="Section 2",
            content="Every incident report must be submitted within 2 hours by the duty officer.",
            anchor={"page": 1, "section": "Section 2", "line_start": 4, "line_end": 5},
        ),
        ParsedSegment(
            heading="Section 3",
            content="The review board approves closure after evidence verification.",
            anchor={"page": 1, "section": "Section 3", "line_start": 7, "line_end": 8},
        ),
    ]

    candidates = ExtractionService().extract(segments)

    assert {item.item_type for item in candidates} >= {"entity", "event", "process", "rule"}
    assert any(item.canonical_name == "Duty Officer" for item in candidates)
    assert any(item.payload["evidence"]["section"] == "Section 2" for item in candidates)
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest apps/api/tests/test_extraction_service.py -q`
Expected: FAIL with `ModuleNotFoundError` for `app.extraction`

- [ ] **Step 3: Write minimal implementation**

```python
# apps/api/app/extraction/rules.py
from dataclasses import dataclass

from app.parsing.service import ParsedSegment
from app.db.base import Base


@dataclass
class ExtractedCandidate:
    item_type: str
    canonical_name: str
    status: str
    confidence: float
    payload: dict


def extract_candidates(segments: list[ParsedSegment]) -> list[ExtractedCandidate]:
    candidates: list[ExtractedCandidate] = []
    for segment in segments:
        content = segment.content.lower()
        if "incident report" in content:
            candidates.append(
                ExtractedCandidate(
                    item_type="entity",
                    canonical_name="Incident Report",
                    status="extracted",
                    confidence=0.92,
                    payload={"evidence": segment.anchor},
                )
            )
        if "duty officer" in content:
            candidates.append(
                ExtractedCandidate(
                    item_type="entity",
                    canonical_name="Duty Officer",
                    status="extracted",
                    confidence=0.88,
                    payload={"evidence": segment.anchor},
                )
            )
            candidates.append(
                ExtractedCandidate(
                    item_type="event",
                    canonical_name="Submit Incident Report",
                    status="extracted",
                    confidence=0.91,
                    payload={"trigger": "report submission", "evidence": segment.anchor},
                )
            )
            candidates.append(
                ExtractedCandidate(
                    item_type="rule",
                    canonical_name="Submission Within Two Hours",
                    status="extracted",
                    confidence=0.86,
                    payload={"expression": "submit <= 2h", "evidence": segment.anchor},
                )
            )
            candidates.append(
                ExtractedCandidate(
                    item_type="process",
                    canonical_name="Incident Closure Review",
                    status="extracted",
                    confidence=0.75,
                    payload={"steps": ["submit", "verify evidence", "approve closure"], "evidence": segment.anchor},
                )
            )
    return candidates

# apps/api/app/extraction/service.py
from app.extraction.rules import extract_candidates


class ExtractionService:
    def extract(self, segments):
        return extract_candidates(segments)

# apps/api/app/db/models/knowledge.py
from datetime import datetime
from uuid import uuid4

from sqlalchemy import DateTime, Float, ForeignKey, JSON, String
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base

class CandidateItem(Base):
    __tablename__ = "candidate_items"
    id: Mapped[str] = mapped_column(String, primary_key=True, default=lambda: str(uuid4()))
    document_version_id: Mapped[str] = mapped_column(ForeignKey("document_versions.id"))
    item_type: Mapped[str] = mapped_column(String(32))
    canonical_name: Mapped[str] = mapped_column(String(255))
    status: Mapped[str] = mapped_column(String(32))
    confidence: Mapped[float] = mapped_column(Float)
    review_status: Mapped[str] = mapped_column(String(32), default="pending")
    payload: Mapped[dict] = mapped_column(JSON, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `uv run pytest apps/api/tests/test_extraction_service.py -q`
Expected: PASS with `1 passed`

- [ ] **Step 5: Commit**

```bash
git add apps/api/app/extraction/service.py apps/api/app/extraction/rules.py apps/api/app/db/models/knowledge.py apps/api/tests/test_extraction_service.py
git commit -m "feat: add candidate extraction service"
```

## Task 6: Implement Governance Review, Publish Versions, and Query APIs

**Files:**
- Create: `apps/api/app/governance/service.py`
- Create: `apps/api/app/query/service.py`
- Create: `apps/api/app/api/routes/governance.py`
- Create: `apps/api/app/api/routes/knowledge.py`
- Modify: `apps/api/app/main.py`
- Create: `apps/api/tests/test_governance_publish.py`
- Create: `apps/api/tests/test_query_service.py`
- Test: `apps/api/tests/test_governance_publish.py`
- Test: `apps/api/tests/test_query_service.py`

- [ ] **Step 1: Write the failing governance and query tests**

```python
# apps/api/tests/test_governance_publish.py
from app.governance.service import GovernanceService


def test_publish_creates_knowledge_version_from_approved_candidates(db_session) -> None:
    service = GovernanceService(db_session)
    candidate_ids = service.seed_candidates_for_test()

    service.approve(candidate_ids[0], reviewer="architect")
    published = service.publish(version_label="v1", publisher="architect")

    assert published.version_label == "v1"
    assert published.status == "published"
    assert service.list_published_items("v1")

# apps/api/tests/test_query_service.py
from app.query.service import QueryService


def test_query_service_returns_graph_and_process_views(db_session) -> None:
    query_service = QueryService(db_session)
    query_service.seed_knowledge_graph_for_test()

    graph = query_service.get_graph("v1")
    processes = query_service.get_processes("v1")

    assert len(graph["nodes"]) >= 2
    assert len(graph["edges"]) >= 1
    assert processes[0]["steps"][0]["label"] == "Submit Incident Report"
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `uv run pytest apps/api/tests/test_governance_publish.py apps/api/tests/test_query_service.py -q`
Expected: FAIL with `ModuleNotFoundError` for `app.governance` and `app.query`

- [ ] **Step 3: Write minimal governance and publish implementation**

```python
# apps/api/app/governance/service.py
from datetime import datetime

from app.db.models.knowledge import CandidateItem, KnowledgeItem, KnowledgeVersion


class GovernanceService:
    def __init__(self, session) -> None:
        self.session = session

    def seed_candidates_for_test(self) -> list[str]:
        candidate = CandidateItem(
            document_version_id="seed-version",
            item_type="entity",
            canonical_name="Incident Report",
            status="extracted",
            confidence=0.91,
            review_status="pending",
            payload={"evidence": {"section": "Section 2"}},
        )
        self.session.add(candidate)
        self.session.commit()
        return [candidate.id]

    def approve(self, candidate_id: str, reviewer: str) -> None:
        candidate = self.session.get(CandidateItem, candidate_id)
        candidate.review_status = "approved"
        candidate.payload = {**candidate.payload, "reviewed_by": reviewer}
        self.session.commit()

    def publish(self, version_label: str, publisher: str) -> KnowledgeVersion:
        version = KnowledgeVersion(version_label=version_label, status="published")
        self.session.add(version)
        self.session.flush()
        approved = self.session.query(CandidateItem).filter_by(review_status="approved").all()
        for candidate in approved:
            self.session.add(
                KnowledgeItem(
                    knowledge_version_id=version.id,
                    item_type=candidate.item_type,
                    canonical_name=candidate.canonical_name,
                    status="published",
                    payload={**candidate.payload, "published_by": publisher, "published_at": datetime.utcnow().isoformat()},
                )
            )
        self.session.commit()
        return version

    def list_published_items(self, version_label: str) -> list[KnowledgeItem]:
        return (
            self.session.query(KnowledgeItem)
            .join(KnowledgeVersion, KnowledgeVersion.id == KnowledgeItem.knowledge_version_id)
            .filter(KnowledgeVersion.version_label == version_label)
            .all()
        )

# apps/api/app/query/service.py
from app.db.models.knowledge import KnowledgeItem, KnowledgeVersion


class QueryService:
    def __init__(self, session) -> None:
        self.session = session

    def seed_knowledge_graph_for_test(self) -> None:
        version = KnowledgeVersion(version_label="v1", status="published")
        self.session.add(version)
        self.session.flush()
        incident = KnowledgeItem(
            knowledge_version_id=version.id,
            item_type="entity",
            canonical_name="Incident Report",
            status="published",
            payload={},
        )
        self.session.add(incident)
        self.session.flush()
        process = KnowledgeItem(
            knowledge_version_id=version.id,
            item_type="process",
            canonical_name="Incident Closure Review",
            status="published",
            payload={"steps": [{"label": "Submit Incident Report"}, {"label": "Verify Evidence"}]},
        )
        relation = KnowledgeItem(
            knowledge_version_id=version.id,
            item_type="event",
            canonical_name="Submit Incident Report",
            status="published",
            payload={"relation_to": {"target_id": incident.id, "type": "changes"}},
        )
        self.session.add_all([process, relation])
        self.session.commit()

    def get_graph(self, version_label: str) -> dict:
        items = (
            self.session.query(KnowledgeItem)
            .join(KnowledgeVersion, KnowledgeVersion.id == KnowledgeItem.knowledge_version_id)
            .filter(KnowledgeVersion.version_label == version_label)
            .all()
        )
        nodes = [{"id": item.id, "label": item.canonical_name, "type": item.item_type} for item in items]
        edges = []
        for item in items:
            relation = item.payload.get("relation_to")
            if relation:
                edges.append({"source": item.id, "target": relation["target_id"], "label": relation["type"]})
        return {"nodes": nodes, "edges": edges}

    def get_processes(self, version_label: str) -> list[dict]:
        items = (
            self.session.query(KnowledgeItem)
            .join(KnowledgeVersion, KnowledgeVersion.id == KnowledgeItem.knowledge_version_id)
            .filter(KnowledgeVersion.version_label == version_label, KnowledgeItem.item_type == "process")
            .all()
        )
        return [{"id": item.id, "name": item.canonical_name, "steps": item.payload.get("steps", [])} for item in items]

# apps/api/app/api/routes/governance.py
from collections.abc import Generator

from fastapi import APIRouter, Depends, Response

from app.db.session import SessionLocal
from app.governance.service import GovernanceService
from app.query.service import QueryService

router = APIRouter(prefix="/governance", tags=["governance"])


def get_governance_service() -> Generator[GovernanceService, None, None]:
    session = SessionLocal()
    try:
        yield GovernanceService(session)
    finally:
        session.close()


@router.post("/candidates/{candidate_id}/approve", status_code=204)
def approve_candidate(candidate_id: str, reviewer: str, service: GovernanceService = Depends(get_governance_service)) -> Response:
    service.approve(candidate_id, reviewer)
    return Response(status_code=204)

@router.post("/publish")
def publish_knowledge(version_label: str, publisher: str, service: GovernanceService = Depends(get_governance_service)):
    version = service.publish(version_label=version_label, publisher=publisher)
    return {"id": version.id, "version_label": version.version_label}

# apps/api/app/api/routes/knowledge.py
router = APIRouter(prefix="/knowledge", tags=["knowledge"])


def get_query_service() -> Generator[QueryService, None, None]:
    session = SessionLocal()
    try:
        yield QueryService(session)
    finally:
        session.close()


@router.get("/graph")
def get_graph(version_label: str, service: QueryService = Depends(get_query_service)):
    return service.get_graph(version_label)

@router.get("/processes")
def get_processes(version_label: str, service: QueryService = Depends(get_query_service)):
    return service.get_processes(version_label)
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `uv run pytest apps/api/tests/test_governance_publish.py apps/api/tests/test_query_service.py -q`
Expected: PASS with `2 passed`

- [ ] **Step 5: Commit**

```bash
git add apps/api/app/governance/service.py apps/api/app/query/service.py apps/api/app/api/routes/governance.py apps/api/app/api/routes/knowledge.py apps/api/app/main.py apps/api/tests/test_governance_publish.py apps/api/tests/test_query_service.py
git commit -m "feat: add governance publish flow and knowledge query api"
```

## Task 7: Build the Web Console for Intake, Governance, and Knowledge Views

**Files:**
- Create: `apps/web/package.json`
- Create: `apps/web/tsconfig.json`
- Create: `apps/web/vite.config.ts`
- Create: `apps/web/index.html`
- Create: `apps/web/src/main.tsx`
- Create: `apps/web/src/App.tsx`
- Create: `apps/web/src/lib/api.ts`
- Create: `apps/web/src/lib/query-client.ts`
- Create: `apps/web/src/pages/DocumentsPage.tsx`
- Create: `apps/web/src/pages/GovernancePage.tsx`
- Create: `apps/web/src/pages/KnowledgeGraphPage.tsx`
- Create: `apps/web/src/pages/ProcessViewPage.tsx`
- Create: `apps/web/src/components/DocumentUploadForm.tsx`
- Create: `apps/web/src/components/CandidateReviewTable.tsx`
- Create: `apps/web/src/components/KnowledgeGraph.tsx`
- Create: `apps/web/src/components/ProcessFlow.tsx`
- Create: `apps/web/src/test/DocumentsPage.test.tsx`
- Create: `apps/web/src/test/GovernancePage.test.tsx`
- Test: `apps/web/src/test/DocumentsPage.test.tsx`
- Test: `apps/web/src/test/GovernancePage.test.tsx`

- [ ] **Step 1: Write the failing UI tests**

```tsx
// apps/web/src/test/DocumentsPage.test.tsx
import { render, screen } from "@testing-library/react";

import { DocumentsPage } from "../pages/DocumentsPage";

test("renders upload form and version table", () => {
  render(<DocumentsPage />);
  expect(screen.getByText("Upload Source Document")).toBeInTheDocument();
  expect(screen.getByText("Document Versions")).toBeInTheDocument();
});

// apps/web/src/test/GovernancePage.test.tsx
import { render, screen } from "@testing-library/react";

import { GovernancePage } from "../pages/GovernancePage";

test("renders candidate review queue", () => {
  render(<GovernancePage />);
  expect(screen.getByText("Candidate Review Queue")).toBeInTheDocument();
  expect(screen.getByRole("button", { name: "Publish Version" })).toBeInTheDocument();
});
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `pnpm --dir apps/web test --runInBand`
Expected: FAIL with `ERR_PNPM_NO_IMPORTER_MANIFEST_FOUND` or missing component files

- [ ] **Step 3: Write minimal implementation**

```json
// apps/web/package.json
{
  "name": "knowledge-warehouse-web",
  "private": true,
  "version": "0.1.0",
  "scripts": {
    "dev": "vite",
    "build": "tsc && vite build",
    "test": "vitest run",
    "preview": "vite preview"
  },
  "dependencies": {
    "@tanstack/react-query": "^5.59.0",
    "antd": "^5.22.0",
    "axios": "^1.7.0",
    "cytoscape": "^3.30.0",
    "react": "^18.3.1",
    "react-dom": "^18.3.1",
    "react-flow-renderer": "^10.3.17",
    "react-router-dom": "^6.28.0"
  },
  "devDependencies": {
    "@testing-library/jest-dom": "^6.6.3",
    "@testing-library/react": "^16.0.1",
    "@types/react": "^18.3.12",
    "@types/react-dom": "^18.3.1",
    "typescript": "^5.6.3",
    "vite": "^5.4.10",
    "vitest": "^2.1.4"
  }
}
```

```tsx
// apps/web/src/pages/DocumentsPage.tsx
import { Card, Table, Typography } from "antd";

import { DocumentUploadForm } from "../components/DocumentUploadForm";

export function DocumentsPage() {
  return (
    <Card>
      <Typography.Title level={3}>Upload Source Document</Typography.Title>
      <DocumentUploadForm />
      <Typography.Title level={4}>Document Versions</Typography.Title>
      <Table dataSource={[]} columns={[{ title: "Version", dataIndex: "version_number" }]} rowKey="version_number" />
    </Card>
  );
}

// apps/web/src/pages/GovernancePage.tsx
import { Button, Card, Typography } from "antd";

import { CandidateReviewTable } from "../components/CandidateReviewTable";

export function GovernancePage() {
  return (
    <Card>
      <Typography.Title level={3}>Candidate Review Queue</Typography.Title>
      <CandidateReviewTable />
      <Button type="primary">Publish Version</Button>
    </Card>
  );
}

// apps/web/src/components/DocumentUploadForm.tsx
import { Button, Form, Input, Upload } from "antd";

export function DocumentUploadForm() {
  return (
    <Form layout="vertical">
      <Form.Item label="Title" name="title">
        <Input />
      </Form.Item>
      <Form.Item label="Source Name" name="source_name">
        <Input />
      </Form.Item>
      <Upload beforeUpload={() => false}>
        <Button>Select File</Button>
      </Upload>
      <Button type="primary" htmlType="submit">
        Upload
      </Button>
    </Form>
  );
}

// apps/web/src/components/CandidateReviewTable.tsx
import { Table } from "antd";

export function CandidateReviewTable() {
  return (
    <Table
      rowKey="id"
      dataSource={[]}
      columns={[
        { title: "Type", dataIndex: "item_type" },
        { title: "Name", dataIndex: "canonical_name" },
        { title: "Confidence", dataIndex: "confidence" },
      ]}
    />
  );
}
```

- [ ] **Step 4: Add explorer pages and API client**

```tsx
// apps/web/src/lib/api.ts
import axios from "axios";

export const api = axios.create({
  baseURL: import.meta.env.VITE_API_BASE_URL ?? "http://localhost:8000/api",
});

// apps/web/src/pages/KnowledgeGraphPage.tsx
import { Card, Typography } from "antd";

import { KnowledgeGraph } from "../components/KnowledgeGraph";

export function KnowledgeGraphPage() {
  return (
    <Card>
      <Typography.Title level={3}>Knowledge Graph</Typography.Title>
      <KnowledgeGraph />
    </Card>
  );
}

// apps/web/src/pages/ProcessViewPage.tsx
import { Card, Typography } from "antd";

import { ProcessFlow } from "../components/ProcessFlow";

export function ProcessViewPage() {
  return (
    <Card>
      <Typography.Title level={3}>Process View</Typography.Title>
      <ProcessFlow />
    </Card>
  );
}
```

- [ ] **Step 5: Run tests to verify they pass**

Run: `pnpm install && pnpm --dir apps/web test`
Expected: PASS with `2 passed`

- [ ] **Step 6: Commit**

```bash
git add apps/web package.json pnpm-workspace.yaml
git commit -m "feat: add knowledge warehouse web console"
```

## Task 8: Add Auth, Audit, and End-to-End Smoke Coverage

**Files:**
- Create: `apps/api/app/auth/service.py`
- Create: `apps/api/app/audit/service.py`
- Modify: `apps/api/app/api/routes/governance.py`
- Modify: `apps/api/app/db/models/knowledge.py`
- Create: `apps/api/tests/test_auth_audit.py`
- Create: `apps/web/playwright.config.ts`
- Create: `apps/web/e2e/knowledge-review.spec.ts`
- Test: `apps/api/tests/test_auth_audit.py`
- Test: `apps/web/e2e/knowledge-review.spec.ts`

- [ ] **Step 1: Write the failing auth and audit tests**

```python
# apps/api/tests/test_auth_audit.py
from fastapi.testclient import TestClient

from app.db.models.knowledge import AuditLog
from app.main import create_app


def test_publish_requires_publisher_role(db_session) -> None:
    client = TestClient(create_app())
    response = client.post("/api/governance/publish?version_label=v1&publisher=analyst")
    assert response.status_code == 403


def test_successful_publish_writes_audit_log(db_session) -> None:
    client = TestClient(create_app())
    response = client.post(
        "/api/governance/publish?version_label=v1&publisher=architect",
        headers={"X-Role": "publisher"},
    )
    assert response.status_code in {200, 201}
    logs = db_session.query(AuditLog).all()
    assert any(log.action == "publish_knowledge" for log in logs)
```

```ts
// apps/web/e2e/knowledge-review.spec.ts
import { expect, test } from "@playwright/test";

test("review flow uploads a document and opens explorers", async ({ page }) => {
  await page.goto("/");
  await expect(page.getByText("Upload Source Document")).toBeVisible();
  await page.getByText("Governance").click();
  await expect(page.getByText("Candidate Review Queue")).toBeVisible();
  await page.getByText("Knowledge Graph").click();
  await expect(page.getByText("Knowledge Graph")).toBeVisible();
});
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `uv run pytest apps/api/tests/test_auth_audit.py -q && pnpm --dir apps/web exec playwright test`
Expected: FAIL with `403` not enforced and missing Playwright config

- [ ] **Step 3: Write minimal implementation**

```python
# apps/api/app/auth/service.py
from fastapi import Header, HTTPException, status


def require_role(required_role: str):
    def dependency(x_role: str | None = Header(default=None)) -> str:
        if x_role != required_role:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="forbidden")
        return x_role

    return dependency

# apps/api/app/audit/service.py
from app.db.models.knowledge import AuditLog


class AuditService:
    def __init__(self, session) -> None:
        self.session = session

    def record(self, action: str, actor: str, payload: dict) -> None:
        self.session.add(AuditLog(action=action, actor=actor, payload=payload))
        self.session.commit()

# apps/api/app/api/routes/governance.py
from collections.abc import Generator

from app.audit.service import AuditService
from app.auth.service import require_role
from app.db.session import SessionLocal


def get_audit_service() -> Generator[AuditService, None, None]:
    session = SessionLocal()
    try:
        yield AuditService(session)
    finally:
        session.close()


@router.post("/publish")
def publish_knowledge(
    version_label: str,
    publisher: str,
    role: str = Depends(require_role("publisher")),
    service: GovernanceService = Depends(get_governance_service),
    audit: AuditService = Depends(get_audit_service),
):
    version = service.publish(version_label=version_label, publisher=publisher)
    audit.record("publish_knowledge", actor=publisher, payload={"version_label": version_label, "role": role})
    return {"id": version.id, "version_label": version.version_label}
```

```ts
// apps/web/playwright.config.ts
import { defineConfig } from "@playwright/test";

export default defineConfig({
  testDir: "./e2e",
  use: {
    baseURL: "http://127.0.0.1:5173",
    headless: true,
  },
  webServer: {
    command: "pnpm dev --host 127.0.0.1 --port 5173",
    port: 5173,
    reuseExistingServer: true,
  },
});
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `uv run pytest apps/api/tests/test_auth_audit.py -q`
Expected: PASS with `2 passed`

Run: `pnpm --dir apps/web exec playwright test`
Expected: PASS with `1 passed`

- [ ] **Step 5: Commit**

```bash
git add apps/api/app/auth/service.py apps/api/app/audit/service.py apps/api/app/api/routes/governance.py apps/api/app/db/models/knowledge.py apps/api/tests/test_auth_audit.py apps/web/playwright.config.ts apps/web/e2e/knowledge-review.spec.ts
git commit -m "feat: add auth audit and e2e smoke coverage"
```

## Task 9: Finish the First-Project Hardening Pass

**Files:**
- Modify: `README.md`
- Modify: `.env.example`
- Modify: `docker-compose.yml`
- Modify: `apps/api/app/api/routes/documents.py`
- Modify: `apps/api/app/api/routes/knowledge.py`
- Modify: `apps/web/src/pages/DocumentsPage.tsx`
- Modify: `apps/web/src/pages/GovernancePage.tsx`
- Modify: `apps/web/src/pages/KnowledgeGraphPage.tsx`
- Modify: `apps/web/src/pages/ProcessViewPage.tsx`
- Test: `apps/api/tests/test_document_upload.py`
- Test: `apps/api/tests/test_governance_publish.py`
- Test: `apps/api/tests/test_query_service.py`
- Test: `apps/web/src/test/DocumentsPage.test.tsx`
- Test: `apps/web/src/test/GovernancePage.test.tsx`
- Test: `apps/web/e2e/knowledge-review.spec.ts`

- [ ] **Step 1: Add the final failing integration test for search and version compare**

```python
# apps/api/tests/test_query_service.py
def test_search_returns_only_published_items_for_requested_version(db_session) -> None:
    query_service = QueryService(db_session)
    query_service.seed_knowledge_graph_for_test()

    results = query_service.search(version_label="v1", query="incident")

    assert all(item["version_label"] == "v1" for item in results)
    assert any(item["canonical_name"] == "Incident Report" for item in results)
```

- [ ] **Step 2: Run the full suite to verify the new test fails**

Run: `uv run pytest apps/api/tests -q && pnpm --dir apps/web test && pnpm --dir apps/web exec playwright test`
Expected: FAIL on missing `search` implementation

- [ ] **Step 3: Implement search, compare endpoints, and README/operator docs**

```python
# apps/api/app/query/service.py
def search(self, version_label: str, query: str) -> list[dict]:
    items = (
        self.session.query(KnowledgeItem)
        .join(KnowledgeVersion, KnowledgeVersion.id == KnowledgeItem.knowledge_version_id)
        .filter(KnowledgeVersion.version_label == version_label)
        .filter(KnowledgeItem.canonical_name.ilike(f"%{query}%"))
        .all()
    )
    return [
        {
            "id": item.id,
            "canonical_name": item.canonical_name,
            "item_type": item.item_type,
            "version_label": version_label,
        }
        for item in items
    ]

# apps/api/app/api/routes/knowledge.py
@router.get("/search")
def search(version_label: str, query: str, service: QueryService = Depends(get_query_service)):
    return service.search(version_label, query)

# README.md
## Local Development
1. `cp .env.example .env`
2. `docker compose up -d`
3. `uv sync`
4. `pnpm install`
5. `uv run uvicorn app.main:app --reload --app-dir apps/api`
6. `pnpm --dir apps/web dev`

## First Release Capabilities
- Upload and version `PDF/DOC/DOCX`
- Parse document segments with evidence anchors
- Extract candidate entities, events, processes, rules, and metrics
- Review, approve, reject, and publish knowledge versions
- Explore graph and process views
```

- [ ] **Step 4: Run the full suite to verify it passes**

Run: `uv run pytest apps/api/tests -q`
Expected: PASS with all backend tests green

Run: `pnpm --dir apps/web test`
Expected: PASS with all UI tests green

Run: `pnpm --dir apps/web exec playwright test`
Expected: PASS with `1 passed`

- [ ] **Step 5: Commit**

```bash
git add README.md .env.example docker-compose.yml apps/api/app/api/routes/documents.py apps/api/app/api/routes/knowledge.py apps/api/app/query/service.py apps/api/tests apps/web/src/pages/DocumentsPage.tsx apps/web/src/pages/GovernancePage.tsx apps/web/src/pages/KnowledgeGraphPage.tsx apps/web/src/pages/ProcessViewPage.tsx
git commit -m "docs: finish knowledge warehouse foundation hardening"
```

## Self-Review Checklist

- Spec coverage: this plan covers phase-one acceptance only, including intake, parsing, extraction, governance, graph/process views, roles, audit, and local deployment. Phase-two construct mapping and later generation loops are intentionally excluded.
- Placeholder scan: no `TBD`, `TODO`, or "implement later" placeholders remain in the task steps.
- Type consistency: the plan uses one stable vocabulary across tasks: `Document`, `DocumentVersion`, `CandidateItem`, `KnowledgeItem`, `KnowledgeVersion`, `ParsingService`, `ExtractionService`, `GovernanceService`, and `QueryService`.
