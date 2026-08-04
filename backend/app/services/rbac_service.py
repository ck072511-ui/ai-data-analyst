import logging
from typing import Any, Dict, List, Optional

from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.audit_log import SystemAuditLog
from app.models.user import User

logger = logging.getLogger(__name__)

# Role Constants
ROLE_ADMIN = "Admin"
ROLE_SCIENTIST = "Data Scientist"
ROLE_ANALYST = "Data Analyst"
ROLE_VIEWER = "Viewer"

ALL_ROLES = [ROLE_ADMIN, ROLE_SCIENTIST, ROLE_ANALYST, ROLE_VIEWER]

# Permissions Mapping
ROLE_PERMISSIONS: Dict[str, List[str]] = {
    ROLE_ADMIN: [
        "user_management",
        "rollback",
        "versioning",
        "ai_recommendations",
        "clean",
        "upload",
        "analyze",
        "profile",
        "dashboard_write",
        "view",
    ],
    ROLE_SCIENTIST: [
        "rollback",
        "versioning",
        "ai_recommendations",
        "clean",
        "upload",
        "analyze",
        "profile",
        "dashboard_write",
        "view",
    ],
    ROLE_ANALYST: ["clean", "upload", "analyze", "profile", "dashboard_write", "view"],
    ROLE_VIEWER: ["view"],
}


def has_permission(role: str, permission: str) -> bool:
    """Checks if a role has the required permission."""
    allowed = ROLE_PERMISSIONS.get(role, [])
    return permission in allowed


async def log_audit_entry(
    session: AsyncSession,
    user_id: Optional[str],
    user_email: Optional[str],
    user_role: Optional[str],
    endpoint: str,
    action: str,
    status: str,
) -> None:
    """Writes a structured log access entry to the system_audit_logs table."""
    try:
        log_item = SystemAuditLog(
            user_id=user_id, user_email=user_email, user_role=user_role, endpoint=endpoint, action=action, status=status
        )
        session.add(log_item)
        await session.commit()
    except Exception as e:
        logger.error(f"Failed to write system audit log: {e}")


async def change_user_role_service(
    session: AsyncSession, target_user_id: str, new_role: str, actor_user: dict
) -> Dict[str, Any]:
    """Updates a user's role in the database. Verifies permissions and roles list validity."""
    if new_role not in ALL_ROLES:
        raise HTTPException(status_code=400, detail=f"Invalid role. Allowed roles: {ALL_ROLES}")

    # Prevent privilege escalation
    if actor_user.get("role") != ROLE_ADMIN:
        raise HTTPException(status_code=403, detail="Only Admins can change user roles")

    stmt = select(User).where(User.id == target_user_id)
    user = (await session.execute(stmt)).scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    old_role = getattr(user, "role", "Viewer")
    user.role = new_role
    await session.commit()
    await session.refresh(user)

    logger.info(f"User {user.email} role updated from {old_role} to {new_role} by Admin {actor_user.get('email')}")
    return {"user_id": user.id, "email": user.email, "old_role": old_role, "new_role": user.role}
