import logging
from datetime import datetime
from typing import Any, Dict, List

import numpy as np
import pandas as pd
from sqlalchemy.orm import Session

from app.core.database import get_sync_engine
from app.models.dashboard import Dashboard
from app.models.dataset import UserDataset

logger = logging.getLogger(__name__)


def choose_optimal_chart(df: pd.DataFrame) -> Dict[str, Any]:
    """Auto chart selection algorithm based on data columns types and cardinality.
    Returns a dict containing:
      - chart_type: str ("line", "bar", "horizontal_bar", "histogram", "scatter", "pie", "donut", "grouped_bar")
      - x_axis: str (column name)
      - y_axis: List[str] or str (column names)
    """
    if df is None or df.empty:
        return {"chart_type": "bar", "x_axis": "", "y_axis": []}

    cols = list(df.columns)
    row_count = len(df)

    # Classify column types
    numeric_cols = []
    categorical_cols = []
    date_cols = []

    for col in cols:
        series = df[col]
        # Check if date-like
        if pd.api.types.is_datetime64_any_dtype(series):
            date_cols.append(col)
        elif pd.api.types.is_numeric_dtype(series):
            # Check if boolean or boolean-like integer
            unique_vals = series.dropna().unique()
            if len(unique_vals) <= 2 and all(x in [0, 1] for x in unique_vals):
                categorical_cols.append(col)
            else:
                numeric_cols.append(col)
        else:
            # Check string dates
            non_null = series.dropna()
            if not non_null.empty and len(non_null) > 5:
                try:
                    parsed_sample = pd.to_datetime(non_null.head(10), format="mixed", errors="coerce")
                    if parsed_sample.notnull().sum() / len(parsed_sample) >= 0.8:
                        date_cols.append(col)
                        continue
                except Exception:
                    pass
            categorical_cols.append(col)

    # Rule 1: Time Series
    if date_cols and numeric_cols:
        return {"chart_type": "line", "x_axis": date_cols[0], "y_axis": numeric_cols[0]}

    # Rule 2: Multiple Categories (Grouped Bar Chart)
    if len(categorical_cols) >= 2 and numeric_cols:
        return {
            "chart_type": "grouped_bar",
            "x_axis": categorical_cols[0],
            "y_axis": numeric_cols[0],
            "group_by": categorical_cols[1],
        }

    # Rule 3: Relationship (Scatter Plot)
    if len(numeric_cols) >= 2:
        return {"chart_type": "scatter", "x_axis": numeric_cols[0], "y_axis": numeric_cols[1]}

    # Rule 4: Category Comparison vs Part of Whole vs Ranking
    if categorical_cols and numeric_cols:
        cat_col = categorical_cols[0]
        num_col = numeric_cols[0]
        unique_cnt = df[cat_col].dropna().nunique()

        if unique_cnt <= 6:
            # Part of a whole
            return {"chart_type": "pie", "x_axis": cat_col, "y_axis": num_col}
        elif unique_cnt > 10:
            # Ranking / Horizontal comparison
            return {"chart_type": "horizontal_bar", "x_axis": cat_col, "y_axis": num_col}
        else:
            # Simple category comparison
            return {"chart_type": "bar", "x_axis": cat_col, "y_axis": num_col}

    # Rule 5: Distribution (Single Numeric column)
    if len(numeric_cols) == 1:
        return {"chart_type": "histogram", "x_axis": numeric_cols[0], "y_axis": "count"}

    # Rule 6: Fallback Default (First two columns as bar)
    if len(cols) >= 2:
        return {"chart_type": "bar", "x_axis": cols[0], "y_axis": cols[1]}

    # Single column fallback
    return {"chart_type": "bar", "x_axis": cols[0] if cols else "", "y_axis": cols[0] if cols else ""}


def format_chart_js_payload(df: pd.DataFrame, config: Dict[str, Any]) -> Dict[str, Any]:
    """Helper to convert a pandas DataFrame into ChartJS datasets format."""
    chart_type = config.get("chart_type", "bar")
    x_col = config.get("x_axis", "")
    y_col = config.get("y_axis", "")
    group_col = config.get("group_by", None)

    if df is None or df.empty or not x_col or not y_col:
        return {"labels": [], "datasets": []}

    # Standardize types for JSON serialization
    df_clean = df.copy()

    # Limit rows to 100 for display sanity (keep charts clean and fast)
    if len(df_clean) > 100 and chart_type != "scatter":
        df_clean = df_clean.head(100)

    # Helper to convert np types to python primitives
    def clean_val(x):
        if pd.isnull(x):
            return None
        if isinstance(x, (np.integer, np.signedinteger)):
            return int(x)
        if isinstance(x, np.floating):
            return float(x)
        if isinstance(x, (pd.Timestamp, np.datetime64)):
            return str(x)
        return str(x)

    # 1. Grouped Bar Chart logic
    if chart_type == "grouped_bar" and group_col:
        labels = [str(x) for x in df_clean[x_col].dropna().unique()]
        groups = df_clean[group_col].dropna().unique()
        datasets = []

        # Color palette
        colors = [
            "rgba(37, 99, 235, 0.75)",  # Blue
            "rgba(249, 115, 22, 0.75)",  # Orange
            "rgba(16, 185, 129, 0.75)",  # Green
            "rgba(124, 58, 237, 0.75)",  # Purple
            "rgba(236, 72, 153, 0.75)",  # Pink
        ]

        for idx, grp in enumerate(groups[:5]):  # limit to top 5 groups
            grp_df = df_clean[df_clean[group_col] == grp]
            data_map = {clean_val(row[x_col]): clean_val(row[y_col]) for _, row in grp_df.iterrows()}
            grp_data = [data_map.get(lbl, 0) for lbl in labels]

            color = colors[idx % len(colors)]
            datasets.append(
                {
                    "label": str(grp),
                    "data": grp_data,
                    "backgroundColor": color,
                    "borderColor": color.replace("0.75", "1"),
                    "borderWidth": 1.5,
                }
            )
        return {"labels": labels, "datasets": datasets}

    # 2. Scatter Plot logic
    if chart_type == "scatter":
        # Scatter data is a list of {x, y} coordinate dicts
        data = []
        # Limit scatter to first 500 rows for rendering speed
        for _, row in df_clean.head(500).iterrows():
            xv = clean_val(row[x_col])
            yv = clean_val(row[y_col])
            if xv is not None and yv is not None:
                data.append({"x": xv, "y": yv})

        return {
            "labels": [],
            "datasets": [
                {
                    "label": f"{y_col} vs {x_col}",
                    "data": data,
                    "backgroundColor": "rgba(37, 99, 235, 0.75)",
                    "borderColor": "rgb(37, 99, 235)",
                    "pointRadius": 5,
                }
            ],
        }

    # 3. Histogram logic
    if chart_type == "histogram":
        series = df_clean[x_col].dropna()
        if series.empty:
            return {"labels": [], "datasets": []}
        # Compute bins
        counts, bins = np.histogram(series, bins=10)
        labels = [f"{round(bins[i], 2)} - {round(bins[i+1], 2)}" for i in range(len(bins) - 1)]
        return {
            "labels": labels,
            "datasets": [
                {
                    "label": "Frequency",
                    "data": [int(x) for x in counts],
                    "backgroundColor": "rgba(124, 58, 237, 0.75)",
                    "borderColor": "rgb(124, 58, 237)",
                    "borderWidth": 1.5,
                }
            ],
        }

    # 4. Standard single series charts (Bar, Horizontal Bar, Line, Pie, Donut)
    labels = [str(x) for x in df_clean[x_col].apply(clean_val).tolist()]
    y_values = df_clean[y_col].apply(clean_val).tolist()

    # Dynamic palette for pie/donut
    if chart_type in ["pie", "donut"]:
        bg_colors = [
            "rgba(37, 99, 235, 0.75)",  # Blue
            "rgba(124, 58, 237, 0.75)",  # Purple
            "rgba(249, 115, 22, 0.75)",  # Orange
            "rgba(16, 185, 129, 0.75)",  # Green
            "rgba(236, 72, 153, 0.75)",  # Pink
            "rgba(234, 179, 8, 0.75)",  # Yellow
        ]
        bg_color = bg_colors[: len(labels)]
        border_color = [c.replace("0.75", "1") for c in bg_color]
    else:
        bg_color = "rgba(37, 99, 235, 0.75)"
        border_color = "rgb(37, 99, 235)"

    return {
        "labels": labels,
        "datasets": [
            {
                "label": f"{y_col}",
                "data": y_values,
                "backgroundColor": bg_color,
                "borderColor": border_color,
                "borderWidth": 1.5,
            }
        ],
    }


def calculate_kpis_for_dataframe(df: pd.DataFrame) -> List[Dict[str, Any]]:
    """Calculates summary KPIs (Total, Average, Max, Min, Median, Count, Unique, Missing %) from a DataFrame."""
    kpis = []
    if df is None or df.empty:
        return kpis

    row_count = len(df)

    for col in df.columns:
        series = df[col]
        non_null = series.dropna()
        missing_count = int(series.isnull().sum())
        missing_pct = round(missing_count / row_count * 100, 2) if row_count > 0 else 0.0
        unique_cnt = int(series.nunique())

        kpi_item = {"column": str(col), "count": row_count, "unique_values": unique_cnt, "missing_pct": missing_pct}

        # Calculate numeric statistics
        if pd.api.types.is_numeric_dtype(series) and not non_null.empty:
            kpi_item["total"] = round(float(non_null.sum()), 2)
            kpi_item["average"] = round(float(non_null.mean()), 2)
            kpi_item["max"] = round(float(non_null.max()), 2)
            kpi_item["min"] = round(float(non_null.min()), 2)
            kpi_item["median"] = round(float(non_null.median()), 2)
            kpi_item["is_numeric"] = True
        else:
            kpi_item["is_numeric"] = False
            if not non_null.empty:
                # String min/max representation
                try:
                    kpi_item["max"] = str(non_null.max())[:30]
                    kpi_item["min"] = str(non_null.min())[:30]
                except Exception:
                    pass

        kpis.append(kpi_item)

    return kpis


def generate_default_dashboard(dataset: UserDataset) -> Dict[str, Any]:
    """Generates a default multi-widget enterprise dashboard layout for a dataset.
    Uses precalculated cached profile information to achieve high performance (avoiding DataFrame copies).
    """
    widgets = []
    profile = dataset.profile_info or {}
    schema = dataset.schema_info or {}

    # 1. Generate KPIs from pre-computed profile/schema info
    kpi_cards = []
    numerical_cols = []
    categorical_cols = []
    date_cols = []

    if profile:
        col_types = profile.get("column_types", {})
        numerical_cols = col_types.get("numerical", [])
        categorical_cols = col_types.get("categorical", []) + col_types.get("text", [])
        date_cols = col_types.get("date", [])

        # Missing values stats
        missing_by_col = profile.get("quality_report", {}).get("missing_values", {}).get("by_column", {})

        # Map numerical cols to KPIs
        num_stats = profile.get("numerical_statistics", {})
        for col in numerical_cols[:4]:  # limit to first 4 numerical columns for dashboard simplicity
            stats = num_stats.get(col, {})
            missing_count = missing_by_col.get(col, 0)
            missing_pct = round(missing_count / dataset.row_count * 100, 2) if dataset.row_count > 0 else 0.0

            kpi_cards.append(
                {
                    "column": col,
                    "is_numeric": True,
                    "count": dataset.row_count,
                    "missing_pct": missing_pct,
                    "average": stats.get("mean"),
                    "median": stats.get("median"),
                    "max": stats.get("max"),
                    "min": stats.get("min"),
                    "total": round(stats.get("mean") * dataset.row_count, 2) if stats.get("mean") is not None else None,
                }
            )
    elif schema:
        # Fallback to schema_info if profile is missing
        for col, s in list(schema.items())[:4]:
            dtype = s.get("dtype", "")
            is_num = "int" in dtype or "float" in dtype or "double" in dtype
            if is_num:
                numerical_cols.append(col)
            else:
                categorical_cols.append(col)

            kpi_cards.append(
                {
                    "column": col,
                    "is_numeric": is_num,
                    "count": dataset.row_count,
                    "missing_pct": (
                        round(s.get("missing_count", 0) / dataset.row_count * 100, 2) if dataset.row_count > 0 else 0.0
                    ),
                    "average": s.get("mean"),
                    "max": s.get("max"),
                    "min": s.get("min"),
                    "unique_values": s.get("unique_count"),
                }
            )

    # 2. Build default charts by reading a minimal sample from SQL
    # To optimize for 100,000+ rows, we load only the columns of interest, not the entire DataFrame!
    sync_engine = get_sync_engine()

    # Choose X and Y axes
    selected_charts = []

    try:
        if date_cols and numerical_cols:
            # Select Time Series Line
            query = f"SELECT `{date_cols[0]}` as x, AVG(`{numerical_cols[0]}`) as y FROM {dataset.table_name} GROUP BY x ORDER BY x LIMIT 100"
            df_chart = pd.read_sql(query, con=sync_engine)
            if not df_chart.empty:
                chart_payload = format_chart_js_payload(df_chart, {"chart_type": "line", "x_axis": "x", "y_axis": "y"})
                selected_charts.append(
                    {
                        "id": "chart_timeseries",
                        "title": f"{numerical_cols[0]} Over Time ({date_cols[0]})",
                        "chart_type": "line",
                        "chart_data": chart_payload,
                        "x_axis": date_cols[0],
                        "y_axis": numerical_cols[0],
                    }
                )

        if categorical_cols and numerical_cols:
            # Select Category Bar
            cat = categorical_cols[0]
            num = numerical_cols[0]
            # Run group-by aggregation directly in SQLite
            query = f"SELECT `{cat}` as x, AVG(`{num}`) as y FROM {dataset.table_name} WHERE `{cat}` IS NOT NULL GROUP BY x ORDER BY y DESC LIMIT 15"
            df_chart = pd.read_sql(query, con=sync_engine)
            if not df_chart.empty:
                chart_type = "horizontal_bar" if len(df_chart) > 8 else "bar"
                chart_payload = format_chart_js_payload(
                    df_chart, {"chart_type": chart_type, "x_axis": "x", "y_axis": "y"}
                )
                selected_charts.append(
                    {
                        "id": "chart_category",
                        "title": f"Average {num} by {cat}",
                        "chart_type": chart_type,
                        "chart_data": chart_payload,
                        "x_axis": cat,
                        "y_axis": num,
                    }
                )

        if len(numerical_cols) >= 2:
            # Select Scatter
            n1 = numerical_cols[0]
            n2 = numerical_cols[1]
            query = f"SELECT `{n1}` as x, `{n2}` as y FROM {dataset.table_name} LIMIT 300"
            df_chart = pd.read_sql(query, con=sync_engine)
            if not df_chart.empty:
                chart_payload = format_chart_js_payload(
                    df_chart, {"chart_type": "scatter", "x_axis": "x", "y_axis": "y"}
                )
                selected_charts.append(
                    {
                        "id": "chart_relationship",
                        "title": f"Relationship: {n2} vs {n1}",
                        "chart_type": "scatter",
                        "chart_data": chart_payload,
                        "x_axis": n1,
                        "y_axis": n2,
                    }
                )

        if len(numerical_cols) == 1 or (not selected_charts and numerical_cols):
            # Select Histogram
            num = numerical_cols[0]
            query = f"SELECT `{num}` FROM {dataset.table_name} WHERE `{num}` IS NOT NULL LIMIT 1000"
            df_chart = pd.read_sql(query, con=sync_engine)
            if not df_chart.empty:
                chart_payload = format_chart_js_payload(
                    df_chart, {"chart_type": "histogram", "x_axis": num, "y_axis": "count"}
                )
                selected_charts.append(
                    {
                        "id": "chart_histogram",
                        "title": f"Distribution of {num}",
                        "chart_type": "histogram",
                        "chart_data": chart_payload,
                        "x_axis": num,
                        "y_axis": "count",
                    }
                )

        # Default fallback: Categorical values pie
        if not selected_charts and categorical_cols:
            cat = categorical_cols[0]
            query = f"SELECT `{cat}` as x, COUNT(*) as y FROM {dataset.table_name} GROUP BY x ORDER BY y DESC LIMIT 6"
            df_chart = pd.read_sql(query, con=sync_engine)
            if not df_chart.empty:
                chart_payload = format_chart_js_payload(df_chart, {"chart_type": "pie", "x_axis": "x", "y_axis": "y"})
                selected_charts.append(
                    {
                        "id": "chart_pie",
                        "title": f"Distribution of {cat}",
                        "chart_type": "pie",
                        "chart_data": chart_payload,
                        "x_axis": cat,
                        "y_axis": "count",
                    }
                )
    except Exception:
        logger.exception("Error executing aggregation queries for default dashboard")

    # Adapt layout grid column counts based on number of charts
    grid_columns = 1 if len(selected_charts) <= 1 else 2

    return {
        "metadata": {
            "dataset_id": dataset.id,
            "dataset_name": dataset.filename,
            "generated_time": datetime.utcnow().isoformat(),
            "number_of_charts": len(selected_charts),
            "number_of_kpis": len(kpi_cards),
            "number_of_records": dataset.row_count,
            "filters_applied": [],
        },
        "kpi_cards": kpi_cards,
        "charts": selected_charts,
        "layout": {"grid_columns": grid_columns},
    }


async def save_dashboard_history(session: Session, user_id: str, name: str, widgets: Dict[str, Any]) -> Dashboard:
    """Inserts a new dashboard layout into SQLite history."""
    db_dashboard = Dashboard(user_id=user_id, name=name, widgets=widgets)
    session.add(db_dashboard)
    await session.commit()
    await session.refresh(db_dashboard)
    return db_dashboard
