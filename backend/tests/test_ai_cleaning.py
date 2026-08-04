import os
import sys
import pytest
import pandas as pd
import numpy as np
from unittest.mock import AsyncMock, patch, MagicMock

# Adjust path to find backend
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

# Set environment variables for testing
os.environ["DATABASE_URL"] = "sqlite:///./test_analytics.db"
os.environ["SECRET_KEY"] = "test-secret-key-must-be-long-enough-32-chars-at-least"
os.environ["ENVIRONMENT"] = "development"

from app.services.ai_cleaning_service import apply_ai_transformations, AICleaningService
from app.services.prompt_builder import PromptBuilder
from app.models.ai_cleaning import AICleaningRecommendation


@pytest.fixture
def anyio_backend():
    return "asyncio"


def test_apply_ai_transformations():
    # Construct mock dataframe
    df = pd.DataFrame({
        "id": [1, 2, 3, 4],
        "name": [" John  ", "Alice", "Bob ", None],
        "age": [20.0, np.nan, 30.0, 40.0],
        "join_date": ["2020-01-05", "2021-06-10", "2022-11-15", None],
        "category": ["A", "B", "A", "B"]
      })

    steps = [
        {"column": "name", "transformation": "trim_spaces", "description": "Trim spacing"},
        {"column": "age", "transformation": "impute_mean", "description": "Impute mean"},
        {"column": "join_date", "transformation": "standardize_dates", "description": "Parse dates"},
        {"column": "category", "transformation": "label_encode", "description": "Label encode categories"}
    ]

    df_cleaned, ops = apply_ai_transformations(df, steps)

    # 1. Assert Whitespace trimmed
    assert df_cleaned.iloc[0]["name"] == "John"
    assert df_cleaned.iloc[2]["name"] == "Bob"

    # 2. Assert Age imputed (mean of 20, 30, 40 is 30)
    assert df_cleaned.iloc[1]["age"] == 30.0

    # 3. Assert dates formatted
    assert df_cleaned.iloc[0]["join_date"] == "2020-01-05"

    # 4. Assert Category encoded
    assert df_cleaned.iloc[0]["category"] in [0, 1]


def test_prompt_builder_cleaning():
    builder = PromptBuilder()
    
    prompt = builder.build_ai_cleaning_prompt(
        filename="sales.csv",
        row_count=100,
        col_count=5,
        profile_summary="age: 15 nulls\nrevenue: 0 nulls"
    )

    assert "sales.csv" in prompt
    assert "overall_quality_improvement_est" in prompt
    assert "execution_plan" in prompt
    assert "confidence_score" in prompt


@pytest.mark.anyio
async def test_generate_recommendations_workflow(anyio_backend):
    service = AICleaningService()
    
    # Mock database session query results
    mock_dataset = MagicMock()
    mock_dataset.filename = "customers.csv"
    mock_dataset.row_count = 50
    mock_dataset.col_count = 3
    mock_dataset.columns = ["id", "email", "created_at"]
    mock_dataset.schema_info = {
        "id": {"dtype": "int64"},
        "email": {"dtype": "object"},
        "created_at": {"dtype": "object"}
    }
    mock_dataset.profile_info = {
        "missing_values": {"by_column": {"email": 5}}
    }

    mock_llm_json = """
    {
      "dataset_explanation": "Email has 5 missing records. Created_at contains standard timestamps.",
      "overall_quality_improvement_est": 20.0,
      "confidence_score": 0.88,
      "execution_plan": [
        {
          "step_id": 1,
          "category": "formatting",
          "column": "email",
          "transformation": "clean_emails",
          "description": "Standardize email inputs.",
          "reason": "Contains blank entries.",
          "estimated_impact": "Prevents email sending loops.",
          "confidence": 0.92,
          "rollback_compatibility": true
        }
      ]
    }
    """

    with patch("app.services.ai_cleaning_service.AsyncSessionLocal") as mock_session_class, \
         patch("app.services.ai_cleaning_service.model_manager.generate", new_callable=AsyncMock) as mock_generate:
        
        mock_generate.return_value = mock_llm_json
        
        # Setup mock db context manager returns
        mock_session = AsyncMock()
        mock_session_class.return_value.__aenter__.return_value = mock_session
        
        # Mock fetch dataset
        mock_execute_res = MagicMock()
        mock_execute_res.scalar_one_or_none.return_value = mock_dataset
        mock_session.execute.return_value = mock_execute_res

        res = await service.generate_recommendations("dataset-uuid", "user-uuid")

        assert "recommendation_id" in res
        assert res["quality_improvement_est"] == 20.0
        assert res["confidence_score"] == 0.88
        assert len(res["execution_plan"]) == 1
        assert res["execution_plan"][0]["column"] == "email"
