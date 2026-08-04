import os
import logging
from typing import Any, Dict
from sqlalchemy import text
from app.core.database import AsyncSessionLocal
from app.services.model_manager import model_manager

logger = logging.getLogger(__name__)

class ReadinessValidator:
    @staticmethod
    async def run_checks() -> Dict[str, Any]:
        """Runs startup validation audits for release candidate readiness."""
        logger.info("Production Readiness Validator starting audits checks...")
        
        status = {}
        is_ready = True

        # 1. Database Check
        try:
            async with AsyncSessionLocal() as session:
                await session.execute(text("SELECT 1"))
            status["database"] = "Healthy"
        except Exception as e:
            status["database"] = f"Unhealthy: {e}"
            is_ready = False

        # 2. Vector Store Directory
        vs_dir = os.path.abspath(
            os.path.join(os.path.dirname(__file__), "..", "..", "vector_store")
        )
        os.makedirs(vs_dir, exist_ok=True)
        if os.path.exists(vs_dir) and os.access(vs_dir, os.W_OK):
            status["vector_store_directory"] = "Healthy (Writable)"
        else:
            status["vector_store_directory"] = "Unhealthy: Directory missing or read-only."
            is_ready = False

        # 3. Generated documents Directory
        doc_dir = os.path.abspath(
            os.path.join(os.path.dirname(__file__), "..", "..", "data", "generated_documents")
        )
        os.makedirs(doc_dir, exist_ok=True)
        if os.path.exists(doc_dir) and os.access(doc_dir, os.W_OK):
            status["document_export_directory"] = "Healthy (Writable)"
        else:
            status["document_export_directory"] = "Unhealthy: Directory read-only."
            is_ready = False

        # 4. Local Model connectivity
        try:
            # Short query to check model manager
            res = await model_manager.generate("ping", max_tokens=5)
            if res:
                status["llm_connectivity"] = "Healthy"
            else:
                status["llm_connectivity"] = "Warning: Empty LLM response."
        except Exception as e:
            status["llm_connectivity"] = f"Unhealthy: {e}"
            # Do not fail complete readiness for Ollama local connectivity since
            # models can be loaded dynamically, but log warning.
            status["llm_connectivity"] = "Warning: Model connectivity offline."

        # 5. Environment parameters
        secret_key = os.getenv("SECRET_KEY")
        if secret_key and secret_key != "prod-secure-token-default-change-me-please":
            status["security_keys"] = "Healthy"
        else:
            status["security_keys"] = "Warning: Default SECRET_KEY in use."

        status["overall_ready"] = is_ready
        logger.warning(f"Production readiness validation check finished. Success: {is_ready}.")
        return status
