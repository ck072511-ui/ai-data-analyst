import uuid
from datetime import datetime
from sqlalchemy import Column, DateTime, ForeignKey, Integer, String, Text, JSON, Float
from sqlalchemy.orm import relationship
from app.models.base import Base

class PromptTemplate(Base):
    __tablename__ = "prompt_templates"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    name = Column(String(255), unique=True, nullable=False)
    category = Column(String(100), nullable=False)  # "sql", "rag", "multi_agent", "insights", "custom"
    content = Column(Text, nullable=False)
    version = Column(Integer, default=1, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class PromptVersion(Base):
    __tablename__ = "prompt_versions"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    prompt_id = Column(String(36), ForeignKey("prompt_templates.id"), nullable=False)
    content = Column(Text, nullable=False)
    version = Column(Integer, nullable=False)
    change_log = Column(String(255), nullable=True)
    author = Column(String(100), default="system", nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)

    prompt = relationship("PromptTemplate")


class RegisteredModel(Base):
    __tablename__ = "registered_models"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    name = Column(String(255), unique=True, nullable=False)
    provider = Column(String(100), default="Ollama", nullable=False)
    version = Column(String(50), default="latest", nullable=False)
    parameters = Column(JSON, nullable=False)  # {"temperature": 0.2, "top_p": 0.9}
    context_length = Column(Integer, default=4096, nullable=False)
    quantization = Column(String(50), default="Q4_K_M", nullable=False)
    status = Column(String(50), default="inactive", nullable=False)  # "active", "inactive"
    created_at = Column(DateTime, default=datetime.utcnow)


class EvaluationRecord(Base):
    __tablename__ = "evaluation_records"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    prompt_id = Column(String(36), ForeignKey("prompt_templates.id"), nullable=True)
    model_name = Column(String(255), nullable=False)
    answer_relevance = Column(Float, default=0.0, nullable=False)
    sql_correctness = Column(Float, default=0.0, nullable=False)
    citation_coverage = Column(Float, default=0.0, nullable=False)
    overall_score = Column(Float, default=0.0, nullable=False)  # 0-100 score
    execution_latency_ms = Column(Integer, default=0, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)

    prompt = relationship("PromptTemplate")
