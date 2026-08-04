import os
import time
from datetime import datetime
from typing import Any, Dict

import redis
from sqlalchemy import text

from app.core.config import settings
from app.core.database import AsyncSessionLocal, check_db_health
from app.services.monitoring_service import monitoring_service

# Global application start time to compute Uptime
START_TIME = time.time()


class HealthService:
    async def get_liveness_status(self) -> Dict[str, Any]:
        """Simple liveness report"""
        return {"status": "healthy", "service": "ai-data-analyst", "timestamp": datetime.utcnow().isoformat() + "Z"}

    async def check_storage_health(self) -> bool:
        """Checks if upload directory is available and writable"""
        try:
            upload_dir = os.path.abspath(
                os.path.join(os.path.dirname(__file__), "..", "..", "data", "uploads")
            )
            os.makedirs(upload_dir, exist_ok=True)
            test_file = os.path.join(upload_dir, f".health_check_temp_{int(time.time())}")
            with open(test_file, "w") as f:
                f.write("test")
            os.remove(test_file)
            return True
        except Exception:
            return False

    async def check_auth_health(self) -> bool:
        """Checks if auth database/user lookup table is accessible"""
        try:
            async with AsyncSessionLocal() as session:
                await session.execute(text("SELECT 1 FROM users LIMIT 1"))
            return True
        except Exception:
            return False

    async def check_redis_health(self) -> bool:
        """Checks Redis connection health if configured"""
        try:
            r = redis.from_url(settings.REDIS_URL, decode_responses=True)
            r.ping()
            return True
        except Exception:
            return False

    def get_uptime_string(self) -> str:
        delta = time.time() - START_TIME
        days = int(delta // (24 * 3600))
        hours = int((delta % (24 * 3600)) // 3600)
        minutes = int((delta % 3600) // 60)
        seconds = int(delta % 60)

        parts = []
        if days > 0:
            parts.append(f"{days}d")
        if hours > 0:
            parts.append(f"{hours}h")
        if minutes > 0:
            parts.append(f"{minutes}m")
        parts.append(f"{seconds}s")
        return " ".join(parts)

    async def get_detailed_health(self) -> Dict[str, Any]:
        """Runs checks across all components and compiles structured JSON status report"""
        db_ok = await check_db_health()
        storage_ok = await self.check_storage_health()
        auth_ok = await self.check_auth_health()
        redis_ok = await self.check_redis_health()
        
        # Check LLM health
        llm_ok = False
        try:
            from app.services.model_manager import model_manager
            llm_ok = await model_manager.health_check()
        except Exception:
            pass

        overall_healthy = db_ok and storage_ok and auth_ok

        return {
            "status": "healthy" if overall_healthy else "unhealthy",
            "service": "ai-data-analyst",
            "version": settings.APP_VERSION,
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "uptime": self.get_uptime_string(),
            "uptime_seconds": int(time.time() - START_TIME),
            "checks": {
                "database": "healthy" if db_ok else "unhealthy",
                "storage": "healthy" if storage_ok else "unhealthy",
                "authentication": "healthy" if auth_ok else "unhealthy",
                "redis": "healthy" if redis_ok else "unhealthy",
                "llm": "healthy" if llm_ok else "unhealthy",
            },
            "metrics": {
                "active_requests": monitoring_service.get_active_requests(),
                "average_response_time_ms": monitoring_service.get_avg_response_time_ms(),
                "total_requests": monitoring_service.get_total_requests(),
            },
        }


health_service = HealthService()
