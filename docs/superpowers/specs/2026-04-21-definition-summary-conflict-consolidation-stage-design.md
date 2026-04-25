# Definition / Summary / Conflict Consolidation Stage Design

## Purpose

`definition_summary_conflict_consolidation` sits between
`relation_review_family_normalization` and `canonical_knowledge` in the original
13-stage extraction blueprint.

Its responsibility is to transform normalized relation-review outputs into
three document-scoped working sets:

- definition candidates
- summary candidates
- conflict candidates

The stage must remain observable as a first-class runtime graph rather than be
collapsed into canonicalization.

## Current Real Execution Entry Points

The stage is now materialized during:

- `build_archive(...)`
- `formalize_document(...)`
- `import_document(...)`

Each entry point persists a runtime snapshot through
`DocumentRuntimeRepository.save_stage_snapshot(...)`.

## Current Real Input

The current implementation builds this stage from the document contribution:

- `document`
- `entities`
- `events`
- `processes`
- `relations`

This keeps the implementation aligned with the existing extraction chain while
still making the stage explicit and inspectable.

## Current Real Output

### Core nodes

- `Relation Review Input`
- `Definition Candidate Set`
- `Summary Candidate Set`
- `Conflict Candidate Set`
- `Consolidation Decisions`
- optional `Definition Stage Warning`
- definition candidate nodes
- summary candidate nodes
- conflict candidate nodes

### Core edges

- `proposes`
- `resolved_by`
- `conflicts_with`
- `contains`
- optional `warned_by`

## Observer Semantics

### Stage view

The stage observer answers:

- how many definitions were materialized
- how many summaries were materialized
- how many unresolved conflicts remain
- what the current primary consolidation path is

### Node view

Node observers expose:

- candidate-set identity
- item/category metadata for definition candidates
- summary type and support counts for summary candidates
- reason and scope for conflict candidates

### Edge view

Edge observers explain:

- why relation-review input proposed definitions
- how summaries were resolved from relation-review input
- why conflict candidates were emitted

## Current Limitations

This stage is already persisted, but it is still derived from contribution
payloads rather than from a separately persisted intermediate consolidation
engine.

That means:

- definitions are inferred from contribution items with evidence
- summaries are derived from document/item/relation counts
- conflicts are currently inferred from alias collisions, missing endpoints,
  and missing evidence

These simplifications are acceptable for the current migration phase because
they preserve the original stage boundary and make it observable without
inventing a parallel pipeline.

## Why This Does Not Drift From the Original Design

The original design explicitly separated:

- `Relation Review / Family Normalization`
- `Definition / Summary / Conflict Consolidation`
- `Canonical Knowledge`

This implementation preserves that separation:

- relation normalization remains upstream
- definition/summary/conflict objects are observable in their own stage
- canonicalization remains downstream

So the runtime chain is still consistent with the target blueprint rather than
compressing multiple semantic steps into one stage.
