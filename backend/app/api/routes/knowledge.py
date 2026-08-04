import json
import logging
from typing import Any, Dict, List, Optional
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select, or_, delete
from app.core.database import AsyncSessionLocal
from app.core.security import get_current_user
from app.services.permission_service import require_permission
from app.models.knowledge import KnowledgeEntity, KnowledgeRelationship
from app.services.knowledge_graph_service import knowledge_graph_service

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/knowledge", tags=["Enterprise Knowledge Graph"])

@router.post("/build", dependencies=[Depends(require_permission("view"))])
async def build_knowledge_graph(current_user: dict = Depends(get_current_user)):
    """Triggers entity and relationship discovery across flat files, database connections, and reports."""
    user_id = current_user["id"]
    try:
        res = await knowledge_graph_service.build_graph(user_id)
        return res
    except Exception as e:
        logger.exception("Failed to build Knowledge Graph")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/rebuild", dependencies=[Depends(require_permission("view"))])
async def rebuild_knowledge_graph(current_user: dict = Depends(get_current_user)):
    """Drops existing graph entities and relationships, then rebuilds."""
    user_id = current_user["id"]
    try:
        # Purge existing graph first
        async with AsyncSessionLocal() as session:
            await session.execute(delete(KnowledgeRelationship).where(KnowledgeRelationship.user_id == user_id))
            await session.execute(delete(KnowledgeEntity).where(KnowledgeEntity.user_id == user_id))
            await session.commit()
            
        res = await knowledge_graph_service.build_graph(user_id)
        return res
    except Exception as e:
        logger.exception("Failed to rebuild Knowledge Graph")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/entities", dependencies=[Depends(require_permission("view"))])
async def list_entities(
    search: Optional[str] = None,
    entity_type: Optional[str] = None,
    current_user: dict = Depends(get_current_user)
):
    """Retrieves entities list, searchable by type or name matching."""
    user_id = current_user["id"]
    async with AsyncSessionLocal() as session:
        stmt = select(KnowledgeEntity).where(KnowledgeEntity.user_id == user_id)
        if entity_type:
            stmt = stmt.where(KnowledgeEntity.entity_type == entity_type)
        if search:
            stmt = stmt.where(
                or_(
                    KnowledgeEntity.name.like(f"%{search}%"),
                    KnowledgeEntity.properties.like(f"%{search}%")
                )
            )
        
        records = (await session.execute(stmt)).scalars().all()
        return [
            {
                "id": r.id,
                "name": r.name,
                "entity_type": r.entity_type,
                "properties": json.loads(r.properties) if r.properties else {},
                "source_id": r.source_id,
                "created_at": r.created_at.isoformat()
            }
            for r in records
        ]

@router.get("/relationships", dependencies=[Depends(require_permission("view"))])
async def list_relationships(current_user: dict = Depends(get_current_user)):
    """Queries relationships connectivity graph list."""
    user_id = current_user["id"]
    async with AsyncSessionLocal() as session:
        records = (await session.execute(
            select(KnowledgeRelationship).where(KnowledgeRelationship.user_id == user_id)
        )).scalars().all()
        
        results = []
        for r in records:
            source = (await session.execute(
                select(KnowledgeEntity).where(KnowledgeEntity.id == r.source_id)
            )).scalar_one_or_none()
            target = (await session.execute(
                select(KnowledgeEntity).where(KnowledgeEntity.id == r.target_id)
            )).scalar_one_or_none()
            
            if source and target:
                results.append({
                    "id": r.id,
                    "source_id": r.source_id,
                    "source_name": source.name,
                    "source_type": source.entity_type,
                    "target_id": r.target_id,
                    "target_name": target.name,
                    "target_type": target.entity_type,
                    "relationship_type": r.relationship_type,
                    "confidence": r.confidence,
                    "properties": json.loads(r.properties) if r.properties else {}
                })
        return results

@router.get("/search", dependencies=[Depends(require_permission("view"))])
async def semantic_search(query: str, current_user: dict = Depends(get_current_user)):
    """Resolves semantic mapping synonyms to scan matching entities."""
    user_id = current_user["id"]
    from app.services.semantic_layer_service import semantic_layer_service
    
    words = query.lower().split()
    resolved = []
    for w in words:
        w_clean = "".join(c for c in w if c.isalnum())
        if w_clean:
            syns = semantic_layer_service.resolve_synonyms(w_clean)
            resolved.extend(syns)
            resolved.append(w_clean)
            
    async with AsyncSessionLocal() as session:
        stmt = select(KnowledgeEntity).where(KnowledgeEntity.user_id == user_id)
        if resolved:
            # Match any synonyms or name matches
            stmt = stmt.where(KnowledgeEntity.name.in_(resolved))
            
        records = (await session.execute(stmt)).scalars().all()
        return [
            {
                "id": r.id,
                "name": r.name,
                "entity_type": r.entity_type,
                "properties": json.loads(r.properties) if r.properties else {},
                "source_id": r.source_id
            }
            for r in records
        ]

@router.get("/lineage/{entity_id}", dependencies=[Depends(require_permission("view"))])
async def get_entity_lineage(entity_id: str, current_user: dict = Depends(get_current_user)):
    """Retrieves upstream lineage path maps for a column/table."""
    user_id = current_user["id"]
    return await knowledge_graph_service.get_lineage(entity_id, user_id)

@router.get("/impact/{entity_id}", dependencies=[Depends(require_permission("view"))])
async def get_entity_impact(entity_id: str, current_user: dict = Depends(get_current_user)):
    """Traces downstream targets that depend on a table or dataset column."""
    user_id = current_user["id"]
    return await knowledge_graph_service.get_impact(entity_id, user_id)
