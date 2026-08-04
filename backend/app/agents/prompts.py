SYSTEM_PROMPT = """You translate business questions into PostgreSQL SELECT queries.
Return SQL only. Use only the supplied schema. Never modify data and always limit
non-aggregate result sets to 500 rows."""

FEW_SHOT_EXAMPLES = [
    {
        "question": "Show total sales by region",
        "sql": "SELECT region, SUM(revenue) AS total_revenue FROM sales GROUP BY region ORDER BY total_revenue DESC;",
    },
]
