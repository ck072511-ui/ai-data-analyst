import hashlib
import logging
import uuid
from datetime import datetime, timedelta
from typing import Any, Dict, Tuple

from fastapi import HTTPException
from jose import JWTError, jwt
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.models.session import UserSession
from app.models.token import RevokedRefreshToken

logger = logging.getLogger(__name__)

# Token configuration constants
ACCESS_TOKEN_EXPIRE_MINUTES = 15
REFRESH_TOKEN_EXPIRE_DAYS = 7


def hash_token(token: str) -> str:
    """Returns SHA-256 hash of a token string for safe database comparisons."""
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


class TokenService:
    @staticmethod
    def create_access_token(user_id: str, email: str, role: str) -> str:
        """Generates a secure access token containing sub, email, and role."""
        expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
        payload = {
            "sub": user_id,
            "email": email,
            "role": role,
            "type": "access",
            "exp": expire,
            "iat": datetime.utcnow(),
            "iss": "ai-data-analyst",
        }
        return jwt.encode(payload, settings.SECRET_KEY, algorithm=settings.JWT_ALGORITHM)

    @staticmethod
    def create_refresh_token(user_id: str, session_id: str) -> str:
        """Generates a secure refresh token bound to a session."""
        expire = datetime.utcnow() + timedelta(days=REFRESH_TOKEN_EXPIRE_DAYS)
        payload = {
            "sub": user_id,
            "session_id": session_id,
            "type": "refresh",
            "exp": expire,
            "iat": datetime.utcnow(),
            "iss": "ai-data-analyst",
            "jti": str(uuid.uuid4()),
        }
        return jwt.encode(payload, settings.SECRET_KEY, algorithm=settings.JWT_ALGORITHM)

    @staticmethod
    def decode_token(token: str) -> Dict[str, Any]:
        """Decodes and validates a JWT token signature."""
        try:
            return jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.JWT_ALGORITHM], issuer="ai-data-analyst")
        except JWTError:
            raise HTTPException(status_code=401, detail="Token signature invalid or expired")

    @classmethod
    async def rotate_refresh_token(cls, session: AsyncSession, refresh_token: str) -> Tuple[str, str, Dict[str, Any]]:
        """
        Validates refresh token, checks for reuse (replay attack detection),
        revokes old token, updates session with new rotated token hash,
        and returns (new_access_token, new_refresh_token, user_details).
        """
        payload = cls.decode_token(refresh_token)
        if payload.get("type") != "refresh":
            raise HTTPException(status_code=401, detail="Invalid token type")

        user_id = payload.get("sub")
        session_id = payload.get("session_id")
        if not user_id or not session_id:
            raise HTTPException(status_code=401, detail="Token parameters missing")

        # 1. Fetch the active user session
        stmt_session = select(UserSession).where(UserSession.id == session_id)
        user_session = (await session.execute(stmt_session)).scalar_one_or_none()

        if not user_session or user_session.status != "active":
            raise HTTPException(status_code=401, detail="Session is inactive or terminated")

        token_hash = hash_token(refresh_token)

        # 2. Check if this token was already revoked (indicates reuse/replay attack)
        stmt_revoked = select(RevokedRefreshToken).where(RevokedRefreshToken.token_hash == token_hash)
        revoked_record = (await session.execute(stmt_revoked)).scalar_one_or_none()

        if revoked_record:
            # REUSE DETECTED: Immediately revoke session and flag in audit logs
            user_session.status = "revoked"
            await session.commit()
            logger.critical(
                f"REUSE DETECTED for refresh token! Session {session_id} has been revoked to prevent hijack."
            )
            raise HTTPException(
                status_code=401, detail="Token has been used already. Session terminated for security reasons."
            )

        # 3. Verify that the presented token is indeed the current one registered for the session
        if user_session.refresh_token_hash != token_hash:
            # Token mismatch (indicates a compromised outdated token)
            user_session.status = "revoked"
            await session.commit()
            raise HTTPException(
                status_code=401, detail="Outdated refresh token presented. Session terminated for security reasons."
            )

        # 4. Fetch the user details to get role and email
        from app.models.user import User

        stmt_user = select(User).where(User.id == user_id)
        user_rec = (await session.execute(stmt_user)).scalar_one_or_none()
        if not user_rec or not user_rec.is_active:
            raise HTTPException(status_code=401, detail="User account is deactivated or not found")

        # 5. Revoke the old refresh token
        revocation = RevokedRefreshToken(
            token_hash=token_hash, user_id=user_id, session_id=session_id, reason="rotated"
        )
        session.add(revocation)

        # 6. Generate rotated pair
        new_access_token = cls.create_access_token(user_id, user_rec.email, user_rec.role)
        new_refresh_token = cls.create_refresh_token(user_id, session_id)

        # Update session with new hash and activity time
        user_session.refresh_token_hash = hash_token(new_refresh_token)
        user_session.last_activity = datetime.utcnow()
        await session.commit()

        user_details = {
            "id": user_rec.id,
            "email": user_rec.email,
            "role": user_rec.role,
            "full_name": user_rec.full_name,
        }

        return new_access_token, new_refresh_token, user_details
