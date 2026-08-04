# Enterprise Production Deployment Guide

This guide details the requirements, procedures, and utilities for deploying, maintaining, and recovering the AI Data Analyst platform in production.

---

## 📋 System Requirements

### Hardware Requirements
*   **CPU**: 4 vCPUs or equivalent core processors (minimum), 8 vCPUs (recommended).
*   **RAM**: 8 GB RAM (minimum), 16 GB RAM (recommended).
*   **Storage**: 50 GB SSD storage (plus dynamic space based on user uploads footprint).

### Software Requirements
*   **Operating System**: Linux (Ubuntu 22.04 LTS, Debian 12, RHEL 9 recommended) or Windows Server 2022.
*   **Container Engine**: Docker Engine 24.0.0+ / Docker Desktop.
*   **Compose Tool**: Docker Compose V2.

---

## 🚀 Installation & First-Time Setup

1.  **Clone the Repository**:
    ```bash
    git clone https://github.com/your-org/ai-data-analyst.git
    cd ai-data-analyst
    ```

2.  **Configure Environment Secrets**:
    Copy the production template and edit the values:
    ```bash
    cp .env.example .env
    nano .env
    ```
    Ensure that you configure:
    *   `ENVIRONMENT=production`
    *   `SECRET_KEY`: Set a cryptographically secure 32-character string.
    *   `DB_ENCRYPTION_KEY`: A 32 URL-safe base64-encoded key used to encrypt remote database passwords.

3.  **Create Docker Named Volumes**:
    Docker creates these automatically on container startup, but you can pre-provision them if required:
    ```bash
    docker volume create ai_analyst_postgres_prod_data
    docker volume create ai_analyst_redis_prod_data
    docker volume create ai_analyst_uploads_prod_data
    docker volume create ai_analyst_ssl_certs_data
    docker volume create ai_analyst_prometheus_prod_data
    docker volume create ai_analyst_grafana_prod_data
    ```

---

## 🛠️ Production Deployment Commands

We use `docker-compose.prod.yml` to orchestrate all services in production.

### Start the Stack (Background daemon)
```bash
docker compose -f docker-compose.prod.yml up --build -d
```

### Stop the Stack
```bash
docker compose -f docker-compose.prod.yml down
```

### View Live Container Status
```bash
docker compose -f docker-compose.prod.yml ps
```

### Inspect Live Logs
```bash
# View all container logs
docker compose -f docker-compose.prod.yml logs -f

# View specific service logs (e.g. backend API)
docker compose -f docker-compose.prod.yml logs -f backend
```

---

## 🔒 SSL/TLS Configuration (Certbot & Nginx)

To enable secure HTTPS traffic in production using Certbot and Let's Encrypt:

1.  **Install Certbot on Host**:
    ```bash
    sudo apt update
    sudo apt install certbot -y
    ```

2.  **Obtain Certificates via Webroot or Standalone Mode**:
    Temporarily stop Nginx container if port 80 is occupied:
    ```bash
    docker compose -f docker-compose.prod.yml stop nginx
    sudo certbot certonly --standalone -d yourdomain.com
    ```

3.  **Map Certificates to Nginx volume**:
    The default Let's Encrypt directory is `/etc/letsencrypt/live/yourdomain.com/`. We link these files into our Nginx container by mounting the SSL volume.
    Copy the certificates to the Docker volume path or adjust `docker-compose.prod.yml` volume mapping for `ssl_certs_data` to map directly to the host path:
    ```yaml
      nginx:
        # ...
        volumes:
          - ./nginx/nginx.conf:/etc/nginx/nginx.conf:ro
          - /etc/letsencrypt:/etc/nginx/ssl:ro
    ```

4.  **Update Nginx configuration**:
    Uncomment SSL settings in `nginx/nginx.conf` to listen on port `443` using the mapped certificates:
    ```nginx
    server {
        listen 443 ssl;
        server_name yourdomain.com;

        ssl_certificate /etc/nginx/ssl/live/yourdomain.com/fullchain.pem;
        ssl_certificate_key /etc/nginx/ssl/live/yourdomain.com/privkey.pem;

        # Add SSL protocols & ciphers...
    }
    ```
    Restart the Nginx container:
    ```bash
    docker compose -f docker-compose.prod.yml start nginx
    ```

---

## 💾 Backup Procedure

Automated backup scripts are located in `scripts/`. They extract data directly from running container namespaces.

### 1. Database Backup
*   **Linux/macOS**:
    ```bash
    ./scripts/backup_database.sh
    ```
*   **Windows**:
    ```cmd
    .\scripts\backup_database.bat
    ```
    *Result*: Saves a compressed gzip database backup to `backups/postgres_backup_YYYYMMDD_HHMMSS.sql.gz`.

### 2. User Uploads Backup
*   **Linux/macOS**:
    ```bash
    ./scripts/backup_uploads.sh
    ```
*   **Windows**:
    ```cmd
    .\scripts\backup_uploads.bat
    ```
    *Result*: Saves a compressed tarball containing uploaded user datasets to `backups/uploads_backup_YYYYMMDD_HHMMSS.tar.gz`.

---

## 🔄 Restore Procedure

Restore scripts take backup file paths as inputs.

### 1. Database Restore
*   **Linux/macOS**:
    ```bash
    ./scripts/restore_database.sh ./backups/postgres_backup_YYYYMMDD_HHMMSS.sql.gz
    ```
*   **Windows** (restores from standard sql files):
    ```cmd
    .\scripts\restore_database.bat .\backups\postgres_backup_YYYYMMDD_HHMMSS.sql
    ```

### 2. User Uploads Restore
*   **Linux/macOS**:
    ```bash
    ./scripts/restore_uploads.sh ./backups/uploads_backup_YYYYMMDD_HHMMSS.tar.gz
    ```
*   **Windows**:
    ```cmd
    .\scripts\restore_uploads.bat .\backups\uploads_backup_YYYYMMDD_HHMMSS.tar.gz
    ```

---

## 🆙 Upgrades & Rollbacks

### Upgrade Procedure
To release updates without downtime or data corruption:
1.  **Fetch Code updates**:
    ```bash
    git pull origin main
    ```
2.  **Backup current database and uploads (Critical)**:
    ```bash
    ./scripts/backup_database.sh
    ./scripts/backup_uploads.sh
    ```
3.  **Rebuild and spin up new containers**:
    ```bash
    docker compose -f docker-compose.prod.yml up --build -d
    ```
    FastAPI will automatically execute Alembic migration scripts on startup to update Postgres schemas.

### Rollback Procedure
If the upgrade introduces critical failures:
1.  **Revert git pointer**:
    ```bash
    git checkout <previous_stable_commit_hash>
    ```
2.  **Rebuild previous container images**:
    ```bash
    docker compose -f docker-compose.prod.yml up --build -d
    ```
3.  **Restore database schemas and uploads if the database schema was modified**:
    ```bash
    ./scripts/restore_database.sh ./backups/postgres_backup_pre_upgrade.sql.gz
    ./scripts/restore_uploads.sh ./backups/uploads_backup_pre_upgrade.tar.gz
    ```

---

## 🔍 Troubleshooting

### Container Health Failures
*   Check container health status:
    ```bash
    docker inspect --format='{{json .State.Health}}' ai_analyst_prod_backend
    ```
*   Verify that Postgres is running and accepting connections.
*   Verify Redis queue accessibility.

### Nginx reverse proxy issues
*   Inspect Nginx access and error logs:
    ```bash
    docker compose -f docker-compose.prod.yml logs nginx
    ```
*   Ensure that the target upstream containers (`frontend:80` and `backend:8000`) are accessible on the internal `ai_prod_network`.

### Celery Background Tasks Blocked
*   Verify Redis connectivity.
*   Inspect worker logs for tracebacks:
    ```bash
    docker compose -f docker-compose.prod.yml logs celery-worker
    ```
