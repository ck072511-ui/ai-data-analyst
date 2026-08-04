import os
import sys

import pandas as pd
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
from app.services.dashboard_service import calculate_kpis_for_dataframe, choose_optimal_chart, format_chart_js_payload

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
        id="test-dashboard-user-uuid",
        email="dashboard@example.com",
        hashed_password=get_password_hash("password123"),
        full_name="Dashboard User",
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


def test_unit_dashboard_service():
    # 1. Test Auto KPI Generation
    df_numeric = pd.DataFrame({"age": [20, 30, 40, None], "salary": [50000, 60000, 70000, 80000]})
    kpis = calculate_kpis_for_dataframe(df_numeric)
    assert len(kpis) == 2
    age_kpi = next(k for k in kpis if k["column"] == "age")
    assert age_kpi["count"] == 4
    assert age_kpi["average"] == 30.0
    assert age_kpi["min"] == 20.0
    assert age_kpi["max"] == 40.0
    assert age_kpi["missing_pct"] == 25.0

    # 2. Test Auto Chart Selection Heuristics
    # A. Time Series (date + numeric)
    df_time = pd.DataFrame({"timestamp": pd.date_range(start="2026-01-01", periods=5), "sales": [10, 15, 20, 25, 30]})
    chart_ts = choose_optimal_chart(df_time)
    assert chart_ts["chart_type"] == "line"
    assert chart_ts["x_axis"] == "timestamp"
    assert chart_ts["y_axis"] == "sales"

    # B. Relationship (2 numeric columns)
    df_rel = pd.DataFrame({"height": [150, 160, 170, 180], "weight": [50, 60, 70, 80]})
    chart_rel = choose_optimal_chart(df_rel)
    assert chart_rel["chart_type"] == "scatter"
    assert chart_rel["x_axis"] == "height"
    assert chart_rel["y_axis"] == "weight"

    # C. Part-to-Whole (low cardinality categorical + numeric)
    df_pie = pd.DataFrame({"country": ["US", "US", "CA", "MX", "CA", "MX"], "revenue": [100, 200, 150, 80, 120, 90]})
    chart_pie = choose_optimal_chart(df_pie)
    assert chart_pie["chart_type"] == "pie"
    assert chart_pie["x_axis"] == "country"
    assert chart_pie["y_axis"] == "revenue"

    # D. Ranking (high cardinality categorical + numeric)
    df_rank = pd.DataFrame({"name": [f"user_{i}" for i in range(15)], "score": [i * 10 for i in range(15)]})
    chart_rank = choose_optimal_chart(df_rank)
    assert chart_rank["chart_type"] == "horizontal_bar"
    assert chart_rank["x_axis"] == "name"
    assert chart_rank["y_axis"] == "score"

    # E. Grouped Bar (multiple categorical + numeric)
    df_grouped = pd.DataFrame(
        {"department": ["HR", "HR", "Sales", "Sales"], "gender": ["F", "M", "F", "M"], "count": [10, 5, 20, 15]}
    )
    chart_grp = choose_optimal_chart(df_grouped)
    assert chart_grp["chart_type"] == "grouped_bar"
    assert chart_grp["x_axis"] == "department"
    assert chart_grp["y_axis"] == "count"
    assert chart_grp["group_by"] == "gender"

    # 3. Format Chart payload check
    payload = format_chart_js_payload(df_pie, chart_pie)
    assert "labels" in payload
    assert "datasets" in payload
    assert len(payload["labels"]) == len(df_pie)
    assert len(payload["datasets"]) == 1


def test_api_dashboard_integration():
    # 1. Login user to get JWT token
    login_response = client.post(
        "/api/v1/auth/login", json={"email": "dashboard@example.com", "password": "password123"}
    )
    assert login_response.status_code == 200
    token = login_response.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    # 2. Generate a temporary CSV dataset matching the mock query structure
    csv_content = (
        "region,revenue,quantity\n"
        "North,6000.0,5\n"
        "South,8000.0,10\n"
        "East,2000.0,8\n"
        "West,900.0,20\n"
        "North,1800.0,15\n"
    )
    csv_file = "test_dashboard_data.csv"
    with open(csv_file, "w") as f:
        f.write(csv_content)

    try:
        # 3. Upload dataset
        with open(csv_file, "rb") as f:
            upload_response = client.post(
                "/api/v1/datasets/upload", files={"file": (csv_file, f, "text/csv")}, headers=headers
            )
        assert upload_response.status_code == 200
        dataset_id = upload_response.json()["id"]

        # 4. GET default dashboard
        dash_response = client.get(f"/api/v1/datasets/{dataset_id}/dashboard", headers=headers)
        assert dash_response.status_code == 200
        dash_data = dash_response.json()
        assert "metadata" in dash_data
        assert "kpi_cards" in dash_data
        assert "charts" in dash_data

        # 5. POST generate a new custom NL dashboard using the mock question "Show sales by region"
        gen_response = client.post(
            "/api/v1/dashboard/generate",
            json={"dataset_id": dataset_id, "question": "Show sales by region"},
            headers=headers,
        )
        assert gen_response.status_code == 200
        gen_data = gen_response.json()
        assert "id" in gen_data
        assert "NL Dashboard" in gen_data["name"]
        dashboard_id = gen_data["id"]

        # 6. GET dashboard by ID from history
        get_response = client.get(f"/api/v1/dashboard/{dashboard_id}", headers=headers)
        assert get_response.status_code == 200
        get_data = get_response.json()
        assert get_data["id"] == dashboard_id
        assert "widgets" in get_data

        # 7. GET dashboard history list
        history_response = client.get("/api/v1/dashboard/history", headers=headers)
        assert history_response.status_code == 200
        history_data = history_response.json()
        assert len(history_data) >= 1
        assert any(d["id"] == dashboard_id for d in history_data)

    finally:
        if os.path.exists(csv_file):
            os.remove(csv_file)

        uploads_dir = os.path.join("backend", "data", "uploads")
        if os.path.exists(uploads_dir):
            for file in os.listdir(uploads_dir):
                if file.startswith("u_") or file.endswith(".csv"):
                    try:
                        os.remove(os.path.join(uploads_dir, file))
                    except Exception:
                        pass
