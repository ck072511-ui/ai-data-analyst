from typing import Optional
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from app.core.security import get_current_user
from app.services.permission_service import require_permission
from app.services.evaluation_service import EvaluationService

router = APIRouter(prefix="/evaluation", tags=["AI Evaluation Engine"])
service = EvaluationService()

class EvaluationRunRequest(BaseModel):
    prompt_id: str
    model_name: str
    compare_model_name: Optional[str] = None


@router.post("/run", dependencies=[Depends(require_permission("view"))])
async def run_prompt_evaluation(request: EvaluationRunRequest, current_user: dict = Depends(get_current_user)):
    """Triggers prompt evaluations or runs A/B side-by-side models checks."""
    if request.compare_model_name:
        return await service.run_ab_comparison(
            prompt_id=request.prompt_id,
            model_a=request.model_name,
            model_b=request.compare_model_name
        )
    
    res = await service.run_evaluation(
        prompt_id=request.prompt_id,
        model_name=request.model_name
    )
    if "error" in res:
        raise HTTPException(status_code=500, detail=res["error"])
    return res


@router.get("/history", dependencies=[Depends(require_permission("view"))])
async def list_evaluation_history(current_user: dict = Depends(get_current_user)):
    """Retrieves list of benchmark histories."""
    return await service.list_history()
