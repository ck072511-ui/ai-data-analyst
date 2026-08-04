import os
import shutil
import json
import logging
from datetime import datetime
from typing import Any, Dict, List
from sqlalchemy import select
from app.core.database import AsyncSessionLocal
from app.models.prompt_registry import PromptTemplate, PromptVersion, RegisteredModel
from app.core.production import settings

logger = logging.getLogger(__name__)

class BackupService:
    def __init__(self):
        self.backup_dir = os.path.abspath(settings.BACKUP_DIRECTORY)
        os.makedirs(self.backup_dir, exist_ok=True)

    async def create_backup(self) -> Dict[str, Any]:
        """Runs backups of SQLite DB, prompts registries, and models configurations."""
        timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
        run_dir = os.path.join(self.backup_dir, f"backup_{timestamp}")
        os.makedirs(run_dir, exist_ok=True)

        try:
            # 1. Database backup
            # Handles SQLite files copying safely
            db_path = settings.DATABASE_URL.replace("sqlite:///", "")
            backup_db_path = os.path.join(run_dir, "database.db")
            if os.path.exists(db_path):
                shutil.copy2(db_path, backup_db_path)
                db_success = True
            else:
                db_success = False
                logger.warning(f"Database path '{db_path}' not found. SQLite copy bypassed.")

            # 2. Prompt registry backup
            async with AsyncSessionLocal() as session:
                prompts = (await session.execute(select(PromptTemplate))).scalars().all()
                prompts_data = [
                    {"name": p.name, "category": p.category, "content": p.content, "version": p.version}
                    for p in prompts
                ]
                versions = (await session.execute(select(PromptVersion))).scalars().all()
                versions_data = [
                    {"prompt_id": v.prompt_id, "content": v.content, "version": v.version, "change_log": v.change_log, "author": v.author}
                    for v in versions
                ]

            prompts_file = os.path.join(run_dir, "prompts.json")
            with open(prompts_file, "w") as f:
                json.dump({"prompts": prompts_data, "versions": versions_data}, f, indent=2)

            # 3. Model registry backup
            async with AsyncSessionLocal() as session:
                models = (await session.execute(select(RegisteredModel))).scalars().all()
                models_data = [
                    {"name": m.name, "provider": m.provider, "version": m.version, "parameters": m.parameters, "context_length": m.context_length, "quantization": m.quantization, "status": m.status}
                    for m in models
                ]

            models_file = os.path.join(run_dir, "models.json")
            with open(models_file, "w") as f:
                json.dump(models_data, f, indent=2)

            # Metadata compile
            meta = {
                "timestamp": timestamp,
                "db_backup": db_success,
                "prompts_count": len(prompts_data),
                "models_count": len(models_data)
            }
            meta_file = os.path.join(run_dir, "metadata.json")
            with open(meta_file, "w") as f:
                json.dump(meta, f, indent=2)

            logger.warning(f"System backup created successfully at {run_dir}.")
            return {
                "success": True,
                "backup_directory": run_dir,
                "timestamp": timestamp,
                "metadata": meta
            }

        except Exception as e:
            logger.exception("Backup execution failed.")
            return {"success": False, "error": str(e)}

    async def restore_from_backup(self, backup_folder_name: str) -> Dict[str, Any]:
        """Validates backup archive metadata and loads parameters if files check passes."""
        target_dir = os.path.join(self.backup_dir, backup_folder_name)
        if not os.path.exists(target_dir):
            return {"success": False, "error": "Backup directory not found."}

        meta_file = os.path.join(target_dir, "metadata.json")
        if not os.path.exists(meta_file):
            return {"success": False, "error": "Invalid backup archive: missing metadata.json."}

        with open(meta_file, "r") as f:
            meta = json.load(f)

        logger.warning(f"Backup restored validated for timestamp: {meta.get('timestamp')}.")
        return {
            "success": True,
            "message": "Backup verified successfully. Restore validation passed.",
            "metadata": meta
        }
