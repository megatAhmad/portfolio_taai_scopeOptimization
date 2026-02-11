"""
Pydantic models for upload API endpoints.
"""

from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field


class ValidationResultModel(BaseModel):
    """Model for validation results."""
    
    is_valid: bool
    errors: List[str] = Field(default_factory=list)
    warnings: List[str] = Field(default_factory=list)
    detected_columns: List[str] = Field(default_factory=list)
    missing_required: List[str] = Field(default_factory=list)
    missing_optional: List[str] = Field(default_factory=list)


class UploadResponse(BaseModel):
    """Response model for file upload."""
    
    session_id: str
    filename: str
    total_rows: int
    columns: List[str]
    validation: ValidationResultModel
    preview: List[Dict[str, Any]] = Field(
        default_factory=list,
        description="First 10 rows of data"
    )
    sheet_names: List[str] = Field(default_factory=list)


class DataPreviewRequest(BaseModel):
    """Request model for data preview with pagination."""
    
    page: int = Field(default=1, ge=1, description="Page number (1-indexed)")
    page_size: int = Field(default=50, ge=1, le=1000, description="Items per page")
    sort_by: Optional[str] = Field(default=None, description="Column to sort by")
    sort_order: str = Field(default="asc", pattern="^(asc|desc)$")


class DataPreviewResponse(BaseModel):
    """Response model for data preview."""
    
    data: List[Dict[str, Any]]
    total_rows: int
    page: int
    page_size: int
    total_pages: int


class ColumnStatsResponse(BaseModel):
    """Response model for column statistics."""
    
    column_name: str
    data_type: str
    null_count: int
    null_percentage: float
    unique_count: int
    sample_values: List[Any] = Field(default_factory=list)
    numeric_stats: Optional[Dict[str, float]] = None  # min, max, mean, median, std


class AllColumnStatsResponse(BaseModel):
    """Response model for all column statistics."""
    
    columns: List[ColumnStatsResponse]
    total_rows: int


class SheetListResponse(BaseModel):
    """Response model for available sheets."""
    
    sheets: List[str]
    current_sheet: str
