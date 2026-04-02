# Equipment ID Cleaning External Harness

This folder contains an external test harness for equipment ID cleaning and expansion.

It stays outside the main platform flow, but imports and runs the exact same shared functions used by the backend:

- `app.services.equipment_id_cleaning.transform_equipment_id`
- `app.services.equipment_id_cleaning.apply_equipment_id_cleaning`

## Quick Start

Run all cases:

```bash
./backend/.venv/bin/python external_tests/equipment_id_cleaning/run_equipment_id_cleaning_checks.py
```

Run one case:

```bash
./backend/.venv/bin/python external_tests/equipment_id_cleaning/run_equipment_id_cleaning_checks.py --case shorthand-slash-001
```

Use a custom case file:

```bash
./backend/.venv/bin/python external_tests/equipment_id_cleaning/run_equipment_id_cleaning_checks.py --cases /path/to/cases.json
```

## Files

- `equipment_id_cleaning_cases.json`
  Starter scenarios for transform and dataframe-expansion behavior.
- `run_equipment_id_cleaning_checks.py`
  Small runner that prints pass/fail output, the raw ID input, and the resulting transformed IDs.

## Case Types

### Transform Cases

Use these for direct checks of a single equipment ID string through `transform_equipment_id`.

### Dataframe Cases

Use these for row-expansion checks through `apply_equipment_id_cleaning`.

These are useful for confirming that one source row expands into multiple emitted rows and that each emitted row contains only one final ID.
