import logging

from fastapi import APIRouter, Depends

from app.core.security import get_current_user
from app.services.permission_service import require_permission
from app.services.worker_service import worker_service

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/workers", tags=["Workers"])


@router.get("/health", dependencies=[Depends(require_permission("view"))])
async def get_worker_health(current_user: dict = Depends(get_current_user)):
    """Checks Redis connectivity, Celery active status, and queue backlog size"""
    status = worker_service.get_worker_health_status()
    return status
