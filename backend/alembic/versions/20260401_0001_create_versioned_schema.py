"""create versioned schema

Revision ID: 20260401_0001
Revises: 
Create Date: 2026-04-01 08:00:00
"""

from alembic import op
import sqlalchemy as sa


revision = '20260401_0001'
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        'projects',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('name', sa.String(length=200), nullable=False, unique=True),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False),
    )
    op.create_index('ix_projects_id', 'projects', ['id'])

    op.create_table(
        'datasets',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('project_id', sa.Integer(), sa.ForeignKey('projects.id'), nullable=False),
        sa.Column('name', sa.String(length=200), nullable=False),
        sa.Column('role', sa.String(length=50), nullable=False),
        sa.Column('file_name', sa.String(length=255), nullable=False),
        sa.Column('file_path', sa.String(length=500), nullable=False),
        sa.Column('sheet_name', sa.String(length=255), nullable=True),
        sa.Column('equipment_id_column', sa.String(length=255), nullable=False),
        sa.Column('canonical_join_column', sa.String(length=255), nullable=True),
        sa.Column('column_mapping', sa.JSON(), nullable=False),
        sa.Column('mapping_rules', sa.JSON(), nullable=False),
        sa.Column('derived_columns', sa.JSON(), nullable=False),
        sa.Column('preview_rows', sa.JSON(), nullable=False),
        sa.Column('schema_profile', sa.JSON(), nullable=False),
        sa.Column('matching_config', sa.JSON(), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False),
    )
    op.create_index('ix_datasets_id', 'datasets', ['id'])

    op.create_table(
        'rulesets',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('project_id', sa.Integer(), sa.ForeignKey('projects.id'), nullable=False),
        sa.Column('version_no', sa.Integer(), nullable=False),
        sa.Column('name', sa.String(length=200), nullable=False),
        sa.Column('ast_json', sa.JSON(), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False),
    )
    op.create_index('ix_rulesets_id', 'rulesets', ['id'])

    op.create_table(
        'classification_runs',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('project_id', sa.Integer(), sa.ForeignKey('projects.id'), nullable=False),
        sa.Column('ruleset_id', sa.Integer(), sa.ForeignKey('rulesets.id'), nullable=False),
        sa.Column('ruleset_version', sa.Integer(), nullable=False),
        sa.Column('status', sa.String(length=50), nullable=False),
        sa.Column('summary', sa.JSON(), nullable=False),
        sa.Column('columns', sa.JSON(), nullable=False),
        sa.Column('total_rows', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('created_at', sa.DateTime(), nullable=False),
    )
    op.create_index('ix_classification_runs_id', 'classification_runs', ['id'])

    op.create_table(
        'classification_run_artifacts',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('run_id', sa.Integer(), sa.ForeignKey('classification_runs.id'), nullable=False),
        sa.Column('artifact_type', sa.String(length=50), nullable=False),
        sa.Column('file_path', sa.String(length=500), nullable=False),
        sa.Column('format', sa.String(length=50), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False),
    )
    op.create_index('ix_classification_run_artifacts_id', 'classification_run_artifacts', ['id'])
    op.create_index('ix_classification_run_artifacts_run_type', 'classification_run_artifacts', ['run_id', 'artifact_type'], unique=True)


def downgrade() -> None:
    op.drop_index('ix_classification_run_artifacts_run_type', table_name='classification_run_artifacts')
    op.drop_index('ix_classification_run_artifacts_id', table_name='classification_run_artifacts')
    op.drop_table('classification_run_artifacts')
    op.drop_index('ix_classification_runs_id', table_name='classification_runs')
    op.drop_table('classification_runs')
    op.drop_index('ix_rulesets_id', table_name='rulesets')
    op.drop_table('rulesets')
    op.drop_index('ix_datasets_id', table_name='datasets')
    op.drop_table('datasets')
    op.drop_index('ix_projects_id', table_name='projects')
    op.drop_table('projects')
