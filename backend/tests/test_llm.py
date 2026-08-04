import os
import sys
import pytest
from unittest.mock import AsyncMock, patch, MagicMock
from fastapi.testclient import TestClient

# Adjust path to find backend
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

# Set environment variables for testing
os.environ["DATABASE_URL"] = "sqlite:///./test_analytics.db"
os.environ["SECRET_KEY"] = "test-secret-key-must-be-long-enough-32-chars-at-least"
os.environ["ENVIRONMENT"] = "development"

from app.core.database import Base
from app.core.security import get_password_hash
from app.main import app
from app.models.user import User
from app.services.model_manager import model_manager
from app.services.ollama_provider import OllamaProvider

client = TestClient(app)


@pytest.fixture
def anyio_backend():
    return "asyncio"


@pytest.fixture(scope="module", autouse=True)
def setup_database():
    from sqlalchemy import create_engine
    from sqlalchemy.orm import sessionmaker

    sync_engine = create_engine("sqlite:///./test_analytics.db")
    Base.metadata.create_all(bind=sync_engine)

    Session = sessionmaker(bind=sync_engine)
    session = Session()

    users = [
        User(
            id="admin-uuid",
            email="admin@example.com",
            hashed_password=get_password_hash("password123"),
            full_name="Admin User",
            role="Admin",
            is_active=1,
        ),
        User(
            id="analyst-uuid",
            email="analyst@example.com",
            hashed_password=get_password_hash("password123"),
            full_name="Analyst User",
            role="Data Analyst",
            is_active=1,
        ),
        User(
            id="viewer-uuid",
            email="viewer@example.com",
            hashed_password=get_password_hash("password123"),
            full_name="Viewer User",
            role="Viewer",
            is_active=1,
        ),
    ]
    for u in users:
        existing = session.query(User).filter_by(email=u.email).first()
        if not existing:
            session.add(u)
        else:
            existing.role = u.role
            
    session.commit()
    session.close()

    yield

    sync_engine.dispose()


def _get_headers(email):
    response = client.post("/api/v1/auth/login", json={"email": email, "password": "password123"})
    assert response.status_code == 200
    token = response.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


@pytest.mark.anyio
async def test_provider_abstractions(anyio_backend):
    # Verify placeholder provider abstractions exist and list correctly
    from app.services.model_manager import LlamaCppProvider, VllmProvider
    
    llama_cpp = LlamaCppProvider()
    assert await llama_cpp.health_check() is False
    models = await llama_cpp.list_models()
    assert "llama.cpp-placeholder" in models

    vllm = VllmProvider()
    assert await vllm.health_check() is False
    vllm_models = await vllm.list_models()
    assert "vllm-placeholder" in vllm_models

    # Test Ollama Provider initialization
    ollama_prov = OllamaProvider(base_url="http://localhost:11434", timeout=10, active_model="llama3")
    assert ollama_prov.base_url == "http://localhost:11434"
    assert ollama_prov.active_model == "llama3"


@pytest.mark.anyio
async def test_ollama_graceful_fallback(anyio_backend):
    # Mocking httpx ConnectError to verify Ollama offline health checks and fallbacks
    with patch("httpx.AsyncClient.get", side_effect=Exception("Connection refused")):
        ollama_prov = OllamaProvider()
        # Health check must catch exceptions and return False
        assert await ollama_prov.health_check() is False

    with patch("httpx.AsyncClient.request", side_effect=Exception("Connection refused")):
        ollama_prov = OllamaProvider()
        # Model discovery must catch exception and return empty list rather than crash
        models = await ollama_prov.list_models()
        assert models == []


@pytest.mark.anyio
async def test_model_manager(anyio_backend):
    # Verify manager settings
    await model_manager.initialize_active_settings()
    assert model_manager.active_provider_name in ["ollama", "llama.cpp", "vllm", "lm_studio", "huggingface_local"]
    
    # Test switching model dynamically
    success = await model_manager.select_model(model_name="qwen", provider_name="ollama")
    assert success is True
    assert await model_manager.get_active_model() == "qwen"
    assert await model_manager.get_active_provider() == "ollama"


def test_api_endpoints_rbac():
    # Viewers should be able to get models and status, but not change active model
    viewer_headers = _get_headers("viewer@example.com")
    analyst_headers = _get_headers("analyst@example.com")

    # 1. Test GET /models (Viewer allowed)
    response = client.get("/api/v1/llm/models", headers=viewer_headers)
    assert response.status_code == 200
    assert "models" in response.json()
    assert "active_model" in response.json()

    # 2. Test GET /status (Viewer allowed)
    response = client.get("/api/v1/llm/status", headers=viewer_headers)
    assert response.status_code == 200
    assert "status" in response.json()
    assert "provider" in response.json()

    # 3. Test POST /select (Viewer Forbidden)
    payload = {"model": "qwen"}
    response = client.post("/api/v1/llm/select", json=payload, headers=viewer_headers)
    assert response.status_code == 403

    # 4. Test POST /select (Analyst Allowed)
    response = client.post("/api/v1/llm/select", json=payload, headers=analyst_headers)
    assert response.status_code == 200
    assert response.json()["model"] == "qwen"


@pytest.mark.anyio
async def test_api_generation_endpoint(anyio_backend):
    analyst_headers = _get_headers("analyst@example.com")

    # Mock dynamic model manager generation to test API returns
    with patch("app.services.model_manager.model_manager.generate", new_callable=AsyncMock) as mock_gen:
        mock_gen.return_value = "This is a mock SQL query response"
        
        response = client.post(
            "/api/v1/llm/test", 
            json={"prompt": "Write SQL to fetch users", "stream": False},
            headers=analyst_headers
        )
        assert response.status_code == 200
        data = response.json()
        assert data["response"] == "This is a mock SQL query response"
        assert "latency_ms" in data
        assert "model" in data
        assert "provider" in data
