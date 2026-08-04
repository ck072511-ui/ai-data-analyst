import logging
from typing import Any, Dict, List
from sqlalchemy import select
from app.core.database import AsyncSessionLocal
from app.models.prompt_registry import RegisteredModel
from app.services.monitoring_service import monitoring_service

logger = logging.getLogger(__name__)

class ModelRegistryService:
    async def list_models(self) -> List[Dict[str, Any]]:
        """List registered local models."""
        async with AsyncSessionLocal() as session:
            records = (await session.execute(select(RegisteredModel))).scalars().all()
            
            # Seed default models if registry is empty
            if not records:
                default_models = [
                    RegisteredModel(name="llama3:8b", provider="Ollama", version="latest", parameters={"temperature": 0.2}, context_length=8192, quantization="Q4_K_M", status="active"),
                    RegisteredModel(name="qwen2:7b", provider="Ollama", version="latest", parameters={"temperature": 0.1}, context_length=32768, quantization="Q4_K_M", status="inactive"),
                    RegisteredModel(name="mistral:7b", provider="Ollama", version="latest", parameters={"temperature": 0.2}, context_length=8192, quantization="Q4_0", status="inactive"),
                    RegisteredModel(name="phi3:mini", provider="Ollama", version="latest", parameters={"temperature": 0.0}, context_length=4096, quantization="Q4_K_M", status="inactive")
                ]
                for m in default_models:
                    session.add(m)
                await session.commit()
                records = (await session.execute(select(RegisteredModel))).scalars().all()

            return [
                {
                    "id": r.id,
                    "name": r.name,
                    "provider": r.provider,
                    "version": r.version,
                    "parameters": r.parameters,
                    "context_length": r.context_length,
                    "quantization": r.quantization,
                    "status": r.status,
                    "created_at": r.created_at.isoformat()
                }
                for r in records
            ]

    async def activate_model(self, model_id: str) -> Dict[str, Any]:
        """Toggles the active default model status."""
        async with AsyncSessionLocal() as session:
            # Set all models inactive
            models = (await session.execute(select(RegisteredModel))).scalars().all()
            target = None
            for m in models:
                if m.id == model_id:
                    m.status = "active"
                    target = m
                else:
                    m.status = "inactive"

            if not target:
                return {"error": "Model registry ID not found."}

            await session.commit()

            # Record Prometheus model change event
            monitoring_service.record_active_model_change()

            logger.warning(f"Default active system model changed to: {target.name}")
            return {
                "id": target.id,
                "name": target.name,
                "status": "active"
            }
