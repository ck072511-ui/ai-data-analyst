import os
import sys
import pytest
from unittest.mock import AsyncMock, patch, MagicMock

# Adjust path to find backend
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

# Set environment variables for testing
os.environ["DATABASE_URL"] = "sqlite:///./test_analytics.db"
os.environ["SECRET_KEY"] = "test-secret-key-must-be-long-enough-32-chars-at-least"
os.environ["ENVIRONMENT"] = "development"

from app.services.planner_agent import PlannerAgent
from app.services.schema_agent import SchemaAgent
from app.services.sql_agent import SQLAgent
from app.services.critic_agent import CriticAgent
from app.services.agent_manager import AgentManager


@pytest.fixture
def anyio_backend():
    return "asyncio"


@pytest.mark.anyio
async def test_planner_agent_output(anyio_backend):
    planner = PlannerAgent()
    
    with patch("app.services.planner_agent.model_manager.generate", new_callable=AsyncMock) as mock_generate:
        mock_generate.return_value = """
        {
          "reasoning": "Standard inspect and query.",
          "tasks": [
            {"task_id": 1, "agent": "SchemaAgent", "description": "Inspect columns"},
            {"task_id": 2, "agent": "SQLAgent", "description": "Run query"}
          ]
        }
        """
        res = await planner.generate_plan("Show total sales per month")
        assert "tasks" in res
        assert len(res["tasks"]) == 2
        assert res["tasks"][0]["agent"] == "SchemaAgent"


@pytest.mark.anyio
async def test_sql_agent_task(anyio_backend):
    sql_agent = SQLAgent()
    shared_memory = {
        "SchemaAgent": {
            "schema_context": "Table Name: sales\nColumns: month, total",
            "table_name": "sales"
        }
    }
    
    with patch("app.services.sql_agent.model_manager.generate", new_callable=AsyncMock) as mock_generate, \
         patch("app.services.sql_agent.get_sync_engine") as mock_engine_func:
        
        mock_generate.return_value = "SELECT month, total FROM sales"
        
        # Mock engine connection and results
        mock_conn = MagicMock()
        mock_res = MagicMock()
        mock_res.keys.return_value = ["month", "total"]
        mock_res.fetchall.return_value = [["January", 150.0], ["February", 200.0]]
        mock_conn.execute.return_value = mock_res
        mock_engine_func.return_value.connect.return_value.__enter__.return_value = mock_conn

        res = await sql_agent.execute_task(
            dataset_id="dataset-uuid",
            question="Show monthly sales",
            shared_memory=shared_memory
        )

        assert "sql" in res
        assert res["sql"] == "SELECT month, total FROM sales"
        assert res["columns"] == ["month", "total"]
        assert len(res["rows"]) == 2


@pytest.mark.anyio
async def test_critic_agent_audit(anyio_backend):
    critic = CriticAgent()
    shared_memory = {
        "SchemaAgent": {"schema_context": "Table Name: sales"},
        "SQLAgent": {"sql": "SELECT month FROM sales", "rows": [["Jan"]], "row_count": 1},
        "InsightAgent": {"insights": ["Monthly sales are steady."]}
    }
    
    with patch("app.services.critic_agent.model_manager.generate", new_callable=AsyncMock) as mock_generate:
        mock_generate.return_value = """
        {
          "is_valid": true,
          "confidence": 0.92,
          "hallucinations": [],
          "inconsistencies": [],
          "needs_replanning": false,
          "replanning_reason": "",
          "final_synthesized_answer": "Checked monthly sales trends."
        }
        """
        res = await critic.execute_task("Show monthly sales", shared_memory)
        assert res["is_valid"] is True
        assert res["confidence"] == 0.92
        assert res["final_synthesized_answer"] == "Checked monthly sales trends."


@pytest.mark.anyio
async def test_orchestrated_agent_manager_workflow(anyio_backend):
    manager = AgentManager()
    
    mock_plan = {
        "reasoning": "Sequential run",
        "tasks": [
            {"task_id": 1, "agent": "SchemaAgent", "description": "Inspect structure"},
            {"task_id": 2, "agent": "CriticAgent", "description": "Synthesize answer"}
        ]
    }
    
    mock_critic_res = {
        "is_valid": True,
        "confidence": 0.95,
        "needs_replanning": False,
        "final_synthesized_answer": "Collaboration output complete."
    }

    with patch("app.services.agent_manager.AsyncSessionLocal") as mock_session_class, \
         patch.object(manager.planner, "generate_plan", new_callable=AsyncMock) as mock_gen_plan, \
         patch.object(manager.schema_agent, "execute_task", new_callable=AsyncMock) as mock_schema_task, \
         patch.object(manager.critic_agent, "execute_task", new_callable=AsyncMock) as mock_critic_task:
        
        mock_gen_plan.return_value = mock_plan
        mock_schema_task.return_value = {"table_name": "sales"}
        mock_critic_task.return_value = mock_critic_res
        
        mock_session = AsyncMock()
        mock_session_class.return_value.__aenter__.return_value = mock_session

        res = await manager.run_analytics_query(
            user_query="Inspect database tables layout details",
            dataset_id="dataset-uuid",
            user_id="user-uuid"
        )

        assert "execution_id" in res
        assert res["final_answer"] == "Collaboration output complete."
        assert res["confidence_score"] == 0.95
        assert len(res["timeline"]) == 2
