from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Body
from pydantic import BaseModel

from app.core.security import get_current_user
from app.services.permission_service import require_permission
from app.services.ai_cleaning_service import AICleaningService

router = APIRouter(prefix="/ai-cleaning", tags=["AI Cleaning Assistant"])
service = AICleaningService()

class ApproveRequest(BaseModel):
    recommendation_id: str
    approved_step_ids: List[int]

class ExecuteRequest(BaseModel):
    recommendation_id: str


@router.get("/recommendations/{dataset_id}", dependencies=[Depends(require_permission("clean"))])
async def get_or_generate_recommendations(
    dataset_id: str,
    current_user: dict = Depends(get_current_user)
):
    """Retrieve existing pending recommendations or trigger local LLM to generate a cleaning plan."""
    return await service.generate_recommendations(
        dataset_id=dataset_id,
        user_id=current_user["id"]
    )


@router.post("/approve", dependencies=[Depends(require_permission("clean"))])
async def approve_recommendation_steps(
    request: ApproveRequest,
    current_user: dict = Depends(get_current_user)
):
    """Save approved checklist steps selected by the user."""
    return await service.approve_recommendation(
        recommendation_id=request.recommendation_id,
        approved_step_ids=request.approved_step_ids,
        user_id=current_user["id"]
    )


@router.post("/execute", dependencies=[Depends(require_permission("clean"))])
async def execute_approved_cleaning_plan(
    request: ExecuteRequest,
    current_user: dict = Depends(get_current_user)
):
    """Trigger the background pipeline to clean the dataset based on approved steps."""
    return await service.execute_recommendation(
        recommendation_id=request.recommendation_id,
        user_id=current_user["id"]
    )


@router.get("/history/{dataset_id}", dependencies=[Depends(require_permission("view"))])
async def get_ai_cleaning_history(
    dataset_id: str,
    current_user: dict = Depends(get_current_user)
):
    """List prior AI cleaning plans and execution states."""
    return await service.get_history(dataset_id=dataset_id)
