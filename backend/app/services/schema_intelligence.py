import logging
from typing import Any, Dict, List
from sqlalchemy import inspect
from app.core.connection_manager import ConnectionManager

logger = logging.getLogger(__name__)

class SchemaIntelligenceService:
    def __init__(self):
        self.conn_manager = ConnectionManager()

    async def discover_schema(self, connection_id: str, db_conn) -> Dict[str, Any]:
        """Fetch tables, columns, primary keys, foreign keys, and relations using SQLAlchemy inspect."""
        engine = self.conn_manager.get_engine(connection_id, db_conn)

        def run_inspect():
            inspector = inspect(engine)
            schema = {}
            for table_name in inspector.get_table_names():
                # Columns
                columns = []
                for col in inspector.get_columns(table_name):
                    columns.append({
                        "name": col["name"],
                        "type": str(col["type"]),
                        "nullable": col.get("nullable", True),
                        "comment": col.get("comment", "") or ""
                    })

                # Primary Keys
                pk_constraint = inspector.get_pk_constraint(table_name)
                primary_keys = pk_constraint.get("constrained_columns", [])

                # Foreign Keys
                foreign_keys = []
                for fk in inspector.get_foreign_keys(table_name):
                    foreign_keys.append({
                        "constrained_columns": fk["constrained_columns"],
                        "referred_table": fk["referred_table"],
                        "referred_columns": fk["referred_columns"]
                    })

                schema[table_name] = {
                    "columns": columns,
                    "primary_keys": primary_keys,
                    "foreign_keys": foreign_keys
                }
            return schema

        from fastapi.concurrency import run_in_threadpool
        try:
            return await run_in_threadpool(run_inspect)
        except Exception as e:
            logger.error(f"Failed to inspect schema for connection {connection_id}: {e}")
            raise e

    def build_schema_context(self, schema_data: Dict[str, Any]) -> str:
        """Compile structural metadata into context formatting strings for prompts."""
        context_parts = []
        for table_name, table_info in schema_data.items():
            context_parts.append(f"Table: {table_name}")
            
            # Columns
            for col in table_info["columns"]:
                pk_indicator = " (PK)" if col["name"] in table_info["primary_keys"] else ""
                comment_indicator = f" -- {col['comment']}" if col["comment"] else ""
                
                # Fetch synonyms from semantic layer
                try:
                    from app.services.semantic_layer_service import semantic_layer_service
                    syns = semantic_layer_service.resolve_synonyms(col["name"])
                    syns_indicator = f" (Synonyms: {', '.join(syns)})" if syns else ""
                except Exception:
                    syns_indicator = ""
                
                context_parts.append(f"  - {col['name']}: {col['type']}{pk_indicator}{comment_indicator}{syns_indicator}")
            
            # Foreign Keys / Relationships
            if table_info["foreign_keys"]:
                context_parts.append("  Relationships:")
                for fk in table_info["foreign_keys"]:
                    src_cols = ", ".join(fk["constrained_columns"])
                    ref_cols = ", ".join(fk["referred_columns"])
                    context_parts.append(f"    * {src_cols} references {fk['referred_table']}({ref_cols})")
            context_parts.append("")
        return "\n".join(context_parts)
