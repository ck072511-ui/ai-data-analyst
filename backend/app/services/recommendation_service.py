from typing import Any, Dict, List


def generate_recommendations(profile_info: Dict[str, Any]) -> List[Dict[str, Any]]:
    """Heuristic cleaning recommendation engine based on dataset profile diagnostics."""
    recommendations = []

    if not profile_info or "quality_report" not in profile_info:
        return recommendations

    report = profile_info["quality_report"]

    # 1. Duplicate Rows
    dup_rows = report.get("duplicate_rows", {})
    if dup_rows.get("count", 0) > 0:
        recommendations.append(
            {
                "issue": f"Detected {dup_rows['count']} duplicate rows ({dup_rows['pct']}% of dataset).",
                "recommendation": "Remove Duplicate Rows",
                "reason": "Redundant identical rows bias statistical summaries and cause machine learning overfitting.",
                "expected_impact": "Deduplicate dataset, reducing storage footprint and correcting row representation weights.",
                "confidence_score": 95,
            }
        )

    # 2. Duplicate Columns
    dup_cols = report.get("duplicate_columns", [])
    if dup_cols:
        recommendations.append(
            {
                "issue": f"Detected {len(dup_cols)} pairs of duplicate columns containing identical contents.",
                "recommendation": "Remove Duplicate Columns",
                "reason": f"Columns with identical contents add no additional variability or explanatory value. Redundant: {', '.join([f'[{p[0]} <-> {p[1]}]' for p in dup_cols])}",
                "expected_impact": "Simplify database schema structure and eliminate redundancy.",
                "confidence_score": 95,
            }
        )

    # 3. Missing Values
    missing_info = report.get("missing_values", {})
    top_affected = missing_info.get("top_affected_columns", [])

    for row in top_affected:
        col = row["column"]
        pct = row["pct"]
        if pct > 30.0:
            recommendations.append(
                {
                    "issue": f"Column '{col}' has high missingness rate ({pct}% nulls).",
                    "recommendation": f"Drop Column '{col}'",
                    "reason": "Missingness exceeds 30%. Imputation introduces high variance and error risk for downstream applications.",
                    "expected_impact": "Remove highly incomplete attribute from the feature set.",
                    "confidence_score": 85,
                }
            )
        elif pct > 0.0:
            col_types = profile_info.get("column_types", {})
            is_num = col in col_types.get("numerical", [])
            strat = "Median Imputation" if is_num else "Mode Imputation"
            recommendations.append(
                {
                    "issue": f"Column '{col}' contains missing values ({pct}% nulls).",
                    "recommendation": f"Apply {strat} on '{col}'",
                    "reason": "Completeness rate is acceptable. Median or Mode fills missing observations without introducing major bias.",
                    "expected_impact": "Ensure 100% cell completeness in column.",
                    "confidence_score": 90,
                }
            )

    # 4. Inconsistent Date Formats
    invalid_dates = report.get("invalid_dates", [])
    for row in invalid_dates:
        col = row["column"]
        formats = row.get("inconsistent_formats", [])
        recommendations.append(
            {
                "issue": f"Column '{col}' contains multiple inconsistent date formats: {', '.join(formats)}.",
                "recommendation": f"Standardize Date Format for '{col}'",
                "reason": "Inconsistent date formatting prevents time-series parsing, index sorting, and date arithmetic.",
                "expected_impact": "Unified date schema string formatted to standard YYYY-MM-DD.",
                "confidence_score": 95,
            }
        )

    # 5. Mixed Data Types
    mixed_types = report.get("mixed_data_types", {})
    for col, types in mixed_types.items():
        recommendations.append(
            {
                "issue": f"Column '{col}' contains mixed data types: {', '.join(types)}.",
                "recommendation": f"Normalize Mixed Types in '{col}'",
                "reason": "Databases and analytics libraries expect a single consistent datatype per column. Mixed types lead to execution errors.",
                "expected_impact": "Cast mixed entries to a unified type and normalize placeholder text values.",
                "confidence_score": 90,
            }
        )

    # 6. Invalid Emails
    invalid_emails = report.get("invalid_emails", {})
    email_affected = invalid_emails.get("affected_columns", {})
    for col, data in email_affected.items():
        recommendations.append(
            {
                "issue": f"Column '{col}' has {data['invalid_count']} malformed email formatting strings.",
                "recommendation": f"Handle Invalid Emails in '{col}'",
                "reason": "Malformed email addresses violate RFC standards and disrupt notification or contact sync mechanisms.",
                "expected_impact": "Remove malformed emails or replace with validation status flags.",
                "confidence_score": 95,
            }
        )

    # 7. Invalid Phones
    invalid_phones = report.get("invalid_phones", {})
    phone_affected = invalid_phones.get("affected_columns", {})
    for col, data in phone_affected.items():
        recommendations.append(
            {
                "issue": f"Column '{col}' has {data['invalid_count']} malformed phone formatting strings.",
                "recommendation": f"Normalize Phone Formatting in '{col}'",
                "reason": "Consistent phone digits are necessary for message routing, dialing validation, and indexing.",
                "expected_impact": "Normalize phone numbers to unified integer/plus-prefix strings.",
                "confidence_score": 95,
            }
        )

    # 8. Empty Columns
    empty_cols = report.get("empty_columns", [])
    if empty_cols:
        recommendations.append(
            {
                "issue": f"Detected {len(empty_cols)} completely empty columns (all nulls or empty strings).",
                "recommendation": "Remove Empty Columns",
                "reason": f"Columns containing 0% populated values provide no information. Redundant: {', '.join(empty_cols)}",
                "expected_impact": "Drop redundant empty columns to clean database table schema.",
                "confidence_score": 95,
            }
        )

    # 9. Constant Columns
    const_cols = report.get("constant_columns", [])
    if const_cols:
        recommendations.append(
            {
                "issue": f"Detected {len(const_cols)} constant columns containing only a single unique value.",
                "recommendation": "Remove Constant Columns",
                "reason": "Zero variance columns add no explanatory weight to statistical calculations or machine learning models. Redundant: "
                + ", ".join(const_cols),
                "expected_impact": "Simplify dataset properties and reduce layout dimensionality.",
                "confidence_score": 90,
            }
        )

    # 10. High Correlations
    corr_info = profile_info.get("correlation_analysis", {})
    high_corrs = corr_info.get("high_correlations", [])
    for p in high_corrs:
        recommendations.append(
            {
                "issue": f"High linear correlation ({p['coefficient']:.2f}) detected between columns '{p['col1']}' and '{p['col2']}'.",
                "recommendation": f"Review correlated features '{p['col1']}' / '{p['col2']}'",
                "reason": "Multicollinearity can distort linear models, inflate standard errors, and add redundant data features.",
                "expected_impact": "Consider dropping one of the correlated features before model training.",
                "confidence_score": 85,
            }
        )

    return recommendations
