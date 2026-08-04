import uuid
from datetime import datetime
from sqlalchemy import Column, DateTime, ForeignKey, Integer, String, Text, JSON, Float, Boolean
from sqlalchemy.orm import relationship
from app.models.base import Base

class NL2SQLConversation(Base):
    __tablename__ = "nl2sql_conversations"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(String(36), ForeignKey("users.id"), nullable=False)
    db_connection_id = Column(String(36), ForeignKey("database_connections.id"), nullable=False)
    title = Column(String(255), default="New SQL Conversation")
    is_pinned = Column(Boolean, default=False, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    user = relationship("User")
    db_connection = relationship("DatabaseConnection")
    queries = relationship("NL2SQLQuery", back_populates="conversation", cascade="all, delete-orphan")


class NL2SQLQuery(Base):
    __tablename__ = "nl2sql_queries"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    conversation_id = Column(String(36), ForeignKey("nl2sql_conversations.id"), nullable=False)
    user_id = Column(String(36), ForeignKey("users.id"), nullable=False)
    question = Column(Text, nullable=False)
    generated_sql = Column(Text)
    optimized_sql = Column(Text)
    explanation = Column(Text)
    confidence_score = Column(Float)
    execution_time_ms = Column(Integer)
    row_count = Column(Integer, default=0)
    success = Column(Boolean, default=True)
    error_message = Column(Text)
    is_optimized = Column(Boolean, default=False)
    explain_plan = Column(Text)
    created_at = Column(DateTime, default=datetime.utcnow)

    conversation = relationship("NL2SQLConversation", back_populates="queries")
    user = relationship("User")
