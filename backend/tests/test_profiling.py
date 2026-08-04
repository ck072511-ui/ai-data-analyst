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
        email="profiler@example.com",
        hashed_password=get_password_hash("password123"),
        full_name="Profiler User",
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

    # Dispose the async engine to free up locks
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


def test_dataset_profiling_workflow():
    # 1. Login user to get JWT token
    login_response = client.post(
        "/api/v1/auth/login", json={"email": "profiler@example.com", "password": "password123"}
    )
    assert login_response.status_code == 200
    token = login_response.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    # 2. Generate a temporary CSV dataset with duplicate rows and missing values
    csv_content = (
        "name,age,salary\n"
        "Alice,30,70000.0\n"
        "Bob,,80000.0\n"
        "Charlie,35,95000.0\n"
        "Alice,30,70000.0\n"  # duplicate row
        "Dave,40,\n"  # missing salary
    )
    csv_file = "test_profiling_data.csv"
    with open(csv_file, "w") as f:
        f.write(csv_content)

    try:
        # 3. Upload dataset
        with open(csv_file, "rb") as f:
            upload_response = client.post(
                "/api/v1/datasets/upload", files={"file": (csv_file, f, "text/csv")}, headers=headers
            )

        assert upload_response.status_code == 200
        upload_data = upload_response.json()
        assert upload_data["filename"] == "test_profiling_data.csv"
        assert upload_data["row_count"] == 5
        assert upload_data["col_count"] == 3
        dataset_id = upload_data["id"]

        # Verify profiling info is returned in upload response
        assert "profile_info" in upload_data
        profile = upload_data["profile_info"]
        assert profile["row_count"] == 5
        assert profile["col_count"] == 3
        assert len(profile["column_types"]["numerical"]) == 2  # age, salary
        assert len(profile["column_types"]["categorical"]) == 1  # name

        # Verify duplicate rows count
        assert profile["quality_report"]["duplicate_rows"]["count"] == 1
        # Verify missing values count
        assert profile["quality_report"]["missing_values"]["total_missing"] == 2  # one in age, one in salary
        # Verify quality score is less than 100 due to warnings
        assert profile["quality_score"] < 100
        assert profile["quality_rating"] in ["Excellent", "Good", "Average", "Poor"]

        # 4. Retrieve profile via GET route
        get_response = client.get(f"/api/v1/datasets/{dataset_id}/profile", headers=headers)
        assert get_response.status_code == 200
        get_profile = get_response.json()
        assert get_profile["quality_score"] == profile["quality_score"]
        assert get_profile["quality_report"]["duplicate_rows"]["count"] == 1

        # 5. Clean up dataset
        delete_response = client.delete(f"/api/v1/datasets/{dataset_id}", headers=headers)
        assert delete_response.status_code == 200

    finally:
        if os.path.exists(csv_file):
            os.remove(csv_file)
