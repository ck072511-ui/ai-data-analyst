# 🤖 AI Data Analyst - Enterprise Analytics Platform

[![Build Status](https://github.com/DELL/ai-data-analyst/actions/workflows/full-ci.yml/badge.svg)](https://github.com/DELL/ai-data-analyst/actions/workflows/full-ci.yml)
[![Tests Status](https://img.shields.io/badge/tests-49%20passed-green.svg)](https://github.com/DELL/ai-data-analyst/actions/workflows/full-ci.yml)
[![Coverage](https://img.shields.io/badge/coverage-70%25-brightgreen.svg)](https://github.com/DELL/ai-data-analyst/actions/workflows/full-ci.yml)
[![Security Scan](https://img.shields.io/badge/security-bandit-green.svg)](https://github.com/DELL/ai-data-analyst/actions/workflows/full-ci.yml)
[![Docker Validation](https://img.shields.io/badge/docker-validated-blue.svg)](https://github.com/DELL/ai-data-analyst/actions/workflows/full-ci.yml)

## 📋 Project Overview
This project converts natural language questions into SQL queries, interactive dashboards, and business insights. It supports flat dataset uploads and secure connections to enterprise databases.

## ✨ Features
- **Enterprise AI Copilot**: Unified conversational interface acting as the central hub of the platform. Detects user intents across 13 platform domains, orchestrates multi-step task execution sequences offline, compiles detailed execution timeline traces (module routing, order, processing latency, and limitations) with complete tool transparency, and auto-generates visual DAG workflow configs from chat history.
- **Enterprise Predictive & Prescriptive Analytics Platform**: Automatically discovers prediction targets, preprocesses features datasets, runs 3-Fold cross-validation grid hyperparameter searches offline, trains custom NumPy ML models (Classification, Regression, Forecasting, Clustering), and saves details in the Model Registry. Prescribes optimal actions using what-if simulation permutations, ranking outputs based on business rule validations. Integrates predictive/prescriptive engines natively into copilot triggers and visual workflow nodes.
- **Enterprise Federated Multi-Database Query Engine**: Query multiple heterogeneous database engines (PostgreSQL, MySQL, SQLite) using unified natural language prompts completely offline. Decomposes prompts into parallel subqueries, and runs in-memory Pandas joins/unions, yielding combined results datasets with partial failure resilience controls.
- **Enterprise Knowledge Graph & Semantic Layer**: Automatically discovers entities (datasets, tables, columns, business glossary terms, RAG documents, reports, and workflows) and relationships (foreign keys, lineage, mappings, references, and dependencies). Enables semantic search by mapping user keywords to resolved synonyms (e.g. turnover ➔ revenue) and displays visual upstream lineages and downstream change-impact pathways.
- **Enterprise Visual AI Workflows & Automation**: Drag-and-drop canvas workspace to construct and execute complex analytical pipelines (comprising dataset upload, data profiling, data cleaning, SQL query, RAG query, Multi-Agent Analysis, Explainability, Report Generation, notifications, exports). Configures node timeout limits, error retries, conditional branches (IF/ELSE, SWITCH), loops, scheduled recurrence cron timers, and visual timeline monitoring.
- **Natural Language to SQL Engine**: Fully-secure local analytical engine parsing plain English into valid SQL queries (PostgreSQL, MySQL, SQLite) utilizing schema intelligence, SQL validation planners, automatic optimizers, safety filters, and conversation thread memories.
- **Enterprise Database Connectivity**: Connect securely to PostgreSQL, MySQL, and SQLite instances.
- **Enterprise Data Quality Detection Engine**: Automatically inspects uploaded datasets, computes comprehensive numeric stats (median, mode, variance, quartiles), generates Pearson correlation heatmaps, detects outliers (IQR and Z-score methods), identifies inconsistent date/email/phone formats, provides sample duplicate rows, and scores quality using a premium visual scorecard.
- **Enterprise Prompt, Evaluation, and Model Registry Suite**: Offline LLM orchestration platform. Features prompt templates libraries, placeholder validation, authors version logs, version difference comparisons, prompt rollbacks, Ollama model registries activations, A/B side-by-side model execution comparisons, and batch evaluation benchmarks (scores 0-100 on answer relevance, SQL correctness, citations, and latency metrics).
- **Enterprise AI Report Generation System**: Offline document compiler generating professional, print-ready reports in PDF (ReportLab), editable Word documents (python-docx), and PowerPoint presentations (python-pptx). Features dynamic Matplotlib chart embedding, corporate branding options (company name, version), automated KPI tables, RAG citation appendixes, and async background processing queues.
- **Enterprise Explainable AI (XAI) & Confidence Engine**: Post-execution explanation pipeline decoding SQL complexity, referenced tables/columns, RAG unique documents cited, and Multi-Agent planning timeline paths. Evaluates system confidence ratings (High/Medium/Low) using a weighted formula (SQL validation, schema match, citation coverage, agent agreement, data completeness) without exposing Chain-of-Thought logs.
- **Enterprise Multi-Agent Analytics System**: Collaborative offline analytics system powered by local LLMs. Coordinates specialized agents—Planner, Schema, SQL, RAG, Visualization, Insight, and Critic—via a shared memory architecture and Critic-led recovery planning loops to solve complex business queries safely and privately.
- **Enterprise Retrieval-Augmented Generation (RAG) System**: A fully-secure, offline document Q&A engine. Ingests PDFs, DOCX, TXTs, Markdown, and CSVs. Automatically splits, embeds (SentenceTransformers), indexes (FAISS/ChromaDB), and ranks chunks (hybrid dense-lexical ranking). Features schema dictionary grounding, citations tracing, and multi-turn chat memory.
- **Enterprise AI Data Cleaning & Transformation Assistant**: Fully-secure offline cleaning recommendations and dataset transformations powered by local LLMs. Formulates quality explanations, suggests missing values imputations, categorical encoding (One-Hot/Label), scaling methods, quantile bucketing, and feature extractions with checklist-based user approvals and 100% rollback compatibility.
- **Enterprise Auto Cleaning Engine**: Granular manual and auto cleaning workflows allowing users to impute missing values (mean, median, mode, constant, ffill, bfill, drop), trim spaces, remove duplicate rows and duplicate columns, cap outliers (Winsorization), normalize null-like text types, and standardize date/email/phone formats, featuring a detailed Preview Report dashboard before applying changes.
- **AI Recommendation Engine**: Rule-based intelligence engine analyzing data profiles to suggest confidence-scored (0-100) clean steps (e.g. drop columns with >30% nulls, median imputation, standardization, deduplication) that auto-populate manual configurations.
- **Automatic Dataset Versioning**: Snapshot isolations mapping dataset updates to version counters (V1, V2, V3, etc.) on disk and isolated SQL tables without data overrides.
- **Active Rollback & Restore**: Restores previous dataset versions dynamically in the schema catalog from the snapshots history panel.
- **Enterprise Production Hardening & Disaster Recovery Suite**: Preparation for release candidate environments. Features secure payloads (100MB body limits), CORS, CSP, and HSTS headers, automated `/health`, `/ready`, and `/live` health check metrics, offline SQLite and registry snapshots backup/restores, and automated startup readiness checkers.
- **Timeline Cleaning Audit Log**: Logs timestamps, change lists, row/column delta changes, and data quality scorecard progressions (Score Before ➔ Score After) in a visual timeline stream.
- **Enterprise AI Insights Engine**: A rule-based diagnostic engine generating dataset quality summaries (missingness, duplicate impact, outliers, and high correlation warnings), business recommendations with confidence ratings and severity badges (Critical, High, Medium, Low), and explanations detailing what changed, why it changed, the business impact, and expected improvements for all applied data cleaning operations.
- **AI Insights APIs**: Dedicated endpoints `GET /api/v1/datasets/{id}/insights` and `GET /api/v1/datasets/{id}/health` delivering dataset health indices, risk listings, strengths, and weaknesses.
- **Enterprise Natural Language Dashboard Generator**: Auto-compiles SQL query results and raw dataset schemas into structured React layouts with auto-calculated numeric KPI cards (Total, Average, Max, Min, Median, Unique values, and Null percentages) and smart visualization type routing (Time Series ➔ Line, Category ➔ Bar, Ranking ➔ Horizontal Bar, Distribution ➔ Histogram, Relationship ➔ Scatter, Part-to-Whole ➔ Pie/Donut).
- **Dashboard Interactive Tools & History logs**: Supports client-side legend toggling, zoom in/out boundaries, pan scrolling, fullscreen viewports, direct canvas-to-PNG downloads, and dashboard layout history retrieval to save and reopen previous layouts.
- **Credential Encryption**: Encrypt stored passwords securely using Fernet symmetric encryption.
- **Dynamic Schema Discovery**: Automatically inspect table lists, columns, data types, and nullability properties.
- **User-Uploaded Datasets**: Upload CSV, Excel (.xlsx, .xls), and JSON files up to 50MB with automatic schema mapping and statistics generation.
- **Interactive Visualizations**: Dynamic Chart.js visualizations (bar, line, pie, scatter) automatically selected based on query metrics.
- **Export Reports**: Export outputs to Excel and PDF formats.
- **User Authentication**: Secure JWT-based registration and login flows.
- **Enterprise Role-Based Access Control (RBAC)**: Fine-grained authorization checks protecting APIs and UI interfaces based on roles: Admin, Data Scientist, Data Analyst, and Viewer. Dynamically fetches role definitions from the database on every request to prevent privilege escalation, logging all access decisions to a secure `system_audit_logs` schema.
- **Production Security Shield**: Hardened security featuring JWT Refresh Token Rotation, user sessions management (list and terminate active device contexts), temporary brute-force lockout protection (15-min lock after 5 failures), sliding window in-memory rate limiting for authentication routes, strong password policies, and security headers middleware injection (CSP, HSTS, X-Content-Type-Options, etc.).
- **Local LLM Framework Integration**: Run multiple offline language models (Llama 3, Qwen, Mistral, Phi) locally through Ollama, with automated model discovery, dynamic hot-swapping, and real-time streaming preview.
- **Enterprise Real-Time Streaming Analytics Platform**: Continuous event ingestion, buffering, and routing engine with backpressure controls (Block, Drop Oldest, Drop Newest). Supports Tumbling, Sliding, and Session windows, with standard operations (Count, Sum, Avg, Min, Max, Distinct Count, and Custom aggregations). Computes running KPIs, statistical z-score anomalies, static thresholds, and alerts linked to automatic workflow actions and incremental Knowledge Graph updates.

## 🛠️ Tech Stack
- **Backend**: FastAPI, PostgreSQL/SQLite, SQLAlchemy, Pandas, Cryptography, HTTPX
- **AI**: 100% Local Offline LLMs via Ollama, llama.cpp, vLLM, LM Studio, Hugging Face Local (placeholders)
- **Frontend**: React, Chart.js, Vanilla CSS
- **Deployment**: Docker, docker-compose

## 🚀 Quick Start

### Prerequisites
- Python 3.11+
- Node.js 18+

### Setup
```bash
# Clone and setup project dependencies
cd ai-data-analyst
./scripts/setup.bat
```

### Run
```bash
./scripts/run.bat
```

## 🔌 Connection Setup Examples

### 🐚 SQLite Connection
- **Database Type**: `SQLite`
- **File Path**: `backend/data/temp_test_remote.db` or relative folder paths.

### 🐘 PostgreSQL Connection
- **Host**: `localhost` (or server ip)
- **Port**: `5432`
- **Database**: `analytics_db`
- **Username**: `postgres`
- **Password**: `YourPassword`

### 🐬 MySQL Connection
- **Host**: `localhost` (or server ip)
- **Port**: `3306`
- **Database**: `company_sales`
- **Username**: `root`
- **Password**: `YourPassword`

## 📡 API Documentation
Access FastAPI auto-documentation at: [http://localhost:8000/docs](http://localhost:8000/docs)

## 💬 How It Works
1. **Context Selection**: Select a custom uploaded dataset or an enterprise connected database. Uploading a flat dataset automatically triggers the backend profiling engine to generate memory, type distribution, and data quality diagnostics.
2. **Schema Ingest**: The backend extracts column mappings and structures to build LLM prompt context.
3. **NL2SQL Query**: The AI parses user questions and translates them into an optimized SQL query.
4. **Security Check**: The SQL validator inspects the statements to prevent lateral table access or SQL injections.
5. **Dynamic Run**: Executes against the target engine, maps Chart.js arrays, and explains the visual trends.

## 🏥 Enterprise Observability & Monitoring
The platform is instrumented with enterprise-grade observability utilizing Prometheus, Grafana, and structured JSON logs.

### Features
- **Prometheus Metrics**: Exposes `GET /metrics` reporting HTTP request metrics (counters, histogram latencies, active requests) and business indicators (auth events, dashboard generation, dataset uploads, CPU/Memory footprint).
- **Structured JSON Logging**: Every log is formatted as a single-line JSON string containing request ID tracing (`X-Request-ID`), user ID, IP address, endpoints, and execution latency.
- **Diagnostics Health Checks**: Exposes `/health`, `/health/live`, and `/health/ready` to check database pool connectivity, storage write availability, authentication table access, and Redis cache health.
- **React System Health Panel**: Renders active requests, response latencies, and component statuses. Auto-refreshes every 30 seconds.

### How to Run Prometheus & Grafana
To spin up the optional observability stack:
1. Ensure Docker and Docker Compose are installed.
2. Start the application with the monitoring services:
   ```bash
   docker-compose up --build -d
   ```
   *Note: The application continues to run normally even if these services are stopped.*
3. **Access Prometheus**: Open [http://localhost:9090](http://localhost:9090) in your browser.
4. **Access Grafana Dashboards**: 
   - Open [http://localhost:3001](http://localhost:3001) in your browser.
   - Default login is `admin` / `admin`.
   - The **AI Data Analyst - Observability & Monitoring** dashboard is pre-provisioned and automatically loaded with live panels.

## ⚙️ Asynchronous Background Processing (Celery & Redis)
The platform features an SRE-grade asynchronous task execution engine to handle long-running operations (profiling datasets, auto cleaning, dashboard generation, and AI insight generations) without blocking the FastAPI event loop.

### Features
- **Task Delegation**: Heavy requests immediately trigger task scheduling and return a `task_id` response to the client.
- **Worker Management**: Distributed worker queueing via Celery backed by Redis broker.
- **SRE-Grade Graceful Fallbacks**: If Celery or Redis is offline, the task service automatically detects this and falls back to run the task asynchronously on a local thread pool runner so that the application maintains full usability.
- **Task Center Console**: React panel displaying real-time worker states, progress meters, task cancel buttons, and rerun retries.
- **Real-Time Toasts**: Toast notification polls report start, success, and error outcomes dynamically.

### How to Run background workers
1. Start the complete application including Redis broker and Celery worker:
   ```bash
   docker-compose up --build -d
   ```
2. Inspect worker state and backlog metrics directly from the **Task Center** tab in the sidebar console.

## ⚡ Performance Optimization, Caching & Compression
The platform implements an enterprise performance suite featuring Redis caching, automatic cache invalidations, ASGI Gzip compression, database index optimizations, and a performance telemetry console.

### Key Components
- **Redis & Local LRU Cache (`cache_service.py`)**: Centralizes cache operations with Redis. Fallback to a size-bounded, thread-safe local OrderedDict LRU cache occurs automatically if Redis is unavailable.
- **ASGI GZip Compression (`compression_service.py`)**: Compresses API responses dynamically, reducing network bandwidth usage and accelerating overall page load times.
- **SQLAlchemy Event Tracing (`database.py`)**: Intercepts queries at cursor execution to track database query time and automatically registers slow queries exceeding 100ms.
- **Enterprise Pagination (`pagination.py`)**: Implements reusable offset pagination with sorting, case-insensitive string searches, and total pages metadata. Flat-list fallback maintains backward compatibility.
- **Performance Console**: Displays cache hit rate, response time progression, compression savings, and slow database queries in real-time.

### Running with Redis caching
1. Boot the application using docker-compose to launch the Redis cache broker automatically:
   ```bash
   docker-compose up --build -d
   ```
2. Navigate to the **Performance** tab in the top navigation bar to monitor live performance stats.

### 📈 Load Testing & Benchmarks
We support automated concurrent load testing and metrics validation using k6, Locust, and inline standard-library benchmark runs. See the [Platform Performance & Load Testing Guide](file:///c:/Users/DELL/OneDrive/ai-data-analyst/docs/performance.md) for full commands and parameters.


## 🚀 Production Deployment

For production deployments, the stack is hardened using security configurations, Nginx reverse proxying, isolated container networking, and PostgreSQL volume bindings.

To launch the production stack:
```bash
docker compose -f docker-compose.prod.yml up --build -d
```

For complete instructions regarding system requirements, SSL certificate provisioning, backups, restores, upgrades, and rollback strategies, see the [Enterprise Production Deployment Guide](file:///c:/Users/DELL/OneDrive/ai-data-analyst/docs/deployment.md).

For the packages upgrade log, dependencies constraints, and resolved vulnerabilities list, see the [Dependencies Modernization & Security Compliance Manual](file:///c:/Users/DELL/OneDrive/ai-data-analyst/docs/dependency-upgrade.md) and the [CHANGELOG.md](file:///c:/Users/DELL/OneDrive/ai-data-analyst/CHANGELOG.md).

## 🔌 Plugin Extension SDK & Marketplace
The platform supports custom functional extension plugins running completely offline. For architecture specifications, development tutorials, and marketplace usage details, consult the following manuals:
- [Plugin SDK Specifications Guide](file:///c:/Users/DELL/OneDrive/ai-data-analyst/docs/plugin-sdk.md)
- [Plugin Development Tutorial](file:///c:/Users/DELL/OneDrive/ai-data-analyst/docs/plugin-development.md)
- [Local Plugin Marketplace Guide](file:///c:/Users/DELL/OneDrive/ai-data-analyst/docs/plugin-marketplace.md)


