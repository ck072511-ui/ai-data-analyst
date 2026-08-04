import os
import sys
import json
import pytest
from unittest.mock import AsyncMock, patch, MagicMock
from fastapi.testclient import TestClient

# Adjust path to find backend
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

# Set environment variables for testing before importing main app
os.environ["DATABASE_URL"] = "sqlite:///./test_copilot.db"
os.environ["SECRET_KEY"] = "test-secret-key-must-be-long-enough-32-chars-at-least"
os.environ["ENVIRONMENT"] = "development"

from app.main import app
from app.core.database import Base, AsyncSessionLocal
from app.core.security import get_current_user
from app.services.copilot_service import copilot_service
from app.models.copilot import CopilotConversation, CopilotMessage
from app.models.workflow import Workflow

client = TestClient(app)

@pytest.fixture(scope="module", autouse=True)
def setup_database():
    from sqlalchemy import create_engine
    from app.core.database import engine

    db_url = str(engine.url)
    if db_url.startswith("postgresql+asyncpg://"):
        db_url = db_url.replace("postgresql+asyncpg://", "postgresql://")
    elif db_url.startswith("sqlite+aiosqlite://"):
        db_url = db_url.replace("sqlite+aiosqlite://", "sqlite://")

    sync_engine = create_engine(db_url)
    Base.metadata.create_all(bind=sync_engine)
    
    # Configure user auth bypass override
    app.dependency_overrides[get_current_user] = lambda: {"id": "test-user-id", "email": "test@example.com", "role": "Admin"}
    
    yield
    sync_engine.dispose()
    app.dependency_overrides.clear()

@pytest.fixture
def anyio_backend():
    return "asyncio"

def test_intent_routing_heuristics():
    # Test intent heuristic rule matches
    res1 = copilot_service._detect_intent_heuristics("Show total sales by region")
    intents1 = [i["intent"] for i in res1]
    assert "SQL Analytics" in intents1

    res2 = copilot_service._detect_intent_heuristics("clean my dataset and remove duplicate rows")
    intents2 = [i["intent"] for i in res2]
    assert "Data Cleaning" in intents2

    res3 = copilot_service._detect_intent_heuristics("profile the column patterns")
    intents3 = [i["intent"] for i in res3]
    assert "Dataset Analysis" in intents3

@pytest.mark.anyio
@patch("app.services.copilot_service.model_manager.generate", new_callable=AsyncMock)
async def test_intent_routing_with_llm(mock_llm):
    # Mock LLM intent detection returning JSON
    mock_llm.return_value = json.dumps([
        {"intent": "SQL Analytics", "confidence": 0.95},
        {"intent": "Report Generation", "confidence": 0.8}
    ])
    
    res = await copilot_service.detect_intent("Execute sales query and print report")
    intents = {i["intent"]: i["confidence"] for i in res}
    
    assert "SQL Analytics" in intents
    assert "Report Generation" in intents
    assert intents["SQL Analytics"] == 0.95

@pytest.mark.anyio
@patch("app.services.copilot_service.model_manager.generate", new_callable=AsyncMock)
async def test_action_orchestrator(mock_llm):
    mock_llm.return_value = "Synthesized Copilot response text."
    
    intents = [
        {"intent": "SQL Analytics", "confidence": 0.9},
        {"intent": "Explainability", "confidence": 0.8}
    ]
    
    # Run orchestrator
    res = await copilot_service.orchestrate_action(
        intents=intents,
        question="Query sales and explain the results",
        dataset_id=None,
        db_connection_id=None,
        user_id="test-user-id"
    )
    
    assert "answer" in res
    assert res["answer"] == "Synthesized Copilot response text."
    assert "tool_transparency" in res
    assert "SQL Analytics" in res["tool_transparency"]["selected_modules"]
    assert "Explainability" in res["tool_transparency"]["selected_modules"]

@pytest.mark.anyio
async def test_conversation_memory_db():
    # Insert conversation & message manually
    async with AsyncSessionLocal() as session:
        conv = CopilotConversation(
            user_id="test-user-id",
            title="Chat thread test"
        )
        session.add(conv)
        await session.commit()
        await session.refresh(conv)
        conv_id = conv.id
        
        user_msg = CopilotMessage(
            conversation_id=conv_id,
            role="user",
            content="Hello Copilot"
        )
        session.add(user_msg)
        await session.commit()
        
    # Verify retrieval via router client
    response = client.get("/api/v1/copilot/history")
    assert response.status_code == 200
    data = response.json()
    assert len(data) > 0
    
    test_convs = [c for c in data if c["id"] == conv_id]
    assert len(test_convs) == 1
    assert test_convs[0]["title"] == "Chat thread test"
    assert len(test_convs[0]["messages"]) == 1
    assert test_convs[0]["messages"][0]["content"] == "Hello Copilot"

@pytest.mark.anyio
async def test_workflow_generation_from_conversation():
    # Create thread with intents
    async with AsyncSessionLocal() as session:
        conv = CopilotConversation(
            user_id="test-user-id",
            title="Workflow gen thread"
        )
        session.add(conv)
        await session.commit()
        await session.refresh(conv)
        conv_id = conv.id
        
        msg1 = CopilotMessage(
            conversation_id=conv_id,
            role="user",
            content="clean dataset and run sql query",
            intent="Data Cleaning, SQL Analytics",
            intent_confidence=0.9
        )
        session.add(msg1)
        await session.commit()

    # Generate workflow via router endpoint
    response = client.post("/api/v1/copilot/workflow", json={
        "conversation_id": conv_id,
        "name": "Auto generated visual sequence",
        "description": "Triggered by Copilot conversation thread"
    })
    
    assert response.status_code == 200
    wf_data = response.json()
    assert wf_data["name"] == "Auto generated visual sequence"
    assert "definition" in wf_data
    
    # Assert DAG nodes structure contains start alert, cleaning, sql, and end alert
    node_types = [n["type"] for n in wf_data["definition"]["nodes"]]
    assert "notification" in node_types
    assert "data_cleaning" in node_types
    assert "sql_query" in node_types

@pytest.mark.anyio
@patch("app.services.copilot_service.model_manager.generate", new_callable=AsyncMock)
async def test_copilot_chat_endpoint(mock_llm):
    mock_llm.return_value = "Assistant text explanation."
    
    # Test POST /api/v1/copilot/chat
    response = client.post("/api/v1/copilot/chat", json={
        "message": "Summarize dataset sales",
        "conversation_id": None
    })
    
    assert response.status_code == 200
    data = response.json()
    assert "conversation_id" in data
    assert "answer" in data
    assert data["answer"] == "Assistant text explanation."
    assert "tool_transparency" in data
    assert "confidence_score" in data

@pytest.mark.anyio
@patch("app.services.copilot_service.model_manager.generate", new_callable=AsyncMock)
async def test_copilot_analyze_endpoint(mock_llm):
    mock_llm.return_value = "Analysis summary results details."
    
    # Test POST /api/v1/copilot/analyze
    response = client.post("/api/v1/copilot/analyze", json={
        "query": "explain query performance"
    })
    
    assert response.status_code == 200
    data = response.json()
    assert "answer" in data
    assert data["answer"] == "Analysis summary results details."
    assert "tool_transparency" in data
