import json
import os
import sys
import pytest
import asyncio
from datetime import datetime, timedelta
from unittest.mock import patch, MagicMock

# Adjust path to find backend
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

os.environ["DATABASE_URL"] = "sqlite:///./test_analytics.db"
os.environ["SECRET_KEY"] = "test-secret-key-must-be-long-enough-32-chars-at-least"
os.environ["ENVIRONMENT"] = "development"

from sqlalchemy import select
from app.core.database import AsyncSessionLocal, Base, engine
from app.models.user import User
from app.models.workflow import Workflow, WorkflowExecution, WorkflowSchedule
from app.services.workflow_engine import workflow_engine
from app.services.workflow_scheduler import calculate_next_run, get_next_cron_run

USER_ID = None

@pytest.fixture
def anyio_backend():
    return "asyncio"

def setup_module():
    from sqlalchemy import create_engine
    db_url = str(engine.url)
    if db_url.startswith("postgresql+asyncpg://"):
        db_url = db_url.replace("postgresql+asyncpg://", "postgresql://")
    elif db_url.startswith("sqlite+aiosqlite://"):
        db_url = db_url.replace("sqlite+aiosqlite://", "sqlite://")

    sync_engine = create_engine(db_url)
    Base.metadata.create_all(bind=sync_engine)
    sync_engine.dispose()

    # Create test user
    async def create_user():
        global USER_ID
        async with AsyncSessionLocal() as session:
            stmt = select(User).where(User.email == "workflow_test@example.com")
            user = (await session.execute(stmt)).scalar_one_or_none()
            if not user:
                import uuid
                user = User(
                    id=str(uuid.uuid4()),
                    email="workflow_test@example.com",
                    hashed_password="secure_password",
                    role="Admin",
                    is_active=True
                )
                session.add(user)
                await session.commit()
                await session.refresh(user)
            USER_ID = user.id

    try:
        loop = asyncio.get_event_loop()
    except RuntimeError:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
    loop.run_until_complete(create_user())

@pytest.mark.anyio
async def test_cron_scheduler_calculation(anyio_backend):
    # Test cron next run matching
    start = datetime(2026, 7, 29, 12, 0)
    # Every 5 minutes
    next_run = get_next_cron_run("*/5 * * * *", start)
    assert next_run == datetime(2026, 7, 29, 12, 5)

    # Specific hours
    next_run_hour = get_next_cron_run("0 15 * * *", start)
    assert next_run_hour == datetime(2026, 7, 29, 15, 0)

    # Interval checks
    assert calculate_next_run("daily", None, start) == start + timedelta(days=1)
    assert calculate_next_run("weekly", None, start) == start + timedelta(weeks=1)

@pytest.mark.anyio
async def test_sequential_workflow_execution(anyio_backend):
    global USER_ID
    
    # 1. Create a simple workflow DAG: dataset_upload -> notification
    dag_def = {
        "nodes": [
            {
                "id": "node_1",
                "type": "notification",
                "label": "Trigger Initial Alert",
                "config": {
                    "title": "Workflow Started",
                    "message": "Sequential flow test starting.",
                    "severity": "info",
                    "retry_policy": {"max_retries": 1, "delay": 0.1},
                    "timeout": 10
                }
            },
            {
                "id": "node_2",
                "type": "notification",
                "label": "Trigger Final Alert",
                "config": {
                    "title": "Workflow Ended",
                    "message": "Sequential flow test completed.",
                    "severity": "success"
                }
            }
        ],
        "edges": [
            {
                "id": "edge_1",
                "source": "node_1",
                "target": "node_2"
            }
        ]
    }

    async with AsyncSessionLocal() as session:
        wf = Workflow(
            name="Sequential Test",
            description="Tests standard workflow path execution",
            definition=json.dumps(dag_def),
            user_id=USER_ID
        )
        session.add(wf)
        await session.commit()
        await session.refresh(wf)
        wf_id = wf.id

        execution = WorkflowExecution(
            workflow_id=wf_id,
            status="pending",
            user_id=USER_ID
        )
        session.add(execution)
        await session.commit()
        await session.refresh(execution)
        exec_id = execution.id

    # Execute workflow sequentially
    await workflow_engine.execute_workflow(exec_id, USER_ID)

    async with AsyncSessionLocal() as session:
        completed_exec = (await session.execute(
            select(WorkflowExecution).where(WorkflowExecution.id == exec_id)
        )).scalar_one()

        assert completed_exec.status == "completed"
        exec_data = json.loads(completed_exec.execution_data)
        assert exec_data["node_states"]["node_1"]["status"] == "completed"
        assert exec_data["node_states"]["node_2"]["status"] == "completed"

@pytest.mark.anyio
async def test_conditional_if_branching(anyio_backend):
    global USER_ID

    # Workflow DAG: IF quality_score < 80 -> fail alert (True) else success alert (False)
    # Since we can mock the preceding node outputs to test branching paths
    dag_def = {
        "nodes": [
            {
                "id": "node_profile",
                "type": "data_profiling",
                "label": "Mock Data Profile",
                "config": {
                    "dataset_id": "mock_id"
                }
            },
            {
                "id": "node_if",
                "type": "if",
                "label": "Check Quality Score",
                "config": {
                    "condition_field": "quality_score",
                    "operator": "<",
                    "value": 80
                }
            },
            {
                "id": "node_alert_low",
                "type": "notification",
                "label": "Alert Low Quality",
                "config": {
                    "title": "Low Quality Alert",
                    "message": "Quality score is under 80."
                }
            },
            {
                "id": "node_alert_high",
                "type": "notification",
                "label": "Alert High Quality",
                "config": {
                    "title": "High Quality Alert",
                    "message": "Quality score is good."
                }
            }
        ],
        "edges": [
            {
                "id": "edge_to_if",
                "source": "node_profile",
                "target": "node_if"
            },
            {
                "id": "edge_true",
                "source": "node_if",
                "target": "node_alert_low",
                "sourceHandle": "true"
            },
            {
                "id": "edge_false",
                "source": "node_if",
                "target": "node_alert_high",
                "sourceHandle": "false"
            }
        ]
    }

    async with AsyncSessionLocal() as session:
        wf = Workflow(
            name="Conditional If Test",
            definition=json.dumps(dag_def),
            user_id=USER_ID
        )
        session.add(wf)
        await session.commit()
        await session.refresh(wf)
        wf_id = wf.id

        execution = WorkflowExecution(
            workflow_id=wf_id,
            status="pending",
            user_id=USER_ID
        )
        session.add(execution)
        await session.commit()
        await session.refresh(execution)
        exec_id = execution.id

    # Mock execute_node_logic to supply quality_score output
    async def mock_execute_logic(node, context, user_id):
        if node["id"] == "node_profile":
            return {"quality_score": 75} # under 80 -> should trigger true branch node_alert_low
        elif node["type"] == "notification":
            return {"notified": True}
        return {"control": True}

    with patch.object(workflow_engine, "_execute_node_logic", side_effect=mock_execute_logic):
        await workflow_engine.execute_workflow(exec_id, USER_ID)

    async with AsyncSessionLocal() as session:
        completed_exec = (await session.execute(
            select(WorkflowExecution).where(WorkflowExecution.id == exec_id)
        )).scalar_one()

        assert completed_exec.status == "completed"
        exec_data = json.loads(completed_exec.execution_data)
        assert exec_data["node_states"]["node_profile"]["status"] == "completed"
        assert exec_data["node_states"]["node_if"]["status"] == "completed"
        # True branch should be completed, False branch should remain pending
        assert exec_data["node_states"]["node_alert_low"]["status"] == "completed"
        assert exec_data["node_states"]["node_alert_high"]["status"] == "pending"
