# Stage 1: Build stage
FROM python:3.11-slim AS builder

WORKDIR /app

# Install build dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# Create virtual environment
RUN python -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# Stage 2: Runtime stage
FROM python:3.11-slim AS runner

WORKDIR /app

ENV PATH="/opt/venv/bin:$PATH"
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

# Copy virtual env from builder
COPY --from=builder /opt/venv /opt/venv

# Create a non-root user for security hardening
RUN groupadd -g 10001 appgroup && \
    useradd -r -u 10001 -g appgroup appuser

# Copy application files and set ownership
COPY --chown=appuser:appgroup . .

# Create uploads and data directories and set permissions
RUN mkdir -p /app/data/uploads && \
    chown -R appuser:appgroup /app/data && \
    chmod -R 775 /app/data

USER appuser

EXPOSE 8000

# Health check using standard library to avoid curl dependency in slim image
HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
    CMD python -c "import os, urllib.request; port = os.getenv('PORT', '8000'); urllib.request.urlopen(f'http://localhost:{port}/health/live')" || exit 1

CMD uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000}