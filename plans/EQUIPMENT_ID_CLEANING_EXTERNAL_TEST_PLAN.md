# Equipment ID Cleaning External Test Plan

## Purpose

Provide a fast external test workflow for the equipment ID cleaning and expansion logic without embedding the test tool inside the main platform.

The external test tool should call the same cleaning function used by the platform so behavior stays aligned.

Primary target function:

- `app.services.equipment_id_cleaning.transform_equipment_id`

Secondary target for row duplication tests:

- `app.services.equipment_id_cleaning.apply_equipment_id_cleaning`

## Goals

- Add new scenarios quickly.
- Record expected outcomes beside each scenario.
- Run all scenarios in one pass.
- See pass or fail immediately.
- Keep the test harness outside the main product flow.

## Recommended External Test Harness Shape

Build a small external runner that:

1. loads a scenario file
2. imports the shared cleaning function from the platform codebase
3. executes each scenario
4. compares actual vs expected
5. prints a compact pass/fail summary

Recommended files outside the main platform:

- `equipment_id_cleaning_cases.json`
- `run_equipment_id_cleaning_checks.py`

The external runner should depend on the platform codebase only for the shared function import.

## Scenario File Format

Use a flat JSON array so adding new scenarios is easy.

Suggested format:

```json
[
  {
    "id": "bracket-bridge-001",
    "description": "Bracket content removed and gap bridged with dash",
    "input": "101A(CC)B",
    "config": {
      "enabled": true
    },
    "expected": {
      "intermediate": "101A-B",
      "final_ids": ["101A-B"],
      "change_types": ["bracket_removed"],
      "parse_status": "cleaned"
    }
  }
]
```

## Minimum Assertions Per Scenario

Each scenario should validate:

- `intermediate`
- `final_ids`
- `parse_status`

Optional but recommended:

- `change_types`
- `notes`

If `change_types` order is unstable, compare as sets instead of ordered arrays.

## Quick Run Workflow

1. Add or edit one scenario in the JSON file.
2. Run the external script.
3. Review pass/fail output.
4. If failed, inspect:
   - input
   - expected
   - actual
5. Fix either:
   - the expected outcome
   - the parser logic

## Output Format Recommendation

Keep the runner output compact and readable.

Recommended summary:

```text
PASS bracket-bridge-001
PASS explicit-split-001
FAIL shorthand-ambiguous-001

Expected final_ids: ['101A', '101B']
Actual final_ids:   ['101A', 'B']

12 passed, 1 failed
```

## Core Scenario Groups

### Group 1. No Change

Purpose:

- verify ordinary IDs pass through unchanged

Scenarios:

- `101A`
- `405R-BL2`
- `P-101-A1`

Expected:

- final output equals input
- `parse_status = unchanged`
- no change types

### Group 2. Bracket Removal

Purpose:

- verify bracket stripping works for all supported bracket types

Scenarios:

- `101A(CC)`
- `101A[CC]`
- `101A{CC}`
- `(TMP)101A`

Expected:

- bracketed content removed
- no unexpected separators

### Group 3. Bracket Gap Bridging

Purpose:

- verify removed bracket blocks become `-` only when content exists on both sides

Scenarios:

- `101A(CC)B` -> `101A-B`
- `ABC[OLD]DEF` -> `ABC-DEF`
- `(OLD)ABC` -> `ABC`
- `ABC(OLD)` -> `ABC`

### Group 4. Explicit Split

Purpose:

- verify full IDs joined by `&`, `/`, or `,` split cleanly

Scenarios:

- `101A & 101B`
- `101A/101B`
- `101A / 101B`
- `101A,101B`
- `101A-CC/405R-BL2`

Expected:

- two final IDs
- no inheritance applied
- `parse_status = expanded`

### Group 5. Shorthand Inheritance

Purpose:

- verify short suffix tokens inherit the shared prefix

Scenarios:

- `101A&B` -> `101A`, `101B`
- `101A/B` -> `101A`, `101B`
- `101A,B` -> `101A`, `101B`
- `P-101A/B/C` -> `P-101A`, `P-101B`, `P-101C`

Expected:

- inherited IDs are reconstructed correctly

### Group 6. Structurally Different IDs

Purpose:

- verify unrelated IDs joined by `/` or `&` stay standalone

Scenarios:

- `101A-CC/405R-BL2`
- `AUX-22A / PMP-03B`

Expected:

- split into complete IDs
- no inheritance

### Group 7. Whitespace Removal At End

Purpose:

- verify whitespace is removed only from final emitted IDs

Scenarios:

- `101 A`
- ` 101A / 101B `
- ` 101A , 101B `
- `101 A & B`

Expected:

- no spaces remain in final IDs
- split logic still works

### Group 8. Ignore Alpha-Only Expansions

Purpose:

- verify final emitted IDs without digits are dropped

Scenarios:

- `101A/ABC`
- `101A,ABC`
- `ONLYTEXT`
- `PUMPA/PUMPB`

Expected:

- any final emitted ID with no digits is removed
- shorthand still works if the final reconstructed ID gains digits
- notes can mention ignored alpha-only expansions

### Group 9. Ambiguous Cases

Purpose:

- verify ambiguous structures are flagged instead of aggressively transformed

Scenarios:

- `101-1/2`
- `P-01A/B-2`
- `101A/B/C-D`

Expected:

- `parse_status = ambiguous` where applicable
- notes present when ambiguity is detected

### Group 10. Config Toggle Cases

Purpose:

- verify each config flag affects behavior correctly

Scenarios:

- cleaning disabled
- bracket removal disabled
- expansion disabled
- whitespace removal disabled
- uppercase enabled

Expected:

- output changes only when the relevant flag is enabled

## Row Expansion Test Cases

For `apply_equipment_id_cleaning`, validate row duplication behavior.

Input dataframe examples:

- one row with `101A&B`
- one row with `101A,B`
- one row with `101A-CC/405R-BL2`

Assertions:

- row count increases correctly
- duplicated rows keep the same non-ID columns
- final equipment ID differs per expanded row
- `equipment_id_source_row_index` is stable
- `equipment_id_expansion_count` is correct
- each expanded row should carry only one final ID, not the full list repeated in every row
- external audit assertions should validate expanded-row behavior separately from grouped source-level audit records

## Suggested Scenario Fields

Each case should support:

```json
{
  "id": "string",
  "description": "string",
  "input": "string",
  "config": {
    "enabled": true,
    "remove_bracketed_content": true,
    "bridge_bracket_gap_with_dash": true,
    "expand_compound_ids": true,
    "remove_whitespace": true,
    "uppercase": false
  },
  "expected": {
    "intermediate": "string",
    "final_ids": ["string"],
    "change_types": ["string"],
    "parse_status": "unchanged | cleaned | expanded | ambiguous",
    "notes_contains": ["string"]
  }
}
```

## Failure Review Checklist

When a scenario fails, check:

1. Was the expected result actually correct?
2. Did config flags match the intended behavior?
3. Did the parser over-inherit shorthand?
4. Did the parser fail to split explicit standalone IDs?
5. Did whitespace removal happen too early?
6. Did bracket cleanup create malformed separators?
7. Was an alpha-only emitted ID supposed to be ignored?

## Regression Pack

Keep a small must-pass regression pack that runs first.

Recommended core set:

- `101A(CC)B`
- `101A&B`
- `101A,B`
- `101A & 101B`
- `101A-CC/405R-BL2`
- ` 101 A / 101B `
- `101A/ABC`
- `101-1/2`

This gives quick confidence after parser changes.

## Recommended Run Cadence

Run the external harness:

- after every parser change
- before merging changes to cleaning logic
- after adding a new scenario rule
- whenever a user reports a bad expansion

## Nice-To-Have Enhancements

For the external tool, consider adding:

- `--case <id>` to run one scenario
- `--changed-only` to rerun recently edited cases
- `--json` output for CI
- CSV export of failures

## Recommendation

Start with:

- one JSON scenario file
- one lightweight Python runner
- one row-expansion test section

That will give you the fastest feedback loop while keeping the test utility outside the platform itself and still aligned to the exact same cleaning functions.

## Post-Implementation Corrections

The external harness should now reflect the current implemented behavior:

- compound splitting supports `,` in addition to `&` and `/`
- whitespace removal happens at the end
- alpha-only emitted expansions are dropped after final normalization
- shorthand cases like `101A/B` and `101A,B` should still resolve to `101A` and `101B`
- row-expansion assertions should verify one final ID per emitted row
