import re
from typing import Any, Dict, List


def generate_rich_business_recommendations(profile_info: Dict[str, Any]) -> List[Dict[str, Any]]:
    """Generates rich, confidence-scored business recommendations based on profiling details."""
    recommendations = []
    if not profile_info or "quality_report" not in profile_info:
        return recommendations

    report = profile_info["quality_report"]
    row_count = profile_info.get("row_count", 0)
    col_types = profile_info.get("column_types", {})

    # 1. Duplicates Impact
    dup_rows = report.get("duplicate_rows", {})
    dup_pct = dup_rows.get("pct", 0.0)
    if dup_rows.get("count", 0) > 0:
        severity = "Critical" if dup_pct > 15 else "Medium"
        recommendations.append(
            {
                "title": "Remove duplicate rows to resolve analytics bias",
                "description": f"Detected {dup_rows['count']} duplicate rows representing {dup_pct}% of the dataset.",
                "business_impact": "Redundant identical rows inflate frequency counts, artificially shift statistical averages, and skew aggregations, leading to biassed executive decisions.",
                "severity": severity,
                "confidence_score": 95,
            }
        )

    # 2. Duplicate Columns
    dup_cols = report.get("duplicate_columns", [])
    if dup_cols:
        recommendations.append(
            {
                "title": "Remove highly redundant duplicate columns",
                "description": f"Identified {len(dup_cols)} pair(s) of columns containing identical data.",
                "business_impact": "Identical columns consume unnecessary memory, clutter user interfaces, and introduce multicollinearity in analytical modeling.",
                "severity": "Medium",
                "confidence_score": 95,
            }
        )

    # 3. High Missing Values
    missing_info = report.get("missing_values", {})
    top_affected = missing_info.get("top_affected_columns", [])
    for row in top_affected:
        col = row["column"]
        pct = row["pct"]
        if pct > 30.0:
            recommendations.append(
                {
                    "title": f"Drop highly incomplete column '{col}'",
                    "description": f"Column '{col}' is missing {pct}% of its cells. Imputation would introduce high error rates.",
                    "business_impact": "Using variables with over 30% missingness in machine learning forces imputation or row deletion, both of which degrade model reliability and predictions.",
                    "severity": "High",
                    "confidence_score": 90,
                }
            )
        elif pct > 0.0:
            is_num = col in col_types.get("numerical", [])
            strat = "median imputation" if is_num else "mode imputation"
            recommendations.append(
                {
                    "title": f"Apply {strat} on '{col}' to restore completeness",
                    "description": f"Column '{col}' is missing {pct}% of its cells. The missingness rate is low enough to safely impute.",
                    "business_impact": "Filling in minor gaps prevents row deletion, ensuring downstream business reports work on complete data records.",
                    "severity": "Low",
                    "confidence_score": 85,
                }
            )

    # 4. Outliers Impact
    outliers_report = report.get("outliers", {})
    by_column_outliers = outliers_report.get("by_column", {})
    for col, data in by_column_outliers.items():
        outlier_pct = data.get("iqr_pct", 0.0)
        outlier_count = data.get("iqr_count", 0)
        if outlier_pct > 5.0:
            recommendations.append(
                {
                    "title": f"Clip or normalize outliers in '{col}' before modeling",
                    "description": f"Column '{col}' contains {outlier_count} outliers ({outlier_pct}% of values).",
                    "business_impact": "Extreme statistical noise skews mathematical properties like mean and standard deviation, negatively biasing prediction models and forecasting analytics.",
                    "severity": "High",
                    "confidence_score": 85,
                }
            )

    # 5. Customer ID or High-cardinality predictor warnings
    high_card = report.get("high_cardinality", [])
    for col in high_card:
        # Check if the column is an ID or key
        is_id = bool(re.search(r"(?i)(id|uuid|key|code|identifier|cust_id|user_id|email_id)", col))
        if is_id:
            recommendations.append(
                {
                    "title": f"Exclude '{col}' column from predictive modeling features",
                    "description": f"Column '{col}' is classified as a high-cardinality identifier or database key.",
                    "business_impact": "Including database primary/foreign keys in training causes models to memorize training examples (overfitting) rather than learning generalized trends, making prediction unusable for new records.",
                    "severity": "High",
                    "confidence_score": 98,
                }
            )
        else:
            recommendations.append(
                {
                    "title": f"Review categorical cardinality of '{col}' before encoding",
                    "description": f"Column '{col}' contains a very high number of unique categories relative to dataset size.",
                    "business_impact": "High-cardinality columns can cause one-hot encoding feature explosions, memory exhaustion, and slow inference speeds.",
                    "severity": "Medium",
                    "confidence_score": 80,
                }
            )

    # 6. Highly Correlated Features
    corr_analysis = profile_info.get("correlation_analysis", {})
    high_corrs = corr_analysis.get("high_correlations", [])
    for p in high_corrs:
        recommendations.append(
            {
                "title": f"Remove highly correlated feature between '{p['col1']}' and '{p['col2']}'",
                "description": f"High linear correlation coefficient of {p['coefficient']:.2f} detected between '{p['col1']}' and '{p['col2']}'.",
                "business_impact": "Multicollinearity between model inputs destabilizes coefficient estimates, making it impossible to determine individual feature impacts on target outcomes.",
                "severity": "Medium",
                "confidence_score": 85,
            }
        )

    # 7. Empty Columns
    empty_cols = report.get("empty_columns", [])
    for col in empty_cols:
        recommendations.append(
            {
                "title": f"Remove completely empty column '{col}'",
                "description": f"Column '{col}' has 100% missing values.",
                "business_impact": "Unpopulated columns add visual and database overhead while offering zero analytical value.",
                "severity": "Medium",
                "confidence_score": 95,
            }
        )

    # 8. Constant Columns
    const_cols = report.get("constant_columns", [])
    for col in const_cols:
        recommendations.append(
            {
                "title": f"Drop constant zero-variance column '{col}'",
                "description": f"Column '{col}' contains a single constant value across all rows.",
                "business_impact": "Columns with zero variance provide no information for statistical differentiation or predictive modelling.",
                "severity": "Low",
                "confidence_score": 90,
            }
        )

    # 9. Inconsistent Date formats
    invalid_dates = report.get("invalid_dates", [])
    for row in invalid_dates:
        col = row["column"]
        formats = row.get("inconsistent_formats", [])
        recommendations.append(
            {
                "title": f"Standardize date formatting in '{col}'",
                "description": f"Column '{col}' has inconsistent date patterns: {', '.join(formats)}.",
                "business_impact": "Irregular date strings disrupt analytical range filters, cohort generation, and time-based index sorting.",
                "severity": "High",
                "confidence_score": 95,
            }
        )

    # 10. Mixed Data Types
    mixed_types = report.get("mixed_data_types", {})
    for col, types in mixed_types.items():
        recommendations.append(
            {
                "title": f"Normalize mixed data types in '{col}'",
                "description": f"Column '{col}' contains mixed data types: {', '.join(types)}.",
                "business_impact": "Varying data types in a single column cause unexpected run-time validation crashes during SQL execution or python modeling.",
                "severity": "High",
                "confidence_score": 90,
            }
        )

    # 11. Malformed phone strings
    invalid_phones = report.get("invalid_phones", {})
    for col, data in invalid_phones.get("affected_columns", {}).items():
        recommendations.append(
            {
                "title": f"Format and validate phone records in '{col}'",
                "description": f"Column '{col}' contains {data['invalid_count']} malformed phone formatting strings.",
                "business_impact": "Malformed or non-numeric phone structures block customer communications, SMS notifications, and user mapping.",
                "severity": "Medium",
                "confidence_score": 95,
            }
        )

    # 12. Malformed email strings
    invalid_emails = report.get("invalid_emails", {})
    for col, data in invalid_emails.get("affected_columns", {}).items():
        recommendations.append(
            {
                "title": f"Clean syntax errors in email column '{col}'",
                "description": f"Column '{col}' has {data['invalid_count']} invalid email formatting patterns.",
                "business_impact": "Invalid email formatting prevents transactional email delivery, increases bounce rates, and damages marketing campaign domains.",
                "severity": "High",
                "confidence_score": 95,
            }
        )

    # 13. Skewness
    num_stats = profile_info.get("numerical_statistics", {})
    for col, stats in num_stats.items():
        mean = stats.get("mean")
        median = stats.get("median")
        std_dev = stats.get("std_dev")
        if mean is not None and median is not None and std_dev and std_dev > 0:
            skew = abs(mean - median) / std_dev
            if skew > 0.5:
                recommendations.append(
                    {
                        "title": f"Normalize skewed numeric distribution in '{col}'",
                        "description": f"The mean ({mean}) and median ({median}) for column '{col}' differ by {skew:.2f} standard deviations.",
                        "business_impact": "Highly skewed features violate normality assumptions for linear regressions, ANOVA tests, and neural networks, distorting analytical predictions.",
                        "severity": "Low",
                        "confidence_score": 80,
                    }
                )

    return recommendations


def generate_dataset_health(profile_info: Dict[str, Any]) -> Dict[str, Any]:
    """Generates dataset health summary including overall score, strengths, weaknesses, risks, and next steps."""
    if not profile_info:
        return {
            "overall_health": 0,
            "top_risks": [{"risk": "No profiling information available", "severity": "Critical"}],
            "strengths": [],
            "weaknesses": ["Dataset has not been profiled"],
            "recommended_next_steps": ["Trigger dataset profiling to identify quality metrics"],
        }

    score = profile_info.get("quality_score", 100)
    report = profile_info.get("quality_report", {})
    row_count = profile_info.get("row_count", 0)

    strengths = []
    weaknesses = []
    top_risks = []
    recommended_next_steps = []

    # Analyze Duplicates
    dup_count = report.get("duplicate_rows", {}).get("count", 0)
    dup_pct = report.get("duplicate_rows", {}).get("pct", 0.0)
    if dup_count == 0:
        strengths.append("No duplicate rows detected, ensuring row representation uniqueness.")
    else:
        weaknesses.append(f"Contains {dup_count} duplicate rows ({dup_pct}% of dataset).")
        top_risks.append(
            {
                "risk": "Row Duplication Bias",
                "description": "Redundant identical rows distort frequency tables and can cause overfitting in ML.",
                "severity": "Critical" if dup_pct > 15 else "Medium",
            }
        )
        recommended_next_steps.append("Deduplicate dataset using row deduplication tool.")

    # Analyze Missing Values
    missing_pct = report.get("missing_values", {}).get("missing_pct", 0.0)
    total_missing = report.get("missing_values", {}).get("total_missing", 0)
    if missing_pct == 0.0:
        strengths.append("Perfect cell completeness: 0% missing values across the entire dataset.")
    elif missing_pct < 2.0:
        strengths.append(f"High completeness score: only {missing_pct}% of cells are missing.")
    else:
        weaknesses.append(f"Significant gaps in data integrity: {missing_pct}% of all cells are missing.")
        top_risks.append(
            {
                "risk": "Data Incompleteness",
                "description": f"Missingness rate is {missing_pct}%. Highly empty columns reduce dataset usefulness.",
                "severity": "High" if missing_pct > 10 else "Medium",
            }
        )
        recommended_next_steps.append("Impute missing numeric values using median, and category values using mode.")

    # Analyze Empty Columns
    empty_cols = report.get("empty_columns", [])
    if len(empty_cols) > 0:
        weaknesses.append(f"Detected {len(empty_cols)} completely empty columns.")
        top_risks.append(
            {
                "risk": "Completely Empty Columns",
                "description": f"Columns {', '.join(empty_cols[:3])} are entirely unpopulated.",
                "severity": "Medium",
            }
        )
        recommended_next_steps.append("Drop completely empty columns from dataset schema.")

    # Analyze Outliers
    outliers_report = report.get("outliers", {})
    by_column_outliers = outliers_report.get("by_column", {})
    total_outliers = outliers_report.get("total_outliers_iqr", 0)
    if total_outliers == 0:
        strengths.append("No extreme numeric outliers detected.")
    else:
        weaknesses.append(f"Detected {total_outliers} numerical outliers across {len(by_column_outliers)} columns.")
        top_risks.append(
            {
                "risk": "Outlier Distortions",
                "description": f"Extreme outliers skew distributions in columns: {', '.join(list(by_column_outliers.keys())[:3])}.",
                "severity": "High" if total_outliers > 50 else "Medium",
            }
        )
        recommended_next_steps.append("Apply Winsorization or outlier filtering to stabilize numeric variances.")

    # Analyze Mixed Types
    mixed_types = report.get("mixed_data_types", {})
    if len(mixed_types) == 0:
        strengths.append("Consistent schema types: all columns have unique data types.")
    else:
        weaknesses.append(f"Mixed data types found in {len(mixed_types)} columns.")
        top_risks.append(
            {
                "risk": "Type Contamination",
                "description": f"Mixed value formats present in columns: {', '.join(list(mixed_types.keys())[:3])}.",
                "severity": "High",
            }
        )
        recommended_next_steps.append(
            "Normalize mixed types by mapping placeholders (null, unknown, N/A) to standard formats."
        )

    # Format Validations
    invalid_dates = report.get("invalid_dates", [])
    invalid_emails = report.get("invalid_emails", {}).get("total_invalid_count", 0)
    invalid_phones = report.get("invalid_phones", {}).get("total_invalid_count", 0)

    if len(invalid_dates) > 0 or invalid_emails > 0 or invalid_phones > 0:
        weaknesses.append("Syntax and schema validations failed on dates, emails, or phones.")
        top_risks.append(
            {
                "risk": "Syntax Format Failures",
                "description": "Inconsistent date patterns or malformed contact addresses found.",
                "severity": "Medium",
            }
        )
        recommended_next_steps.append("Standardize date formatting to YYYY-MM-DD and run contact normalizations.")
    else:
        strengths.append("Contacts, emails, and dates are well-formatted and compliant.")

    # High Correlation
    corr_analysis = profile_info.get("correlation_analysis", {})
    high_corrs = corr_analysis.get("high_correlations", [])
    if len(high_corrs) > 0:
        weaknesses.append(f"Found {len(high_corrs)} pairs of highly correlated features.")
        top_risks.append(
            {
                "risk": "Multicollinearity",
                "description": "High correlation may distort linear regression coefficients and overfit predictions.",
                "severity": "Medium",
            }
        )
        recommended_next_steps.append(
            "Evaluate highly correlated columns and consider dropping redundant features before training."
        )

    # Default next steps
    if not recommended_next_steps:
        recommended_next_steps.append("Export the clean dataset schema for analytics workflows.")

    # Sort risks by severity: Critical > High > Medium > Low
    severity_order = {"Critical": 0, "High": 1, "Medium": 2, "Low": 3}
    top_risks.sort(key=lambda r: severity_order.get(r["severity"], 4))

    return {
        "overall_health": score,
        "top_risks": top_risks,
        "strengths": strengths,
        "weaknesses": weaknesses,
        "recommended_next_steps": recommended_next_steps,
    }


def explain_applied_cleaning_operations(operations: List[str]) -> List[Dict[str, str]]:
    """Explains every applied cleaning action, detailing what changed, why it changed, the business impact, and expected improvements."""
    explanations = []
    if not operations:
        return explanations

    # Definitions
    whitespace_desc = {
        "operation": "Whitespace Trimming",
        "what_changed": "Leading and trailing spaces (e.g. ' Text ') were trimmed from string fields.",
        "why_it_changed": "Extra whitespaces make exact matches fail during string search, table joins, or SQL grouping queries.",
        "business_impact": "Ensures clean categories and reliable data merging across multiple business tables.",
        "expected_improvement": "100% clean string fields with zero risk of whitespace-induced grouping mismatches.",
    }

    text_norm_desc = {
        "operation": "Text Casing Standardization",
        "what_changed": "Standardized characters to uniform case formatting (UPPERCASE, lowercase, or Title Case).",
        "why_it_changed": "Mixed cases create duplicate analytical categories (like 'Retail' vs 'retail' vs 'RETAIL').",
        "business_impact": "Ensures report summaries and dashboards aggregate counts correctly without duplicated labels.",
        "expected_improvement": "Unified categorical groupings with redundant labels completely eliminated.",
    }

    mixed_types_desc = {
        "operation": "Mixed Type Standardization",
        "what_changed": "Replaced mixed-type strings ('unknown', 'n/a', 'null', 'none') with standard NaN database null values.",
        "why_it_changed": "Analytical packages and databases cannot perform numeric or type-safe operations on contaminated string values.",
        "business_impact": "Enables robust calculation of metrics (sums, averages) and avoids engine runtime parsing errors.",
        "expected_improvement": "A standard missing-value indicator format across the entire dataset.",
    }

    date_desc = {
        "operation": "Date Format Standardizing",
        "what_changed": "Parsed inconsistent dates and converted them into ISO 8601 YYYY-MM-DD standard structure.",
        "why_it_changed": "Varying date patterns make sorting, filtering by date ranges, or time-series forecasting impossible.",
        "business_impact": "Enables reliable time-based analytical cohorts, season trends, and financial reports.",
        "expected_improvement": "Unified date parsing enabling safe date math and indexing.",
    }

    phone_desc = {
        "operation": "Phone Format Normalization",
        "what_changed": "Stripped invalid formatting characters and standardized phone digits.",
        "why_it_changed": "Inconsistent formatting prevents telephone system dialers, SMS platforms, or CRM integration from working.",
        "business_impact": "Enhances contact rates and lowers SMS transaction drops.",
        "expected_improvement": "Syntactically correct and clean communication records.",
    }

    email_desc = {
        "operation": "Email Domain Verification",
        "what_changed": "Verified emails against RFC specifications and corrected syntax errors.",
        "why_it_changed": "Malformed email addresses lead to email campaign bounces and domain blacklisting.",
        "business_impact": "Ensures customer notifications reach target users and keeps marketing domains healthy.",
        "expected_improvement": "Zero invalid email format strings left in communication fields.",
    }

    winsor_desc = {
        "operation": "Winsorization Outlier Clipping",
        "what_changed": "Clipped extreme outliers beyond standard deviation thresholds to the 1st and 99th percentiles.",
        "why_it_changed": "Extreme outliers distort statistics like mean and variance, biasing machine learning prediction models.",
        "business_impact": "Protects analytical dashboards and models from being biased by anomaly spikes.",
        "expected_improvement": "Stabilized numeric variance, resulting in more robust forecast outputs.",
    }

    outlier_remove_desc = {
        "operation": "Outlier Row Deletion",
        "what_changed": "Removed rows with values outside valid mathematical distribution boundaries.",
        "why_it_changed": "Highly distorted outliers represent capture errors or extreme anomalies that skew core trends.",
        "business_impact": "Ensures statistics are reflective of core operations and standard business events.",
        "expected_improvement": "Outlier-free dataset representing baseline business records.",
    }

    num_impute_desc = {
        "operation": "Numeric Imputation",
        "what_changed": "Imputed missing numeric cells with statistical mean or median.",
        "why_it_changed": "Many downstream forecasting engines and ML algorithms drop entire rows if any cell is missing.",
        "business_impact": "Retains all rows in sample datasets, maximizing explanatory data size.",
        "expected_improvement": "100% numeric completeness with zero row-deletion data loss.",
    }

    cat_impute_desc = {
        "operation": "Categorical Imputation",
        "what_changed": "Imputed missing textual categories using statistical mode (most frequent value) or constant.",
        "why_it_changed": "Missing categories distort dashboards and break predictive class variables.",
        "business_impact": "Ensures analytics reports can group rows properly under valid labels.",
        "expected_improvement": "Complete categorical fields with zero null indicators.",
    }

    dup_row_desc = {
        "operation": "Deduplicate Duplicate Rows",
        "what_changed": "Removed exact duplicate row entries from the dataset.",
        "why_it_changed": "Identical rows artificially inflate dataset rows, double-counting transactions and biasing averages.",
        "business_impact": "Reduces data storage usage and guarantees each business record is represented exactly once.",
        "expected_improvement": "100% unique transaction ledger.",
    }

    empty_col_desc = {
        "operation": "Drop Empty Columns",
        "what_changed": "Dropped columns containing only null or empty values from the table schema.",
        "why_it_changed": "Completely empty fields contain zero variance and provide no informative value.",
        "business_impact": "Simplifies data models and clarifies dashboard display layouts.",
        "expected_improvement": "A streamlined database layout featuring only informative columns.",
    }

    const_col_desc = {
        "operation": "Drop Constant Columns",
        "what_changed": "Dropped zero-variance columns containing only a single constant value.",
        "why_it_changed": "Columns that do not change add no weight to predictions or analytical reports.",
        "business_impact": "Saves processing memory and reduces feature dimensions.",
        "expected_improvement": "Fewer, higher-quality variables focus analytical pipelines.",
    }

    for op in operations:
        op_lower = op.lower()
        if "whitespace" in op_lower or "trim" in op_lower:
            explanations.append(whitespace_desc)
        elif "text case" in op_lower or "casing" in op_lower or "normalization applied" in op_lower:
            explanations.append(text_norm_desc)
        elif "mixed datatype" in op_lower or "mixed type" in op_lower:
            explanations.append(mixed_types_desc)
        elif "standardized date" in op_lower or "date standardization" in op_lower:
            explanations.append(date_desc)
        elif "phone" in op_lower:
            explanations.append(phone_desc)
        elif "email" in op_lower:
            explanations.append(email_desc)
        elif "winsorized" in op_lower or "winsorize" in op_lower:
            explanations.append(winsor_desc)
        elif "removed outliers" in op_lower or "outliers outside" in op_lower:
            explanations.append(outlier_remove_desc)
        elif "imputed" in op_lower and "numeric" in op_lower:
            explanations.append(num_impute_desc)
        elif "imputed" in op_lower and "categor" in op_lower:
            explanations.append(cat_impute_desc)
        elif "duplicate row" in op_lower or "deduplicate" in op_lower:
            explanations.append(dup_row_desc)
        elif "empty column" in op_lower:
            explanations.append(empty_col_desc)
        elif "constant column" in op_lower:
            explanations.append(const_col_desc)
        else:
            # Fallback explanation
            explanations.append(
                {
                    "operation": op,
                    "what_changed": f"Applied cleaning operation: '{op}'.",
                    "why_it_changed": "Standardized schema rules to ensure data quality.",
                    "business_impact": "Improves data analytics integrity and reporting reliability.",
                    "expected_improvement": "Standard-compliant dataset values.",
                }
            )

    return explanations


def generate_dataset_insights(profile_info: Dict[str, Any], audit_logs: List[Any] = None) -> Dict[str, Any]:
    """Generates dataset quality summaries, duplicate impact, missing value impact, outlier observations, and cardinality profiles."""
    if not profile_info:
        return {
            "quality_summary": "Dataset has not been profiled yet.",
            "most_problematic_columns": [],
            "duplicate_impact": "No profiling information.",
            "missing_value_impact": "No profiling information.",
            "outlier_impact": "No profiling information.",
            "correlation_observations": "No profiling information.",
            "high_cardinality_observations": "No profiling information.",
        }

    score = profile_info.get("quality_score", 100)
    rating = profile_info.get("quality_rating", "Excellent")
    row_count = profile_info.get("row_count", 0)
    col_count = profile_info.get("col_count", 0)
    report = profile_info.get("quality_report", {})

    # 1. Dataset Quality Summary
    quality_summary = (
        f"This dataset contains {row_count:,} rows and {col_count:,} columns. "
        f"The overall data quality score is {score}/100, which is rated as '{rating}'. "
    )
    if score >= 85:
        quality_summary += "The dataset is in excellent health and requires minimal cleaning before analytics or machine learning modeling."
    elif score >= 70:
        quality_summary += "The dataset is in good condition, but resolving minor warnings will improve predictive metrics and reporting accuracy."
    else:
        quality_summary += "The dataset has significant quality issues that must be addressed (such as duplicates, outliers, or missing cells) before executing business intelligence queries."

    # 2. Most Problematic Columns
    problematic_cols = []
    # Missing cells
    missing_by_col = report.get("missing_values", {}).get("by_column", {})
    for col, count in missing_by_col.items():
        pct = round(count / row_count * 100, 2) if row_count > 0 else 0
        if pct > 0:
            problematic_cols.append(
                {
                    "column": col,
                    "issue": f"Missing {count:,} values ({pct}%)",
                    "severity": "Critical" if pct > 30 else "Medium",
                    "score_weight": pct,
                }
            )

    # Mixed data types
    mixed_types = report.get("mixed_data_types", {})
    for col, types in mixed_types.items():
        problematic_cols.append(
            {"column": col, "issue": f"Mixed data types: {', '.join(types)}", "severity": "High", "score_weight": 25.0}
        )

    # Outliers
    outliers_report = report.get("outliers", {})
    by_column_outliers = outliers_report.get("by_column", {})
    for col, data in by_column_outliers.items():
        outlier_pct = data.get("iqr_pct", 0)
        if outlier_pct > 5.0:
            problematic_cols.append(
                {
                    "column": col,
                    "issue": f"High outlier rate ({outlier_pct}%)",
                    "severity": "High",
                    "score_weight": outlier_pct,
                }
            )

    # Invalid contact formats
    invalid_emails = report.get("invalid_emails", {}).get("affected_columns", {})
    for col, data in invalid_emails.items():
        problematic_cols.append(
            {
                "column": col,
                "issue": f"Malformed emails ({data['invalid_count']} records)",
                "severity": "Medium",
                "score_weight": 15.0,
            }
        )

    invalid_phones = report.get("invalid_phones", {}).get("affected_columns", {})
    for col, data in invalid_phones.items():
        problematic_cols.append(
            {
                "column": col,
                "issue": f"Malformed phones ({data['invalid_count']} records)",
                "severity": "Medium",
                "score_weight": 15.0,
            }
        )

    # Sort problematic columns by score_weight descending
    problematic_cols.sort(key=lambda x: x["score_weight"], reverse=True)
    most_problematic = [
        {"column": x["column"], "issue": x["issue"], "severity": x["severity"]} for x in problematic_cols[:5]
    ]

    # 3. Duplicate Impact
    dup_rows = report.get("duplicate_rows", {})
    dup_count = dup_rows.get("count", 0)
    dup_pct = dup_rows.get("pct", 0)
    if dup_count > 0:
        duplicate_impact = (
            f"There are {dup_count:,} exact duplicate rows, compromising {dup_pct}% of the dataset. "
            "These identical duplicates artificially inflate frequency counts, shift distribution curves, "
            "and skew metrics like sums and averages. Resolving these duplicates reduces dataset size and avoids analytics bias."
        )
    else:
        duplicate_impact = "No duplicate rows detected. Row representation is unique, guaranteeing that aggregations will not suffer from duplicate row bias."

    # 4. Missing Value Impact
    missing_info = report.get("missing_values", {})
    missing_pct = missing_info.get("missing_pct", 0)
    total_missing = missing_info.get("total_missing", 0)
    if total_missing > 0:
        missing_value_impact = (
            f"The dataset is missing a total of {total_missing:,} cells ({missing_pct}% of the overall table grid). "
            "Incomplete values can cause machine learning algorithms to crash, and forces analytics summaries to ignore "
            "records with nulls. Cleaning these missing fields using median or mode imputation will restore record continuity."
        )
    else:
        missing_value_impact = "The dataset has 100% cell population with zero missing values. This maximizes record usability and eliminates the need for statistical imputation."

    # 5. Outlier Impact
    total_outliers = outliers_report.get("total_outliers_iqr", 0)
    if total_outliers > 0:
        outlier_impact = (
            f"A total of {total_outliers:,} numeric values are classified as extreme statistical outliers. "
            "Extreme outliers inflate the variance of columns, distort scale normalization (like MinMax Scaling), "
            "and can lead to incorrect predictive models. Applying Winsorization clips these extremes to safe thresholds."
        )
    else:
        outlier_impact = "No extreme outliers detected within numeric fields. Distribution variations are within normal bounds, ensuring robust modeling results."

    # 6. Correlation Observations
    corr_analysis = profile_info.get("correlation_analysis", {})
    high_corrs = corr_analysis.get("high_correlations", [])
    if len(high_corrs) > 0:
        corr_observations = (
            f"Identified {len(high_corrs)} pair(s) of highly correlated numerical columns (coefficient > 0.85). "
            f"For example, '{high_corrs[0]['col1']}' and '{high_corrs[0]['col2']}' share a Pearson coefficient of {high_corrs[0]['coefficient']:.2f}. "
            "High linear correlations indicate redundant columns that may destabilize prediction regressions (multicollinearity)."
        )
    else:
        corr_observations = "No highly correlated numerical columns (Pearson coefficient > 0.85) were detected. The features are statistically distinct, minimizing multicollinearity risk."

    # 7. High Cardinality Observations
    high_card = report.get("high_cardinality", [])
    if len(high_card) > 0:
        corr_cols = []
        for col in high_card:
            is_id = bool(re.search(r"(?i)(id|uuid|key|code|identifier|cust_id|user_id|email_id)", col))
            corr_cols.append(f"'{col}'" + (" (suspected unique identifier)" if is_id else ""))
        high_cardinality_observations = (
            f"Columns: {', '.join(corr_cols[:3])} exhibit very high cardinality. "
            "High cardinality in categorical data complicates one-hot encodings and risks database lookup slow downs. "
            "Columns suspected to be identifiers must be excluded from feature vectors in model training."
        )
    else:
        high_cardinality_observations = "All categorical features contain a low to moderate number of unique values, suitable for database indexing and encoding techniques."

    return {
        "quality_summary": quality_summary,
        "most_problematic_columns": most_problematic,
        "duplicate_impact": duplicate_impact,
        "missing_value_impact": missing_value_impact,
        "outlier_impact": outlier_impact,
        "correlation_observations": corr_observations,
        "high_cardinality_observations": high_cardinality_observations,
    }
