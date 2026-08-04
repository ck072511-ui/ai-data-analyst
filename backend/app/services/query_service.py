from datetime import datetime
from typing import Any, Dict, Optional

from sqlalchemy import desc, select

from app.agents.nl2sql_agent import NL2SQLAgent
from app.core.cache import CacheManager
from app.core.database import AsyncSessionLocal
from app.core.exceptions import RateLimitError
from app.core.monitoring import MetricsCollector
from app.models import QueryHistory
from app.services.rate_limiter import RateLimiter


class QueryService:
    def __init__(self):
        self.agent = NL2SQLAgent()
        self.cache = CacheManager()
        self.rate_limiter = RateLimiter()
        self.metrics = MetricsCollector()

    async def process_query(
        self,
        user_id: str,
        question: str,
        session_id: Optional[str] = None,
        dataset_id: Optional[str] = None,
        db_connection_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        if not await self.rate_limiter.check(user_id):
            raise RateLimitError("Daily query limit exceeded")

        # Partition caching specifically by dataset_id or db_connection_id context
        context_id = db_connection_id or dataset_id or "default"
        cache_key = f"query:{user_id}:{context_id}:{question.strip().lower()}"
        cached = await self.cache.get(cache_key)
        if cached:
            self.metrics.record_cache_hit()
            return cached

        started = datetime.utcnow()
        result = await self.agent.process(question, user_id, dataset_id=dataset_id, db_connection_id=db_connection_id)
        elapsed_ms = int((datetime.utcnow() - started).total_seconds() * 1000)

        async with AsyncSessionLocal() as session:
            session.add(
                QueryHistory(
                    user_id=user_id,
                    session_id=session_id,
                    natural_language=question,
                    generated_sql=result.get("sql"),
                    result_data=result.get("data"),
                    chart_type=result.get("chart_type"),
                    execution_time=elapsed_ms,
                    row_count=len(result.get("data", [])),
                    success=int(result.get("success", False)),
                    error_message=result.get("error"),
                )
            )
            await session.commit()

        await self.cache.set(cache_key, result)
        self.metrics.record_query(duration=elapsed_ms, success=result.get("success", False))
        return result

    async def get_query_history(self, user_id: str, limit: int = 50):
        async with AsyncSessionLocal() as session:
            records = (
                (
                    await session.execute(
                        select(QueryHistory)
                        .where(QueryHistory.user_id == user_id)
                        .order_by(desc(QueryHistory.created_at))
                        .limit(limit)
                    )
                )
                .scalars()
                .all()
            )
        return records
