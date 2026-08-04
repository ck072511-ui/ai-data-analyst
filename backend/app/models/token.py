import uuid
from datetime import datetime

from sqlalchemy import Column, DateTime, ForeignKey, String

from app.models.base import Base


class RevokedRefreshToken(Base):
    """
    Tracks rotated or explicitly revoked refresh tokens to detect and prevent reuse.
    """

    __tablename__ = "revoked_refresh_tokens"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    token_hash = Column(String(255), unique=True, nullable=False, index=True)
    user_id = Column(String(36), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    session_id = Column(String(36), ForeignKey("user_sessions.id", ondelete="CASCADE"), nullable=False)
    revoked_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    reason = Column(String(100), default="rotated", nullable=False)  # "rotated", "logout", "reuse_detected"
