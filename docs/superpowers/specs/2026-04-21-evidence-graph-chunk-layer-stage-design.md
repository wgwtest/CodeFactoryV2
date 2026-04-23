# Evidence Graph / Chunk Layer Stage Design

## Purpose

`evidence_graph_chunk_layer` is the first persisted stage that turns evidence units into a
document-level topology that downstream retrieval can consume. It answers:

- How evidence units are grouped into chunk windows
- How chunk windows are linked into an evidence graph layer
- Which chunks required boundary adjustments
- Which evidence units were grouped into which chunks

This stage sits between:

- `evidence_constructor`
- `evidence_pack`

and keeps the original 13-stage blueprint intact.

## Real execution entry points

The stage now runs and persists from all three document entry paths:

- `ArchiveExtractionService.build_archive(...)`
- `ArchiveExtractionService.formalize_document(...)`
- `ArchiveExtractionService.import_document(...)`

It is only persisted when both of these inputs exist:

- a document contribution
- a parsed document

## Inputs

The builder consumes:

- `archive_id`
- `document_id`
- `document_title`
- `contribution`
- `parsed_document`

The contribution provides the source evidence excerpts.
The parsed document provides segment ordering and anchor context.

## Output snapshot

Stage id:

- `evidence_graph_chunk_layer`

Current snapshot title:

- `Evidence Graph / Chunk Layer`

## Core runtime nodes

Primary nodes:

- `Chunk Planning`
- `Evidence Unit Set`
- `Chunk Group`
- `Evidence Graph Layer`

Secondary nodes:

- `Boundary Adjustments`
- `Evidence Unit {n}`
- `Chunk {n}`
- `Boundary Fix {n}`
- `Chunk Warning` (only when no chunks can be built)

## Core runtime edges

Primary edges:

- `results_in`
- `grouped_into`
- `connects`
- `linked_to`

Secondary edges:

- `contains`
- `adjusted_by`

## Stage semantics

### Chunk construction

Evidence rows are first matched against parsed segments using the same matching logic as
`evidence_constructor`.

Then the stage builds one chunk per matched segment index.

If no matched evidence rows exist, the stage falls back to the first parser segments and emits
fallback chunk windows so runtime visualization still has a real object graph.

### Boundary adjustment

A chunk is marked as boundary-adjusted when either:

- it contains more than one evidence unit, or
- its underlying segment window is unusually long

This keeps the stage aligned with the intended role of:

- `Chunk Planning`
- `Evidence Graph / Chunk Layer`
- boundary repair / boundary fix behavior

### Graph links

Adjacent chunk windows are connected with `linked_to` edges to form the evidence graph layer.

This is intentionally conservative for the current migration step:

- it gives runtime a real graph topology
- it does not yet attempt semantic graph construction beyond adjacency

## Observer window semantics

### Stage view

Shows:

- evidence unit count
- chunk count
- graph link count
- adjusted chunk count
- strategy (`segment_evidence_alignment`)

The stream explains:

- evidence alignment
- chunk creation
- boundary adjustment count

### Node view

Node observers are currently provided for:

- `Chunk Group`
- `Evidence Graph Layer`
- first 3 chunk nodes

Each chunk node shows:

- chunk index
- segment index
- evidence unit count
- anchor
- boundary adjusted flag

### Edge view

Edge observers are currently provided for:

- `results_in`
- `connects`
- the first `linked_to`

This is enough to support the current single-document drilldown interaction model.

## Dynamic behavior represented

The stage snapshot is designed so runtime can present:

- chunk creation
- chunk adjacency
- chunk regrouping context
- boundary adjustment presence

It does **not** yet persist:

- a time-ordered chunk event log
- chunk merge/split history
- semantic graph edges beyond adjacency

Those remain future enhancements.

## Current limits

1. Chunk windows are inferred from evidence-to-segment alignment rather than built from a
   first-class chunk engine.
2. Boundary adjustments are heuristic.
3. Graph links are adjacency-based, not semantic similarity links.
4. Only a subset of nodes and edges has dedicated observer payloads.

## Why this stage is still correct

Even with the current limits, this implementation is already materially different from the old
derived runtime fallback:

- it is executed during extract/import/formalize
- it is persisted as a real stage snapshot
- runtime prefers the persisted snapshot over fallback mapping

That means `evidence_graph_chunk_layer` is now part of the real execution chain rather than just a
display-only derived stage.
