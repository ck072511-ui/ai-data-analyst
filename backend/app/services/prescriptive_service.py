import logging
import time
import numpy as np
from typing import Any, Dict, List, Optional
from sqlalchemy import select

from app.core.database import AsyncSessionLocal
from app.models.prompt_registry import RegisteredModel

logger = logging.getLogger(__name__)

class PrescriptiveService:
    async def simulate_scenario(self, model_id: str, base_features: Dict[str, float], modifications: Dict[str, float]) -> Dict[str, Any]:
        """Runs what-if simulation: calculates model outputs under user-modified parameters."""
        async with AsyncSessionLocal() as session:
            model_record = (await session.execute(
                select(RegisteredModel).where(RegisteredModel.id == model_id)
            )).scalar_one_or_none()
            if not model_record:
                raise ValueError("Model not found in registry.")

        params = model_record.parameters
        task_type = params["task_type"]
        feature_cols = params["feature_cols"]
        prep_metadata = params["preprocess"]
        model_meta = params["model_metadata"]
        algorithm = model_meta["algorithm"]

        # Merge base features and modifications
        simulated_features = base_features.copy()
        simulated_features.update(modifications)

        # Scale the features
        scaling = prep_metadata.get("scaling", {})
        X_row = np.zeros(len(feature_cols))
        
        for idx, col in enumerate(feature_cols):
            val = float(simulated_features.get(col, 0.0))
            # If categorical map encoding is used
            enc = prep_metadata.get("encodings", {}).get(col, {})
            if enc and col in simulated_features:
                raw_val = str(simulated_features[col])
                val = float(enc.get(raw_val, 0.0))

            # Apply scaling
            stats = scaling.get(col, {"mean": 0.0, "std": 1.0})
            X_row[idx] = (val - stats["mean"]) / stats["std"]

        # Predict output value
        prediction_val = 0.0
        probability_val = None

        if algorithm == "LogisticRegression":
            w = np.array(model_meta["weights"])
            b = model_meta["bias"]
            linear = np.dot(X_row, w) + b
            prob = 1 / (1 + np.exp(-np.clip(linear, -20, 20)))
            probability_val = float(prob)
            prediction_val = 1.0 if prob >= 0.5 else 0.0

        elif algorithm == "RidgeRegression":
            w = np.array(model_meta["weights"])
            b = model_meta["bias"]
            prediction_val = float(np.dot(X_row, w) + b)

        return {
            "model_id": model_id,
            "task_type": task_type,
            "base_features": base_features,
            "modifications": modifications,
            "simulated_features": simulated_features,
            "predicted_value": prediction_val,
            "predicted_probability": probability_val
        }

    async def generate_prescriptive_actions(
        self,
        model_id: str,
        base_features: Dict[str, float],
        actionable_features: List[str],
        business_rules: Dict[str, Any],
        target_direction: str = "minimize"  # "minimize" or "maximize"
    ) -> Dict[str, Any]:
        """Simulates combinations of actionable features to suggest ranked optimization recommendations."""
        start_time = time.time()
        
        # Calculate baseline forecast value
        base_res = await self.simulate_scenario(model_id, base_features, {})
        base_val = base_res["predicted_probability"] if base_res["predicted_probability"] is not None else base_res["predicted_value"]

        recommendations = []

        # For each actionable feature, simulate typical adjustments complying with rules
        for col in actionable_features:
            rules = business_rules.get(col, {})
            # Determine candidate test values
            test_values = []
            
            if "values" in rules:
                test_values = rules["values"]
            elif "min" in rules and "max" in rules:
                # Test 3 points: min, mid, max
                test_values = [rules["min"], (rules["min"] + rules["max"]) / 2, rules["max"]]
            else:
                # Default numeric test step: subtract/add 10%, 20%
                curr = float(base_features.get(col, 0.0))
                if curr != 0.0:
                    test_values = [curr * 0.8, curr * 0.9, curr * 1.1, curr * 1.2]
                else:
                    test_values = [-1.0, 1.0]

            for test_val in test_values:
                # Run what-if simulation
                sim_res = await self.simulate_scenario(model_id, base_features, {col: test_val})
                sim_val = sim_res["predicted_probability"] if sim_res["predicted_probability"] is not None else sim_res["predicted_value"]

                # Calculate improvement score
                diff = sim_val - base_val
                improvement = -diff if target_direction == "minimize" else diff
                
                # Check business rules constraints
                is_valid = True
                if "max_limit" in rules and test_val > rules["max_limit"]:
                    is_valid = False
                if "min_limit" in rules and test_val < rules["min_limit"]:
                    is_valid = False

                if is_valid and improvement > 0:
                    recommendations.append({
                        "feature": col,
                        "action_value": test_val,
                        "base_value": base_features.get(col, 0.0),
                        "simulated_score": sim_val,
                        "score_improvement": improvement,
                        "description": f"Adjust '{col}' from {base_features.get(col, 0.0)} to {test_val} to optimize outcome."
                    })

        # Rank recommendations by improvement
        recommendations.sort(key=lambda x: x["score_improvement"], reverse=True)

        return {
            "model_id": model_id,
            "baseline_score": base_val,
            "target_direction": target_direction,
            "recommendations": recommendations,
            "recommendation_count": len(recommendations),
            "generation_time_seconds": round(time.time() - start_time, 4)
        }

prescriptive_service = PrescriptiveService()
