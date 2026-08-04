import logging
import time
import json
import uuid
import numpy as np
import pandas as pd
from typing import Any, Dict, List, Tuple, Optional
from sqlalchemy import select, update

from app.core.database import AsyncSessionLocal
from app.models.prompt_registry import RegisteredModel
from app.models.predictive import PredictiveHistory
from app.models.dataset import UserDataset
from app.api.routes.dataset import _load_dataframe_blocking, sanitize_column_name
from app.services.knowledge_graph_service import knowledge_graph_service
from app.services.monitoring_service import monitoring_service

logger = logging.getLogger(__name__)

# --- Lightweight custom NumPy ML algorithms ---

class CustomLogisticRegression:
    def __init__(self, learning_rate=0.1, epochs=300, l2_reg=0.01):
        self.learning_rate = learning_rate
        self.epochs = epochs
        self.l2_reg = l2_reg
        self.weights = None
        self.bias = 0.0

    def fit(self, X: np.ndarray, y: np.ndarray):
        n_samples, n_features = X.shape
        self.weights = np.zeros(n_features)
        self.bias = 0.0

        for _ in range(self.epochs):
            linear_model = np.dot(X, self.weights) + self.bias
            predictions = 1 / (1 + np.exp(-np.clip(linear_model, -20, 20)))
            
            dw = (1 / n_samples) * np.dot(X.T, (predictions - y)) + (self.l2_reg * self.weights) / n_samples
            db = (1 / n_samples) * np.sum(predictions - y)

            self.weights -= self.learning_rate * dw
            self.bias -= self.learning_rate * db

    def predict_proba(self, X: np.ndarray) -> np.ndarray:
        linear_model = np.dot(X, self.weights) + self.bias
        return 1 / (1 + np.exp(-np.clip(linear_model, -20, 20)))

    def predict(self, X: np.ndarray) -> np.ndarray:
        return (self.predict_proba(X) >= 0.5).astype(int)


class CustomRidgeRegression:
    def __init__(self, alpha=1.0):
        self.alpha = alpha
        self.weights = None
        self.bias = 0.0

    def fit(self, X: np.ndarray, y: np.ndarray):
        n_samples, n_features = X.shape
        X_b = np.hstack([np.ones((n_samples, 1)), X])
        
        A = self.alpha * np.eye(n_features + 1)
        A[0, 0] = 0.0
        
        beta = np.linalg.pinv(X_b.T @ X_b + A) @ X_b.T @ y
        self.bias = float(beta[0])
        self.weights = beta[1:]

    def predict(self, X: np.ndarray) -> np.ndarray:
        return np.dot(X, self.weights) + self.bias


class CustomKMeans:
    def __init__(self, k=3, max_iter=100, tol=1e-4):
        self.k = k
        self.max_iter = max_iter
        self.tol = tol
        self.centroids = None

    def fit(self, X: np.ndarray):
        n_samples = X.shape[0]
        if n_samples < self.k:
            self.centroids = X.copy()
            return
        
        # Simple KMeans++ style initialization
        idx = np.random.choice(n_samples, self.k, replace=False)
        self.centroids = X[idx].copy()
        
        for _ in range(self.max_iter):
            distances = np.linalg.norm(X[:, np.newaxis] - self.centroids, axis=2)
            labels = np.argmin(distances, axis=1)
            
            new_centroids = np.zeros_like(self.centroids)
            for i in range(self.k):
                points = X[labels == i]
                if len(points) > 0:
                    new_centroids[i] = points.mean(axis=0)
                else:
                    new_centroids[i] = X[np.random.choice(n_samples)]
            
            if np.linalg.norm(new_centroids - self.centroids) < self.tol:
                self.centroids = new_centroids
                break
            self.centroids = new_centroids

    def predict(self, X: np.ndarray) -> np.ndarray:
        distances = np.linalg.norm(X[:, np.newaxis] - self.centroids, axis=2)
        return np.argmin(distances, axis=1)


class CustomHoltForecasting:
    def __init__(self, alpha=0.5, beta=0.2):
        self.alpha = alpha
        self.beta = beta

    def fit_and_forecast(self, y: np.ndarray, steps=10) -> np.ndarray:
        n = len(y)
        if n < 2:
            return np.full(steps, float(y[0]) if n > 0 else 0.0)

        level = float(y[0])
        trend = float(y[1] - y[0])

        for i in range(1, n):
            last_level = level
            val = float(y[i])
            level = self.alpha * val + (1 - self.alpha) * (level + trend)
            trend = self.beta * (level - last_level) + (1 - self.beta) * trend

        forecasts = []
        for h in range(1, steps + 1):
            forecasts.append(level + h * trend)

        return np.array(forecasts)


# --- Helper data processing functions ---

def preprocess_dataset(df: pd.DataFrame, target: Optional[str] = None) -> Tuple[pd.DataFrame, List[str], Dict[str, Any]]:
    """Encodes variables, imputes nulls, normalizes features, and returns metadata."""
    df_clean = df.copy()
    
    # Simple null imputation
    for col in df_clean.columns:
        if df_clean[col].isnull().any():
            if pd.api.types.is_numeric_dtype(df_clean[col]):
                df_clean[col] = df_clean[col].fillna(df_clean[col].mean())
            else:
                df_clean[col] = df_clean[col].fillna(df_clean[col].mode().iloc[0] if not df_clean[col].mode().empty else "unknown")

    # Select numerical columns and encode categorical columns
    feature_cols = []
    encodings = {}
    
    for col in df_clean.columns:
        if col == target:
            continue
        
        # Ignore ID columns or constant columns
        if col.lower() in ["id", "uuid", "index"] or df_clean[col].nunique() <= 1:
            continue

        if pd.api.types.is_numeric_dtype(df_clean[col]):
            feature_cols.append(col)
        elif df_clean[col].nunique() < 10:  # Simple label encoding for low-cardinality strings
            unique_vals = sorted(list(df_clean[col].unique()))
            mapping = {val: i for i, val in enumerate(unique_vals)}
            df_clean[col] = df_clean[col].map(mapping)
            feature_cols.append(col)
            encodings[col] = mapping

    # Normalize features
    mean_std = {}
    for col in feature_cols:
        mean_val = float(df_clean[col].mean())
        std_val = float(df_clean[col].std())
        if std_val == 0:
            std_val = 1.0
        df_clean[col] = (df_clean[col] - mean_val) / std_val
        mean_std[col] = {"mean": mean_val, "std": std_val}

    return df_clean, feature_cols, {"encodings": encodings, "scaling": mean_std}


# --- Service implementation ---

class PredictiveAnalyticsService:
    async def discover_prediction_opportunities(self, dataset_id: str) -> Dict[str, Any]:
        """Scans dataset columns to auto-recommend ML task type and target column."""
        async with AsyncSessionLocal() as session:
            dataset = (await session.execute(
                select(UserDataset).where(UserDataset.id == dataset_id)
            )).scalar_one_or_none()
            if not dataset:
                raise ValueError("Dataset not found.")

        ext = dataset.filename.split(".")[-1].lower() if "." in dataset.filename else ""
        df = _load_dataframe_blocking(dataset.file_path, ext)
        df.columns = [sanitize_column_name(c) for c in df.columns]

        candidates = []
        
        # 1. Look for Binary / Low cardinality class labels (Classification)
        for col in df.columns:
            if col.lower() in ["id", "index", "date", "timestamp"]:
                continue
            nunique = df[col].nunique()
            if nunique == 2 or (nunique < 8 and not pd.api.types.is_numeric_dtype(df[col])):
                candidates.append({
                    "target": col,
                    "task_type": "classification",
                    "reason": f"Column has {nunique} unique classes, indicating a customer churn, fraud, or category classification.",
                    "confidence": 90
                })

        # 2. Look for Continuous target variable (Regression)
        for col in df.columns:
            if pd.api.types.is_numeric_dtype(df[col]) and df[col].nunique() > 20:
                if col.lower() in ["sales", "revenue", "price", "amount", "cost", "total"]:
                    candidates.append({
                        "target": col,
                        "task_type": "regression",
                        "reason": f"Numeric column with high variance, ideal for predicting performance metrics.",
                        "confidence": 85
                    })

        # 3. Look for Time Series trends
        date_cols = [col for col in df.columns if "date" in col.lower() or "time" in col.lower()]
        numeric_cols = [col for col in df.columns if pd.api.types.is_numeric_dtype(df[col]) and col not in date_cols]
        if date_cols and numeric_cols:
            candidates.append({
                "target": numeric_cols[0],
                "task_type": "forecasting",
                "reason": f"Detected date column '{date_cols[0]}' and numeric column '{numeric_cols[0]}', suggesting a time-series forecast.",
                "confidence": 80
            })

        # 4. Fallback Clustering segment recommendation
        candidates.append({
            "target": "None",
            "task_type": "clustering",
            "reason": "Unsupervised customer segmentation or outlier detection.",
            "confidence": 60
        })

        # Sort candidates by confidence
        candidates.sort(key=lambda x: x["confidence"], reverse=True)
        return {
            "dataset_id": dataset_id,
            "opportunities": candidates,
            "recommended": candidates[0] if candidates else None
        }

    async def train_automl_model(self, dataset_id: str, target: str, task_type: str, user_id: str) -> Dict[str, Any]:
        """Executes full AutoML train loop with cross-validation and hyperparameter search."""
        start_time = time.time()
        
        async with AsyncSessionLocal() as session:
            dataset = (await session.execute(
                select(UserDataset).where(UserDataset.id == dataset_id)
            )).scalar_one_or_none()
            if not dataset:
                raise ValueError("Dataset not found.")

        ext = dataset.filename.split(".")[-1].lower() if "." in dataset.filename else ""
        df = _load_dataframe_blocking(dataset.file_path, ext)
        df.columns = [sanitize_column_name(c) for c in df.columns]

        if task_type != "clustering" and target not in df.columns:
            raise ValueError(f"Target column '{target}' not present in dataset schema.")

        df_processed, feature_cols, prep_metadata = preprocess_dataset(df, target if task_type != "clustering" else None)
        
        # Prepare inputs
        X = df_processed[feature_cols].values
        
        if task_type == "classification":
            # Encode binary targets
            y_col = df[target].copy()
            if not pd.api.types.is_numeric_dtype(y_col):
                y_mapping = {val: i for i, val in enumerate(sorted(list(y_col.dropna().unique())))}
                y_col = y_col.map(y_mapping)
                prep_metadata["target_mapping"] = y_mapping
            else:
                # Convert to binary if numeric range > 1
                if y_col.nunique() > 2:
                    med = y_col.median()
                    y_col = (y_col > med).astype(int)
            y = y_col.fillna(0).values.astype(int)

        elif task_type == "regression":
            y = df[target].fillna(df[target].mean()).values.astype(float)
            
        elif task_type == "forecasting":
            # Sort by datetime column if available
            date_cols = [col for col in df.columns if "date" in col.lower() or "time" in col.lower()]
            if date_cols:
                df_sorted = df.sort_values(by=date_cols[0])
                y = df_sorted[target].fillna(df_sorted[target].mean()).values.astype(float)
            else:
                y = df[target].fillna(df[target].mean()).values.astype(float)

        elif task_type == "clustering":
            y = np.zeros(X.shape[0])  # Unsupervised

        n_samples = X.shape[0]
        
        # Hyperparameter Grid Search & Cross Validation
        best_model = None
        best_score = -float("inf") if task_type in ["classification", "clustering"] else float("inf")
        model_results = []

        if task_type == "classification":
            # Evaluate Logistic Regression parameters
            for lr in [0.01, 0.1]:
                for reg in [0.0, 0.1]:
                    scores = []
                    # 3-Fold Cross Validation
                    fold_size = n_samples // 3
                    for fold in range(3):
                        start_idx = fold * fold_size
                        end_idx = start_idx + fold_size
                        
                        val_idx = list(range(start_idx, end_idx))
                        train_idx = [i for i in range(n_samples) if i not in val_idx]
                        
                        if len(train_idx) == 0 or len(val_idx) == 0:
                            continue
                            
                        clf = CustomLogisticRegression(learning_rate=lr, epochs=200, l2_reg=reg)
                        clf.fit(X[train_idx], y[train_idx])
                        preds = clf.predict(X[val_idx])
                        accuracy = np.mean(preds == y[val_idx])
                        scores.append(accuracy)
                    
                    mean_score = np.mean(scores) if scores else 0.0
                    model_results.append({
                        "algorithm": "LogisticRegression",
                        "params": {"learning_rate": lr, "l2_reg": reg},
                        "metric_name": "accuracy",
                        "score": mean_score
                    })
                    
                    if mean_score > best_score:
                        best_score = mean_score
                        best_model = {
                            "algorithm": "LogisticRegression",
                            "model_obj": clf,
                            "params": {"learning_rate": lr, "l2_reg": reg},
                            "weights": clf.weights.tolist(),
                            "bias": float(clf.bias)
                        }

        elif task_type == "regression":
            # Evaluate Ridge parameters
            for reg in [0.0, 1.0, 10.0]:
                scores = []
                fold_size = n_samples // 3
                for fold in range(3):
                    start_idx = fold * fold_size
                    end_idx = start_idx + fold_size
                    
                    val_idx = list(range(start_idx, end_idx))
                    train_idx = [i for i in range(n_samples) if i not in val_idx]
                    
                    if len(train_idx) == 0 or len(val_idx) == 0:
                        continue
                        
                    reg_model = CustomRidgeRegression(alpha=reg)
                    reg_model.fit(X[train_idx], y[train_idx])
                    preds = reg_model.predict(X[val_idx])
                    # Metric: Mean Squared Error (minimize)
                    mse = np.mean((preds - y[val_idx]) ** 2)
                    scores.append(mse)
                
                mean_score = np.mean(scores) if scores else 0.0
                model_results.append({
                    "algorithm": "RidgeRegression",
                    "params": {"alpha": reg},
                    "metric_name": "mse",
                    "score": mean_score
                })
                
                if mean_score < best_score:  # Lower MSE is better
                    best_score = mean_score
                    best_model = {
                        "algorithm": "RidgeRegression",
                        "model_obj": reg_model,
                        "params": {"alpha": reg},
                        "weights": reg_model.weights.tolist(),
                        "bias": float(reg_model.bias)
                    }

        elif task_type == "forecasting":
            # Evaluate Holt smoothing factors
            for alpha in [0.2, 0.5, 0.8]:
                for beta in [0.1, 0.3]:
                    # Evaluate on last 20% of timeseries
                    split_idx = int(n_samples * 0.8)
                    if split_idx < 2:
                        split_idx = 1
                    train_y = y[:split_idx]
                    val_y = y[split_idx:]
                    
                    forecaster = CustomHoltForecasting(alpha=alpha, beta=beta)
                    preds = forecaster.fit_and_forecast(train_y, steps=len(val_y))
                    
                    # Compute Mean Absolute Percentage Error (MAPE)
                    mape = np.mean(np.abs((val_y - preds) / (val_y + 1e-5))) * 100
                    
                    model_results.append({
                        "algorithm": "HoltLinearTrend",
                        "params": {"alpha": alpha, "beta": beta},
                        "metric_name": "mape",
                        "score": mape
                    })
                    
                    if mape < best_score:
                        best_score = mape
                        best_model = {
                            "algorithm": "HoltLinearTrend",
                            "model_obj": forecaster,
                            "params": {"alpha": alpha, "beta": beta},
                            "y_history": y.tolist()
                        }

        elif task_type == "clustering":
            # Evaluate K values
            for k in [2, 3, 5]:
                scores = []
                kmeans = CustomKMeans(k=k)
                kmeans.fit(X)
                preds = kmeans.predict(X)
                # Metric: Inertia (Within-Cluster Sum of Squares)
                inertia = 0.0
                for i in range(k):
                    cluster_points = X[preds == i]
                    if len(cluster_points) > 0:
                        inertia += np.sum((cluster_points - kmeans.centroids[i]) ** 2)
                
                model_results.append({
                    "algorithm": "KMeans",
                    "params": {"k": k},
                    "metric_name": "inertia",
                    "score": inertia
                })
                
                # Check simple score representation (we prefer 3 clusters or lower inertia)
                if best_score == -float("inf") or inertia < best_score:
                    best_score = inertia
                    best_model = {
                        "algorithm": "KMeans",
                        "model_obj": kmeans,
                        "params": {"k": k},
                        "centroids": kmeans.centroids.tolist()
                    }

        # Select model and prepare metadata
        model_name = f"predictive_{task_type}_{target}_{uuid.uuid4().hex[:6]}"
        metrics_dict = {"best_score": float(best_score)}
        for item in model_results:
            metrics_dict[f"{item['algorithm']}_{item['metric_name']}_{item['params']}"] = float(item["score"])

        # Create active model in registry
        params_payload = {
            "task_type": task_type,
            "target": target,
            "dataset_id": dataset_id,
            "feature_cols": feature_cols,
            "preprocess": prep_metadata,
            "model_metadata": {k: v for k, v in best_model.items() if k != "model_obj"},
            "metrics": metrics_dict
        }

        async with AsyncSessionLocal() as session:
            # Register in Model Registry
            registered = RegisteredModel(
                name=model_name,
                provider="AutoML",
                version="1.0.0",
                parameters=params_payload,
                status="active"
            )
            session.add(registered)
            await session.commit()
            await session.refresh(registered)
            model_uuid = registered.id

            # Save in history
            hist = PredictiveHistory(
                dataset_id=dataset_id,
                target_variable=target,
                task_type=task_type,
                best_model_name=model_name,
                metrics=metrics_dict,
                parameters={"features": feature_cols, "algorithm": best_model["algorithm"], "hyperparameters": best_model["params"]}
            )
            session.add(hist)
            await session.commit()

        # Update Knowledge Graph automatically
        try:
            await knowledge_graph_service.build_graph(user_id)
            await self._update_knowledge_graph_predictive(dataset_id, target, model_uuid, model_name, task_type, feature_cols, user_id)
        except Exception as e:
            logger.error(f"Failed to update predictive model in knowledge graph: {e}")

        duration = time.time() - start_time
        
        # Record monitoring stats
        try:
            monitoring_service.record_predictive_training_run(duration, float(best_score))
        except Exception:
            pass

        return {
            "model_id": model_uuid,
            "model_name": model_name,
            "task_type": task_type,
            "target": target,
            "feature_count": len(feature_cols),
            "best_algorithm": best_model["algorithm"],
            "metrics": metrics_dict,
            "training_duration_seconds": round(duration, 2)
        }

    async def _update_knowledge_graph_predictive(self, dataset_id: str, target: str, model_uuid: str, model_name: str, task_type: str, features: List[str], user_id: str):
        """Registers predictive models, dependencies, target targets and lineages in KG."""
        async with AsyncSessionLocal() as session:
            from app.models.knowledge import KnowledgeEntity, KnowledgeRelationship
            
            # 1. Create Model Entity
            model_ent = KnowledgeEntity(
                id=str(uuid.uuid4()),
                name=model_name,
                entity_type="Model",
                properties=json.dumps({
                    "model_id": model_uuid,
                    "task_type": task_type,
                    "target_variable": target,
                    "features_count": len(features)
                }),
                source_id=f"model_{model_uuid}",
                user_id=user_id
            )
            session.add(model_ent)
            await session.flush()

            # 2. Get dataset entity
            ds_ent = (await session.execute(
                select(KnowledgeEntity).where(KnowledgeEntity.source_id == dataset_id, KnowledgeEntity.user_id == user_id)
            )).scalar_one_or_none()

            if ds_ent:
                # Add relationship: Model -> trained_on -> Dataset
                rel = KnowledgeRelationship(
                    id=str(uuid.uuid4()),
                    source_id=model_ent.id,
                    target_id=ds_ent.id,
                    relationship_type="trained_on",
                    confidence=1.0,
                    properties=json.dumps({"description": "Machine learning model trained on source dataset"}),
                    user_id=user_id
                )
                session.add(rel)

            # 3. Target Variable lineage column
            tar_key = f"col_{dataset_id}_{target}".lower()
            # Try looking up target variable columns in the KG
            tar_col = (await session.execute(
                select(KnowledgeEntity).where(KnowledgeEntity.name == target, KnowledgeEntity.entity_type == "Column", KnowledgeEntity.user_id == user_id)
            )).scalars().first()

            if tar_col:
                rel = KnowledgeRelationship(
                    id=str(uuid.uuid4()),
                    source_id=model_ent.id,
                    target_id=tar_col.id,
                    relationship_type="predicts_target",
                    confidence=1.0,
                    properties=json.dumps({"description": "Model target prediction label"}),
                    user_id=user_id
                )
                session.add(rel)

            await session.commit()

    async def get_registered_models(self) -> List[Dict[str, Any]]:
        """List registered predictive models."""
        async with AsyncSessionLocal() as session:
            records = (await session.execute(
                select(RegisteredModel).where(RegisteredModel.provider == "AutoML")
            )).scalars().all()
            return [
                {
                    "id": r.id,
                    "name": r.name,
                    "parameters": r.parameters,
                    "created_at": r.created_at.isoformat()
                }
                for r in records
            ]

    async def get_history(self) -> List[Dict[str, Any]]:
        """List historical model training logs."""
        async with AsyncSessionLocal() as session:
            records = (await session.execute(
                select(PredictiveHistory).order_by(PredictiveHistory.created_at.desc())
            )).scalars().all()
            return [
                {
                    "id": r.id,
                    "dataset_id": r.dataset_id,
                    "target_variable": r.target_variable,
                    "task_type": r.task_type,
                    "best_model_name": r.best_model_name,
                    "metrics": r.metrics,
                    "parameters": r.parameters,
                    "created_at": r.created_at.isoformat()
                }
                for r in records
            ]

    async def generate_predictions(self, model_id: str, dataset_id: str) -> Dict[str, Any]:
        """Loads model and applies inference parameters on target dataset."""
        start_time = time.time()
        
        async with AsyncSessionLocal() as session:
            model_record = (await session.execute(
                select(RegisteredModel).where(RegisteredModel.id == model_id)
            )).scalar_one_or_none()
            if not model_record:
                raise ValueError("Model not found in registry.")

            dataset = (await session.execute(
                select(UserDataset).where(UserDataset.id == dataset_id)
            )).scalar_one_or_none()
            if not dataset:
                raise ValueError("Dataset not found.")

        ext = dataset.filename.split(".")[-1].lower() if "." in dataset.filename else ""
        df = _load_dataframe_blocking(dataset.file_path, ext)
        df.columns = [sanitize_column_name(c) for c in df.columns]

        params = model_record.parameters
        task_type = params["task_type"]
        feature_cols = params["feature_cols"]
        prep_metadata = params["preprocess"]
        model_meta = params["model_metadata"]

        # Run preprocessing alignment
        df_imputed = df.copy()
        for col in df_imputed.columns:
            if df_imputed[col].isnull().any():
                if pd.api.types.is_numeric_dtype(df_imputed[col]):
                    df_imputed[col] = df_imputed[col].fillna(df_imputed[col].mean())
                else:
                    df_imputed[col] = df_imputed[col].fillna("unknown")

        # Encode categories
        enc = prep_metadata.get("encodings", {})
        for col, mapping in enc.items():
            if col in df_imputed.columns:
                df_imputed[col] = df_imputed[col].map(mapping).fillna(0)

        # Scale features
        scaling = prep_metadata.get("scaling", {})
        for col in feature_cols:
            if col not in df_imputed.columns:
                # Add dummy zero-filled column if missing in predict dataset
                df_imputed[col] = 0.0
            else:
                stats = scaling.get(col, {"mean": 0.0, "std": 1.0})
                df_imputed[col] = (df_imputed[col] - stats["mean"]) / stats["std"]

        X = df_imputed[feature_cols].values
        algorithm = model_meta["algorithm"]

        # Compute predictions based on saved model structures
        predictions = []
        
        if algorithm == "LogisticRegression":
            w = np.array(model_meta["weights"])
            b = model_meta["bias"]
            # Sigmoid prediction
            linear = np.dot(X, w) + b
            probs = 1 / (1 + np.exp(-np.clip(linear, -20, 20)))
            
            # If target class mappings exist, return string names
            target_map = prep_metadata.get("target_mapping")
            inv_map = {v: k for k, v in target_map.items()} if target_map else None
            
            for i, p in enumerate(probs):
                label = int(p >= 0.5)
                label_str = inv_map.get(label, str(label)) if inv_map else str(label)
                predictions.append({
                    "row_index": i,
                    "probability": float(p),
                    "prediction": label_str
                })

        elif algorithm == "RidgeRegression":
            w = np.array(model_meta["weights"])
            b = model_meta["bias"]
            preds = np.dot(X, w) + b
            for i, p in enumerate(preds):
                predictions.append({
                    "row_index": i,
                    "prediction": float(p)
                })

        elif algorithm == "HoltLinearTrend":
            history_y = np.array(model_meta["y_history"])
            alpha = model_meta["params"]["alpha"]
            beta = model_meta["params"]["beta"]
            forecaster = CustomHoltForecasting(alpha=alpha, beta=beta)
            forecasts = forecaster.fit_and_forecast(history_y, steps=10)
            
            for i, p in enumerate(forecasts):
                predictions.append({
                    "step": i + 1,
                    "prediction": float(p)
                })

        elif algorithm == "KMeans":
            centroids = np.array(model_meta["centroids"])
            # Calculate labels by closest centroid
            distances = np.linalg.norm(X[:, np.newaxis] - centroids, axis=2)
            labels = np.argmin(distances, axis=1)
            for i, l in enumerate(labels):
                predictions.append({
                    "row_index": i,
                    "cluster_label": int(l)
                })

        latency = time.time() - start_time
        return {
            "model_id": model_id,
            "task_type": task_type,
            "predictions": predictions,
            "predictions_count": len(predictions),
            "inference_latency_seconds": round(latency, 4)
        }

predictive_analytics_service = PredictiveAnalyticsService()
