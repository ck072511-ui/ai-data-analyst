import os
import shutil
import sys
import json
import logging
import importlib.util
import time
from typing import Dict, Any, List, Optional, Set
from datetime import datetime
from app.services.plugin_sdk import BasePlugin
from app.services.plugin_registry import PluginRegistry

logger = logging.getLogger(__name__)

# Sample plugin code definitions to build offline files dynamically on disk
BLUEPRINTS_CODE = {
    "csv_import_plus": """import os
import csv
from typing import Dict, Any, List
from app.services.plugin_sdk import DataSourcePlugin

class CSVImportPlusPlugin(DataSourcePlugin):
    @property
    def metadata(self) -> Dict[str, Any]:
        return {
            "name": "CSV Import Plus",
            "description": "Enhanced CSV parsing data source with customizable delimiters, character encoding selectors, and header sanitizers.",
            "author": "Platform Team",
            "capability": "data_source",
            "compatible_versions": ["1.0.0"]
        }

    @property
    def version(self) -> str:
        return "1.0.0"

    def validate_config(self, config: Dict[str, Any]) -> bool:
        delim = config.get("delimiter", ",")
        if len(delim) != 1:
            raise ValueError("Delimiter must be a single character.")
        return True

    async def health_check(self) -> Dict[str, Any]:
        return {"status": "healthy", "details": {"delimiter_validated": True}}

    async def fetch_data(self, config: Dict[str, Any], params: Dict[str, Any]) -> List[Dict[str, Any]]:
        self.validate_config(config)
        filepath = params.get("file_path")
        if not filepath or not os.path.exists(filepath):
            raise ValueError(f"File path '{filepath}' does not exist.")
        
        delim = config.get("delimiter", ",")
        encoding = config.get("encoding", "utf-8")
        skip_rows = int(config.get("skip_rows", 0))
        
        rows = []
        with open(filepath, 'r', encoding=encoding) as f:
            for _ in range(skip_rows):
                next(f, None)
            reader = csv.DictReader(f, delimiter=delim)
            for row in reader:
                rows.append(dict(row))
        return rows
""",
    "advanced_charts": """from typing import Dict, Any, List
from app.services.plugin_sdk import VisualizationPlugin

class AdvancedChartsPlugin(VisualizationPlugin):
    @property
    def metadata(self) -> Dict[str, Any]:
        return {
            "name": "Advanced Charts",
            "description": "Premium charting extension compiling visual specs for Radar, Polar Area, and Bubble layouts.",
            "author": "Visualization Labs",
            "capability": "visualization",
            "compatible_versions": ["1.0.0"]
        }

    @property
    def version(self) -> str:
        return "1.0.0"

    def validate_config(self, config: Dict[str, Any]) -> bool:
        theme = config.get("chart_theme", "dark")
        if theme not in ["light", "dark", "glass"]:
            raise ValueError("Invalid chart_theme option.")
        return True

    async def health_check(self) -> Dict[str, Any]:
        return {"status": "healthy", "details": {"canvas_ready": True}}

    def generate_chart_spec(self, data: List[Dict[str, Any]], config: Dict[str, Any]) -> Dict[str, Any]:
        self.validate_config(config)
        theme = config.get("chart_theme", "dark")
        labels = [str(r.get("label", idx)) for idx, r in enumerate(data)]
        values = [float(r.get("value", 0.0)) for r in data]
        
        background_colors = {
            "light": "rgba(37, 99, 235, 0.2)",
            "dark": "rgba(124, 58, 237, 0.4)",
            "glass": "rgba(255, 255, 255, 0.15)"
        }
        border_colors = {
            "light": "#2563eb",
            "dark": "#7c3aed",
            "glass": "rgba(255, 255, 255, 0.8)"
        }
        
        return {
            "type": "radar",
            "data": {
                "labels": labels,
                "datasets": [{
                    "label": config.get("dataset_label", "Plugin Metric"),
                    "data": values,
                    "backgroundColor": background_colors.get(theme),
                    "borderColor": border_colors.get(theme),
                    "borderWidth": 2
                }]
            },
            "options": {
                "responsive": True,
                "plugins": {
                    "legend": {"position": "top"},
                    "title": {"display": True, "text": "Advanced Charts (Plugin Engine)"}
                }
            }
        }
""",
    "kpi_library": """from typing import Dict, Any, List
from app.services.plugin_sdk import AnalyticsPlugin, AIToolPlugin

class KPILibraryPlugin(AnalyticsPlugin, AIToolPlugin):
    @property
    def metadata(self) -> Dict[str, Any]:
        return {
            "name": "KPI Library",
            "description": "Calculates business core KPIs (e.g. Gross Margin Ratio, Customer Acquisition Cost, and Year-over-Year Growth).",
            "author": "Finance Analytics Group",
            "capability": "analytics",
            "compatible_versions": ["1.0.0"]
        }

    @property
    def version(self) -> str:
        return "1.0.0"

    def validate_config(self, config: Dict[str, Any]) -> bool:
        if not config.get("revenue_col") or not config.get("cost_col"):
            raise ValueError("Both revenue_col and cost_col must be specified in the configuration.")
        return True

    async def health_check(self) -> Dict[str, Any]:
        return {"status": "healthy", "details": {"library_ready": True}}

    async def run_analytics(self, data: List[Dict[str, Any]], config: Dict[str, Any]) -> Dict[str, Any]:
        self.validate_config(config)
        rev_col = config["revenue_col"]
        cost_col = config["cost_col"]
        
        total_rev = 0.0
        total_cost = 0.0
        row_count = 0
        
        for row in data:
            try:
                total_rev += float(row.get(rev_col, 0.0))
                total_cost += float(row.get(cost_col, 0.0))
                row_count += 1
            except (ValueError, TypeError):
                continue
                
        gross_profit = total_rev - total_cost
        margin_ratio = gross_profit / total_rev if total_rev > 0 else 0.0
        
        return {
            "metrics": {
                "total_revenue": round(total_rev, 2),
                "total_cost_of_sales": round(total_cost, 2),
                "gross_profit": round(gross_profit, 2),
                "gross_margin_ratio": round(margin_ratio, 4)
            },
            "rows_evaluated": row_count,
            "status": "success"
        }

    async def run_tool(self, inputs: Dict[str, Any], user_id: str) -> Dict[str, Any]:
        data = inputs.get("data", [])
        config = {
            "revenue_col": inputs.get("revenue_col", "revenue"),
            "cost_col": inputs.get("cost_col", "cost")
        }
        res = await self.run_analytics(data, config)
        return {
            "result": res,
            "explanation": f"KPI Library evaluated {res['rows_evaluated']} records. Gross Margin Ratio calculated as {round(res['metrics']['gross_margin_ratio']*100, 2)}%."
        }
""",
    "custom_report": """from typing import Dict, Any
from app.services.plugin_sdk import ReportPlugin

class CustomReportTemplatePlugin(ReportPlugin):
    @property
    def metadata(self) -> Dict[str, Any]:
        return {
            "name": "Custom Report Template",
            "description": "Renders reports with customized headers, enterprise logos, dynamic table styles, and signature panels.",
            "author": "Document Engineering",
            "capability": "report",
            "compatible_versions": ["1.0.0"]
        }

    @property
    def version(self) -> str:
        return "1.0.0"

    def validate_config(self, config: Dict[str, Any]) -> bool:
        return True

    async def health_check(self) -> Dict[str, Any]:
        return {"status": "healthy", "details": {"pdf_templates_loaded": True}}

    async def generate_report(self, data: Dict[str, Any], config: Dict[str, Any]) -> Dict[str, Any]:
        logo = config.get("logo_url", "default_logo.png")
        color = config.get("primary_color", "#1e3a8a")
        
        report_title = data.get("title", "Executive Financial Summary")
        creator = data.get("creator", "AI System Report")
        
        import os
        import uuid
        filename = f"custom_report_{uuid.uuid4().hex[:8]}.pdf"
        exports_dir = os.path.abspath(os.path.join("backend", "data", "exports")) if os.path.exists("backend") else os.path.abspath(os.path.join("data", "exports"))
        os.makedirs(exports_dir, exist_ok=True)
        file_path = os.path.join(exports_dir, filename)
        
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(f"CUSTOM PDF REPORT\\nTitle: {report_title}\\nCreator: {creator}\\nLogo: {logo}\\nPrimary Color: {color}\\n")
            f.write(f"KPI Margins: {data.get('kpi_summary', 'N/A')}\\n")
            if config.get("include_sign_off", True):
                f.write("\\nSigned off by: ________________________\\n")
                
        return {
            "file_path": file_path,
            "filename": filename,
            "status": "completed",
            "metadata": {
                "logo": logo,
                "color": color,
                "size_bytes": os.path.getsize(file_path)
            }
        }
""",
    "forecast_helper": """from typing import Dict, Any, List
from app.services.plugin_sdk import AnalyticsPlugin

class ForecastHelperPlugin(AnalyticsPlugin):
    @property
    def metadata(self) -> Dict[str, Any]:
        return {
            "name": "Forecast Helper",
            "description": "Runs simple offline moving average and trend extrapolation predictions on data series.",
            "author": "Predictive Science",
            "capability": "analytics",
            "compatible_versions": ["1.0.0"]
        }

    @property
    def version(self) -> str:
        return "1.0.0"

    @property
    def dependencies(self) -> List[str]:
        return ["kpi_library"]

    def validate_config(self, config: Dict[str, Any]) -> bool:
        if not config.get("target_col"):
            raise ValueError("target_col must be specified for predictions.")
        return True

    async def health_check(self) -> Dict[str, Any]:
        return {"status": "healthy", "details": {"pandas_inference_active": True}}

    async def run_analytics(self, data: List[Dict[str, Any]], config: Dict[str, Any]) -> Dict[str, Any]:
        self.validate_config(config)
        target = config["target_col"]
        periods = int(config.get("periods", 6))
        method = config.get("method", "moving_average")
        
        vals = []
        for r in data:
            try:
                vals.append(float(r.get(target, 0.0)))
            except (ValueError, TypeError):
                continue
                
        if len(vals) < 3:
            raise ValueError("Insufficient data points for forecasting (minimum 3 required).")
            
        projections = []
        if method == "moving_average":
            window = min(3, len(vals))
            current = list(vals)
            for _ in range(periods):
                avg = sum(current[-window:]) / window
                projections.append(round(avg, 2))
                current.append(avg)
        else: # linear extrapolation
            x1, y1 = 0, vals[0]
            xn, yn = len(vals) - 1, vals[-1]
            slope = (yn - y1) / (xn - x1) if xn > x1 else 0.0
            for i in range(1, periods + 1):
                proj = yn + (slope * i)
                projections.append(round(proj, 2))
                
        return {
            "forecast": projections,
            "method": method,
            "periods": periods,
            "input_points": len(vals),
            "status": "success"
        }
""",
    "data_quality": """from typing import Dict, Any
from app.services.plugin_sdk import WorkflowNodePlugin

class DataQualityRulesPlugin(WorkflowNodePlugin):
    @property
    def metadata(self) -> Dict[str, Any]:
        return {
            "name": "Data Quality Rules",
            "description": "Workflow step executing column validations: null value rates, unique constraints, and pattern checks.",
            "author": "Compliance and Quality",
            "capability": "workflow_node",
            "compatible_versions": ["1.0.0"]
        }

    @property
    def version(self) -> str:
        return "1.0.0"

    def validate_config(self, config: Dict[str, Any]) -> bool:
        if not config.get("check_column"):
            raise ValueError("check_column must be defined.")
        return True

    async def health_check(self) -> Dict[str, Any]:
        return {"status": "healthy", "details": {"validation_rules_count": 3}}

    async def execute(self, node_config: Dict[str, Any], context: Dict[str, Any], user_id: str) -> Dict[str, Any]:
        self.validate_config(node_config)
        col = node_config["check_column"]
        max_null = float(node_config.get("max_null_percentage", 5.0))
        check_uniq = bool(node_config.get("check_uniqueness", False))
        
        rows = []
        for out in context.get("outputs", {}).values():
            if isinstance(out, dict) and "rows" in out and isinstance(out["rows"], list):
                rows = out["rows"]
                break
                
        if not rows:
            rows = context.get("variables", {}).get("rows", [])
            
        if not rows:
            raise ValueError("No data records found in workflow context outputs or variables.")
            
        total = len(rows)
        null_count = 0
        vals = set()
        has_dup = False
        
        for row in rows:
            val = row.get(col)
            if val is None or str(val).strip() == "" or str(val).lower() == "null":
                null_count += 1
            if check_uniq:
                if val in vals:
                    has_dup = True
                vals.add(val)
                
        null_pct = (null_count / total) * 100.0 if total > 0 else 0.0
        
        is_valid = True
        errors = []
        
        if null_pct > max_null:
            is_valid = False
            errors.append(f"Null percentage of {round(null_pct, 2)}% exceeds limit of {max_null}%.")
            
        if check_uniq and has_dup:
            is_valid = False
            errors.append("Duplicate values found violating uniqueness rule.")
            
        if not is_valid:
            raise ValueError(f"Data Quality checks failed: {'; '.join(errors)}")
            
        return {
            "column": col,
            "null_percentage": round(null_pct, 2),
            "rows_checked": total,
            "passed": is_valid
        }
"""
}


class PluginManager:
    def __init__(self):
        base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        self.plugins_root = os.path.join(base_dir, "plugins_store")
        self.marketplace_dir = os.path.join(self.plugins_root, "marketplace")
        self.installed_dir = os.path.join(self.plugins_root, "installed")
        
        os.makedirs(self.marketplace_dir, exist_ok=True)
        os.makedirs(self.installed_dir, exist_ok=True)
        
        self.registry = PluginRegistry()
        self.loaded_plugins: Dict[str, BasePlugin] = {}
        
        # Telemetry metrics dictionary
        self.telemetry = {
            "loaded_count": 0,
            "failed_count": 0,
            "execution_count": 0,
            "execution_duration_sec": 0.0,
            "errors_count": 0,
            "usage": {},
            "errors": {}
        }
        
        # Initialize file folders
        self._initialize_store()

    def _initialize_store(self):
        """Pre-populates the marketplace and registry on server start."""
        # 1. Create __init__.py files
        for folder in [self.plugins_root, self.marketplace_dir, self.installed_dir]:
            init_file = os.path.join(folder, "__init__.py")
            if not os.path.exists(init_file):
                with open(init_file, 'w', encoding='utf-8') as f:
                    f.write("# Plugin package init\n")
                    
        # 2. Write sample plugin blueprints in the marketplace folder
        available_market = self.registry.list_available()
        for pid, code in BLUEPRINTS_CODE.items():
            blueprint_path = os.path.join(self.marketplace_dir, pid)
            os.makedirs(blueprint_path, exist_ok=True)
            
            # Write main.py
            main_py = os.path.join(blueprint_path, "main.py")
            if not os.path.exists(main_py):
                with open(main_py, 'w', encoding='utf-8') as f:
                    f.write(code)
            
            # Write metadata.json
            meta_json = os.path.join(blueprint_path, "metadata.json")
            if not os.path.exists(meta_json):
                meta = available_market.get(pid, {})
                with open(meta_json, 'w', encoding='utf-8') as f:
                    json.dump(meta, f, indent=2)

    def discover_and_load_plugins(self):
        """Scans installed directory, resolves dependencies, and dynamically imports plugins."""
        self.loaded_plugins.clear()
        self.telemetry["loaded_count"] = 0
        self.telemetry["failed_count"] = 0
        
        installed_list = self.registry.list_installed()
        
        # Scan files on disk
        candidates = {}
        for name in os.listdir(self.installed_dir):
            plugin_path = os.path.join(self.installed_dir, name)
            if os.path.isdir(plugin_path):
                meta_file = os.path.join(plugin_path, "metadata.json")
                main_file = os.path.join(plugin_path, "main.py")
                if os.path.exists(meta_file) and os.path.exists(main_file):
                    try:
                        with open(meta_file, 'r', encoding='utf-8') as f:
                            meta = json.load(f)
                        candidates[name] = {
                            "metadata": meta,
                            "main_file": main_file,
                            "path": plugin_path
                        }
                    except Exception as e:
                        logger.error(f"Failed to read candidates metadata for {name}: {e}")
                        self.telemetry["failed_count"] += 1
                        
        # Filter by registry enabled status
        enabled_candidates = {}
        for pid, c in candidates.items():
            reg_entry = installed_list.get(pid)
            if reg_entry and reg_entry.get("enabled", True):
                enabled_candidates[pid] = c
            elif not reg_entry:
                # If discovered on disk but not in registry, register and enable it by default
                self.registry.register_installed(pid, c["metadata"], enabled=True)
                enabled_candidates[pid] = c
                
        # Resolve dependencies using topological sort
        ordered_pids = self._resolve_dependencies(enabled_candidates)
        
        # Dynamically load
        for pid in ordered_pids:
            c = enabled_candidates[pid]
            try:
                plugin_instance = self._load_module(pid, c["main_file"])
                # Validate interface
                if not isinstance(plugin_instance, BasePlugin):
                    raise TypeError("Plugin class must inherit from BasePlugin")
                
                # Check version compatibility
                comp_vers = plugin_instance.metadata.get("compatible_versions", [])
                if "1.0.0" not in comp_vers:  # core version is 1.0.0
                    logger.warning(f"Plugin '{pid}' version compatibility check failed.")
                
                self.loaded_plugins[pid] = plugin_instance
                self.telemetry["loaded_count"] += 1
                self.registry.update_health(pid, "healthy", "Loaded successfully")
                
                # Record in Prometheus counter
                self._record_prometheus_load(pid, "success")
                
            except Exception as e:
                logger.exception(f"Failed to load plugin {pid}")
                self.telemetry["failed_count"] += 1
                self.registry.update_health(pid, "unhealthy", f"Load failed: {str(e)}")
                self._record_prometheus_load(pid, "failure")
                
    def _load_module(self, plugin_id: str, filepath: str) -> BasePlugin:
        """Loads python module dynamically using importlib."""
        module_name = f"app.plugins_store.installed.{plugin_id}.main"
        
        # Remove from sys.modules if already loaded to force reload
        if module_name in sys.modules:
            del sys.modules[module_name]
            
        spec = importlib.util.spec_from_file_location(module_name, filepath)
        if spec is None or spec.loader is None:
            raise ImportError(f"Cannot load module spec for {plugin_id}")
            
        module = importlib.util.module_from_spec(spec)
        sys.modules[module_name] = module
        spec.loader.exec_module(module)
        
        # Instantiate class inheriting from BasePlugin
        for attr_name in dir(module):
            attr = getattr(module, attr_name)
            if isinstance(attr, type) and issubclass(attr, BasePlugin) and attr is not BasePlugin:
                if attr.__module__ == module_name:
                    return attr()
                
        raise TypeError(f"No class implementing BasePlugin found in {filepath}")

    def _resolve_dependencies(self, candidates: Dict[str, Any]) -> List[str]:
        """Performs topological sorting of plugins based on their dependencies."""
        resolved = []
        visited = {} # State mapping: 0=visiting, 1=visited
        
        def dep_check(pid: str):
            visited[pid] = 0
            # Get dependencies from candidate metadata or blueprint schema
            deps = candidates[pid]["metadata"].get("dependencies", [])
            for dep in deps:
                if dep not in candidates:
                    # Missing dependency or disabled dependency
                    raise ValueError(f"Plugin '{pid}' depends on missing or disabled plugin '{dep}'")
                if dep not in visited:
                    dep_check(dep)
                elif visited[dep] == 0:
                    raise ValueError(f"Circular dependency detected between '{pid}' and '{dep}'")
            visited[pid] = 1
            resolved.append(pid)
            
        for pid in candidates:
            if pid not in visited:
                try:
                    dep_check(pid)
                except ValueError as err:
                    logger.error(str(err))
                    self.registry.update_health(pid, "unhealthy", f"Dependency resolution failed: {str(err)}")
                    # Remove candidate so it doesn't try to load
                    
        return resolved

    def install_plugin(self, plugin_id: str) -> bool:
        """Installs plugin from offline marketplace catalog."""
        src_path = os.path.join(self.marketplace_dir, plugin_id)
        dest_path = os.path.join(self.installed_dir, plugin_id)
        
        if not os.path.exists(src_path):
            raise FileNotFoundError(f"Plugin '{plugin_id}' not found in marketplace catalog.")
            
        # Copy package folder
        if os.path.exists(dest_path):
            shutil.rmtree(dest_path)
        shutil.copytree(src_path, dest_path)
        
        # Load metadata to register
        meta_file = os.path.join(dest_path, "metadata.json")
        with open(meta_file, 'r', encoding='utf-8') as f:
            metadata = json.load(f)
            
        self.registry.register_installed(plugin_id, metadata, enabled=True)
        self.discover_and_load_plugins()
        return True

    def uninstall_plugin(self, plugin_id: str) -> bool:
        """Removes plugin package and metadata completely."""
        dest_path = os.path.join(self.installed_dir, plugin_id)
        if os.path.exists(dest_path):
            shutil.rmtree(dest_path)
            
        self.registry.unregister_installed(plugin_id)
        if plugin_id in self.loaded_plugins:
            del self.loaded_plugins[plugin_id]
        return True

    def enable_plugin(self, plugin_id: str) -> bool:
        self.registry.set_enabled(plugin_id, True)
        self.discover_and_load_plugins()
        return True

    def disable_plugin(self, plugin_id: str) -> bool:
        self.registry.set_enabled(plugin_id, False)
        if plugin_id in self.loaded_plugins:
            del self.loaded_plugins[plugin_id]
        self.discover_and_load_plugins()
        return True

    def upgrade_plugin(self, plugin_id: str) -> bool:
        """Upgrades plugin files from marketplace catalog, logs action."""
        src_path = os.path.join(self.marketplace_dir, plugin_id)
        meta_file = os.path.join(src_path, "metadata.json")
        if not os.path.exists(meta_file):
            raise FileNotFoundError("Marketplace plugin metadata not found.")
            
        with open(meta_file, 'r', encoding='utf-8') as f:
            metadata = json.load(f)
        new_version = metadata.get("version", "1.0.0")
        
        # Perform install replacement
        self.install_plugin(plugin_id)
        self.registry.log_version_action(plugin_id, new_version, "upgraded")
        return True

    def rollback_plugin(self, plugin_id: str) -> bool:
        """Rolls back the plugin version."""
        # For simplicity, restore default marketplace version
        self.install_plugin(plugin_id)
        self.registry.log_version_action(plugin_id, "1.0.0", "rolled_back")
        return True

    async def run_health_checks(self) -> List[Dict[str, Any]]:
        """Invokes health checks on all loaded plugins and updates registry."""
        results = []
        for pid, plugin in list(self.loaded_plugins.items()):
            try:
                start_t = time.time()
                res = await plugin.health_check()
                duration = time.time() - start_t
                
                status = res.get("status", "healthy")
                details = res.get("details", {})
                self.registry.update_health(pid, status, f"Health check passed in {round(duration, 4)}s.")
                
                results.append({
                    "plugin_id": pid,
                    "name": plugin.metadata.get("name"),
                    "status": status,
                    "details": details
                })
            except Exception as e:
                logger.error(f"Health check failed for plugin {pid}: {e}")
                self.registry.update_health(pid, "unhealthy", f"Health check failed: {str(e)}")
                results.append({
                    "plugin_id": pid,
                    "name": plugin.metadata.get("name") if plugin else pid,
                    "status": "unhealthy",
                    "details": {"error": str(e)}
                })
        return results

    # Execution capabilities wrappers with metrics
    def has_node_type(self, node_type: str) -> bool:
        return any(
            p.metadata.get("capability") == "workflow_node" and node_type == pid
            for pid, p in self.loaded_plugins.items()
        )

    async def validate_node_config(self, node_type: str, node: Dict[str, Any], context: Dict[str, Any]):
        plugin = self.loaded_plugins.get(node_type)
        if plugin:
            config = node.get("config", {})
            plugin.validate_config(config)

    async def execute_node(self, node_type: str, node: Dict[str, Any], context: Dict[str, Any], user_id: str) -> Dict[str, Any]:
        plugin = self.loaded_plugins.get(node_type)
        if not plugin:
            raise ValueError(f"Plugin for node type {node_type} not found or disabled.")
            
        start_t = time.time()
        self.telemetry["execution_count"] += 1
        self._record_prometheus_usage(node_type)
        
        try:
            res = await plugin.execute(node.get("config", {}), context, user_id)
            duration = time.time() - start_t
            self.telemetry["execution_duration_sec"] += duration
            
            # Record Prometheus latency
            self._record_prometheus_execution(node_type, "workflow_node", duration)
            return res
        except Exception as e:
            self.telemetry["errors_count"] += 1
            self.telemetry["errors"][node_type] = self.telemetry["errors"].get(node_type, 0) + 1
            self._record_prometheus_error(node_type, type(e).__name__)
            raise e

    def get_enabled_plugins_by_capability(self, capability: str) -> List[tuple]:
        return [
            (pid, p) for pid, p in self.loaded_plugins.items()
            if p.metadata.get("capability") == capability
        ]

    async def execute_ai_tool(self, plugin_id: str, inputs: Dict[str, Any], user_id: str) -> Dict[str, Any]:
        plugin = self.loaded_plugins.get(plugin_id)
        if not plugin or not hasattr(plugin, "run_tool"):
            raise ValueError(f"AI Tool plugin '{plugin_id}' is not loaded.")
            
        start_t = time.time()
        self.telemetry["execution_count"] += 1
        self._record_prometheus_usage(plugin_id)
        
        try:
            res = await plugin.run_tool(inputs, user_id)
            duration = time.time() - start_t
            self.telemetry["execution_duration_sec"] += duration
            self._record_prometheus_execution(plugin_id, "ai_tool", duration)
            return res
        except Exception as e:
            self.telemetry["errors_count"] += 1
            self.telemetry["errors"][plugin_id] = self.telemetry["errors"].get(plugin_id, 0) + 1
            self._record_prometheus_error(plugin_id, type(e).__name__)
            raise e

    def get_telemetry_stats(self) -> dict:
        """Gathers stats for system performance integrations."""
        return {
            "loaded_plugins_count": self.telemetry["loaded_count"],
            "failed_plugins_count": self.telemetry["failed_count"],
            "execution_count": self.telemetry["execution_count"],
            "avg_execution_time_ms": round((self.telemetry["execution_duration_sec"] / self.telemetry["execution_count"] * 1000), 2) if self.telemetry["execution_count"] > 0 else 0.0,
            "errors_count": self.telemetry["errors_count"],
            "errors_distribution": self.telemetry["errors"]
        }

    # Internal metrics helper bindings to Prometheus
    def _record_prometheus_load(self, plugin: str, status: str):
        try:
            from app.services.monitoring_service import monitoring_service
            if hasattr(monitoring_service, "record_plugin_load"):
                monitoring_service.record_plugin_load(plugin, status)
        except Exception:
            pass

    def _record_prometheus_execution(self, plugin: str, capability: str, duration_sec: float):
        try:
            from app.services.monitoring_service import monitoring_service
            if hasattr(monitoring_service, "record_plugin_execution"):
                monitoring_service.record_plugin_execution(plugin, capability, duration_sec)
        except Exception:
            pass

    def _record_prometheus_error(self, plugin: str, error_type: str):
        try:
            from app.services.monitoring_service import monitoring_service
            if hasattr(monitoring_service, "record_plugin_error"):
                monitoring_service.record_plugin_error(plugin, error_type)
        except Exception:
            pass

    def _record_prometheus_usage(self, plugin: str):
        try:
            from app.services.monitoring_service import monitoring_service
            if hasattr(monitoring_service, "record_plugin_usage"):
                monitoring_service.record_plugin_usage(plugin)
        except Exception:
            pass


plugin_manager = PluginManager()
