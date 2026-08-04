import uuid
from datetime import datetime
from sqlalchemy import Column, String, Text, DateTime, ForeignKey, Float
from sqlalchemy.orm import relationship

from app.models.base import Base

class FederatedQueryRecord(Base):
    __tablename__ = "federated_queries"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    question = Column(Text, nullable=False)
    execution_plan = Column(Text, nullable=False)  # JSON-serialized execution plan
    status = Column(String(50), nullable=False)  # success, partial_failure, failed
    error_message = Column(Text, nullable=True)
    latency_ms = Column(Float, default=0.0)
    created_at = Column(DateTime, default=datetime.utcnow)
    user_id = Column(String(36), ForeignKey("users.id"), nullable=False)

    # Relationships
    user = relationship("User")
