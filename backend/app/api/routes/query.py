from typing import Optional

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy import desc, select

from app.core.database import AsyncSessionLocal
from app.core.security import get_current_user
from app.models import QueryHistory
from app.services.permission_service import require_permission
from app.services.query_service import QueryService

router = APIRouter(prefix="/query", tags=["Query"])


class QueryRequest(BaseModel):
    question: str
    session_id: Optional[str] = None
    dataset_id: Optional[str] = None
    db_connection_id: Optional[str] = None


@router.post("/", dependencies=[Depends(require_permission("analyze"))])
async def ask_question(request: QueryRequest, current_user: dict = Depends(get_current_user)):
    service = QueryService()
    result = await service.process_query(
        user_id=current_user["id"],
        question=request.question,
        session_id=request.session_id,
        dataset_id=request.dataset_id,
        db_connection_id=request.db_connection_id,
    )
    return result


@router.get("/history", dependencies=[Depends(require_permission("view"))])
async def get_query_history(limit: int = 50, current_user: dict = Depends(get_current_user)):
    async with AsyncSessionLocal() as session:
        result = await session.execute(
            select(QueryHistory)
            .where(QueryHistory.user_id == current_user["id"])
            .order_by(desc(QueryHistory.created_at))
            .limit(limit)
        )
        queries = result.scalars().all()
        return [
            {"id": q.id, "question": q.natural_language, "sql": q.generated_sql, "created_at": q.created_at.isoformat()}
            for q in queries
        ]
