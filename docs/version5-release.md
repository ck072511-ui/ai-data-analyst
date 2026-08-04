# Version 5.0 Release & Operations Guide

This document details the configuration, deployment lifecycle, and monitoring configurations for the Version 5.0 Release Candidate 1 (RC1) platform.

---

## 📋 System Requirements

### Hardware Requirements
- **CPU**: 4 vCPUs (minimum), 8 vCPUs (recommended).
- **RAM**: 8 GB RAM (minimum), 16 GB RAM (recommended).
- **Storage**: 50 GB SSD storage.

### Software Dependencies
- **Container Engine**: Docker Engine 24.0.0+ / Docker Desktop.
- **Compose Tool**: Docker Compose V2.
- **Local LLM API**: Ollama service running locally (for fully offline setups).

---

## 🚀 One-Command Deployment

We provide pre-packaged scripts and configuration profiles for single-command start:

### 1. Configure Secrets & Keys
Create a local `.env` file copying the variables template:
```bash
cp .env.example .env
```
Ensure that you set:
- `SECRET_KEY`: Set a cryptographically secure 32-character string.
- `DB_ENCRYPTION_KEY`: A 32 URL-safe base64 key to secure connection credentials.
- `ENVIRONMENT`: Set to `production` or `development`.

### 2. Startup Stack
- **Windows**:
  ```cmd
  .\scripts\run.bat
  ```
- **Linux/macOS**:
  ```bash
  docker compose -f docker-compose.prod.yml up --build -d
  ```

### 3. Verification
Verify active container states:
```bash
docker compose -f docker-compose.prod.yml ps
```
And check Nginx routing logs:
```bash
docker compose -f docker-compose.prod.yml logs -f nginx
```

---

## 💾 Backups & Restore Pipelines

Version 5.0 includes auto-detecting backup and restoration tools inside `scripts/`:

### 1. Database Backups
- **Windows**:
  ```cmd
  .\scripts\backup_database.bat
  ```
- **Linux/macOS**:
  ```bash
  ./scripts/backup_database.sh
  ```
  *Saves backup snapshot to*: `backups/postgres_backup_YYYYMMDD_HHMMSS.sql.gz`

### 2. Database Restoration
- **Windows**:
  ```cmd
  .\scripts\restore_database.bat .\backups\postgres_backup_file.sql
  ```
- **Linux/macOS**:
  ```bash
  ./scripts/restore_database.sh ./backups/postgres_backup_file.sql.gz
  ```

---

## 📊 Telemetry & Performance Monitoring

### Prometheus Metrics
Exposed at `/metrics` from the backend service:
- `cluster_worker_count`: Active cluster nodes.
- `cluster_queue_depth`: Jobs queue backlog length.
- `cluster_worker_utilization`: Core node CPU/RAM loads.
- `slow_queries_total`: Database slow SELECT query logs.

### Grafana Dashboard
Access the visual dashboard at `http://localhost:3001` (Default credentials: `admin` / `admin`). Includes preconfigured layout charts monitoring memory usage, request counts, queue latency, and cluster node distributions.
