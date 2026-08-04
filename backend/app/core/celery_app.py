from celery import Celery

from app.core.config import settings

# Initialize Celery app
celery_app = Celery("tasks", broker=settings.REDIS_URL, backend=settings.REDIS_URL)

# Celery Configurations
celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    task_time_limit=600,  # 10 minutes hard limit
    task_soft_time_limit=500,  # 8.3 minutes soft limit
)


# Helper function to check if Redis connection is working for Celery broker
def check_celery_broker_available() -> bool:
    try:
        import redis

        r = redis.from_url(settings.REDIS_URL)
        r.ping()
        return True
    except Exception:
        return False


# Celery task registration
@celery_app.task(bind=True, max_retries=3, default_retry_delay=10)
def celery_run_task(self, task_id: str, task_type: str, payload: dict):
    """Celery background worker task wrapper"""
    import asyncio

    from app.services.task_service import task_service

    # Run async logic inside Celery synchronous worker
    try:
        loop = asyncio.get_event_loop()
    except RuntimeError:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)

    return loop.run_until_complete(task_service.execute_task_logic(task_id, task_type, payload))
