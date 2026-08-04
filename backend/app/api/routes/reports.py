from typing import Any, Dict, List, Optional
from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from fastapi.responses import FileResponse
from pydantic import BaseModel

from app.core.security import get_current_user
from app.services.permission_service import require_permission
from app.services.report_service import ReportService
from app.services.monitoring_service import monitoring_service

router = APIRouter(prefix="/reports", tags=["Enterprise Reporting Engine"])
service = ReportService()

class ReportGenerateRequest(BaseModel):
    execution_id: str
    report_type: str  # "executive", "technical", "audit", "data_quality", "ai_insights"
    file_format: str  # "pdf", "docx", "pptx"
    branding: Dict[str, Any] = {} # {company_name, footer, version}


@router.post("/generate", dependencies=[Depends(require_permission("view"))])
async def generate_report_async(
    request: ReportGenerateRequest,
    background_tasks: BackgroundTasks,
    current_user: dict = Depends(get_current_user)
):
    """Triggers an asynchronous background report generation."""
    try:
        res = await service.trigger_generation(
            execution_id=request.execution_id,
            report_type=request.report_type,
            file_format=request.file_format,
            branding=request.branding,
            user_id=current_user["id"]
        )
        
        # Enqueue the actual document generator task
        background_tasks.add_task(service.execute_async_generation, res["report_id"])
        
        return res
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("", dependencies=[Depends(require_permission("view"))])
async def list_user_reports(current_user: dict = Depends(get_current_user)):
    """Retrieves list of compiled report histories."""
    return await service.list_reports(user_id=current_user["id"])


@router.get("/{id}", dependencies=[Depends(require_permission("view"))])
async def get_report_status(id: str, current_user: dict = Depends(get_current_user)):
    """Inspects status details of a specific report query."""
    res = await service.get_report(report_id=id, user_id=current_user["id"])
    if "error" in res:
        raise HTTPException(status_code=404, detail=res["error"])
    return res


@router.get("/{id}/download", dependencies=[Depends(require_permission("view"))])
async def download_report_file(id: str, current_user: dict = Depends(get_current_user)):
    """Serves the generated report file for direct download."""
    res = await service.get_report(report_id=id, user_id=current_user["id"])
    if "error" in res:
        raise HTTPException(status_code=404, detail=res["error"])
    
    file_path = res.get("file_path")
    if not file_path or not os.path.exists(file_path):
        raise HTTPException(status_code=400, detail="Report file not found or generation not finished yet.")

    monitoring_service.record_report_download()
    return FileResponse(
        path=file_path,
        filename=os.path.basename(file_path),
        media_type="application/octet-stream"
    )


@router.delete("/{id}", dependencies=[Depends(require_permission("view"))])
async def delete_report(id: str, current_user: dict = Depends(get_current_user)):
    """Deletes physical files and database entries."""
    res = await service.delete_report(report_id=id, user_id=current_user["id"])
    if "error" in res:
        raise HTTPException(status_code=404, detail=res["error"])
    return res

import os
