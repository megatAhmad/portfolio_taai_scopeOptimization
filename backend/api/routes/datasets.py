"""
Datasets API routes for MWCS Backend.

Handles supporting datasets for lookups and enrichment.
"""

import logging
from fastapi import APIRouter, HTTPException

from api.services.session_store import get_session_store

logger = logging.getLogger(__name__)

router = APIRouter()


@router.get("/equipment-classification")
async def get_equipment_classification():
    """Get equipment classification dataset."""
    # TODO: Load from supporting_datasets.py
    return {"data": []}


@router.get("/work-type")
async def get_work_type():
    """Get work type categories dataset."""
    # TODO: Load from supporting_datasets.py
    return {"data": []}


@router.get("/redundancy")
async def get_redundancy():
    """Get equipment redundancy dataset."""
    # TODO: Load from supporting_datasets.py
    return {"data": []}


@router.get("/decision-matrix")
async def get_decision_matrix():
    """Get decision matrix dataset."""
    # TODO: Load from supporting_datasets.py
    return {"data": []}
