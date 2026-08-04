import time
import logging
from typing import Dict, Any, List, Optional
import asyncio
import uuid

from app.services.cluster_manager import cluster_manager

logger = logging.getLogger(__name__)


class ClusterJob:
    def __init__(
        self,
        job_id: str,
        task_type: str,
        payload: Dict[str, Any],
        priority: str = "medium",
        preferred_capability: Optional[str] = None,
        max_retries: int = 3
    ):
        self.job_id = job_id
        self.task_type = task_type
        self.payload = payload
        self.priority = priority  # high, medium, low
        self.preferred_capability = preferred_capability
        self.status = "pending"  # pending, running, completed, failed
        self.worker_id: Optional[str] = None
        self.retries = 0
        self.max_retries = max_retries
        self.progress = 0.0
        self.logs: List[str] = []
        self.output: Dict[str, Any] = {}
        self.created_at = time.time()
        self.started_at: Optional[float] = None
        self.completed_at: Optional[float] = None
        self.assigned_at: Optional[float] = None

    def get_priority_weight(self) -> int:
        weights = {"high": 3, "medium": 2, "low": 1}
        return weights.get(self.priority, 2)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "job_id": self.job_id,
            "task_type": self.task_type,
            "payload": self.payload,
            "priority": self.priority,
            "preferred_capability": self.preferred_capability,
            "status": self.status,
            "worker_id": self.worker_id,
            "retries": self.retries,
            "max_retries": self.max_retries,
            "progress": self.progress,
            "logs": self.logs,
            "output": self.output,
            "created_at": self.created_at,
            "started_at": self.started_at,
            "completed_at": self.completed_at
        }


class DistributedScheduler:
    def __init__(self):
        self.jobs: Dict[str, ClusterJob] = {}
        self.queue: List[str] = []  # List of job IDs
        self._lock = asyncio.Lock()
        self._dispatch_loop_task: Optional[asyncio.Task] = None
        self.is_running = False

    async def start(self):
        """Starts the background scheduler dispatch loop."""
        if self.is_running:
            return
        self.is_running = True
        self._dispatch_loop_task = asyncio.create_task(self._scheduler_loop())
        logger.info("Distributed Task Scheduler loop started.")

    async def stop(self):
        self.is_running = False
        if self._dispatch_loop_task:
            self._dispatch_loop_task.cancel()
            try:
                await self._dispatch_loop_task
            except asyncio.CancelledError:
                pass
        logger.info("Distributed Task Scheduler loop stopped.")

    async def submit_job(
        self,
        task_type: str,
        payload: Dict[str, Any],
        priority: str = "medium",
        preferred_capability: Optional[str] = None,
        max_retries: int = 3,
        job_id: Optional[str] = None
    ) -> str:
        """Enqueues a new distributed job request."""
        async with self._lock:
            jid = job_id or f"job-{uuid.uuid4().hex[:8]}"
            job = ClusterJob(
                job_id=jid,
                task_type=task_type,
                payload=payload,
                priority=priority,
                preferred_capability=preferred_capability,
                max_retries=max_retries
            )
            self.jobs[jid] = job
            self.queue.append(jid)
            self._sort_queue()
            
            logger.info(f"Submitted Job '{jid}' [Type: {task_type}, Priority: {priority}]. Queue depth: {len(self.queue)}")
            
            try:
                from app.services.monitoring_service import monitoring_service
                monitoring_service.set_scheduler_queue_depth(len(self.queue))
            except Exception:
                pass
                
            return jid

    def _sort_queue(self):
        """Sorts pending queue by priority (descending) and submission timestamp (ascending)."""
        self.queue.sort(
            key=lambda jid: (-self.jobs[jid].get_priority_weight(), self.jobs[jid].created_at)
        )

    async def _scheduler_loop(self):
        """Infinite loop matching queued jobs to available workers using Least Connection policy."""
        while self.is_running:
            try:
                await asyncio.sleep(0.5)
                await self.dispatch_next_jobs()
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in scheduler loop: {e}", exc_info=True)

    async def dispatch_next_jobs(self):
        """Matches queued jobs to available workers using Least Connection policy."""
        if not self.queue:
            return
        async with self._lock:
            if not self.queue:
                return

            # Keep a temporary list of matched jobs to remove from queue
            dispatched = []

            for jid in list(self.queue):
                job = self.jobs.get(jid)
                if not job or job.status != "pending":
                    dispatched.append(jid)
                    continue

                # Query workers supporting preferred capabilities
                workers = cluster_manager.get_active_workers(job.preferred_capability)
                if not workers:
                    # No active worker supports this capability
                    continue

                # Least Connection Selection: pick worker with lowest active_jobs
                selected_worker = min(workers, key=lambda w: w.active_jobs)
                
                # Assign job
                job.worker_id = selected_worker.worker_id
                job.status = "running"
                job.started_at = time.time()
                job.assigned_at = time.time()
                job.logs.append(f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] Assigned to worker node '{selected_worker.name}'.")
                
                selected_worker.active_jobs += 1
                dispatched.append(jid)

                logger.info(f"Scheduler dispatched Job '{jid}' to Worker '{selected_worker.name}' ({selected_worker.worker_id}).")
                
                # Launch execution handler in background
                asyncio.create_task(self._dispatch_job_execution(job, selected_worker))

            for jid in dispatched:
                if jid in self.queue:
                    self.queue.remove(jid)
            
            try:
                from app.services.monitoring_service import monitoring_service
                monitoring_service.set_scheduler_queue_depth(len(self.queue))
            except Exception:
                pass

    async def _dispatch_job_execution(self, job: ClusterJob, worker: Any):
        """Asynchronous worker pipeline runner. Integrates failover loops on offline statuses."""
        from app.services.worker_agent import worker_agent
        start_time = time.time()

        try:
            # Execute job using worker agent
            success, output = await worker_agent.execute_job_on_node(worker.worker_id, job)
            
            async with self._lock:
                worker.active_jobs = max(0, worker.active_jobs - 1)
                
                if success:
                    job.status = "completed"
                    job.progress = 100.0
                    job.output = output
                    job.completed_at = time.time()
                    job.logs.append(f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] Job completed successfully.")
                    
                    try:
                        from app.services.monitoring_service import monitoring_service
                        monitoring_service.record_scheduler_latency(time.time() - start_time)
                    except Exception:
                        pass
                else:
                    # Job execution failed
                    job.logs.append(f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] Execution failed: {output.get('error', 'Unknown error')}")
                    await self._handle_job_failure(job, output.get("error", "Execution failed"))

        except Exception as e:
            logger.error(f"Execution error on job {job.job_id}: {e}")
            async with self._lock:
                worker.active_jobs = max(0, worker.active_jobs - 1)
                await self._handle_job_failure(job, str(e))

    async def _handle_job_failure(self, job: ClusterJob, error_msg: str):
        """Evaluates retry rules, enqueuing tasks back or transitioning to failed."""
        if job.retries < job.max_retries:
            job.retries += 1
            job.status = "pending"
            job.worker_id = None
            job.logs.append(f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] Retrying execution (Attempt {job.retries}/{job.max_retries}).")
            self.queue.append(job.job_id)
            self._sort_queue()
            
            try:
                from app.services.monitoring_service import monitoring_service
                monitoring_service.record_task_retry()
            except Exception:
                pass
                
            logger.info(f"Job '{job.job_id}' failed and enqueued back for retry (Attempt {job.retries}).")
        else:
            job.status = "failed"
            job.completed_at = time.time()
            job.output = {"error": error_msg}
            job.logs.append(f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] Max retries reached. Job marked as failed.")
            logger.error(f"Job '{job.job_id}' failed permanently after {job.retries} retries: {error_msg}")

    async def handle_worker_failure(self, offline_worker_id: str):
        """Failover re-assignment for jobs currently assigned to an offline worker."""
        async with self._lock:
            for job in self.jobs.values():
                if job.status == "running" and job.worker_id == offline_worker_id:
                    job.logs.append(f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] Worker node went offline. Triggering task failover.")
                    job.worker_id = None
                    job.status = "pending"
                    self.queue.append(job.job_id)
                    self._sort_queue()
                    logger.warning(f"Re-scheduled Job '{job.job_id}' due to failover of worker '{offline_worker_id}'.")
                    
                    try:
                        from app.services.monitoring_service import monitoring_service
                        monitoring_service.record_failover_event()
                    except Exception:
                        pass

    def get_job(self, job_id: str) -> Optional[Dict[str, Any]]:
        job = self.jobs.get(job_id)
        return job.to_dict() if job else None

    def get_all_jobs(self) -> List[Dict[str, Any]]:
        return [j.to_dict() for j in self.jobs.values()]


distributed_scheduler = DistributedScheduler()
