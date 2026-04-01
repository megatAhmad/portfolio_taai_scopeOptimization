from __future__ import annotations

from datetime import datetime
from difflib import SequenceMatcher
from pathlib import Path
from typing import Any

import pandas as pd

from app.schemas import ColumnProfile, MappingEntry, RuleConditionNode, RuleGroupNode, RuleSetAst


def read_dataset(path: str, file_name: str, sheet_name: str | None = None) -> pd.DataFrame:
    ext = Path(file_name).suffix.lower()
    if ext == '.csv':
        return pd.read_csv(path)
    if ext in {'.xlsx', '.xls'}:
        if not sheet_name:
            raise ValueError('Excel uploads require an explicit sheet selection')
        return pd.read_excel(path, sheet_name=sheet_name)
    raise ValueError(f'Unsupported file type: {ext}')


def inspect_upload(upload, sheet_name: str | None = None) -> tuple[str, list[str], pd.DataFrame | None]:
    upload.file.seek(0)
    ext = Path(upload.filename).suffix.lower()
    if ext == '.csv':
        return 'csv', [], pd.read_csv(upload.file)
    if ext in {'.xlsx', '.xls'}:
        excel = pd.ExcelFile(upload.file)
        available = list(excel.sheet_names)
        if not sheet_name:
            return 'excel', available, None
        if sheet_name not in available:
            raise ValueError(f'Sheet "{sheet_name}" not found')
        return 'excel', available, pd.read_excel(excel, sheet_name=sheet_name)
    raise ValueError(f'Unsupported file type: {ext}')


def normalize_null(value: Any) -> bool:
    if isinstance(value, list):
        return len(value) == 0 or all(normalize_null(item) for item in value)
    return pd.isna(value) or value == ''


def normalize_text(value: Any) -> str:
    text = '' if value is None else str(value)
    return ''.join(ch.lower() for ch in text.strip() if ch.isalnum())


def infer_series_type(series: pd.Series) -> str:
    non_null = series.dropna()
    if non_null.empty:
        return 'empty'
    if pd.to_numeric(non_null, errors='coerce').notna().mean() > 0.8:
        return 'numeric'
    if pd.to_datetime(non_null, errors='coerce', format='mixed').notna().mean() > 0.8:
        return 'date'
    return 'text'


def profile_dataframe(df: pd.DataFrame) -> list[ColumnProfile]:
    profiles: list[ColumnProfile] = []
    for column in df.columns:
        series = df[column]
        cleaned = series.dropna().astype(str)
        profiles.append(
            ColumnProfile(
                source=str(column),
                inferred_type=infer_series_type(series),
                sample_values=cleaned.head(3).tolist(),
                null_ratio=float(series.isna().mean()) if len(series) else 0.0,
            )
        )
    return profiles


def preview_dataframe(df: pd.DataFrame, limit: int = 8) -> tuple[list[str], list[dict[str, Any]]]:
    preview = df.head(limit).where(pd.notna(df.head(limit)), None).to_dict(orient='records')
    return [str(col) for col in df.columns], preview


def suggest_mappings(source_columns: list[str], canonical_columns: list[str]) -> list[MappingEntry]:
    normalized_canonical = {col: normalize_text(col) for col in canonical_columns}
    suggestions: list[MappingEntry] = []
    for source in source_columns:
        best_target = source
        best_score = 0.0
        normalized_source = normalize_text(source)
        for target, normalized_target in normalized_canonical.items():
            score = SequenceMatcher(None, normalized_source, normalized_target).ratio()
            if normalized_source == normalized_target:
                best_target = target
                best_score = 1.0
                break
            if score > best_score:
                best_target = target
                best_score = score
        suggestions.append(
            MappingEntry(
                source=source,
                target=best_target if best_score >= 0.65 else source,
                suggested_target=best_target if best_score >= 0.65 else None,
                inferred_type='text',
            )
        )
    return suggestions


def apply_mapping(df: pd.DataFrame, mapping_rules: list[dict[str, Any]] | list[MappingEntry]) -> pd.DataFrame:
    rules = [rule.model_dump() if isinstance(rule, MappingEntry) else rule for rule in mapping_rules]
    include_columns = [rule['source'] for rule in rules if rule.get('include', True)]
    working = df.loc[:, [column for column in df.columns if str(column) in include_columns]].copy() if rules else df.copy()
    rename_map = {
        rule['source']: rule['target']
        for rule in rules
        if rule.get('include', True) and rule['target'] and rule['target'] != rule['source']
    }
    return working.rename(columns=rename_map)


def resolve_mapping_target(mapping_rules: list[dict[str, Any]], source_name: str) -> str:
    for rule in mapping_rules:
        if rule['source'] == source_name and rule.get('include', True):
            return rule['target']
    return source_name


def resolve_mapped_column(mapping_rules: list[dict[str, Any]], source_name: str, available_columns: list[str] | None = None) -> str:
    if source_name in (available_columns or []):
        return source_name
    target = resolve_mapping_target(mapping_rules, source_name)
    included_sources = {rule['source'] for rule in mapping_rules if rule.get('include', True)}
    if mapping_rules and source_name not in included_sources and source_name not in (available_columns or []):
        raise ValueError(f'Column "{source_name}" was excluded from mapping')
    return target


def resolve_derived_columns(derived_columns: list[dict[str, Any]], mapping_rules: list[dict[str, Any]], available_columns: list[str]) -> list[dict[str, Any]]:
    resolved: list[dict[str, Any]] = []
    for definition in derived_columns:
        next_definition = dict(definition)
        next_conditions = []
        for condition in definition.get('conditions', []):
            next_condition = dict(condition)
            next_condition['column'] = resolve_mapped_column(mapping_rules, condition['column'], available_columns)
            if next_condition['column'] not in available_columns:
                raise ValueError(f'Derived column source "{condition["column"]}" not found after mapping')
            next_conditions.append(next_condition)
        next_definition['conditions'] = next_conditions
        resolved.append(next_definition)
    return resolved


def to_numeric(value: Any) -> float | None:
    parsed = pd.to_numeric(pd.Series([value]), errors='coerce').iloc[0]
    return None if pd.isna(parsed) else float(parsed)


def to_date(value: Any):
    parsed = pd.to_datetime(pd.Series([value]), errors='coerce', format='mixed').iloc[0]
    return None if pd.isna(parsed) else parsed


def iter_condition_values(value: Any) -> list[Any]:
    if isinstance(value, list):
        return [item for item in value if not normalize_null(item)]
    return [] if normalize_null(value) else [value]


def evaluate_scalar_condition(left: Any, condition: dict[str, Any]) -> bool | None:
    operator = condition['operator']
    data_type = condition['data_type']
    right = condition.get('value')
    second = condition.get('secondary_value')

    if data_type == 'numeric':
        left = to_numeric(left)
        right = to_numeric(right)
        second = to_numeric(second)
    elif data_type == 'date':
        left = to_date(left)
        right = to_date(right)
        second = to_date(second)
    else:
        left = str(left)
        right = '' if right is None else str(right)
        second = '' if second is None else str(second)

    if left is None:
        return None

    if operator == '=':
        return left == right
    if operator == '!=':
        return left != right
    if operator == '<':
        return left < right
    if operator == '>':
        return left > right
    if operator == '<=':
        return left <= right
    if operator == '>=':
        return left >= right
    if operator == 'BETWEEN':
        return right <= left <= second
    if operator == 'CONTAINS':
        return str(right).lower() in str(left).lower()
    if operator == 'CONTAINS ANY':
        values = [item.strip() for item in str(right).split(',') if item.strip()]
        return any(token.lower() in str(left).lower() for token in values)
    if operator == 'CONTAINS ALL':
        values = [item.strip() for item in str(right).split(',') if item.strip()]
        return all(token.lower() in str(left).lower() for token in values)
    if operator == 'IN':
        values = [item.strip() for item in str(right).split(',') if item.strip()]
        return str(left) in values
    raise ValueError(f'Unsupported operator: {operator}')


def evaluate_condition(value: Any, condition: dict[str, Any]) -> bool | None:
    values = iter_condition_values(value)
    if not values:
        return None

    if isinstance(value, list) and condition['data_type'] == 'text' and condition['operator'] in {'CONTAINS', 'CONTAINS ANY', 'CONTAINS ALL'}:
        return evaluate_scalar_condition(' | '.join(str(item) for item in values), condition)

    outcomes = [evaluate_scalar_condition(item, condition) for item in values]
    filtered = [outcome for outcome in outcomes if outcome is not None]
    if not filtered:
        return None
    return any(filtered)


def apply_derived_columns(df: pd.DataFrame, derived_columns: list[dict[str, Any]]) -> pd.DataFrame:
    working = df.copy()
    for definition in derived_columns:
        def compute(row):
            results = []
            has_null = False
            for condition in definition.get('conditions', []):
                outcome = evaluate_condition(row.get(condition['column']), condition)
                if outcome is None:
                    has_null = True
                results.append(bool(outcome))
            if has_null and definition.get('null_value') is not None:
                return definition.get('null_value')
            return definition['true_value'] if all(results) else definition.get('false_value')

        working[definition['name']] = working.apply(compute, axis=1)
    return working


def validate_mapping_rules(mapping_rules: list[dict[str, Any]]) -> None:
    included = [rule for rule in mapping_rules if rule.get('include', True)]
    missing_targets = [rule['source'] for rule in included if not str(rule.get('target', '')).strip()]
    if missing_targets:
        raise ValueError(f'Mapped target names are required for included columns: {", ".join(missing_targets)}')

    seen: dict[str, str] = {}
    duplicates: list[str] = []
    for rule in included:
        target = rule['target'].strip()
        if target in seen and seen[target] != rule['source']:
            duplicates.append(target)
        seen[target] = rule['source']
    if duplicates:
        ordered = ', '.join(sorted(set(duplicates)))
        raise ValueError(f'Duplicate mapped target names are not allowed: {ordered}')


def validate_upload_configuration(
    raw_df: pd.DataFrame,
    mapped_df: pd.DataFrame,
    mapping_rules: list[dict[str, Any]],
    equipment_id_column: str,
    role: str,
    canonical_join_column: str | None = None,
    canonical_dataset=None,
) -> tuple[str, str | None]:
    validate_mapping_rules(mapping_rules)

    raw_columns = [str(column) for column in raw_df.columns]
    mapped_columns = [str(column) for column in mapped_df.columns]

    if equipment_id_column not in raw_columns:
        raise ValueError('Mapped equipment ID column not found in source file')

    resolved_equipment = resolve_mapped_column(mapping_rules, equipment_id_column, mapped_columns)
    if resolved_equipment not in mapped_columns:
        raise ValueError('Mapped equipment ID column not found after mapping')

    resolved_join: str | None = None
    if role == 'supplementary':
        if not canonical_dataset:
            raise ValueError('Upload a canonical dataset before supplementary datasets')
        if not canonical_join_column:
            raise ValueError('Select a canonical join column for supplementary datasets')
        canonical_df = read_dataset(canonical_dataset.file_path, canonical_dataset.file_name, canonical_dataset.sheet_name)
        canonical_mapped = apply_mapping(canonical_df, canonical_dataset.mapping_rules or [])
        canonical_columns = [str(column) for column in canonical_mapped.columns]
        if canonical_join_column not in canonical_columns:
            raise ValueError('Selected canonical join column not found after mapping')
        resolved_join = canonical_join_column
    return resolved_equipment, resolved_join


def build_match_table(base: pd.DataFrame, sup: pd.DataFrame, left_key: str, right_key: str, dataset_name: str, strategy: str, fuzzy_threshold: float) -> pd.DataFrame:
    raw_lookup: dict[str, list[dict[str, Any]]] = {}
    normalized_lookup: dict[str, list[dict[str, Any]]] = {}

    for _, row in sup.iterrows():
        row_dict = row.to_dict()
        source_id = row.get(right_key)
        raw_key = '' if source_id is None else str(source_id)
        normalized_key = normalize_text(source_id)
        if raw_key:
            raw_lookup.setdefault(raw_key, []).append(row_dict)
        if normalized_key:
            normalized_lookup.setdefault(normalized_key, []).append(row_dict)

    normalized_candidates = list(normalized_lookup.keys())
    merged_rows: list[dict[str, Any]] = []
    metadata_prefix = f'{dataset_name}__'

    for _, base_row in base.iterrows():
        canonical_value = base_row.get(left_key)
        raw_left = '' if canonical_value is None else str(canonical_value)
        normalized_left = normalize_text(canonical_value)
        matches: list[dict[str, Any]] = []
        match_method = 'unmatched'
        match_confidence = 0.0

        if strategy == 'exact' and raw_left in raw_lookup:
            matches = raw_lookup[raw_left]
            match_method = 'exact'
            match_confidence = 1.0
        elif strategy in {'normalized', 'fuzzy'} and normalized_left in normalized_lookup:
            matches = normalized_lookup[normalized_left]
            match_method = 'exact' if any(str(item.get(right_key, '')) == raw_left for item in matches) else 'normalized_exact'
            match_confidence = 1.0
        elif strategy == 'fuzzy' and normalized_left and normalized_candidates:
            candidate, score = max(
                ((candidate_key, SequenceMatcher(None, normalized_left, candidate_key).ratio()) for candidate_key in normalized_candidates),
                key=lambda item: item[1],
            )
            if score >= fuzzy_threshold:
                matches = normalized_lookup[candidate]
                match_method = 'fuzzy'
                match_confidence = float(score)

        merged = base_row.to_dict()
        if matches:
            for column in sup.columns:
                values = [item.get(column) for item in matches if not normalize_null(item.get(column))]
                merged[column] = values
            merged[f'{metadata_prefix}matched_source_ids'] = [item.get(right_key) for item in matches if not normalize_null(item.get(right_key))]
            merged[f'{metadata_prefix}match_methods'] = [match_method for _ in matches]
            merged[f'{metadata_prefix}match_confidences'] = [match_confidence for _ in matches]
            merged[f'{metadata_prefix}match_confidence'] = match_confidence
            merged[f'{metadata_prefix}match_method'] = match_method
            merged[f'{metadata_prefix}match_count'] = len(matches)
            merged[f'{metadata_prefix}evidence_rows'] = matches
        else:
            for column in sup.columns:
                if column not in merged:
                    merged[column] = []
            merged[f'{metadata_prefix}matched_source_ids'] = []
            merged[f'{metadata_prefix}match_methods'] = []
            merged[f'{metadata_prefix}match_confidences'] = []
            merged[f'{metadata_prefix}match_confidence'] = 0.0
            merged[f'{metadata_prefix}match_method'] = 'unmatched'
            merged[f'{metadata_prefix}match_count'] = 0
            merged[f'{metadata_prefix}evidence_rows'] = []
        merged_rows.append(merged)

    return pd.DataFrame(merged_rows)


def build_master_dataframe(canonical_dataset, supplementary_datasets) -> pd.DataFrame:
    base = read_dataset(canonical_dataset.file_path, canonical_dataset.file_name, canonical_dataset.sheet_name)
    base = apply_mapping(base, canonical_dataset.mapping_rules or [])
    resolved_derived = resolve_derived_columns(canonical_dataset.derived_columns or [], canonical_dataset.mapping_rules or [], [str(column) for column in base.columns])
    base = apply_derived_columns(base, resolved_derived)

    canonical_key = resolve_mapping_target(canonical_dataset.mapping_rules or [], canonical_dataset.equipment_id_column)

    for dataset in supplementary_datasets:
        sup = read_dataset(dataset.file_path, dataset.file_name, dataset.sheet_name)
        sup = apply_mapping(sup, dataset.mapping_rules or [])
        resolved_sup_derived = resolve_derived_columns(dataset.derived_columns or [], dataset.mapping_rules or [], [str(column) for column in sup.columns])
        sup = apply_derived_columns(sup, resolved_sup_derived)
        right_key = resolve_mapping_target(dataset.mapping_rules or [], dataset.equipment_id_column)
        matching_config = dataset.matching_config or {'strategy': 'normalized', 'fuzzy_threshold': 0.82}

        renamed = {}
        for col in sup.columns:
            if col in base.columns:
                renamed[col] = f'{dataset.name}_{col}'
        sup = sup.rename(columns=renamed)
        right_key = renamed.get(right_key, right_key)

        left_key = dataset.canonical_join_column or canonical_key
        left_key = resolve_mapping_target(canonical_dataset.mapping_rules or [], left_key)

        base = build_match_table(
            base=base,
            sup=sup,
            left_key=left_key,
            right_key=right_key,
            dataset_name=dataset.name,
            strategy=matching_config.get('strategy', 'normalized'),
            fuzzy_threshold=float(matching_config.get('fuzzy_threshold', 0.82)),
        )
    return base


def evaluate_ast_with_trace(row: dict[str, Any], node: RuleGroupNode | RuleConditionNode) -> tuple[bool, dict[str, Any], list[str], set[str]]:
    if isinstance(node, RuleGroupNode):
        child_traces = []
        path: list[str] = []
        source_fields: set[str] = set()
        child_results = []
        for child in node.children:
            result, trace, child_path, child_fields = evaluate_ast_with_trace(row, child)
            child_results.append(result)
            child_traces.append(trace)
            if result:
                path.append(child.id)
            path.extend(child_path)
            source_fields.update(child_fields)
        result = all(child_results) if node.combinator == 'AND' else any(child_results) if child_results else False
        return result, {'node_id': node.id, 'combinator': node.combinator, 'result': result, 'children': child_traces}, path, source_fields

    outcome = evaluate_condition(
        row.get(node.field),
        {
            'data_type': node.data_type,
            'operator': node.operator,
            'value': node.value,
            'secondary_value': node.secondary_value,
        },
    )
    return bool(outcome), {
        'node_id': node.id,
        'field': node.field,
        'operator': node.operator,
        'data_type': node.data_type,
        'result': outcome,
        'actual_value': row.get(node.field),
        'expected_value': node.value,
        'secondary_value': node.secondary_value,
    }, [node.id] if outcome else [], {node.field}


def classify_dataframe(df: pd.DataFrame, ast_json: RuleSetAst | dict[str, Any], equipment_column: str) -> tuple[pd.DataFrame, list[dict[str, Any]]]:
    rules = ast_json if isinstance(ast_json, RuleSetAst) else RuleSetAst.model_validate(ast_json)
    explanations: list[dict[str, Any]] = []

    def classify(row_index: int, row: pd.Series) -> str:
        as_dict = row.to_dict()
        must_result, must_trace, must_path, must_fields = evaluate_ast_with_trace(as_dict, rules.must_have)
        if must_result:
            explanations.append(
                {
                    'row_index': row_index,
                    'equipment_id': str(as_dict.get(equipment_column, '')),
                    'classification': 'Must Have',
                    'matched_rule': 'must_have',
                    'rule_path': must_path,
                    'source_fields': sorted(must_fields),
                    'condition_trace': must_trace,
                }
            )
            return 'Must Have'

        good_result, good_trace, good_path, good_fields = evaluate_ast_with_trace(as_dict, rules.good_to_have)
        if good_result:
            explanations.append(
                {
                    'row_index': row_index,
                    'equipment_id': str(as_dict.get(equipment_column, '')),
                    'classification': 'Good to Have',
                    'matched_rule': 'good_to_have',
                    'rule_path': good_path,
                    'source_fields': sorted(good_fields),
                    'condition_trace': good_trace,
                }
            )
            return 'Good to Have'

        explanations.append(
            {
                'row_index': row_index,
                'equipment_id': str(as_dict.get(equipment_column, '')),
                'classification': rules.fallback_label,
                'matched_rule': 'fallback',
                'rule_path': [],
                'source_fields': [],
                'condition_trace': good_trace,
            }
        )
        return rules.fallback_label

    result = df.copy()
    classifications = []
    for row_index, row in result.iterrows():
        classifications.append(classify(int(row_index), row))
    result['classification'] = classifications
    result['evaluated_at'] = datetime.utcnow().isoformat()
    return result, explanations
