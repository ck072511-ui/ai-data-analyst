import uuid
from datetime import datetime
from sqlalchemy import Column, DateTime, ForeignKey, Integer, String, Text, JSON, Float
from sqlalchemy.orm import relationship
from app.models.base import Base

class AgentExecution(Base):
    __tablename__ = "agent_executions"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(String(36), ForeignKey("users.id"), nullable=False)
    prompt = Column(Text, nullable=False)
    execution_plan = Column(JSON, nullable=False)  # Task list breakdown
    timeline = Column(JSON, nullable=False)        # Active states logs
    shared_memory = Column(JSON, nullable=False)   # Intermediate artifacts
    final_answer = Column(Text, nullable=True)
    confidence_score = Column(Float, default=0.0, nullable=False)
    duration_ms = Column(Integer, default=0, nullable=False)
    status = Column(String(50), default="running", nullable=False)  # "running", "completed", "failed", "critic_rejected"
    created_at = Column(DateTime, default=datetime.utcnow)

    user = relationship("User")
