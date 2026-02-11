"""
Preview API routes for MWCS Backend.

Handles rule flowchart and sample evaluation preview.
"""

import logging
from fastapi import APIRouter, HTTPException

from api.models.process import PreviewResponse
from api.services.session_store import get_session_store

logger = logging.getLogger(__name__)

router = APIRouter()


@router.get("/{session_id}/flowchart")
async def get_flowchart(session_id: str):
    """Get flowchart data for rule visualization."""
    session_store = get_session_store()
    session = session_store.get_session(session_id)
    
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    
    # TODO: Generate flowchart data from rules
    flowchart_data = {
        "nodes": [],
        "edges": []
    }
    
    return flowchart_data


@router.get("/{session_id}/sample")
async def get_sample_preview(session_id: str, sample_size: int = 5):
    """Get sample evaluation preview."""
    session_store = get_session_store()
    session = session_store.get_session(session_id)
    
    if not session or not session.uploaded_data:
        raise HTTPException(status_code=404, detail="Session not found or no data uploaded")
    
    # TODO: Run sample evaluation
    sample_evaluations = []
    
    return PreviewResponse(
        flowchart_data={"nodes": [], "edges": []},
        sample_evaluations=sample_evaluations
    )
