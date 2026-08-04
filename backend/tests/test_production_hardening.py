import os
import sys
import pytest
import shutil
from unittest.mock import AsyncMock, patch, MagicMock

# Adjust path to find backend
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

# Set environment variables for testing
os.environ["DATABASE_URL"] = "sqlite:///./test_analytics.db"
os.environ["SECRET_KEY"] = "test-secret-key-must-be-long-enough-32-chars-at-least"
os.environ["ENVIRONMENT"] = "production"

from fastapi.testclient import TestClient
from app.main import app
from app.services.backup_service import BackupService
from app.services.readiness_validator import ReadinessValidator

client = TestClient(app)


@pytest.fixture
def anyio_backend():
    return "asyncio"


def test_liveness_check():
    """Verify application liveness ping."""
    response = client.get("/health/live")
    assert response.status_code == 200
    assert response.json()["status"] == "healthy"


@pytest.mark.anyio
async def test_readiness_checks(anyio_backend):
    """Verify readiness checklist compiler outcomes."""
    with patch("app.services.readiness_validator.AsyncSessionLocal") as mock_session_class, \
         patch("app.services.model_manager.model_manager.generate") as mock_gen:
        
        mock_session = AsyncMock()
        mock_session_class.return_value.__aenter__.return_value = mock_session
        mock_gen.return_value = "pong"
        
        res = await ReadinessValidator.run_checks()
        assert "database" in res
        assert "vector_store_directory" in res
        assert "document_export_directory" in res


@pytest.mark.anyio
async def test_backup_and_restore_workflow(anyio_backend):
    """Verify SQL backups, prompt JSON saves, and metadata schemas."""
    service = BackupService()
    
    with patch("app.services.backup_service.AsyncSessionLocal") as mock_session_class:
        mock_session = AsyncMock()
        mock_session_class.return_value.__aenter__.return_value = mock_session
        
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = []
        mock_session.execute = AsyncMock(return_value=mock_result)
        
        # Test backup create
        res = await service.create_backup()
        assert res["success"] is True
        assert "backup_directory" in res
        assert os.path.exists(res["backup_directory"])
        
        # Test backup verify
        folder_name = os.path.basename(res["backup_directory"])
        verify_res = await service.restore_from_backup(folder_name)
        assert verify_res["success"] is True
        
        # Cleanup
        shutil.rmtree(res["backup_directory"])


def test_payload_size_limit():
    """Verify size limits middleware blocks huge requests."""
    # Send a request with a Content-Length header that exceeds the limit
    headers = {"Content-Length": str(200 * 1024 * 1024)} # 200MB
    response = client.post("/api/v1/auth/login", headers=headers, json={"username": "a", "password": "b"})
    assert response.status_code == 413
