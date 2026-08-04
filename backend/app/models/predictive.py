import uuid
from datetime import datetime
from sqlalchemy import Column, DateTime, String, JSON
from app.models.base import Base

class PredictiveHistory(Base):
    __tablename__ = "predictive_histories"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    dataset_id = Column(String(36), nullable=False)
    target_variable = Column(String(255), nullable=False)
    task_type = Column(String(100), nullable=False)  # "classification", "regression", "forecasting", "clustering"
    best_model_name = Column(String(255), nullable=False)
    metrics = Column(JSON, nullable=False)  # {"accuracy": 0.92, "f1": 0.91} or R2, MSE, Silhouette
    parameters = Column(JSON, nullable=False)  # {"features": ["age", "tenure"], "hyperparameters": {...}}
    created_at = Column(DateTime, default=datetime.utcnow)
