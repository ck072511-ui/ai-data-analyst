import os
import sys
import pytest
from unittest.mock import AsyncMock, patch, MagicMock

# Adjust path to find backend
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

# Set environment variables for testing
os.environ["DATABASE_URL"] = "sqlite:///./test_analytics.db"
os.environ["SECRET_KEY"] = "test-secret-key-must-be-long-enough-32-chars-at-least"
os.environ["ENVIRONMENT"] = "development"

from app.services.prompt_service import PromptService
from app.services.prompt_version_service import PromptVersionService
from app.services.model_registry_service import ModelRegistryService
from app.services.evaluation_service import EvaluationService


@pytest.fixture
def anyio_backend():
    return "asyncio"


def test_variables_extractor():
    content = "Hello {name}, select columns from table {table_name} where date = {date}"
    variables = PromptService.extract_variables(content)
    assert "name" in variables
    assert "table_name" in variables
    assert "date" in variables
    assert len(variables) == 3


@pytest.mark.anyio
async def test_prompt_crud_and_versioning(anyio_backend):
    service = PromptService()
    version_service = PromptVersionService()

    with patch("app.services.prompt_service.AsyncSessionLocal") as mock_session_class, \
         patch("app.services.prompt_version_service.AsyncSessionLocal") as mock_v_session_class:
        
        # Mock database session execution
        mock_session = AsyncMock()
        mock_session_class.return_value.__aenter__.return_value = mock_session
        
        mock_prompt = MagicMock()
        mock_prompt.id = "prompt-uuid"
        mock_prompt.name = "sql_generation"
        mock_prompt.content = "Initial SQL content template"
        mock_prompt.version = 1
        
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_session.execute = AsyncMock(return_value=mock_result)

        # Create
        res_create = await service.create_prompt(
            name="sql_generation",
            category="sql",
            content="Initial SQL content template"
        )
        assert "id" in res_create
        assert res_create["version"] == 1


@pytest.mark.anyio
async def test_model_registry_activations(anyio_backend):
    service = ModelRegistryService()
    
    mock_model = MagicMock()
    mock_model.id = "model-uuid"
    mock_model.name = "llama3:8b"
    mock_model.status = "inactive"

    with patch("app.services.model_registry_service.AsyncSessionLocal") as mock_session_class:
        mock_session = AsyncMock()
        mock_session_class.return_value.__aenter__.return_value = mock_session
        
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = [mock_model]
        mock_session.execute = AsyncMock(return_value=mock_result)

        res = await service.activate_model("model-uuid")
        assert res["status"] == "active"
        assert mock_model.status == "active"


def test_evaluation_metric_scores():
    # Fast query, SQL and citations matching
    res = EvaluationService.run_metrics_score(
        sql="SELECT * FROM sales",
        citations=[{"filename": "doc.pdf"}],
        latency_ms=1200,
        answer="Monthly business metrics reports look good."
    )
    assert res["overall_score"] >= 80.0

    # Slow query, missing citations
    res_slow = EvaluationService.run_metrics_score(
        sql="",
        citations=[],
        latency_ms=12000, # 12 seconds
        answer="No data."
    )
    assert res_slow["overall_score"] < 50.0
