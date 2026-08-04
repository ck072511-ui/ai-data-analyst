import logging
from typing import Any, Dict

from fastapi import APIRouter
from pydantic import BaseModel

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/analytics", tags=["Analytics"])


class AnalyticsEvent(BaseModel):
    event: str
    properties: Dict[str, Any] = {}
    timestamp: str


@router.post("/track", status_code=202)
async def track_event(payload: AnalyticsEvent):
    """Accept anonymous browser telemetry without affecting the user workflow."""
    logger.info("Analytics event: %s", payload.event)
    return {"accepted": True}
