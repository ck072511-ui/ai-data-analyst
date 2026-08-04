from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from app.core.security import get_current_user
from app.services.permission_service import require_permission
from app.services.model_registry_service import ModelRegistryService

router = APIRouter(prefix="/models", tags=["Model Registry Engine"])
service = ModelRegistryService()

class ActivateModelRequest(BaseModel):
    model_id: str


@router.get("", dependencies=[Depends(require_permission("view"))])
async def list_registered_models(current_user: dict = Depends(get_current_user)):
    """List registered local models."""
    return await service.list_models()


@router.post("/activate", dependencies=[Depends(require_permission("view"))])
async def activate_system_model(request: ActivateModelRequest, current_user: dict = Depends(get_current_user)):
    """Toggles active default model status."""
    res = await service.activate_model(model_id=request.model_id)
    if "error" in res:
        raise HTTPException(status_code=400, detail=res["error"])
    return res
