import uuid
from datetime import datetime
from sqlalchemy import Column, String, Text, DateTime, ForeignKey, Boolean
from sqlalchemy.orm import relationship

from app.models.base import Base

class StreamConfig(Base):
    __tablename__ = "stream_configs"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    name = Column(String(100), nullable=False)
    description = Column(Text, nullable=True)
    source_type = Column(String(50), nullable=False)  # csv, json, rest, websocket, fs
    source_config = Column(Text, nullable=False)  # JSON-serialized configuration parameters
    window_type = Column(String(50), nullable=True)  # tumbling, sliding, session
    window_size_sec = Column(String(50), nullable=True)  # Window parameters (e.g. interval, slide, gap)
    aggregations = Column(Text, nullable=True)  # JSON-serialized list of fields & aggregate operations
    schema_definition = Column(Text, nullable=True)  # JSON-serialized schema mapping fields to data types
    active = Column(Boolean, default=False, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    user_id = Column(String(36), ForeignKey("users.id"), nullable=False)

    user = relationship("User")


class StreamAlert(Base):
    __tablename__ = "stream_alerts"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    stream_id = Column(String(36), ForeignKey("stream_configs.id", ondelete="CASCADE"), nullable=False)
    alert_type = Column(String(50), nullable=False)  # threshold, anomaly, failure, recovery
    message = Column(Text, nullable=False)
    severity = Column(String(20), default="warning")  # info, warning, critical
    timestamp = Column(DateTime, default=datetime.utcnow)
    resolved = Column(Boolean, default=False, nullable=False)
    user_id = Column(String(36), ForeignKey("users.id"), nullable=False)

    stream = relationship("StreamConfig")
    user = relationship("User")
