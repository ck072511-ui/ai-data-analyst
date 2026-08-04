import os
import json
import logging
from typing import Dict, Any, List, Optional
from datetime import datetime

logger = logging.getLogger(__name__)

DEFAULT_MARKETPLACE = {
    "csv_import_plus": {
        "id": "csv_import_plus",
        "name": "CSV Import Plus",
        "version": "1.0.0",
        "description": "Enhanced CSV parsing data source with customizable delimiters, character encoding selectors, and header sanitizers.",
        "author": "Platform Team",
        "capability": "data_source",
        "compatible_versions": ["1.0.0"],
        "dependencies": [],
        "config_schema": {
            "type": "object",
            "properties": {
                "delimiter": {"type": "string", "default": ",", "description": "Character separating fields (e.g. , ; tab)"},
                "encoding": {"type": "string", "default": "utf-8", "description": "Character encoding (e.g. utf-8, latin-1)"},
                "skip_rows": {"type": "integer", "default": 0, "description": "Number of header rows to skip"}
            },
            "required": []
        }
    },
    "advanced_charts": {
        "id": "advanced_charts",
        "name": "Advanced Charts",
        "version": "1.0.0",
        "description": "Premium charting extension compiling visual specs for Radar, Polar Area, and Bubble layouts.",
        "author": "Visualization Labs",
        "capability": "visualization",
        "compatible_versions": ["1.0.0"],
        "dependencies": [],
        "config_schema": {
            "type": "object",
            "properties": {
                "chart_theme": {"type": "string", "default": "dark", "enum": ["light", "dark", "glass"]},
                "show_grid": {"type": "boolean", "default": True},
                "animation_duration_ms": {"type": "integer", "default": 800}
            },
            "required": []
        }
    },
    "kpi_library": {
        "id": "kpi_library",
        "name": "KPI Library",
        "version": "1.0.0",
        "description": "Calculates business core KPIs (e.g. Gross Margin Ratio, Customer Acquisition Cost, and Year-over-Year Growth).",
        "author": "Finance Analytics Group",
        "capability": "analytics",
        "compatible_versions": ["1.0.0"],
        "dependencies": [],
        "config_schema": {
            "type": "object",
            "properties": {
                "revenue_col": {"type": "string", "default": "revenue", "description": "Name of the revenue column"},
                "cost_col": {"type": "string", "default": "cost", "description": "Name of the cost of goods sold column"},
                "period_col": {"type": "string", "default": "date", "description": "Time dimension column"}
            },
            "required": ["revenue_col", "cost_col"]
        }
    },
    "custom_report": {
        "id": "custom_report",
        "name": "Custom Report Template",
        "version": "1.0.0",
        "description": "Renders reports with customized headers, enterprise logos, dynamic table styles, and signature panels.",
        "author": "Document Engineering",
        "capability": "report",
        "compatible_versions": ["1.0.0"],
        "dependencies": [],
        "config_schema": {
            "type": "object",
            "properties": {
                "logo_url": {"type": "string", "default": "", "description": "Absolute URL or path of logo image file"},
                "primary_color": {"type": "string", "default": "#1e3a8a", "description": "Hex primary color code"},
                "include_sign_off": {"type": "boolean", "default": True}
            },
            "required": []
        }
    },
    "forecast_helper": {
        "id": "forecast_helper",
        "name": "Forecast Helper",
        "version": "1.0.0",
        "description": "Runs simple offline moving average and trend extrapolation predictions on data series.",
        "author": "Predictive Science",
        "capability": "analytics",
        "compatible_versions": ["1.0.0"],
        "dependencies": ["kpi_library"],
        "config_schema": {
            "type": "object",
            "properties": {
                "target_col": {"type": "string", "default": "value", "description": "Column name to project"},
                "periods": {"type": "integer", "default": 6, "description": "Number of periods forward to predict"},
                "method": {"type": "string", "default": "moving_average", "enum": ["moving_average", "linear_extrapolate"]}
            },
            "required": ["target_col"]
        }
    },
    "data_quality": {
        "id": "data_quality",
        "name": "Data Quality Rules",
        "version": "1.0.0",
        "description": "Workflow step executing column validations: null value rates, unique constraints, and pattern checks.",
        "author": "Compliance and Quality",
        "capability": "workflow_node",
        "compatible_versions": ["1.0.0"],
        "dependencies": [],
        "config_schema": {
            "type": "object",
            "properties": {
                "check_column": {"type": "string", "default": "", "description": "Column to evaluate"},
                "max_null_percentage": {"type": "number", "default": 5.0, "description": "Fail if null percentage exceeds this limit"},
                "check_uniqueness": {"type": "boolean", "default": False}
            },
            "required": ["check_column"]
        }
    }
}


class PluginRegistry:
    def __init__(self, registry_path: str = None):
        if not registry_path:
            base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
            registry_path = os.path.join(base_dir, "plugins_store", "registry.json")
            
        self.registry_path = os.path.abspath(registry_path)
        os.makedirs(os.path.dirname(self.registry_path), exist_ok=True)
        self.registry: Dict[str, Any] = self._load()

    def _load(self) -> Dict[str, Any]:
        if os.path.exists(self.registry_path):
            try:
                with open(self.registry_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    if "installed" not in data:
                        data["installed"] = {}
                    # Always sync default marketplace schemas
                    data["marketplace"] = DEFAULT_MARKETPLACE
                    return data
            except Exception as e:
                logger.error(f"Failed to load plugin registry file {self.registry_path}: {e}")
        return {"installed": {}, "marketplace": DEFAULT_MARKETPLACE}

    def save(self):
        try:
            with open(self.registry_path, 'w', encoding='utf-8') as f:
                json.dump(self.registry, f, indent=2)
        except Exception as e:
            logger.error(f"Failed to save plugin registry: {e}")

    def register_installed(self, plugin_id: str, metadata: Dict[str, Any], enabled: bool = True):
        self.registry["installed"][plugin_id] = {
            "metadata": metadata,
            "enabled": enabled,
            "version": metadata.get("version", "1.0.0"),
            "health_status": "healthy",
            "health_message": "Plugin loaded successfully",
            "last_health_check": datetime.utcnow().isoformat(),
            "install_time": datetime.utcnow().isoformat(),
            "version_history": [{"version": metadata.get("version", "1.0.0"), "timestamp": datetime.utcnow().isoformat(), "action": "installed"}]
        }
        self.save()

    def unregister_installed(self, plugin_id: str):
        if plugin_id in self.registry.get("installed", {}):
            del self.registry["installed"][plugin_id]
            self.save()

    def set_enabled(self, plugin_id: str, enabled: bool):
        if plugin_id in self.registry.get("installed", {}):
            self.registry["installed"][plugin_id]["enabled"] = enabled
            self.save()

    def update_health(self, plugin_id: str, status: str, message: str):
        if plugin_id in self.registry.get("installed", {}):
            self.registry["installed"][plugin_id]["health_status"] = status
            self.registry["installed"][plugin_id]["health_message"] = message
            self.registry["installed"][plugin_id]["last_health_check"] = datetime.utcnow().isoformat()
            self.save()

    def log_version_action(self, plugin_id: str, version: str, action: str):
        if plugin_id in self.registry.get("installed", {}):
            entry = self.registry["installed"][plugin_id]
            if "version_history" not in entry:
                entry["version_history"] = []
            entry["version_history"].append({
                "version": version,
                "timestamp": datetime.utcnow().isoformat(),
                "action": action
            })
            entry["version"] = version
            self.save()

    def list_installed(self) -> Dict[str, Any]:
        return self.registry.get("installed", {})

    def list_available(self) -> Dict[str, Any]:
        return self.registry.get("marketplace", {})
