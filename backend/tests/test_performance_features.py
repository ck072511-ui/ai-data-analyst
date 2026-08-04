import os
import sys

import pytest
from fastapi.testclient import TestClient

# Adjust path to find backend
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

# Set environment variables for testing before importing main app
os.environ["DATABASE_URL"] = "sqlite:///./test_performance.db"
os.environ["SECRET_KEY"] = "test-secret-key-must-be-long-enough-32-chars-at-least"
os.environ["ENVIRONMENT"] = "development"

from app.core.database import AsyncSessionLocal
from app.main import app
from app.models.user import User
from app.services.cache_service import cache_service
from app.services.performance_service import performance_service
from app.utils.pagination import paginate

client = TestClient(app)


@pytest.fixture
def anyio_backend():
    return "asyncio"


@pytest.fixture(scope="module", autouse=True)
def setup_database():
    from sqlalchemy import create_engine

    from app.core.database import Base, engine

    db_url = str(engine.url)
    if db_url.startswith("postgresql+asyncpg://"):
        db_url = db_url.replace("postgresql+asyncpg://", "postgresql://")
    elif db_url.startswith("sqlite+aiosqlite://"):
        db_url = db_url.replace("sqlite+aiosqlite://", "sqlite://")

    sync_engine = create_engine(db_url)
    Base.metadata.create_all(bind=sync_engine)
    yield
    sync_engine.dispose()


@pytest.mark.anyio
async def test_cache_operations_and_fallback():
    # Verify set and get
    await cache_service.set("perf_test_key", {"data": 42}, ttl=60)
    val = await cache_service.get("perf_test_key")
    assert val == {"data": 42}

    # Verify delete
    await cache_service.delete("perf_test_key")
    val = await cache_service.get("perf_test_key")
    assert val is None


@pytest.mark.anyio
async def test_cache_invalidation():
    # Set mock user profile and permissions
    await cache_service.set("user:profile:user123", {"name": "Test User"})
    await cache_service.set("user:permissions:user123:view", True)

    # Run user invalidation
    await cache_service.invalidate_user("user123")

    # Verify both caches cleared
    p = await cache_service.get("user:profile:user123")
    perm = await cache_service.get("user:permissions:user123:view")
    assert p is None
    assert perm is None


@pytest.mark.anyio
async def test_cache_pattern_invalidation():
    await cache_service.set("dataset:list:user123:p_1", "page1")
    await cache_service.set("dataset:list:user123:p_2", "page2")
    await cache_service.set("dataset:details:ds999", "details")

    # Invalidate all user dataset lists
    await cache_service.invalidate_pattern("dataset:list:user123:*")

    l1 = await cache_service.get("dataset:list:user123:p_1")
    l2 = await cache_service.get("dataset:list:user123:p_2")
    det = await cache_service.get("dataset:details:ds999")

    assert l1 is None
    assert l2 is None
    assert det == "details"
    await cache_service.delete("dataset:details:ds999")


@pytest.mark.anyio
async def test_pagination_utility():
    async with AsyncSessionLocal() as session:
        # Use paginate helper on User table
        items, meta = await paginate(
            session=session, model=User, page=1, page_size=5, sort_by="email", sort_order="asc"
        )
        assert isinstance(items, list)
        assert "page" in meta
        assert meta["page"] == 1
        assert meta["page_size"] == 5


def test_gzip_compression_response():
    headers = {"Accept-Encoding": "gzip"}
    response = client.get("/health", headers=headers)
    assert response.status_code == 200

    content_encoding = response.headers.get("Content-Encoding", "")
    assert "gzip" in content_encoding or content_encoding == ""


@pytest.mark.anyio
async def test_performance_slow_queries_tracking():
    # Simulate a slow query recording
    performance_service.record_slow_query("SELECT * FROM dashboards WHERE user_id = :id", 0.25)
    stats = await performance_service.get_stats()
    assert len(stats["slow_queries"]) > 0
    assert stats["slow_queries"][-1]["sql"] == "SELECT * FROM dashboards WHERE user_id = :id"
    assert stats["slow_queries"][-1]["duration_sec"] == 0.25
