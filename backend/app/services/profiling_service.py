import os
import re
from typing import Any, Dict, List, Tuple

import numpy as np
import pandas as pd


def is_phone_number(val: Any) -> bool:
    val_str = str(val).strip()
    if not val_str or val_str.lower() in ["nan", "none", "null", ""]:
        return False
    # Count digits
    digits = [c for c in val_str if c.isdigit()]
    if len(digits) < 7 or len(digits) > 15:
        return False
    # Consists of valid characters only
    return bool(re.match(r"^\+?[\d\s\-\(\)\.]{7,20}$", val_str))


def is_email_address(val: Any) -> bool:
    val_str = str(val).strip()
    if not val_str or val_str.lower() in ["nan", "none", "null", ""]:
        return False
    # Simple RFC 5322 regex
    email_regex = r"^[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+$"
    return bool(re.match(email_regex, val_str))


def get_date_pattern(val: Any) -> str:
    val_str = str(val).strip()
    if not val_str or val_str.lower() in ["nan", "none", "null", ""]:
        return None
    if re.match(r"^\d{4}-\d{2}-\d{2}$", val_str):
        return "YYYY-MM-DD"
    if re.match(r"^\d{2}/\d{2}/\d{4}$", val_str):
        return "DD/MM/YYYY"
    if re.match(r"^\d{2}-\d{2}-\d{4}$", val_str):
        return "DD-MM-YYYY"
    if re.match(r"^\d{4}/\d{2}/\d{2}$", val_str):
        return "YYYY/MM/DD"
    if re.match(r"^\d{1,2}\s+[A-Za-z]{3,}\s+\d{4}$", val_str):
        return "DD Month YYYY"
    if re.match(r"^[A-Za-z]{3,}\s+\d{1,2},\s+\d{4}$", val_str):
        return "Month DD, YYYY"
    if re.match(r"^\d{2}/\d{2}/\d{2}$", val_str):
        return "DD/MM/YY"
    if re.match(r"^\d{4}-\d{2}-\d{2}\s+\d{2}:\d{2}:\d{2}", val_str):
        return "YYYY-MM-DD HH:MM:SS"
    # Try parsing
    try:
        pd.to_datetime(val_str, format="mixed", errors="raise")
        return "Generic Date"
    except Exception:
        return None


def detect_outliers_iqr(series: pd.Series) -> Tuple[int, float, List[Any]]:
    clean_series = series.dropna()
    if clean_series.empty:
        return 0, 0.0, []
    try:
        q1 = clean_series.quantile(0.25)
        q3 = clean_series.quantile(0.75)
        iqr = q3 - q1
        lower_bound = q1 - 1.5 * iqr
        upper_bound = q3 + 1.5 * iqr
        outliers = clean_series[(clean_series < lower_bound) | (clean_series > upper_bound)]
        outlier_list = [float(x) for x in outliers.unique()[:10]]
        return len(outliers), float(round(len(outliers) / len(series) * 100, 2)), outlier_list
    except Exception:
        return 0, 0.0, []


def detect_outliers_zscore(series: pd.Series) -> Tuple[int, float, List[Any]]:
    clean_series = series.dropna()
    if clean_series.empty:
        return 0, 0.0, []
    try:
        mean = clean_series.mean()
        std = clean_series.std()
        if std == 0:
            return 0, 0.0, []
        z_scores = (clean_series - mean) / std
        outliers = clean_series[z_scores.abs() > 3]
        outlier_list = [float(x) for x in outliers.unique()[:10]]
        return len(outliers), float(round(len(outliers) / len(series) * 100, 2)), outlier_list
    except Exception:
        return 0, 0.0, []


def sanitize_value(val: Any) -> Any:
    """Helper to ensure values are JSON serializable (converts numpy types, handles nan)."""
    if pd.isnull(val):
        return None
    if isinstance(val, (int, np.integer, np.signedinteger)):
        return int(val)
    if isinstance(val, (np.floating, float)):
        return float(val) if not np.isnan(val) else None
    if isinstance(val, (np.bool_, bool)):
        return bool(val)
    if isinstance(val, (pd.Timestamp, np.datetime64)):
        return str(val)
    return str(val)


def generate_data_profile(df: pd.DataFrame, file_path: str) -> Dict[str, Any]:
    row_count = len(df)
    col_count = len(df.columns)

    # 1. Memory & Size
    try:
        mem_bytes = int(df.memory_usage(deep=True).sum())
        if mem_bytes >= 1024 * 1024:
            memory_usage = f"{round(mem_bytes / (1024 * 1024), 2)} MB"
        else:
            memory_usage = f"{round(mem_bytes / 1024, 2)} KB"
    except Exception:
        memory_usage = "N/A"

    try:
        size_bytes = os.path.getsize(file_path)
        if size_bytes >= 1024 * 1024:
            file_size = f"{round(size_bytes / (1024 * 1024), 2)} MB"
        else:
            file_size = f"{round(size_bytes / 1024, 2)} KB"
    except Exception:
        file_size = "N/A"

    # 2. Type Classification
    numerical_cols = []
    categorical_cols = []
    date_cols = []
    boolean_cols = []
    text_cols = []

    for col in df.columns:
        col_str = str(col)
        col_series = df[col]
        if pd.api.types.is_bool_dtype(col_series):
            boolean_cols.append(col_str)
        elif pd.api.types.is_numeric_dtype(col_series):
            numerical_cols.append(col_str)
        elif pd.api.types.is_datetime64_any_dtype(col_series):
            date_cols.append(col_str)
        else:
            # Check if boolean-like
            unique_vals = col_series.dropna().unique()
            if len(unique_vals) <= 2 and all(
                str(x).lower() in ["true", "false", "1", "0", "yes", "no"] for x in unique_vals
            ):
                boolean_cols.append(col_str)
                continue
            # Check if date-like
            non_null_series = col_series.dropna()
            if not non_null_series.empty and len(non_null_series) > 5:
                sample = non_null_series.head(20)
                try:
                    parsed_sample = pd.to_datetime(sample, format="mixed", errors="coerce")
                    if parsed_sample.notnull().sum() / len(sample) >= 0.85:
                        parsed_all = pd.to_datetime(col_series, format="mixed", errors="coerce")
                        if parsed_all.notnull().sum() / len(non_null_series) >= 0.85:
                            date_cols.append(col_str)
                            continue
                except Exception:
                    pass
            # Category vs Text
            unique_count = len(unique_vals)
            if row_count > 0 and (unique_count < 20 or (unique_count / row_count < 0.1)):
                categorical_cols.append(col_str)
            else:
                avg_length = non_null_series.astype(str).str.len().mean() if not non_null_series.empty else 0
                if avg_length > 30:
                    text_cols.append(col_str)
                else:
                    categorical_cols.append(col_str)

    # 3. Duplicate Detection
    dup_rows_count = int(df.duplicated().sum())
    dup_rows_pct = round((dup_rows_count / row_count * 100), 2) if row_count > 0 else 0.0

    # Grab duplicate samples
    dup_df = df[df.duplicated(keep="first")]
    sample_duplicates = []
    if not dup_df.empty:
        # Convert first 10 rows to lists of sanitized dicts
        for idx, row in dup_df.head(10).iterrows():
            row_dict = {str(c): sanitize_value(v) for c, v in row.items()}
            sample_duplicates.append(row_dict)

    # Duplicate columns
    duplicate_columns = []
    for i in range(col_count):
        for j in range(i + 1, col_count):
            c1 = df.columns[i]
            c2 = df.columns[j]
            if df[c1].equals(df[c2]):
                duplicate_columns.append([str(c1), str(c2)])

    # 4. Missing Value Analysis
    missing_by_col = {}
    total_missing_cells = 0
    total_cells = row_count * col_count

    for col in df.columns:
        col_str = str(col)
        m_count = int(df[col].isnull().sum())
        missing_by_col[col_str] = m_count
        total_missing_cells += m_count

    missing_pct = round((total_missing_cells / total_cells * 100), 2) if total_cells > 0 else 0.0

    # Top 10 affected columns
    top_affected_columns = [
        {"column": col, "count": int(cnt), "pct": round(cnt / row_count * 100, 2)}
        for col, cnt in missing_by_col.items()
        if cnt > 0
    ]
    top_affected_columns = sorted(top_affected_columns, key=lambda x: x["count"], reverse=True)[:10]

    # Filter out columns with no missing cells from by_column mapping to avoid json bloat
    missing_by_col_filtered = {col: cnt for col, cnt in missing_by_col.items() if cnt > 0}

    # 5. Outlier Detection (IQR & Z-score)
    outliers_report = {
        "total_outliers_iqr": 0,
        "pct_outliers_iqr": 0.0,
        "total_outliers_zscore": 0,
        "pct_outliers_zscore": 0.0,
        "by_column": {},
    }

    total_iqr_outliers = 0
    total_zscore_outliers = 0

    for col in numerical_cols:
        col_series = df[col]
        iqr_cnt, iqr_pct, iqr_list = detect_outliers_iqr(col_series)
        z_cnt, z_pct, z_list = detect_outliers_zscore(col_series)

        total_iqr_outliers += iqr_cnt
        total_zscore_outliers += z_cnt

        if iqr_cnt > 0 or z_cnt > 0:
            outliers_report["by_column"][col] = {
                "iqr_count": iqr_cnt,
                "iqr_pct": iqr_pct,
                "iqr_outliers": iqr_list,
                "zscore_count": z_cnt,
                "zscore_pct": z_pct,
                "zscore_outliers": z_list,
            }

    outliers_report["total_outliers_iqr"] = total_iqr_outliers
    outliers_report["pct_outliers_iqr"] = round(total_iqr_outliers / total_cells * 100, 2) if total_cells > 0 else 0.0
    outliers_report["total_outliers_zscore"] = total_zscore_outliers
    outliers_report["pct_outliers_zscore"] = (
        round(total_zscore_outliers / total_cells * 100, 2) if total_cells > 0 else 0.0
    )

    # 6. Mixed Data Type Detection
    mixed_data_types = {}
    for col in df.columns:
        col_str = str(col)
        non_null_vals = df[col].dropna()
        if not non_null_vals.empty:
            types = non_null_vals.map(type).unique()
            if len(types) > 1:
                mixed_data_types[col_str] = [t.__name__ for t in types]

    # 7. Empty Column Detection
    empty_columns = []
    for col in df.columns:
        col_str = str(col)
        col_series = df[col]
        # Drop true missing
        clean_series = col_series.dropna()
        if clean_series.empty:
            empty_columns.append(col_str)
        else:
            # If string type, check if it contains only whitespace
            if pd.api.types.is_object_dtype(col_series):
                is_empty = clean_series.astype(str).str.strip().eq("").all()
                if is_empty:
                    empty_columns.append(col_str)

    # 8. Constant Column Detection
    constant_columns = [str(col) for col in df.columns if df[col].dropna().nunique() == 1]

    # 9. Invalid Date Format Detection
    invalid_dates = []
    for col in df.columns:
        col_str = str(col)
        non_null_series = df[col].dropna()
        if non_null_series.empty:
            continue

        # Determine how many parse as dates and what formats are present
        patterns = []
        for val in non_null_series:
            pat = get_date_pattern(val)
            if pat:
                patterns.append(pat)

        if len(patterns) > 0 and (len(patterns) / len(non_null_series) >= 0.40):
            # Check pattern uniformity
            unique_patterns = list(set(patterns))
            if len(unique_patterns) >= 2:
                # Find sample invalid values (that have formats different from the main format, or fail to parse)
                # Main format is the most common format
                main_format = max(set(patterns), key=patterns.count)
                samples = []
                for val in non_null_series:
                    pat = get_date_pattern(val)
                    if not pat or pat != main_format:
                        samples.append(str(val))
                        if len(samples) >= 10:
                            break
                invalid_dates.append(
                    {"column": col_str, "inconsistent_formats": unique_patterns, "sample_invalid_values": samples}
                )

    # 10. Invalid Email Detection
    invalid_emails = {"total_invalid_count": 0, "affected_columns": {}}
    total_inv_emails = 0
    for col in df.columns:
        col_str = str(col)
        if not pd.api.types.is_object_dtype(df[col]):
            continue
        non_null_vals = df[col].dropna()
        if non_null_vals.empty:
            continue

        # Detect if it's an email column: name contains "email" or >30% look like emails
        is_email_col = "email" in col_str.lower()
        if not is_email_col:
            # Check sample
            email_looks = sum(1 for v in non_null_vals.head(50) if "@" in str(v) and "." in str(v))
            if email_looks / min(50, len(non_null_vals)) > 0.30:
                is_email_col = True

        if is_email_col:
            invalid_list = []
            for val in non_null_vals:
                if not is_email_address(val):
                    invalid_list.append(str(val))
            if len(invalid_list) > 0:
                total_inv_emails += len(invalid_list)
                invalid_emails["affected_columns"][col_str] = {
                    "invalid_count": len(invalid_list),
                    "sample_invalid_values": invalid_list[:10],
                }
    invalid_emails["total_invalid_count"] = total_inv_emails

    # 11. Invalid Phone Number Detection
    invalid_phones = {"total_invalid_count": 0, "affected_columns": {}}
    total_inv_phones = 0
    for col in df.columns:
        col_str = str(col)
        # Classify phone column: name contains phone/tel or >30% values are phone-like
        non_null_vals = df[col].dropna()
        if non_null_vals.empty:
            continue

        is_phone_col = any(x in col_str.lower() for x in ["phone", "telephone", "mobile", "tel_number"])
        if not is_phone_col:
            # Inspect sample values
            phone_looks = sum(1 for v in non_null_vals.head(50) if is_phone_number(v))
            if phone_looks / min(50, len(non_null_vals)) > 0.30:
                is_phone_col = True

        if is_phone_col:
            invalid_list = []
            for val in non_null_vals:
                # Try to clean formatting before checking if phone
                if not is_phone_number(val):
                    invalid_list.append(str(val))
            if len(invalid_list) > 0:
                total_inv_phones += len(invalid_list)
                invalid_phones["affected_columns"][col_str] = {
                    "invalid_count": len(invalid_list),
                    "sample_invalid_values": invalid_list[:10],
                }
    invalid_phones["total_invalid_count"] = total_inv_phones

    # 12. High Cardinality Detection
    high_cardinality = []
    # Check all categorical & text columns
    for col in categorical_cols + text_cols:
        col_str = str(col)
        unique_cnt = int(df[col].dropna().nunique())
        if unique_cnt > 10:
            unique_pct = round(unique_cnt / row_count * 100, 2) if row_count > 0 else 0.0
            if unique_pct > 50.0:
                high_cardinality.append(
                    {
                        "column": col_str,
                        "unique_count": unique_cnt,
                        "unique_pct": unique_pct,
                        "severity": "High" if unique_pct > 80 else "Medium",
                    }
                )

    # 13. Correlation Analysis
    correlation_report = {"correlation_matrix": {"columns": [], "matrix": []}, "high_correlations": []}

    if len(numerical_cols) >= 2:
        try:
            # Select columns with standard deviation > 0
            valid_num_cols = [c for c in numerical_cols if df[c].dropna().std() > 0]
            if len(valid_num_cols) >= 2:
                corr_df = df[valid_num_cols].corr(method="pearson").fillna(0.0)
                correlation_report["correlation_matrix"]["columns"] = valid_num_cols
                correlation_report["correlation_matrix"]["matrix"] = corr_df.values.tolist()

                # Extract high correlations
                for i in range(len(valid_num_cols)):
                    for j in range(i + 1, len(valid_num_cols)):
                        val = float(corr_df.iloc[i, j])
                        if abs(val) > 0.85:
                            correlation_report["high_correlations"].append(
                                {"col1": valid_num_cols[i], "col2": valid_num_cols[j], "coefficient": round(val, 4)}
                            )
        except Exception:
            pass

    # 14. Extended Numerical Statistics
    numerical_statistics = {}
    for col in numerical_cols:
        col_str = str(col)
        col_series = df[col]
        clean_series = col_series.dropna()
        if clean_series.empty:
            numerical_statistics[col_str] = {
                "mean": None,
                "median": None,
                "mode": None,
                "min": None,
                "max": None,
                "std_dev": None,
                "variance": None,
                "quartiles": {"q1": None, "q2": None, "q3": None},
            }
            continue

        try:
            mean = float(clean_series.mean())
            median = float(clean_series.median())
            mode_series = clean_series.mode()
            mode_val = float(mode_series.iloc[0]) if not mode_series.empty else None
            min_val = float(clean_series.min())
            max_val = float(clean_series.max())
            std_dev = float(clean_series.std()) if len(clean_series) > 1 else 0.0
            variance = float(clean_series.var()) if len(clean_series) > 1 else 0.0
            q1 = float(clean_series.quantile(0.25))
            q2 = float(clean_series.quantile(0.50))
            q3 = float(clean_series.quantile(0.75))

            # Format and check nan values
            std_dev = std_dev if not np.isnan(std_dev) else None
            variance = variance if not np.isnan(variance) else None

            numerical_statistics[col_str] = {
                "mean": round(mean, 2) if mean is not None else None,
                "median": round(median, 2) if median is not None else None,
                "mode": round(mode_val, 2) if mode_val is not None else None,
                "min": round(min_val, 2) if min_val is not None else None,
                "max": round(max_val, 2) if max_val is not None else None,
                "std_dev": round(std_dev, 2) if std_dev is not None else None,
                "variance": round(variance, 2) if variance is not None else None,
                "quartiles": {
                    "q1": round(q1, 2) if q1 is not None else None,
                    "q2": round(q2, 2) if q2 is not None else None,
                    "q3": round(q3, 2) if q3 is not None else None,
                },
            }
        except Exception:
            pass

    # 15. Quality Score Metric
    score = 100
    if missing_pct > 0:
        score -= min(25, int(missing_pct * 1.5))
    if dup_rows_pct > 0:
        score -= min(20, int(dup_rows_pct * 2.0))
    if len(duplicate_columns) > 0:
        score -= min(15, len(duplicate_columns) * 5)
    if len(mixed_data_types) > 0:
        score -= min(15, len(mixed_data_types) * 5)
    if len(empty_columns) > 0:
        score -= min(15, len(empty_columns) * 5)
    if len(constant_columns) > 0:
        score -= min(10, len(constant_columns) * 2)
    # Deduct for invalid phone, email, date formats
    if invalid_emails["total_invalid_count"] > 0:
        score -= min(10, int(invalid_emails["total_invalid_count"] / row_count * 20) + 2)
    if invalid_phones["total_invalid_count"] > 0:
        score -= min(10, int(invalid_phones["total_invalid_count"] / row_count * 20) + 2)
    if len(invalid_dates) > 0:
        score -= min(10, len(invalid_dates) * 3)

    score = max(0, min(100, score))

    # Rating
    if score >= 85:
        rating = "Excellent"
    elif score >= 70:
        rating = "Good"
    elif score >= 50:
        rating = "Average"
    else:
        rating = "Poor"

    profile = {
        "dataset_name": (
            os.path.basename(file_path).split("_", 1)[-1]
            if "_" in os.path.basename(file_path)
            else os.path.basename(file_path)
        ),
        "row_count": row_count,
        "col_count": col_count,
        "memory_usage": memory_usage,
        "file_size": file_size,
        "column_types": {
            "numerical": numerical_cols,
            "categorical": categorical_cols,
            "date": date_cols,
            "boolean": boolean_cols,
            "text": text_cols,
        },
        "quality_report": {
            "missing_values": {
                "by_column": missing_by_col_filtered,
                "total_missing": total_missing_cells,
                "missing_pct": missing_pct,
                "top_affected_columns": top_affected_columns,
            },
            "duplicate_rows": {"count": dup_rows_count, "pct": dup_rows_pct, "sample_records": sample_duplicates},
            "duplicate_columns": duplicate_columns,
            "mixed_data_types": mixed_data_types,
            "empty_columns": empty_columns,
            "constant_columns": constant_columns,
            "outliers": outliers_report,
            "invalid_dates": invalid_dates,
            "invalid_emails": invalid_emails,
            "invalid_phones": invalid_phones,
            "high_cardinality": high_cardinality,
        },
        "correlation_analysis": correlation_report,
        "numerical_statistics": numerical_statistics,
        "quality_score": score,
        "quality_rating": rating,
    }

    return profile
