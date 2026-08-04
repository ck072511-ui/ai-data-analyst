import time
import logging
from typing import Dict, Any, List, Optional
import asyncio

logger = logging.getLogger(__name__)


class ClusterWorker:
    def __init__(
        self,
        worker_id: str,
        name: str,
        host: str,
        port: int,
        capabilities: List[str],
        resources: Dict[str, Any]
    ):
        self.worker_id = worker_id
        self.name = name
        self.host = host
        self.port = port
        self.capabilities = capabilities
        self.resources = resources  # {"cpu_cores": 4, "total_memory_mb": 8192}
        self.status = "healthy"  # healthy, warning, offline
        self.last_heartbeat = time.time()
        self.active_jobs = 0
        self.cpu_util = 0.0
        self.mem_util = 0.0
        self.logs_stream: List[str] = []

    def to_dict(self) -> Dict[str, Any]:
        return {
            "worker_id": self.worker_id,
            "name": self.name,
            "host": self.host,
            "port": self.port,
            "capabilities": self.capabilities,
            "resources": self.resources,
            "status": self.status,
            "last_heartbeat": self.last_heartbeat,
            "active_jobs": self.active_jobs,
            "cpu_util": self.cpu_util,
            "mem_util": self.mem_util,
            "seconds_since_heartbeat": round(time.time() - self.last_heartbeat, 1)
        }


class ClusterManager:
    def __init__(self, heartbeat_timeout: float = 15.0):
        self.workers: Dict[str, ClusterWorker] = {}
        self.heartbeat_timeout = heartbeat_timeout
        self._lock = asyncio.Lock()
        
        # Pre-populate with two simulated offline nodes for instant local distributed testing
        self._prepopulate_virtual_workers()

    def _prepopulate_virtual_workers(self):
        """Registers simulated cluster nodes for local single-machine testing."""
        w1 = ClusterWorker(
            worker_id="worker-1-local",
            name="Virtual GPU Node Alpha",
            host="127.0.0.1",
            port=9001,
            capabilities=["data_cleaning", "predictive", "report", "rag"],
            resources={"cpu_cores": 8, "total_memory_mb": 16384, "gpu": True}
        )
        w2 = ClusterWorker(
            worker_id="worker-2-local",
            name="Virtual Analytics Node Beta",
            host="127.0.0.1",
            port=9002,
            capabilities=["federated_queries", "streaming", "multi_agent", "data_cleaning"],
            resources={"cpu_cores": 4, "total_memory_mb": 8192, "gpu": False}
        )
        self.workers["worker-1-local"] = w1
        self.workers["worker-2-local"] = w2

    async def register_worker(
        self,
        worker_id: str,
        name: str,
        host: str,
        port: int,
        capabilities: List[str],
        resources: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Registers or re-enables a cluster worker node."""
        async with self._lock:
            worker = ClusterWorker(
                worker_id=worker_id,
                name=name,
                host=host,
                port=port,
                capabilities=capabilities,
                resources=resources
            )
            self.workers[worker_id] = worker
            logger.info(f"Worker '{name}' ({worker_id}) registered successfully.")
            
            try:
                from app.services.monitoring_service import monitoring_service
                monitoring_service.set_cluster_worker_count(len(self.get_active_workers()))
            except Exception:
                pass
                
            return worker.to_dict()

    async def record_heartbeat(
        self,
        worker_id: str,
        cpu_util: float,
        mem_util: float,
        active_jobs: int
    ) -> bool:
        """Updates health status and resource telemetry parameters from heartbeats."""
        async with self._lock:
            worker = self.workers.get(worker_id)
            if not worker:
                logger.warning(f"Heartbeat received from unregistered worker: {worker_id}")
                return False
                
            worker.last_heartbeat = time.time()
            worker.cpu_util = cpu_util
            worker.mem_util = mem_util
            worker.active_jobs = active_jobs
            
            # Auto transitions warning status if high resource consumption
            if cpu_util > 90.0 or mem_util > 90.0:
                worker.status = "warning"
            else:
                worker.status = "healthy"
                
            try:
                from app.services.monitoring_service import monitoring_service
                monitoring_service.record_worker_utilization(worker_id, cpu_util, mem_util)
            except Exception:
                pass
                
            return True

    async def run_health_check_sweep(self) -> List[str]:
        """Scans registered workers, transitioning unresponsive nodes to offline."""
        offline_nodes = []
        async with self._lock:
            now = time.time()
            for worker_id, worker in self.workers.items():
                if worker.status != "offline" and (now - worker.last_heartbeat) > self.heartbeat_timeout:
                    worker.status = "offline"
                    logger.error(f"Worker '{worker.name}' ({worker_id}) is offline (no heartbeat for {round(now - worker.last_heartbeat, 1)}s).")
                    offline_nodes.append(worker_id)
                    
                    try:
                        from app.services.monitoring_service import monitoring_service
                        monitoring_service.record_failover_event()
                    except Exception:
                        pass
            
            try:
                from app.services.monitoring_service import monitoring_service
                monitoring_service.set_cluster_worker_count(len(self.get_active_workers()))
            except Exception:
                pass
                
        return offline_nodes

    def get_worker(self, worker_id: str) -> Optional[Dict[str, Any]]:
        worker = self.workers.get(worker_id)
        return worker.to_dict() if worker else None

    def get_all_workers(self) -> List[Dict[str, Any]]:
        return [w.to_dict() for w in self.workers.values()]

    def get_active_workers(self, capability: Optional[str] = None) -> List[ClusterWorker]:
        """Returns online (healthy/warning) workers, optionally filtered by capability."""
        active = []
        for w in self.workers.values():
            if w.status != "offline":
                if capability is None or capability in w.capabilities:
                    active.append(w)
        return active

    def get_topology(self) -> Dict[str, Any]:
        """Generates visual layout mappings of the cluster network nodes and state links."""
        nodes = []
        links = []
        
        # Center hub representation
        nodes.append({
            "id": "hub-center",
            "label": "Platform Coordinator (Hub)",
            "type": "coordinator",
            "status": "healthy"
        })
        
        for w in self.workers.values():
            nodes.append({
                "id": w.worker_id,
                "label": w.name,
                "type": "worker",
                "status": w.status,
                "cpu": w.cpu_util,
                "memory": w.mem_util,
                "jobs": w.active_jobs
            })
            # Draw line mapping connection link
            links.append({
                "source": "hub-center",
                "target": w.worker_id,
                "status": "connected" if w.status != "offline" else "broken"
            })
            
        return {"nodes": nodes, "links": links}


cluster_manager = ClusterManager()
