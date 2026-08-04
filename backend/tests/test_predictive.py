import os
import sys
import json
import pytest
from unittest.mock import AsyncMock, patch
from fastapi.testclient import TestClient

# Adjust path to find backend
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

# Set environment variables for testing before importing main app
os.environ["DATABASE_URL"] = "sqlite:///./test_predictive.db"
os.environ["SECRET_KEY"] = "test-secret-key-must-be-long-enough-32-chars-at-least"
os.environ["ENVIRONMENT"] = "development"

from sqlalchemy import select
from app.main import app
from app.core.database import Base, AsyncSessionLocal
from app.core.security import get_current_user
from app.services.predictive_analytics_service import predictive_analytics_service
from app.services.prescriptive_service import prescriptive_service
from app.services.copilot_service import copilot_service
from app.models.dataset import UserDataset
from app.models.prompt_registry import RegisteredModel
from app.models.predictive import PredictiveHistory
from app.models.workflow import Workflow, WorkflowExecution

client = TestClient(app)

@pytest.fixture(scope="module", autouse=True)
def setup_database():
    from sqlalchemy import create_engine
    from app.core.database import engine

    db_url = "sqlite:///./test_predictive.db"
    if os.path.exists("./test_predictive.db"):
        try:
            os.remove("./test_predictive.db")
        except Exception:
            pass

    sync_engine = create_engine(db_url)
    Base.metadata.drop_all(bind=sync_engine)
    Base.metadata.create_all(bind=sync_engine)
    
    # Configure user auth override
    app.dependency_overrides[get_current_user] = lambda: {"id": "test-user-id", "email": "test@example.com", "role": "Admin"}
    
    yield
    sync_engine.dispose()
    app.dependency_overrides.clear()
    
    # Cleanup database file
    if os.path.exists("./test_predictive.db"):
        try:
            os.remove("./test_predictive.db")
        except Exception:
            pass

@pytest.fixture
def anyio_backend():
    return "asyncio"


@pytest.mark.anyio
async def test_automl_training_and_selection():
    # Setup mock dataset file and DB record
    csv_path = "./test_mock_data.csv"
    import pandas as pd
    import numpy as np
    
    # Generate simple clean dataframe
    np.random.seed(42)
    df = pd.DataFrame({
        "age": np.random.randint(18, 70, size=50),
        "tenure": np.random.randint(1, 60, size=50),
        "monthly_charges": np.random.rand(50) * 100,
        "churn": np.random.choice([0, 1], size=50)
    })
    df.to_csv(csv_path, index=False)
    
    async with AsyncSessionLocal() as session:
        ds = UserDataset(
            id="test-dataset-predictive-id",
            filename="test_mock_data.csv",
            table_name="test_mock_data",
            file_path=csv_path,
            row_count=50,
            col_count=4,
            columns=["age", "tenure", "monthly_charges", "churn"],
            user_id="test-user-id"
        )
        session.add(ds)
        await session.commit()
        await session.refresh(ds)

    # 1. Test opportunities discovery
    opp_res = await predictive_analytics_service.discover_prediction_opportunities("test-dataset-predictive-id")
    assert opp_res["dataset_id"] == "test-dataset-predictive-id"
    assert len(opp_res["opportunities"]) > 0

    # 2. Test AutoML training execution
    train_res = await predictive_analytics_service.train_automl_model(
        dataset_id="test-dataset-predictive-id",
        target="churn",
        task_type="classification",
        user_id="test-user-id"
    )
    
    assert train_res["task_type"] == "classification"
    assert "model_id" in train_res
    assert train_res["best_algorithm"] == "LogisticRegression"

    # 3. Test Predictions generation inference
    model_id = train_res["model_id"]
    pred_res = await predictive_analytics_service.generate_predictions(
        model_id=model_id,
        dataset_id="test-dataset-predictive-id"
    )
    assert pred_res["model_id"] == model_id
    assert pred_res["predictions_count"] == 50

    # Clean up temp file
    if os.path.exists(csv_path):
        os.remove(csv_path)


@pytest.mark.anyio
async def test_prescriptive_scenario_simulation():
    # Retrieve active trained model from registry
    async with AsyncSessionLocal() as session:
        models = (await session.execute(
            select(RegisteredModel).where(RegisteredModel.provider == "AutoML")
        )).scalars().all()
        assert len(models) > 0
        model_id = models[0].id

    # 1. Test what-if scenario prediction
    base = {"age": 35, "tenure": 12, "monthly_charges": 70.0}
    mods = {"monthly_charges": 50.0} # simulate discount
    
    sim_res = await prescriptive_service.simulate_scenario(
        model_id=model_id,
        base_features=base,
        modifications=mods
    )
    
    assert sim_res["predicted_probability"] is not None

    # 2. Test optimization recommendations ranking
    rules = {
        "monthly_charges": {"min": 40.0, "max": 90.0}
    }
    actions_res = await prescriptive_service.generate_prescriptive_actions(
        model_id=model_id,
        base_features=base,
        actionable_features=["monthly_charges"],
        business_rules=rules,
        target_direction="minimize"
    )
    
    assert "recommendations" in actions_res


@pytest.mark.anyio
async def test_workflow_nodes_integration():
    # Retrieve trained model
    async with AsyncSessionLocal() as session:
        model = (await session.execute(
            select(RegisteredModel).where(RegisteredModel.provider == "AutoML")
        )).scalars().first()
        model_id = model.id

    # Create dummy workflow execution data
    wf_def = {
        "nodes": [
            {
                "id": "train_node",
                "label": "AutoML Training",
                "type": "model_training",
                "config": {
                    "dataset_id": "test-dataset-predictive-id",
                    "target_variable": "churn",
                    "task_type": "classification"
                }
            },
            {
                "id": "pred_node",
                "label": "AutoML Prediction",
                "type": "prediction",
                "config": {
                    "model_id": model_id,
                    "dataset_id": "test-dataset-predictive-id"
                }
            }
        ],
        "edges": [
            {"source": "train_node", "target": "pred_node"}
        ]
    }

    async with AsyncSessionLocal() as session:
        wf = Workflow(
            name="Predictive pipeline flow",
            definition=json.dumps(wf_def),
            user_id="test-user-id"
        )
        session.add(wf)
        await session.commit()
        await session.refresh(wf)
        
        exec_record = WorkflowExecution(
            workflow_id=wf.id,
            status="pending",
            user_id="test-user-id"
        )
        session.add(exec_record)
        await session.commit()
        await session.refresh(exec_record)
        exec_id = exec_record.id

    # Trigger workflow execution
    from app.services.workflow_engine import WorkflowEngine
    engine = WorkflowEngine()
    
    # We patch _load_dataframe_blocking inside engine node to bypass actual CSV reads
    import pandas as pd
    import numpy as np
    mock_df = pd.DataFrame({
        "age": np.random.randint(18, 70, size=10),
        "tenure": np.random.randint(1, 60, size=10),
        "monthly_charges": np.random.rand(10) * 100,
        "churn": np.random.choice([0, 1], size=10)
    })
    
    with patch("app.services.predictive_analytics_service._load_dataframe_blocking", return_value=mock_df):
        await engine.execute_workflow(exec_id, "test-user-id")

    async with AsyncSessionLocal() as session:
        completed_exec = (await session.execute(
            select(WorkflowExecution).where(WorkflowExecution.id == exec_id)
        )).scalar_one()
        # Verify it executed successfully
        assert completed_exec.status == "completed"


def test_copilot_intents_routing():
    # Verify heuristics parsing
    res = copilot_service._detect_intent_heuristics("Predict customer churn probabilities")
    intents = [i["intent"] for i in res]
    assert "Predictive Analytics" in intents

    res2 = copilot_service._detect_intent_heuristics("recommend what-if scenarios rules")
    intents2 = [i["intent"] for i in res2]
    assert "Prescriptive Analytics" in intents2


def test_api_endpoints():
    # Test GET models
    response = client.get("/api/v1/predictive/models")
    assert response.status_code == 200
    assert isinstance(response.json(), list)

    # Test GET history
    response_hist = client.get("/api/v1/predictive/history")
    assert response_hist.status_code == 200
    assert isinstance(response_hist.json(), list)
