import os
import sys
import json
import pytest
import asyncio
from unittest.mock import AsyncMock, patch, MagicMock

# Adjust path to find backend
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

# Set environment variables for testing
os.environ["DATABASE_URL"] = "sqlite:///./test_analytics.db"
os.environ["SECRET_KEY"] = "test-secret-key-must-be-long-enough-32-chars-at-least"
os.environ["ENVIRONMENT"] = "development"

from app.services.cluster_manager import ClusterManager, ClusterWorker
from app.services.distributed_scheduler import DistributedScheduler, ClusterJob
from app.services.worker_agent import WorkerAgent
from app.services.workflow_engine import WorkflowEngine
from app.core.security import get_current_user
from fastapi.testclient import TestClient
from app.main import app

@pytest.fixture
def anyio_backend():
    return "asyncio"


# 1. Cluster Manager Registration & Heartbeats
@pytest.mark.anyio
async def test_cluster_worker_registration_lifecycle():
    manager = ClusterManager()
    
    # Check registration
    worker_id = "test-worker-node"
    capabilities = ["rag", "analytics"]
    resources = {"cpu_cores": 4, "total_memory_mb": 8192}
    
    res = await manager.register_worker(
        worker_id=worker_id,
        name="Test Worker",
        host="127.0.0.1",
        port=8081,
        capabilities=capabilities,
        resources=resources
    )
    
    assert res["worker_id"] == worker_id
    assert res["status"] == "healthy"
    assert worker_id in [w["worker_id"] for w in manager.get_all_workers()]
    
    # Check heartbeats update resource statistics
    success = await manager.record_heartbeat(
        worker_id=worker_id,
        cpu_util=45.2,
        mem_util=60.8,
        active_jobs=2
    )
    assert success is True
    
    worker_dict = manager.get_worker(worker_id)
    assert worker_dict["cpu_util"] == 45.2
    assert worker_dict["mem_util"] == 60.8
    assert worker_dict["active_jobs"] == 2


# 2. Heartbeats Unresponsive Sweep & Node Transition Offline
@pytest.mark.anyio
async def test_heartbeat_sweep_and_transition_offline():
    # Setup short timeout for testing
    manager = ClusterManager(heartbeat_timeout=0.1)
    
    worker_id = "temp-worker"
    await manager.register_worker(
        worker_id=worker_id,
        name="Temp Worker",
        host="127.0.0.1",
        port=8082,
        capabilities=["analytics"],
        resources={}
    )
    
    # Initial status is healthy
    assert manager.get_worker(worker_id)["status"] == "healthy"
    
    # Sleep to exceed timeout threshold
    await asyncio.sleep(0.15)
    
    offline_nodes = await manager.run_health_check_sweep()
    assert worker_id in offline_nodes
    assert manager.get_worker(worker_id)["status"] == "offline"


# 3. Distributed Scheduler Queue Priority Sorting
@pytest.mark.anyio
async def test_scheduler_queue_priority_sorting():
    scheduler = DistributedScheduler()
    
    # Submit multiple jobs with different priorities
    j1 = await scheduler.submit_job("analytics", {"task": 1}, priority="low")
    j2 = await scheduler.submit_job("analytics", {"task": 2}, priority="high")
    j3 = await scheduler.submit_job("analytics", {"task": 3}, priority="medium")
    
    # Assert queue is sorted: high -> medium -> low
    assert scheduler.queue[0] == j2  # High
    assert scheduler.queue[1] == j3  # Medium
    assert scheduler.queue[2] == j1  # Low


# 4. Local Fallback Mode
@pytest.mark.anyio
async def test_workflow_engine_local_fallback_no_workers():
    # Setup workflow execution contexts with distributed config
    node = {
        "id": "predictive_node_1",
        "type": "prescriptive_analysis",
        "config": {
            "execution_mode": "distributed",
            "preferred_capability": "predictive",
            "priority": "high",
            "model_id": "model-1",
            "base_features": {"f1": 10.0},
            "actionable_features": ["f1"],
            "business_rules": {"f1": {"min": 5.0, "max": 15.0}},
            "target_direction": "maximize"
        }
    }
    
    context = {
        "node_states": {
            "predictive_node_1": {
                "status": "pending",
                "logs": []
            }
        },
        "outputs": {},
        "variables": {}
    }
    
    engine = WorkflowEngine()
    
    # Verify that in a mock environment without any active cluster workers, the engine executes locally without crashing
    with patch("app.services.cluster_manager.ClusterManager.get_active_workers", return_value=[]), \
         patch("app.services.prescriptive_service.prescriptive_service.generate_prescriptive_actions", new_callable=AsyncMock) as mock_run:
         
        mock_run.return_value = {"recommendation_count": 2}
        
        node_id, success, output = await engine._run_node_with_retry_and_timeout(node, "exec-1", context, user_id="test_user")
        assert success is True
        assert output["recommendation_count"] == 2
        
        # Verify log confirms fallback
        fallback_log = any("Falling back to local execution" in log for log in context["node_states"]["predictive_node_1"]["logs"])
        assert fallback_log is True


# 5. Distributed Execution on Worker Node
@pytest.mark.anyio
async def test_worker_agent_execution_logic():
    agent = WorkerAgent()
    
    job = ClusterJob(
        job_id="test-job-id",
        task_type="ai_cleaning",
        payload={"mock": True, "dataset_id": "test_dataset"}
    )
    
    success, output = await agent.execute_job_on_node("worker-1-local", job)
    assert success is True
    assert output["cleaned_rows"] == 100
    assert job.progress == 100.0


# 6. Scheduler Task Re-assignment on Failover
@pytest.mark.anyio
async def test_scheduler_failover_reassignment():
    scheduler = DistributedScheduler()
    
    # Submit job and mark running on worker-x
    job_id = await scheduler.submit_job("analytics", {"task": 1}, priority="high")
    job = scheduler.jobs[job_id]
    job.status = "running"
    job.worker_id = "worker-x"
    
    # Trigger worker failure
    await scheduler.handle_worker_failure("worker-x")
    
    # Verify job is enqueued back with status pending and worker cleared
    assert job.status == "pending"
    assert job.worker_id is None
    assert job_id in scheduler.queue


# 7. Endpoint HTTP routes integration
def test_cluster_endpoints():
    client = TestClient(app)
    token_headers = {"Authorization": "Bearer dummy_token"}
    
    # Setup dependency overrides for auth and mock permissions
    app.dependency_overrides[get_current_user] = lambda: {"id": "admin_user", "email": "admin@example.com", "role": "Admin"}
    
    try:
        # GET /api/v1/cluster/workers
        response = client.get("/api/v1/cluster/workers", headers=token_headers)
        assert response.status_code == 200
        assert isinstance(response.json(), list)
        
        # GET /api/v1/cluster/topology
        response = client.get("/api/v1/cluster/topology", headers=token_headers)
        assert response.status_code == 200
        assert "nodes" in response.json()
        assert "links" in response.json()
        
        # POST /api/v1/cluster/register
        reg_body = {
            "worker_id": "api-worker-test",
            "name": "API Test Worker",
            "host": "127.0.0.1",
            "port": 8990,
            "capabilities": ["streaming"],
            "resources": {"cores": 2}
        }
        response = client.post("/api/v1/cluster/register", json=reg_body, headers=token_headers)
        assert response.status_code == 200
        
        # POST /api/v1/cluster/heartbeat
        hb_body = {
            "worker_id": "api-worker-test",
            "cpu_util": 12.5,
            "mem_util": 35.0,
            "active_jobs": 0
        }
        response = client.post("/api/v1/cluster/heartbeat", json=hb_body, headers=token_headers)
        assert response.status_code == 200
        
        # POST /api/v1/cluster/dispatch
        disp_body = {
            "task_type": "report",
            "payload": {"mock": True},
            "priority": "low"
        }
        response = client.post("/api/v1/cluster/dispatch", json=disp_body, headers=token_headers)
        assert response.status_code == 200
        assert "job_id" in response.json()
        
    finally:
        app.dependency_overrides.clear()
