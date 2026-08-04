# Changelog - Version 5.0 (Release Candidate 1)

All notable changes and additions introduced in the Version 5.0 release of the AI Data Analyst Enterprise Platform.

---

## [5.0.0-rc1] - 2026-08-01

### Added
- **Plugin & Extension SDK**: Exposes interfaces forDataSourcePlugin, WorkflowNodePlugin, Visualizations, and custom AI tools. Includes JSON catalog registry (`registry.json`) and rollbacks capability.
- **Distributed Execution & Cluster Platform**: Extends the workflow execution engine with worker registrations, heartbeats tracking, least connection scheduler queues, priority weight allocations, failover reassignment, and automatic local fallback loops.
- **Streaming Ingestion Adapters**: Implemented tailer adapters for watch directories, websockets streams, push REST feeds, CSV tails, and JSON lines.
- **RAG Multi-Source Ingest**: Offline ingestion pipelines parsing PDF, DOCX, TXT, and Markdown files into local vector indexes.
- **Multi-Agent Critic Loop**: Collaborative orchestration timeline using Critic feedback loops to self-correct SQL joins and chart recommendations.
- **Explainable AI (XAI)**: Visual dashboard compiling trust ratings, citations lookups, and programmatic SQL breakdown explanations.
- **Prometheus Telemetry**: Added gauges monitoring queue depths, worker status, cache hit rates, and database slow queries.
- **Auto-Detect Scripts**: Upgraded backups and restoration shell/batch files to dynamically find running development or production Docker containers.

### Changed
- **Workflow Engine Polling**: Optimized polling frequency from 200ms to 50ms inside node executors to minimize queue runtimes.
- **Scheduler Double-Check Lock**: Integrated a pre-lock queue check in `distributed_scheduler.py` to prevent CPU lock contention when the job queue is empty.
- **Nginx Hardening**: Increased client upload body limit sizes to 50MB and secured headers inside Nginx proxy routing templates.
- **Ollama Offline Models Registry**: Restricted AI Copilot models discovery calls to run 100% locally.

### Fixed
- **React Warning Triggers**: Fixed unused variables and missing hook dependency array ESLint warnings in `DatabaseConnections.jsx`, `WorkflowBuilder.jsx`, and `WorkflowExecution.jsx`.
- **Worker Execution Fallbacks**: Resolved execution failures when Celery brokers are offline by automatically falling back to synchronous local executors.
