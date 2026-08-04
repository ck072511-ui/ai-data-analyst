from fastapi import APIRouter, Depends
from fastapi.responses import FileResponse

from app.core.security import get_current_user
from app.services.export_service import ExportService

router = APIRouter(prefix="/export", tags=["Export"])


@router.post("/pdf")
async def export_pdf(data: dict, current_user: dict = Depends(get_current_user)):
    service = ExportService()
    file_path = await service.export_to_pdf(data)
    return FileResponse(file_path, filename="report.pdf")


@router.post("/excel")
async def export_excel(data: dict, current_user: dict = Depends(get_current_user)):
    service = ExportService()
    file_path = await service.export_to_excel(data)
    return FileResponse(file_path, filename="data.xlsx")
