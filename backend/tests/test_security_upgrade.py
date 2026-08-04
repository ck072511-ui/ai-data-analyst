import os
import sys
import time

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
from app.services.security_service import SecurityService, login_limiter

client = TestClient(app)


@pytest.fixture(scope="module", autouse=True)
def setup_database():
    from sqlalchemy import create_engine

    sync_engine = create_engine("sqlite:///./test_analytics.db")
    Base.metadata.drop_all(bind=sync_engine)
    Base.metadata.create_all(bind=sync_engine)

    from sqlalchemy.orm import sessionmaker

    Session = sessionmaker(bind=sync_engine)
    session = Session()

    # Create test user matching complex password requirements
    test_user = User(
        id="lockout-user-uuid",
        email="lockout@example.com",
        hashed_password=get_password_hash("ComplexPassword123!"),
        full_name="Lockout User",
        role="Viewer",
        is_active=1,
    )
    session.add(test_user)
    session.commit()
    session.close()

    yield

    try:
        Base.metadata.drop_all(bind=sync_engine)
    except Exception:
        pass
    sync_engine.dispose()


def test_password_policy():
    # 1. Weak passwords rejected
    v, msg = SecurityService.validate_password_strength("weak")
    assert not v
    assert "at least 8" in msg

    v, msg = SecurityService.validate_password_strength("lowercase123!")
    assert not v
    assert "uppercase" in msg

    v, msg = SecurityService.validate_password_strength("UPPERCASE123!")
    assert not v
    assert "lowercase" in msg

    v, msg = SecurityService.validate_password_strength("UpperLower!")
    assert not v
    assert "number" in msg

    v, msg = SecurityService.validate_password_strength("UpperLower123")
    assert not v
    assert "special character" in msg

    # 2. Strong password accepted
    v, msg = SecurityService.validate_password_strength("StrongPassword123!")
    assert v
    assert msg is None


def test_account_lockout_mechanism():
    # Guarantee clean state at test start
    from sqlalchemy import create_engine
    from sqlalchemy.orm import sessionmaker

    engine = create_engine("sqlite:///./test_analytics.db")
    Session = sessionmaker(bind=engine)
    session = Session()
    user = session.query(User).filter_by(email="lockout@example.com").first()
    if user:
        user.failed_login_attempts = 0
        user.lockout_until = None
        session.commit()
    session.close()

    # Trigger 5 failed login attempts to verify account locks
    for i in range(5):
        resp = client.post("/api/v1/auth/login", json={"email": "lockout@example.com", "password": "WrongPassword"})
        if i < 4:
            assert resp.status_code == 401
        else:
            assert resp.status_code == 400  # becomes locked
            assert "locked" in resp.json()["detail"]

    # Trying again immediately returns locked error
    resp = client.post("/api/v1/auth/login", json={"email": "lockout@example.com", "password": "ComplexPassword123!"})
    assert resp.status_code == 400
    assert "locked" in resp.json()["detail"]


def test_security_headers():
    resp = client.get("/api/v1/query/history")
    assert resp.headers.get("X-Content-Type-Options") == "nosniff"
    assert resp.headers.get("X-Frame-Options") == "DENY"
    assert "default-src 'self'" in resp.headers.get("Content-Security-Policy")


def test_refresh_token_and_session_management():
    # 1. Bypass lockout for login test by resetting counter in DB directly
    from sqlalchemy import create_engine
    from sqlalchemy.orm import sessionmaker

    engine = create_engine("sqlite:///./test_analytics.db")
    Session = sessionmaker(bind=engine)
    session = Session()
    user = session.query(User).filter_by(email="lockout@example.com").first()
    user.failed_login_attempts = 0
    user.lockout_until = None
    session.commit()
    session.close()

    # 2. Authenticate to establish session
    resp = client.post("/api/v1/auth/login", json={"email": "lockout@example.com", "password": "ComplexPassword123!"})
    assert resp.status_code == 200
    data = resp.json()
    assert "access_token" in data
    assert "refresh_token" in data
    refresh_token_1 = data["refresh_token"]

    # 3. Retrieve sessions list
    headers = {"Authorization": f"Bearer {data['access_token']}"}
    sessions_resp = client.get("/api/v1/auth/sessions", headers=headers)
    assert sessions_resp.status_code == 200
    active_sessions = sessions_resp.json()
    assert len(active_sessions) >= 1

    # 4. Use refresh token rotation
    refresh_resp = client.post("/api/v1/auth/refresh", json={"refresh_token": refresh_token_1})
    assert refresh_resp.status_code == 200
    rot_data = refresh_resp.json()
    assert "access_token" in rot_data
    assert "refresh_token" in rot_data
    refresh_token_2 = rot_data["refresh_token"]

    # 5. Token reuse detection: Re-using the old refresh_token_1 should immediately trigger lock/revocation
    hijack_resp = client.post("/api/v1/auth/refresh", json={"refresh_token": refresh_token_1})
    assert hijack_resp.status_code == 401
    assert "used already" in hijack_resp.json()["detail"]


def test_rate_limiting():
    # Trigger rate limiter on login
    client_ip = "testclient"
    # Artificially populate sliding window history to force a 429
    now = time.time()
    login_limiter.history[client_ip] = [now] * 10

    resp = client.post(
        "/api/v1/auth/login",
        json={"email": "lockout@example.com", "password": "ComplexPassword123!"},
        headers={"x-force-rate-limit": "force_rate_limit"},
    )
    assert resp.status_code == 429
    assert "Too many requests" in resp.json()["detail"]

    # Reset limit history
    login_limiter.history[client_ip] = []
