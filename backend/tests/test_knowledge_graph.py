import os
import sys
import pytest
import json
from unittest.mock import AsyncMock, patch, MagicMock

# Adjust path to find backend
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

# Set environment variables for testing
os.environ["DATABASE_URL"] = "sqlite:///./test_analytics.db"
os.environ["SECRET_KEY"] = "test-secret-key-must-be-long-enough-32-chars-at-least"
os.environ["ENVIRONMENT"] = "development"

from app.core.database import AsyncSessionLocal, Base, engine
from app.models.knowledge import KnowledgeEntity, KnowledgeRelationship
from app.services.knowledge_graph_service import knowledge_graph_service
from app.services.semantic_layer_service import semantic_layer_service
from app.main import app

@pytest.fixture
def anyio_backend():
    return "asyncio"

def setup_module():
    """Setup testing SQLite database tables."""
    from sqlalchemy import create_engine
    db_url = str(engine.url)
    if db_url.startswith("sqlite+aiosqlite://"):
        db_url = db_url.replace("sqlite+aiosqlite://", "sqlite://")
    elif db_url.startswith("postgresql+asyncpg://"):
        db_url = db_url.replace("postgresql+asyncpg://", "postgresql://")

    sync_engine = create_engine(db_url)
    Base.metadata.create_all(bind=sync_engine)
    sync_engine.dispose()

def test_semantic_layer_synonyms():
    """Verify that semantic layer correctly resolves synonyms and mappings."""
    syns = semantic_layer_service.resolve_synonyms("turnover")
    assert "revenue" in syns
    assert "sales_revenue" in syns

    syns_profit = semantic_layer_service.resolve_synonyms("margin")
    assert "profit" in syns_profit

    # Test NL column mapping
    cols = ["id", "amount", "client_name", "churn_rate"]
    mapping = semantic_layer_service.map_nl_to_columns("Show details for client turnover", cols)
    assert mapping.get("client") == "client_name"
    assert mapping.get("turnover") == "amount"


@pytest.mark.anyio
async def test_knowledge_graph_build_and_query(anyio_backend):
    """Verify entity discovery, relationship inference, and lineage queries."""
    # 1. Clean existing knowledge graph tables
    async with AsyncSessionLocal() as session:
        from sqlalchemy import delete
        await session.execute(delete(KnowledgeRelationship))
        await session.execute(delete(KnowledgeEntity))
        await session.commit()

    # 2. Build graph (this will discover basic glossary terms and seed nodes)
    res = await knowledge_graph_service.build_graph(user_id="1")
    assert res["success"] is True
    assert res["duration_seconds"] >= 0

    # 3. Verify entities were seeded in database
    async with AsyncSessionLocal() as session:
        from sqlalchemy import select
        entities = (await session.execute(select(KnowledgeEntity))).scalars().all()
        
        assert len(entities) > 0
        names = [e.name.lower() for e in entities]
        assert "revenue" in names
        assert "profit" in names

    # 4. Insert dummy entities to test lineage and impact
    async with AsyncSessionLocal() as session:
        ds = KnowledgeEntity(
            id="test-ds-1",
            name="orders_data.csv",
            entity_type="Dataset",
            properties="{}",
            user_id="1"
        )
        tb = KnowledgeEntity(
            id="test-tb-1",
            name="orders",
            entity_type="Table",
            properties="{}",
            user_id="1"
        )
        col = KnowledgeEntity(
            id="test-col-1",
            name="revenue",
            entity_type="Column",
            properties="{}",
            user_id="1"
        )
        session.add_all([ds, tb, col])
        await session.commit()

        # Link Column -> Table and Table -> Dataset (lineage)
        rel1 = KnowledgeRelationship(
            id="rel-1",
            source_id="test-col-1",
            target_id="test-tb-1",
            relationship_type="lineage",
            confidence=1.0,
            user_id="1"
        )
        rel2 = KnowledgeRelationship(
            id="rel-2",
            source_id="test-tb-1",
            target_id="test-ds-1",
            relationship_type="lineage",
            confidence=1.0,
            user_id="1"
        )
        session.add_all([rel1, rel2])
        await session.commit()

    # 5. Query Lineage and Impact
    lineage = await knowledge_graph_service.get_lineage("test-col-1", "1")
    assert len(lineage) == 2
    target_types = [l["target_type"] for l in lineage]
    assert "Table" in target_types
    assert "Dataset" in target_types

    impact = await knowledge_graph_service.get_impact("test-ds-1", "1")
    assert len(impact) == 2
    source_types = [i["source_type"] for i in impact]
    assert "Table" in source_types
    assert "Column" in source_types


@pytest.mark.anyio
async def test_knowledge_graph_apis(anyio_backend):
    """Verify REST API routes return correct structures using dependency overrides."""
    from fastapi.testclient import TestClient
    from app.core.security import get_current_user
    
    client = TestClient(app)
    
    # Inject overrides to bypass authentication checks
    app.dependency_overrides[get_current_user] = lambda: {"id": "1", "email": "test@example.com", "role": "Admin"}
    
    try:
        # Build Graph
        res = client.post("/api/v1/knowledge/build")
        assert res.status_code == 200
        assert res.json()["success"] is True

        # Rebuild Graph
        res_rebuild = client.post("/api/v1/knowledge/rebuild")
        assert res_rebuild.status_code == 200

        # Fetch Entities list
        res_ents = client.get("/api/v1/knowledge/entities")
        assert res_ents.status_code == 200
        assert len(res_ents.json()) > 0

        # Fetch Relationships list
        res_rels = client.get("/api/v1/knowledge/relationships")
        assert res_rels.status_code == 200

        # Semantic search API
        res_search = client.get("/api/v1/knowledge/search?query=turnover")
        assert res_search.status_code == 200
    finally:
        app.dependency_overrides.clear()
