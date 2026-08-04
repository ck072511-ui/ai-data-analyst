import json
import os
import sys

import pytest

# Adjust path to find backend
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

# Set environment variables for testing before importing settings
os.environ["DATABASE_URL"] = "sqlite:///./test_analytics.db"
os.environ["SECRET_KEY"] = "test-secret-key-must-be-long-enough-32-chars-at-least"
os.environ["ENVIRONMENT"] = "development"

import asyncio
from unittest.mock import MagicMock, patch

from sqlalchemy import select

from app.core.celery_app import celery_run_task
from app.core.database import AsyncSessionLocal, Base, engine
from app.models.dataset import UserDataset
from app.models.task import Task
from app.models.user import User
from app.services.task_service import task_service
from app.services.worker_service import worker_service

USER_ID = None
DATASET_ID = None


@pytest.fixture
def anyio_backend():
    return "asyncio"


def setup_module():
    # Setup database schema
    from sqlalchemy import create_engine

    db_url = str(engine.url)
    if db_url.startswith("postgresql+asyncpg://"):
        db_url = db_url.replace("postgresql+asyncpg://", "postgresql://")
    elif db_url.startswith("sqlite+aiosqlite://"):
        db_url = db_url.replace("sqlite+aiosqlite://", "sqlite://")

    sync_engine = create_engine(db_url)
    Base.metadata.create_all(bind=sync_engine)
    sync_engine.dispose()

    # Initialize a test user and dataset
    async def create_records():
        global USER_ID, DATASET_ID
        async with AsyncSessionLocal() as session:
            # Create user if not exists
            stmt = select(User).where(User.email == "background_test@example.com")
            user = (await session.execute(stmt)).scalar_one_or_none()
            if not user:
                import uuid

                user = User(
                    id=str(uuid.uuid4()),
                    email="background_test@example.com",
                    hashed_password="secure_password",
                    role="Admin",
                    is_active=True,
                )
                session.add(user)
                await session.commit()
                await session.refresh(user)
            USER_ID = user.id

            # Create dataset
            stmt = select(UserDataset).where(UserDataset.filename == "test_task_data.csv")
            dataset = (await session.execute(stmt)).scalar_one_or_none()
            if not dataset:
                import uuid

                dataset = UserDataset(
                    id=str(uuid.uuid4()),
                    user_id=user.id,
                    filename="test_task_data.csv",
                    table_name="test_task_table",
                    file_path="test_task_data.csv",
                    row_count=0,
                    col_count=0,
                    columns=[],
                    schema_info={},
                    profile_info={},
                    status="processing",
                )
                session.add(dataset)
                await session.commit()
                await session.refresh(dataset)
            DATASET_ID = dataset.id

    try:
        loop = asyncio.get_event_loop()
    except RuntimeError:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
    loop.run_until_complete(create_records())


@pytest.mark.anyio
async def test_task_creation_and_payload_storage():
    payload = {"dataset_id": DATASET_ID, "mode": "fast"}

    with patch.object(task_service, "trigger_task_execution") as mock_trigger:
        task = await task_service.create_task(
            task_type="dataset_profiling", user_id=USER_ID, dataset_id=DATASET_ID, payload=payload
        )

        assert task.id is not None
        assert task.task_type == "dataset_profiling"
        assert task.status == "pending"
        assert json.loads(task.payload) == payload
        mock_trigger.assert_called_once_with(task.id, "dataset_profiling", payload)


@pytest.mark.anyio
async def test_local_thread_fallback_on_broker_offline():
    payload = {"dataset_id": DATASET_ID, "skip_test_sync": True}

    with (
        patch("app.services.task_service.check_celery_broker_available", return_value=False),
        patch.object(task_service, "_run_task_locally") as mock_run_local,
    ):

        await task_service.trigger_task_execution("dummy-id", "dataset_profiling", payload)
        mock_run_local.assert_called_once_with("dummy-id", "dataset_profiling", payload)


@pytest.mark.anyio
async def test_worker_health_diagnostics():
    mock_redis = MagicMock()
    mock_redis.ping.return_value = True
    mock_redis.llen.return_value = 5

    mock_ping = MagicMock()
    mock_ping.ping.return_value = {"celery@localhost": "pong"}

    with (
        patch("redis.from_url", return_value=mock_redis),
        patch("app.core.celery_app.celery_app.control.inspect", return_value=mock_ping),
    ):

        status = worker_service.get_worker_health_status()
        assert status["status"] == "healthy"
        assert status["redis_connected"] is True
        assert status["celery_workers_active"] is True
        assert status["queue_backlog"] == 5


@pytest.mark.anyio
async def test_task_progress_tracking_updates():
    async with AsyncSessionLocal() as session:
        task = Task(
            id="test-progress-id", task_type="ai_insights", status="pending", progress=0, user_id=USER_ID, payload="{}"
        )
        session.add(task)
        await session.commit()

    async with AsyncSessionLocal() as session:
        await task_service.update_progress("test-progress-id", 65, session)

    async with AsyncSessionLocal() as session:
        updated_task = (await session.execute(select(Task).where(Task.id == "test-progress-id"))).scalar_one()
        assert updated_task.progress == 65
        assert updated_task.status == "running"

        await session.delete(updated_task)
        await session.commit()


@pytest.mark.anyio
async def test_task_retry_mechanism():
    async with AsyncSessionLocal() as session:
        task = Task(
            id="test-retry-id",
            task_type="ai_insights",
            status="failed",
            progress=40,
            user_id=USER_ID,
            dataset_id=DATASET_ID,
            payload=json.dumps({"dataset_id": DATASET_ID}),
            error_message="Connection timed out",
        )
        session.add(task)
        await session.commit()

    with patch.object(task_service, "trigger_task_execution") as mock_trigger:
        async with AsyncSessionLocal() as session:
            retried_task = await task_service.retry_task("test-retry-id", session)

            assert retried_task.status == "pending"
            assert retried_task.progress == 0
            assert retried_task.error_message is None
            mock_trigger.assert_called_once_with("test-retry-id", "ai_insights", {"dataset_id": DATASET_ID})

        async with AsyncSessionLocal() as session:
            db_task = (await session.execute(select(Task).where(Task.id == "test-retry-id"))).scalar_one()
            await session.delete(db_task)
            await session.commit()


def test_celery_wrapper_logic_execution():
    import asyncio

    from app.core.database import AsyncSessionLocal

    async def helper():
        async with AsyncSessionLocal() as session:
            task = Task(
                id="test-celery-run-id",
                task_type="ai_insights",
                status="pending",
                progress=0,
                user_id=USER_ID,
                dataset_id=DATASET_ID,
                payload="{}",
            )
            session.add(task)
            await session.commit()

        with (
            patch.object(task_service, "execute_task_logic", return_value=None) as mock_exec,
            patch("asyncio.get_event_loop") as mock_get_loop,
        ):

            mock_loop = MagicMock()
            mock_get_loop.return_value = mock_loop
            celery_run_task("test-celery-run-id", "ai_insights", {})
            mock_loop.run_until_complete.assert_called_once()

        async with AsyncSessionLocal() as session:
            db_task = (await session.execute(select(Task).where(Task.id == "test-celery-run-id"))).scalar_one()
            await session.delete(db_task)
            await session.commit()

    try:
        loop = asyncio.get_event_loop()
    except RuntimeError:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
    loop.run_until_complete(helper())
