# Canonical Knowledge real stage design

## Purpose

This document describes how the `canonical_knowledge` stage is implemented as a
real persisted runtime stage within the current extraction chain.

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

This slice only turns stage `11` into a real runtime snapshot. It does not
change the overall stage order.

## Stage responsibility

`canonical_knowledge` answers:

- which normalized document-scoped knowledge objects were materialized
- which relation edges survived into the canonical layer
- how many entities / events / processes exist after consolidation
- which review state distribution the canonical layer currently carries

This stage is intentionally placed between:

- the upstream candidate/relation/definition stages
- the downstream `quality_policy_evaluation_governance_gate`

## Current real execution entry points

The real snapshot is now written from all document-producing extraction entry
points:

- `ArchiveExtractionService.build_archive(...)`
- `ArchiveExtractionService.formalize_document(...)`
- `ArchiveExtractionService.import_document(...)`

## Current real input

The stage currently consumes:

- `contribution`
- `document`
- `knowledge_items`

Where `knowledge_items` are built from:

- `ArchiveKnowledgeService._build_document_knowledge_items_from_contribution(...)`

This means the current real stage is persisted, but its upstream canonical
objects are still derived from the current contribution layer, not yet from
fully independent upstream persisted candidate stages.

## Current real output

Persisted stage snapshot id:

- `canonical_knowledge`

Core nodes:

- `Canonical Item Set`
- `Canonical Relation Set`
- `Merge Decisions`
- `Dropped Candidates`
- individual canonical item nodes

Core edges:

- `results_in`
- `supports`
- `contains`
- canonical relation edges between normalized items

## Observer semantics

### Stage view

Shows:

- canonical item count
- relation count
- entity / event / process distribution
- review distribution
- consolidation progress/result stream

### Node view

Primary node observers are available for:

- `Canonical Item Set`
- `Canonical Relation Set`
- `Merge Decisions`
- individual canonical items

### Edge view

Primary edge observers are available for:

- canonical relation edges
- stage-level consolidation edges

## Current limitations

The stage is now real and persisted, but it still has boundaries:

1. canonical items are still derived from contribution payloads
2. merge decisions are represented as a persisted stage object, but not yet as
   a fully independent execution task with its own event store
3. upstream candidate stages are not yet real persisted stages, so this stage
   cannot yet point back to native candidate objects

## Why this is still the right next step

Even with those limitations, making `canonical_knowledge` real is necessary
before the remaining middle stages become real, because:

- `quality_gate` should eventually consume canonical objects, not ad-hoc item
  lists
- the document drilldown graph needs a stable normalized object layer
- the runtime contract now has a real bridge from evidence structures into
  governance structures

## Recommended next stages after this slice

With `canonical_knowledge` persisted, the next recommended real stages are:

1. `parser_router`
2. `concept_candidate_review`
3. `relation_review_family_normalization`
4. `definition_summary_conflict_consolidation`
5. `indexes_snapshots_apis`

The order still intentionally follows the original blueprint and does not drift
into an alternative pipeline.
