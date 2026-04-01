from __future__ import annotations

import re
from typing import Any

import pandas as pd

from app.schemas import EquipmentIdAuditRecord, EquipmentIdCleaningConfig

BRACKET_PATTERNS = [re.compile(r'\([^()]*\)'), re.compile(r'\[[^\[\]]*\]'), re.compile(r'\{[^{}]*\}')]


def default_cleaning_config() -> dict[str, Any]:
    return EquipmentIdCleaningConfig().model_dump()


def normalize_cleaning_config(config: dict[str, Any] | EquipmentIdCleaningConfig | None) -> EquipmentIdCleaningConfig:
    if isinstance(config, EquipmentIdCleaningConfig):
        return config
    return EquipmentIdCleaningConfig.model_validate(config or {})


def _is_null_like(value: Any) -> bool:
    if isinstance(value, list):
        return len(value) == 0 or all(_is_null_like(item) for item in value)
    return pd.isna(value) or value == ''


def remove_bracketed_content(value: str, bridge_gap_with_dash: bool) -> tuple[str, bool]:
    text = value
    changed = False

    while True:
        matches: list[tuple[int, int]] = []
        for pattern in BRACKET_PATTERNS:
            match = pattern.search(text)
            if match:
                matches.append(match.span())
        if not matches:
            break

        start, end = min(matches, key=lambda item: item[0])
        before = text[:start]
        after = text[end:]
        prev_char = before[-1] if before else ''
        next_char = after[0] if after else ''
        replacement = '-' if bridge_gap_with_dash and prev_char.isalnum() and next_char.isalnum() else ''
        text = before + replacement + after
        changed = True

    return text, changed


def cleanup_separators(value: str) -> str:
    text = re.sub(r'\s*-\s*', '-', value)
    text = re.sub(r'-{2,}', '-', text)
    text = re.sub(r'([/&]){2,}', r'\1', text)
    text = re.sub(r'(^[-/&]+|[-/&]+$)', '', text)
    return text.strip()


def _infer_shorthand(base: str, token: str) -> str | None:
    stripped = token.strip()
    if not stripped or len(stripped) >= len(base):
        return None
    if any(separator in stripped for separator in '-_/'):
        return None
    if re.fullmatch(r'[A-Za-z]+', stripped):
        prefix = re.sub(r'[A-Za-z]+$', '', base)
        return prefix + stripped if prefix and prefix != base else None
    if re.fullmatch(r'\d+', stripped):
        prefix = re.sub(r'\d+$', '', base)
        return prefix + stripped if prefix and prefix != base else None
    return None


def expand_compound_ids(value: str) -> tuple[list[str], bool, bool, list[str]]:
    if '&' not in value and '/' not in value:
        return [value], False, False, []

    tokens = [item.strip() for item in re.split(r'[&/]', value) if item.strip()]
    if len(tokens) <= 1:
        return [value], False, False, []

    expanded = [tokens[0]]
    ambiguous = False
    notes: list[str] = []

    for token in tokens[1:]:
        inherited = _infer_shorthand(tokens[0], token)
        if inherited:
            expanded.append(inherited)
            continue

        if len(token) < len(tokens[0]) and not any(separator in token for separator in '-_/'):
            ambiguous = True
            notes.append(f'Ambiguous shorthand token "{token}" kept as standalone ID')
        expanded.append(token)

    return expanded, True, ambiguous, notes


def transform_equipment_id(value: Any, config: EquipmentIdCleaningConfig) -> tuple[str, list[str], list[str], str, list[str]]:
    raw = '' if _is_null_like(value) else str(value)
    if not config.enabled or not raw:
        return raw, [raw] if raw else [''], [], 'unchanged', []

    change_types: list[str] = []
    notes: list[str] = []
    intermediate = raw

    if config.remove_bracketed_content:
        intermediate, changed = remove_bracketed_content(intermediate, config.bridge_bracket_gap_with_dash)
        if changed:
            change_types.append('bracket_removed')
        intermediate = cleanup_separators(intermediate)

    expanded = [intermediate]
    parse_status = 'cleaned' if change_types else 'unchanged'
    if config.expand_compound_ids:
        expanded, did_expand, ambiguous, expand_notes = expand_compound_ids(intermediate)
        if did_expand:
            change_types.append('expanded_from_compound')
            parse_status = 'expanded'
        if ambiguous:
            parse_status = 'ambiguous'
            change_types.append('ambiguous_parse')
        notes.extend(expand_notes)

    final_ids: list[str] = []
    whitespace_changed = False
    case_changed = False
    for item in expanded:
        next_item = cleanup_separators(item)
        if config.remove_whitespace:
            compacted = re.sub(r'\s+', '', next_item)
            whitespace_changed = whitespace_changed or compacted != next_item
            next_item = compacted
        if config.uppercase:
            upper = next_item.upper()
            case_changed = case_changed or upper != next_item
            next_item = upper
        final_ids.append(next_item)

    if whitespace_changed:
        change_types.append('whitespace_removed')
    if case_changed:
        change_types.append('uppercased')

    deduped = [item for item in dict.fromkeys(final_ids) if item]
    if not deduped:
        deduped = ['']

    if len(change_types) > 1:
        change_types = ['multiple_changes', *[item for item in change_types if item != 'multiple_changes']]

    return intermediate, deduped, list(dict.fromkeys(change_types)), parse_status, notes


def apply_equipment_id_cleaning(
    df: pd.DataFrame,
    equipment_column: str,
    config: dict[str, Any] | EquipmentIdCleaningConfig | None,
) -> tuple[pd.DataFrame, list[EquipmentIdAuditRecord]]:
    cleaning = normalize_cleaning_config(config)
    if equipment_column not in [str(column) for column in df.columns]:
        raise ValueError(f'Equipment ID column "{equipment_column}" not found for cleaning')

    if not cleaning.enabled:
        preview = df.copy()
        preview['equipment_id_raw'] = preview[equipment_column].map(lambda value: '' if _is_null_like(value) else str(value))
        preview['equipment_id_cleaned'] = preview['equipment_id_raw']
        preview['equipment_id_expansion_count'] = 1
        preview['equipment_id_source_row_index'] = list(range(len(preview)))
        preview['equipment_id_parse_status'] = 'unchanged'
        preview['equipment_id_change_types'] = ''
        preview['equipment_id_audit_notes'] = ''
        audits = [
            EquipmentIdAuditRecord(
                source_row_index=int(index),
                equipment_id_raw='' if _is_null_like(row[equipment_column]) else str(row[equipment_column]),
                equipment_id_intermediate='' if _is_null_like(row[equipment_column]) else str(row[equipment_column]),
                equipment_id_final=['' if _is_null_like(row[equipment_column]) else str(row[equipment_column])],
                change_types=[],
                parse_status='unchanged',
                notes=[],
            )
            for index, row in df.iterrows()
        ]
        return preview, audits

    transformed_rows: list[dict[str, Any]] = []
    audits: list[EquipmentIdAuditRecord] = []

    for row_index, (_, row) in enumerate(df.iterrows()):
        row_dict = row.to_dict()
        intermediate, final_ids, change_types, parse_status, notes = transform_equipment_id(row_dict.get(equipment_column), cleaning)
        raw = '' if _is_null_like(row_dict.get(equipment_column)) else str(row_dict.get(equipment_column))

        audits.append(
            EquipmentIdAuditRecord(
                source_row_index=row_index,
                equipment_id_raw=raw,
                equipment_id_intermediate=intermediate,
                equipment_id_final=final_ids,
                change_types=change_types,
                parse_status=parse_status,
                notes=notes,
            )
        )

        for expanded_index, final_id in enumerate(final_ids):
            next_row = dict(row_dict)
            next_row[equipment_column] = final_id
            next_row['equipment_id_raw'] = raw
            next_row['equipment_id_cleaned'] = intermediate
            next_row['equipment_id_expansion_count'] = len(final_ids)
            next_row['equipment_id_source_row_index'] = row_index
            next_row['equipment_id_expansion_index'] = expanded_index
            next_row['equipment_id_parse_status'] = parse_status
            next_row['equipment_id_change_types'] = ', '.join(change_types)
            next_row['equipment_id_audit_notes'] = ' | '.join(notes)
            transformed_rows.append(next_row)

    return pd.DataFrame(transformed_rows), audits
