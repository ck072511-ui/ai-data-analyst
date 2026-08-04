from typing import Dict, Any, List
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
