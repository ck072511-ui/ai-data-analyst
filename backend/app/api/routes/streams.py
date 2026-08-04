import json
import logging
from typing import Any, Dict, List, Optional
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, WebSocket, WebSocketDisconnect
from pydantic import BaseModel
from sqlalchemy import select, delete

from app.core.database import AsyncSessionLocal
from app.core.security import get_current_user
from app.services.permission_service import require_permission
from app.models.stream import StreamConfig, StreamAlert
from app.services.streaming_service import streaming_service, LocalRESTAdapter, LocalWebSocketAdapter
from app.services.stream_analytics_service import stream_analytics_service

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/streams", tags=["Real-Time Streaming Engine"])

class StreamCreateRequest(BaseModel):
    name: str
    description: Optional[str] = ""
    source_type: str  # csv, json, rest, websocket, fs
    source_config: Dict[str, Any]  # file paths, queue sizes, backpressure strategies, thresholds
    window_type: Optional[str] = "tumbling"  # tumbling, sliding, session
    window_size_sec: Optional[str] = "10"  # single integer, or JSON object for slide/session properties
    aggregations: Optional[List[Dict[str, Any]]] = []  # List of { field, op, label, code }
    schema_definition: Optional[Dict[str, str]] = {}  # col_name -> type

@router.post("", dependencies=[Depends(require_permission("view"))])
async def create_stream(request: StreamCreateRequest, current_user: dict = Depends(get_current_user)):
    """Creates a new offline stream configuration definition."""
    user_id = current_user["id"]
    
    # Simple validation
    if request.source_type not in ["csv", "json", "rest", "websocket", "fs"]:
        raise HTTPException(status_code=400, detail="Invalid source type.")

    async with AsyncSessionLocal() as session:
        stream = StreamConfig(
            name=request.name,
            description=request.description,
            source_type=request.source_type,
            source_config=json.dumps(request.source_config),
            window_type=request.window_type,
            window_size_sec=request.window_size_sec,
            aggregations=json.dumps(request.aggregations),
            schema_definition=json.dumps(request.schema_definition),
            active=False,
            user_id=user_id
        )
        session.add(stream)
        await session.commit()
        await session.refresh(stream)
        
        logger.info(f"User {user_id} created stream configuration {stream.id} ({stream.name})")
        return {
            "id": stream.id,
            "name": stream.name,
            "source_type": stream.source_type,
            "active": stream.active,
            "created_at": stream.created_at.isoformat()
        }

@router.get("", dependencies=[Depends(require_permission("view"))])
async def list_streams(current_user: dict = Depends(get_current_user)):
    """Retrieves all registered stream configurations."""
    user_id = current_user["id"]
    
    async with AsyncSessionLocal() as session:
        records = (await session.execute(
            select(StreamConfig).where(StreamConfig.user_id == user_id)
        )).scalars().all()
        
        return [
            {
                "id": r.id,
                "name": r.name,
                "description": r.description,
                "source_type": r.source_type,
                "source_config": json.loads(r.source_config),
                "window_type": r.window_type,
                "window_size_sec": r.window_size_sec,
                "aggregations": json.loads(r.aggregations) if r.aggregations else [],
                "schema_definition": json.loads(r.schema_definition) if r.schema_definition else {},
                "active": r.active,
                "created_at": r.created_at.isoformat(),
                "updated_at": r.updated_at.isoformat()
            }
            for r in records
        ]

@router.post("/{id}/start", dependencies=[Depends(require_permission("view"))])
async def start_stream(id: str, current_user: dict = Depends(get_current_user)):
    """Activates ingestion threads and window aggregators for a stream."""
    user_id = current_user["id"]
    try:
        await streaming_service.start_stream(id, user_id)
        return {"status": "started", "stream_id": id}
    except Exception as e:
        logger.exception(f"Failed to start stream {id}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/{id}/stop", dependencies=[Depends(require_permission("view"))])
async def stop_stream(id: str, current_user: dict = Depends(get_current_user)):
    """Deactivates ingestion and tears down threads gracefully."""
    user_id = current_user["id"]
    try:
        await streaming_service.stop_stream(id, user_id)
        return {"status": "stopped", "stream_id": id}
    except Exception as e:
        logger.exception(f"Failed to stop stream {id}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/statistics", dependencies=[Depends(require_permission("view"))])
async def get_stream_statistics(current_user: dict = Depends(get_current_user)):
    """Aggregates metrics for active queues, window durations, throughput, and error counters."""
    user_id = current_user["id"]
    
    # Consolidate running statistics
    stats_data = {
        "total_active_streams": len(streaming_service.active_consumers),
        "recent_events_count": len(streaming_service.recent_events_buffer),
        "streams": {}
    }
    
    async with AsyncSessionLocal() as session:
        configs = (await session.execute(
            select(StreamConfig).where(StreamConfig.user_id == user_id)
        )).scalars().all()
        
        for cfg in configs:
            kpis = stream_analytics_service.running_kpis.get(cfg.id, {})
            history = stream_analytics_service.window_history.get(cfg.id, [])
            
            # Count historical alerts
            alerts_count = (await session.execute(
                select(StreamConfig).where(StreamAlert.stream_id == cfg.id)
            )).rowcount or 0
            
            queue_depth = 0
            if cfg.id in streaming_service.queues:
                queue_depth = streaming_service.queues[cfg.id].qsize()

            stats_data["streams"][cfg.id] = {
                "name": cfg.name,
                "active": cfg.active,
                "total_events": kpis.get("total_events", 0),
                "window_count": kpis.get("window_count", 0),
                "queue_depth": queue_depth,
                "recent_windows_stats": history[-5:],
                "running_kpis": kpis
            }
            
    return stats_data

@router.get("/events", dependencies=[Depends(require_permission("view"))])
async def get_recent_events(stream_id: Optional[str] = None, current_user: dict = Depends(get_current_user)):
    """Exposes buffered sliding-window events for active UI dashboard logs."""
    all_events = list(streaming_service.recent_events_buffer)
    if stream_id:
        filtered = [e for e in all_events if e.get("_stream_id") == stream_id]
        return filtered[-50:]
    return all_events[-100:]

@router.post("/{id}/ingest", dependencies=[Depends(require_permission("view"))])
async def ingest_rest_event(id: str, event_data: Dict[str, Any], current_user: dict = Depends(get_current_user)):
    """Receives POST pushes for REST adapters."""
    adapter = streaming_service.get_adapter(id)
    if not adapter or not isinstance(adapter, LocalRESTAdapter):
        raise HTTPException(
            status_code=400, 
            detail="Stream configuration is not active, or is not configured for REST event ingestion."
        )
    try:
        await adapter.ingest_event(event_data)
        return {"status": "success", "message": "Event ingested."}
    except Exception as e:
        logger.error(f"REST ingestion failed for stream {id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.websocket("/{id}/ws")
async def websocket_ingest(websocket: WebSocket, id: str):
    """Establishes full-duplex WebSocket connections for live JSON event streams."""
    await websocket.accept()
    adapter = streaming_service.get_adapter(id)
    if not adapter or not isinstance(adapter, LocalWebSocketAdapter):
        await websocket.close(code=1003, reason="WebSocket stream not running or configured for websocket source.")
        return
    
    logger.info(f"WebSocket client connected to stream {id}")
    try:
        await adapter.handle_websocket(websocket)
    except WebSocketDisconnect:
        logger.info(f"WebSocket client disconnected from stream {id}")
    except Exception as e:
        logger.error(f"WebSocket error on stream {id}: {e}")
        try:
            await websocket.close()
        except Exception:
            pass
