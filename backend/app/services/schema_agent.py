import logging
from typing import Any, Dict
from sqlalchemy import select
from app.core.database import AsyncSessionLocal
from app.models.dataset import UserDataset
from app.services.schema_intelligence import SchemaIntelligenceService

logger = logging.getLogger(__name__)

class SchemaAgent:
    def __init__(self):
        self.schema_service = SchemaIntelligenceService()

    async def execute_task(self, dataset_id: str, shared_memory: Dict[str, Any]) -> Dict[str, Any]:
        """Inspects table layouts, relations, and constructs schema context descriptions."""
        logger.info(f"Schema Agent inspecting schema parameters for dataset {dataset_id}")

        async with AsyncSessionLocal() as session:
            dataset = (await session.execute(
                select(UserDataset).where(UserDataset.id == dataset_id)
            )).scalar_one_or_none()

        if not dataset:
            return {"error": "Dataset registry not found", "schema_context": ""}

        schema_info = dataset.schema_info or {}
        columns_desc = []
        for col, meta in schema_info.items():
            dtype = meta.get("dtype", "unknown")
            columns_desc.append(f"  - {col} ({dtype})")

        schema_context = (
            f"Table Name: {dataset.table_name}\n"
            f"Description: Relational dataset parsed from uploaded file '{dataset.filename}'\n"
            f"Columns list:\n" + "\n".join(columns_desc)
        )

        return {
            "table_name": dataset.table_name,
            "filename": dataset.filename,
            "row_count": dataset.row_count,
            "column_count": dataset.col_count,
            "schema_context": schema_context
        }
