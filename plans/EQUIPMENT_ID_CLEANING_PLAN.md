# Equipment ID Cleaning And Expansion Plan

## Goal

Introduce a configurable preprocessing stage for equipment IDs before matching so users can:

- clean noisy equipment IDs during dataset intake
- expand one source row into multiple equipment IDs when compound IDs are present
- review the transformed dataset before upload is finalized
- audit exactly which IDs were edited or expanded

This preprocessing must be configurable per dataset and must run before canonical-to-supplementary matching.

## Core Principles

- Preserve the original source value at all times.
- Make transformations visible before they affect matching.
- Be conservative when parsing ambiguous shorthand.
- Duplicate rows only when expansion is intentional and traceable.
- Keep cleaning configuration separate from matching strategy configuration.

## Proposed Processing Pipeline

For the selected equipment ID column, process values in this order:

1. Preserve `equipment_id_raw`.
2. Remove bracketed content from `()`, `[]`, and `{}`.
3. Apply bracket-gap replacement logic:
   - if alphanumeric content exists on both sides of the removed bracket block, replace the removed block with `-`
   - otherwise remove the block entirely
4. Parse compound IDs joined by `&` or `/`.
5. Expand compound IDs into one or more output IDs.
6. Normalize separator artifacts created by cleaning or expansion.
7. Remove whitespace at the end.
8. Emit one row per final equipment ID.

Whitespace removal is intentionally last so spacing remains available as a parsing clue for compound IDs.

## Supported Cleaning Rules

### 1. Bracket Removal

Supported bracket types:

- `(...)`
- `[...]`
- `{...}`

Examples:

- `101A(CC)` -> `101A`
- `101A(CC)B` -> `101A-B`
- `101A [OLD] B` -> `101A-B`
- `(TEMP)101A` -> `101A`

Additional cleanup after bracket removal:

- collapse repeated `-`
- trim leading and trailing separators
- avoid leaving malformed `/-` or `&-` fragments

### 2. Compound ID Expansion

Supported delimiters:

- `&`
- `/`

Expansion categories:

- Fully explicit IDs:
  - `101A & 101B` -> `101A`, `101B`
  - `101A/101B` -> `101A`, `101B`
- Shorthand inherited IDs:
  - `101A&B` -> `101A`, `101B`
  - `101A/B` -> `101A`, `101B`
  - `P-101A/B/C` -> `P-101A`, `P-101B`, `P-101C`
- Totally different IDs:
  - `101A-CC/405R-BL2` -> `101A-CC`, `405R-BL2`

### 3. Whitespace Removal

Whitespace is removed only after expansion logic completes.

Examples:

- `101 A` -> `101A`
- `101A / 101B` -> `101A`, `101B`

## Parsing Heuristics

The parser should classify each compound segment as either:

- explicit standalone ID
- shorthand fragment that inherits structure from the first token
- ambiguous token requiring warning

### Inheritance Heuristic

Treat a later token as shorthand only if all are true:

- the token is shorter than the first token
- the token does not already look like a complete ID
- the first token has a recognizable shared prefix plus varying suffix

Examples:

- `101A&B`:
  - first token: `101A`
  - shared prefix: `101`
  - variants: `A`, `B`
- `101A & 101B`:
  - both tokens are already complete
  - do not inherit
- `101A-CC/405R-BL2`:
  - second token is structurally independent
  - do not inherit

### Ambiguity Policy

If parsing confidence is low:

- do not silently invent aggressive transformations
- prefer a conservative split or no inheritance
- emit a warning for audit and review

Examples that should likely be flagged:

- `101-1/2`
- `P-01A/B-2`
- `101A/B/C-D`

## Data Model Changes

### New Config Model

Add a dedicated per-dataset config separate from `matching_config`.

Suggested shape:

```ts
type EquipmentIdCleaningConfig = {
  enabled: boolean
  remove_bracketed_content: boolean
  bridge_bracket_gap_with_dash: boolean
  expand_compound_ids: boolean
  remove_whitespace: boolean
  uppercase: boolean
}
```

Suggested default:

```ts
{
  enabled: false,
  remove_bracketed_content: true,
  bridge_bracket_gap_with_dash: true,
  expand_compound_ids: true,
  remove_whitespace: true,
  uppercase: false
}
```

### New Preview/Audit Output

The dataset inspection response should include transformed preview data and audit records when cleaning is enabled.

Suggested additions:

```ts
type EquipmentIdAuditRecord = {
  source_row_index: number
  equipment_id_raw: string
  equipment_id_intermediate?: string
  equipment_id_final: string[]
  change_types: string[]
  parse_status: 'unchanged' | 'cleaned' | 'expanded' | 'ambiguous'
  notes?: string[]
}
```

Suggested response additions:

- `transformed_preview_rows`
- `equipment_id_audit`
- `transformed_row_count`
- `changed_row_count`

### Persistence

Persist the cleaning config with the dataset record so rebuilds and re-runs are deterministic.

Optional future enhancement:

- persist a lightweight audit summary with the dataset metadata

## Backend Plan

### Schema Updates

Update backend schema definitions to support:

- `EquipmentIdCleaningConfig`
- audit response payloads for inspection
- dataset persistence of the cleaning config

Files likely affected:

- `backend/app/schemas.py`
- `backend/app/models.py`
- Alembic migration for the new JSON column

### Service Layer

Add a preprocessing module dedicated to equipment ID cleaning.

Suggested new service responsibilities:

- remove bracketed content
- normalize separators
- split compound IDs
- detect shorthand inheritance
- expand rows
- build audit records

Suggested file:

- `backend/app/services/equipment_id_cleaning.py`

### Intake Flow Integration

Update dataset inspection flow to optionally apply cleaning in preview mode.

Suggested flow during inspect:

1. read raw file
2. apply mapping
3. resolve selected equipment ID column
4. apply cleaning config if enabled
5. return transformed preview rows and audit results

Update dataset upload flow to apply the same cleaning configuration when finalizing the dataset.

### Matching Integration

Cleaning and expansion must happen before matching.

Suggested matching flow:

1. load dataset
2. apply mapping
3. apply derived columns
4. apply equipment ID cleaning and row expansion
5. run canonical-to-supplementary matching using the cleaned expanded IDs

This should apply to both canonical and supplementary datasets so both sides can be normalized consistently.

## Frontend Plan

### Dataset Intake UI

Add a new panel in the upload form for equipment ID cleaning.

Suggested controls:

- `Enable equipment ID cleaning`
- `Remove bracketed content`
- `Bridge removed bracket gaps with dash`
- `Expand IDs containing & or /`
- `Remove whitespace at end`
- `Uppercase normalized IDs`

File likely affected:

- `frontend/src/components/DatasetUploadForm.tsx`

### Uploaded Data Review Section

Add a review table visible after inspection and before upload finalization.

Purpose:

- show the transformed dataset as it will be used for matching
- let users confirm row duplication and final IDs

Suggested columns:

- source row index
- original equipment ID
- cleaned/intermediate equipment ID
- final equipment ID
- expansion count
- parse status

Suggested behavior:

- always visible once inspection is complete
- paginated or truncated if preview size is large
- highlights rows that changed

### ID Audit Section

Add a focused audit section showing only changed rows.

Purpose:

- let users self-audit edits and expansions without reading the whole preview

Suggested columns:

- source row index
- raw equipment ID
- final expanded IDs
- change types
- parse status
- notes

Suggested filters:

- changed rows only
- expanded only
- ambiguous only

Suggested behavior:

- hidden when no changes exist
- visible when at least one row was changed or expanded

## Auditability Requirements

Each transformed row should preserve traceability back to its origin.

Suggested metadata:

- `source_row_index`
- `equipment_id_raw`
- `equipment_id_cleaned`
- `equipment_id_final`
- `expansion_group_id`
- `expansion_index`
- `parse_status`
- `change_types`

This traceability should be available both in inspection preview and downstream matching/debug views where practical.

## Acceptance Examples

### Bracket Removal

- `101A(CC)` -> `101A`
- `101A(CC)B` -> `101A-B`
- `101A [OLD] B` -> `101A-B`
- `{TMP}101A` -> `101A`

### Explicit Expansion

- `101A & 101B` -> `101A`, `101B`
- `101A/101B` -> `101A`, `101B`

### Shorthand Expansion

- `101A&B` -> `101A`, `101B`
- `101A/B` -> `101A`, `101B`
- `P-101A/B/C` -> `P-101A`, `P-101B`, `P-101C`

### Different IDs

- `101A-CC/405R-BL2` -> `101A-CC`, `405R-BL2`

### Final Whitespace Cleanup

- `101 A` -> `101A`
- ` 101A / 101B ` -> `101A`, `101B`

### Ambiguity Cases

These should be flagged for review:

- `101-1/2`
- `P-01A/B-2`
- `101A/B/C-D`

## Rollout Phases

### Phase 1

Deliver the safest high-value foundation:

- cleaning config in UI and backend
- bracket removal
- explicit `&` and `/` splitting
- final whitespace removal
- uploaded data review section
- ID audit section

### Phase 2

Add shorthand inheritance support:

- `101A&B`
- `101A/B`
- repeated suffix inheritance such as `P-101A/B/C`

### Phase 3

Improve ambiguity handling and review support:

- parse warnings
- ambiguous-only filters
- richer audit notes
- optional confidence scoring

## Testing Plan

### Backend Unit Tests

Add tests for:

- bracket removal logic
- bracket dash-bridge logic
- explicit splitting
- shorthand inheritance
- structurally different ID splitting
- whitespace removal at end
- row duplication behavior
- audit record generation
- ambiguity flagging

### Integration Tests

Add tests for:

- inspection preview with cleaning disabled
- inspection preview with cleaning enabled
- upload finalization with expanded rows
- matching behavior after cleaning
- canonical and supplementary normalization consistency

### Frontend Tests

Add tests for:

- cleaning config form behavior
- transformed data preview rendering
- audit table rendering
- changed-only and ambiguous-only filters
- upload payload includes cleaning config

## Open Questions

- Should uppercase normalization be enabled by default or remain optional?
- Should ambiguous IDs block upload or only warn?
- Should expanded rows be persisted physically or regenerated on demand from raw input plus config?
- Should the transformed equipment ID replace the mapped source column, or should it live beside the original in a dedicated normalized column?
- How much preview data should be shown before pagination or truncation is required?

## Recommendation

Implement Phase 1 first and keep the parser conservative.

That gives users immediate value with:

- visible cleanup
- safer matching inputs
- row expansion for clear compound IDs
- self-audit tooling before upload

Then add shorthand inheritance only after the preview and audit experience is in place, so users can verify the parser's behavior with confidence.
