import redis

from app.core.celery_app import celery_app
from app.core.config import settings


class WorkerService:
    def check_redis_available(self) -> bool:
        try:
            r = redis.from_url(settings.REDIS_URL, decode_responses=True)
            r.ping()
            return True
        except Exception:
            return False

    def check_celery_available(self) -> bool:
        try:
            insp = celery_app.control.inspect()
            ping_res = insp.ping()
            return ping_res is not None and len(ping_res) > 0
        except Exception:
            return False

    def get_queue_backlog(self) -> int:
        try:
            r = redis.from_url(settings.REDIS_URL)
            return int(r.llen("celery"))
        except Exception:
            return 0

    def get_worker_health_status(self) -> dict:
        redis_ok = self.check_redis_available()
        celery_ok = self.check_celery_available()
        backlog = self.get_queue_backlog() if redis_ok else 0

        overall_healthy = redis_ok

        return {
            "status": "healthy" if overall_healthy else "unhealthy",
            "redis_connected": redis_ok,
            "celery_workers_active": celery_ok,
            "queue_backlog": backlog,
        }


worker_service = WorkerService()
