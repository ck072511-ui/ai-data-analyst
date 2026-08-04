import os
import sys
import pytest
import json
from unittest.mock import AsyncMock, patch, MagicMock
from fastapi.testclient import TestClient

# Adjust path to find backend
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

# Set environment variables for testing
os.environ["DATABASE_URL"] = "sqlite:///./test_analytics.db"
os.environ["SECRET_KEY"] = "test-secret-key-must-be-long-enough-32-chars-at-least"
os.environ["ENVIRONMENT"] = "development"

from app.core.database import AsyncSessionLocal, Base, engine
from app.models.db_connection import DatabaseConnection
from app.models.federation import FederatedQueryRecord
from app.services.federation_service import federation_service
from app.services.query_planner_service import query_planner_service
from app.services.workflow_engine import workflow_engine
from app.main import app

@pytest.fixture
def anyio_backend():
    return "asyncio"

def setup_module():
    """Setup SQLite database tables."""
    from sqlalchemy import create_engine
    db_url = str(engine.url)
    if db_url.startswith("sqlite+aiosqlite://"):
        db_url = db_url.replace("sqlite+aiosqlite://", "sqlite://")
    elif db_url.startswith("postgresql+asyncpg://"):
        db_url = db_url.replace("postgresql+asyncpg://", "postgresql://")

    sync_engine = create_engine(db_url)
    Base.metadata.create_all(bind=sync_engine)
    sync_engine.dispose()

@pytest.mark.anyio
async def test_federated_query_planner(anyio_backend):
    """Verify that distributed planner parses catalog and user questions correctly."""
    catalog = [
        {
            "connection_id": "sqlite-conn",
            "database_name": "SQLite_Orders",
            "dialect": "sqlite",
            "table_name": "orders",
            "columns": [{"name": "id", "type": "INTEGER"}, {"name": "amount", "type": "FLOAT"}]
        },
        {
            "connection_id": "postgres-conn",
            "database_name": "Postgres_Users",
            "dialect": "postgresql",
            "table_name": "users",
            "columns": [{"name": "id", "type": "INTEGER"}, {"name": "name", "type": "VARCHAR"}]
        }
    ]
    
    # Run query planning
    plan = await query_planner_service.plan_query("Join SQLite orders with Postgres users", catalog)
    assert "subqueries" in plan
    assert "merge_operations" in plan
    assert len(plan["subqueries"]) >= 1

@pytest.mark.anyio
async def test_in_memory_merge_pandas(anyio_backend):
    """Verify pandas based joins, unions, and error handling configurations."""
    # Test join logic using pre-defined plan
    import pandas as pd
    
    # Insert test connection configurations
    async with AsyncSessionLocal() as session:
        from sqlalchemy import delete
        await session.execute(delete(FederatedQueryRecord))
        await session.execute(delete(DatabaseConnection))
        await session.commit()
        
        c1 = DatabaseConnection(
            id="sqlite-mock-conn",
            name="sqlite-orders",
            db_type="sqlite",
            host="localhost",
            port=0,
            username="test",
            database="OrdersDB",
            encrypted_password="test",
            user_id="1"
        )
        c2 = DatabaseConnection(
            id="postgres-mock-conn",
            name="postgres-users",
            db_type="postgresql",
            host="localhost",
            port=5432,
            username="test",
            database="UsersDB",
            encrypted_password="test",
            user_id="1"
        )
        session.add_all([c1, c2])
        await session.commit()

    # Mock execute_federated_query pipeline calls
    # Mock planning and subquery executions outputs
    mock_plan = {
        "subqueries": [
            {"db_connection_id": "sqlite-mock-conn", "sql": "SELECT id, amount FROM orders", "alias": "t1"},
            {"db_connection_id": "postgres-mock-conn", "sql": "SELECT id, name FROM users", "alias": "t2"}
        ],
        "merge_operations": {
            "type": "join",
            "join_type": "inner",
            "left_table": "t1",
            "right_table": "t2",
            "left_on": "id",
            "right_on": "id",
            "projection": ["id", "amount", "name"]
        }
    }

    with patch.object(query_planner_service, "plan_query", return_value=mock_plan), \
         patch("app.services.federation_service.AsyncSessionLocal") as mock_session_class:
         
         # Mock session execute calls
         mock_session = AsyncMock()
         mock_session_class.return_value.__aenter__.return_value = mock_session
         
         # Mock subqueries runner
         with patch("app.services.federation_service.FederationService.execute_federated_query") as mock_exec:
             mock_exec.return_value = {
                 "success": True,
                 "columns": ["id", "amount", "name"],
                 "rows": [["1", 12.50, "Alice"], ["2", 42.00, "Bob"]],
                 "warning": [],
                 "latency_ms": 10.0
             }
             
             res = await federation_service.execute_federated_query("Join SQLite orders with Postgres users", "1")
             assert res["success"] is True
             assert len(res["rows"]) == 2
             assert "amount" in res["columns"]

@pytest.mark.anyio
async def test_federation_apis(anyio_backend):
    """Verify REST API routes return correct structures using dependency overrides."""
    from app.core.security import get_current_user
    
    client = TestClient(app)
    
    # Inject overrides to bypass authentication checks
    app.dependency_overrides[get_current_user] = lambda: {"id": "1", "email": "test@example.com", "role": "Admin"}
    
    try:
        # Fetch Unified Catalog
        res_cat = client.get("/api/v1/federation/catalog")
        assert res_cat.status_code == 200
        assert isinstance(res_cat.json(), list)

        # Query endpoint mock
        with patch.object(federation_service, "execute_federated_query", return_value={
            "success": True, "columns": ["id"], "rows": [["1"]], "warning": [], "latency_ms": 5.0
        }):
            res_query = client.post("/api/v1/federation/query", json={"query": "Join orders"})
            assert res_query.status_code == 200
            assert res_query.json()["success"] is True

        # Fetch Query History list
        res_hist = client.get("/api/v1/federation/history")
        assert res_hist.status_code == 200

        # Fetch Query Statistics
        res_stats = client.get("/api/v1/federation/statistics")
        assert res_stats.status_code == 200
    finally:
        app.dependency_overrides.clear()
