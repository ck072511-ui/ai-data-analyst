import os
import sys

import pandas as pd

# Adjust path to find backend
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app.services.profiling_service import (
    detect_outliers_iqr,
    detect_outliers_zscore,
    generate_data_profile,
    get_date_pattern,
    is_email_address,
    is_phone_number,
)


def test_phone_number_validation():
    assert is_phone_number("+1-234-567-8901") is True
    assert is_phone_number("1234567") is True
    assert is_phone_number("(123) 456-7890") is True
    assert is_phone_number("123-456") is False  # too short
    assert is_phone_number("invalid-phone") is False
    assert is_phone_number(None) is False


def test_email_address_validation():
    assert is_email_address("test@example.com") is True
    assert is_email_address("user.name+alias@domain.co.uk") is True
    assert is_email_address("malformed@com") is False
    assert is_email_address("no-at-sign.com") is False
    assert is_email_address(None) is False


def test_date_pattern_retrieval():
    assert get_date_pattern("2024-02-15") == "YYYY-MM-DD"
    assert get_date_pattern("15/02/2024") == "DD/MM/YYYY"
    assert get_date_pattern("1 Feb 2024") == "DD Month YYYY"
    assert get_date_pattern("Not a date") is None
    assert get_date_pattern(None) is None


def test_outlier_detectors():
    # Symmetric data with 1 extreme outlier
    data = pd.Series([10, 12, 11, 13, 12, 11, 10, 12, 110])  # 110 is extreme outlier

    iqr_count, iqr_pct, iqr_list = detect_outliers_iqr(data)
    assert iqr_count == 1
    assert 110.0 in iqr_list

    # Standard normal series has no outliers beyond 3 std, construct 50 elements with 1 outlier
    normal_data = pd.Series([1.0] * 50 + [100.0])  # 100.0 is an outlier
    z_count, z_pct, z_list = detect_outliers_zscore(normal_data)
    assert z_count == 1
    assert 100.0 in z_list


def test_complete_profiling_engine():
    # Construct synthetic dataframe containing all Sprint 2.2 quality issues
    df = pd.DataFrame(
        {
            "emails": ["a@b.com", "c@d.org", "invalid-email", "e@f.net", "g@h.com"] * 3,
            "phones": ["+1 555-0199", "5550232", "555-0129", "invalid-phone", "555-0321"] * 3,
            "mixed_col": [25, 30, "Unknown", 40, 25] * 3,
            "empty_col": [None, "", "  ", None, None] * 3,
            "constant_col": ["active"] * 15,
            "dates_inconsistent": ["2024-02-01", "02/01/24", "2024-02-03", "2024-02-04", "02/01/24"] * 3,
            "numerical_col": [10.0, 20.0, 15.0, 12.0, 100.0] * 3,  # 100 is outlier
            "cardinality_col": [f"val_{i}" for i in range(15)],  # unique count = 15 (100% unique)
            "dup_col_1": [1, 2, 3, 4, 1] * 3,
            "dup_col_2": [1, 2, 3, 4, 1] * 3,  # identical to dup_col_1
        }
    )

    # Save a temporary file path
    temp_file = "temp_test_profile.csv"
    df.to_csv(temp_file, index=False)

    try:
        profile = generate_data_profile(df, temp_file)

        # Verify 1. general structure
        assert profile["row_count"] == 15
        assert profile["col_count"] == 10

        # Verify 3. Duplicate columns (dup_col_1 and dup_col_2)
        dup_cols = profile["quality_report"]["duplicate_columns"]
        assert ["dup_col_1", "dup_col_2"] in dup_cols or ["dup_col_2", "dup_col_1"] in dup_cols

        # Verify 4. Outliers
        outliers = profile["quality_report"]["outliers"]["by_column"]["numerical_col"]
        assert outliers["iqr_count"] == 3
        assert 100.0 in outliers["iqr_outliers"]

        # Verify 5. Mixed types
        assert "mixed_col" in profile["quality_report"]["mixed_data_types"]

        # Verify 6. Empty columns (empty_col only contains NaN, empty strings, and spaces)
        assert "empty_col" in profile["quality_report"]["empty_columns"]

        # Verify 7. Constant columns
        assert "constant_col" in profile["quality_report"]["constant_columns"]

        # Verify 8. Invalid dates (mix of YYYY-MM-DD and DD/MM/YY)
        assert any(row["column"] == "dates_inconsistent" for row in profile["quality_report"]["invalid_dates"])

        # Verify 9. Invalid emails (invalid-email)
        assert "emails" in profile["quality_report"]["invalid_emails"]["affected_columns"]
        assert profile["quality_report"]["invalid_emails"]["affected_columns"]["emails"]["invalid_count"] == 3

        # Verify 10. Invalid phones (invalid-phone)
        assert "phones" in profile["quality_report"]["invalid_phones"]["affected_columns"]
        assert profile["quality_report"]["invalid_phones"]["affected_columns"]["phones"]["invalid_count"] == 3

        # Verify 11. High cardinality
        assert any(row["column"] == "cardinality_col" for row in profile["quality_report"]["high_cardinality"])

        # Verify 12. Correlation analysis
        assert "dup_col_1" in profile["correlation_analysis"]["correlation_matrix"]["columns"]

        # Verify 13. Numerical statistics
        assert "numerical_col" in profile["numerical_statistics"]
        stats = profile["numerical_statistics"]["numerical_col"]
        assert stats["mean"] is not None
        assert stats["quartiles"]["q1"] is not None

    finally:
        if os.path.exists(temp_file):
            os.remove(temp_file)


def test_exact_row_duplicates():
    # Construct df with exact row duplicates
    df = pd.DataFrame({"A": [1, 2, 3, 1], "B": ["X", "Y", "Z", "X"]})
    temp_file = "temp_test_duplicates.csv"
    df.to_csv(temp_file, index=False)
    try:
        profile = generate_data_profile(df, temp_file)
        assert profile["quality_report"]["duplicate_rows"]["count"] == 1
        assert profile["quality_report"]["duplicate_rows"]["pct"] == 25.0
        assert len(profile["quality_report"]["duplicate_rows"]["sample_records"]) == 1
        assert profile["quality_report"]["duplicate_rows"]["sample_records"][0]["A"] == 1
    finally:
        if os.path.exists(temp_file):
            os.remove(temp_file)
