import math
import json
import logging
from collections import defaultdict
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)

class StreamAnalyticsService:
    def __init__(self):
        # Cache for historical window results: stream_id -> List of window results dicts
        self.window_history: Dict[str, List[Dict[str, Any]]] = defaultdict(list)
        # Running KPIs: stream_id -> dict of overall aggregates
        self.running_kpis: Dict[str, Dict[str, Any]] = defaultdict(dict)
        # Maximum history depth to keep for calculating rolling metrics
        self.max_history_len = 100

    async def process_window_results(self, stream_id: str, results: Dict[str, Any], user_id: str):
        """Main processing entry point for incoming window aggregate outputs."""
        history = self.window_history[stream_id]
        history.append(results)
        if len(history) > self.max_history_len:
            history.pop(0)

        # 1. Update running KPIs & cumulative statistics
        await self._update_running_kpis(stream_id, results)

        # 2. Check Static Thresholds
        await self._check_thresholds(stream_id, results, user_id)

        # 3. Detect Trends
        await self._detect_trends(stream_id, results, user_id)

        # 4. Perform Z-Score Anomaly Detection
        await self._detect_anomalies(stream_id, results, user_id)

    async def get_running_metrics(self, stream_id: str) -> Dict[str, Any]:
        return {
            "running_kpis": self.running_kpis[stream_id],
            "recent_windows": self.window_history[stream_id][-10:]
        }

    async def _update_running_kpis(self, stream_id: str, results: Dict[str, Any]):
        """Maintains global running aggregates for active streams."""
        kpis = self.running_kpis[stream_id]
        
        # Cumulative event count
        kpis["total_events"] = kpis.get("total_events", 0) + results.get("_event_count", 0)
        kpis["window_count"] = kpis.get("window_count", 0) + 1

        # Check for numeric metrics in result and update cumulative sums
        for k, v in results.items():
            if k.startswith("_") or not isinstance(v, (int, float)):
                continue

            sum_key = f"running_sum_{k}"
            avg_key = f"running_avg_{k}"
            max_key = f"running_max_{k}"
            min_key = f"running_min_{k}"

            kpis[sum_key] = kpis.get(sum_key, 0.0) + float(v)
            kpis[max_key] = max(kpis.get(max_key, float("-inf")), float(v))
            kpis[min_key] = min(kpis.get(min_key, float("inf")), float(v))
            kpis[avg_key] = kpis[sum_key] / kpis["window_count"]

            # Incrementally register derived metrics in Knowledge Graph if needed
            try:
                from app.services.knowledge_graph_service import knowledge_graph_service
                # Add to incremental metric registry
                await knowledge_graph_service.register_derived_metric_incrementally(
                    stream_id, metric_name=k, formula=f"Running aggregate average/sum of {k}"
                )
            except Exception as e:
                logger.error(f"Failed to update derived metric in Knowledge Graph: {e}")

    async def _check_thresholds(self, stream_id: str, results: Dict[str, Any], user_id: str):
        """Evaluates whether aggregated field values exceed specified limits."""
        from app.core.database import AsyncSessionLocal
        from app.models.stream import StreamConfig
        from app.services.stream_alert_service import stream_alert_service

        async with AsyncSessionLocal() as session:
            stream = (await session.execute(
                select(StreamConfig).where(StreamConfig.id == stream_id)
            )).scalar_one_or_none()
            if not stream:
                return

            try:
                source_config = json.loads(stream.source_config)
                thresholds = source_config.get("thresholds", []) # List of threshold dicts
            except Exception:
                thresholds = []

            for th in thresholds:
                field = th.get("field")
                operator = th.get("operator", ">")
                threshold_val = float(th.get("value", 0))
                severity = th.get("severity", "warning")

                if field in results and results[field] is not None:
                    val = float(results[field])
                    breached = False

                    if operator == ">" and val > threshold_val:
                        breached = True
                    elif operator == ">=" and val >= threshold_val:
                        breached = True
                    elif operator == "<" and val < threshold_val:
                        breached = True
                    elif operator == "<=" and val <= threshold_val:
                        breached = True
                    elif operator == "==" and val == threshold_val:
                        breached = True

                    if breached:
                        msg = f"Threshold breached on {stream.name}: field '{field}' = {val} (Condition: {operator} {threshold_val})"
                        await stream_alert_service.trigger_threshold_alert(
                            stream_id=stream_id,
                            message=msg,
                            severity=severity,
                            user_id=user_id
                        )

    async def _detect_trends(self, stream_id: str, results: Dict[str, Any], user_id: str):
        """Computes rate of change/trends over consecutive windows."""
        history = self.window_history[stream_id]
        if len(history) < 2:
            return

        prev_results = history[-2]

        for k, val in results.items():
            if k.startswith("_") or not isinstance(val, (int, float)):
                continue

            prev_val = prev_results.get(k)
            if prev_val is not None and isinstance(prev_val, (int, float)) and prev_val != 0:
                percent_change = ((val - prev_val) / prev_val) * 100
                
                # Check for significant trend jumps (e.g., > 50% increase or decrease)
                if abs(percent_change) > 50.0:
                    logger.info(f"Significant trend detected on stream {stream_id}: field {k} changed by {percent_change:.2f}%")

    async def _detect_anomalies(self, stream_id: str, results: Dict[str, Any], user_id: str):
        """Detects statistical outliers using rolling mean and standard deviation (Z-score)."""
        history = self.window_history[stream_id]
        # Require at least 5 windows for a rolling window standard deviation base
        if len(history) < 5:
            return

        from app.services.stream_alert_service import stream_alert_service
        from app.core.database import AsyncSessionLocal
        from app.models.stream import StreamConfig

        # Standard Z-Score threshold (default to 2.5 standard deviations)
        z_threshold = 2.5

        async with AsyncSessionLocal() as session:
            stream = (await session.execute(
                select(StreamConfig).where(StreamConfig.id == stream_id)
            )).scalar_one_or_none()
            if stream:
                try:
                    source_config = json.loads(stream.source_config)
                    z_threshold = float(source_config.get("anomaly_z_score", 2.5))
                except Exception:
                    pass

        # Check numeric metrics for anomaly
        for k, val in results.items():
            if k.startswith("_") or not isinstance(val, (int, float)):
                continue

            # Compute rolling statistics over preceding windows
            prev_values = [h[k] for h in history[:-1] if k in h and isinstance(h[k], (int, float))]
            if len(prev_values) < 4:
                continue

            mean = sum(prev_values) / len(prev_values)
            variance = sum((x - mean) ** 2 for x in prev_values) / len(prev_values)
            std_dev = math.sqrt(variance)

            if std_dev > 0:
                z_score = abs(val - mean) / std_dev
                if z_score > z_threshold:
                    msg = f"Statistical anomaly detected on stream {stream.name if stream else stream_id}: field '{k}' = {val} has Z-score of {z_score:.2f} (exceeds threshold {z_threshold}; Mean: {mean:.2f}, StdDev: {std_dev:.2f})"
                    await stream_alert_service.trigger_anomaly_alert(
                        stream_id=stream_id,
                        message=msg,
                        user_id=user_id
                    )


# Import select inside functions or lazily
from sqlalchemy import select

stream_analytics_service = StreamAnalyticsService()
