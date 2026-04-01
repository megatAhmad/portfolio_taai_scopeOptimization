# Gap Closure Plan

## Purpose

This plan closes the implementation gaps identified between the current prototype and the PRD in `shutdown_maintenance_equipment_prd.md`. It is organized so the team can move from a functional prototype to a production-shaped product with stronger auditability, guided workflows, and industry-standard engineering practices.

## Current State Summary

The current implementation already provides:

- Project creation and deletion
- Dataset upload and deletion
- CSV and Excel ingestion
- Basic schema preview
- Basic derived column evaluation
- Basic AST persistence with versioning
- Classification output table

The main gaps are:

- No confidence-based or fuzzy entity matching
- No row-level rule lineage or supporting evidence output
- No engineer-facing rule path or confidence view
- Excel sheet selection is not enforced through an intercept flow
- Schema mapping is manual JSON, not a guided grid
- Rule builder is flat, not a nested visual AST tree
- No downloadable/exportable results
- Limited validation, observability, testing, and deployment readiness

## Delivery Principles

- Preserve the existing working prototype while iterating toward the PRD
- Prefer backward-compatible API changes where possible
- Build auditability into the data model, not just the UI
- Separate user-facing workflow improvements from backend execution correctness
- Add verification and test coverage alongside each workstream

## Recommended Delivery Phases

### Phase 1: Product-Critical PRD Gaps

Goal: Close the largest functional gaps that block PRD alignment.

#### 1. Guided Excel Sheet Selection

### Problem
The PRD requires an explicit React intercept for Excel sheet selection. The current form only exposes a text field and the backend defaults to the first sheet when none is supplied.

### Build
- Add a backend endpoint to inspect uploaded Excel files and return available sheet names before final ingestion
- Introduce a temporary upload or in-memory inspection flow for Excel files
- Replace the current text input with a modal-based sheet selection experience
- Prevent upload submission until a sheet is explicitly selected for `.xlsx` and `.xls`
- Add error states for invalid or missing sheet selections

### Backend deliverables
- `POST /api/datasets/inspect-file` or equivalent endpoint returning:
  - file type
  - sheet names
  - preview of selected sheet headers if useful
- Validation to reject Excel uploads without sheet selection
- Removal of the current silent fallback to sheet `0`

### Frontend deliverables
- File drop/select handler that detects Excel files
- Modal for sheet selection
- Upload state machine for:
  - file selected
  - sheet inspection loading
  - sheet chosen
  - upload confirmed

### Acceptance criteria
- Excel uploads cannot proceed without explicit sheet selection
- Users can choose from actual sheet names returned by the backend
- Invalid sheet names produce clear errors

#### 2. Guided Schema Mapping Grid

### Problem
The PRD calls for a schema mapping grid, but the current implementation relies on raw JSON and manual text entry.

### Build
- Add a field-mapping UI that compares supplementary columns against canonical columns
- Support user-defined renaming targets and join key selection via dropdowns
- Show mapping suggestions based on exact and normalized name similarity
- Validate that required join columns are present before upload
- Keep advanced JSON editing only as an optional expert mode, if at all

### Backend deliverables
- Schema introspection response for uploaded files:
  - source columns
  - inferred data types
  - preview rows
- Optional mapping suggestion endpoint

### Frontend deliverables
- Mapping grid with columns such as:
  - source column
  - mapped target column
  - inferred type
  - include/exclude toggle
- Join column selector for canonical and supplementary datasets
- Validation messages for invalid mappings

### Acceptance criteria
- Users can complete mapping without writing JSON
- Mapping rules are stored in structured form
- Supplementary datasets can be aligned to canonical fields through the UI alone

#### 3. Nested Visual Rule Builder

### Problem
The PRD expects a dynamic visual AST tree. The current builder supports only flat condition groups.

### Build
- Redesign the rule builder to support nested groups
- Allow users to add:
  - condition
  - subgroup
  - AND/OR combinators at any group level
- Support reordering and removing nodes
- Show a synchronized AST preview
- Add validation for invalid tree states

### Backend deliverables
- Pydantic models for recursive AST validation
- Request validation for nested rule trees
- Stable serialization format with version history

### Frontend deliverables
- Recursive rule editor component
- Controls to add subgroup and condition nodes
- Delete and reorder controls
- Validation states for empty or invalid groups

### Acceptance criteria
- Users can create nested rule trees with multiple levels
- The AST stored in the database reflects the visual structure exactly
- Latest saved version reloads accurately

#### 4. Classification Explainability and Evidence Trace

### Problem
The PRD requires clear rule lineage, supporting source evidence, and visible rule paths. The current implementation only returns final labels and rows.

### Build
- Extend classification execution to produce row-level explanation objects
- Capture for each row:
  - final classification
  - matched top-level rule (`must_have`, `good_to_have`, fallback)
  - path of evaluated groups/conditions
  - each condition result
  - source fields consulted
  - derived fields consulted
  - null/fallback behavior used
- Add a row drill-down panel in the UI

### Backend deliverables
- A structured explanation model included with classification results
- Optional persisted run records for reproducibility
- Rule node IDs in AST to make explanations stable and traceable

### Frontend deliverables
- Result table with row selection
- Evidence drawer/modal showing:
  - rule path
  - condition outcomes
  - field values used during evaluation
  - joined source context

### Acceptance criteria
- A planner can explain why each row was classified the way it was
- An engineer can inspect rule path and supporting evidence for any row

#### 5. Confidence-Based Matching and Low-Quality ID Handling

### Problem
The PRD highlights messy real-world data and confidence-based matching. The current implementation uses exact joins only.

### Build
- Introduce normalized matching for equipment IDs:
  - trim whitespace
  - case normalization
  - punctuation stripping
  - configurable normalization rules
- Add optional fuzzy matching for non-exact IDs
- Generate a confidence score and match method per supplementary join
- Preserve both exact and fuzzy match diagnostics for auditability
- Allow users to review low-confidence matches

### Backend deliverables
- Matching pipeline supporting:
  - exact match
  - normalized exact match
  - fuzzy candidate match
- Matching result columns such as:
  - `match_method`
  - `match_confidence`
  - `matched_source_id`
- Threshold configuration for auto-accept vs manual review

### Frontend deliverables
- Match review UI for low-confidence rows
- Confidence badges in results
- Filters for unmatched and low-confidence items

### Acceptance criteria
- The system can surface and explain non-exact matches
- Confidence scores are visible and auditable
- Users can review problematic joins instead of silently losing rows

#### 6. Downloadable Results

### Problem
The PRD references downloadable results, but the product currently only renders a table.

### Build
- Add export endpoints for classification runs
- Support CSV initially, with Excel export as a second step if needed
- Include both summary and row-level details in exports
- Optionally include evidence columns and confidence metadata

### Backend deliverables
- `GET /api/projects/{id}/classifications/latest/export?format=csv`
- Streaming or generated file response

### Frontend deliverables
- Export button on results view
- Export options such as:
  - summary only
  - full results
  - include evidence columns

### Acceptance criteria
- Users can download the final classified matrix in a common format

## Phase 2: Governance, Reliability, and Production Readiness

Goal: Apply industry-standard engineering practices that reduce operational risk.

#### 7. Strong Input Validation and Upload Safety

### Build
- Validate file extension, MIME type, max size, and parseability
- Validate mapping payload structure before persisting dataset metadata
- Validate rule ASTs before saving
- Clean up partially persisted uploads on failure
- Reject unsupported operators and malformed payloads with structured errors

### Acceptance criteria
- Invalid inputs fail safely and clearly
- No orphaned files remain after failed upload attempts

#### 8. Persisted Classification Runs

### Build
- Add a `classification_runs` table with:
  - project id
  - ruleset id/version
  - run timestamp
  - status
  - result summary
  - metadata snapshot
- Optionally store row-level output separately or as a generated artifact
- Allow viewing latest and historical runs

### Acceptance criteria
- A classification run is reproducible against a known ruleset version and dataset state

#### 9. Audit Logging

### Build
- Capture activity events for:
  - project creation/deletion
  - dataset upload/deletion
  - ruleset save
  - classification run
  - export action
- Store actor, timestamp, object id, and metadata snapshot

### Acceptance criteria
- Admins can reconstruct who changed what and when

#### 10. Alembic Migrations and Environment Management

### Build
- Replace `Base.metadata.create_all()` bootstrap with Alembic migrations
- Add environment-based configuration for:
  - database path
  - upload directory
  - file size limit
  - CORS origins
- Add `.env.example`

### Acceptance criteria
- The database schema is versioned and deployable across environments

#### 11. Background Jobs for Heavy Operations

### Build
- Move classification and large-ingestion workflows into background tasks or a queue
- Add job polling or websocket progress updates
- Support retries and failure states

### Acceptance criteria
- Large files and complex classifications do not block request-response cycles

#### 12. Observability and Error Monitoring

### Build
- Structured logging
- Request IDs and correlation IDs
- Metrics for uploads, classification duration, failure rate
- Centralized error handling in FastAPI

### Acceptance criteria
- Failures can be diagnosed from logs and metrics without manual reproduction

## Phase 3: UX and Decision Quality Improvements

Goal: Improve usability, trust, and planning efficiency.

#### 13. Richer Dataset Preview and Profiling

### Build
- Show inferred data types, null rates, and sample values
- Warn on duplicate IDs, missing join keys, and suspicious columns
- Highlight columns used by saved rules

#### 14. Better Result Exploration

### Build
- Filters by classification, confidence, match type, and missing evidence
- Search by equipment ID
- Column visibility toggle
- Side-by-side source evidence view

#### 15. Row-Level Review Workflow

### Build
- Manual review queue for unmatched and low-confidence rows
- Resolution actions such as:
  - accept suggested match
  - override match
  - mark as unresolved

#### 16. Saved Views and Rule Impact Preview

### Build
- Preview how many rows would move between classes before saving a new ruleset
- Compare current ruleset to previous version
- Highlight changed decisions between versions

## Cross-Cutting Engineering Work

### Testing Strategy

#### Backend tests
- Unit tests for operator evaluation
- Unit tests for null and fallback behavior
- Unit tests for normalization and fuzzy matching
- Integration tests for upload, ruleset save, classification, export, delete cascade

#### Frontend tests
- Component tests for mapping grid and rule builder
- Workflow tests for upload, sheet selection, classification, and evidence drill-down

#### End-to-end tests
- Happy path from project creation to export
- Failure paths for invalid uploads and bad rules

### Security and Data Handling

- Limit upload size and file types
- Sanitize filenames
- Protect against malicious spreadsheets and oversized payloads
- Add CSRF/auth strategy if this becomes multi-user
- Review whether uploaded source files contain sensitive operational data and apply retention rules

### Performance

- Paginate classification results
- Avoid returning entire result sets inline for large jobs
- Cache schema introspection when possible
- Use parquet or persisted intermediate tables if data volumes grow

## Proposed Data Model Additions

Add or revise the following entities:

- `classification_runs`
- `classification_run_rows` or exported artifact references
- `audit_events`
- `dataset_match_reviews`
- `dataset_profiles`
- richer `rulesets` with node IDs and metadata

## Proposed API Additions

- `POST /api/datasets/inspect-file`
- `POST /api/projects/{id}/datasets/preview-mapping`
- `GET /api/projects/{id}/rulesets/history`
- `POST /api/projects/{id}/classify` returning run id instead of only inline data for async mode
- `GET /api/projects/{id}/classification-runs`
- `GET /api/classification-runs/{run_id}`
- `GET /api/classification-runs/{run_id}/export`
- `POST /api/classification-runs/{run_id}/review-match`

## Implementation Order Recommendation

### Sprint 1
- Guided Excel sheet selection
- Schema mapping grid
- Strong validation for uploads and mappings

### Sprint 2
- Nested visual rule builder
- Recursive AST validation
- Rule node IDs

### Sprint 3
- Explainability engine
- Evidence drawer UI
- Persisted classification runs

### Sprint 4
- Confidence-based matching
- Low-confidence review queue
- Exportable results

### Sprint 5
- Audit logging
- Alembic migrations
- Observability and structured logging
- Background job architecture

## Definition of Done for PRD Alignment

The implementation should be considered aligned with the PRD when all of the following are true:

- Excel uploads require explicit sheet selection through a guided intercept flow
- Supplementary-to-canonical mapping is completed through a mapping grid, not raw JSON
- Rule builder supports nested visual AST construction
- Rules are versioned and validated using structured recursive schemas
- Classification output includes rule lineage, supporting evidence, and row-level rule paths
- Low-quality IDs are handled through normalization and confidence-aware matching
- Users can inspect confidence and source categories for each equipment row
- Results can be exported in at least CSV format
- Dataset and project deletions are auditable and fully cascading
- Migrations, tests, validation, and logging are in place for production use

## Immediate Next Recommendation

If the team wants the highest ROI path, start with these three builds first:

1. Guided schema mapping and Excel sheet selection
2. Nested AST rule builder with backend validation
3. Explainability output with row-level evidence panel

These three changes close the biggest PRD gaps and create the foundation needed for confidence matching and governed exports.
