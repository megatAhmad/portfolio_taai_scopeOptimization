#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
BACKEND_DIR = ROOT / 'backend'
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from app.services.equipment_id_cleaning import apply_equipment_id_cleaning, normalize_cleaning_config, transform_equipment_id  # noqa: E402


def load_cases(path: Path) -> list[dict[str, Any]]:
    data = json.loads(path.read_text())
    if not isinstance(data, list):
        raise ValueError('Case file must contain a JSON array')
    return data


def compare_sequence(name: str, actual: list[Any], expected: list[Any], failures: list[str]) -> None:
    if actual != expected:
        failures.append(f'{name}: expected {expected!r}, got {actual!r}')


def compare_set_contains(name: str, actual: list[str], expected: list[str], failures: list[str]) -> None:
    missing = [item for item in expected if item not in actual]
    if missing:
        failures.append(f'{name}: missing expected items {missing!r} from {actual!r}')


def run_transform_case(case: dict[str, Any]) -> tuple[list[str], list[str]]:
    failures: list[str] = []
    config = normalize_cleaning_config(case.get('config'))
    raw_input = case.get('input')
    intermediate, final_ids, change_types, parse_status, notes = transform_equipment_id(raw_input, config)
    expected = case.get('expected', {})
    details = [
        f"  raw: {raw_input!r}",
        f"  intermediate: {intermediate!r}",
        f"  final_ids: {final_ids!r}",
    ]

    if 'intermediate' in expected and intermediate != expected['intermediate']:
        failures.append(f"intermediate: expected {expected['intermediate']!r}, got {intermediate!r}")
    if 'final_ids' in expected:
        compare_sequence('final_ids', final_ids, expected['final_ids'], failures)
    if 'change_types' in expected:
        compare_sequence('change_types', change_types, expected['change_types'], failures)
    if 'change_types_contains' in expected:
        compare_set_contains('change_types_contains', change_types, expected['change_types_contains'], failures)
    if 'parse_status' in expected and parse_status != expected['parse_status']:
        failures.append(f"parse_status: expected {expected['parse_status']!r}, got {parse_status!r}")
    if 'notes_contains' in expected:
        for snippet in expected['notes_contains']:
            if not any(snippet in note for note in notes):
                failures.append(f'notes_contains: expected a note containing {snippet!r}, got {notes!r}')

    return failures, details


def run_dataframe_case(case: dict[str, Any]) -> tuple[list[str], list[str]]:
    failures: list[str] = []
    equipment_column = case['equipment_column']
    frame = pd.DataFrame(case.get('rows', []))
    transformed, audits = apply_equipment_id_cleaning(frame, equipment_column, case.get('config'))
    expected = case.get('expected', {})
    raw_ids = frame[equipment_column].astype(str).tolist() if equipment_column in frame.columns else []
    final_ids = transformed[equipment_column].astype(str).tolist() if equipment_column in transformed.columns else []
    details = [
        f"  raw_ids: {raw_ids!r}",
        f"  emitted_ids: {final_ids!r}",
    ]

    if 'row_count' in expected and len(transformed) != expected['row_count']:
        failures.append(f"row_count: expected {expected['row_count']!r}, got {len(transformed)!r}")

    if 'final_ids' in expected:
        compare_sequence('final_ids', final_ids, expected['final_ids'], failures)

    if 'source_row_indexes' in expected:
        compare_sequence(
            'source_row_indexes',
            transformed['equipment_id_source_row_index'].astype(int).tolist(),
            expected['source_row_indexes'],
            failures,
        )

    if 'expansion_counts' in expected:
        compare_sequence(
            'expansion_counts',
            transformed['equipment_id_expansion_count'].astype(int).tolist(),
            expected['expansion_counts'],
            failures,
        )

    for column, values in expected.get('copied_columns', {}).items():
        compare_sequence(f'copied_columns.{column}', transformed[column].astype(str).tolist(), values, failures)

    if expected.get('single_final_id_per_row'):
        duplicates = transformed[equipment_column].astype(str).tolist()
        if any(',' in value or '/' in value or '&' in value for value in duplicates):
            failures.append(f'single_final_id_per_row: expected one final ID per row, got {duplicates!r}')

    expected_audit_count = expected.get('audit_count')
    if expected_audit_count is not None and len(audits) != expected_audit_count:
        failures.append(f'audit_count: expected {expected_audit_count!r}, got {len(audits)!r}')

    return failures, details


def run_case(case: dict[str, Any]) -> tuple[list[str], list[str]]:
    case_type = case.get('type', 'transform')
    if case_type == 'transform':
        return run_transform_case(case)
    if case_type == 'dataframe':
        return run_dataframe_case(case)
    return [f"Unsupported case type: {case_type!r}"], []


def main() -> int:
    parser = argparse.ArgumentParser(description='Run external equipment ID cleaning checks')
    parser.add_argument(
        '--cases',
        default=str(Path(__file__).with_name('equipment_id_cleaning_cases.json')),
        help='Path to JSON case file',
    )
    parser.add_argument('--case', help='Run one case by id')
    args = parser.parse_args()

    case_path = Path(args.cases).resolve()
    cases = load_cases(case_path)
    if args.case:
        cases = [case for case in cases if case.get('id') == args.case]
        if not cases:
            print(f'No case found with id {args.case!r}')
            return 1

    passed = 0
    failed = 0
    for case in cases:
        failures, details = run_case(case)
        if failures:
            failed += 1
            print(f"FAIL {case.get('id', '<missing-id>')}")
            print(f"Description: {case.get('description', '')}")
            for item in details:
                print(item)
            for item in failures:
                print(f'  - {item}')
            print()
        else:
            passed += 1
            print(f"PASS {case.get('id', '<missing-id>')}")
            for item in details:
                print(item)

    print()
    print(f'{passed} passed, {failed} failed')
    return 1 if failed else 0


if __name__ == '__main__':
    raise SystemExit(main())
