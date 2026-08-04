import logging
import re
from typing import Any, Dict
from sqlalchemy import text
from app.core.database import get_sync_engine
from app.services.model_manager import model_manager

logger = logging.getLogger(__name__)

class SQLAgent:
    def __init__(self):
        self.forbidden_keywords = ["delete", "update", "drop", "alter", "truncate", "insert"]

    async def execute_task(self, dataset_id: str, question: str, shared_memory: Dict[str, Any]) -> Dict[str, Any]:
        """Translates intent to SQL, inspects syntax, runs query, and calculates metrics."""
        logger.info(f"SQL Agent formulating query parameters for query: {question}")
        
        schema_context = shared_memory.get("SchemaAgent", {}).get("schema_context", "")
        table_name = shared_memory.get("SchemaAgent", {}).get("table_name", "dataset_table")

        # 1. Compile generation prompt
        prompt = (
            "You are a Senior SQL Developer and Database Architect.\n"
            "Generate a SELECT SQL query that answers the user's question about the table schema provided.\n\n"
            "=== SCHEMA CONTEXT ===\n"
            f"{schema_context}\n\n"
            "=== QUESTION ===\n"
            f"{question}\n\n"
            "Output ONLY the raw SQL query. Do not wrap in markdown or backticks."
        )

        try:
            sql = await model_manager.generate(prompt=prompt)
            sql = sql.strip().replace("```sql", "").replace("```", "").strip()
            
            # Basic validation
            is_safe = True
            for kw in self.forbidden_keywords:
                if re.search(r"\b" + kw + r"\b", sql.lower()):
                    is_safe = False
                    break
            
            if not is_safe:
                return {
                    "sql": sql,
                    "error": "Forbidden SQL command detected. SQL execution aborted for security.",
                    "confidence": 0.0
                }

            # Execute query on SQLite engine
            engine = get_sync_engine()
            results = []
            columns = []
            with engine.connect() as conn:
                res = conn.execute(text(sql))
                columns = list(res.keys())
                for row in res.fetchall():
                    results.append(list(row))

            logger.info("SQL Agent successfully generated and ran query.")
            return {
                "sql": sql,
                "columns": columns,
                "rows": results[:100],  # cap row returns for context window safety
                "row_count": len(results),
                "confidence": 0.90
            }

        except Exception as e:
            logger.warning(f"SQL Agent failed query generation or execution: {e}")
            return {
                "sql": "",
                "error": str(e),
                "confidence": 0.0
            }
