from prometheus_client import Counter, Gauge, Histogram

# Initialize metrics
HTTP_REQUESTS_TOTAL = Counter("http_requests_total", "Total HTTP requests", ["method", "endpoint", "status_code"])
HTTP_REQUEST_DURATION_SECONDS = Histogram(
    "http_request_duration_seconds", "HTTP request duration in seconds", ["method", "endpoint"]
)
ACTIVE_REQUESTS = Gauge("active_requests", "Number of active requests")
AUTH_SUCCESS_TOTAL = Counter("auth_success_total", "Total successful authentications")
AUTH_FAILURE_TOTAL = Counter("auth_failure_total", "Total failed authentications")
DASHBOARD_GENERATION_TOTAL = Counter("dashboard_generation_total", "Total dashboards generated")
DATASET_UPLOAD_TOTAL = Counter("dataset_upload_total", "Total datasets uploaded")
AI_QUERY_TOTAL = Counter("ai_query_total", "Total AI queries executed")

# NL2SQL metrics
NL2SQL_LATENCY_SECONDS = Histogram(
    "nl2sql_latency_seconds", "Latency of NL2SQL operations in seconds", ["operation"]
)
NL2SQL_VALIDATION_FAILURES_TOTAL = Counter(
    "nl2sql_validation_failures_total", "Total validation failures"
)
NL2SQL_BLOCKED_QUERIES_TOTAL = Counter(
    "nl2sql_blocked_queries_total", "Total queries blocked by safety layer"
)
NL2SQL_CONFIDENCE_SUM = Counter(
    "nl2sql_confidence_sum", "Sum of confidence scores for averaging"
)
NL2SQL_CONFIDENCE_COUNT = Counter(
    "nl2sql_confidence_count", "Count of confidence scores"
)

# AI Cleaning metrics
AI_CLEANING_RECOMMENDATION_LATENCY = Histogram(
    "ai_cleaning_recommendation_latency_seconds", "Inference latency of AI data cleaning recommendations"
)
AI_CLEANING_EXECUTION_DURATION = Histogram(
    "ai_cleaning_execution_duration_seconds", "Execution duration of AI cleaning pipelines"
)
AI_CLEANING_APPROVALS_TOTAL = Counter(
    "ai_cleaning_approvals_total", "Total recommendations reviewed by user", ["status"]
)
AI_CLEANING_ROLLBACKS_TOTAL = Counter(
    "ai_cleaning_rollbacks_total", "Total rollbacks initiated on AI cleaning versions"
)
AI_CLEANING_CONFIDENCE_SUM = Counter(
    "ai_cleaning_confidence_sum", "Sum of recommendation confidence scores"
)
AI_CLEANING_CONFIDENCE_COUNT = Counter(
    "ai_cleaning_confidence_count", "Count of recommendation confidence scores"
)
AI_CLEANING_TRANSFORMATIONS_TOTAL = Counter(
    "ai_cleaning_transformations_total", "Total count of executed transformations by type", ["transformation"]
)

# RAG metrics
RAG_EMBEDDING_LATENCY = Histogram("rag_embedding_latency_seconds", "Latency of generating query embeddings")
RAG_RETRIEVAL_LATENCY = Histogram("rag_retrieval_latency_seconds", "Latency of vector store context chunk retrieval")
RAG_GENERATION_LATENCY = Histogram("rag_generation_latency_seconds", "Latency of RAG answer generation from LLM")
RAG_CONFIDENCE_SUM = Counter("rag_confidence_sum", "Sum of query similarity confidence scores")
RAG_CONFIDENCE_COUNT = Counter("rag_confidence_count", "Count of query similarity confidence scores")
RAG_RETRIEVED_CHUNKS_SUM = Counter("rag_retrieved_chunks_sum", "Sum of retrieved chunks counts")
RAG_RETRIEVED_CHUNKS_COUNT = Counter("rag_retrieved_chunks_count", "Count of chunk retrieval calls")
RAG_QUERIES_TOTAL = Counter("rag_queries_total", "Total RAG queries processed", ["status"])

# Agent metrics
AGENT_LATENCY_SECONDS = Histogram("agent_latency_seconds", "Inference and task execution duration per agent", ["agent"])
AGENT_FAILURES_TOTAL = Counter("agent_failures_total", "Execution failure count per agent", ["agent"])
CRITIC_REJECTS_TOTAL = Counter("critic_rejects_total", "Total queries rejected by Critic Agent requiring re-planning")

# XAI metrics
XAI_EXPLANATION_LATENCY = Histogram("xai_explanation_latency_seconds", "Latency of explainability reports compiler")
XAI_CONFIDENCE_SUM = Counter("xai_confidence_sum", "Sum of generated queries final confidence scores")
XAI_CONFIDENCE_COUNT = Counter("xai_confidence_count", "Count of generated queries final confidence scores")
XAI_LOW_CONFIDENCE_RESPONSES = Counter("xai_low_confidence_responses_total", "Count of responses with confidence less than 50%")
XAI_MISSING_CITATIONS = Counter("xai_missing_citations_total", "Count of queries executed with empty citations")

# Report metrics
REPORT_GENERATION_DURATION = Histogram("report_generation_duration_seconds", "Report compilation latency", ["format"])
REPORT_FAILURES_TOTAL = Counter("report_failures_total", "Count of report compilation failures")
REPORT_DOWNLOADS_TOTAL = Counter("report_downloads_total", "Count of physical report downloads")
REPORT_SIZE_SUM = Counter("report_size_sum", "Sum of generated report file sizes in bytes", ["format"])
REPORT_SIZE_COUNT = Counter("report_size_count", "Count of generated reports sizes logged", ["format"])

# Prompt and Evaluation metrics
PROMPT_EXECUTIONS_TOTAL = Counter("prompt_executions_total", "Total prompt templates executed")
PROMPT_ROLLBACKS_TOTAL = Counter("prompt_rollbacks_total", "Total prompt templates rollbacks triggered")
MODEL_CHANGES_TOTAL = Counter("model_changes_total", "Total default model activation changes")
EVALUATION_DURATION = Histogram("evaluation_duration_seconds", "LLM evaluation execution latency")
EVAL_SCORE_SUM = Counter("eval_score_sum", "Sum of prompt evaluation scores")
EVAL_SCORE_COUNT = Counter("eval_score_count", "Count of prompt evaluations conducted")

# Caching metrics
CACHE_HITS_TOTAL = Counter("cache_hits_total", "Total cache hits", ["cache_type"])
CACHE_MISSES_TOTAL = Counter("cache_misses_total", "Total cache misses", ["cache_type"])
CACHE_MEMORY_USAGE_BYTES = Gauge("cache_memory_usage_bytes", "Memory used by cache in bytes")

# Compression metrics
COMPRESSION_RATIO = Gauge("compression_ratio", "API response compression ratio")

# Predictive and Prescriptive metrics
PREDICTIVE_TRAINING_DURATION = Histogram("predictive_training_duration_seconds", "AutoML model training duration in seconds")
PREDICTIVE_PREDICTION_LATENCY = Histogram("predictive_prediction_latency_seconds", "Model inference latency in seconds")
PREDICTIVE_MODEL_ACCURACY = Gauge("predictive_model_accuracy", "Accuracy or r2 score of trained models")
PREDICTIVE_ACTIVE_MODELS = Gauge("predictive_active_models", "Total count of active trained models in registry")
PRESCRIPTIVE_RECOMMENDATION_LATENCY = Histogram("prescriptive_recommendation_latency_seconds", "Prescriptive actions recommendation generation latency in seconds")
WORKFLOW_PREDICTION_EXECUTIONS = Counter("workflow_prediction_executions_total", "Total workflow prediction node executions completed")

# Performance metrics
SLOW_REQUESTS_TOTAL = Counter("slow_requests_total", "Total requests slower than threshold", ["method", "endpoint"])
LARGE_RESPONSES_TOTAL = Counter("large_responses_total", "Total large responses", ["method", "endpoint"])
DB_QUERY_DURATION_SECONDS = Histogram("db_query_duration_seconds", "Database query execution time in seconds")
DASHBOARD_GENERATION_DURATION_SECONDS = Histogram(
    "dashboard_generation_duration_seconds", "Dashboard generation time in seconds"
)
DATASET_PROCESSING_DURATION_SECONDS = Histogram(
    "dataset_processing_duration_seconds", "Dataset processing time in seconds"
)

# Knowledge Graph metrics
KG_ENTITY_COUNT = Gauge("kg_entity_count", "Total entities in Knowledge Graph")
KG_RELATIONSHIP_COUNT = Gauge("kg_relationship_count", "Total relationships in Knowledge Graph")
KG_BUILD_DURATION_SECONDS = Histogram("kg_build_duration_seconds", "Knowledge Graph build duration in seconds")
KG_SEARCH_LATENCY_SECONDS = Histogram("kg_search_latency_seconds", "Knowledge Graph search latency in seconds")

# Federated Query Engine metrics
FEDERATION_LATENCY_SECONDS = Histogram("federation_latency_seconds", "Overall distributed federation query duration")
FEDERATION_JOIN_TIME_SECONDS = Histogram("federation_join_time_seconds", "In-memory join operations time in seconds")
FEDERATION_SUCCESS_TOTAL = Counter("federation_success_total", "Total successful federated queries")
FEDERATION_PARTIAL_FAILURES_TOTAL = Counter("federation_partial_failures_total", "Total federated queries with partial database failures")

# Streaming metrics
STREAMING_EVENTS_TOTAL = Counter("streaming_events_total", "Total streaming events processed", ["stream_id"])
STREAMING_PROCESSING_LATENCY = Histogram("streaming_processing_latency_seconds", "Latency of processing streaming events", ["stream_id"])
STREAMING_ACTIVE_STREAMS = Gauge("streaming_active_streams", "Number of active data streams")
STREAMING_QUEUE_DEPTH = Gauge("streaming_queue_depth", "Depth of stream event queue", ["stream_id"])
STREAMING_DROPPED_EVENTS = Counter("streaming_dropped_events_total", "Total dropped streaming events", ["stream_id"])
STREAMING_WINDOW_EXECUTION_TIME = Histogram("streaming_window_execution_seconds", "Execution duration of streaming windows", ["stream_id", "window_type"])
STREAMING_TRIGGERED_WORKFLOWS = Counter("streaming_triggered_workflows_total", "Total workflows triggered by streaming events", ["stream_id", "trigger_reason"])

# Plugin Extension metrics
PLUGIN_LOADS_TOTAL = Counter("plugin_loads_total", "Total plugins loaded", ["plugin", "status"])
PLUGIN_EXECUTION_DURATION_SECONDS = Histogram("plugin_execution_duration_seconds", "Plugin execution latency in seconds", ["plugin", "capability"])
PLUGIN_ERRORS_TOTAL = Counter("plugin_errors_total", "Total plugin execution errors", ["plugin", "error_type"])
PLUGIN_USAGE_TOTAL = Counter("plugin_usage_total", "Total plugin invocation counts", ["plugin"])

# Cluster platform metrics
CLUSTER_WORKER_COUNT = Gauge("cluster_worker_count", "Number of active cluster workers")
CLUSTER_QUEUE_DEPTH = Gauge("cluster_queue_depth", "Distributed scheduler queue depth")
CLUSTER_WORKER_UTILIZATION = Gauge("cluster_worker_utilization", "CPU/RAM utilization percentage", ["worker_id", "resource_type"])
CLUSTER_TASK_LATENCY = Histogram("cluster_task_latency_seconds", "Task latency in seconds", ["task_type"])
CLUSTER_TASK_RETRIES = Counter("cluster_task_retries_total", "Total task retries count")
CLUSTER_FAILOVER_EVENTS = Counter("cluster_failover_events_total", "Total cluster node failover events count")
CLUSTER_SCHEDULER_LATENCY = Histogram("cluster_scheduler_latency_seconds", "Scheduler latency in seconds")


class StatisticsTracker:
    def __init__(self):
        self.total_requests = 0
        self.total_response_time_sec = 0.0
        self.request_count_with_duration = 0

    def record_request(self, duration_sec: float):
        self.total_requests += 1
        self.total_response_time_sec += duration_sec
        self.request_count_with_duration += 1

    def get_avg_response_time_ms(self) -> float:
        if self.request_count_with_duration == 0:
            return 0.0
        return round((self.total_response_time_sec / self.request_count_with_duration) * 1000, 2)


stats_tracker = StatisticsTracker()


class MonitoringServiceWrapper:
    def record_request(
        self, method: str, endpoint: str, status_code: int, duration_sec: float, response_size_bytes: int
    ):
        HTTP_REQUESTS_TOTAL.labels(method=method, endpoint=endpoint, status_code=str(status_code)).inc()
        HTTP_REQUEST_DURATION_SECONDS.labels(method=method, endpoint=endpoint).observe(duration_sec)

        stats_tracker.record_request(duration_sec)

        from app.core.config import settings

        slow_threshold = getattr(settings, "SLOW_REQUEST_THRESHOLD_SEC", 2.0)
        if duration_sec > slow_threshold:
            SLOW_REQUESTS_TOTAL.labels(method=method, endpoint=endpoint).inc()

        large_threshold = getattr(settings, "LARGE_RESPONSE_THRESHOLD_BYTES", 1024 * 1024)
        if response_size_bytes > large_threshold:
            LARGE_RESPONSES_TOTAL.labels(method=method, endpoint=endpoint).inc()

    def increment_active_requests(self):
        ACTIVE_REQUESTS.inc()

    def decrement_active_requests(self):
        ACTIVE_REQUESTS.dec()

    def get_active_requests(self) -> int:
        try:
            return int(ACTIVE_REQUESTS._value.get())
        except Exception:
            return 0

    def record_auth_success(self):
        AUTH_SUCCESS_TOTAL.inc()

    def record_auth_failure(self):
        AUTH_FAILURE_TOTAL.inc()

    def record_dashboard_generated(self, duration_sec: float):
        DASHBOARD_GENERATION_TOTAL.inc()
        DASHBOARD_GENERATION_DURATION_SECONDS.observe(duration_sec)

    def record_dataset_uploaded(self, duration_sec: float):
        DATASET_UPLOAD_TOTAL.inc()
        DATASET_PROCESSING_DURATION_SECONDS.observe(duration_sec)

    def record_ai_query(self, duration_sec: float):
        AI_QUERY_TOTAL.inc()

    def record_db_query(self, duration_sec: float):
        DB_QUERY_DURATION_SECONDS.observe(duration_sec)

    def record_cache_hit(self, cache_type: str):
        CACHE_HITS_TOTAL.labels(cache_type=cache_type).inc()

    def record_cache_miss(self, cache_type: str):
        CACHE_MISSES_TOTAL.labels(cache_type=cache_type).inc()

    def set_cache_memory(self, bytes_val: int):
        CACHE_MEMORY_USAGE_BYTES.set(bytes_val)

    def set_compression_ratio(self, ratio: float):
        COMPRESSION_RATIO.set(ratio)

    def record_nl2sql_query(self, latency_sec: float, confidence: float, blocked: bool = False, validation_failed: bool = False):
        NL2SQL_LATENCY_SECONDS.labels(operation="generate").observe(latency_sec)
        if blocked:
            NL2SQL_BLOCKED_QUERIES_TOTAL.inc()
        if validation_failed:
            NL2SQL_VALIDATION_FAILURES_TOTAL.inc()
        if not blocked and not validation_failed:
            NL2SQL_CONFIDENCE_SUM.inc(confidence)
            NL2SQL_CONFIDENCE_COUNT.inc()

    def record_ai_recommendation(self, latency_sec: float, confidence: float):
        AI_CLEANING_RECOMMENDATION_LATENCY.observe(latency_sec)
        AI_CLEANING_CONFIDENCE_SUM.inc(confidence)
        AI_CLEANING_CONFIDENCE_COUNT.inc()

    def record_ai_cleaning_execution(self, duration_sec: float, transformations: list):
        AI_CLEANING_EXECUTION_DURATION.observe(duration_sec)
        for tx in transformations:
            if tx:
                AI_CLEANING_TRANSFORMATIONS_TOTAL.labels(transformation=tx).inc()

    def record_ai_approval(self, status: str):
        AI_CLEANING_APPROVALS_TOTAL.labels(status=status).inc()

    def record_ai_rollback(self):
        AI_CLEANING_ROLLBACKS_TOTAL.inc()

    def record_rag_query(self, emb_latency: float, ret_latency: float, gen_latency: float, confidence: float, chunks_cnt: int, success: bool = True):
        RAG_EMBEDDING_LATENCY.observe(emb_latency)
        RAG_RETRIEVAL_LATENCY.observe(ret_latency)
        if gen_latency > 0:
            RAG_GENERATION_LATENCY.observe(gen_latency)
        RAG_CONFIDENCE_SUM.inc(confidence)
        RAG_CONFIDENCE_COUNT.inc()
        RAG_RETRIEVED_CHUNKS_SUM.inc(chunks_cnt)
        RAG_RETRIEVED_CHUNKS_COUNT.inc()
        status_lbl = "success" if success else "failure"
        RAG_QUERIES_TOTAL.labels(status=status_lbl).inc()

    def record_agent_execution(self, agent: str, latency_sec: float, success: bool = True):
        if agent:
            AGENT_LATENCY_SECONDS.labels(agent=agent).observe(latency_sec)
            if not success:
                AGENT_FAILURES_TOTAL.labels(agent=agent).inc()

    def record_critic_reject(self):
        CRITIC_REJECTS_TOTAL.inc()

    def record_xai_metrics(self, latency_sec: float, confidence: float, missing_citations: bool):
        XAI_EXPLANATION_LATENCY.observe(latency_sec)
        XAI_CONFIDENCE_SUM.inc(confidence)
        XAI_CONFIDENCE_COUNT.inc()
        if confidence < 50.0:
            XAI_LOW_CONFIDENCE_RESPONSES.inc()
        if missing_citations:
            XAI_MISSING_CITATIONS.inc()

    def record_report_generation(self, fmt: str, latency_sec: float, file_size_bytes: int):
        REPORT_GENERATION_DURATION.labels(format=fmt).observe(latency_sec)
        REPORT_SIZE_SUM.labels(format=fmt).inc(file_size_bytes)
        REPORT_SIZE_COUNT.labels(format=fmt).inc()

    def record_report_failure(self):
        REPORT_FAILURES_TOTAL.inc()

    def record_report_download(self):
        REPORT_DOWNLOADS_TOTAL.inc()

    def record_prompt_execution(self):
        PROMPT_EXECUTIONS_TOTAL.inc()

    def record_prompt_rollback(self):
        PROMPT_ROLLBACKS_TOTAL.inc()

    def record_active_model_change(self):
        MODEL_CHANGES_TOTAL.inc()

    def record_evaluation_run(self, duration_sec: float, score: float):
        EVALUATION_DURATION.observe(duration_sec)
        EVAL_SCORE_SUM.inc(score)
        EVAL_SCORE_COUNT.inc()

    def record_predictive_training_run(self, duration_sec: float, accuracy: float):
        PREDICTIVE_TRAINING_DURATION.observe(duration_sec)
        PREDICTIVE_MODEL_ACCURACY.set(accuracy)

    def record_predictive_inference(self, duration_sec: float):
        PREDICTIVE_PREDICTION_LATENCY.observe(duration_sec)

    def set_active_predictive_models(self, count: int):
        PREDICTIVE_ACTIVE_MODELS.set(count)

    def record_prescriptive_generation(self, duration_sec: float):
        PRESCRIPTIVE_RECOMMENDATION_LATENCY.observe(duration_sec)

    def record_workflow_prediction_execution(self):
        WORKFLOW_PREDICTION_EXECUTIONS.inc()

    def get_avg_response_time_ms(self) -> float:
        return stats_tracker.get_avg_response_time_ms()

    def get_total_requests(self) -> int:
        return stats_tracker.total_requests

    def record_streaming_event(self, stream_id: str):
        STREAMING_EVENTS_TOTAL.labels(stream_id=stream_id).inc()

    def record_streaming_latency(self, stream_id: str, latency_sec: float):
        STREAMING_PROCESSING_LATENCY.labels(stream_id=stream_id).observe(latency_sec)

    def set_active_streams(self, count: int):
        STREAMING_ACTIVE_STREAMS.set(count)

    def set_stream_queue_depth(self, stream_id: str, depth: int):
        STREAMING_QUEUE_DEPTH.labels(stream_id=stream_id).set(depth)

    def record_dropped_event(self, stream_id: str):
        STREAMING_DROPPED_EVENTS.labels(stream_id=stream_id).inc()

    def record_window_execution(self, stream_id: str, window_type: str, duration_sec: float):
        STREAMING_WINDOW_EXECUTION_TIME.labels(stream_id=stream_id, window_type=window_type).observe(duration_sec)

    def record_streaming_workflow_triggered(self, stream_id: str, trigger_reason: str):
        STREAMING_TRIGGERED_WORKFLOWS.labels(stream_id=stream_id, trigger_reason=trigger_reason).inc()

    def record_plugin_load(self, plugin: str, status: str):
        PLUGIN_LOADS_TOTAL.labels(plugin=plugin, status=status).inc()

    def record_plugin_execution(self, plugin: str, capability: str, duration_sec: float):
        PLUGIN_EXECUTION_DURATION_SECONDS.labels(plugin=plugin, capability=capability).observe(duration_sec)

    def record_plugin_error(self, plugin: str, error_type: str):
        PLUGIN_ERRORS_TOTAL.labels(plugin=plugin, error_type=error_type).inc()

    def record_plugin_usage(self, plugin: str):
        PLUGIN_USAGE_TOTAL.labels(plugin=plugin).inc()

    def set_cluster_worker_count(self, count: int):
        CLUSTER_WORKER_COUNT.set(count)

    def set_scheduler_queue_depth(self, depth: int):
        CLUSTER_QUEUE_DEPTH.set(depth)

    def record_worker_utilization(self, worker_id: str, cpu: float, mem: float):
        CLUSTER_WORKER_UTILIZATION.labels(worker_id=worker_id, resource_type="cpu").set(cpu)
        CLUSTER_WORKER_UTILIZATION.labels(worker_id=worker_id, resource_type="memory").set(mem)

    def record_cluster_task_latency(self, task_type: str, duration_sec: float):
        CLUSTER_TASK_LATENCY.labels(task_type=task_type).observe(duration_sec)

    def record_task_retry(self):
        CLUSTER_TASK_RETRIES.inc()

    def record_failover_event(self):
        CLUSTER_FAILOVER_EVENTS.inc()

    def record_scheduler_latency(self, duration_sec: float):
        CLUSTER_SCHEDULER_LATENCY.observe(duration_sec)


monitoring_service = MonitoringServiceWrapper()

