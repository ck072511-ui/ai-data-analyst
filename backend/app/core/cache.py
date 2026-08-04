"""
Simple Cache Manager - Redis based caching
"""

import json
import logging

import redis

from app.core.config import settings

logger = logging.getLogger(__name__)


class CacheManager:
    """Simple cache manager using Redis"""

    def __init__(self):
        self._memory_cache = {}
        try:
            self.redis = redis.from_url(settings.REDIS_URL, decode_responses=True)
            self.redis.ping()
            logger.info("Redis cache connected successfully")
        except Exception as e:
            logger.warning(f"Redis not available, using in-memory cache: {e}")
            self.redis = None

    async def get(self, key: str):
        """Get value from cache"""
        if self.redis:
            try:
                value = self.redis.get(key)
                if value is not None:
                    return json.loads(value)
            except Exception:
                pass
        return self._memory_cache.get(key)

    async def set(self, key: str, value, expire: int = 3600):
        """Set value in cache"""
        if self.redis:
            try:
                self.redis.setex(key, expire, json.dumps(value))
                return True
            except Exception:
                pass
        self._memory_cache[key] = value
        return True

    async def delete(self, key: str):
        """Delete from cache"""
        if self.redis:
            try:
                self.redis.delete(key)
                return
            except Exception:
                pass
        self._memory_cache.pop(key, None)

    async def clear(self):
        """Clear all cache"""
        if self.redis:
            try:
                self.redis.flushall()
                return
            except Exception:
                pass
        self._memory_cache.clear()
