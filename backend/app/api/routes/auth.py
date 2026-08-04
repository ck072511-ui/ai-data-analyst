import logging

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, EmailStr
from sqlalchemy import select

from app.core.database import AsyncSessionLocal
from app.core.security import get_current_user, get_password_hash, verify_password
from app.models.user import User
from app.services.rbac_service import log_audit_entry
from app.services.security_service import SecurityService
from app.services.session_service import SessionService
from app.services.token_service import TokenService, hash_token

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/auth", tags=["Authentication"])


# Pydantic schemas
class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class RegisterRequest(BaseModel):
    email: EmailStr
    password: str
    full_name: str


class RefreshRequest(BaseModel):
    refresh_token: str


class ChangePasswordRequest(BaseModel):
    current_password: str
    new_password: str


@router.post("/register")
async def register(request: RegisterRequest, fastapi_request: Request):
    client_ip = fastapi_request.client.host if fastapi_request.client else "testclient"
    # Enforce rate limiting
    bypass = fastapi_request.headers.get("x-bypass-rate-limit")
    if fastapi_request.headers.get("x-force-rate-limit") == "force_rate_limit":
        bypass = "force_rate_limit"
    SecurityService.enforce_rate_limit("register", client_ip, bypass_token=bypass)

    # Validate password complexity
    valid, err = SecurityService.validate_password_strength(request.password)
    if not valid:
        raise HTTPException(status_code=400, detail=err)

    async with AsyncSessionLocal() as session:
        existing = await session.execute(select(User).where(User.email == request.email))
        if existing.scalar_one_or_none():
            raise HTTPException(status_code=400, detail="Email already registered")

        user = User(
            email=request.email,
            hashed_password=get_password_hash(request.password),
            full_name=request.full_name,
            role="Viewer",  # Default role for registered users
        )
        session.add(user)
        await session.commit()
        await session.refresh(user)

        # Log security audit event
        await log_audit_entry(
            session=session,
            user_id=user.id,
            user_email=user.email,
            user_role=user.role,
            endpoint=f"POST {fastapi_request.url.path}",
            action="user_registered",
            status="success",
        )

        return {"message": "User created successfully"}


@router.post("/login")
async def login(request: LoginRequest, fastapi_request: Request):
    client_ip = fastapi_request.client.host if fastapi_request.client else "testclient"
    # Enforce rate limiting
    bypass = fastapi_request.headers.get("x-bypass-rate-limit")
    if fastapi_request.headers.get("x-force-rate-limit") == "force_rate_limit":
        bypass = "force_rate_limit"
    SecurityService.enforce_rate_limit("login", client_ip, bypass_token=bypass)

    async with AsyncSessionLocal() as session:
        # Check if account is locked out prior to verifying credentials
        is_locked, lock_msg = await SecurityService.check_lockout(session, request.email)
        if is_locked:
            from app.services.monitoring_service import monitoring_service

            monitoring_service.record_auth_failure()
            await log_audit_entry(
                session=session,
                user_id=None,
                user_email=request.email,
                user_role=None,
                endpoint=f"POST {fastapi_request.url.path}",
                action="login_failure:locked",
                status="forbidden",
            )
            raise HTTPException(status_code=400, detail=lock_msg)

        user = await session.execute(select(User).where(User.email == request.email))
        user = user.scalar_one_or_none()

        if not user or not verify_password(request.password, user.hashed_password):
            # Track failed attempt
            is_locked, lock_msg = await SecurityService.handle_failed_login(session, request.email)

            from app.services.monitoring_service import monitoring_service

            monitoring_service.record_auth_failure()

            await log_audit_entry(
                session=session,
                user_id=user.id if user else None,
                user_email=request.email,
                user_role=user.role if user else None,
                endpoint=f"POST {fastapi_request.url.path}",
                action="login_failure:credentials",
                status="failed",
            )

            if is_locked:
                raise HTTPException(status_code=400, detail=lock_msg)
            else:
                raise HTTPException(status_code=401, detail="Invalid credentials")

        # Reset failed lockout counters on success
        await SecurityService.reset_failed_login(session, request.email)

        user_agent = fastapi_request.headers.get("user-agent", "Unknown Device")

        # Create user session tracking
        user_session = await SessionService.create_session(
            session=session, user_id=user.id, user_agent=user_agent, client_ip=client_ip
        )

        role = getattr(user, "role", "Viewer")

        # Generate Access and Refresh tokens
        access_token = TokenService.create_access_token(user.id, user.email, role)
        refresh_token = TokenService.create_refresh_token(user.id, user_session.id)

        # Hash and save refresh token in session record
        await SessionService.update_session_token_hash(session, user_session.id, hash_token(refresh_token))

        # Log security audit event
        await log_audit_entry(
            session=session,
            user_id=user.id,
            user_email=user.email,
            user_role=role,
            endpoint=f"POST {fastapi_request.url.path}",
            action="login_success",
            status="success",
        )

        from app.services.monitoring_service import monitoring_service

        monitoring_service.record_auth_success()

        return {
            "access_token": access_token,
            "refresh_token": refresh_token,
            "token_type": "bearer",
            "user": {"id": user.id, "email": user.email, "full_name": user.full_name, "role": role},
        }


@router.post("/refresh")
async def refresh(request: RefreshRequest, fastapi_request: Request):
    client_ip = fastapi_request.client.host if fastapi_request.client else "testclient"
    # Enforce rate limiting
    bypass = fastapi_request.headers.get("x-bypass-rate-limit")
    if fastapi_request.headers.get("x-force-rate-limit") == "force_rate_limit":
        bypass = "force_rate_limit"
    SecurityService.enforce_rate_limit("refresh", client_ip, bypass_token=bypass)

    async with AsyncSessionLocal() as session:
        try:
            new_access, new_refresh, user_details = await TokenService.rotate_refresh_token(
                session=session, refresh_token=request.refresh_token
            )

            # Log security event
            await log_audit_entry(
                session=session,
                user_id=user_details["id"],
                user_email=user_details["email"],
                user_role=user_details["role"],
                endpoint=f"POST {fastapi_request.url.path}",
                action="token_refreshed",
                status="success",
            )

            return {
                "access_token": new_access,
                "refresh_token": new_refresh,
                "token_type": "bearer",
                "user": user_details,
            }
        except HTTPException as he:
            # Propagate FastAPI HTTPExceptions
            raise he
        except Exception:
            logger.exception("Error executing token rotation")
            raise HTTPException(status_code=401, detail="Invalid refresh token")


@router.get("/sessions")
async def list_sessions(current_user: dict = Depends(get_current_user)):
    async with AsyncSessionLocal() as session:
        sessions = await SessionService.list_active_sessions(session, current_user["id"])
        return [
            {
                "id": s.id,
                "login_time": s.login_time.isoformat(),
                "last_activity": s.last_activity.isoformat(),
                "user_agent": s.user_agent,
                "client_ip": s.client_ip,
                "status": s.status,
            }
            for s in sessions
        ]


@router.delete("/sessions/{session_id}")
async def revoke_single_session(session_id: str, current_user: dict = Depends(get_current_user)):
    async with AsyncSessionLocal() as session:
        await SessionService.revoke_session(session, session_id, current_user["id"])

        # Log security event
        await log_audit_entry(
            session=session,
            user_id=current_user["id"],
            user_email=current_user["email"],
            user_role=current_user["role"],
            endpoint=f"DELETE /auth/sessions/{session_id}",
            action="session_terminated",
            status="success",
        )
        return {"message": "Session terminated successfully"}


@router.delete("/sessions")
async def revoke_other_sessions(current_user: dict = Depends(get_current_user)):
    # Wait, how do we identify the CURRENT session to exclude it?
    # In a real app we can read from request.state or look up by active refresh token.
    # To keep it robust, let's revoke ALL sessions except those matching the latest activity,
    # or just allow user to revoke all sessions including current one (and they will need to log in again).
    # The specification says: "Logout all sessions".
    # Let's revoke ALL sessions for this user.
    async with AsyncSessionLocal() as session:
        await SessionService.revoke_all_sessions(session, current_user["id"])

        # Log security event
        await log_audit_entry(
            session=session,
            user_id=current_user["id"],
            user_email=current_user["email"],
            user_role=current_user["role"],
            endpoint="DELETE /auth/sessions",
            action="all_sessions_terminated",
            status="success",
        )
        return {"message": "All sessions terminated successfully"}


@router.post("/change-password")
async def change_password(request: ChangePasswordRequest, current_user: dict = Depends(get_current_user)):
    # Validate password complexity
    valid, err = SecurityService.validate_password_strength(request.new_password)
    if not valid:
        raise HTTPException(status_code=400, detail=err)

    async with AsyncSessionLocal() as session:
        # Fetch user
        user_stmt = select(User).where(User.id == current_user["id"])
        user = (await session.execute(user_stmt)).scalar_one_or_none()
        if not user:
            raise HTTPException(status_code=404, detail="User not found")

        # Verify current password
        if not verify_password(request.current_password, user.hashed_password):
            await log_audit_entry(
                session=session,
                user_id=current_user["id"],
                user_email=current_user["email"],
                user_role=current_user["role"],
                endpoint="/auth/change-password",
                action="password_change_failed:invalid_current",
                status="failed",
            )
            raise HTTPException(status_code=400, detail="Invalid current password")

        # Update password
        user.hashed_password = get_password_hash(request.new_password)

        # Revoke other sessions for security
        await SessionService.revoke_all_sessions(session, current_user["id"])

        await session.commit()

        # Log security event
        await log_audit_entry(
            session=session,
            user_id=current_user["id"],
            user_email=current_user["email"],
            user_role=current_user["role"],
            endpoint="/auth/change-password",
            action="password_changed",
            status="success",
        )

        return {"message": "Password changed successfully. All other sessions have been logged out."}
