from app.services.monitoring_service import monitoring_service


class MetricsCollector:
    """Lightweight in-process metrics delegated to the main monitoring service."""

    def __init__(self):
        self.queries = 0
        self.errors = 0
        self.cache_hits = 0

    def record_query(self, duration: float = 0.0, success: bool = True, **_kwargs):
        self.queries += 1
        monitoring_service.record_ai_query(duration / 1000.0)

    def record_error(self):
        self.errors += 1

    def record_cache_hit(self):
        self.cache_hits += 1
