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

    # Create test users with different roles
    from sqlalchemy.orm import sessionmaker

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
            id="scientist-uuid",
            email="scientist@example.com",
            hashed_password=get_password_hash("password123"),
            full_name="Scientist User",
            role="Data Scientist",
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
        session.add(u)
    session.commit()
    session.close()

    yield

    # Cleanup
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


def _get_headers(email):
    response = client.post("/api/v1/auth/login", json={"email": email, "password": "password123"})
    assert response.status_code == 200
    token = response.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


def test_viewer_restrictions():
    headers = _get_headers("viewer@example.com")

    # 1. Viewer cannot upload dataset
    files = {"file": ("test.csv", b"a,b\n1,2\n")}
    response = client.post("/api/v1/datasets/upload", files=files, headers=headers)
    assert response.status_code == 403
    assert "Forbidden" in response.json()["detail"]

    # 2. Viewer CAN list datasets
    response = client.get("/api/v1/datasets/", headers=headers)
    assert response.status_code == 200


def test_analyst_permissions():
    headers = _get_headers("analyst@example.com")

    # 1. Analyst CAN upload dataset
    files = {"file": ("test_analyst.csv", b"a,b\n1,2\n")}
    response = client.post("/api/v1/datasets/upload", files=files, headers=headers)
    assert response.status_code == 200
    dataset_id = response.json()["id"]

    # 2. Analyst cannot access user management list
    response = client.get("/api/v1/users/roles", headers=headers)
    assert response.status_code == 403


def test_admin_permissions():
    headers = _get_headers("admin@example.com")

    # 1. Admin can access user list and roles
    response = client.get("/api/v1/users/roles", headers=headers)
    assert response.status_code == 200
    data = response.json()
    assert "users" in data
    assert "roles" in data

    # 2. Admin can change roles
    # Promote viewer to Analyst
    payload = {"role": "Data Analyst"}
    response = client.patch("/api/v1/users/viewer-uuid/role", json=payload, headers=headers)
    assert response.status_code == 200
    assert response.json()["new_role"] == "Data Analyst"

    # Verify that the promoted user now has Analyst privileges (can login, profile etc.)
    viewer_headers = _get_headers("viewer@example.com")
    files = {"file": ("promoted.csv", b"x,y\n9,9\n")}
    response = client.post("/api/v1/datasets/upload", files=files, headers=viewer_headers)
    assert response.status_code == 200  # Promoted Viewer can now upload!
