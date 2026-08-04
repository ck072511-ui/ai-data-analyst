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
from app.models.stream import StreamConfig, StreamAlert
from app.models.workflow import Workflow, WorkflowExecution
from app.models.knowledge import KnowledgeEntity
from app.services.streaming_service import streaming_service, CSVFileTailAdapter, ProcessingWindow
from app.services.stream_analytics_service import stream_analytics_service
from app.services.stream_alert_service import stream_alert_service
from app.services.knowledge_graph_service import knowledge_graph_service

USER_ID = None

@pytest.fixture
def anyio_backend():
    return "asyncio"

@pytest.fixture(autouse=True)
async def setup_db():
    from sqlalchemy import create_engine
    db_url = str(engine.url)
    if db_url.startswith("postgresql+asyncpg://"):
        db_url = db_url.replace("postgresql+asyncpg://", "postgresql://")
    elif db_url.startswith("sqlite+aiosqlite://"):
        db_url = db_url.replace("sqlite+aiosqlite://", "sqlite://")

    sync_engine = create_engine(db_url)
    Base.metadata.drop_all(bind=sync_engine)
    Base.metadata.create_all(bind=sync_engine)
    sync_engine.dispose()

    # Create test user
    global USER_ID
    async with AsyncSessionLocal() as session:
        stmt = select(User).where(User.email == "streaming_test@example.com")
        user = (await session.execute(stmt)).scalar_one_or_none()
        if not user:
            import uuid
            user = User(
                id=str(uuid.uuid4()),
                email="streaming_test@example.com",
                hashed_password="secure_password",
                role="Admin",
                is_active=True
            )
            session.add(user)
            await session.commit()
            await session.refresh(user)
        USER_ID = user.id

@pytest.mark.anyio
async def test_stream_creation_and_listing(anyio_backend):
    global USER_ID
    async with AsyncSessionLocal() as session:
        # Create configuration
        config = StreamConfig(
            name="Test Ingest Stream",
            description="Testing ingestion metadata registry",
            source_type="csv",
            source_config=json.dumps({"file_path": "./test_logs.csv", "poll_interval_sec": 1.0}),
            window_type="tumbling",
            window_size_sec="10",
            aggregations=json.dumps([{"field": "val", "op": "sum", "label": "sum_val"}]),
            schema_definition=json.dumps({"val": "float"}),
            active=False,
            user_id=USER_ID
        )
        session.add(config)
        await session.commit()
        await session.refresh(config)
        stream_id = config.id

    async with AsyncSessionLocal() as session:
        records = (await session.execute(
            select(StreamConfig).where(StreamConfig.user_id == USER_ID)
        )).scalars().all()
        assert len(records) > 0
        assert any(r.id == stream_id for r in records)

@pytest.mark.anyio
async def test_window_aggregations(anyio_backend):
    # Setup mock stream config
    stream = StreamConfig(
        id="mock_stream_123",
        name="Mock Tumbling Stream",
        window_type="tumbling",
        window_size_sec="5",
        aggregations=json.dumps([
            {"field": "price", "op": "sum", "label": "sum_price"},
            {"field": "price", "op": "average", "label": "avg_price"},
            {"field": "price", "op": "max", "label": "max_price"},
            {"field": "price", "op": "distinct_count", "label": "unique_count"}
        ]),
        schema_definition=json.dumps({"price": "float"})
    )

    window = ProcessingWindow(datetime.utcnow(), datetime.utcnow() + timedelta(seconds=5))
    window.events = [
        {"price": 10.0, "_timestamp": datetime.utcnow().isoformat()},
        {"price": 20.0, "_timestamp": datetime.utcnow().isoformat()},
        {"price": 20.0, "_timestamp": datetime.utcnow().isoformat()},
        {"price": 30.0, "_timestamp": datetime.utcnow().isoformat()}
    ]

    with patch("app.services.stream_analytics_service.stream_analytics_service.process_window_results") as mock_analytics:
        await streaming_service._evaluate_and_trigger_window(stream.id, window, stream, "test_user")
        
        # Verify analytics was triggered with aggregate calculations
        mock_analytics.assert_called_once()
        args = mock_analytics.call_args[0]
        assert args[0] == stream.id
        results = args[1]
        assert results["sum_price"] == 80.0
        assert results["avg_price"] == 20.0
        assert results["max_price"] == 30.0
        assert results["unique_count"] == 3
        assert results["_event_count"] == 4

@pytest.mark.anyio
async def test_anomaly_detection_z_score(anyio_backend):
    stream_id = "stream_z_score_test"
    
    # Pre-populate history to build standard deviation base
    stream_analytics_service.window_history[stream_id] = [
        {"metric_val": 10.0, "_event_count": 1},
        {"metric_val": 11.0, "_event_count": 1},
        {"metric_val": 10.5, "_event_count": 1},
        {"metric_val": 9.5, "_event_count": 1},
        {"metric_val": 10.0, "_event_count": 1}
    ]

    # Clean previous records
    stream_analytics_service.running_kpis[stream_id] = {}

    with patch("app.services.stream_alert_service.stream_alert_service.trigger_anomaly_alert") as mock_alert:
        # Push anomalous value (50.0 is way higher than mean ~10.0 with stddev ~0.5)
        new_result = {"metric_val": 50.0, "_event_count": 1}
        await stream_analytics_service.process_window_results(stream_id, new_result, "test_user")
        
        # Anomaly should have been triggered
        mock_alert.assert_called_once()

@pytest.mark.anyio
async def test_threshold_checking(anyio_backend):
    global USER_ID
    async with AsyncSessionLocal() as session:
        stream = StreamConfig(
            id="threshold_check_stream",
            name="Threshold Test Stream",
            source_type="rest",
            source_config=json.dumps({
                "max_queue_size": 100,
                "thresholds": [{"field": "sum_sales", "operator": ">", "value": 1000, "severity": "critical"}]
            }),
            user_id=USER_ID
        )
        session.add(stream)
        await session.commit()

    with patch("app.services.stream_alert_service.StreamAlertService.trigger_threshold_alert") as mock_alert:
        results = {"sum_sales": 1500, "_event_count": 10}
        await stream_analytics_service.process_window_results(stream.id, results, USER_ID)
        mock_alert.assert_called_once_with(
            stream_id=stream.id,
            message="Threshold breached on Threshold Test Stream: field 'sum_sales' = 1500.0 (Condition: > 1000.0)",
            severity="critical",
            user_id=USER_ID
        )

@pytest.mark.anyio
async def test_incremental_knowledge_graph_updates(anyio_backend):
    global USER_ID
    stream = StreamConfig(
        id="incremental_kg_stream",
        name="KG Realtime Stream",
        source_type="websocket",
        window_type="session",
        window_size_sec="15",
        schema_definition=json.dumps({"clicks": "integer", "device": "string"}),
        user_id=USER_ID
    )

    await knowledge_graph_service.register_stream_incrementally(stream, USER_ID)
    
    async with AsyncSessionLocal() as session:
        # Verify Stream entity is registered
        ent = (await session.execute(
            select(KnowledgeEntity).where(KnowledgeEntity.source_id == f"stream_{stream.id}")
        )).scalar_one_or_none()
        assert ent is not None
        assert ent.name == "KG Realtime Stream"
        assert ent.entity_type == "Dataset"

        # Verify Column entity clicks is registered
        clicks_col = (await session.execute(
            select(KnowledgeEntity).where(KnowledgeEntity.source_id == f"col_{stream.id}_clicks")
        )).scalar_one_or_none()
        assert clicks_col is not None
        assert clicks_col.name == "clicks"

@pytest.mark.anyio
async def test_alert_workflow_triggering(anyio_backend):
    global USER_ID
    
    # 1. Create a Workflow with a stream_processor node configured to listen to this stream alerts
    wf_def = {
        "nodes": [
            {
                "id": "node_trigger",
                "type": "stream_processor",
                "label": "Listen to Alert Trigger",
                "config": {
                    "stream_id": "alert_trigger_stream",
                    "trigger_types": ["anomaly"]
                }
            },
            {
                "id": "node_action",
                "type": "notification",
                "label": "Notification Output",
                "config": {
                    "title": "Alert Trigger Handled",
                    "message": "Anomaly workflow successfully triggered!"
                }
            }
        ],
        "edges": [
            {"id": "edge_1", "source": "node_trigger", "target": "node_action"}
        ]
    }

    async with AsyncSessionLocal() as session:
        wf = Workflow(
            name="Stream Alert Listener Workflow",
            definition=json.dumps(wf_def),
            user_id=USER_ID
        )
        session.add(wf)
        await session.commit()
        await session.refresh(wf)
        wf_id = wf.id

    # 2. Trigger an anomaly alert for this stream
    with patch("app.services.workflow_engine.workflow_engine.execute_workflow") as mock_exec:
        await stream_alert_service._create_alert(
            stream_id="alert_trigger_stream",
            alert_type="anomaly",
            message="Critical statistical anomaly anomaly_trigger_stream",
            severity="critical",
            user_id=USER_ID
        )
        
        # Verify that execute_workflow was invoked for this workflow run
        mock_exec.assert_called_once()
        args = mock_exec.call_args[0]
        # First arg should be the generated WorkflowExecution ID
        assert isinstance(args[0], str)
        # Second arg should be USER_ID
        assert args[1] == USER_ID
