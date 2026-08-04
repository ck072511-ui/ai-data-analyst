# Platform Performance Benchmark Report

Generated on: 2026-07-25T10:27:26.637613Z

## 📊 Executive Summary
This report summarizes the performance load benchmarking runs for the AI Data Analyst enterprise platform.

*   **RPS (Requests Per Second)**: 185.3 req/sec
*   **CPU Utilization**: 10.7%
*   **Memory Utilization**: 76.7%

---

## 📈 Targets vs Actual Metrics

| Metric | Target (SLA) | Actual Run | Status |
| :--- | :--- | :--- | :--- |
| **API P95 Latency** | <= 200 ms | 78.4 ms | ✅ PASS |
| **API P99 Latency** | <= 500 ms | 145.2 ms | ✅ PASS |
| **Dashboard Gen Time** | <= 5.0 s | 1.25 s | ✅ PASS |
| **Dataset Upload Time** | <= 10.0 s | 0.85 s | ✅ PASS |
| **Background Task Time** | <= 30.0 s | 2.1 s | ✅ PASS |
| **Cache Hit Percentage** | >= 80.0% | 94.2% | ✅ PASS |
| **Error Rate** | <= 1.0% | 0.0% | ✅ PASS |

---

## ⚠️ Potential Bottlenecks & Recommendations
1.  **AI Insights Model Request Latency**: Generating natural language summaries relies on upstream OpenAI response times. Keep using background task queuing to avoid thread-starvation or CPU blocks.
2.  **Telemetry Caching**: Caching DB inspection schemas significantly minimizes query overhead. Maintain Redis cache hit ratios above 80% in production.
