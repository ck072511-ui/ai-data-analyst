import os
import sys

import pandas as pd

# Adjust path to find backend
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app.services.cleaning_service import apply_cleaning_operations


def test_whitespace_and_text_normalization():
    df = pd.DataFrame({"text_col": ["  hello  ", "WORLD  ", "  Title Case  ", None]})

    config = {"whitespace": {"apply": True}, "text_normalization": {"apply": True, "strategies": {"text_col": "upper"}}}

    cleaned_df, report = apply_cleaning_operations(df, config)
    assert cleaned_df.loc[0, "text_col"] == "HELLO"
    assert cleaned_df.loc[1, "text_col"] == "WORLD"
    assert cleaned_df.loc[2, "text_col"] == "TITLE CASE"
    assert pd.isnull(cleaned_df.loc[3, "text_col"])
    assert report["estimated_changes"] == 5


def test_mixed_types_normalization():
    df = pd.DataFrame({"mixed": ["value", "Unknown", "N/A", "null", None]})
    config = {"mixed_types": {"apply": True, "normalization_value": "MISSING_FLAG"}}
    cleaned_df, report = apply_cleaning_operations(df, config)
    assert cleaned_df.loc[0, "mixed"] == "value"
    assert cleaned_df.loc[1, "mixed"] == "MISSING_FLAG"
    assert cleaned_df.loc[2, "mixed"] == "MISSING_FLAG"
    assert cleaned_df.loc[3, "mixed"] == "MISSING_FLAG"
    assert pd.isnull(
        cleaned_df.loc[4, "mixed"]
    )  # None doesn't map to replacement (it is raw NaN/None, which is left alone or handled by missing values)


def test_date_phone_email_normalizations():
    df = pd.DataFrame(
        {
            "dates": ["2024-02-15", "15/02/2024", "not-a-date"],
            "emails": ["valid@test.com", "invalid-email", None],
            "phones": ["+1 (555) 019-9232", "555-0231", "too-short"],
        }
    )
    config = {
        "invalid_dates": {"apply": True, "columns": ["dates"], "format": "YYYY-MM-DD"},
        "invalid_emails": {"apply": True, "columns": ["emails"], "strategy": "mark"},
        "invalid_phones": {"apply": True, "columns": ["phones"]},
    }
    cleaned_df, report = apply_cleaning_operations(df, config)

    # Dates: parsed correctly formatted to YYYY-MM-DD, third item kept original or set to NaN/nat
    assert cleaned_df.loc[0, "dates"] == "2024-02-15"
    assert cleaned_df.loc[1, "dates"] == "2024-02-15"

    # Emails
    assert cleaned_df.loc[0, "emails"] == "valid@test.com"
    assert cleaned_df.loc[1, "emails"] == "INVALID_EMAIL"

    # Phones: only digits and plus signs kept
    assert cleaned_df.loc[0, "phones"] == "+15550199232"
    assert cleaned_df.loc[1, "phones"] == "5550231"


def test_outlier_handling():
    # Symmetric data with one major outlier
    df = pd.DataFrame({"numeric": [10.0, 11.0, 12.0, 10.0, 11.0, 12.0, 100.0]})

    config = {"outliers": {"apply": True, "columns": ["numeric"], "strategy": "cap"}}
    cleaned_df, report = apply_cleaning_operations(df, config)
    # 100.0 is capped to upper bound (around 15.0)
    assert cleaned_df.loc[6, "numeric"] < 100.0

    config_remove = {"outliers": {"apply": True, "columns": ["numeric"], "strategy": "remove"}}
    cleaned_df_rm, report_rm = apply_cleaning_operations(df, config_remove)
    assert len(cleaned_df_rm) == 6
    assert report_rm["rows_after"] == 6


def test_missing_values_imputation():
    df = pd.DataFrame({"num_col": [10.0, 20.0, None, 30.0], "cat_col": ["A", "B", "A", None]})

    config = {
        "missing_values": {
            "apply": True,
            "strategies": {"num_col": "mean", "cat_col": "constant"},
            "constant_values": {"cat_col": "UNKNOWN_VAL"},
        }
    }

    cleaned_df, report = apply_cleaning_operations(df, config)
    assert cleaned_df.loc[2, "num_col"] == 20.0  # mean = (10+20+30)/3 = 20
    assert cleaned_df.loc[3, "cat_col"] == "UNKNOWN_VAL"


def test_empty_constant_and_duplicates():
    df = pd.DataFrame(
        {
            "empty": [None, None, None, None],
            "constant": [5, 5, 5, 5],
            "dup_col_1": [1, 2, 3, 1],
            "dup_col_2": [1, 2, 3, 1],
        }
    )

    config = {
        "empty_columns": {"apply": True},
        "constant_columns": {"apply": True},
        "duplicate_columns": {"apply": True},
        "duplicate_rows": {"apply": True},
    }

    cleaned_df, report = apply_cleaning_operations(df, config)

    # empty should be removed
    assert "empty" not in cleaned_df.columns
    # constant should be removed
    assert "constant" not in cleaned_df.columns
    # duplicate column (dup_col_2) should be removed
    assert "dup_col_1" in cleaned_df.columns
    assert "dup_col_2" not in cleaned_df.columns
    # duplicate row (index 3) should be removed
    assert len(cleaned_df) == 3
