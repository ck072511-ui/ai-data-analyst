import logging
from typing import Any, Dict, List, Optional
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from app.core.security import get_current_user
from app.services.permission_service import require_permission
from app.services.predictive_analytics_service import predictive_analytics_service
from app.services.prescriptive_service import prescriptive_service

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/predictive", tags=["Predictive & Prescriptive Analytics"])

class TrainRequest(BaseModel):
    dataset_id: str
    target_variable: str
    task_type: str  # "classification", "regression", "forecasting", "clustering"

class PredictRequest(BaseModel):
    model_id: str
    dataset_id: str

class PrescribeRequest(BaseModel):
    model_id: str
    base_features: Dict[str, float]
    actionable_features: List[str]
    business_rules: Dict[str, Any]
    target_direction: Optional[str] = "minimize"  # "minimize" or "maximize"


@router.post("/train", dependencies=[Depends(require_permission("edit"))])
async def train_model(request: TrainRequest, current_user: dict = Depends(get_current_user)):
    try:
        res = await predictive_analytics_service.train_automl_model(
            dataset_id=request.dataset_id,
            target=request.target_variable,
            task_type=request.task_type,
            user_id=current_user["id"]
        )
        return res
    except Exception as e:
        logger.exception("Model training failed")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/predict", dependencies=[Depends(require_permission("view"))])
async def generate_prediction(request: PredictRequest, current_user: dict = Depends(get_current_user)):
    try:
        res = await predictive_analytics_service.generate_predictions(
            model_id=request.model_id,
            dataset_id=request.dataset_id
        )
        return res
    except Exception as e:
        logger.exception("Prediction inference failed")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/prescribe", dependencies=[Depends(require_permission("view"))])
async def generate_prescriptions(request: PrescribeRequest, current_user: dict = Depends(get_current_user)):
    try:
        res = await prescriptive_service.generate_prescriptive_actions(
            model_id=request.model_id,
            base_features=request.base_features,
            actionable_features=request.actionable_features,
            business_rules=request.business_rules,
            target_direction=request.target_direction
        )
        return res
    except Exception as e:
        logger.exception("Prescription generation failed")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/models", dependencies=[Depends(require_permission("view"))])
async def get_models(current_user: dict = Depends(get_current_user)):
    try:
        return await predictive_analytics_service.get_registered_models()
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/history", dependencies=[Depends(require_permission("view"))])
async def get_training_history(current_user: dict = Depends(get_current_user)):
    try:
        return await predictive_analytics_service.get_history()
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
