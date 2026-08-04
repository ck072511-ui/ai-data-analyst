import os
import sys
from unittest.mock import MagicMock, patch

import pytest

# Adjust path to find backend
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app.models.task import Task
from app.services.cache_service import CacheService
from app.services.task_service import TaskService


@pytest.fixture
def anyio_backend():
    return "asyncio"


@pytest.mark.anyio
async def test_cache_service_offline_fallback(anyio_backend):
    """Verifies CacheService falls back gracefully to in-memory OrderedDict when Redis is offline."""
    cache = CacheService()

    # Mock Redis is offline
    with patch.object(cache, "is_redis_available", return_value=False):
        # Cache writes/reads should function successfully via fallback OrderedDict (async calls)
        await cache.set("resilience_test_key", "graceful_fallback", ttl=30)
        val = await cache.get("resilience_test_key")
        assert val == "graceful_fallback"

        # Verify clear and stats operations work on fallback cache
        stats = cache.get_stats()
        assert stats["hit_rate"] == 100.0
        assert stats["keys_count"] == 1

        await cache.clear()
        val_after_clear = await cache.get("resilience_test_key")
        assert val_after_clear is None


@pytest.mark.anyio
async def test_task_service_celery_offline_fallback(anyio_backend):
    """Verifies TaskService falls back to executing background tasks locally in daemon threads when Celery is offline."""
    task_service = TaskService()

    # Mock database session mapping
    mock_session = MagicMock()
    mock_task = Task(id="resilience-task-uuid", task_type="profiling", status="pending", progress=0, payload="{}")

    # Mock Celery broker is offline
    with patch("app.services.task_service.check_celery_broker_available", return_value=False):
        with patch.object(task_service, "_run_task_locally") as mock_run_local:
            # Trigger execution by passing skip_test_sync to force celery branch check
            await task_service.trigger_task_execution(
                task_id=mock_task.id, task_type=mock_task.task_type, payload={"skip_test_sync": True}
            )
            # Verify the fallback execution path was triggered
            mock_run_local.assert_called_once_with(mock_task.id, mock_task.task_type, {"skip_test_sync": True})
