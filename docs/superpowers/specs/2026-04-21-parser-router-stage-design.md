## Parser Router Stage Design

### Purpose
`parser_router` is the first stage that turns a raw document into an executable parsing plan.
It answers a narrow question:

- what parser route should this document take
- why was that parser selected
- which fallback candidates were considered

This stage sits between `asset_intake` and `parser_execution`.

### Real Execution Entry Points
The stage is now persisted from the same three entry points used by the other real runtime slices:

- `build_archive(...)`
- `formalize_document(...)`
- `import_document(...)`

The implementation lives in:

- `apps/api/app/archive_knowledge/runtime_parser_router.py`
- `apps/api/app/archive_knowledge/extraction.py`

### Inputs
The persisted runtime snapshot is built from:

- `document_id`
- `document_title`
- `file_type`
- `source_file_path`
- `parser_name`
- `parser_version`

Current routing is still constrained by the legacy extraction engine. That means:

- when parser metadata is available, the snapshot records the actual selected parser
- when parser metadata is missing, the snapshot falls back to a deterministic file-type based route

### Outputs
The runtime snapshot persists:

- stage observer
- graph nodes
- graph edges
- node observers
- edge observers

### Real Nodes
The current real graph includes:

- `Source File`
- `Routing Task`
- `Document Type`
- `Selected Parser`
- `Routing Decision`
- optional `Parser Candidate` fallback nodes
- optional `Routing Warning`

### Real Edges
The current real graph includes:

- `classified_as`
- `evaluated_by`
- `selects`
- `results_in`
- optional `considered`
- optional `warned_by`

### Observer Semantics
#### Stage view
Shows:

- detected document type
- selected parser
- parser version
- number of candidate routes
- fallback vs metadata mode

#### Node view
The most important node views are:

- `Selected Parser`
- `Routing Decision`

They explain:

- which parser was selected
- whether the route was derived from actual parser metadata or file-type fallback
- what the selected parser version is

#### Edge view
The key edge is:

- `Routing Task -> Selected Parser` via `selects`

This explains the route decision itself.

### Current Limitations
This is a real persisted runtime stage, but it is still limited by the old extraction engine:

- there is no fully independent parser-router execution engine yet
- candidate parser lists are deterministic and file-type based
- route rules are still simplified compared with the target 13-stage design

### Why This Still Matches the Original Design
This implementation still respects the original phase intent:

- it separates routing from parsing
- it makes the parser selection observable
- it leaves room for a later true routing engine without changing the runtime contract shape

### Recommended Next Stages
After `parser_router`, the next high-value real stages remain:

- `concept_candidate_review`
- `relation_review_family_normalization`
- `definition_summary_conflict_consolidation`
- `indexes_snapshots_apis`
