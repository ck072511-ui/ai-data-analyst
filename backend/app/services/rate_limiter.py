from collections import defaultdict
from datetime import date

from app.core.config import settings


class RateLimiter:
    def __init__(self):
        self.counts = defaultdict(int)

    async def check(self, user_id: str) -> bool:
        key = (user_id, date.today().isoformat())
        self.counts[key] += 1
        return self.counts[key] <= settings.RATE_LIMIT_PER_DAY
