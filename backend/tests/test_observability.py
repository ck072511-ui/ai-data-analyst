import os
import sys

import pytest
from fastapi.testclient import TestClient

# Adjust path to find backend
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

# Set environment variables for testing before importing main app
os.environ["DATABASE_URL"] = "sqlite:///./test_observability.db"
os.environ["SECRET_KEY"] = "test-secret-key-must-be-long-enough-32-chars-at-least"
os.environ["ENVIRONMENT"] = "development"

from app.main import app
from app.services.logging_service import JSONFormatter
from app.services.monitoring_service import monitoring_service

client = TestClient(app)


@pytest.fixture(scope="module", autouse=True)
def setup_database():
    from sqlalchemy import create_engine

    from app.core.database import Base, engine

    db_url = str(engine.url)
    if db_url.startswith("postgresql+asyncpg://"):
        db_url = db_url.replace("postgresql+asyncpg://", "postgresql://")
    elif db_url.startswith("sqlite+aiosqlite://"):
        db_url = db_url.replace("sqlite+aiosqlite://", "sqlite://")

    sync_engine = create_engine(db_url)
    Base.metadata.create_all(bind=sync_engine)
    yield
    sync_engine.dispose()


def test_health_endpoints():
    # Test GET /health/live
    response = client.get("/health/live")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
    assert data["service"] == "ai-data-analyst"

    # Test GET /health
    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert "status" in data
    assert "checks" in data
    assert "database" in data["checks"]
    assert "storage" in data["checks"]
    assert "authentication" in data["checks"]

    # Test GET /health/ready
    response = client.get("/health/ready")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"


def test_metrics_endpoint():
    # Make a request to trigger metrics increment
    client.get("/")

    # Test GET /metrics
    response = client.get("/metrics")
    assert response.status_code == 200
    assert "http_requests_total" in response.text
    assert "active_requests" in response.text


def test_request_tracing_middleware():
    response = client.get("/")
    assert response.status_code == 200
    assert "X-Request-ID" in response.headers
    request_id = response.headers["X-Request-ID"]
    assert len(request_id) > 0

    # Pass in custom request ID
    custom_id = "test-custom-id-1234"
    response = client.get("/", headers={"X-Request-ID": custom_id})
    assert response.status_code == 200
    assert response.headers["X-Request-ID"] == custom_id


def test_json_logging_formatter():
    import logging

    formatter = JSONFormatter()
    record = logging.LogRecord(
        name="test_logger",
        level=logging.INFO,
        pathname="test.py",
        lineno=10,
        msg="Test log message",
        args=None,
        exc_info=None,
    )
    formatted = formatter.format(record)
    import json

    parsed = json.loads(formatted)
    assert parsed["level"] == "INFO"
    assert parsed["message"] == "Test log message"
    assert parsed["logger"] == "test_logger"
    assert "timestamp" in parsed
    assert "request_id" in parsed
    assert "user_id" in parsed


def test_monitoring_service_api():
    # Test manual increments on monitoring service
    prev_success = monitoring_service.get_total_requests()
    monitoring_service.record_request("GET", "/test-mon", 200, 0.05, 100)
    assert monitoring_service.get_total_requests() == prev_success + 1
