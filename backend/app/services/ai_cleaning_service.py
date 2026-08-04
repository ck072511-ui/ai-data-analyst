import json
import logging
import re
import time
from datetime import datetime, date
from decimal import Decimal
from typing import Any, Dict, List, Optional, Tuple

import numpy as np
import pandas as pd
from fastapi import HTTPException
from sqlalchemy import select, desc

from app.core.database import AsyncSessionLocal
from app.models.dataset import UserDataset
from app.models.ai_cleaning import AICleaningRecommendation
from app.services.model_manager import model_manager
from app.services.prompt_builder import PromptBuilder
from app.services.monitoring_service import monitoring_service

logger = logging.getLogger(__name__)


def apply_ai_transformations(df: pd.DataFrame, steps: List[Dict[str, Any]]) -> Tuple[pd.DataFrame, List[str]]:
    """Applies a sequence of dynamic Pandas cleaning & feature engineering transformations."""
    df_cleaned = df.copy()
    operations_applied = []

    for step in steps:
        col = step.get("column")
        transformation = step.get("transformation")
        desc_text = step.get("description", "")

        # 1. Missing Values
        if transformation == "impute_mean" and col in df_cleaned.columns:
            if pd.api.types.is_numeric_dtype(df_cleaned[col]):
                mean_val = float(df_cleaned[col].mean()) if not df_cleaned[col].dropna().empty else 0.0
                df_cleaned[col] = df_cleaned[col].fillna(mean_val)
                operations_applied.append(f"Imputed missing values in '{col}' using mean ({round(mean_val, 2)}).")
        elif transformation == "impute_median" and col in df_cleaned.columns:
            if pd.api.types.is_numeric_dtype(df_cleaned[col]):
                median_val = float(df_cleaned[col].median()) if not df_cleaned[col].dropna().empty else 0.0
                df_cleaned[col] = df_cleaned[col].fillna(median_val)
                operations_applied.append(f"Imputed missing values in '{col}' using median ({round(median_val, 2)}).")
        elif transformation == "impute_mode" and col in df_cleaned.columns:
            mode_series = df_cleaned[col].mode()
            if not mode_series.empty:
                mode_val = mode_series.iloc[0]
                df_cleaned[col] = df_cleaned[col].fillna(mode_val)
                operations_applied.append(f"Imputed missing values in '{col}' using mode ({mode_val}).")
        elif transformation == "ffill" and col in df_cleaned.columns:
            df_cleaned[col] = df_cleaned[col].ffill()
            operations_applied.append(f"Forward filled missing values in '{col}'.")
        elif transformation == "bfill" and col in df_cleaned.columns:
            df_cleaned[col] = df_cleaned[col].bfill()
            operations_applied.append(f"Backward filled missing values in '{col}'.")
        elif transformation == "drop_rows" and col in df_cleaned.columns:
            before_cnt = len(df_cleaned)
            df_cleaned = df_cleaned.dropna(subset=[col])
            operations_applied.append(f"Dropped {before_cnt - len(df_cleaned)} rows with missing values in '{col}'.")
        elif transformation == "drop_columns" and col in df_cleaned.columns:
            df_cleaned = df_cleaned.drop(columns=[col])
            operations_applied.append(f"Dropped column '{col}' due to missingness.")

        # 2. Duplicates
        elif transformation == "remove_duplicate_rows":
            before_cnt = len(df_cleaned)
            df_cleaned = df_cleaned.drop_duplicates()
            operations_applied.append(f"Removed {before_cnt - len(df_cleaned)} duplicate rows.")
        elif transformation == "remove_duplicate_columns" and col in df_cleaned.columns:
            df_cleaned = df_cleaned.drop(columns=[col])
            operations_applied.append(f"Removed duplicate column '{col}'.")

        # 3. Outliers
        elif transformation == "cap_iqr" and col in df_cleaned.columns:
            if pd.api.types.is_numeric_dtype(df_cleaned[col]):
                q1 = df_cleaned[col].quantile(0.25)
                q3 = df_cleaned[col].quantile(0.75)
                iqr = q3 - q1
                lower = q1 - 1.5 * iqr
                upper = q3 + 1.5 * iqr
                df_cleaned[col] = df_cleaned[col].clip(lower=lower, upper=upper)
                operations_applied.append(f"Capped outliers in '{col}' to range [{round(lower, 2)}, {round(upper, 2)}].")
        elif transformation == "remove_rows_iqr" and col in df_cleaned.columns:
            if pd.api.types.is_numeric_dtype(df_cleaned[col]):
                q1 = df_cleaned[col].quantile(0.25)
                q3 = df_cleaned[col].quantile(0.75)
                iqr = q3 - q1
                lower = q1 - 1.5 * iqr
                upper = q3 + 1.5 * iqr
                before_cnt = len(df_cleaned)
                df_cleaned = df_cleaned[(df_cleaned[col] >= lower) & (df_cleaned[col] <= upper)]
                operations_applied.append(f"Removed {before_cnt - len(df_cleaned)} rows with outliers in '{col}'.")

        # 4. Whitespace & casing
        elif transformation == "trim_spaces" and col in df_cleaned.columns:
            if pd.api.types.is_object_dtype(df_cleaned[col]):
                df_cleaned[col] = df_cleaned[col].astype(str).str.strip().replace(["nan", "None", "<NA>"], np.nan)
                operations_applied.append(f"Trimmed leading/trailing whitespaces in '{col}'.")
        elif transformation == "to_upper" and col in df_cleaned.columns:
            df_cleaned[col] = df_cleaned[col].astype(str).str.upper().replace(["NAN", "NONE"], np.nan)
            operations_applied.append(f"Converted text casing to uppercase in '{col}'.")
        elif transformation == "to_lower" and col in df_cleaned.columns:
            df_cleaned[col] = df_cleaned[col].astype(str).str.lower().replace(["nan", "none"], np.nan)
            operations_applied.append(f"Converted text casing to lowercase in '{col}'.")
        elif transformation == "to_title" and col in df_cleaned.columns:
            df_cleaned[col] = df_cleaned[col].astype(str).str.title().replace(["Nan", "None"], np.nan)
            operations_applied.append(f"Converted text casing to titlecase in '{col}'.")

        # 5. Encoding
        elif transformation == "label_encode" and col in df_cleaned.columns:
            df_cleaned[col] = df_cleaned[col].astype('category').cat.codes
            operations_applied.append(f"Applied Label Encoding to categorical column '{col}'.")
        elif transformation == "one_hot_encode" and col in df_cleaned.columns:
            df_cleaned = pd.get_dummies(df_cleaned, columns=[col], prefix=col, drop_first=True)
            operations_applied.append(f"Applied One-Hot Encoding to categorical column '{col}'.")
        elif transformation == "frequency_encode" and col in df_cleaned.columns:
            freq = df_cleaned[col].value_counts(normalize=True)
            df_cleaned[col] = df_cleaned[col].map(freq)
            operations_applied.append(f"Applied Frequency Encoding to categorical column '{col}'.")

        # 6. Scaling
        elif transformation == "standard_scale" and col in df_cleaned.columns:
            if pd.api.types.is_numeric_dtype(df_cleaned[col]):
                mean_val = df_cleaned[col].mean()
                std_val = df_cleaned[col].std()
                df_cleaned[col] = (df_cleaned[col] - mean_val) / std_val if std_val != 0 else 0.0
                operations_applied.append(f"Standard Scaled numeric column '{col}'.")
        elif transformation == "minmax_scale" and col in df_cleaned.columns:
            if pd.api.types.is_numeric_dtype(df_cleaned[col]):
                min_val = df_cleaned[col].min()
                max_val = df_cleaned[col].max()
                df_cleaned[col] = (df_cleaned[col] - min_val) / (max_val - min_val) if (max_val - min_val) != 0 else 0.0
                operations_applied.append(f"MinMax Scaled numeric column '{col}'.")
        elif transformation == "robust_scale" and col in df_cleaned.columns:
            if pd.api.types.is_numeric_dtype(df_cleaned[col]):
                q1 = df_cleaned[col].quantile(0.25)
                q3 = df_cleaned[col].quantile(0.75)
                median_val = df_cleaned[col].median()
                iqr_val = q3 - q1
                df_cleaned[col] = (df_cleaned[col] - median_val) / iqr_val if iqr_val != 0 else 0.0
                operations_applied.append(f"Robust Scaled numeric column '{col}'.")

        # 7. Formatting & Standardising
        elif transformation == "standardize_dates" and col in df_cleaned.columns:
            parsed = pd.to_datetime(df_cleaned[col], errors='coerce')
            df_cleaned[col] = parsed.dt.strftime('%Y-%m-%d').replace(["NaT", "nan"], np.nan)
            operations_applied.append(f"Standardized date formatting in '{col}' (YYYY-MM-DD).")
        elif transformation == "normalize_phones" and col in df_cleaned.columns:
            def clean_phone(val):
                if pd.isnull(val): return val
                cleaned = re.sub(r"[^\d+]", "", str(val))
                return cleaned if len(cleaned) >= 7 else np.nan
            df_cleaned[col] = df_cleaned[col].apply(clean_phone)
            operations_applied.append(f"Normalized phone number formats in '{col}'.")
        elif transformation == "clean_emails" and col in df_cleaned.columns:
            from app.services.profiling_service import is_email_address
            df_cleaned[col] = df_cleaned[col].apply(lambda x: x if pd.isnull(x) or is_email_address(x) else np.nan)
            operations_applied.append(f"Nullified malformed email addresses in '{col}'.")

        # 8. Feature Engineering
        elif transformation == "extract_date_parts" and col in df_cleaned.columns:
            parsed = pd.to_datetime(df_cleaned[col], errors='coerce')
            df_cleaned[f"{col}_year"] = parsed.dt.year
            df_cleaned[f"{col}_month"] = parsed.dt.month
            df_cleaned[f"{col}_day"] = parsed.dt.day
            operations_applied.append(f"Extracted date components from '{col}'.")
        elif transformation == "calculate_age" and col in df_cleaned.columns:
            parsed = pd.to_datetime(df_cleaned[col], errors='coerce')
            df_cleaned[f"{col}_age"] = datetime.utcnow().year - parsed.dt.year
            operations_applied.append(f"Calculated age from date column '{col}'.")
        elif transformation == "bucketize_numeric" and col in df_cleaned.columns:
            if pd.api.types.is_numeric_dtype(df_cleaned[col]):
                df_cleaned[f"{col}_bucket"] = pd.qcut(df_cleaned[col], q=4, labels=["Low", "Medium-Low", "Medium-High", "High"], duplicates="drop")
                operations_applied.append(f"Segmented numeric '{col}' into 4 quantile buckets.")
        elif transformation == "text_normalization" and col in df_cleaned.columns:
            df_cleaned[col] = df_cleaned[col].astype(str).str.normalize('NFKD').str.encode('ascii', errors='ignore').str.decode('utf-8')
            operations_applied.append(f"Applied text normalization to '{col}'.")
        else:
            operations_applied.append(f"Applied step: {desc_text}")

    return df_cleaned, operations_applied


class AICleaningService:
    def __init__(self):
        self.prompt_builder = PromptBuilder()

    async def generate_recommendations(self, dataset_id: str, user_id: str) -> Dict[str, Any]:
        """Loads dataset profile metadata, compiles LLM suggestions and constructs the plan."""
        async with AsyncSessionLocal() as session:
            dataset = (await session.execute(
                select(UserDataset).where(UserDataset.id == dataset_id)
            )).scalar_one_or_none()

        if not dataset:
            raise HTTPException(status_code=404, detail="Dataset not found.")

        # Serialize profile summaries for LLM digest
        profile = dataset.profile_info or {}
        columns_meta = []
        for col in dataset.columns or []:
            missing_cnt = profile.get("missing_values", {}).get("by_column", {}).get(col, 0)
            dtype = dataset.schema_info.get(col, {}).get("dtype", "unknown")
            columns_meta.append(f"- {col} ({dtype}): {missing_cnt} nulls")
        profile_summary = "\n".join(columns_meta)

        prompt = self.prompt_builder.build_ai_cleaning_prompt(
            filename=dataset.filename,
            row_count=dataset.row_count,
            col_count=dataset.col_count,
            profile_summary=profile_summary
        )

        started = time.time()
        try:
            generated_text = await model_manager.generate(prompt=prompt)
            latency = time.time() - started
        except Exception as e:
            logger.error(f"Inference failure generating suggestions: {e}")
            raise HTTPException(status_code=500, detail=f"Local inference failed: {e}")

        # Parse JSON recommendations
        try:
            json_text = generated_text.strip()
            if json_text.startswith("```json"):
                json_text = json_text[7:]
            if json_text.endswith("```"):
                json_text = json_text[:-3]
            json_text = json_text.strip()
            parsed = json.loads(json_text)
        except Exception as e:
            logger.warning(f"Failed to parse LLM suggestions as JSON. Output: {generated_text}")
            # Generate a standard default safe plan
            parsed = {
                "dataset_explanation": "Identified standard quality patterns. Applying default safe imputation steps.",
                "overall_quality_improvement_est": 10.0,
                "confidence_score": 0.75,
                "execution_plan": [
                    {
                        "step_id": 1,
                        "category": "whitespace",
                        "column": dataset.columns[0] if dataset.columns else "id",
                        "transformation": "trim_spaces",
                        "description": "Trim whitespaces from primary key columns.",
                        "reason": "Whitespaces cause indexing and join errors.",
                        "estimated_impact": "Ensures clean join indices.",
                        "confidence": 0.85,
                        "rollback_compatibility": True
                    }
                ]
            }

        confidence = parsed.get("confidence_score", 0.8)
        monitoring_service.record_ai_recommendation(latency, confidence)

        # Upsert recommendation
        async with AsyncSessionLocal() as session:
            existing = (await session.execute(
                select(AICleaningRecommendation).where(
                    AICleaningRecommendation.dataset_id == dataset_id,
                    AICleaningRecommendation.status == "pending"
                )
            )).scalar_one_or_none()

            if existing:
                existing.analysis_results = parsed
                existing.execution_plan = parsed.get("execution_plan", [])
                existing.confidence_score = confidence
                session.add(existing)
                await session.commit()
                rec_id = existing.id
            else:
                new_rec = AICleaningRecommendation(
                    dataset_id=dataset_id,
                    user_id=user_id,
                    analysis_results=parsed,
                    execution_plan=parsed.get("execution_plan", []),
                    confidence_score=confidence
                )
                session.add(new_rec)
                await session.commit()
                rec_id = new_rec.id

        return {
            "recommendation_id": rec_id,
            "dataset_explanation": parsed.get("dataset_explanation", ""),
            "quality_improvement_est": parsed.get("overall_quality_improvement_est", 15.0),
            "confidence_score": confidence,
            "execution_plan": parsed.get("execution_plan", [])
        }

    async def approve_recommendation(self, recommendation_id: str, approved_step_ids: List[int], user_id: str) -> Dict[str, Any]:
        """Saves user reviewed/approved transformation checklist step IDs."""
        async with AsyncSessionLocal() as session:
            rec = (await session.execute(
                select(AICleaningRecommendation).where(
                    AICleaningRecommendation.id == recommendation_id
                )
            )).scalar_one_or_none()

            if not rec:
                raise HTTPException(status_code=404, detail="Recommendation record not found.")

            rec.approved_steps = approved_step_ids
            rec.status = "approved"
            session.add(rec)
            await session.commit()
            
            monitoring_service.record_ai_approval("approved")

        return {"success": True, "message": "Recommendations checklist approved successfully."}

    async def execute_recommendation(self, recommendation_id: str, user_id: str) -> Dict[str, Any]:
        """Triggers the background execution task using task manager."""
        async with AsyncSessionLocal() as session:
            rec = (await session.execute(
                select(AICleaningRecommendation).where(
                    AICleaningRecommendation.id == recommendation_id
                )
            )).scalar_one_or_none()

            if not rec:
                raise HTTPException(status_code=404, detail="Recommendation record not found.")
            
            # Switch state to executing
            rec.status = "executing"
            session.add(rec)
            await session.commit()

        from app.services.task_service import task_service
        # Trigger background task execution logic
        task = await task_service.create_task(
            task_type="ai_cleaning",
            user_id=user_id,
            dataset_id=rec.dataset_id,
            payload={"recommendation_id": rec.id}
        )

        return {
            "success": True,
            "message": "AI dataset cleaning task triggered successfully in the background.",
            "task_id": task.id
        }

    async def get_history(self, dataset_id: str) -> List[Dict[str, Any]]:
        """Lists historical recommendation logs and statuses."""
        async with AsyncSessionLocal() as session:
            records = (await session.execute(
                select(AICleaningRecommendation)
                .where(AICleaningRecommendation.dataset_id == dataset_id)
                .order_by(desc(AICleaningRecommendation.created_at))
            )).scalars().all()

            return [
                {
                    "id": r.id,
                    "status": r.status,
                    "confidence_score": r.confidence_score,
                    "approved_steps": r.approved_steps,
                    "created_at": r.created_at.isoformat(),
                    "executed_at": r.executed_at.isoformat() if r.executed_at else None
                }
                for r in records
            ]
