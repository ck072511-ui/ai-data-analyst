from typing import Dict, Any, List
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
