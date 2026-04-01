# Review Fix Plan

## Purpose

This plan addresses the issues raised during the post-implementation review. It focuses on eliminating correctness risks, tightening validation, improving UX fidelity, and reducing scale-related risk in the current implementation.

## Review Findings Covered

This plan addresses the following reviewed concerns:

1. Supplementary datasets with duplicate equipment IDs are collapsed into a single match, losing source evidence.
2. Upload validation does not guarantee that mapped join and equipment ID columns still exist after mapping.
3. Excel interception still previews the first sheet before the user explicitly confirms a sheet.
4. Project navigation can leave stale classification results visible.
5. Classification run persistence is not scalable for large datasets because full rows and explanation trees are stored in a single JSON-heavy table.

## Guiding Principles

- Fail fast on invalid data configuration.
- Preserve auditability without silently dropping source evidence.
- Keep the guided UX aligned with the PRD’s intent, not just minimally functional.
- Make persistence patterns sustainable for larger datasets.
- Prefer incremental, testable changes over broad refactors without checkpoints.

## Workstream 1: Preserve Duplicate Supplementary Matches

### Problem

The current matching logic builds a dictionary keyed by normalized source ID. If the supplementary dataset contains duplicate or repeated IDs, only the last row survives in memory and all previous matches are discarded.

### Desired Outcome

A canonical row should be able to retain all relevant supplementary evidence, or the product should apply a deliberate aggregation policy rather than silently overwriting rows.

### Fix Options

#### Option A: One-to-many exploded join

Use a matching pipeline that preserves every matching supplementary row and produces multiple joined rows when multiple supplementary records match the same canonical row.

Use this if:
- the product wants a fully normalized evidence model
- downstream classification can operate on exploded row sets

Tradeoffs:
- row counts increase quickly
- UI and export logic must handle repeated canonical rows cleanly

#### Option B: Evidence aggregation per canonical row

Aggregate duplicate supplementary matches into a list structure per canonical row, such as:
- matched source ids
- matched categories
- match confidence list
- evidence row snapshots

Use this if:
- the product wants a single canonical output row
- rule evaluation can operate against aggregated derived values or flattened helper columns

Tradeoffs:
- AST and derived-column logic may need support for array-aware evaluation
- export formatting becomes more deliberate

### Recommended Approach

Implement Option B first.

Reason:
- it preserves the single source-of-truth row model already used in the product
- it closes the silent data-loss problem without forcing major UI redesign
- it better matches the PRD language about seeing all source categories tied to an equipment item

### Build Tasks

#### Backend
- Replace the `normalized_source_ids` single-row dictionary logic with grouped match candidates.
- Build a match aggregation structure keyed by canonical row.
- Persist supplementary evidence columns in a deterministic way, for example:
  - `*_matched_source_ids`
  - `*_match_count`
  - `*_matched_values`
  - `*_match_confidences`
- Decide how rule evaluation should behave when a field contains multiple matched values.
- If necessary, introduce helper flattening rules such as:
  - first match
  - concatenated text
  - max confidence
  - any-match boolean

#### Frontend
- Update results view so evidence trace can show multiple supplementary matches for a single canonical row.
- Update export formatting to include aggregated evidence values clearly.

#### Testing
- Add tests for duplicate supplementary IDs.
- Add tests ensuring no evidence rows are silently dropped.

### Acceptance Criteria

- Duplicate supplementary matches no longer overwrite one another.
- Users can inspect all matched supplementary evidence for a canonical row.
- Classification behavior is explicit and deterministic when duplicates exist.

## Workstream 2: Enforce Strong Upload Validation for Join and ID Columns

### Problem

After mapping is applied, the system does not guarantee that the selected `equipment_id_column` or `canonical_join_column` still exists. This can lead to apparently successful uploads followed by invalid classification behavior.

### Desired Outcome

Any upload with broken mapping or invalid join configuration should fail immediately with a specific validation error.

### Build Tasks

#### Backend
- After `apply_mapping`, assert that:
  - canonical dataset equipment ID column exists in the mapped dataframe
  - supplementary dataset equipment ID column exists in the mapped dataframe
  - supplementary canonical join column exists in the canonical mapped dataframe
- Validate that required columns are included, not excluded by the mapping grid.
- Return actionable errors such as:
  - `Mapped equipment ID column not found`
  - `Selected canonical join column not found after mapping`
  - `Join column was excluded from mapping`
- Add dataset-level validation metadata if useful for future diagnostics.

#### Frontend
- Disable upload when required mapped targets are empty.
- Add inline validation in the mapping grid for:
  - missing target names
  - duplicate target names where disallowed
  - excluded join/id fields
- Show validation summaries before submit.

#### Testing
- Upload failure tests for broken mappings.
- Tests covering excluded required fields.
- Tests for renamed join columns.

### Acceptance Criteria

- Invalid join/id mappings fail during upload.
- Users receive a clear and specific validation message.
- No broken dataset configuration can proceed to classification.

## Workstream 3: Make Excel Sheet Selection Fully Explicit

### Problem

The current flow still previews the first Excel sheet before the user explicitly selects a sheet. That weakens the contract of explicit sheet interception.

### Desired Outcome

No sheet-dependent schema, preview, or mapping state should be shown until the user explicitly selects a sheet.

### Build Tasks

#### Backend
- Change file inspection behavior for Excel uploads without `sheet_name` so it returns only:
  - file type
  - sheet names
- Do not return preview rows or schema profile for Excel files until a sheet is selected.
- Optionally split endpoints into:
  - `inspect workbook`
  - `inspect sheet`

#### Frontend
- Treat Excel inspection as a two-stage workflow:
  1. workbook detected
  2. sheet selected
- Keep preview, schema profile, mapping suggestions, and derived-column setup hidden until sheet confirmation.
- Prevent modal dismissal from leaving a half-inspected state that implies a sheet was chosen.
- Add explicit retry flow if the user wants to change sheets after preview.

#### Testing
- Verify that workbook inspection returns no preview before selection.
- Verify that UI blocks mapping and upload until a sheet is chosen.
- Verify that changing sheet resets preview/mapping state safely.

### Acceptance Criteria

- Excel uploads provide no sheet-derived preview before explicit selection.
- Users cannot proceed to mapping or upload without selecting a sheet.
- The UX exactly reflects the PRD’s explicit sheet-intercept requirement.

## Workstream 4: Clear Stale Classification State on Project Change

### Problem

When a project has no latest classification run, the UI may keep showing results from a previously viewed project.

### Desired Outcome

Project navigation should always show only data belonging to the current project.

### Build Tasks

#### Frontend
- In project load logic, explicitly set `result` to `null` if there is no `latest_run`.
- Consider resetting `result` immediately when `projectId` changes before the fetch completes.
- Add a loading transition so the previous project’s result does not flash.

#### Testing
- Navigation test from project with run to project without run.
- Navigation test between two projects with different runs.

### Acceptance Criteria

- No stale classification output appears after navigating to another project.
- Result state always matches the currently loaded project.

## Workstream 5: Redesign Classification Run Persistence for Scale

### Problem

The current persistence model stores full result rows and explanation trees directly in JSON columns inside `classification_runs`. This will become heavy and slow as datasets grow.

### Desired Outcome

Classification results should remain queryable, exportable, and explainable without relying on a single oversized JSON row.

### Recommended Target Design

#### Split run metadata from run payloads

Use:
- `classification_runs`
  - run metadata only
  - project id
  - ruleset id/version
  - status
  - summary
  - timestamps
- `classification_run_artifacts`
  - references to persisted files or storage locations
  - rows artifact
  - explanations artifact
  - export artifact
- optionally `classification_run_rows`
  - if row-level querying is needed in-database

#### Preferred persistence strategy

Persist heavy run payloads as files rather than single-row JSON blobs.

Good options:
- CSV or Parquet for result rows
- JSON Lines for explanation payloads
- generated CSV export files for download

### Build Tasks

#### Backend
- Add a run-artifact model or file reference structure.
- Persist classification rows to disk or structured artifact storage.
- Persist explanations separately from summary metadata.
- Keep only summary and references in `classification_runs`.
- Update export endpoint to stream from stored artifacts instead of in-memory JSON columns.
- Consider pagination endpoint for row retrieval from persisted artifacts.

#### Frontend
- Update result fetching to support:
  - summary metadata
  - paginated row views
  - row-level explanation lookup
- Preserve the current UX while changing the data source under the hood.

#### Testing
- Large-run persistence tests.
- Export tests against artifact-backed storage.
- Run retrieval tests with pagination.

### Acceptance Criteria

- Large classification runs do not depend on a single oversized DB JSON payload.
- Export still works.
- Evidence trace remains accessible.
- Run metadata remains fast to query.

## Recommended Implementation Order

### Phase 1: Correctness First

1. Strong upload validation for join/id fields
2. Clear stale classification state on project change
3. Make Excel sheet selection fully explicit

### Phase 2: Data Integrity and Auditability

4. Preserve duplicate supplementary matches

### Phase 3: Scalability

5. Redesign classification run persistence for scale

## Detailed Sprint Plan

### Sprint A

Focus:
- Upload validation
- Stale result clearing
- Excel explicit selection fix

Deliverables:
- backend upload validation errors
- frontend mapping-grid validation
- explicit Excel two-stage inspect flow
- project result reset on navigation

### Sprint B

Focus:
- Duplicate supplementary match preservation
- evidence rendering for multiple matches

Deliverables:
- new backend match aggregation logic
- updated evidence trace model
- export support for aggregated supplementary evidence

### Sprint C

Focus:
- run persistence redesign
- artifact-backed export and retrieval

Deliverables:
- new data model or artifact reference layer
- migration path from current JSON-run storage
- paginated result loading if needed

## Suggested Code Changes by File Area

### Backend likely files to update
- `backend/app/api/routes.py`
- `backend/app/services/dataframe_engine.py`
- `backend/app/models.py`
- `backend/app/schemas.py`
- new artifact or persistence service module

### Frontend likely files to update
- `frontend/src/components/DatasetUploadForm.tsx`
- `frontend/src/components/ResultsPanel.tsx`
- `frontend/src/pages/ProjectPage.tsx`
- `frontend/src/lib/api.ts`
- `frontend/src/types/index.ts`

## Testing Plan

### Backend tests
- invalid mapping upload rejection
- invalid join column rejection
- duplicate supplementary match preservation
- explicit Excel inspection flow behavior
- run export from persisted artifacts

### Frontend tests
- Excel modal blocks preview until sheet selection
- mapping validation blocks invalid submit
- stale result cleared on project switch
- evidence panel shows aggregated supplementary evidence

### End-to-end tests
- canonical upload + supplementary upload + nested rules + classify + export
- project switch with and without prior runs
- duplicate supplementary match scenario

## Definition of Done

All review concerns are considered addressed when:

- duplicate supplementary evidence is preserved rather than overwritten
- broken mapped join/id configurations fail during upload with explicit messages
- Excel uploads do not show preview or mapping state until a sheet is explicitly selected
- project navigation cannot display stale classification output
- classification runs are stored in a scalable format rather than a single oversized JSON payload

## Immediate Next Recommendation

Start with Sprint A.

Reason:
- it removes the most immediate correctness and UX risks
- it is low-to-medium complexity compared with persistence redesign
- it creates a safer baseline before changing matching semantics or storage architecture
