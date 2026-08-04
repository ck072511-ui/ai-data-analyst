import os
import sys
import pytest
from unittest.mock import AsyncMock, patch, MagicMock

# Adjust path to find backend
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

# Set environment variables for testing
os.environ["DATABASE_URL"] = "sqlite:///./test_analytics.db"
os.environ["SECRET_KEY"] = "test-secret-key-must-be-long-enough-32-chars-at-least"
os.environ["ENVIRONMENT"] = "development"

from app.core.database import Base
from app.services.nl2sql_service import NL2SQLService, SQLSafetyLayer
from app.services.prompt_builder import PromptBuilder
from app.services.schema_intelligence import SchemaIntelligenceService
from app.models.db_connection import DatabaseConnection
from app.models.nl2sql import NL2SQLConversation, NL2SQLQuery


@pytest.fixture
def anyio_backend():
    return "asyncio"


def test_sql_safety_layer():
    # Discovered schema mock
    mock_schema = {
        "users": {
            "columns": [{"name": "id", "type": "INTEGER"}, {"name": "name", "type": "TEXT"}],
            "primary_keys": ["id"],
            "foreign_keys": []
        }
    }

    # Unsafe query examples
    unsafe_queries = [
        "DROP TABLE users;",
        "DELETE FROM users WHERE id = 1;",
        "TRUNCATE TABLE users;",
        "ALTER TABLE users ADD COLUMN age INTEGER;",
        "UPDATE users SET name = 'admin' WHERE id = 1;",
        "INSERT INTO users (id, name) VALUES (1, 'User');",
        "CREATE TABLE test (id INTEGER);",
        "EXEC sp_help;",
        "SELECT * FROM pg_catalog.pg_tables;",
        "SELECT * FROM users CROSS JOIN products;",
        "SELECT * FROM users WHERE name = 'user' OR 1=1;",
        "SELECT * FROM users UNION ALL SELECT * FROM passwords;"
    ]

    for q in unsafe_queries:
        is_safe, msg = SQLSafetyLayer.inspect_safety(q, mock_schema)
        assert is_safe is False, f"Query should be blocked as unsafe: {q}. Message: {msg}"

    # Safe query examples
    safe_queries = [
        "SELECT * FROM users LIMIT 10;",
        "SELECT name FROM users WHERE id = 5;",
        "WITH active_users AS (SELECT * FROM users) SELECT * FROM active_users;"
    ]

    for q in safe_queries:
        is_safe, msg = SQLSafetyLayer.inspect_safety(q, mock_schema)
        assert is_safe is True, f"Query should be allowed as safe: {q}. Message: {msg}"


def test_prompt_builder():
    builder = PromptBuilder()
    
    schema_context = "Table: users\n  - id: INTEGER (PK)\n  - name: TEXT"
    question = "List all user names"
    history = [{"role": "user", "content": "Hello"}, {"role": "assistant", "content": "SQL: SELECT * FROM users;"}]
    
    prompt = builder.build_sql_generation_prompt(
        schema_context=schema_context,
        question=question,
        history=history,
        dialect="postgresql",
        business_rules=["Include only active users."]
    )

    assert "users" in prompt
    assert "dialect" in prompt.lower()
    assert "postgresql" in prompt
    assert "active users" in prompt
    assert "confidence_score" in prompt
    assert "List all user names" in prompt


@pytest.mark.anyio
async def test_schema_discovery(anyio_backend):
    # Mock engine inspect
    service = SchemaIntelligenceService()
    
    db_conn = DatabaseConnection(
        id="mock-conn-id",
        user_id="mock-user-id",
        name="test_db",
        db_type="sqlite",
        database="test.db"
    )

    mock_columns = [
        {"name": "id", "type": "INTEGER", "nullable": False},
        {"name": "title", "type": "TEXT", "nullable": True}
    ]
    mock_pk = {"constrained_columns": ["id"]}
    mock_fk = []

    mock_inspector = MagicMock()
    mock_inspector.get_table_names.return_value = ["tasks"]
    mock_inspector.get_columns.return_value = mock_columns
    mock_inspector.get_pk_constraint.return_value = mock_pk
    mock_inspector.get_foreign_keys.return_value = mock_fk

    with patch("app.services.schema_intelligence.inspect") as mock_inspect, \
         patch("app.core.connection_manager.ConnectionManager.get_engine") as mock_engine:
        mock_inspect.return_value = mock_inspector
        
        schema_data = await service.discover_schema("mock-conn-id", db_conn)
        
        assert "tasks" in schema_data
        assert schema_data["tasks"]["primary_keys"] == ["id"]
        assert len(schema_data["tasks"]["columns"]) == 2
        
        context = service.build_schema_context(schema_data)
        assert "Table: tasks" in context
        assert "id: INTEGER (PK)" in context
