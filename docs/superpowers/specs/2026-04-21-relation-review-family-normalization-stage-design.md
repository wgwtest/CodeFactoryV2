# Relation Review / Family Normalization Stage Design

## Stage Position

`Relation Review / Family Normalization` is the 9th stage in the agreed
13-stage extraction blueprint:

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

- which relation candidates were materialized from the current document
- how candidate endpoints map into family groups
- whether alias collisions exist across family groups
- how relation candidates connect to normalized family clusters before canonical consolidation

## Why This Stage Matters

Before this slice, runtime could only show relation review through a thin
derived view rebuilt from contribution payloads. That was enough for rendering,
but not enough for persistence, replay, or stage-level observer inspection.

By materializing `relation_review_family_normalization` as a real stage
snapshot, the system now has a persisted relation-review layer between:

- upstream `concept_candidate_review`
- downstream `canonical_knowledge`

## Real Execution Entry Points

The real stage snapshot is now persisted from the same archive execution paths
already used by the previously completed stages:

- `ArchiveExtractionService.build_archive(...)`
- `ArchiveExtractionService.formalize_document(...)`
- `ArchiveExtractionService.import_document(...)`

This keeps the implementation aligned with the current archive extraction chain
while moving runtime closer to the target 13-stage engine.

## Current Real Inputs

The stage currently consumes:

- `archive_id`
- `document_id`
- `document_title`
- `contribution`

The real source of truth is the contribution payload already produced by the
formal extraction chain:

- `relations`
- `entities`
- `events`
- `processes`
- aliases attached to those items
- relation endpoint names and evidence

## Current Real Outputs

Stage snapshot id:

- `relation_review_family_normalization`

### Core nodes

The persisted graph currently materializes:

- `Evidence Pack Input`
- `Relation Candidate Set`
- `Family Normalization`
- `Family Groups`
- `Alias Collisions`
- relation candidate nodes derived from document relations
- family group nodes derived from item names and aliases
- alias collision nodes when one alias maps to multiple family groups
- optional `Relation Review Warning`

### Core edges

The persisted graph currently materializes:

- `proposes`
- `normalized_by`
- `contains`
- `source_family`
- `target_family`
- `conflicts_with`
- optional `warned_by`

## Observer Semantics

### Stage observer

The stage observer focuses on:

- relation candidate count
- family group count
- alias collision count
- relation type distribution
- normalization progress and result events

### Node observer

The node observer currently provides real payloads for:

- `Relation Candidate Set`
- `Family Normalization`
- each `Family Group`
- each `Relation Candidate`
- each `Alias Collision`

This means the UI can click a relation candidate or family group node and see:

- source / target names
- confidence
- family key
- alias count
- member count
- relation reference count

### Edge observer

The edge observer currently provides real payloads for:

- `Evidence Pack Input -> Relation Candidate Set` (`proposes`)
- `Relation Candidate Set -> Family Normalization` (`normalized_by`)
- `Relation Candidate -> Family Group` (`source_family`, `target_family`)
- `Relation Candidate -> Alias Collision` (`conflicts_with`)

This lets the UI inspect not only nodes but also the actual normalization and
collision relationships inside the stage graph.

## Current Limits

This is now a real stage, but it is still intentionally scoped:

1. Family groups are derived from contribution items and relation endpoints
   - there is not yet a separate native family store outside runtime snapshots

2. Alias collision detection is string-normalization based
   - later iterations may add richer semantic grouping or controlled vocabularies

3. Relation rejection and drop reasoning is still minimal
   - the current snapshot focuses on materialized candidates, family grouping,
     and alias-collision visibility

## Why This Does Not Drift from the Original Design

This implementation does **not** invent a parallel pipeline.

Instead, it keeps the stage exactly where it belongs in the original design:

- `evidence_pack` prepares the evidence input
- `concept_candidate_review` materializes concept-like candidates
- `relation_review_family_normalization` resolves relation and family structure
- `canonical_knowledge` consolidates normalized outputs later

So the runtime model is moving closer to the original 13-stage blueprint, not
away from it.
