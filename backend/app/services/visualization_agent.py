import logging
import pandas as pd
from typing import Any, Dict
from app.services.dashboard_service import (
    choose_optimal_chart,
    format_chart_js_payload,
    calculate_kpis_for_dataframe
)

logger = logging.getLogger(__name__)

class VisualizationAgent:
    async def execute_task(self, shared_memory: Dict[str, Any]) -> Dict[str, Any]:
        """Translates row records from previous sql agents to chart configs."""
        logger.info("Visualization Agent evaluating rows metadata for charting recommendations.")
        
        sql_output = shared_memory.get("SQLAgent", {})
        rows = sql_output.get("rows", [])
        columns = sql_output.get("columns", [])

        if not rows or not columns:
            return {
                "chart_recommended": False,
                "chart_type": None,
                "chart_data": None,
                "kpis": [],
                "reason": "No query data available to visualize."
            }

        try:
            # Reconstruct pandas DataFrame
            df = pd.DataFrame(rows, columns=columns)
            
            # Reuses existing optimal chart decider
            config = choose_optimal_chart(df)
            payload = format_chart_js_payload(df, config)
            kpis = calculate_kpis_for_dataframe(df)

            return {
                "chart_recommended": True,
                "chart_type": config.get("chart_type", "bar"),
                "chart_data": payload,
                "x_axis": config.get("x_axis"),
                "y_axis": config.get("y_axis"),
                "kpis": kpis[:4],
                "reason": f"Optimal chart selection determined: {config.get('chart_type')}."
            }

        except Exception as e:
            logger.warning(f"Visualization Agent failed layout creation: {e}")
            return {
                "chart_recommended": False,
                "chart_type": None,
                "chart_data": None,
                "kpis": [],
                "reason": f"Visualization generation failed: {e}"
            }
