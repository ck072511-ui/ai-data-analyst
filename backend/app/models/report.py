import uuid
from datetime import datetime
from sqlalchemy import Column, DateTime, ForeignKey, String, Text, JSON
from sqlalchemy.orm import relationship
from app.models.base import Base

class GeneratedReport(Base):
    __tablename__ = "generated_reports"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(String(36), ForeignKey("users.id"), nullable=False)
    execution_id = Column(String(36), ForeignKey("agent_executions.id"), nullable=True)
    title = Column(String(255), nullable=False)
    report_type = Column(String(50), nullable=False)  # "executive", "technical", "audit", "data_quality", "ai_insights"
    file_format = Column(String(10), nullable=False)  # "pdf", "docx", "pptx"
    branding = Column(JSON, nullable=False)           # {company_name, footer, version, logo_path}
    status = Column(String(50), default="pending", nullable=False)  # "pending", "running", "completed", "failed"
    file_path = Column(Text, nullable=True)
    error_message = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    user = relationship("User")
    execution = relationship("AgentExecution")
