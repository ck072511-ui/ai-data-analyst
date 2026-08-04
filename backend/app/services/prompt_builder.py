from typing import List, Dict, Any, Optional

class PromptBuilder:
    def __init__(self):
        self.sql_generation_template = (
            "You are a Senior SQL Developer and Database Architect.\n"
            "Your task is to translate a user's natural language question into a single, valid, and highly optimized SQL query.\n\n"
            "=== TARGET DATABASE SCHEMAS ===\n"
            "{schema_context}\n\n"
            "=== DIALECT ===\n"
            "Target Dialect: {dialect}\n\n"
            "=== BUSINESS RULES & CONSTRAINTS ===\n"
            "1. Only return safe, read-only SELECT analytical queries.\n"
            "2. Never use DROP, DELETE, TRUNCATE, ALTER, UPDATE, INSERT, CREATE, or EXEC.\n"
            "3. Limit result sets to 500 rows unless specified otherwise.\n"
            "{business_rules}\n\n"
            "=== CONVERSATION HISTORY ===\n"
            "{conversation_history}\n\n"
            "=== USER QUESTION ===\n"
            "Question: {question}\n\n"
            "=== OUTPUT FORMAT ===\n"
            "Return JSON only in the following format:\n"
            "{{\n"
            "  \"sql\": \"YOUR_SQL_QUERY\",\n"
            "  \"confidence_score\": 0.95,\n"
            "  \"explanation\": \"A concise explanation of how the query resolves the question.\"\n"
            "}}\n"
            "Ensure the output contains nothing but the valid JSON object. Do not include markdown code block syntax around the JSON."
        )
        
        self.sql_explain_template = (
            "You are a Database Architect.\n"
            "Analyze and explain the following SQL query in plain English for business analysts.\n\n"
            "=== SCHEMA CONTEXT ===\n"
            "{schema_context}\n\n"
            "=== SQL QUERY ===\n"
            "{sql}\n\n"
            "=== INSTRUCTIONS ===\n"
            "Provide a brief, clear explanation (2-3 sentences max) detailing what fields and tables are queried, any filters applied, and the business purpose of this query."
        )

        self.sql_optimize_template = (
            "You are a Principal Database Administrator.\n"
            "Optimize and rewrite the following SQL query to improve performance.\n\n"
            "=== SCHEMA CONTEXT ===\n"
            "{schema_context}\n\n"
            "=== DIALECT ===\n"
            "{dialect}\n\n"
            "=== SQL QUERY ===\n"
            "{sql}\n\n"
            "=== EXPLAIN PLAN ===\n"
            "{explain_plan}\n\n"
            "=== OUTPUT FORMAT ===\n"
            "Return JSON only in the following format:\n"
            "{{\n"
            "  \"optimized_sql\": \"REWRITTEN_SQL_QUERY\",\n"
            "  \"performance_impact\": \"Estimated impact (e.g. reduced joins, indexes suggested, lower cost)\",\n"
            "  \"suggestions\": [\"index suggestions or rewrite reasons\"]\n"
            "}}\n"
            "Ensure the output contains nothing but the valid JSON object. Do not include markdown code block syntax around the JSON."
        )

        self.ai_cleaning_recommendation_template = (
            "You are a Staff Data Scientist and Expert Data Cleaning & Quality Engineer.\n"
            "Your task is to analyze the structural and formatting metadata profile of a user's dataset and generate a comprehensive cleaning and feature engineering transformation plan.\n\n"
            "=== DATASET PROFILE METADATA ===\n"
            "Filename: {filename}\n"
            "Row Count: {row_count}\n"
            "Column Count: {col_count}\n"
            "Column Schemas & Stats:\n"
            "{profile_summary}\n\n"
            "=== ANALYSIS OBJECTIVES ===\n"
            "Identify details regarding:\n"
            "1. Missing values, empty/constant columns.\n"
            "2. Duplicate rows and duplicate columns.\n"
            "3. Numeric outliers (IQR or Zscore methods).\n"
            "4. Formatting issues: Whitespace padding, mixed casing, invalid emails, phone formats, and dates.\n"
            "5. Mixed data types.\n"
            "6. Scaling opportunities and Categorical column encoding.\n"
            "7. Feature Engineering opportunities: age calculations, date part extractions, segment bucketing.\n\n"
            "=== OUTPUT FORMAT ===\n"
            "You must output JSON only in the following schema:\n"
            "{{\n"
            "  \"dataset_explanation\": \"A natural language explanation summarizing key data quality issues, patterns, and mixed casing anomalies.\",\n"
            "  \"overall_quality_improvement_est\": 15.5,\n"
            "  \"confidence_score\": 0.85,\n"
            "  \"execution_plan\": [\n"
            "    {{\n"
            "      \"step_id\": 1,\n"
            "      \"category\": \"missing_values\",\n"
            "      \"column\": \"COLUMN_NAME\",\n"
            "      \"transformation\": \"impute_mean|impute_median|impute_mode|ffill|bfill|drop_rows|drop_columns|remove_duplicate_rows|remove_duplicate_columns|cap_iqr|remove_rows_iqr|trim_spaces|to_upper|to_lower|to_title|label_encode|one_hot_encode|frequency_encode|standard_scale|minmax_scale|robust_scale|standardize_dates|normalize_phones|clean_emails|extract_date_parts|calculate_age|bucketize_numeric|text_normalization\",\n"
            "      \"description\": \"Actionable summary description.\",\n"
            "      \"reason\": \"Reason why this transformation was recommended.\",\n"
            "      \"estimated_impact\": \"Estimated quality score impact/improvement.\",\n"
            "      \"confidence\": 0.90,\n"
            "      \"rollback_compatibility\": true\n"
            "    }}\n"
            "  ]\n"
            "}}\n"
            "Ensure the output contains nothing but the valid JSON object. Do not include markdown code block syntax around the JSON."
        )


    def build_sql_generation_prompt(
        self,
        schema_context: str,
        question: str,
        history: List[Dict[str, str]],
        dialect: str,
        business_rules: Optional[List[str]] = None
    ) -> str:
        rules_str = ""
        if business_rules:
            rules_str = "\n".join(f"- {rule}" for rule in business_rules)
        
        history_parts = []
        for msg in history:
            role = "User" if msg.get("role") == "user" else "Assistant"
            content = msg.get("content", "")
            history_parts.append(f"{role}: {content}")
        history_str = "\n".join(history_parts) if history_parts else "No previous conversation history."
        
        return self.sql_generation_template.format(
            schema_context=schema_context,
            dialect=dialect,
            business_rules=rules_str,
            conversation_history=history_str,
            question=question
        )

    def build_explain_prompt(self, sql: str, schema_context: str) -> str:
        return self.sql_explain_template.format(
            sql=sql,
            schema_context=schema_context
        )

    def build_optimize_prompt(self, sql: str, schema_context: str, dialect: str, explain_plan: str) -> str:
        return self.sql_optimize_template.format(
            sql=sql,
            schema_context=schema_context,
            dialect=dialect,
            explain_plan=explain_plan
        )

    def build_ai_cleaning_prompt(self, filename: str, row_count: int, col_count: int, profile_summary: str) -> str:
        return self.ai_cleaning_recommendation_template.format(
            filename=filename,
            row_count=row_count,
            col_count=col_count,
            profile_summary=profile_summary
        )
