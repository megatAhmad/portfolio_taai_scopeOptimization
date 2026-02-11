"""
Pydantic models for export API endpoints.
"""

from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field


class ExportFormat(str):
    """Export format options."""
    XLSX = "xlsx"
    CSV = "csv"
    JSON = "json"


class FilterRequest(BaseModel):
    """Request model for filtering results."""
    
    outcomes: Optional[List[str]] = Field(
        default=None,
        description="Filter by outcomes: ACCEPTED, RECONSIDER, REJECTED"
    )
    min_confidence: Optional[float] = Field(default=None, ge=0.0, le=1.0)
    max_confidence: Optional[float] = Field(default=None, ge=0.0, le=1.0)
    search_text: Optional[str] = None
    columns: Optional[List[str]] = None


class FilteredResultsResponse(BaseModel):
    """Response model for filtered results."""
    
    data: List[Dict[str, Any]]
    total_count: int
    filtered_count: int


class AuditMetadataResponse(BaseModel):
    """Response model for audit metadata."""
    
    session_id: str
    filename: str
    processed_at: str
    total_rows: int
    rules_applied: List[Dict[str, Any]]
    ai_config: Optional[Dict[str, Any]] = None
    processing_time_seconds: float
    summary: Dict[str, Any]
