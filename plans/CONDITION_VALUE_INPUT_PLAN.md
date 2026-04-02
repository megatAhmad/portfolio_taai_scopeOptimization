# Condition Value Input Plan

## Purpose

This plan improves the rule builder condition editor so value entry matches the selected operator more naturally. The current UI exposes generic value fields and does not guide users toward the correct number or shape of inputs. The goal is to make single-value operators feel simple by default while still supporting multi-value conditions in a controlled way.

## Problem Summary

The current logic builder allows condition values to feel broader and less structured than they should.

Current issues:

- The UI always presents value editing in a generic way rather than adapting strongly to the selected operator
- Single-value operators do not feel clearly limited to one value
- `BETWEEN` needs two inputs, but most other operators do not
- `CONTAINS ANY` and `CONTAINS ALL` imply multiple values, but the current input model does not express that cleanly
- Users can be left guessing whether to type one value, comma-separated text, or multiple values in an inconsistent format

This increases friction and makes operator intent less obvious.

## Desired UX

The condition editor should behave according to operator semantics.

### Default behavior

For most operators, show exactly one value input.

Applies to:

- `=`
- `!=`
- `CONTAINS`
- `IN`
- `<`
- `>`
- `<=`
- `>=`

### `BETWEEN`

Show exactly two value inputs:

- first value
- second value

This is the only operator that should expose two fixed input fields by default.

### `CONTAINS ANY` and `CONTAINS ALL`

Use a list-based value editor where:

- each row accepts exactly one value
- the UI starts with one row by default
- users can add another row with `+`
- users can remove a row with `-`
- the placeholder can indicate row number or example content if useful
- pasting comma-separated values can optionally split into multiple rows for convenience

This keeps the UI structured while still allowing multiple accepted values.

## Product Recommendation

Do not use a single free-form comma-separated text field as the primary UI.

Recommended approach:

- each value gets its own row or input section
- comma-separated paste is treated as a convenience enhancement, not the core interaction

Reason:

- easier to validate
- clearer to users
- avoids ambiguity around whitespace and escaped commas
- makes future chips/tags UI possible without changing the underlying concept

## Data Model Recommendation

The current condition node shape is too limited for clean multi-value support.

Current shape:

- `value`
- `secondary_value`

Recommended extension:

- keep `value`
- keep `secondary_value`
- add `values?: string[]`

Suggested semantics:

- single-value operators use `value`
- `BETWEEN` uses `value` and `secondary_value`
- `CONTAINS ANY` and `CONTAINS ALL` use `values`

This preserves backward compatibility while allowing explicit multi-value support.

## Scope of Change

The change affects:

- frontend condition editor UX
- frontend AST typing
- frontend normalization logic
- backend rule schema validation
- backend rule evaluation logic for multi-value operators
- optional trace/explanation behavior if values should be shown more explicitly

## Implementation Workstreams

### Workstream 1: Clarify operator-to-input behavior

#### Goal

Define a single source of truth for which operators expect which input shape.

#### Build

Add a small operator metadata layer in the frontend and backend.

Suggested model:

- `single`
- `between`
- `multi_list`

Suggested mappings:

- `BETWEEN` -> `between`
- `CONTAINS ANY` -> `multi_list`
- `CONTAINS ALL` -> `multi_list`
- everything else -> `single`

#### Acceptance criteria

- The app can reliably determine which editor to show for each operator
- Operator changes can immediately reshape the value editor

### Workstream 2: Extend AST typing for multi-value conditions

#### Goal

Make multi-value conditions explicit in the schema rather than overloading a single string field.

#### Frontend build

Update condition typings in:

- `frontend/src/types/index.ts`

Add:

- `values?: string[]`

Update normalization behavior in the rule builder so:

- existing saved rules still load correctly
- missing `values` defaults safely
- switching operators preserves or resets values appropriately

#### Backend build

Update condition schema in:

- `backend/app/schemas.py`

Add:

- `values: list[str] | None = None`

Keep compatibility with rulesets that only use:

- `value`
- `secondary_value`

#### Acceptance criteria

- Existing rulesets remain valid
- New multi-value conditions can be persisted without schema errors

### Workstream 3: Replace the current generic value UI

#### Goal

Render the correct input editor for the selected operator.

#### Frontend build

In `frontend/src/components/RuleBuilder.tsx`:

- for single-value operators:
  - show one input only
- for `BETWEEN`:
  - show two inputs only
- for `CONTAINS ANY` and `CONTAINS ALL`:
  - show repeatable one-value-per-row inputs
  - include add/remove controls
  - ensure at least one row exists

Recommended UX details:

- when switching from single-value to multi-value:
  - seed the first row from existing `value` if present
- when switching from multi-value to single-value:
  - keep the first value as `value`
- when switching to `BETWEEN`:
  - use the first available value as `value`
  - use an empty string for `secondary_value` if missing

#### Acceptance criteria

- Single-value operators never show unnecessary extra inputs
- `BETWEEN` always shows exactly two inputs
- `CONTAINS ANY` and `CONTAINS ALL` support multiple rows with one value per row

### Workstream 4: Add comma-splitting convenience

#### Goal

Support fast data entry without making comma-separated text the primary data model.

#### Build

For multi-value rows:

- if the user pastes comma-separated text into a row, split it into multiple rows
- trim whitespace around each value
- discard empty segments

Optional:

- if the user types commas manually, split on blur instead of on every keystroke

This keeps editing stable and avoids cursor-jump issues.

#### Acceptance criteria

- Pasting `pump, motor, valve` produces three rows
- Each resulting row contains one value

### Workstream 5: Update backend evaluation logic

#### Goal

Ensure rule execution uses the new multi-value structure correctly.

#### Build

Update condition evaluation logic in:

- `backend/app/services/dataframe_engine.py`

Expected behavior:

- `CONTAINS ANY` checks whether the actual value matches any item in `values`
- `CONTAINS ALL` checks whether the actual value matches all items in `values`
- if `values` is missing for older data, fall back safely to `value`

Validation rules:

- `BETWEEN` should require two values at evaluation time
- `CONTAINS ANY` and `CONTAINS ALL` should require at least one non-empty item

#### Acceptance criteria

- Multi-value operators evaluate correctly
- Older rulesets still evaluate correctly

### Workstream 6: Improve summaries and traces

#### Goal

Make visual summaries and explanation output reflect multi-value conditions clearly.

#### Build

Update frontend summary rendering in the rule builder so:

- single-value conditions show one value
- `BETWEEN` shows both values
- multi-value conditions show a concise joined summary

Update trace or result rendering if needed so expected values are understandable when the operator uses a list.

Possible output examples:

- `equipment_type CONTAINS ANY pump, motor, valve`
- `shutdown_days BETWEEN 5 and 14`

#### Acceptance criteria

- Node summaries remain compact and understandable
- Evidence views do not hide how many values were actually configured

## Migration and Compatibility Strategy

This should be a backward-compatible change.

### Existing rulesets

Existing rulesets that only contain:

- `value`
- `secondary_value`

should continue to load and run without edits.

### New rulesets

New rulesets may store:

- `values`

for multi-value operators.

### Operator switching behavior

Switching operators in the editor should not produce invalid hidden state.

Recommended normalization rules:

- `single` operators keep one value in `value`
- `between` uses `value` and `secondary_value`
- `multi_list` uses `values`
- stale fields may remain in the payload for compatibility, but the active operator should determine which fields are used

If preferred, inactive fields can also be cleared during normalization.

## Risks and Mitigations

### Risk 1: Breaking existing saved rules

Mitigation:

- Keep old fields supported
- Normalize old payloads into the new editor safely
- Fall back from `values` to `value` when needed

### Risk 2: Confusing operator switching

Mitigation:

- Define explicit conversion behavior between single, between, and multi-list modes
- Seed new mode values from the old mode when possible

### Risk 3: Ambiguity around comma handling

Mitigation:

- Treat comma splitting as a paste convenience, not the primary data model
- Split on blur or paste rather than every keystroke

### Risk 4: Backend/frontend drift

Mitigation:

- Update frontend types and backend schemas in the same change
- Verify save/load/evaluation using a real ruleset round trip

## Testing Plan

### Frontend tests

- Switching operators updates the visible input shape correctly
- Single-value operators show one input only
- `BETWEEN` shows two inputs only
- `CONTAINS ANY` and `CONTAINS ALL` support add/remove value rows
- Pasting comma-separated text expands into multiple rows
- Saving and reloading preserves multi-value conditions

### Backend tests

- Old rulesets without `values` remain valid
- `CONTAINS ANY` evaluates correctly with `values`
- `CONTAINS ALL` evaluates correctly with `values`
- `BETWEEN` requires and uses two values
- Empty multi-value lists are handled safely

### Manual verification

- Create a single-value condition and confirm only one input is shown
- Switch to `BETWEEN` and confirm exactly two inputs appear
- Switch to `CONTAINS ANY` and add three values
- Paste comma-separated text into a multi-value row and confirm it splits
- Save, reload, and run classification using the new operators

## Acceptance Criteria

This work is complete when:

- Single-value operators default to exactly one value input
- `BETWEEN` is the only operator with two fixed value inputs
- `CONTAINS ANY` and `CONTAINS ALL` support multiple one-value rows
- Comma-separated paste can expand into multiple rows
- The AST remains backward compatible
- Rule evaluation continues to work for both old and new rulesets

## Recommended Next Action

Implement the data model extension and operator-aware editor in the same change so the UX and persisted AST stay aligned.
