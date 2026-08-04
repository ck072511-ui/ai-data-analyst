from typing import Dict, Any, List
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
