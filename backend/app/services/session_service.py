import logging
from datetime import datetime
from typing import List, Optional

from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.session import UserSession
from app.models.token import RevokedRefreshToken

logger = logging.getLogger(__name__)


class SessionService:
    @staticmethod
    async def create_session(
        session: AsyncSession, user_id: str, user_agent: Optional[str], client_ip: Optional[str]
    ) -> UserSession:
        """Creates and persists a new UserSession in the database."""
        user_session = UserSession(
            user_id=user_id,
            user_agent=user_agent or "Unknown Device",
            client_ip=client_ip or "Unknown IP",
            status="active",
            login_time=datetime.utcnow(),
            last_activity=datetime.utcnow(),
        )
        session.add(user_session)
        await session.commit()
        await session.refresh(user_session)
        return user_session

    @staticmethod
    async def update_session_token_hash(session: AsyncSession, session_id: str, token_hash: str) -> None:
        """Binds the current refresh token hash to the session."""
        stmt = select(UserSession).where(UserSession.id == session_id)
        user_session = (await session.execute(stmt)).scalar_one_or_none()
        if user_session:
            user_session.refresh_token_hash = token_hash
            user_session.last_activity = datetime.utcnow()
            await session.commit()

    @staticmethod
    async def update_activity(session: AsyncSession, session_id: str) -> None:
        """Updates the last activity timestamp for an active session."""
        stmt = select(UserSession).where(UserSession.id == session_id)
        user_session = (await session.execute(stmt)).scalar_one_or_none()
        if user_session and user_session.status == "active":
            user_session.last_activity = datetime.utcnow()
            await session.commit()

    @staticmethod
    async def list_active_sessions(session: AsyncSession, user_id: str) -> List[UserSession]:
        """Lists all active user sessions."""
        stmt = (
            select(UserSession)
            .where(UserSession.user_id == user_id, UserSession.status == "active")
            .order_by(UserSession.last_activity.desc())
        )
        result = await session.execute(stmt)
        return list(result.scalars().all())

    @classmethod
    async def revoke_session(cls, session: AsyncSession, session_id: str, user_id: str) -> None:
        """Terminates (revokes) a specific active session."""
        stmt = select(UserSession).where(UserSession.id == session_id, UserSession.user_id == user_id)
        user_session = (await session.execute(stmt)).scalar_one_or_none()
        if not user_session:
            raise HTTPException(status_code=404, detail="Session not found")

        user_session.status = "revoked"

        # Add its current refresh token to revoked if present
        if user_session.refresh_token_hash:
            revocation = RevokedRefreshToken(
                token_hash=user_session.refresh_token_hash, user_id=user_id, session_id=session_id, reason="logout"
            )
            session.add(revocation)

        await session.commit()
        logger.info(f"Session {session_id} has been revoked.")

    @classmethod
    async def revoke_all_sessions(
        cls, session: AsyncSession, user_id: str, exclude_session_id: Optional[str] = None
    ) -> None:
        """Terminates all active sessions for a user, optionally excluding a specific session."""
        stmt = select(UserSession).where(UserSession.user_id == user_id, UserSession.status == "active")
        if exclude_session_id:
            stmt = stmt.where(UserSession.id != exclude_session_id)

        result = await session.execute(stmt)
        active_sessions = result.scalars().all()

        for user_session in active_sessions:
            user_session.status = "revoked"
            if user_session.refresh_token_hash:
                revocation = RevokedRefreshToken(
                    token_hash=user_session.refresh_token_hash,
                    user_id=user_id,
                    session_id=user_session.id,
                    reason="logout",
                )
                session.add(revocation)

        await session.commit()
        logger.info(f"All sessions revoked for user {user_id} (excluding: {exclude_session_id}).")
