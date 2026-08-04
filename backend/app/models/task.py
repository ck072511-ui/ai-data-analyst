import uuid
from datetime import datetime

from sqlalchemy import Column, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import relationship

from app.models.base import Base


class Task(Base):
    __tablename__ = "tasks"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    task_type = Column(
        String(50), nullable=False
    )  # 'dataset_profiling', 'data_cleaning', 'dashboard_generation', 'ai_insights'
    status = Column(
        String(20), default="pending", nullable=False
    )  # 'pending', 'running', 'completed', 'failed', 'cancelled'
    progress = Column(Integer, default=0, nullable=False)
    started_at = Column(DateTime, default=datetime.utcnow, nullable=True)
    finished_at = Column(DateTime, nullable=True)
    error_message = Column(Text, nullable=True)
    user_id = Column(String(36), ForeignKey("users.id"), nullable=False)
    dataset_id = Column(String(36), ForeignKey("user_datasets.id"), nullable=True)
    payload = Column(Text, nullable=True)  # JSON-serialized task parameters for retry support

    # Relationships
    user = relationship("User")
    dataset = relationship("UserDataset")
