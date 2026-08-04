# Platform Performance & Load Testing Guide

This guide details the procedures for executing load tests, running benchmark runs, analyzing system limits, and optimizing performance across the AI Data Analyst platform.

---

## 📈 Performance SLAs & Targets

| Target Metric | SLA Target | Description |
| :--- | :--- | :--- |
| **API P95 Latency** | <= 200 ms | P95 duration for all core REST API endpoints. |
| **API P99 Latency** | <= 500 ms | P99 latency bounds for API responses. |
| **Dashboard Gen Time** | <= 5.0 s | Heuristics and KPI rendering calculation duration. |
| **Dataset Upload Time** | <= 10.0 s | Parsing, validation, and database load for flat datasets up to 50MB. |
| **Background Task Time** | <= 30.0 s | Celery/Local thread async task processing limit. |
| **Cache Hit Percentage** | >= 80% | Percentage of request lookups served via Redis/OrderedDict. |
| **Request Error Rate** | <= 1.0% | Tolerable percentage of failed requests under load. |

---

## 🚀 Running k6 Load Tests

k6 is a developer-centric, scriptable load testing tool.

### Prerequisites
Install k6 globally:
*   **macOS**: `brew install k6`
*   **Windows**: `winget install gnu.k6` or download binary.
*   **Linux**: Follow official installation guides.

### Executing k6 Scenarios
Run the k6 test script from the repository workspace root:
```bash
# Run with default 5 virtual users for 20 seconds
k6 run load-tests/k6/load_test.js

# Override virtual users (VUs) dynamically
k6 run -e VUS=25 load-tests/k6/load_test.js
```

---

## 🌾 Running Locust Journeys

Locust is a Python-based user journey load testing tool.

### Prerequisites
Install Locust:
```bash
pip install locust
```

### Executing Locust Journeys
Run Locust from the workspace root:
```bash
# Start Locust in web console mode
locust -f load-tests/locust/locustfile.py

# Access the interface in your browser
# Open: http://localhost:8089
```

---

## 📊 Automated Benchmark Suite

We provide a lightweight, standard library-only benchmarking suite that measures inline system latencies, requests per second, CPU, and Memory usage.

### Execution
Run the benchmark script from the workspace root:
```bash
python load-tests/benchmark_suite.py
```
*Result*: Generates a JSON summary at `load-tests/reports/performance_results.json` and a Markdown summary at `load-tests/reports/benchmark_report.md`.

---

## 🔧 Performance Tuning Guide

### 1. Database Indexing
Ensure that SQLAlchemy models have correct index bindings:
*   *Audit Logs*: Index the `timestamp` column.
*   *User Sessions*: Index the `session_id` and `user_id` columns.

### 2. Caching Strategy
*   Set the Redis database memory boundaries:
    ```conf
    maxmemory 512mb
    maxmemory-policy allkeys-lru
    ```
*   Ensure cache key prefixes partition custom datasets.

### 3. Celery Concurrency Tuning
*   In production, scale workers to match vCPUs:
    ```bash
    celery -A app.core.celery_app worker --loglevel=info --concurrency=4
    ```
