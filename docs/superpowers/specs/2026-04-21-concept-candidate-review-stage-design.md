# Concept Candidate Review Stage Design

## Stage Position

`Concept Candidate Review` is the 8th stage in the agreed 13-stage extraction blueprint:

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

This stage answers:

- which concept-like candidates were proposed from the current evidence pack
- how many candidate objects were materialized for the document
- which categories and aliases were attached during candidate review
- what the document-level candidate distribution looks like before canonical consolidation

## Why This Stage Matters

Before this slice, the runtime UI could only show concept review through a derived view rebuilt from contribution payloads. That was enough for visualization, but it was not a real stage object that could be persisted, replayed, or preferred by the runtime API.

By materializing `concept_candidate_review` as a real stage snapshot, the system now has a persisted contract between:

- upstream `evidence_pack`
- downstream `canonical_knowledge`

## Real Execution Entry Points

The real stage snapshot is now persisted from the same three execution paths already used by other implemented stages:

- `ArchiveExtractionService.build_archive(...)`
- `ArchiveExtractionService.formalize_document(...)`
- `ArchiveExtractionService.import_document(...)`

This keeps the implementation aligned with the current archive extraction chain while moving the runtime model toward the target 13-stage engine.

## Current Real Inputs

The stage currently consumes:

- `archive_id`
- `document_id`
- `document_title`
- `contribution`

The real source of truth is the contribution payload already produced by the formal extraction chain:

- `entities`
- `events`
- `processes`
- their aliases
- their evidence rows
- their category fields

## Current Real Outputs

Stage snapshot id:

- `concept_candidate_review`

### Core nodes

The persisted graph currently materializes:

- `Evidence Pack Input`
- `Concept Candidate Set`
- `Category Groups`
- `Alias Groups`
- candidate nodes derived from document `entities / events / processes`
- category nodes
- alias nodes
- optional `Concept Candidate Warning`

### Core edges

The persisted graph currently materializes:

- `proposes`
- `contains`
- `categorized_as`
- `aliased_as`
- optional `warned_by`

## Observer Semantics

### Stage observer

The stage observer focuses on:

- candidate count
- evidence count
- category count
- alias count
- candidate type distribution
- stage-level progress and result events

### Node observer

The node observer currently provides real payloads for:

- `Concept Candidate Set`
- each candidate node

This means the UI can click a concept candidate node and see:

- object identity
- candidate type
- category
- review status
- alias count
- evidence count

### Edge observer

The edge observer currently provides real payloads for:

- `Evidence Pack Input -> Concept Candidate Set` (`proposes`)
- `candidate -> category` (`categorized_as`)
- `candidate -> alias` (`aliased_as`)

This lets the UI inspect not only nodes but also the actual relationship objects inside the stage graph.

## Current Limits

This is now a real stage, but it is still intentionally scoped:

1. Candidate review is still sourced from contribution objects
   - it does not yet persist a fully native intermediate candidate store outside runtime snapshots

2. The stage currently treats document `entities / events / processes` as the candidate source
   - later iterations may separate raw candidate proposals from normalized contribution items

3. Candidate rejection and drop reasoning is still minimal
   - the current snapshot focuses on positive materialization, category assignment, and alias links

## Why This Does Not Drift from the Original Design

This implementation does **not** introduce a parallel pipeline.

Instead, it keeps the stage exactly where it belongs in the original design:

- `evidence_pack` produces task-scoped evidence
- `concept_candidate_review` materializes candidate objects
- `canonical_knowledge` consolidates them later

So the runtime model is getting closer to the original design, not farther away from it.
