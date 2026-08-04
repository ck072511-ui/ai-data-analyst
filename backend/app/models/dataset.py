import uuid
from datetime import datetime

from sqlalchemy import JSON, Column, DateTime, ForeignKey, Integer, String

from app.models.base import Base


class UserDataset(Base):
    __tablename__ = "user_datasets"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(String(36), ForeignKey("users.id"), nullable=False)
    filename = Column(String(255), nullable=False)
    table_name = Column(String(100), nullable=False)
    file_path = Column(String(500), nullable=False)
    row_count = Column(Integer, default=0)
    col_count = Column(Integer, default=0)
    columns = Column(JSON)  # List of column names
    schema_info = Column(JSON)  # Dict mapping col_name -> stats/EDA properties
    profile_info = Column(JSON, nullable=True)
    status = Column(String(50), default="active", nullable=True)  # 'processing', 'active', 'failed'
    created_at = Column(DateTime, default=datetime.utcnow)
