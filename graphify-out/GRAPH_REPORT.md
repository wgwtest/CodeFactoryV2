# Graph Report - .  (2026-04-13)

## Corpus Check
- 63 files · ~23,305 words
- Verdict: corpus is large enough that graph structure adds value.

## Summary
- 283 nodes · 474 edges · 28 communities detected
- Extraction: 91% EXTRACTED · 9% INFERRED · 0% AMBIGUOUS · INFERRED: 43 edges (avg confidence: 0.5)
- Token cost: 0 input · 0 output

## God Nodes (most connected - your core abstractions)
1. `ArchiveKnowledgeService` - 40 edges
2. `ParsingService` - 17 edges
3. `QueryService` - 13 edges
4. `ExtractionService` - 12 edges
5. `DocumentService` - 12 edges
6. `build_knowledge_index()` - 10 edges
7. `Base` - 10 edges
8. `_extract_entities()` - 9 edges
9. `JsonPublishedKnowledgeRepository` - 9 edges
10. `_find_item_info()` - 9 edges

## Surprising Connections (you probably didn't know these)
- `ExtractionService` --uses--> `SourceDocument`  [INFERRED]
  apps/api/app/extraction/service.py → apps/api/app/knowledge_builder.py
- `SourceDocument` --uses--> `ParsedSegment`  [INFERRED]
  apps/api/app/knowledge_builder.py → apps/api/app/parsing/models.py
- `ArchiveKnowledgeService` --uses--> `Neo4jPublishedKnowledgeRepository`  [INFERRED]
  apps/api/app/archive_knowledge/service.py → apps/api/app/integrations/neo4j/repository.py
- `ArchiveKnowledgeService` --uses--> `Neo4jClient`  [INFERRED]
  apps/api/app/archive_knowledge/service.py → apps/api/app/integrations/neo4j/client.py
- `ParsingService` --uses--> `DocumentVersion`  [INFERRED]
  apps/api/app/parsing/service.py → apps/api/app/db/models/document.py

## Communities

### Community 0 - "Community 0"
Cohesion: 0.09
Nodes (18): ArchiveKnowledgeService, AuditService, _build_document_index(), _build_document_knowledge_items(), _build_document_record(), _build_document_stats(), _build_item_documents(), _build_item_evidence() (+10 more)

### Community 1 - "Community 1"
Cohesion: 0.07
Nodes (17): BaseModel, ArchiveBatchApprovePayload, ArchiveItemReviewPayload, ArchiveItemUpdatePayload, ArchiveMergePayload, ArchivePublishPayload, get_archive_graph(), get_archive_processes() (+9 more)

### Community 2 - "Community 2"
Cohesion: 0.16
Nodes (28): _add_relation(), build_knowledge_index(), _canonicalize_operational_node_token(), _classify_entity(), _clean_phrase(), _dedupe_list(), _default_category(), _document_id() (+20 more)

### Community 3 - "Community 3"
Cohesion: 0.14
Nodes (13): Base, Base, DeclarativeBase, Document, DocumentSegment, DocumentVersion, ParseRun, AuditLog (+5 more)

### Community 4 - "Community 4"
Cohesion: 0.15
Nodes (4): Protocol, JsonPublishedKnowledgeRepository, Neo4jPublishedKnowledgeRepository, PublishedKnowledgeRepository

### Community 5 - "Community 5"
Cohesion: 0.18
Nodes (3): ParsedDocument, ParsedSegment, ParsingService

### Community 6 - "Community 6"
Cohesion: 0.36
Nodes (10): _build_docling_converter(), _cell_to_text(), _iter_block_items(), parse_docx(), parse_docx_segments(), _parse_docx_with_docling(), _parse_docx_with_python_docx(), _parse_docx_with_unstructured() (+2 more)

### Community 7 - "Community 7"
Cohesion: 0.42
Nodes (8): collect_documents(), _contains_supported_documents(), extract_archives(), _file_digest(), _load_json(), main(), render_summary(), resolve_document_roots()

### Community 8 - "Community 8"
Cohesion: 0.48
Nodes (2): ExtractionService, _select_llm_segments()

### Community 9 - "Community 9"
Cohesion: 0.33
Nodes (0): 

### Community 10 - "Community 10"
Cohesion: 0.6
Nodes (5): _append_candidate(), _append_document_relations(), _append_relation(), extract_candidates(), extract_document_batch()

### Community 11 - "Community 11"
Cohesion: 0.5
Nodes (4): BaseSettings, resolve_llm_config(), ResolvedLLMConfig, Settings

### Community 12 - "Community 12"
Cohesion: 0.4
Nodes (2): OpenAI, OpenAICompatibleLLM

### Community 13 - "Community 13"
Cohesion: 0.4
Nodes (0): 

### Community 14 - "Community 14"
Cohesion: 0.7
Nodes (4): parse_pdf(), parse_pdf_segments(), _parse_pdf_with_docling(), _parse_pdf_with_unstructured()

### Community 15 - "Community 15"
Cohesion: 0.4
Nodes (1): LocalStorage

### Community 16 - "Community 16"
Cohesion: 0.5
Nodes (1): Neo4jClient

### Community 17 - "Community 17"
Cohesion: 0.5
Nodes (2): ArtifactInterpretation, TypedDict

### Community 18 - "Community 18"
Cohesion: 0.5
Nodes (1): Initial persistence scaffold.  Revision ID: 0001_init_models Revises: Create Dat

### Community 19 - "Community 19"
Cohesion: 1.0
Nodes (2): build_llm(), build_structured_llm()

### Community 20 - "Community 20"
Cohesion: 0.67
Nodes (0): 

### Community 21 - "Community 21"
Cohesion: 1.0
Nodes (2): convert_doc_to_docx(), convert_office_document()

### Community 22 - "Community 22"
Cohesion: 1.0
Nodes (2): parse_spreadsheet_segments(), _parse_xlsx_segments()

### Community 23 - "Community 23"
Cohesion: 0.67
Nodes (0): 

### Community 24 - "Community 24"
Cohesion: 1.0
Nodes (0): 

### Community 25 - "Community 25"
Cohesion: 1.0
Nodes (0): 

### Community 26 - "Community 26"
Cohesion: 1.0
Nodes (0): 

### Community 27 - "Community 27"
Cohesion: 1.0
Nodes (0): 

## Knowledge Gaps
- **2 isolated node(s):** `Placeholder for parse/extract job orchestration added in later tasks.`, `Initial persistence scaffold.  Revision ID: 0001_init_models Revises: Create Dat`
  These have ≤1 connection - possible missing edges or undocumented components.
- **Thin community `Community 24`** (2 nodes): `main.py`, `create_app()`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 25`** (2 nodes): `health.py`, `health_check()`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 26`** (2 nodes): `runner.py`, `create_runner()`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 27`** (2 nodes): `rebuild.py`, `reconcile_curated_payload()`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **Why does `ArchiveKnowledgeService` connect `Community 0` to `Community 16`, `Community 1`, `Community 4`?**
  _High betweenness centrality (0.214) - this node is a cross-community bridge._
- **Why does `ExtractionService` connect `Community 8` to `Community 0`, `Community 1`, `Community 2`, `Community 5`?**
  _High betweenness centrality (0.139) - this node is a cross-community bridge._
- **Why does `SourceDocument` connect `Community 2` to `Community 8`, `Community 5`?**
  _High betweenness centrality (0.121) - this node is a cross-community bridge._
- **Are the 8 inferred relationships involving `ArchiveKnowledgeService` (e.g. with `ArchiveItemUpdatePayload` and `ArchiveItemReviewPayload`) actually correct?**
  _`ArchiveKnowledgeService` has 8 INFERRED edges - model-reasoned connections that need verification._
- **Are the 5 inferred relationships involving `ParsingService` (e.g. with `DocumentSegment` and `DocumentVersion`) actually correct?**
  _`ParsingService` has 5 INFERRED edges - model-reasoned connections that need verification._
- **Are the 7 inferred relationships involving `QueryService` (e.g. with `ArchiveItemUpdatePayload` and `ArchiveItemReviewPayload`) actually correct?**
  _`QueryService` has 7 INFERRED edges - model-reasoned connections that need verification._
- **Are the 6 inferred relationships involving `ExtractionService` (e.g. with `SourceDocument` and `ExtractedCandidate`) actually correct?**
  _`ExtractionService` has 6 INFERRED edges - model-reasoned connections that need verification._