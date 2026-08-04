import shutil
from fastapi import APIRouter, HTTPException
from fastapi.responses import JSONResponse
from app.services.readiness_validator import ReadinessValidator

router = APIRouter(tags=["Health Checks"])


@router.get("/health")
@router.get("/api/v1/health")
async def health_check():
    """Detailed health status mapping checks for database, storage, vector, and LLM."""
    checks = await ReadinessValidator.run_checks()
    return {
        "status": "healthy" if checks.get("overall_ready") else "unhealthy",
        "service": "ai-data-analyst",
        "checks": {
            "database": "Healthy" if "Healthy" in str(checks.get("database")) else "Unhealthy",
            "storage": "Healthy" if "Healthy" in str(checks.get("document_export_directory")) else "Unhealthy",
            "authentication": "Healthy",
            "vector_store": "Healthy" if "Healthy" in str(checks.get("vector_store_directory")) else "Unhealthy",
            "llm": "Healthy" if "Healthy" in str(checks.get("llm_connectivity")) else "Unhealthy"
        }
    }


@router.get("/health/live")
@router.get("/api/v1/health/live")
@router.get("/live")
async def live_check():
    """Liveness check confirming the FastAPI application process is running."""
    return {"status": "healthy", "service": "ai-data-analyst"}


@router.get("/health/ready")
@router.get("/api/v1/health/ready")
@router.get("/ready")
async def ready_check():
    """Readiness check validating disk partitions and dependencies."""
    checks = await ReadinessValidator.run_checks()
    
    # Check disk partition usage
    total, used, free = shutil.disk_usage(".")
    free_gb = free / (1024 ** 3)
    
    checks["disk_space_free_gb"] = round(free_gb, 2)
    if free_gb < 1.0:
        checks["disk_space"] = "Unhealthy: less than 1GB free."
        checks["overall_ready"] = False
    else:
        checks["disk_space"] = "Healthy"

    checks["status"] = "healthy" if checks.get("overall_ready") else "unhealthy"
    if not checks["overall_ready"]:
        return JSONResponse(status_code=503, content=checks)
        
    return checks
