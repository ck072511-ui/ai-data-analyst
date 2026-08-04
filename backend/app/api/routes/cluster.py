import logging
from typing import Dict, Any, List, Optional
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel

from app.core.security import get_current_user
from app.services.permission_service import require_permission
from app.services.cluster_manager import cluster_manager
from app.services.distributed_scheduler import distributed_scheduler

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/cluster", tags=["Distributed Cluster Management"])


class WorkerRegisterRequest(BaseModel):
    worker_id: str
    name: str
    host: str
    port: int
    capabilities: List[str]
    resources: Dict[str, Any]


class WorkerHeartbeatRequest(BaseModel):
    worker_id: str
    cpu_util: float
    mem_util: float
    active_jobs: int


class DispatchJobRequest(BaseModel):
    task_type: str
    payload: Dict[str, Any]
    priority: str = "medium"
    preferred_capability: Optional[str] = None
    max_retries: int = 3


@router.get("/workers", dependencies=[Depends(require_permission("view"))])
async def list_workers(current_user: dict = Depends(get_current_user)):
    """Returns lists of all registered and virtual cluster nodes."""
    try:
        # Trigger health check sweep to ensure statuses are updated
        await cluster_manager.run_health_check_sweep()
        return cluster_manager.get_all_workers()
    except Exception as e:
        logger.exception("Failed to retrieve workers list")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/jobs", dependencies=[Depends(require_permission("view"))])
async def list_jobs(current_user: dict = Depends(get_current_user)):
    """Retrieves all submitted, pending, active, and completed cluster jobs."""
    try:
        return distributed_scheduler.get_all_jobs()
    except Exception as e:
        logger.exception("Failed to retrieve jobs list")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/register")
async def register_worker(request: WorkerRegisterRequest):
    """Registers a new worker node (called by remote worker agents)."""
    try:
        res = await cluster_manager.register_worker(
            worker_id=request.worker_id,
            name=request.name,
            host=request.host,
            port=request.port,
            capabilities=request.capabilities,
            resources=request.resources
        )
        return {"status": "success", "worker": res}
    except Exception as e:
        logger.exception(f"Failed to register worker {request.worker_id}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/heartbeat")
async def record_heartbeat(request: WorkerHeartbeatRequest):
    """Records heartbeat and resources utilization metrics from active worker agents."""
    success = await cluster_manager.record_heartbeat(
        worker_id=request.worker_id,
        cpu_util=request.cpu_util,
        mem_util=request.mem_util,
        active_jobs=request.active_jobs
    )
    if not success:
        raise HTTPException(status_code=404, detail=f"Worker '{request.worker_id}' not found. Please register first.")
    return {"status": "recorded"}


@router.post("/dispatch", dependencies=[Depends(require_permission("view"))])
async def dispatch_job(request: DispatchJobRequest, current_user: dict = Depends(get_current_user)):
    """Dispatches a job to the cluster scheduler queue."""
    try:
        job_id = await distributed_scheduler.submit_job(
            task_type=request.task_type,
            payload=request.payload,
            priority=request.priority,
            preferred_capability=request.preferred_capability,
            max_retries=request.max_retries
        )
        return {"status": "enqueued", "job_id": job_id}
    except Exception as e:
        logger.exception("Failed to submit distributed job")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/topology", dependencies=[Depends(require_permission("view"))])
async def get_topology(current_user: dict = Depends(get_current_user)):
    """Returns cluster network node structures and state connections."""
    try:
        await cluster_manager.run_health_check_sweep()
        return cluster_manager.get_topology()
    except Exception as e:
        logger.exception("Failed to compile cluster topology")
        raise HTTPException(status_code=500, detail=str(e))
