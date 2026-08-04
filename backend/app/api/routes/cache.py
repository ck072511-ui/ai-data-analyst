from fastapi import APIRouter, Depends
from pydantic import BaseModel

from app.core.security import get_current_user
from app.services.cache_service import cache_service
from app.services.permission_service import require_permission

router = APIRouter(prefix="/cache", tags=["Cache Operations"])


class InvalidateRequest(BaseModel):
    pattern: str


@router.get("/stats", dependencies=[Depends(require_permission("view"))])
async def get_cache_stats(current_user: dict = Depends(get_current_user)):
    """Returns Redis keys count, hit/miss rates, memory usage, and availability status."""
    return cache_service.get_stats()


@router.post("/clear", dependencies=[Depends(require_permission("user_management"))])
async def clear_cache_endpoint(current_user: dict = Depends(get_current_user)):
    """Clears all cached items from Redis and memory fallback (Admin only)."""
    await cache_service.clear()
    return {"success": True, "message": "Cache successfully cleared."}


@router.post("/invalidate", dependencies=[Depends(require_permission("user_management"))])
async def invalidate_cache_pattern(request: InvalidateRequest, current_user: dict = Depends(get_current_user)):
    """Invalidates all keys matching a glob pattern (Admin only)."""
    await cache_service.invalidate_pattern(request.pattern)
    return {"success": True, "message": f"Keys matching pattern '{request.pattern}' successfully invalidated."}
