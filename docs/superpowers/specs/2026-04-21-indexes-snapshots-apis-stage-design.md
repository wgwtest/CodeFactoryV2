# Indexes / Snapshots / APIs real stage design

## Purpose

This document describes how the `indexes_snapshots_apis` stage is implemented
as a real persisted runtime stage within the current extraction chain.

The stage still follows the original 13-stage blueprint:

1. `asset_intake`
2. `parser_router`
3. `parser_execution`
4. `unified_document_object`
5. `evidence_constructor`
6. `evidence_graph_chunk_layer`
7. `evidence_pack`
8. `concept_candidate_review`
9. `relation_review_family_normalization`
10. `definition_summary_conflict_consolidation`
11. `canonical_knowledge`
12. `quality_policy_evaluation_governance_gate`
13. `indexes_snapshots_apis`

This slice only turns stage `13` into a real runtime snapshot. It does not
change the overall stage order.

## Stage responsibility

`indexes_snapshots_apis` answers:

- whether the current document has a published snapshot representation
- which version label is currently active for publication
- whether index-layer materialization is available
- whether the API payload layer can serve the published object set

This stage is intentionally placed after:

- `quality_policy_evaluation_governance_gate`

Because it represents the output surface of the pipeline rather than another
quality or consolidation step.

## Current real execution entry points

The real snapshot is now written from all document-producing extraction entry
points:

- `ArchiveExtractionService.build_archive(...)`
- `ArchiveExtractionService.formalize_document(...)`
- `ArchiveExtractionService.import_document(...)`

## Current real input

The stage currently consumes:

- `document`
- `current_version`
- `document_published`

Where publication state is derived from:

- `ArchiveKnowledgeService.get_publication_overview(...)`
- `JsonPublishedKnowledgeRepository.load_latest(...)`

This means the stage is now persisted from real archive publication state
instead of being derived only at runtime display time.

## Current real output

Persisted stage snapshot id:

- `indexes_snapshots_apis`

Core nodes:

- `Publication Snapshot`
- `Search / Graph Index`
- `API Payload`

Core edges:

- `indexed_as`
- `served_by`

## Observer semantics

### Stage view

Shows:

- whether the document is currently published
- the active publication version label
- whether the snapshot is materialized into the index and API layers
- the resulting publish-layer status

### Node view

Primary node observers are available for:

- `Publication Snapshot`
- `Search / Graph Index`
- `API Payload`

### Edge view

Primary edge observers are available for:

- `Publication Snapshot -> Search / Graph Index` via `indexed_as`
- `Publication Snapshot -> API Payload` via `served_by`

## Current limitations

The stage is now real and persisted, but it still has clear boundaries:

1. it represents the publication layer from persisted publication state rather
   than a standalone asynchronous index writer
2. it does not yet differentiate between search index and graph index as two
   separate physical execution tasks
3. it does not yet persist per-backend write acknowledgements

## Why this still matches the original design

This implementation still respects the original phase intent:

- it keeps the publish surface separate from `quality_gate`
- it exposes versioned snapshot state as a first-class runtime object
- it allows later replacement by a more detailed publish/index execution engine
  without changing the runtime contract shape

## Resulting migration state

With this stage completed, all 13 stages in the original extraction blueprint
now have real persisted runtime snapshots.
