import logging
from typing import Dict

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select

from app.core.database import AsyncSessionLocal
from app.core.security import get_current_user
from app.models.user import User
from app.services.permission_service import require_permission
from app.services.rbac_service import ALL_ROLES, change_user_role_service

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/users", tags=["Users"])


@router.get("/me")
async def get_my_profile(current_user: dict = Depends(get_current_user)):
    """Returns profile information for the authenticated user, including their role."""
    user_id = current_user["id"]
    from app.services.cache_service import cache_service

    cache_key = f"user:profile:{user_id}"
    cached_res = await cache_service.get(cache_key)
    if cached_res is not None:
        return cached_res

    res = {
        "id": current_user["id"],
        "email": current_user["email"],
        "full_name": current_user.get("full_name"),
        "role": current_user["role"],
        "is_active": current_user.get("is_active"),
    }
    await cache_service.set(cache_key, res, ttl=300)
    return res


@router.get("/roles", dependencies=[Depends(require_permission("user_management"))])
async def list_users_and_roles(
    page: int = 1,
    page_size: int = 10,
    sort_by: str = "created_at",
    sort_order: str = "desc",
    search: str = None,
    paginated: bool = False,
    current_user: dict = Depends(get_current_user),
):
    """Returns a list of all users and their roles, plus the available roles in the system.
    Only accessible by Admin (user_management permission)."""
    from app.services.cache_service import cache_service

    cache_key = f"user:list:p_{page}:ps_{page_size}:sb_{sort_by}:so_{sort_order}:s_{search}:pag_{paginated}"
    cached_res = await cache_service.get(cache_key)
    if cached_res is not None:
        return cached_res

    async with AsyncSessionLocal() as session:
        base_stmt = select(User)

        if paginated:
            from app.utils.pagination import paginate

            users, meta = await paginate(
                session=session,
                model=User,
                page=page,
                page_size=page_size,
                sort_by=sort_by,
                sort_order=sort_order,
                search=search,
                search_fields=["full_name", "email"],
                base_query=base_stmt,
            )
            user_list = [
                {
                    "id": u.id,
                    "email": u.email,
                    "full_name": u.full_name,
                    "role": getattr(u, "role", "Viewer"),
                    "is_active": u.is_active,
                    "created_at": u.created_at.isoformat(),
                }
                for u in users
            ]
            res = {"users": user_list, "pagination": meta, "roles": ALL_ROLES}
        else:
            stmt = base_stmt.order_by(User.created_at.desc())
            if search:
                from sqlalchemy import or_

                stmt = stmt.where(or_(User.full_name.ilike(f"%{search}%"), User.email.ilike(f"%{search}%")))
            users = (await session.execute(stmt)).scalars().all()
            user_list = [
                {
                    "id": u.id,
                    "email": u.email,
                    "full_name": u.full_name,
                    "role": getattr(u, "role", "Viewer"),
                    "is_active": u.is_active,
                    "created_at": u.created_at.isoformat(),
                }
                for u in users
            ]
            res = {"users": user_list, "roles": ALL_ROLES}

        await cache_service.set(cache_key, res, ttl=300)
        return res


@router.patch("/{user_id}/role", dependencies=[Depends(require_permission("user_management"))])
async def update_user_role(user_id: str, payload: Dict[str, str], current_user: dict = Depends(get_current_user)):
    """Updates a user's role.
    Only accessible by Admin (user_management permission)."""
    new_role = payload.get("role")
    if not new_role:
        raise HTTPException(status_code=400, detail="Field 'role' is required")

    async with AsyncSessionLocal() as session:
        result = await change_user_role_service(
            session=session, target_user_id=user_id, new_role=new_role, actor_user=current_user
        )

        # Invalidate user cache entries
        from app.services.cache_service import cache_service

        await cache_service.invalidate_user(user_id)
        await cache_service.invalidate_pattern(f"user:permissions:{user_id}:*")
        await cache_service.invalidate_pattern("user:list:*")

        return result
