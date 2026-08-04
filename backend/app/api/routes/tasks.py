import logging
from typing import Any, Dict, Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from app.core.database import AsyncSessionLocal
from app.core.security import get_current_user
from app.services.notification_service import notification_service
from app.services.permission_service import require_permission
from app.services.task_service import task_service

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/tasks", tags=["Tasks"])


class TaskRunRequest(BaseModel):
    task_type: str
    dataset_id: Optional[str] = None
    payload: Optional[Dict[str, Any]] = None


@router.post("/run", dependencies=[Depends(require_permission("view"))])
async def run_task_endpoint(request: TaskRunRequest, current_user: dict = Depends(get_current_user)):
    """Triggers background task run manually"""
    user_id = current_user["id"]
    try:
        task = await task_service.create_task(
            task_type=request.task_type, user_id=user_id, dataset_id=request.dataset_id, payload=request.payload
        )
        return {
            "task_id": task.id,
            "task_type": task.task_type,
            "status": task.status,
            "progress": task.progress,
            "created_at": task.started_at.isoformat() if task.started_at else None,
        }
    except Exception as e:
        logger.exception("Failed to run task manually")
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/", dependencies=[Depends(require_permission("view"))])
async def list_tasks_endpoint(
    page: int = 1,
    page_size: int = 10,
    sort_by: str = "started_at",
    sort_order: str = "desc",
    search: str = None,
    paginated: bool = False,
    current_user: dict = Depends(get_current_user),
):
    """Lists all task records for current user, optionally paginated."""
    user_id = current_user["id"]
    from sqlalchemy import select

    from app.models.task import Task

    async with AsyncSessionLocal() as session:
        base_stmt = select(Task).where(Task.user_id == user_id)

        if paginated:
            from app.utils.pagination import paginate

            tasks, meta = await paginate(
                session=session,
                model=Task,
                page=page,
                page_size=page_size,
                sort_by=sort_by,
                sort_order=sort_order,
                search=search,
                search_fields=["task_type", "status"],
                base_query=base_stmt,
            )
            items = [
                {
                    "id": t.id,
                    "task_type": t.task_type,
                    "status": t.status,
                    "progress": t.progress,
                    "started_at": t.started_at.isoformat() if t.started_at else None,
                    "finished_at": t.finished_at.isoformat() if t.finished_at else None,
                    "error_message": t.error_message,
                    "dataset_id": t.dataset_id,
                }
                for t in tasks
            ]
            return {"items": items, "pagination": meta}
        else:
            tasks = await task_service.list_tasks(user_id, session)
            if search:
                tasks = [
                    t
                    for t in tasks
                    if search.lower() in t.task_type.lower() or (t.status and search.lower() in t.status.lower())
                ]
            return [
                {
                    "id": t.id,
                    "task_type": t.task_type,
                    "status": t.status,
                    "progress": t.progress,
                    "started_at": t.started_at.isoformat() if t.started_at else None,
                    "finished_at": t.finished_at.isoformat() if t.finished_at else None,
                    "error_message": t.error_message,
                    "dataset_id": t.dataset_id,
                }
                for t in tasks
            ]


@router.get("/notifications", dependencies=[Depends(require_permission("view"))])
async def get_notifications_endpoint(current_user: dict = Depends(get_current_user)):
    """Poll for current user's unread toast notifications"""
    user_id = current_user["id"]
    notifications = notification_service.get_unread(user_id)
    return {"notifications": notifications}


@router.get("/{task_id}", dependencies=[Depends(require_permission("view"))])
async def get_task_endpoint(task_id: str, current_user: dict = Depends(get_current_user)):
    """Gets details for a specific task"""
    user_id = current_user["id"]
    async with AsyncSessionLocal() as session:
        task = await task_service.get_task(task_id, session)
        if not task:
            raise HTTPException(status_code=404, detail="Task not found")
        if task.user_id != user_id:
            raise HTTPException(status_code=403, detail="Forbidden")

        return {
            "id": task.id,
            "task_type": task.task_type,
            "status": task.status,
            "progress": task.progress,
            "started_at": task.started_at.isoformat() if task.started_at else None,
            "finished_at": task.finished_at.isoformat() if task.finished_at else None,
            "error_message": task.error_message,
            "dataset_id": task.dataset_id,
        }


@router.post("/{task_id}/retry", dependencies=[Depends(require_permission("view"))])
async def retry_task_endpoint(task_id: str, current_user: dict = Depends(get_current_user)):
    """Retries a failed background task"""
    user_id = current_user["id"]
    async with AsyncSessionLocal() as session:
        task = await task_service.get_task(task_id, session)
        if not task:
            raise HTTPException(status_code=404, detail="Task not found")
        if task.user_id != user_id:
            raise HTTPException(status_code=403, detail="Forbidden")

        if task.status != "failed":
            raise HTTPException(status_code=400, detail="Only failed tasks can be retried")

        retried = await task_service.retry_task(task_id, session)
        return {"task_id": retried.id, "status": retried.status, "progress": retried.progress}


@router.delete("/{task_id}", dependencies=[Depends(require_permission("view"))])
async def delete_task_endpoint(task_id: str, current_user: dict = Depends(get_current_user)):
    """Cancels or deletes a background task"""
    user_id = current_user["id"]
    async with AsyncSessionLocal() as session:
        task = await task_service.get_task(task_id, session)
        if not task:
            raise HTTPException(status_code=404, detail="Task not found")
        if task.user_id != user_id:
            raise HTTPException(status_code=403, detail="Forbidden")

        success = await task_service.delete_task(task_id, session)
        return {"success": success}
