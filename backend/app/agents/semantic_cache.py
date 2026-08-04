from app.core.cache import CacheManager


class SemanticCache:
    """A deterministic cache interface; embeddings can replace the keying later."""

    def __init__(self):
        self.cache = CacheManager()

    async def get(self, question: str):
        return await self.cache.get(f"nl2sql:{question.strip().lower()}")

    async def set(self, question: str, value):
        await self.cache.set(f"nl2sql:{question.strip().lower()}", value)

    def get_hit_rate(self) -> float:
        return 0.0
