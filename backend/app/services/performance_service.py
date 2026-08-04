import time
from typing import Any, Dict, List


class PerformanceService:
    def __init__(self):
        self.slow_queries: List[Dict[str, Any]] = []
        self.max_slow_queries = 20
        self.total_compressed_size = 0
        self.total_uncompressed_size = 0

    def record_slow_query(self, sql: str, duration_sec: float):
        """Records queries exceeding the database slow threshold."""
        self.slow_queries.append({"timestamp": time.time(), "sql": sql, "duration_sec": round(duration_sec, 4)})
        if len(self.slow_queries) > self.max_slow_queries:
            self.slow_queries.pop(0)

    def record_compression(self, uncompressed_bytes: int, compressed_bytes: int):
        """Records uncompressed and compressed payload sizes to compute compression ratio."""
        self.total_uncompressed_size += uncompressed_bytes
        self.total_compressed_size += compressed_bytes

    def get_compression_ratio(self) -> float:
        if self.total_compressed_size == 0:
            return 1.0
        ratio = self.total_uncompressed_size / self.total_compressed_size
        try:
            from app.services.monitoring_service import monitoring_service

            monitoring_service.set_compression_ratio(ratio)
        except Exception:
            pass
        return round(ratio, 2)

    async def get_stats(self) -> dict:
        """Returns statistics for response times, compression, and list of slow queries."""
        from app.services.monitoring_service import monitoring_service

        kg_entities_count = 0
        kg_relationships_count = 0
        try:
            from app.core.database import AsyncSessionLocal
            from sqlalchemy import select, func
            from app.models.knowledge import KnowledgeEntity, KnowledgeRelationship
            from app.services.monitoring_service import KG_ENTITY_COUNT, KG_RELATIONSHIP_COUNT
            
            async with AsyncSessionLocal() as session:
                kg_entities_count = (await session.execute(select(func.count(KnowledgeEntity.id)))).scalar() or 0
                kg_relationships_count = (await session.execute(select(func.count(KnowledgeRelationship.id)))).scalar() or 0
                
            KG_ENTITY_COUNT.set(kg_entities_count)
            KG_RELATIONSHIP_COUNT.set(kg_relationships_count)
        except Exception:
            pass

        # Collect predictive stats
        predictive_stats = {}
        try:
            from app.models.predictive import PredictiveHistory
            from app.models.prompt_registry import RegisteredModel
            async with AsyncSessionLocal() as session:
                total_models = (await session.execute(select(func.count(RegisteredModel.id)).where(RegisteredModel.provider == "AutoML"))).scalar() or 0
                total_trainings = (await session.execute(select(func.count(PredictiveHistory.id)))).scalar() or 0
                
            predictive_stats = {
                "active_models_count": total_models,
                "total_trainings_count": total_trainings
            }
            # Update Prometheus active models count
            monitoring_service.set_active_predictive_models(total_models)
        except Exception:
            pass

        # Collect plugin stats
        plugin_stats = {}
        try:
            from app.services.plugin_manager import plugin_manager
            plugin_stats = plugin_manager.get_telemetry_stats()
        except Exception:
            pass

        # Collect cluster stats
        cluster_stats = {}
        try:
            from app.services.cluster_manager import cluster_manager
            from app.services.distributed_scheduler import distributed_scheduler
            
            all_workers = cluster_manager.get_all_workers()
            all_jobs = distributed_scheduler.get_all_jobs()
            
            cluster_stats = {
                "active_workers_count": len([w for w in all_workers if w["status"] != "offline"]),
                "total_workers_count": len(all_workers),
                "queue_depth": len(distributed_scheduler.queue),
                "total_jobs_count": len(all_jobs),
                "failed_jobs_count": len([j for j in all_jobs if j["status"] == "failed"]),
                "running_jobs_count": len([j for j in all_jobs if j["status"] == "running"]),
                "workers": all_workers
            }
        except Exception:
            pass

        return {
            "avg_response_time_ms": monitoring_service.get_avg_response_time_ms(),
            "total_requests": monitoring_service.get_total_requests(),
            "slow_queries": self.slow_queries,
            "compression_ratio": self.get_compression_ratio(),
            "total_uncompressed_bytes": self.total_uncompressed_size,
            "total_compressed_bytes": self.total_compressed_size,
            "kg_entities_count": kg_entities_count,
            "kg_relationships_count": kg_relationships_count,
            "copilot_stats": copilot_telemetry.get_stats(),
            "predictive_stats": predictive_stats,
            "plugin_stats": plugin_stats,
            "cluster_stats": cluster_stats
        }


class CopilotTelemetry:
    def __init__(self):
        self.request_count = 0
        self.total_latency = 0.0
        self.intent_distribution = {
            "SQL Analytics": 0,
            "Dataset Analysis": 0,
            "Data Cleaning": 0,
            "Knowledge Graph": 0,
            "RAG Document Search": 0,
            "Workflow Automation": 0,
            "Federated Queries": 0,
            "Streaming Analytics": 0,
            "Report Generation": 0,
            "Explainability": 0,
            "Model Evaluation": 0,
            "Predictive Analytics": 0,
            "Prescriptive Analytics": 0
        }
        self.tool_usage_frequency = {
            "dataset_analysis": 0,
            "data_cleaning": 0,
            "federated_queries": 0,
            "sql_analytics": 0,
            "rag_document_search": 0,
            "knowledge_graph": 0,
            "streaming_analytics": 0,
            "model_evaluation": 0,
            "explainability": 0,
            "report_generation": 0,
            "predictive_analytics": 0,
            "prescriptive_analytics": 0
        }
        self.failed_orchestrations = 0

    def record_request(self, latency: float, intents: List[str], tools: List[str], success: bool):
        self.request_count += 1
        self.total_latency += latency
        for intent in intents:
            if intent in self.intent_distribution:
                self.intent_distribution[intent] += 1
        for tool in tools:
            if tool in self.tool_usage_frequency:
                self.tool_usage_frequency[tool] += 1
        if not success:
            self.failed_orchestrations += 1

    def get_stats(self) -> dict:
        avg_latency = self.total_latency / self.request_count if self.request_count > 0 else 0.0
        return {
            "request_count": self.request_count,
            "avg_response_time_ms": round(avg_latency * 1000, 2),
            "intent_distribution": self.intent_distribution,
            "tool_usage_frequency": self.tool_usage_frequency,
            "failed_orchestrations": self.failed_orchestrations
        }


performance_service = PerformanceService()
copilot_telemetry = CopilotTelemetry()

