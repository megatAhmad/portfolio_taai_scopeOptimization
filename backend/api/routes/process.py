"""
Process API routes for MWCS Backend.

Handles data processing, WebSocket progress updates, and status monitoring.
"""

import logging
from fastapi import APIRouter, HTTPException, WebSocket, WebSocketDisconnect

from api.models.process import (
    ProcessRequest,
    ProcessStatusResponse,
    ProcessSummaryResponse
)
from api.services.session_store import get_session_store
from api.services.websocket import get_connection_manager

logger = logging.getLogger(__name__)

router = APIRouter()


@router.post("/{session_id}", response_model=ProcessStatusResponse)
async def start_processing(session_id: str, request: ProcessRequest):
    """Start processing the uploaded data with configured rules."""
    session_store = get_session_store()
    session = session_store.get_session(session_id)
    
    if not session or not session.uploaded_data:
        raise HTTPException(status_code=404, detail="Session not found or no data uploaded")
    
    if not session.rule_builder or not session.rule_builder.rules:
        raise HTTPException(status_code=400, detail="No rules configured")
    
    # Update session status
    session.processing_status = "processing"
    session.processing_progress = 0.0
    
    # TODO: Implement actual processing logic
    # This should run in background and update progress via WebSocket
    
    logger.info(f"Started processing for session {session_id}")
    
    return ProcessStatusResponse(
        session_id=session_id,
        status="processing",
        progress=0.0,
        total_rows=len(session.uploaded_data.main_df),
        message="Processing started"
    )


@router.websocket("/ws/{session_id}")
async def websocket_endpoint(websocket: WebSocket, session_id: str):
    """WebSocket endpoint for real-time progress updates."""
    connection_manager = get_connection_manager()
    
    await connection_manager.connect(websocket, session_id)
    
    try:
        while True:
            # Keep connection alive and receive any client messages
            data = await websocket.receive_text()
            logger.debug(f"Received WebSocket message: {data}")
            
    except WebSocketDisconnect:
        connection_manager.disconnect(websocket, session_id)
        logger.info(f"WebSocket disconnected for session {session_id}")


@router.get("/{session_id}/status", response_model=ProcessStatusResponse)
async def get_processing_status(session_id: str):
    """Get current processing status."""
    session_store = get_session_store()
    session = session_store.get_session(session_id)
    
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    
    total_rows = len(session.uploaded_data.main_df) if session.uploaded_data else 0
    
    return ProcessStatusResponse(
        session_id=session_id,
        status=session.processing_status,
        progress=session.processing_progress,
        total_rows=total_rows,
        error=session.processing_error
    )


@router.get("/{session_id}/summary", response_model=ProcessSummaryResponse)
async def get_processing_summary(session_id: str):
    """Get processing summary after completion."""
    session_store = get_session_store()
    session = session_store.get_session(session_id)
    
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    
    if session.processing_status != "completed":
        raise HTTPException(status_code=400, detail="Processing not completed")
    
    # TODO: Calculate actual summary from results
    return ProcessSummaryResponse(
        session_id=session_id,
        total_processed=0,
        accepted_count=0,
        reconsider_count=0,
        rejected_count=0,
        processing_time_seconds=0.0,
        rules_applied=0,
        justifications_generated=0,
        summary_stats={}
    )
