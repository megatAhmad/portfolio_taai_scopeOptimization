from pydantic import BaseModel, ConfigDict
from datetime import datetime
from typing import List, Optional, Any, Dict

class ProjectBase(BaseModel):
    name: str

class ProjectCreate(ProjectBase):
    pass

class Project(ProjectBase):
    project_id: int
    created_by: str
    created_at: datetime
    model_config = ConfigDict(from_attributes=True)

class DatasetUploadBase(BaseModel):
    name: str
    is_original: bool = False
    sheet_name: Optional[str] = None

class DatasetUploadCreate(DatasetUploadBase):
    file_path: str
    dataset_schema: Dict[str, Any] = {}

class DatasetUpload(DatasetUploadBase):
    dataset_id: int
    project_id: int
    file_path: str
    dataset_schema: Dict[str, Any]
    uploaded_at: datetime
    model_config = ConfigDict(from_attributes=True)

class ColumnMappingBase(BaseModel):
    equipment_id_col: str
    category_col: Optional[str] = None
    mapping_rules: Optional[List[Dict[str, Any]]] = None
    derived_column_name: Optional[str] = None
    data_type: Optional[str] = "text"
    default_output: Optional[str] = "N/A"
    empty_output: Optional[str] = "N/A"

class ColumnMappingCreate(ColumnMappingBase):
    pass

class ColumnMapping(ColumnMappingBase):
    mapping_id: int
    dataset_id: int
    model_config = ConfigDict(from_attributes=True)

class RuleSetBase(BaseModel):
    ast_json: Dict[str, Any]
    status: str = "draft"

class RuleSetCreate(RuleSetBase):
    pass

class RuleSet(RuleSetBase):
    rule_set_id: int
    project_id: int
    version_no: int
    created_at: datetime
    model_config = ConfigDict(from_attributes=True)
