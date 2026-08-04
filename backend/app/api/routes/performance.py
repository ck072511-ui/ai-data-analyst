from fastapi import APIRouter, Depends
from sqlalchemy import select

from app.core.security import get_current_user
from app.services.performance_service import performance_service
from app.services.permission_service import require_permission

router = APIRouter(prefix="/performance", tags=["Performance Telemetry"])


@router.get("/", dependencies=[Depends(require_permission("view"))])
async def get_performance_telemetry(current_user: dict = Depends(get_current_user)):
    """Exposes slow queries log, avg response time, compression ratio and cache stats."""
    return await performance_service.get_stats()


@router.get("/benchmarks", dependencies=[Depends(require_permission("view"))])
async def get_benchmarks_report():
    """Retrieves the latest benchmark report results (JSON)."""
    import json
    import os

    path = os.path.join("load-tests", "reports", "performance_results.json")
    if not os.path.exists(path):
        return {
            "status": "No benchmarks run yet",
            "targets": {
                "api_p95_latency_ms": 200,
                "api_p99_latency_ms": 500,
                "dashboard_gen_time_s": 5.0,
                "dataset_upload_time_s": 10.0,
                "task_completion_time_s": 30.0,
                "cache_hit_percentage": 80.0,
                "error_rate_threshold_pct": 1.0,
            },
            "actuals": {},
            "history": [],
        }
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception as e:
        return {"error": f"Failed to load benchmarks file: {str(e)}"}


@router.get("/audit", dependencies=[Depends(require_permission("user_management"))])
async def get_system_audit_logs(
    page: int = 1,
    page_size: int = 20,
    sort_by: str = "timestamp",
    sort_order: str = "desc",
    search: str = None,
    current_user: dict = Depends(get_current_user),
):
    """Paginated system-wide security audit logs (Admin only)."""
    from app.core.database import AsyncSessionLocal
    from app.models.audit_log import SystemAuditLog
    from app.utils.pagination import paginate

    async with AsyncSessionLocal() as session:
        base_stmt = select(SystemAuditLog)

        items, meta = await paginate(
            session=session,
            model=SystemAuditLog,
            page=page,
            page_size=page_size,
            sort_by=sort_by,
            sort_order=sort_order,
            search=search,
            search_fields=["user_email", "endpoint", "action", "status"],
            base_query=base_stmt,
        )

        serialized_items = [
            {
                "id": log.id,
                "user_id": log.user_id,
                "user_email": log.user_email,
                "user_role": log.user_role,
                "endpoint": log.endpoint,
                "action": log.action,
                "timestamp": log.timestamp.isoformat(),
                "status": log.status,
            }
            for log in items
        ]
        return {"items": serialized_items, "pagination": meta}
