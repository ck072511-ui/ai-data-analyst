import uuid
from datetime import datetime

from sqlalchemy import Column, DateTime, String

from app.models.base import Base


class SystemAuditLog(Base):
    __tablename__ = "system_audit_logs"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(String(36), nullable=True)
    user_email = Column(String(255), nullable=True)
    user_role = Column(String(50), nullable=True)
    endpoint = Column(String(255), nullable=False)
    action = Column(String(100), nullable=False)
    timestamp = Column(DateTime, default=datetime.utcnow)
    status = Column(String(50), nullable=False)  # "success" or "forbidden" or "unauthorized" or "failed"
