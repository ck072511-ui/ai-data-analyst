# Release Notes - AI Data Analyst Enterprise Version 5.0 (RC1)

We are proud to announce the Release Candidate 1 (RC1) of the AI Data Analyst Enterprise Platform (Version 5.0). This release is designed for production deployment audits, performance optimization, and stability auditing.

---

## 🚀 Version 5.0 Highlights

### 1. Extensible Plugin & Custom Tools SDK
Software engineers can now build, publish, and load custom analytics nodes, database connectors, and visual panels completely offline. The built-in Plugin Manager coordinates dependencies verification, version upgrades, and sandboxed run bounds.

### 2. Distributed Task Scheduler & Worker Cluster
To support large enterprise workloads, the platform introduces a distributed scheduler. Task loads are dynamically balanced using a Least Connection strategy across active worker nodes (with auto-detecting failover queues and local fallback resilience).

### 3. Multi-Agent Planning & Critic Validation
Leverages cooperative LLM nodes (Planners, SQL Builders, Visualizers, and Critics) to automatically check database schema mappings, verify generated SQL, and format data dashboards without manual user corrections.

### 4. Real-Time Streaming Ingestion
Allows operators to configure watch directories, REST endpoints, and websocket channels to parse incoming events in real-time, executing sliding window aggregate formulas and triggering workflow tasks.

---

## 🛡️ Stability, Hardening & Security
- **Sliding JWT Sessions**: Secured refresh token rotators, password complexity checks, and account lockout rate limiters.
- **Enterprise-Grade Nginx Proxy**: Preconfigured SSL configurations, body upload limits (50MB), and security header policies.
- **Auto-Detect Backups**: Shell/batch utilities auto-detect running Docker containers for zero-downtime PostgreSQL dumps.

---

## ⚠️ Compatibility & Migration Notes
- **100% Backward Compatible**: Preserves all existing SQLite/PostgreSQL metadata schemas and user uploaded files footprints.
- **Offline Configuration**: Ensure local Ollama instances have downloaded the default required model classes before launching.
