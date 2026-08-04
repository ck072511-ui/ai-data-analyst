import uuid
from datetime import datetime
from sqlalchemy import Column, DateTime, ForeignKey, Integer, String, Text, JSON, Float, Boolean
from sqlalchemy.orm import relationship
from app.models.base import Base

class AICleaningRecommendation(Base):
    __tablename__ = "ai_cleaning_recommendations"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    dataset_id = Column(String(36), ForeignKey("user_datasets.id"), nullable=False)
    user_id = Column(String(36), ForeignKey("users.id"), nullable=False)
    
    # Store the generated analysis text/details
    analysis_results = Column(JSON, nullable=False)
    
    # Store the recommended checklist pipeline
    execution_plan = Column(JSON, nullable=False)
    
    status = Column(String(50), default="pending", nullable=False)  # "pending", "approved", "executed"
    approved_steps = Column(JSON, nullable=True)  # List of approved step indices/IDs
    
    confidence_score = Column(Float, default=0.0, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    executed_at = Column(DateTime, nullable=True)

    dataset = relationship("UserDataset")
    user = relationship("User")
