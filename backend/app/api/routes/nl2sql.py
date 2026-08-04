import json
import logging
from typing import Optional, Dict, Any, List
from fastapi import APIRouter, Depends, HTTPException, Body
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

from app.core.security import get_current_user
from app.services.permission_service import require_permission
from app.services.nl2sql_service import NL2SQLService

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/nl2sql", tags=["Enterprise NL2SQL Engine"])
service = NL2SQLService()

class QueryRequest(BaseModel):
    db_connection_id: str
    question: str
    conversation_id: Optional[str] = None
    stream: Optional[bool] = False

class ExplainRequest(BaseModel):
    db_connection_id: str
    sql: str

class ValidateRequest(BaseModel):
    db_connection_id: str
    sql: str


@router.post("/query", dependencies=[Depends(require_permission("analyze"))])
async def generate_query(
    request: QueryRequest,
    current_user: dict = Depends(get_current_user)
):
    """Generate SQL query, validate safety and syntax, execute against the database, and explain trends."""
    if request.stream:
        async def event_generator():
            try:
                async for chunk in service.stream_query(
                    user_id=current_user["id"],
                    db_connection_id=request.db_connection_id,
                    question=request.question,
                    conversation_id=request.conversation_id
                ):
                    yield f"data: {chunk}\n\n"
                yield "data: [DONE]\n\n"
            except Exception as e:
                logger.error(f"NL2SQL Streaming failed: {e}")
                yield f"data: {json.dumps({'type': 'error', 'message': str(e)})}\n\n"
                
        return StreamingResponse(event_generator(), media_type="text/event-stream")
    else:
        return await service.process_query(
            user_id=current_user["id"],
            db_connection_id=request.db_connection_id,
            question=request.question,
            conversation_id=request.conversation_id
        )


@router.post("/explain", dependencies=[Depends(require_permission("view"))])
async def explain_query(
    request: ExplainRequest,
    current_user: dict = Depends(get_current_user)
):
    """Provide a natural language explanation for a raw SQL query."""
    return await service.explain_sql(
        connection_id=request.db_connection_id,
        sql=request.sql
    )


@router.post("/validate", dependencies=[Depends(require_permission("view"))])
async def validate_query(
    request: ValidateRequest,
    current_user: dict = Depends(get_current_user)
):
    """Verify syntax plan, table/column existence, safety limits, and estimate execution cost."""
    return await service.validate_sql(
        connection_id=request.db_connection_id,
        sql=request.sql
    )


@router.get("/history", dependencies=[Depends(require_permission("view"))])
async def get_nl2sql_history(
    conversation_id: Optional[str] = None,
    current_user: dict = Depends(get_current_user)
):
    """List active user conversations or retrieve message history logs of a specific thread."""
    if conversation_id:
        return await service.get_conversation_history(conversation_id, current_user["id"])
    else:
        return await service.list_conversations(current_user["id"])


@router.post("/conversations/{conversation_id}/pin", dependencies=[Depends(require_permission("view"))])
async def toggle_pin_conversation(
    conversation_id: str,
    current_user: dict = Depends(get_current_user)
):
    """Pin or unpin a conversation thread to the top of the history feed."""
    return await service.toggle_pin_conversation(conversation_id, current_user["id"])


@router.delete("/conversations/{conversation_id}", dependencies=[Depends(require_permission("view"))])
async def delete_conversation(
    conversation_id: str,
    current_user: dict = Depends(get_current_user)
):
    """Permanently delete a conversation thread and its associated query records."""
    return await service.delete_conversation(conversation_id, current_user["id"])
