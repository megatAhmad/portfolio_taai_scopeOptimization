"""
Pydantic models for process API endpoints.
"""

from typing import Optional, Dict, Any, List
from pydantic import BaseModel, Field


class AIConfigModel(BaseModel):
    """Model for AI configuration."""
    
    provider: str = Field(..., pattern="^(azure|openrouter)$")
    model: str
    api_key: Optional[str] = None
    endpoint: Optional[str] = None
    temperature: float = Field(default=0.7, ge=0.0, le=2.0)
    max_tokens: int = Field(default=500, ge=1, le=4000)


class ProcessRequest(BaseModel):
    """Request model for starting processing."""
    
    ai_config: Optional[AIConfigModel] = None
    generate_justifications: bool = True
    batch_size: int = Field(default=10, ge=1, le=100)


class ProcessStatusResponse(BaseModel):
    """Response model for processing status."""
    
    session_id: str
    status: str  # idle, processing, completed, error
    progress: float = Field(ge=0.0, le=100.0)
    current_row: Optional[int] = None
    total_rows: Optional[int] = None
    message: Optional[str] = None
    error: Optional[str] = None


class ProcessSummaryResponse(BaseModel):
    """Response model for processing summary."""
    
    session_id: str
    total_processed: int
    accepted_count: int
    reconsider_count: int
    rejected_count: int
    processing_time_seconds: float
    rules_applied: int
    justifications_generated: int
    summary_stats: Dict[str, Any] = Field(default_factory=dict)


class PreviewRequest(BaseModel):
    """Request model for preview."""
    
    sample_size: int = Field(default=5, ge=1, le=20)


class PreviewResponse(BaseModel):
    """Response model for preview."""
    
    flowchart_data: Dict[str, Any]
    sample_evaluations: List[Dict[str, Any]]
