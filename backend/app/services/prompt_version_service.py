import logging
from datetime import datetime
from typing import Any, Dict, List
from sqlalchemy import select, desc
from app.core.database import AsyncSessionLocal
from app.models.prompt_registry import PromptTemplate, PromptVersion
from app.services.monitoring_service import monitoring_service

logger = logging.getLogger(__name__)

class PromptVersionService:
    async def list_versions(self, prompt_id: str) -> List[Dict[str, Any]]:
        """Retrieves historical versions list for a template."""
        async with AsyncSessionLocal() as session:
            records = (await session.execute(
                select(PromptVersion)
                .where(PromptVersion.prompt_id == prompt_id)
                .order_by(desc(PromptVersion.version))
            )).scalars().all()

            return [
                {
                    "id": v.id,
                    "version": v.version,
                    "content": v.content,
                    "change_log": v.change_log,
                    "author": v.author,
                    "created_at": v.created_at.isoformat()
                }
                for v in records
            ]

    async def compare_versions(self, prompt_id: str, ver_a: int, ver_b: int) -> Dict[str, Any]:
        """Loads two versions to facilitate diff rendering."""
        async with AsyncSessionLocal() as session:
            recs = (await session.execute(
                select(PromptVersion)
                .where(PromptVersion.prompt_id == prompt_id, PromptVersion.version.in_([ver_a, ver_b]))
            )).scalars().all()

            mapped = {r.version: r.content for r in recs}
            return {
                "ver_a": ver_a,
                "content_a": mapped.get(ver_a, ""),
                "ver_b": ver_b,
                "content_b": mapped.get(ver_b, "")
            }

    async def rollback_to_version(self, prompt_id: str, target_ver: int, author: str = "admin") -> Dict[str, Any]:
        """Rollbacks the active prompt template content back to a historical version."""
        async with AsyncSessionLocal() as session:
            # Check target version content
            v_rec = (await session.execute(
                select(PromptVersion)
                .where(PromptVersion.prompt_id == prompt_id, PromptVersion.version == target_ver)
            )).scalar_one_or_none()

            if not v_rec:
                return {"error": f"Target version {target_ver} not found in history logs."}

            p = (await session.execute(
                select(PromptTemplate).where(PromptTemplate.id == prompt_id)
            )).scalar_one_or_none()

            if not p:
                return {"error": "Prompt template not found"}

            next_ver = p.version + 1
            p.content = v_rec.content
            p.version = next_ver
            p.updated_at = datetime.utcnow()

            # Insert new rollback version record
            new_v = PromptVersion(
                prompt_id=p.id,
                content=v_rec.content,
                version=next_ver,
                change_log=f"Rollback to version {target_ver}",
                author=author
            )
            session.add(new_v)
            await session.commit()

            # Record Prometheus rollback metric
            monitoring_service.record_prompt_rollback()

            logger.warning(f"Prompt '{p.name}' rolled back to version {target_ver}. Current version: {next_ver}.")
            return {
                "id": p.id,
                "name": p.name,
                "version": next_ver,
                "rolled_back_to": target_ver
            }
