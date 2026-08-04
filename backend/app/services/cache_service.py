import json
import logging
from collections import OrderedDict
from typing import Any, Optional

import redis

from app.core.config import settings
from app.services.monitoring_service import monitoring_service

logger = logging.getLogger(__name__)


class CacheService:
    def __init__(self):
        self._redis_client = None
        self._fallback_cache = OrderedDict()
        self._max_fallback_size = 1000

        # In-memory stats counter for internal dashboard
        self.hits = 0
        self.misses = 0

        try:
            self._redis_client = redis.from_url(settings.REDIS_URL, decode_responses=True)
            self._redis_client.ping()
            logger.info("CacheService connected to Redis successfully.")
        except Exception as e:
            logger.warning(f"Redis cache broker offline, falling back to local memory: {e}")
            self._redis_client = None

    def is_redis_available(self) -> bool:
        if self._redis_client is None:
            return False
        try:
            self._redis_client.ping()
            return True
        except Exception:
            return False

    async def get(self, key: str) -> Optional[Any]:
        """Get a value from cache. Falls back to in-memory dictionary if Redis is offline."""
        if self.is_redis_available():
            try:
                val = self._redis_client.get(key)
                if val is not None:
                    self.hits += 1
                    monitoring_service.record_cache_hit("redis")
                    return json.loads(val)
            except Exception as e:
                logger.error(f"Redis get error: {e}")

        # Fallback cache
        if key in self._fallback_cache:
            self.hits += 1
            monitoring_service.record_cache_hit("memory")
            # Move to end (LRU behavior)
            val = self._fallback_cache.pop(key)
            self._fallback_cache[key] = val
            return val

        self.misses += 1
        monitoring_service.record_cache_miss("redis" if self._redis_client else "memory")
        return None

    async def set(self, key: str, value: Any, ttl: int = 3600) -> bool:
        """Set a value in cache. Falls back to in-memory dictionary if Redis is offline."""
        if self.is_redis_available():
            try:
                self._redis_client.setex(key, ttl, json.dumps(value))
                self._update_metrics()
                return True
            except Exception as e:
                logger.error(f"Redis set error: {e}")

        # Fallback cache
        self._fallback_cache[key] = value
        if len(self._fallback_cache) > self._max_fallback_size:
            self._fallback_cache.popitem(last=False)  # pop oldest (first item in OrderedDict)
        self._update_metrics()
        return True

    async def delete(self, key: str):
        """Delete key from cache."""
        if self.is_redis_available():
            try:
                self._redis_client.delete(key)
                self._update_metrics()
            except Exception as e:
                logger.error(f"Redis delete error: {e}")
        self._fallback_cache.pop(key, None)
        self._update_metrics()

    async def clear(self):
        """Clear all cache keys."""
        if self.is_redis_available():
            try:
                self._redis_client.flushdb()
                self._update_metrics()
            except Exception as e:
                logger.error(f"Redis flush error: {e}")
        self._fallback_cache.clear()
        self._update_metrics()

    async def invalidate_pattern(self, pattern: str):
        """Invalidates all keys matching a specific glob pattern."""
        if self.is_redis_available():
            try:
                keys = self._redis_client.keys(pattern)
                if keys:
                    self._redis_client.delete(*keys)
                self._update_metrics()
            except Exception as e:
                logger.error(f"Redis invalidate pattern error: {e}")

        # In-memory pattern invalidation
        import fnmatch

        keys_to_del = [k for k in self._fallback_cache.keys() if fnmatch.fnmatch(k, pattern)]
        for k in keys_to_del:
            self._fallback_cache.pop(k, None)
        self._update_metrics()

    def _update_metrics(self):
        try:
            mem_usage = self.get_memory_usage()
            monitoring_service.set_cache_memory(mem_usage)
        except Exception:
            pass

    def get_memory_usage(self) -> int:
        """Returns cache memory usage in bytes."""
        if self.is_redis_available():
            try:
                info = self._redis_client.info("memory")
                return info.get("used_memory", 0)
            except Exception:
                pass
        # Estimate in-memory cache size by serializing values to JSON
        try:
            return sum(len(json.dumps(v)) for v in self._fallback_cache.values())
        except Exception:
            return 0

    def get_stats(self) -> dict:
        """Returns statistics for Cache hits, misses, hit rate, and availability."""
        total = self.hits + self.misses
        hit_rate = (self.hits / total) if total > 0 else 0.0
        return {
            "hits": self.hits,
            "misses": self.misses,
            "hit_rate": round(hit_rate * 100, 2),
            "keys_count": self._get_redis_keys_count() if self.is_redis_available() else len(self._fallback_cache),
            "memory_usage_bytes": self.get_memory_usage(),
            "redis_available": self.is_redis_available(),
        }

    def _get_redis_keys_count(self) -> int:
        try:
            return self._redis_client.dbsize()
        except Exception:
            return 0

    async def invalidate_dataset(self, dataset_id: str, user_id: str):
        """Invalidate all cache entries associated with a dataset when it is modified or cleaned"""
        await self.delete(f"dataset:details:{dataset_id}")
        await self.delete(f"dataset:profile:{dataset_id}")
        await self.delete(f"dataset:quality:{dataset_id}")
        await self.delete(f"dataset:health:{dataset_id}")
        await self.delete(f"insights:{dataset_id}")
        await self.delete(f"dashboard:metadata:{dataset_id}")
        await self.delete(f"dashboard:kpis:{dataset_id}")
        # Also invalidate user dataset lists
        await self.invalidate_pattern(f"dataset:list:{user_id}:*")

    async def invalidate_dashboard(self, dataset_id: str):
        """Invalidate dashboard-related caches"""
        await self.delete(f"dashboard:metadata:{dataset_id}")
        await self.delete(f"dashboard:kpis:{dataset_id}")

    async def invalidate_insights(self, dataset_id: str):
        """Invalidate insights caches"""
        await self.delete(f"insights:{dataset_id}")

    async def invalidate_user(self, user_id: str):
        """Invalidate user profile and permission caches"""
        await self.delete(f"user:profile:{user_id}")
        await self.invalidate_pattern(f"user:permissions:{user_id}:*")


# Singleton instance
cache_service = CacheService()
