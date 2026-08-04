import uuid
from datetime import datetime

from sqlalchemy import Column, DateTime, ForeignKey, String
from sqlalchemy.orm import relationship

from app.models.base import Base


class UserSession(Base):
    __tablename__ = "user_sessions"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(String(36), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    login_time = Column(DateTime, default=datetime.utcnow, nullable=False)
    last_activity = Column(DateTime, default=datetime.utcnow, nullable=False)
    user_agent = Column(String(255), nullable=True)
    client_ip = Column(String(50), nullable=True)
    status = Column(String(50), default="active", nullable=False)  # "active", "logged_out", "revoked", "expired"
    refresh_token_hash = Column(String(255), nullable=True)  # to support token rotation verification

    user = relationship("User", backref="sessions")
