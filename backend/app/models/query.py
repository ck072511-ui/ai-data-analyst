import uuid
from datetime import datetime

from sqlalchemy import JSON, Column, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import relationship

from app.models.base import Base


class QueryHistory(Base):
    __tablename__ = "query_history"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(String(36), ForeignKey("users.id"))
    natural_language = Column(Text, nullable=False)
    generated_sql = Column(Text)
    result_data = Column(JSON)
    chart_type = Column(String(50))
    execution_time = Column(Integer)
    row_count = Column(Integer, default=0)
    success = Column(Integer, default=1)
    error_message = Column(Text)
    session_id = Column(String(36), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    user = relationship("User", back_populates="queries")
