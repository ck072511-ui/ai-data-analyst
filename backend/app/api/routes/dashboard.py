from typing import Any, Dict, List

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy import select

from app.core.database import AsyncSessionLocal
from app.core.security import get_current_user
from app.models import Dashboard
from app.services.permission_service import require_permission

router = APIRouter(prefix="/dashboards", tags=["Dashboards"])


class DashboardCreate(BaseModel):
    name: str
    widgets: List[Dict[str, Any]]


@router.post("/", dependencies=[Depends(require_permission("dashboard_write"))])
async def create_dashboard(dashboard: DashboardCreate, current_user: dict = Depends(get_current_user)):
    async with AsyncSessionLocal() as session:
        db_dashboard = Dashboard(user_id=current_user["id"], name=dashboard.name, widgets=dashboard.widgets)
        session.add(db_dashboard)
        await session.commit()
        await session.refresh(db_dashboard)
        return {"id": db_dashboard.id, "name": db_dashboard.name, "widgets": db_dashboard.widgets}


@router.get("/", dependencies=[Depends(require_permission("view"))])
async def get_dashboards(current_user: dict = Depends(get_current_user)):
    async with AsyncSessionLocal() as session:
        result = await session.execute(select(Dashboard).where(Dashboard.user_id == current_user["id"]))
        dashboards = result.scalars().all()
        return [
            {"id": d.id, "name": d.name, "widgets": d.widgets, "created_at": d.created_at.isoformat()}
            for d in dashboards
        ]
