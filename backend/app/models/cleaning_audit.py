import uuid
from datetime import datetime

from sqlalchemy import JSON, Column, DateTime, ForeignKey, Integer, String

from app.models.base import Base


class CleaningAudit(Base):
    __tablename__ = "cleaning_audits"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    timestamp = Column(DateTime, default=datetime.utcnow)
    dataset_id = Column(String(36), ForeignKey("user_datasets.id", ondelete="CASCADE"), nullable=False)
    dataset_name = Column(String(255), nullable=False)
    user_id = Column(String(36), ForeignKey("users.id"), nullable=False)
    user_email = Column(String(255), nullable=False)
    operations_applied = Column(JSON)  # List of strings
    rows_changed = Column(Integer, default=0)
    columns_changed = Column(Integer, default=0)
    quality_score_before = Column(Integer, default=0)
    quality_score_after = Column(Integer, default=0)
    version_created = Column(Integer, nullable=False)
    status = Column(String(50), default="success")
