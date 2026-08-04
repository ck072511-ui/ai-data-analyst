import os
import sys

import pytest
from fastapi.testclient import TestClient

# Adjust path to find backend
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

# Set environment variables for testing before importing settings
os.environ["DATABASE_URL"] = "sqlite:///./test_analytics.db"
os.environ["SECRET_KEY"] = "test-secret-key-must-be-long-enough-32-chars-at-least"
os.environ["ENVIRONMENT"] = "development"

from app.core.database import Base
from app.core.security import get_password_hash
from app.main import app
from app.models.user import User
from app.services.insight_service import (
    explain_applied_cleaning_operations,
    generate_dataset_health,
    generate_rich_business_recommendations,
)

client = TestClient(app)


@pytest.fixture(scope="module", autouse=True)
def setup_database():
    # Sync database setup for SQLite test
    from sqlalchemy import create_engine

    sync_engine = create_engine("sqlite:///./test_analytics.db")
    Base.metadata.drop_all(bind=sync_engine)
    Base.metadata.create_all(bind=sync_engine)

    # Create a test user
    from sqlalchemy.orm import sessionmaker

    Session = sessionmaker(bind=sync_engine)
    session = Session()
    test_user = User(
        id="test-user-uuid",
        email="insights@example.com",
        hashed_password=get_password_hash("password123"),
        full_name="Insights User",
        role="Admin",
        is_active=1,
    )
    session.add(test_user)
    session.commit()
    session.close()

    yield

    # Cleanup database and uploads folder after tests
    try:
        Base.metadata.drop_all(bind=sync_engine)
    except Exception:
        pass
    sync_engine.dispose()

    import asyncio

    from app.core.database import engine as async_engine

    try:
        loop = asyncio.get_event_loop()
        if loop.is_running():
            loop.create_task(async_engine.dispose())
        else:
            loop.run_until_complete(async_engine.dispose())
    except Exception:
        pass

    if os.path.exists("./test_analytics.db"):
        try:
            os.remove("./test_analytics.db")
        except Exception:
            pass


def test_unit_insight_service():
    sample_profile = {
        "quality_score": 78,
        "quality_rating": "Good",
        "row_count": 1000,
        "col_count": 5,
        "column_types": {
            "numerical": ["age", "salary"],
            "categorical": ["country", "id"],
            "date": [],
            "boolean": [],
            "text": [],
        },
        "quality_report": {
            "missing_values": {
                "by_column": {"age": 10, "salary": 200},
                "total_missing": 210,
                "missing_pct": 4.2,
                "top_affected_columns": [{"column": "salary", "pct": 20.0}, {"column": "age", "pct": 1.0}],
            },
            "duplicate_rows": {"count": 50, "pct": 5.0, "sample_records": []},
            "duplicate_columns": [],
            "mixed_data_types": {"age": ["int", "str"]},
            "empty_columns": ["notes"],
            "constant_columns": ["status"],
            "outliers": {"salary": {"outlier_count": 60, "outlier_percentage": 6.0}},
            "invalid_dates": [],
            "invalid_emails": {"total_invalid_count": 5, "affected_columns": {"email": {"invalid_count": 5}}},
            "invalid_phones": {"total_invalid_count": 0, "affected_columns": {}},
            "high_cardinality": ["id"],
        },
        "correlation_analysis": {"high_correlations": [{"col1": "age", "col2": "salary", "coefficient": 0.89}]},
        "numerical_statistics": {"age": {"mean": 45, "median": 30, "std_dev": 10}},
    }

    # 1. Test rich recommendations
    recs = generate_rich_business_recommendations(sample_profile)
    assert len(recs) > 0
    # verify fields
    for rec in recs:
        assert "title" in rec
        assert "description" in rec
        assert "business_impact" in rec
        assert "severity" in rec
        assert "confidence_score" in rec

    titles = [r["title"] for r in recs]
    assert any("duplicate rows" in t for t in titles)
    assert any("notes" in t for t in titles)
    assert any("status" in t for t in titles)
    assert any("age" in t and "salary" in t for t in titles)

    # 2. Test Health Summary
    health = generate_dataset_health(sample_profile)
    assert health["overall_health"] == 78
    assert len(health["strengths"]) >= 0
    assert len(health["weaknesses"]) > 0
    assert len(health["top_risks"]) > 0
    assert len(health["recommended_next_steps"]) > 0

    # 3. Test cleaning explanations
    operations = [
        "Whitespace trimming applied to text columns.",
        "Removed exact duplicate row entries.",
        "Winsorized outlier extremes in numerical columns.",
    ]
    explanations = explain_applied_cleaning_operations(operations)
    assert len(explanations) == 3
    for exp in explanations:
        assert "operation" in exp
        assert "what_changed" in exp
        assert "why_it_changed" in exp
        assert "business_impact" in exp
        assert "expected_improvement" in exp


def test_api_insights_integration():
    # 1. Login user to get JWT token
    login_response = client.post(
        "/api/v1/auth/login", json={"email": "insights@example.com", "password": "password123"}
    )
    assert login_response.status_code == 200
    token = login_response.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    # 2. Generate a temporary CSV dataset
    csv_content = (
        "id,name,age,salary,email\n"
        "1,Alice,30,70000.0,alice@example.com\n"
        "2,Bob,25,80000.0,bob-invalid-email\n"
        "3,Charlie,35,95000.0,charlie@example.com\n"
        "1,Alice,30,70000.0,alice@example.com\n"  # duplicate row
        "4,Dave,40,,dave@example.com\n"  # missing salary
    )
    csv_file = "test_insights_data.csv"
    with open(csv_file, "w") as f:
        f.write(csv_content)

    try:
        # 3. Upload dataset to create profile
        with open(csv_file, "rb") as f:
            upload_response = client.post(
                "/api/v1/datasets/upload", files={"file": (csv_file, f, "text/csv")}, headers=headers
            )
        assert upload_response.status_code == 200
        dataset_id = upload_response.json()["id"]

        # 4. Request insights
        insights_response = client.get(f"/api/v1/datasets/{dataset_id}/insights", headers=headers)
        assert insights_response.status_code == 200
        insights_data = insights_response.json()
        assert "quality_summary" in insights_data
        assert "business_recommendations" in insights_data
        assert "cleaning_explanations" in insights_data
        assert "quality_improvement" in insights_data

        # 5. Request health
        health_response = client.get(f"/api/v1/datasets/{dataset_id}/health", headers=headers)
        assert health_response.status_code == 200
        health_data = health_response.json()
        assert "overall_health" in health_data
        assert "top_risks" in health_data
        assert "strengths" in health_data
        assert "weaknesses" in health_data
        assert "recommended_next_steps" in health_data

    finally:
        if os.path.exists(csv_file):
            os.remove(csv_file)

        # Cleanup uploaded files from uploads directory
        uploads_dir = os.path.join("backend", "data", "uploads")
        if os.path.exists(uploads_dir):
            for file in os.listdir(uploads_dir):
                if file.startswith("u_") or file.endswith(".csv"):
                    try:
                        os.remove(os.path.join(uploads_dir, file))
                    except Exception:
                        pass
