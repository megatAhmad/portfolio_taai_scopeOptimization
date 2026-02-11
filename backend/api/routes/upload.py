"""
Upload API routes for MWCS Backend.

Handles file upload, validation, and data preview.
"""

import logging
import tempfile
from pathlib import Path
from typing import Optional

from fastapi import APIRouter, UploadFile, File, HTTPException, Query
from fastapi.responses import JSONResponse

from api.models.upload import (
    UploadResponse,
    ValidationResultModel,
    DataPreviewRequest,
    DataPreviewResponse,
    ColumnStatsResponse,
    AllColumnStatsResponse,
    SheetListResponse
)
from api.services.session_store import get_session_store
from src.upload import DataUploader

logger = logging.getLogger(__name__)

router = APIRouter()


@router.post("/", response_model=UploadResponse)
async def upload_file(file: UploadFile = File(...)):
    """
    Upload an Excel file and create a new session.
    
    Returns session ID, validation results, and data preview.
    """
    logger.info(f"Received file upload: {file.filename}")
    
    # Validate file type
    if not file.filename.endswith(('.xlsx', '.xls')):
        raise HTTPException(
            status_code=400,
            detail="Invalid file type. Only Excel files (.xlsx, .xls) are supported."
        )
    
    # Create session
    session_store = get_session_store()
    session_id = session_store.create_session()
    session = session_store.get_session(session_id)
    
    try:
        # Save uploaded file to temporary location
        with tempfile.NamedTemporaryFile(delete=False, suffix='.xlsx') as tmp_file:
            content = await file.read()
            tmp_file.write(content)
            tmp_file_path = tmp_file.name
        
        # Load and validate the file
        uploader = DataUploader()
        uploaded_data = uploader.load_excel(tmp_file_path)
        
        # Store in session
        session.uploaded_data = uploaded_data
        
        # Clean up temp file
        Path(tmp_file_path).unlink()
        
        # Convert validation result to Pydantic model
        validation = ValidationResultModel(
            is_valid=uploaded_data.validation.is_valid,
            errors=uploaded_data.validation.errors,
            warnings=uploaded_data.validation.warnings,
            detected_columns=uploaded_data.validation.detected_columns,
            missing_required=uploaded_data.validation.missing_required,
            missing_optional=uploaded_data.validation.missing_optional
        )
        
        # Get preview data (first 10 rows)
        preview_data = uploaded_data.main_df.head(10).to_dict('records')
        
        # Prepare response
        response = UploadResponse(
            session_id=session_id,
            filename=file.filename,
            total_rows=len(uploaded_data.main_df),
            columns=list(uploaded_data.main_df.columns),
            validation=validation,
            preview=preview_data,
            sheet_names=uploaded_data.sheet_names
        )
        
        logger.info(f"File uploaded successfully. Session: {session_id}")
        return response
        
    except Exception as e:
        logger.error(f"Error uploading file: {e}", exc_info=True)
        # Clean up session on error
        session_store.delete_session(session_id)
        raise HTTPException(status_code=500, detail=f"Error processing file: {str(e)}")


@router.get("/{session_id}/preview", response_model=DataPreviewResponse)
async def get_data_preview(
    session_id: str,
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=1000),
    sort_by: Optional[str] = None,
    sort_order: str = Query("asc", pattern="^(asc|desc)$")
):
    """
    Get paginated data preview for a session.
    """
    session_store = get_session_store()
    session = session_store.get_session(session_id)
    
    if not session or not session.uploaded_data:
        raise HTTPException(status_code=404, detail="Session not found or no data uploaded")
    
    df = session.uploaded_data.main_df
    
    # Apply sorting if requested
    if sort_by and sort_by in df.columns:
        ascending = (sort_order == "asc")
        df = df.sort_values(by=sort_by, ascending=ascending)
    
    # Calculate pagination
    total_rows = len(df)
    total_pages = (total_rows + page_size - 1) // page_size
    start_idx = (page - 1) * page_size
    end_idx = start_idx + page_size
    
    # Get page data
    page_data = df.iloc[start_idx:end_idx].to_dict('records')
    
    return DataPreviewResponse(
        data=page_data,
        total_rows=total_rows,
        page=page,
        page_size=page_size,
        total_pages=total_pages
    )


@router.get("/{session_id}/stats", response_model=AllColumnStatsResponse)
async def get_column_stats(session_id: str):
    """
    Get statistics for all columns in the uploaded data.
    """
    session_store = get_session_store()
    session = session_store.get_session(session_id)
    
    if not session or not session.uploaded_data:
        raise HTTPException(status_code=404, detail="Session not found or no data uploaded")
    
    df = session.uploaded_data.main_df
    total_rows = len(df)
    
    column_stats = []
    
    for col in df.columns:
        null_count = df[col].isnull().sum()
        null_percentage = (null_count / total_rows * 100) if total_rows > 0 else 0
        unique_count = df[col].nunique()
        
        # Get sample values (up to 5 unique values)
        sample_values = df[col].dropna().unique()[:5].tolist()
        
        # Get numeric stats if applicable
        numeric_stats = None
        if df[col].dtype in ['int64', 'float64']:
            numeric_stats = {
                'min': float(df[col].min()),
                'max': float(df[col].max()),
                'mean': float(df[col].mean()),
                'median': float(df[col].median()),
                'std': float(df[col].std())
            }
        
        column_stats.append(ColumnStatsResponse(
            column_name=col,
            data_type=str(df[col].dtype),
            null_count=int(null_count),
            null_percentage=round(null_percentage, 2),
            unique_count=int(unique_count),
            sample_values=sample_values,
            numeric_stats=numeric_stats
        ))
    
    return AllColumnStatsResponse(
        columns=column_stats,
        total_rows=total_rows
    )


@router.get("/{session_id}/sheets", response_model=SheetListResponse)
async def get_sheet_list(session_id: str):
    """
    Get list of available sheets in the uploaded file.
    """
    session_store = get_session_store()
    session = session_store.get_session(session_id)
    
    if not session or not session.uploaded_data:
        raise HTTPException(status_code=404, detail="Session not found or no data uploaded")
    
    return SheetListResponse(
        sheets=session.uploaded_data.sheet_names,
        current_sheet=session.uploaded_data.sheet_names[0] if session.uploaded_data.sheet_names else ""
    )
