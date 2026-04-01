from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from alembic import command
from alembic.config import Config
from sqlalchemy import inspect, text

from app.core.config import BASE_DIR, DB_PATH
from app.db import engine
from app.services.classification_storage import persist_run_artifacts

ALEMBIC_REVISION = '20260401_0001'


def _alembic_config() -> Config:
    config = Config(str(BASE_DIR / 'alembic.ini'))
    config.set_main_option('sqlalchemy.url', f'sqlite:///{DB_PATH}')
    return config


def _deserialize_json(value: Any, fallback: Any) -> Any:
    if value in (None, ''):
        return fallback
    if isinstance(value, str):
        return json.loads(value)
    return value


def _legacy_rows_to_artifacts(run_row: dict[str, Any]) -> list[dict[str, str]]:
    rows_path = run_row.get('rows_artifact_path')
    explanations_path = run_row.get('explanations_artifact_path')
    export_path = run_row.get('export_artifact_path')
    if rows_path and explanations_path and export_path:
        if Path(rows_path).exists() and Path(explanations_path).exists() and Path(export_path).exists():
            return [
                {'artifact_type': 'rows', 'file_path': rows_path, 'format': 'jsonl'},
                {'artifact_type': 'explanations', 'file_path': explanations_path, 'format': 'jsonl'},
                {'artifact_type': 'export', 'file_path': export_path, 'format': 'csv'},
            ]

    rows = _deserialize_json(run_row.get('rows'), [])
    explanations = _deserialize_json(run_row.get('explanations'), [])
    columns = _deserialize_json(run_row.get('columns'), [])
    return persist_run_artifacts(int(run_row['id']), rows, explanations, [str(column) for column in columns])


def _bootstrap_legacy_database() -> None:
    inspector = inspect(engine)
    tables = set(inspector.get_table_names())
    if not tables:
        return
    if 'alembic_version' in tables:
        version = engine.connect().execute(text('SELECT version_num FROM alembic_version')).scalar()
        if version:
            return
    if 'classification_runs' not in tables and 'classification_runs_legacy' not in tables:
        return

    source_table = 'classification_runs_legacy' if 'classification_runs_legacy' in tables else 'classification_runs'
    source_columns = {column['name'] for column in inspector.get_columns(source_table)}
    if source_table == 'classification_runs' and 'classification_run_artifacts' in tables and 'rows' not in source_columns and 'explanations' not in source_columns:
        command.stamp(_alembic_config(), ALEMBIC_REVISION)
        return

    with engine.begin() as connection:
        raw_rows = connection.execute(text(f'SELECT * FROM {source_table}')).mappings().all()
        run_rows = [dict(row) for row in raw_rows]

        if source_table == 'classification_runs':
            connection.execute(text('ALTER TABLE classification_runs RENAME TO classification_runs_legacy'))

        if 'classification_runs' not in tables or source_table == 'classification_runs':
            connection.execute(
                text(
                    '''
                    CREATE TABLE classification_runs (
                        id INTEGER NOT NULL PRIMARY KEY,
                        project_id INTEGER NOT NULL,
                        ruleset_id INTEGER NOT NULL,
                        ruleset_version INTEGER NOT NULL,
                        status VARCHAR(50) NOT NULL,
                        summary JSON NOT NULL,
                        columns JSON NOT NULL,
                        total_rows INTEGER NOT NULL DEFAULT 0,
                        created_at DATETIME NOT NULL,
                        FOREIGN KEY(project_id) REFERENCES projects (id),
                        FOREIGN KEY(ruleset_id) REFERENCES rulesets (id)
                    )
                    '''
                )
            )
        else:
            connection.execute(text('DELETE FROM classification_runs'))

        if 'classification_run_artifacts' not in tables:
            connection.execute(
                text(
                    '''
                    CREATE TABLE classification_run_artifacts (
                        id INTEGER NOT NULL PRIMARY KEY,
                        run_id INTEGER NOT NULL,
                        artifact_type VARCHAR(50) NOT NULL,
                        file_path VARCHAR(500) NOT NULL,
                        format VARCHAR(50) NOT NULL,
                        created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
                        FOREIGN KEY(run_id) REFERENCES classification_runs (id)
                    )
                    '''
                )
            )
            connection.execute(text('CREATE UNIQUE INDEX ix_classification_run_artifacts_run_type ON classification_run_artifacts (run_id, artifact_type)'))
        else:
            connection.execute(text('DELETE FROM classification_run_artifacts'))

        for run_row in run_rows:
            rows_payload = _deserialize_json(run_row.get('rows'), [])
            total_rows = run_row.get('total_rows') or len(rows_payload)
            connection.execute(
                text(
                    '''
                    INSERT INTO classification_runs (id, project_id, ruleset_id, ruleset_version, status, summary, columns, total_rows, created_at)
                    VALUES (:id, :project_id, :ruleset_id, :ruleset_version, :status, :summary, :columns, :total_rows, :created_at)
                    '''
                ),
                {
                    'id': run_row['id'],
                    'project_id': run_row['project_id'],
                    'ruleset_id': run_row['ruleset_id'],
                    'ruleset_version': run_row['ruleset_version'],
                    'status': run_row['status'],
                    'summary': json.dumps(_deserialize_json(run_row.get('summary'), {})),
                    'columns': json.dumps(_deserialize_json(run_row.get('columns'), [])),
                    'total_rows': total_rows,
                    'created_at': run_row['created_at'],
                },
            )
            for artifact in _legacy_rows_to_artifacts(run_row):
                connection.execute(
                    text(
                        '''
                        INSERT INTO classification_run_artifacts (run_id, artifact_type, file_path, format, created_at)
                        VALUES (:run_id, :artifact_type, :file_path, :format, CURRENT_TIMESTAMP)
                        '''
                    ),
                    {
                        'run_id': run_row['id'],
                        'artifact_type': artifact['artifact_type'],
                        'file_path': artifact['file_path'],
                        'format': artifact['format'],
                    },
                )

        connection.execute(text('DROP TABLE IF EXISTS classification_runs_legacy'))

    command.stamp(_alembic_config(), ALEMBIC_REVISION)


def migrate_database() -> None:
    _bootstrap_legacy_database()
    command.upgrade(_alembic_config(), 'head')
