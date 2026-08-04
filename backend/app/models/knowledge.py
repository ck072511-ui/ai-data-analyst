import uuid
from datetime import datetime
from sqlalchemy import Column, String, Text, DateTime, ForeignKey, Float
from sqlalchemy.orm import relationship

from app.models.base import Base

class KnowledgeEntity(Base):
    __tablename__ = "knowledge_entities"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    name = Column(String(100), nullable=False)
    entity_type = Column(String(50), nullable=False)  # Dataset, Table, Column, KPI, Metric, Business Term, Document, etc.
    properties = Column(Text, nullable=True)  # JSON-serialized fields (description, synonyms, datatype, aliases)
    source_id = Column(String(100), nullable=True)  # Path, table name or version reference identifier
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    user_id = Column(String(36), ForeignKey("users.id"), nullable=False)

    # Relationships
    user = relationship("User")


class KnowledgeRelationship(Base):
    __tablename__ = "knowledge_relationships"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    source_id = Column(String(36), ForeignKey("knowledge_entities.id", ondelete="CASCADE"), nullable=False)
    target_id = Column(String(36), ForeignKey("knowledge_entities.id", ondelete="CASCADE"), nullable=False)
    relationship_type = Column(String(50), nullable=False)  # foreign_key, lineage, references, kpi_dependency, glossary_mapping, alias, etc.
    confidence = Column(Float, default=1.0)
    properties = Column(Text, nullable=True)  # JSON-serialized metadata
    created_at = Column(DateTime, default=datetime.utcnow)
    user_id = Column(String(36), ForeignKey("users.id"), nullable=False)

    # Relationships
    source = relationship("KnowledgeEntity", foreign_keys=[source_id])
    target = relationship("KnowledgeEntity", foreign_keys=[target_id])
    user = relationship("User")
