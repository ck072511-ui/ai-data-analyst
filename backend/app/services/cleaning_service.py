import re
from typing import Any, Dict, Tuple

import numpy as np
import pandas as pd

from app.services.profiling_service import is_email_address


def apply_cleaning_operations(df: pd.DataFrame, config: Dict[str, Any]) -> Tuple[pd.DataFrame, Dict[str, Any]]:
    df_cleaned = df.copy()

    rows_before = len(df)
    cols_before = len(df.columns)

    operations_applied = []
    total_cells_modified = 0
    rows_removed = 0
    cols_removed = 0

    # Helper to count cell changes on a series
    def count_changes(series_orig: pd.Series, series_new: pd.Series) -> int:
        # Align indexes and count differences
        aligned_orig = series_orig.loc[series_new.index]
        # Treat NaNs as equal if both are NaN, otherwise compare
        mask_diff = (aligned_orig != series_new) & ~(aligned_orig.isna() & series_new.isna())
        return int(mask_diff.sum())

    # 1. Whitespace Cleaning (Trim spaces)
    if config.get("whitespace", {}).get("apply", False):
        for col in df_cleaned.columns:
            if pd.api.types.is_object_dtype(df_cleaned[col]):
                orig = df_cleaned[col].copy()
                df_cleaned[col] = df_cleaned[col].astype(str).str.strip()
                # Restore NaNs/Nones
                df_cleaned[col] = df_cleaned[col].replace(["nan", "None", "<NA>"], np.nan)
                total_cells_modified += count_changes(orig, df_cleaned[col])
        operations_applied.append("Whitespace trimming applied to text columns.")

    # 2. Text Normalization
    text_norm_conf = config.get("text_normalization", {})
    if text_norm_conf.get("apply", False):
        norm_strategies = text_norm_conf.get("strategies", {})
        for col, strategy in norm_strategies.items():
            if col in df_cleaned.columns:
                orig = df_cleaned[col].copy()
                if strategy == "upper":
                    df_cleaned[col] = df_cleaned[col].astype(str).str.upper()
                elif strategy == "lower":
                    df_cleaned[col] = df_cleaned[col].astype(str).str.lower()
                elif strategy == "title":
                    df_cleaned[col] = df_cleaned[col].astype(str).str.title()
                # Restore NaNs
                df_cleaned[col] = df_cleaned[col].replace(["NAN", "NONE", "nan", "None", "<NA>"], np.nan)
                total_cells_modified += count_changes(orig, df_cleaned[col])
        if norm_strategies:
            operations_applied.append(f"Text case normalization applied to {len(norm_strategies)} column(s).")

    # 3. Mixed Data Types Normalization
    mixed_conf = config.get("mixed_types", {})
    if mixed_conf.get("apply", False):
        val_repl = mixed_conf.get("normalization_value", None)
        # We can map standard string descriptors of null (case insensitive) to NaN or replacement val
        null_descriptors = ["unknown", "n/a", "null", "none", "nan", ""]
        cells_changed_mixed = 0
        for col in df_cleaned.columns:
            orig = df_cleaned[col].copy()
            if pd.api.types.is_object_dtype(df_cleaned[col]):
                # Map to replacement value
                mapped = df_cleaned[col].apply(
                    lambda x: val_repl if not pd.isnull(x) and str(x).strip().lower() in null_descriptors else x
                )
                df_cleaned[col] = mapped
                cells_changed_mixed += count_changes(orig, df_cleaned[col])
        if cells_changed_mixed > 0:
            total_cells_modified += cells_changed_mixed
            operations_applied.append("Normalized mixed datatype placeholders (Unknown, N/A, null, None).")

    # 4. Standardize Invalid Dates
    date_conf = config.get("invalid_dates", {})
    if date_conf.get("apply", False):
        date_cols = date_conf.get("columns", [])
        target_format = date_conf.get("format", "YYYY-MM-DD")
        py_format = "%Y-%m-%d" if target_format == "YYYY-MM-DD" else "%Y-%m-%d"  # default to YYYY-MM-DD

        for col in date_cols:
            if col in df_cleaned.columns:
                orig = df_cleaned[col].copy()

                def parse_date_element(x):
                    if pd.isnull(x):
                        return pd.NaT
                    try:
                        if isinstance(x, str) and "-" in x and len(x.split("-")[0]) == 4:
                            return pd.to_datetime(x, format="mixed")
                        return pd.to_datetime(x, dayfirst=True, format="mixed")
                    except Exception:
                        return pd.NaT

                parsed = pd.to_datetime(df_cleaned[col].apply(parse_date_element), errors="coerce")
                # Keep values that successfully parsed, otherwise fallback to original value
                df_cleaned[col] = parsed.dt.strftime(py_format).where(parsed.notnull(), df_cleaned[col])
                # Convert string representation of NaT to NaN
                df_cleaned[col] = df_cleaned[col].replace(["NaT", "nan"], np.nan)
                total_cells_modified += count_changes(orig, df_cleaned[col])
        if date_cols:
            operations_applied.append(f"Standardized date formats for {len(date_cols)} column(s).")

    # 5. Invalid Emails Handling
    email_conf = config.get("invalid_emails", {})
    if email_conf.get("apply", False):
        email_cols = email_conf.get("columns", [])
        strategy = email_conf.get("strategy", "remove")  # "remove" (nullify) or "mark" (INVALID_EMAIL)

        for col in email_cols:
            if col in df_cleaned.columns:
                orig = df_cleaned[col].copy()

                def clean_email(val):
                    if pd.isnull(val):
                        return val
                    if is_email_address(val):
                        return val
                    return np.nan if strategy == "remove" else "INVALID_EMAIL"

                df_cleaned[col] = df_cleaned[col].apply(clean_email)
                total_cells_modified += count_changes(orig, df_cleaned[col])
        if email_cols:
            operations_applied.append(f"Handled invalid email entries in {len(email_cols)} column(s).")

    # 6. Invalid Phone Numbers Normalization
    phone_conf = config.get("invalid_phones", {})
    if phone_conf.get("apply", False):
        phone_cols = phone_conf.get("columns", [])
        for col in phone_cols:
            if col in df_cleaned.columns:
                orig = df_cleaned[col].copy()

                def clean_phone(val):
                    if pd.isnull(val):
                        return val
                    val_str = str(val).strip()
                    # Check if valid phone, then keep only digits/plus prefix
                    cleaned = re.sub(r"[^\d+]", "", val_str)
                    if len(cleaned) >= 7 and len(cleaned) <= 15:
                        return cleaned
                    # Malformed: set to nan or keep cleaned digits
                    return cleaned if len(cleaned) > 0 else np.nan

                df_cleaned[col] = df_cleaned[col].apply(clean_phone)
                total_cells_modified += count_changes(orig, df_cleaned[col])
        if phone_cols:
            operations_applied.append(f"Normalized phone formatting for {len(phone_cols)} column(s).")

    # 7. Outliers Handling
    outlier_conf = config.get("outliers", {})
    if outlier_conf.get("apply", False):
        outlier_cols = outlier_conf.get("columns", [])
        strategy = outlier_conf.get("strategy", "cap")  # "cap" (Winsorize) or "remove" (drop rows)

        rows_to_drop = set()
        for col in outlier_cols:
            if col in df_cleaned.columns and pd.api.types.is_numeric_dtype(df_cleaned[col]):
                series = df_cleaned[col]
                q1 = series.quantile(0.25)
                q3 = series.quantile(0.75)
                iqr = q3 - q1
                lower_bound = q1 - 1.5 * iqr
                upper_bound = q3 + 1.5 * iqr

                if strategy == "cap":
                    orig = series.copy()
                    # Clip values between lower and upper bounds
                    df_cleaned[col] = series.clip(lower=lower_bound, upper=upper_bound)
                    total_cells_modified += count_changes(orig, df_cleaned[col])
                elif strategy == "remove":
                    outlier_indices = series[(series < lower_bound) | (series > upper_bound)].index
                    rows_to_drop.update(outlier_indices)

        if strategy == "remove" and rows_to_drop:
            rows_removed += len(rows_to_drop)
            df_cleaned = df_cleaned.drop(index=list(rows_to_drop))
            operations_applied.append(f"Removed {len(rows_to_drop)} rows containing numeric outliers.")
        elif strategy == "cap" and outlier_cols:
            operations_applied.append(f"Capped/Winsorized outlier values in {len(outlier_cols)} columns.")

    # 8. Missing Values Imputation
    missing_conf = config.get("missing_values", {})
    if missing_conf.get("apply", False):
        strategies = missing_conf.get("strategies", {})
        constant_vals = missing_conf.get("constant_values", {})
        cols_to_drop = []
        rows_to_drop = set()

        for col, strat in strategies.items():
            if col in df_cleaned.columns:
                series = df_cleaned[col]
                if series.isnull().sum() == 0:
                    continue

                orig = series.copy()
                if strat == "mean" and pd.api.types.is_numeric_dtype(series):
                    val = float(series.mean())
                    df_cleaned[col] = series.fillna(val)
                    total_cells_modified += count_changes(orig, df_cleaned[col])
                elif strat == "median" and pd.api.types.is_numeric_dtype(series):
                    val = float(series.median())
                    df_cleaned[col] = series.fillna(val)
                    total_cells_modified += count_changes(orig, df_cleaned[col])
                elif strat == "mode":
                    mode_series = series.mode()
                    if not mode_series.empty:
                        val = mode_series.iloc[0]
                        df_cleaned[col] = series.fillna(val)
                        total_cells_modified += count_changes(orig, df_cleaned[col])
                elif strat == "constant":
                    val = constant_vals.get(col, "Missing")
                    # Try converting value to column dtype if applicable
                    try:
                        if pd.api.types.is_numeric_dtype(series):
                            val = float(val) if "." in str(val) else int(val)
                    except Exception:
                        pass
                    df_cleaned[col] = series.fillna(val)
                    total_cells_modified += count_changes(orig, df_cleaned[col])
                elif strat == "ffill":
                    df_cleaned[col] = series.ffill()
                    total_cells_modified += count_changes(orig, df_cleaned[col])
                elif strat == "bfill":
                    df_cleaned[col] = series.bfill()
                    total_cells_modified += count_changes(orig, df_cleaned[col])
                elif strat == "drop_rows":
                    null_indices = series[series.isnull()].index
                    rows_to_drop.update(null_indices)
                elif strat == "drop_columns":
                    cols_to_drop.append(col)

        if rows_to_drop:
            rows_removed += len(rows_to_drop)
            df_cleaned = df_cleaned.drop(index=list(rows_to_drop))
            operations_applied.append(f"Dropped {len(rows_to_drop)} rows due to missing cell strategies.")
        if cols_to_drop:
            cols_removed += len(cols_to_drop)
            df_cleaned = df_cleaned.drop(columns=cols_to_drop)
            operations_applied.append(f"Dropped columns: {', '.join(cols_to_drop)} containing nulls.")
        elif len(strategies) > 0:
            operations_applied.append(f"Imputed missing fields on {len(strategies)} column(s).")

    # 9. Constant Columns Dropping
    if config.get("constant_columns", {}).get("apply", False):
        const_cols = [col for col in df_cleaned.columns if df_cleaned[col].dropna().nunique() == 1]
        if const_cols:
            cols_removed += len(const_cols)
            df_cleaned = df_cleaned.drop(columns=const_cols)
            operations_applied.append(f"Removed constant column(s): {', '.join(const_cols)}")

    # 10. Empty Columns Dropping
    if config.get("empty_columns", {}).get("apply", False):
        empty_cols = []
        for col in df_cleaned.columns:
            col_series = df_cleaned[col]
            clean_series = col_series.dropna()
            if clean_series.empty:
                empty_cols.append(col)
            elif pd.api.types.is_object_dtype(col_series):
                if clean_series.astype(str).str.strip().eq("").all():
                    empty_cols.append(col)

        if empty_cols:
            cols_removed += len(empty_cols)
            df_cleaned = df_cleaned.drop(columns=empty_cols)
            operations_applied.append(f"Removed 100% empty column(s): {', '.join(empty_cols)}")

    # 11. Duplicate Columns Dropping
    if config.get("duplicate_columns", {}).get("apply", False):
        cols_to_drop = []
        cols_list = list(df_cleaned.columns)
        for i in range(len(cols_list)):
            for j in range(i + 1, len(cols_list)):
                c1 = cols_list[i]
                c2 = cols_list[j]
                if c2 not in cols_to_drop and df_cleaned[c1].equals(df_cleaned[c2]):
                    cols_to_drop.append(c2)
        if cols_to_drop:
            cols_removed += len(cols_to_drop)
            df_cleaned = df_cleaned.drop(columns=cols_to_drop)
            operations_applied.append(f"Removed identical content column(s): {', '.join(cols_to_drop)}")

    # 12. Duplicate Row Removal
    if config.get("duplicate_rows", {}).get("apply", False):
        dups_count = int(df_cleaned.duplicated().sum())
        if dups_count > 0:
            rows_removed += dups_count
            df_cleaned = df_cleaned.drop_duplicates(keep="first")
            operations_applied.append(f"Removed {dups_count} duplicate row records.")

    # Reindex df_cleaned to reset index if rows were dropped
    if rows_removed > 0:
        df_cleaned = df_cleaned.reset_index(drop=True)

    rows_after = len(df_cleaned)
    cols_after = len(df_cleaned.columns)

    # Calculate potential data loss metrics
    if rows_before > 0:
        pct_rows_lost = (rows_before - rows_after) / rows_before * 100
    else:
        pct_rows_lost = 0.0

    if pct_rows_lost > 15:
        potential_data_loss = f"High ({round(pct_rows_lost, 2)}% rows dropped)"
    elif pct_rows_lost > 5:
        potential_data_loss = f"Medium ({round(pct_rows_lost, 2)}% rows dropped)"
    elif pct_rows_lost > 0:
        potential_data_loss = f"Low ({round(pct_rows_lost, 2)}% rows dropped)"
    else:
        potential_data_loss = "None"

    preview_report = {
        "rows_before": rows_before,
        "rows_after": rows_after,
        "columns_before": cols_before,
        "columns_after": cols_after,
        "estimated_changes": total_cells_modified,
        "operations_to_apply": operations_applied if operations_applied else ["No cleaning operations required."],
        "potential_data_loss": potential_data_loss,
    }

    return df_cleaned, preview_report
