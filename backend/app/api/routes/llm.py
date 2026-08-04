import json
import logging
import time
from typing import Dict, Any
from fastapi import APIRouter, Depends, HTTPException, Body
from fastapi.responses import StreamingResponse

from app.core.security import get_current_user
from app.services.permission_service import require_permission
from app.services.model_manager import model_manager

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/llm", tags=["LLM Framework Orchestrator"])


@router.get("/models", dependencies=[Depends(require_permission("view"))])
async def get_models(current_user: dict = Depends(get_current_user)):
    """List available LLM models from the active provider."""
    models = await model_manager.list_models()
    active_model = await model_manager.get_active_model()
    return {"models": models, "active_model": active_model}


@router.get("/status", dependencies=[Depends(require_permission("view"))])
async def get_status(current_user: dict = Depends(get_current_user)):
    """Retrieve telemetry metrics and health check status of the active LLM provider."""
    is_healthy = await model_manager.health_check()
    stats = model_manager.get_monitoring_stats()
    
    # Check if Ollama is active
    active_provider = await model_manager.get_active_provider()
    ollama_active = (active_provider == "ollama")
        
    return {
        "status": "healthy" if is_healthy else "unhealthy",
        "provider": active_provider,
        "ollama_connected": is_healthy if ollama_active else False,
        **stats
    }


@router.post("/select", dependencies=[Depends(require_permission("clean"))])
async def select_model(
    payload: Dict[str, str] = Body(...),
    current_user: dict = Depends(get_current_user)
):
    """Switch active LLM model and provider dynamically."""
    model_name = payload.get("model")
    provider_name = payload.get("provider")  # Optional
    if not model_name:
        raise HTTPException(status_code=400, detail="Missing parameter 'model'")
        
    success = await model_manager.select_model(model_name, provider_name)
    if not success:
        raise HTTPException(status_code=400, detail=f"Failed to switch model to {model_name}.")
    return {"message": f"Successfully switched to model {model_name}", "model": model_name}


@router.post("/test", dependencies=[Depends(require_permission("view"))])
async def test_model(
    payload: Dict[str, Any] = Body(...),
    current_user: dict = Depends(get_current_user)
):
    """Test model completions with a user prompt. Supports streaming response (Server-Sent Events)."""
    prompt = payload.get("prompt")
    stream = payload.get("stream", False)
    
    if not prompt:
        raise HTTPException(status_code=400, detail="Missing parameter 'prompt'")
        
    if stream:
        async def event_generator():
            try:
                async for chunk in model_manager.stream_generate(prompt=prompt):
                    yield f"data: {json.dumps({'chunk': chunk})}\n\n"
                yield "data: [DONE]\n\n"
            except Exception as e:
                logger.error(f"Inference streaming failed: {e}")
                yield f"data: {json.dumps({'error': str(e)})}\n\n"
                
        return StreamingResponse(event_generator(), media_type="text/event-stream")
    else:
        start_time = time.time()
        try:
            response = await model_manager.generate(prompt=prompt)
            latency_ms = int((time.time() - start_time) * 1000)
            return {
                "response": response,
                "latency_ms": latency_ms,
                "model": await model_manager.get_active_model(),
                "provider": await model_manager.get_active_provider()
            }
        except Exception as e:
            logger.error(f"Inference execution failed: {e}")
            raise HTTPException(status_code=500, detail=f"Inference failed: {str(e)}")
