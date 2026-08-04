from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from app.core.security import get_current_user
from app.services.permission_service import require_permission
from app.services.prompt_service import PromptService
from app.services.prompt_version_service import PromptVersionService

router = APIRouter(prefix="/prompts", tags=["Prompt Management Engine"])
service = PromptService()
version_service = PromptVersionService()

class PromptCreateRequest(BaseModel):
    name: str
    category: str
    content: str

class PromptUpdateRequest(BaseModel):
    content: str
    change_log: str

class RollbackRequest(BaseModel):
    target_version: int


@router.get("", dependencies=[Depends(require_permission("view"))])
async def list_prompts(current_user: dict = Depends(get_current_user)):
    """Retrieves list of active prompt templates."""
    return await service.list_prompts()


@router.post("", dependencies=[Depends(require_permission("view"))])
async def create_prompt(request: PromptCreateRequest, current_user: dict = Depends(get_current_user)):
    """Creates a new prompt."""
    res = await service.create_prompt(
        name=request.name,
        category=request.category,
        content=request.content,
        author=current_user["username"]
    )
    if "error" in res:
        raise HTTPException(status_code=400, detail=res["error"])
    return res


@router.get("/{id}", dependencies=[Depends(require_permission("view"))])
async def get_prompt(id: str, current_user: dict = Depends(get_current_user)):
    """Queries prompt details."""
    res = await service.get_prompt(prompt_id=id)
    if "error" in res:
        raise HTTPException(status_code=404, detail=res["error"])
    return res


@router.put("/{id}", dependencies=[Depends(require_permission("view"))])
async def update_prompt(id: str, request: PromptUpdateRequest, current_user: dict = Depends(get_current_user)):
    """Updates prompt template content, incrementing version numbers."""
    res = await service.update_prompt(
        prompt_id=id,
        content=request.content,
        change_log=request.change_log,
        author=current_user["username"]
    )
    if "error" in res:
        raise HTTPException(status_code=400, detail=res["error"])
    return res


@router.get("/{id}/versions", dependencies=[Depends(require_permission("view"))])
async def get_prompt_versions(id: str, current_user: dict = Depends(get_current_user)):
    """Retrieves historical versions list for a template."""
    return await version_service.list_versions(prompt_id=id)


@router.post("/{id}/rollback", dependencies=[Depends(require_permission("view"))])
async def rollback_prompt(id: str, request: RollbackRequest, current_user: dict = Depends(get_current_user)):
    """Rollbacks the active prompt template content back to a historical version."""
    res = await version_service.rollback_to_version(
        prompt_id=id,
        target_ver=request.target_version,
        author=current_user["username"]
    )
    if "error" in res:
        raise HTTPException(status_code=400, detail=res["error"])
    return res
