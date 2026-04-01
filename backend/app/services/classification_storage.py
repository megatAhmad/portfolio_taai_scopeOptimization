from __future__ import annotations

import csv
import json
from pathlib import Path
from typing import Any

from fastapi.responses import FileResponse

from app.core.config import DATA_DIR
from app.models import ClassificationRun, ClassificationRunArtifact

RUNS_DIR = DATA_DIR / 'classification_runs'
RUNS_DIR.mkdir(parents=True, exist_ok=True)


def _serialize_value(value: Any) -> Any:
    if isinstance(value, dict):
        return {str(key): _serialize_value(item) for key, item in value.items()}
    if isinstance(value, (list, tuple, set)):
        return [_serialize_value(item) for item in value]
    if hasattr(value, 'isoformat'):
        return value.isoformat()
    return value


def _stringify_for_csv(value: Any) -> str:
    serialized = _serialize_value(value)
    if isinstance(serialized, (dict, list)):
        return json.dumps(serialized, ensure_ascii=True)
    return '' if serialized is None else str(serialized)


def _artifact_dir(run_id: int) -> Path:
    directory = RUNS_DIR / str(run_id)
    directory.mkdir(parents=True, exist_ok=True)
    return directory


def _artifact_map(run: ClassificationRun) -> dict[str, ClassificationRunArtifact]:
    return {artifact.artifact_type: artifact for artifact in run.artifacts}


def artifact_file_path(run: ClassificationRun, artifact_type: str) -> str | None:
    artifact = _artifact_map(run).get(artifact_type)
    return artifact.file_path if artifact else None


def persist_run_artifacts(run_id: int, rows: list[dict[str, Any]], explanations: list[dict[str, Any]], columns: list[str]) -> list[dict[str, str]]:
    directory = _artifact_dir(run_id)
    rows_path = directory / 'rows.jsonl'
    explanations_path = directory / 'explanations.jsonl'
    export_path = directory / 'results.csv'

    with rows_path.open('w', encoding='utf-8') as handle:
        for row in rows:
            handle.write(json.dumps(_serialize_value(row), ensure_ascii=True) + '\n')

    with explanations_path.open('w', encoding='utf-8') as handle:
        for explanation in explanations:
            handle.write(json.dumps(_serialize_value(explanation), ensure_ascii=True) + '\n')

    explanation_lookup = {item['row_index']: item for item in explanations}
    with export_path.open('w', encoding='utf-8', newline='') as handle:
        fieldnames = list(columns) + ['matched_rule', 'rule_path', 'source_fields']
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        for index, row in enumerate(rows):
            explanation = explanation_lookup.get(index, {})
            export_row = {column: _stringify_for_csv(row.get(column)) for column in columns}
            export_row['matched_rule'] = str(explanation.get('matched_rule', ''))
            export_row['rule_path'] = ' > '.join(explanation.get('rule_path', []))
            export_row['source_fields'] = ', '.join(explanation.get('source_fields', []))
            writer.writerow(export_row)

    return [
        {'artifact_type': 'rows', 'file_path': str(rows_path), 'format': 'jsonl'},
        {'artifact_type': 'explanations', 'file_path': str(explanations_path), 'format': 'jsonl'},
        {'artifact_type': 'export', 'file_path': str(export_path), 'format': 'csv'},
    ]


def _load_jsonl_slice(path: str | None, offset: int, limit: int) -> list[dict[str, Any]]:
    if not path:
        return []
    start = max(offset, 0)
    remaining = max(limit, 0)
    if remaining == 0:
        return []

    records: list[dict[str, Any]] = []
    with Path(path).open('r', encoding='utf-8') as handle:
        for index, line in enumerate(handle):
            if index < start:
                continue
            if len(records) >= remaining:
                break
            records.append(json.loads(line))
    return records


def load_run_page(run: ClassificationRun, offset: int = 0, limit: int = 100) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    return (
        _load_jsonl_slice(artifact_file_path(run, 'rows'), offset, limit),
        _load_jsonl_slice(artifact_file_path(run, 'explanations'), offset, limit),
    )


def export_run_file(run: ClassificationRun) -> FileResponse:
    export_artifact = artifact_file_path(run, 'export')
    if not export_artifact:
        raise FileNotFoundError('Classification export artifact is missing')
    export_path = Path(export_artifact)
    if not export_path.exists():
        raise FileNotFoundError('Classification export artifact is missing')
    return FileResponse(export_path, media_type='text/csv', filename=f'classification_run_{run.id}.csv')
