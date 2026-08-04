import logging
from typing import Dict, Any, List, Optional
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel

from app.core.security import get_current_user
from app.services.permission_service import require_permission
from app.services.plugin_manager import plugin_manager

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/plugins", tags=["Plugin Extension SDK"])


class PluginRequest(BaseModel):
    plugin_id: str


@router.get("", dependencies=[Depends(require_permission("view"))])
async def list_plugins(current_user: dict = Depends(get_current_user)):
    """Lists all installed plugins and available marketplace blueprints."""
    try:
        installed = plugin_manager.registry.list_installed()
        available = plugin_manager.registry.list_available()
        
        # Merge status flags
        merged = []
        for pid, avail in available.items():
            entry = {
                "id": pid,
                "name": avail.get("name"),
                "description": avail.get("description"),
                "version": avail.get("version"),
                "author": avail.get("author"),
                "capability": avail.get("capability"),
                "config_schema": avail.get("config_schema"),
                "dependencies": avail.get("dependencies", []),
                "installed": pid in installed,
                "enabled": installed[pid].get("enabled", False) if pid in installed else False,
                "health_status": installed[pid].get("health_status", "unknown") if pid in installed else "unknown",
                "health_message": installed[pid].get("health_message", "") if pid in installed else "",
                "last_health_check": installed[pid].get("last_health_check", "") if pid in installed else "",
                "install_time": installed[pid].get("install_time", "") if pid in installed else "",
                "version_history": installed[pid].get("version_history", []) if pid in installed else []
            }
            merged.append(entry)
            
        return merged
    except Exception as e:
        logger.exception("Failed to retrieve plugins list")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/install", dependencies=[Depends(require_permission("user_management"))])
async def install_plugin(request: PluginRequest, current_user: dict = Depends(get_current_user)):
    """Installs a plugin from the marketplace catalog (Admin only)."""
    try:
        plugin_manager.install_plugin(request.plugin_id)
        return {"status": "success", "message": f"Plugin '{request.plugin_id}' installed and validated."}
    except FileNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.exception(f"Failed to install plugin {request.plugin_id}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/uninstall", dependencies=[Depends(require_permission("user_management"))])
async def uninstall_plugin(request: PluginRequest, current_user: dict = Depends(get_current_user)):
    """Uninstalls a plugin completely from storage (Admin only)."""
    try:
        plugin_manager.uninstall_plugin(request.plugin_id)
        return {"status": "success", "message": f"Plugin '{request.plugin_id}' uninstalled successfully."}
    except Exception as e:
        logger.exception(f"Failed to uninstall plugin {request.plugin_id}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/enable", dependencies=[Depends(require_permission("user_management"))])
async def enable_plugin(request: PluginRequest, current_user: dict = Depends(get_current_user)):
    """Enables an installed plugin (Admin only)."""
    try:
        plugin_manager.enable_plugin(request.plugin_id)
        return {"status": "success", "message": f"Plugin '{request.plugin_id}' is now enabled."}
    except Exception as e:
        logger.exception(f"Failed to enable plugin {request.plugin_id}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/disable", dependencies=[Depends(require_permission("user_management"))])
async def disable_plugin(request: PluginRequest, current_user: dict = Depends(get_current_user)):
    """Disables a plugin from loading and executing (Admin only)."""
    try:
        plugin_manager.disable_plugin(request.plugin_id)
        return {"status": "success", "message": f"Plugin '{request.plugin_id}' disabled successfully."}
    except Exception as e:
        logger.exception(f"Failed to disable plugin {request.plugin_id}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/health", dependencies=[Depends(require_permission("view"))])
async def get_plugins_health(current_user: dict = Depends(get_current_user)):
    """Triggers and returns a health diagnostic report of all loaded plugins."""
    try:
        reports = await plugin_manager.run_health_checks()
        return {
            "overall_status": "healthy" if not any(r["status"] == "unhealthy" for r in reports) else "unhealthy",
            "reports": reports
        }
    except Exception as e:
        logger.exception("Failed to run plugin health checks")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/upgrade", dependencies=[Depends(require_permission("user_management"))])
async def upgrade_plugin(request: PluginRequest, current_user: dict = Depends(get_current_user)):
    """Upgrades a plugin version from the marketplace catalog (Admin only)."""
    try:
        plugin_manager.upgrade_plugin(request.plugin_id)
        return {"status": "success", "message": f"Plugin '{request.plugin_id}' upgraded to latest version."}
    except FileNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.exception(f"Failed to upgrade plugin {request.plugin_id}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/rollback", dependencies=[Depends(require_permission("user_management"))])
async def rollback_plugin(request: PluginRequest, current_user: dict = Depends(get_current_user)):
    """Rolls back the plugin version to the previous template configuration (Admin only)."""
    try:
        plugin_manager.rollback_plugin(request.plugin_id)
        return {"status": "success", "message": f"Plugin '{request.plugin_id}' version rolled back."}
    except FileNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.exception(f"Failed to roll back plugin {request.plugin_id}")
        raise HTTPException(status_code=500, detail=str(e))
