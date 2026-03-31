from sqlalchemy import Column, Integer, String, Float, Boolean, ForeignKey, JSON, DateTime
from sqlalchemy.orm import relationship
from datetime import datetime, timezone
from app.database import Base

class Project(Base):
    __tablename__ = "projects"
    project_id = Column(Integer, primary_key=True, index=True)
    name = Column(String, index=True)
    created_by = Column(String, default="system")
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    datasets = relationship("DatasetUpload", back_populates="project")
    rules = relationship("RuleSet", back_populates="project")

class DatasetUpload(Base):
    __tablename__ = "dataset_uploads"
    dataset_id = Column(Integer, primary_key=True, index=True)
    project_id = Column(Integer, ForeignKey("projects.project_id"))
    name = Column(String, index=True)
    file_path = Column(String)
    dataset_schema = Column(JSON, default=dict) # To store column types, row counts
    uploaded_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    is_original = Column(Boolean, default=False)

    project = relationship("Project", back_populates="datasets")
    column_mapping = relationship("ColumnMapping", back_populates="dataset", uselist=False)

class ColumnMapping(Base):
    __tablename__ = "column_mappings"
    mapping_id = Column(Integer, primary_key=True, index=True)
    dataset_id = Column(Integer, ForeignKey("dataset_uploads.dataset_id"), unique=True)
    equipment_id_col = Column(String, nullable=False)
    category_col = Column(String, nullable=True) # None for the original dataset config

    dataset = relationship("DatasetUpload", back_populates="column_mapping")

class CanonicalEquipment(Base):
    __tablename__ = "canonical_equipment"
    canonical_id = Column(Integer, primary_key=True, index=True)
    project_id = Column(Integer, ForeignKey("projects.project_id"))
    canonical_label = Column(String, index=True)
    normalized_label = Column(String, index=True)
    alias_count = Column(Integer, default=0)

class MatchRecord(Base):
    __tablename__ = "match_records"
    match_id = Column(Integer, primary_key=True, index=True)
    project_id = Column(Integer, ForeignKey("projects.project_id"))
    dataset_id = Column(Integer, ForeignKey("dataset_uploads.dataset_id"))
    canonical_id = Column(Integer, ForeignKey("canonical_equipment.canonical_id"))
    source_row_index = Column(Integer) # Row index from pandas DataFrame
    source_equipment_id = Column(String) # Raw ID from supplementary dataset
    method = Column(String) # 'exact', 'fuzzy_token_set_ratio', etc
    score = Column(Float)
    reviewer = Column(String, nullable=True) # if manual override
    is_approved = Column(Boolean, default=True)

class RuleSet(Base):
    __tablename__ = "rule_sets"
    rule_set_id = Column(Integer, primary_key=True, index=True)
    project_id = Column(Integer, ForeignKey("projects.project_id"))
    version_no = Column(Integer, default=1)
    ast_json = Column(JSON, default=dict)
    status = Column(String, default="draft") # draft, active, archived
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    project = relationship("Project", back_populates="rules")

class ClassificationRun(Base):
    __tablename__ = "classification_runs"
    run_id = Column(Integer, primary_key=True, index=True)
    project_id = Column(Integer, ForeignKey("projects.project_id"))
    rule_set_id = Column(Integer, ForeignKey("rule_sets.rule_set_id"))
    started_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    status = Column(String, default="running")
    metrics_json = Column(JSON, default=dict) # summary stats
