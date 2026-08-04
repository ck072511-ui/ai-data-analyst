import os
import sys

import pytest
from sqlalchemy import text
from sqlalchemy.orm import sessionmaker

# Adjust path to find backend
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

# Set environment variables for testing before importing settings
os.environ["DATABASE_URL"] = "sqlite:///./test_sprint_2_4.db"
os.environ["SECRET_KEY"] = "test-secret-key-must-be-long-enough-32-chars-at-least"
os.environ["ENVIRONMENT"] = "development"

from app.core.database import get_sync_engine
from app.models.base import Base
from app.models.dataset import UserDataset
from app.models.user import User
from app.services.audit_service import get_audit_history, log_audit_entry
from app.services.recommendation_service import generate_recommendations
from app.services.versioning_service import create_initial_version, create_next_version, rollback_to_version

sync_engine = get_sync_engine()
SessionLocal = sessionmaker(bind=sync_engine)


@pytest.fixture(scope="module", autouse=True)
def setup_test_db():
    Base.metadata.drop_all(bind=sync_engine)
    Base.metadata.create_all(bind=sync_engine)

    session = SessionLocal()
    # Create test user
    user = User(
        id="user-sprint-2-4-uuid",
        email="sprint24@example.com",
        hashed_password="hashed_pass_placeholder",
        full_name="Sprint 2.4 User",
        role="Admin",
        is_active=1,
    )
    session.add(user)
    session.commit()
    session.close()
    yield
    Base.metadata.drop_all(bind=sync_engine)


def test_heuristic_recommendation_engine():
    """Verifies that recommendation_service correctly triggers rule matches on quality reports."""
    mock_profile = {
        "quality_score": 75,
        "quality_report": {
            "missing_values": {
                "total_missing": 100,
                "missing_pct": 10.0,
                "by_column": {"salary": 100},
                "top_affected_columns": [{"column": "salary", "count": 100, "pct": 40.0}],
            },
            "duplicate_rows": {"count": 12, "pct": 3.5},
            "duplicate_columns": [["col1", "col2"]],
            "invalid_dates": [{"column": "joined_date", "inconsistent_formats": ["%Y-%m-%d", "%d/%m/%Y"]}],
            "mixed_data_types": {"age": ["int", "str"]},
            "empty_columns": ["notes"],
            "constant_columns": ["status_flag"],
            "invalid_emails": {"affected_columns": {"email": {"invalid_count": 5}}},
            "invalid_phones": {"affected_columns": {"phone": {"invalid_count": 8}}},
        },
        "correlation_analysis": {"high_correlations": [{"col1": "col_a", "col2": "col_b", "coefficient": 0.95}]},
        "column_types": {"numerical": ["salary"], "categorical": []},
    }

    recs = generate_recommendations(mock_profile)

    # Assert specific rules are matched
    rec_texts = [r["recommendation"] for r in recs]
    assert "Remove Duplicate Rows" in rec_texts
    assert "Remove Duplicate Columns" in rec_texts
    assert "Drop Column 'salary'" in rec_texts  # missingness > 30%
    assert "Standardize Date Format for 'joined_date'" in rec_texts
    assert "Normalize Mixed Types in 'age'" in rec_texts
    assert "Remove Empty Columns" in rec_texts
    assert "Remove Constant Columns" in rec_texts
    assert "Handle Invalid Emails in 'email'" in rec_texts
    assert "Normalize Phone Formatting in 'phone'" in rec_texts
    assert "Review correlated features 'col_a' / 'col_b'" in rec_texts

    # Confirm expected confidence scores
    for r in recs:
        assert 0 <= r["confidence_score"] <= 100
        assert r["issue"] != ""
        assert r["reason"] != ""
        assert r["expected_impact"] != ""


def test_dataset_versioning_and_rollback_flow():
    """Verifies creation of snapshots, child increments, pointer redirects, and database restores."""
    session = SessionLocal()

    # 1. Create a dummy dataset
    dataset = UserDataset(
        id="dataset-versioning-test-uuid",
        user_id="user-sprint-2-4-uuid",
        filename="test_versioning.csv",
        table_name="test_versioning_table",
        file_path="test_versioning_path.csv",
        row_count=100,
        col_count=5,
        columns=["id", "name", "age", "joined_date", "email"],
        schema_info={"id": {"dtype": "int"}},
        profile_info={"quality_score": 80},
    )
    session.add(dataset)
    session.commit()

    # Mock physical file exist for copying
    with open("test_versioning_path.csv", "w") as f:
        f.write("id,name,age,joined_date,email\n1,Alice,25,2021-01-01,alice@example.com")

    # Mock sync database tables structure
    with sync_engine.begin() as conn:
        conn.execute(text("CREATE TABLE test_versioning_table (id INTEGER)"))
    v1_record = None
    v2_record = None
    try:
        # 2. Test create initial version (V1)
        v1_record = create_initial_version(session, dataset)
        assert v1_record.version_number == 1
        assert v1_record.parent_version is None
        assert "Initial Upload" in v1_record.operations_applied

        # Pointers update
        assert dataset.file_path.endswith("_v1.csv")
        assert dataset.table_name == "test_versioning_table_v1"

        # Verify snapshot files on disk
        assert os.path.exists(v1_record.file_path)

        # 3. Test create new version (V2)
        def save_df_callback(path, ext):
            with open(path, "w") as f_new:
                f_new.write("id,name,age,joined_date,email\n1,Alice,25,2021-01-01,alice@example.com")

        # Mock writing to active table
        with sync_engine.begin() as conn:
            conn.execute(text("CREATE TABLE IF NOT EXISTS test_versioning_table_v1 (id INTEGER)"))

        v2_record = create_next_version(
            db_session=session,
            dataset=dataset,
            operations=["Remove Duplicate Rows", "Trim Whitespaces"],
            row_count=98,
            col_count=5,
            columns=dataset.columns,
            schema_info=dataset.schema_info,
            profile_info={"quality_score": 95},
            save_df_callback=save_df_callback,
        )
        assert v2_record.version_number == 2
        assert v2_record.parent_version == 1
        assert "Remove Duplicate Rows" in v2_record.operations_applied
        assert dataset.row_count == 98
        assert dataset.profile_info["quality_score"] == 95

        # 4. Test rollback back to V1
        rolled_back_version = rollback_to_version(session, dataset, 1)
        assert rolled_back_version.version_number == 1
        assert dataset.row_count == 100
        assert dataset.profile_info["quality_score"] == 80
        assert dataset.table_name == "test_versioning_table_v1"

    finally:
        # Cleanup physical file mocks
        if os.path.exists("test_versioning_path.csv"):
            os.remove("test_versioning_path.csv")
        if v1_record and os.path.exists(v1_record.file_path):
            os.remove(v1_record.file_path)
        if v2_record and os.path.exists(v2_record.file_path):
            os.remove(v2_record.file_path)

        # Cleanup DB tables
        with sync_engine.begin() as conn:
            conn.execute(text("DROP TABLE IF EXISTS test_versioning_table"))
            conn.execute(text("DROP TABLE IF EXISTS test_versioning_table_v1"))
            conn.execute(text("DROP TABLE IF EXISTS test_versioning_table_v2"))
            if v2_record:
                conn.execute(text(f"DROP TABLE IF EXISTS {v2_record.table_name}"))
        session.close()


def test_cleaning_audit_trail_logging():
    """Verifies that log_audit_entry stores audit logs and get_audit_history queries correct lists."""
    session = SessionLocal()

    # Create mock dataset row
    dataset = UserDataset(
        id="dataset-audit-test-uuid",
        user_id="user-sprint-2-4-uuid",
        filename="test_audit.csv",
        table_name="test_audit_table",
        file_path="test_audit_path.csv",
        row_count=100,
        col_count=5,
        columns=["id", "name"],
        schema_info={},
        profile_info={},
    )
    session.add(dataset)
    session.commit()

    try:
        # Log clean audit
        audit = log_audit_entry(
            db_session=session,
            dataset=dataset,
            user_id="user-sprint-2-4-uuid",
            user_email="sprint24@example.com",
            operations_applied=["Drop Constant Columns", "Winsorize Outliers"],
            rows_changed=2,
            columns_changed=1,
            quality_score_before=70,
            quality_score_after=88,
            version_created=2,
        )

        assert audit.dataset_id == dataset.id
        assert audit.user_email == "sprint24@example.com"
        assert audit.version_created == 2
        assert "Winsorize Outliers" in audit.operations_applied
        assert audit.rows_changed == 2
        assert audit.columns_changed == 1
        assert audit.quality_score_before == 70
        assert audit.quality_score_after == 88

        # Query audit history
        history = get_audit_history(session, dataset.id)
        assert len(history) == 1
        assert history[0].id == audit.id

    finally:
        session.close()
