import json
import os
import shutil
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
        email="test@example.com",
        hashed_password=get_password_hash("password123"),
        full_name="Test User",
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
        # Close connection pool
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
        except Exception as e:
            print(f"Warning: could not delete test_analytics.db: {e}")

    uploads_dir = os.path.join("backend", "data", "uploads")
    if os.path.exists(uploads_dir):
        shutil.rmtree(uploads_dir)
    elif os.path.exists("data/uploads"):
        shutil.rmtree("data/uploads")


def test_full_workflow():
    # 1. Login user to get JWT token
    login_response = client.post("/api/v1/auth/login", json={"email": "test@example.com", "password": "password123"})
    assert login_response.status_code == 200
    token = login_response.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    # 2. Generate a temporary CSV dataset
    csv_content = (
        "region,revenue,quantity\n"
        "North,6000.0,5\n"
        "South,8000.0,10\n"
        "East,2000.0,8\n"
        "West,900.0,20\n"
        "North,1800.0,15\n"
    )
    csv_file = "test_sales.csv"
    with open(csv_file, "w") as f:
        f.write(csv_content)

    # 3. Upload dataset
    with open(csv_file, "rb") as f:
        upload_response = client.post(
            "/api/v1/datasets/upload", files={"file": (csv_file, f, "text/csv")}, headers=headers
        )
    os.remove(csv_file)

    assert upload_response.status_code == 200
    dataset_info = upload_response.json()
    assert dataset_info["filename"] == "test_sales.csv"
    assert dataset_info["row_count"] == 5
    assert dataset_info["col_count"] == 3
    assert "region" in dataset_info["columns"]
    assert "revenue" in dataset_info["columns"]
    dataset_id = dataset_info["id"]
    table_name = dataset_info["table_name"]

    # 4. Get dataset details & dashboard preview
    details_response = client.get(f"/api/v1/datasets/{dataset_id}", headers=headers)
    assert details_response.status_code == 200
    details = details_response.json()
    assert len(details["preview"]) == 5
    assert "schema_info" in details
    assert details["schema_info"]["region"]["dtype"] == "object"
    assert details["schema_info"]["revenue"]["dtype"] == "float64"
    assert details["schema_info"]["revenue"]["mean"] == 3740.0

    # 5. List all user datasets
    list_response = client.get("/api/v1/datasets/", headers=headers)
    assert list_response.status_code == 200
    assert len(list_response.json()) >= 1
    assert list_response.json()[0]["id"] == dataset_id

    # 6. Ask Question: "Show total sales by region"
    query_response = client.post(
        "/api/v1/query/", json={"question": "Show total sales by region", "dataset_id": dataset_id}, headers=headers
    )
    assert query_response.status_code == 200
    query_data = query_response.json()

    assert query_data["success"] is True
    # Verify that the generated SQL queries the dynamic table name
    assert table_name in query_data["sql"]
    assert "region" in query_data["sql"]
    assert "revenue" in query_data["sql"]

    # Check that execution output has correct numbers
    # North sum should be 6000 + 1800 = 7800
    # South sum should be 8000
    data_rows = query_data["data"]
    assert len(data_rows) > 0
    north_sales = next(row for row in data_rows if row["region"] == "North")
    south_sales = next(row for row in data_rows if row["region"] == "South")
    # Verify values match (handling key casing / alias name)
    revenue_key = [k for k in north_sales.keys() if k != "region"][0]
    assert float(north_sales[revenue_key]) == 7800.0
    assert float(south_sales[revenue_key]) == 8000.0

    # Verify chart type auto selection (bar chart for categorical + numeric sales)
    assert query_data["chart_type"] == "bar"
    assert len(query_data["chart_data"]["labels"]) == len(data_rows)
    assert len(query_data["chart_data"]["datasets"]) == 1

    # 7. Delete dataset
    delete_response = client.delete(f"/api/v1/datasets/{dataset_id}", headers=headers)
    assert delete_response.status_code == 200
    assert delete_response.json()["success"] is True

    # 8. Verify deletion (table dropped)
    from sqlalchemy import create_engine, inspect

    sync_engine = create_engine("sqlite:///./test_analytics.db")
    inspector = inspect(sync_engine)
    assert table_name not in inspector.get_table_names()

    # 9. Verify dataset list is now empty
    list_response_after = client.get("/api/v1/datasets/", headers=headers)
    assert len(list_response_after.json()) == 0


def test_json_upload():
    # Login user to get JWT token
    login_response = client.post("/api/v1/auth/login", json={"email": "test@example.com", "password": "password123"})
    assert login_response.status_code == 200
    token = login_response.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    # Generate a temporary JSON dataset
    json_data = [
        {"item": "Laptop", "price": 1200.0, "qty": 2},
        {"item": "Mouse", "price": 25.0, "qty": 10},
        {"item": "Monitor", "price": 300.0, "qty": 5},
    ]
    json_file = "test_inventory.json"
    with open(json_file, "w") as f:
        json.dump(json_data, f)

    # Upload JSON
    with open(json_file, "rb") as f:
        upload_response = client.post(
            "/api/v1/datasets/upload", files={"file": (json_file, f, "application/json")}, headers=headers
        )
    os.remove(json_file)

    assert upload_response.status_code == 200
    dataset_info = upload_response.json()
    assert dataset_info["filename"] == "test_inventory.json"
    assert dataset_info["row_count"] == 3
    assert dataset_info["col_count"] == 3
    dataset_id = dataset_info["id"]

    # Delete dataset
    delete_response = client.delete(f"/api/v1/datasets/{dataset_id}", headers=headers)
    assert delete_response.status_code == 200


def test_excel_upload():
    # Login user to get JWT token
    login_response = client.post("/api/v1/auth/login", json={"email": "test@example.com", "password": "password123"})
    assert login_response.status_code == 200
    token = login_response.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    # Generate temporary Excel dataset using pandas
    import pandas as pd

    excel_data = {
        "employee": ["Alice", "Bob", "Charlie"],
        "salary": [70000, 80000, 95000],
        "dept": ["HR", "Eng", "Eng"],
    }
    df = pd.DataFrame(excel_data)
    excel_file = "test_employees.xlsx"
    df.to_excel(excel_file, index=False)

    # Upload Excel
    with open(excel_file, "rb") as f:
        upload_response = client.post(
            "/api/v1/datasets/upload",
            files={"file": (excel_file, f, "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")},
            headers=headers,
        )
    os.remove(excel_file)

    assert upload_response.status_code == 200
    dataset_info = upload_response.json()
    assert dataset_info["filename"] == "test_employees.xlsx"
    assert dataset_info["row_count"] == 3
    assert dataset_info["col_count"] == 3
    dataset_id = dataset_info["id"]

    # Delete dataset
    delete_response = client.delete(f"/api/v1/datasets/{dataset_id}", headers=headers)
    assert delete_response.status_code == 200


def test_database_connectivity():
    # Login user to get JWT token
    login_response = client.post("/api/v1/auth/login", json={"email": "test@example.com", "password": "password123"})
    assert login_response.status_code == 200
    token = login_response.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    # Create a temporary SQLite database for testing connection
    import sqlite3

    test_db_path = "backend/data/temp_test_remote.db" if os.path.exists("backend") else "data/temp_test_remote.db"
    os.makedirs(os.path.dirname(test_db_path), exist_ok=True)

    # Initialize SQLite database with a sample table
    conn = sqlite3.connect(test_db_path)
    cursor = conn.cursor()
    cursor.execute("DROP TABLE IF EXISTS sales_remote")
    cursor.execute("CREATE TABLE sales_remote (region TEXT, revenue REAL)")
    cursor.execute("INSERT INTO sales_remote VALUES ('North', 5000.0)")
    cursor.execute("INSERT INTO sales_remote VALUES ('South', 6000.0)")
    conn.commit()
    conn.close()

    try:
        # 1. Test database connection API (without saving)
        test_payload = {"db_type": "sqlite", "database": test_db_path}
        test_response = client.post("/api/v1/database/test", json=test_payload, headers=headers)
        assert test_response.status_code == 200
        assert test_response.json()["success"] is True

        # 2. Connect database (save configuration)
        connect_payload = {"name": "Test Remote DB", "db_type": "sqlite", "database": test_db_path}
        connect_response = client.post("/api/v1/database/connect", json=connect_payload, headers=headers)
        assert connect_response.status_code == 200
        conn_info = connect_response.json()
        assert conn_info["name"] == "Test Remote DB"
        assert conn_info["db_type"] == "sqlite"
        connection_id = conn_info["id"]

        # 3. List database connections
        list_response = client.get("/api/v1/database/list", headers=headers)
        assert list_response.status_code == 200
        connections = list_response.json()
        assert len(connections) >= 1
        assert any(c["id"] == connection_id for c in connections)

        # 4. Get Connection Schema
        schema_response = client.get(f"/api/v1/database/{connection_id}/schema", headers=headers)
        assert schema_response.status_code == 200
        schema_data = schema_response.json()["schema"]
        assert "sales_remote" in schema_data
        assert any(c["name"] == "region" for c in schema_data["sales_remote"])
        assert any(c["name"] == "revenue" for c in schema_data["sales_remote"])

        # 4.5 Test existing connection status (card-level test)
        card_test_response = client.post(f"/api/v1/database/{connection_id}/test", headers=headers)
        assert card_test_response.status_code == 200
        assert card_test_response.json()["success"] is True

        # 4.6 Edit database connection configuration (PUT)
        update_payload = {"name": "Updated Test Remote DB", "database": test_db_path}
        update_response = client.put(f"/api/v1/database/{connection_id}", json=update_payload, headers=headers)
        assert update_response.status_code == 200
        updated_info = update_response.json()
        assert updated_info["name"] == "Updated Test Remote DB"
        assert updated_info["database"] == test_db_path

        # 5. Query active connected database using NL2SQL
        query_response = client.post(
            "/api/v1/query/",
            json={"question": "Show total sales by region", "db_connection_id": connection_id},
            headers=headers,
        )
        assert query_response.status_code == 200
        query_data = query_response.json()
        assert query_data["success"] is True
        assert "sales_remote" in query_data["sql"]
        assert len(query_data["data"]) == 2

        # 6. Delete Database connection configuration
        delete_response = client.delete(f"/api/v1/database/{connection_id}", headers=headers)
        assert delete_response.status_code == 200

    finally:
        # Clean up temporary database file
        if os.path.exists(test_db_path):
            try:
                os.remove(test_db_path)
            except Exception:
                pass


if __name__ == "__main__":
    pytest.main([__file__])
