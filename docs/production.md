# Enterprise Production Operations Guide

This guide details configuration settings, sizing metrics, memory layouts, and health check architectures.

---

## ⚙️ Configuration Profile

Settings profiles are handled via [production.py](file:///c:/Users/DELL/OneDrive/ai-data-analyst/backend/app/core/production.py). Enforce the following env variables:
```bash
ENVIRONMENT=production
SECRET_KEY=secure-unique-uuid-key
DATABASE_URL=sqlite:///./prod_analytics.db
MAX_FILE_SIZE_MB=100
```

---

## 🩺 System Health Audits

The system exposes REST health endpoints to facilitate load balancers and orchestrator queries:

1. **Liveness**: `/live` (Fast process status check)
2. **Readiness**: `/ready` (Checks database ping, vector directories permissions, local model connectivity, and disk partitions spaces)
3. **Overall Health**: `/health` (Deep health check status)

---

## 💾 Backups & Disaster Recovery

Backups snapshot files containing active database, prompt libraries, and model registries are stored in `./database_backups`.
- Run backup trigger: `POST /api/v1/backups`
- Verify backup directory archive: `POST /api/v1/backups/verify`
