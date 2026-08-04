import json
import logging
from typing import Any, Dict, List, Optional
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import select, desc

from app.core.database import AsyncSessionLocal
from app.core.security import get_current_user
from app.services.permission_service import require_permission
from app.models.copilot import CopilotConversation, CopilotMessage
from app.services.copilot_service import copilot_service

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/copilot", tags=["Enterprise AI Copilot"])

class ChatRequest(BaseModel):
    message: str
    conversation_id: Optional[str] = None
    dataset_id: Optional[str] = None
    db_connection_id: Optional[str] = None

class AnalyzeRequest(BaseModel):
    query: str
    dataset_id: Optional[str] = None
    db_connection_id: Optional[str] = None

class WorkflowRequest(BaseModel):
    conversation_id: str
    name: str
    description: Optional[str] = ""

@router.post("/chat", dependencies=[Depends(require_permission("view"))])
async def post_copilot_chat(request: ChatRequest, current_user: dict = Depends(get_current_user)):
    user_id = current_user["id"]
    conv_id = request.conversation_id
    
    async with AsyncSessionLocal() as session:
        # Resolve or create conversation
        if not conv_id:
            conv = CopilotConversation(
                user_id=user_id,
                title=request.message[:50] + "..." if len(request.message) > 50 else request.message
            )
            session.add(conv)
            await session.commit()
            await session.refresh(conv)
            conv_id = conv.id
        else:
            conv = (await session.execute(
                select(CopilotConversation).where(CopilotConversation.id == conv_id, CopilotConversation.user_id == user_id)
            )).scalar_one_or_none()
            if not conv:
                raise HTTPException(status_code=404, detail="Conversation thread not found.")
        
        # Save user message
        user_msg = CopilotMessage(
            conversation_id=conv_id,
            role="user",
            content=request.message
        )
        session.add(user_msg)
        await session.commit()

    # Detect intents
    intents = await copilot_service.detect_intent(request.message)
    intent_names = ", ".join([i["intent"] for i in intents])
    avg_conf = sum(i["confidence"] for i in intents) / len(intents) if intents else 0.8
    
    # Run sequential Action Orchestrator
    import time
    start_time = time.time()
    orchestration_res = await copilot_service.orchestrate_action(
        intents=intents,
        question=request.message,
        dataset_id=request.dataset_id,
        db_connection_id=request.db_connection_id,
        user_id=user_id
    )
    latency = time.time() - start_time
    
    # Record telemetry
    from app.services.performance_service import copilot_telemetry
    try:
        copilot_telemetry.record_request(
            latency=latency,
            intents=[i["intent"] for i in intents],
            tools=orchestration_res["tool_transparency"]["execution_order"],
            success=all(s["status"] == "success" for s in orchestration_res["tool_transparency"]["timeline"])
        )
    except Exception as e:
        logger.warning(f"Telemetry logging failed: {e}")
    
    # Save assistant message
    async with AsyncSessionLocal() as session:
        assistant_msg = CopilotMessage(
            conversation_id=conv_id,
            role="assistant",
            content=orchestration_res["answer"],
            intent=intent_names,
            intent_confidence=avg_conf,
            orchestration_plan=json.dumps(orchestration_res["tool_transparency"]),
            response_metadata=json.dumps({
                "confidence_score": orchestration_res["confidence_score"],
                "processing_time_seconds": orchestration_res["processing_time_seconds"]
            })
        )
        session.add(assistant_msg)
        await session.commit()
        
    return {
        "conversation_id": conv_id,
        "answer": orchestration_res["answer"],
        "confidence_score": orchestration_res["confidence_score"],
        "processing_time_seconds": orchestration_res["processing_time_seconds"],
        "tool_transparency": orchestration_res["tool_transparency"]
    }

@router.post("/analyze", dependencies=[Depends(require_permission("view"))])
async def post_copilot_analyze(request: AnalyzeRequest, current_user: dict = Depends(get_current_user)):
    user_id = current_user["id"]
    intents = await copilot_service.detect_intent(request.query)
    
    import time
    start_time = time.time()
    orchestration_res = await copilot_service.orchestrate_action(
        intents=intents,
        question=request.query,
        dataset_id=request.dataset_id,
        db_connection_id=request.db_connection_id,
        user_id=user_id
    )
    latency = time.time() - start_time
    
    # Record telemetry
    from app.services.performance_service import copilot_telemetry
    try:
        copilot_telemetry.record_request(
            latency=latency,
            intents=[i["intent"] for i in intents],
            tools=orchestration_res["tool_transparency"]["execution_order"],
            success=all(s["status"] == "success" for s in orchestration_res["tool_transparency"]["timeline"])
        )
    except Exception as e:
        logger.warning(f"Telemetry logging failed: {e}")
        
    return orchestration_res


@router.post("/workflow", dependencies=[Depends(require_permission("view"))])
async def post_copilot_workflow(request: WorkflowRequest, current_user: dict = Depends(get_current_user)):
    user_id = current_user["id"]
    try:
        wf_res = await copilot_service.generate_workflow_from_history(
            conversation_id=request.conversation_id,
            name=request.name,
            description=request.description,
            user_id=user_id
        )
        return wf_res
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/history", dependencies=[Depends(require_permission("view"))])
async def get_copilot_history(current_user: dict = Depends(get_current_user)):
    user_id = current_user["id"]
    async with AsyncSessionLocal() as session:
        records = (await session.execute(
            select(CopilotConversation)
            .where(CopilotConversation.user_id == user_id)
            .order_by(desc(CopilotConversation.created_at))
        )).scalars().all()
        
        results = []
        for r in records:
            # Query messages count
            msg_count = (await session.execute(
                select(CopilotMessage).where(CopilotMessage.conversation_id == r.id).order_by(CopilotMessage.created_at)
            )).scalars().all()
            
            # Serialize conversation
            results.append({
                "id": r.id,
                "title": r.title,
                "summary": r.summary,
                "preferences": r.preferences,
                "created_at": r.created_at.isoformat(),
                "updated_at": r.updated_at.isoformat(),
                "message_count": len(msg_count),
                "messages": [
                    {
                        "id": m.id,
                        "role": m.role,
                        "content": m.content,
                        "intent": m.intent,
                        "intent_confidence": m.intent_confidence,
                        "orchestration_plan": json.loads(m.orchestration_plan) if m.orchestration_plan else None,
                        "response_metadata": json.loads(m.response_metadata) if m.response_metadata else None,
                        "created_at": m.created_at.isoformat()
                    }
                    for m in msg_count
                ]
            })
        return results
