from fastapi import Depends, HTTPException, Request

from app.core.database import AsyncSessionLocal
from app.core.security import get_current_user
from app.services.rbac_service import has_permission, log_audit_entry


class PermissionChecker:
    def __init__(self, permission: str):
        self.permission = permission

    async def __call__(self, request: Request, current_user: dict = Depends(get_current_user)):
        endpoint = f"{request.method} {request.url.path}"
        user_id = current_user.get("id")
        user_email = current_user.get("email")
        user_role = current_user.get("role", "Viewer")

        # Check permissions cache
        from app.services.cache_service import cache_service

        cache_key = f"user:permissions:{user_id}:{self.permission}"
        cached_allowed = await cache_service.get(cache_key)

        if cached_allowed is not None:
            allowed = cached_allowed
        else:
            allowed = has_permission(user_role, self.permission)
            await cache_service.set(cache_key, allowed, ttl=300)

        if not allowed:
            async with AsyncSessionLocal() as session:
                await log_audit_entry(
                    session=session,
                    user_id=user_id,
                    user_email=user_email,
                    user_role=user_role,
                    endpoint=endpoint,
                    action=f"access_denied:{self.permission}",
                    status="forbidden",
                )
            raise HTTPException(status_code=403, detail="Forbidden: Insufficient permissions")

        async with AsyncSessionLocal() as session:
            await log_audit_entry(
                session=session,
                user_id=user_id,
                user_email=user_email,
                user_role=user_role,
                endpoint=endpoint,
                action=f"access_granted:{self.permission}",
                status="success",
            )

        return current_user


def require_permission(permission: str):
    return PermissionChecker(permission)
