import json
import logging
import re
from datetime import datetime
from typing import Any, Dict, List
from sqlalchemy import select

from app.core.database import AsyncSessionLocal
from app.models.prompt_registry import PromptTemplate, PromptVersion

logger = logging.getLogger(__name__)

class PromptService:
    @staticmethod
    def extract_variables(content: str) -> List[str]:
        """Identifies placeholders formatted as {variable_name}."""
        return list(set(re.findall(r"\{([a-zA-Z0-9_]+)\}", content)))

    async def list_prompts(self) -> List[Dict[str, Any]]:
        """Retrieves list of active prompt templates."""
        async with AsyncSessionLocal() as session:
            records = (await session.execute(select(PromptTemplate))).scalars().all()
            return [
                {
                    "id": r.id,
                    "name": r.name,
                    "category": r.category,
                    "content": r.content,
                    "version": r.version,
                    "variables": self.extract_variables(r.content),
                    "updated_at": r.updated_at.isoformat()
                }
                for r in records
            ]

    async def get_prompt(self, prompt_id: str) -> Dict[str, Any]:
        """Queries prompt details."""
        async with AsyncSessionLocal() as session:
            r = (await session.execute(
                select(PromptTemplate).where(PromptTemplate.id == prompt_id)
            )).scalar_one_or_none()

            if not r:
                return {"error": "Prompt not found"}

            return {
                "id": r.id,
                "name": r.name,
                "category": r.category,
                "content": r.content,
                "version": r.version,
                "variables": self.extract_variables(r.content),
                "updated_at": r.updated_at.isoformat()
            }

    async def create_prompt(self, name: str, category: str, content: str, author: str = "admin") -> Dict[str, Any]:
        """Creates a new prompt and logs version 1."""
        async with AsyncSessionLocal() as session:
            # Check duplicate name
            existing = (await session.execute(
                select(PromptTemplate).where(PromptTemplate.name == name)
            )).scalar_one_or_none()
            if existing:
                return {"error": f"Prompt with name '{name}' already exists."}

            p = PromptTemplate(name=name, category=category, content=content, version=1)
            session.add(p)
            await session.commit()
            await session.refresh(p)

            # Create version history
            v = PromptVersion(
                prompt_id=p.id,
                content=content,
                version=1,
                change_log="Initial Prompt Creation",
                author=author
            )
            session.add(v)
            await session.commit()
            
            logger.info(f"Created prompt '{name}' version 1.")
            return {"id": p.id, "name": p.name, "version": 1}

    async def update_prompt(self, prompt_id: str, content: str, change_log: str, author: str = "admin") -> Dict[str, Any]:
        """Updates prompt content, incrementing version numbers."""
        async with AsyncSessionLocal() as session:
            p = (await session.execute(
                select(PromptTemplate).where(PromptTemplate.id == prompt_id)
            )).scalar_one_or_none()

            if not p:
                return {"error": "Prompt template not found"}

            next_ver = p.version + 1
            p.content = content
            p.version = next_ver
            p.updated_at = datetime.utcnow()

            v = PromptVersion(
                prompt_id=p.id,
                content=content,
                version=next_ver,
                change_log=change_log,
                author=author
            )
            session.add(v)
            await session.commit()

            logger.info(f"Updated prompt '{p.name}' to version {next_ver}.")
            return {"id": p.id, "name": p.name, "version": next_ver}

    async def duplicate_prompt(self, prompt_id: str, new_name: str) -> Dict[str, Any]:
        """Duplicates a template to a new prompt name registry."""
        async with AsyncSessionLocal() as session:
            source = (await session.execute(
                select(PromptTemplate).where(PromptTemplate.id == prompt_id)
            )).scalar_one_or_none()

            if not source:
                return {"error": "Source prompt template not found."}

        return await self.create_prompt(
            name=new_name,
            category=source.category,
            content=source.content
        )

    @staticmethod
    def export_prompts(prompts: List[Dict[str, Any]]) -> str:
        """Serializes templates lists directly to JSON strings."""
        return json.dumps(prompts, indent=2)

    async def import_prompts(self, json_data: str) -> Dict[str, Any]:
        """Parses and registers imported JSON templates."""
        try:
            items = json.loads(json_data)
            cnt = 0
            for item in items:
                res = await self.create_prompt(
                    name=item.get("name"),
                    category=item.get("category", "custom"),
                    content=item.get("content", "")
                )
                if "error" not in res:
                    cnt += 1
            return {"success": True, "imported_count": cnt}
        except Exception as e:
            return {"error": f"Failed parsing JSON import payload: {e}"}
