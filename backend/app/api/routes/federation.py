import json
import logging
from typing import Any, Dict, List, Optional
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from app.core.database import AsyncSessionLocal
from app.core.security import get_current_user
from app.services.permission_service import require_permission
from app.models.federation import FederatedQueryRecord
from app.services.federation_service import federation_service

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/federation", tags=["Federated Query Engine"])

@router.get("/catalog", dependencies=[Depends(require_permission("view"))])
async def get_unified_catalog(current_user: dict = Depends(get_current_user)):
    """Exposes compiled unified catalog exposing tables, columns, dialects, and connections."""
    user_id = current_user["id"]
    try:
        return await federation_service.get_unified_catalog(user_id)
    except Exception as e:
        logger.exception("Failed to build unified virtual schema catalog")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/query", dependencies=[Depends(require_permission("view"))])
async def execute_federated_query(payload: Dict[str, Any], current_user: dict = Depends(get_current_user)):
    """Executes natural language queries across multiple databases."""
    user_id = current_user["id"]
    question = payload.get("query")
    if not question:
        raise HTTPException(status_code=400, detail="Query prompt string is required.")
        
    try:
        res = await federation_service.execute_federated_query(question, user_id)
        return res
    except Exception as e:
        logger.exception("Failed to execute federated query")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/history", dependencies=[Depends(require_permission("view"))])
async def get_query_history(current_user: dict = Depends(get_current_user)):
    """Queries logs history of completed and failed federated executions."""
    user_id = current_user["id"]
    async with AsyncSessionLocal() as session:
        records = (await session.execute(
            select(FederatedQueryRecord)
            .where(FederatedQueryRecord.user_id == user_id)
            .order_by(FederatedQueryRecord.created_at.desc())
            .limit(30)
        )).scalars().all()
        
        return [
            {
                "id": r.id,
                "question": r.question,
                "execution_plan": json.loads(r.execution_plan) if r.execution_plan else {},
                "status": r.status,
                "error_message": r.error_message,
                "latency_ms": r.latency_ms,
                "created_at": r.created_at.isoformat()
            }
            for r in records
        ]

@router.get("/statistics", dependencies=[Depends(require_permission("view"))])
async def get_statistics(current_user: dict = Depends(get_current_user)):
    """Retrieves engine query latencies, success counts, and join timings."""
    try:
        return federation_service.get_statistics()
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
