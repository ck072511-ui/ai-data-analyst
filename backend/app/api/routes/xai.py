import time
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from app.core.database import AsyncSessionLocal
from app.core.security import get_current_user
from app.services.permission_service import require_permission
from app.models.multi_agent import AgentExecution
from app.services.confidence_service import ConfidenceService
from app.services.xai_service import XAIService
from app.services.monitoring_service import monitoring_service

router = APIRouter(prefix="/xai", tags=["Explainable AI Engine"])


@router.get("/explain/{execution_id}", dependencies=[Depends(require_permission("view"))])
async def get_agent_explanation(execution_id: str, current_user: dict = Depends(get_current_user)):
    """Generates programmatically structured explainability details for SQL, RAG, and Agents."""
    start_time = time.time()
    async with AsyncSessionLocal() as session:
        rec = (await session.execute(
            select(AgentExecution).where(AgentExecution.id == execution_id)
        )).scalar_one_or_none()

    if not rec:
        raise HTTPException(status_code=404, detail="Execution audit log not found.")

    sm = rec.shared_memory or {}
    timeline = rec.timeline or []
    citations = sm.get("RAGAgent", {}).get("citations", [])

    # Explanations compiles
    sql_explanation = XAIService.parse_sql_explanation(sm.get("SQLAgent", {}).get("sql", ""))
    rag_explanation = XAIService.parse_rag_explanation(citations)
    agent_explanation = XAIService.parse_agent_explanation(timeline, sm.get("CriticAgent", {}))
    business_explanation = XAIService.parse_business_explanation(sm.get("InsightAgent", {}))

    # Compute confidence
    score, level = ConfidenceService.calculate_confidence(sm, timeline)

    latency = time.time() - start_time
    monitoring_service.record_xai_metrics(
        latency_sec=latency,
        confidence=score,
        missing_citations=len(citations) == 0
    )

    return {
        "execution_id": execution_id,
        "confidence_score": score,
        "confidence_level": level,
        "sql_explanation": sql_explanation,
        "rag_explanation": rag_explanation,
        "agent_explanation": agent_explanation,
        "business_explanation": business_explanation,
        "final_synthesized_answer": rec.final_answer
    }


@router.get("/confidence/{execution_id}", dependencies=[Depends(require_permission("view"))])
async def get_confidence_breakdown(execution_id: str, current_user: dict = Depends(get_current_user)):
    """Computes confidence parameters and breakdown ratings."""
    async with AsyncSessionLocal() as session:
        rec = (await session.execute(
            select(AgentExecution).where(AgentExecution.id == execution_id)
        )).scalar_one_or_none()

    if not rec:
        raise HTTPException(status_code=404, detail="Execution audit log not found.")

    sm = rec.shared_memory or {}
    timeline = rec.timeline or []
    
    score, level = ConfidenceService.calculate_confidence(sm, timeline)
    return {
        "confidence_score": score,
        "confidence_level": level,
        "sql_valid": bool(sm.get("SQLAgent", {}).get("sql") and not sm.get("SQLAgent", {}).get("error")),
        "schema_valid": bool(sm.get("SchemaAgent", {}).get("schema_context")),
        "citations_count": len(sm.get("RAGAgent", {}).get("citations", [])),
        "timeline_steps_count": len(timeline)
    }


@router.get("/evidence/{execution_id}", dependencies=[Depends(require_permission("view"))])
async def get_cited_evidence(execution_id: str, current_user: dict = Depends(get_current_user)):
    """Retrieves document citation passages directly."""
    async with AsyncSessionLocal() as session:
        rec = (await session.execute(
            select(AgentExecution).where(AgentExecution.id == execution_id)
        )).scalar_one_or_none()

    if not rec:
        raise HTTPException(status_code=404, detail="Execution audit log not found.")

    sm = rec.shared_memory or {}
    return {
        "citations": sm.get("RAGAgent", {}).get("citations", []),
        "glossary_context": sm.get("RAGAgent", {}).get("dictionary_context", "")
    }
