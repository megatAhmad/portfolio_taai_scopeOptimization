from __future__ import annotations

from datetime import datetime

from sqlalchemy import JSON, DateTime, ForeignKey, Index, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db import Base


class Project(Base):
    __tablename__ = 'projects'

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    name: Mapped[str] = mapped_column(String(200), unique=True)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    datasets: Mapped[list['Dataset']] = relationship(back_populates='project', cascade='all, delete-orphan')
    rulesets: Mapped[list['RuleSet']] = relationship(back_populates='project', cascade='all, delete-orphan')
    classification_runs: Mapped[list['ClassificationRun']] = relationship(back_populates='project', cascade='all, delete-orphan')


class Dataset(Base):
    __tablename__ = 'datasets'

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    project_id: Mapped[int] = mapped_column(ForeignKey('projects.id'))
    name: Mapped[str] = mapped_column(String(200))
    role: Mapped[str] = mapped_column(String(50))
    file_name: Mapped[str] = mapped_column(String(255))
    file_path: Mapped[str] = mapped_column(String(500))
    sheet_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    equipment_id_column: Mapped[str] = mapped_column(String(255))
    canonical_join_column: Mapped[str | None] = mapped_column(String(255), nullable=True)
    column_mapping: Mapped[dict] = mapped_column(JSON, default=dict)
    mapping_rules: Mapped[list] = mapped_column(JSON, default=list)
    derived_columns: Mapped[list] = mapped_column(JSON, default=list)
    preview_rows: Mapped[list] = mapped_column(JSON, default=list)
    schema_profile: Mapped[list] = mapped_column(JSON, default=list)
    matching_config: Mapped[dict] = mapped_column(JSON, default=dict)
    equipment_id_cleaning_config: Mapped[dict] = mapped_column(JSON, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    project: Mapped['Project'] = relationship(back_populates='datasets')


class RuleSet(Base):
    __tablename__ = 'rulesets'

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    project_id: Mapped[int] = mapped_column(ForeignKey('projects.id'))
    version_no: Mapped[int] = mapped_column(Integer)
    name: Mapped[str] = mapped_column(String(200), default='Default Rule Set')
    ast_json: Mapped[dict] = mapped_column(JSON)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    project: Mapped['Project'] = relationship(back_populates='rulesets')
    classification_runs: Mapped[list['ClassificationRun']] = relationship(back_populates='ruleset')


class ClassificationRun(Base):
    __tablename__ = 'classification_runs'

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    project_id: Mapped[int] = mapped_column(ForeignKey('projects.id'))
    ruleset_id: Mapped[int] = mapped_column(ForeignKey('rulesets.id'))
    ruleset_version: Mapped[int] = mapped_column(Integer)
    status: Mapped[str] = mapped_column(String(50), default='completed')
    summary: Mapped[dict] = mapped_column(JSON, default=dict)
    columns: Mapped[list] = mapped_column(JSON, default=list)
    total_rows: Mapped[int] = mapped_column(Integer, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    project: Mapped['Project'] = relationship(back_populates='classification_runs')
    ruleset: Mapped['RuleSet'] = relationship(back_populates='classification_runs')
    artifacts: Mapped[list['ClassificationRunArtifact']] = relationship(back_populates='run', cascade='all, delete-orphan')


class ClassificationRunArtifact(Base):
    __tablename__ = 'classification_run_artifacts'
    __table_args__ = (Index('ix_classification_run_artifacts_run_type', 'run_id', 'artifact_type', unique=True),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    run_id: Mapped[int] = mapped_column(ForeignKey('classification_runs.id'))
    artifact_type: Mapped[str] = mapped_column(String(50))
    file_path: Mapped[str] = mapped_column(String(500))
    format: Mapped[str] = mapped_column(String(50))
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    run: Mapped['ClassificationRun'] = relationship(back_populates='artifacts')
