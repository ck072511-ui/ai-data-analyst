from sqlalchemy import inspect

from app.core.database import engine


class SchemaRetriever:
    """Fetch and cache a compact representation of the analytics schema."""

    def __init__(self):
        self.schema_cache = None

    async def get_relevant_schema(self, _question: str) -> str:
        if self.schema_cache is not None:
            return self.schema_cache

        def read_schema(connection) -> str:
            inspector = inspect(connection)
            parts = []
            for table_name in inspector.get_table_names():
                parts.append(f"Table: {table_name}")
                for column in inspector.get_columns(table_name):
                    nullable = "" if column.get("nullable", True) else " NOT NULL"
                    parts.append(f"  - {column['name']}: {column['type']}{nullable}")
            return "\n".join(parts)

        async with engine.connect() as connection:
            self.schema_cache = await connection.run_sync(read_schema)
        return self.schema_cache
