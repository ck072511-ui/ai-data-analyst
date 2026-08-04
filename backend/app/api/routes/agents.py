from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from app.core.security import get_current_user
from app.services.permission_service import require_permission
from app.services.agent_manager import AgentManager

router = APIRouter(prefix="/agents", tags=["Multi-Agent Analytics Engine"])
manager = AgentManager()

class QueryRequest(BaseModel):
    question: str
    dataset_id: str

class ReplayRequest(BaseModel):
    execution_id: str


@router.post("/query", dependencies=[Depends(require_permission("view"))])
async def run_multi_agent_query(
    request: QueryRequest,
    current_user: dict = Depends(get_current_user)
):
    """Triggers collaborative multi-agent execution tasks."""
    try:
        return await manager.run_analytics_query(
            user_query=request.question,
            dataset_id=request.dataset_id,
            user_id=current_user["id"]
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/history", dependencies=[Depends(require_permission("view"))])
async def get_multi_agent_history(current_user: dict = Depends(get_current_user)):
    """Retrieve all execution history details."""
    return await manager.list_history(user_id=current_user["id"])


@router.get("/status/{execution_id}", dependencies=[Depends(require_permission("view"))])
async def get_multi_agent_status(execution_id: str, current_user: dict = Depends(get_current_user)):
    """Stream active progress logs of executing tasks."""
    res = await manager.get_execution_status(execution_id)
    if "error" in res:
        raise HTTPException(status_code=404, detail=res["error"])
    return res


@router.post("/replay", dependencies=[Depends(require_permission("view"))])
async def replay_prior_execution(
    request: ReplayRequest,
    current_user: dict = Depends(get_current_user)
):
    """Replays intermediate steps and configurations directly from history logs."""
    res = await manager.replay_execution(request.execution_id)
    if "error" in res:
        raise HTTPException(status_code=404, detail=res["error"])
    return res
