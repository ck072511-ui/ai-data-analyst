import uuid
from datetime import datetime

from sqlalchemy import JSON, Column, DateTime, ForeignKey, Integer, String

from app.models.base import Base


class DatasetVersion(Base):
    __tablename__ = "dataset_versions"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    dataset_id = Column(String(36), ForeignKey("user_datasets.id", ondelete="CASCADE"), nullable=False)
    version_number = Column(Integer, nullable=False)
    timestamp = Column(DateTime, default=datetime.utcnow)
    user_id = Column(String(36), ForeignKey("users.id"), nullable=False)
    file_path = Column(String(500), nullable=False)
    table_name = Column(String(100), nullable=False)
    row_count = Column(Integer, default=0)
    col_count = Column(Integer, default=0)
    columns = Column(JSON)
    schema_info = Column(JSON)
    profile_info = Column(JSON, nullable=True)
    operations_applied = Column(JSON)  # List of string descriptions of ops applied
    parent_version = Column(Integer, nullable=True)
