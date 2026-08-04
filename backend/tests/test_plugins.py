import os
import sys
import json
import shutil
import pytest
from unittest.mock import AsyncMock, patch, MagicMock

# Adjust path to find backend
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

# Set environment variables for testing
os.environ["DATABASE_URL"] = "sqlite:///./test_analytics.db"
os.environ["SECRET_KEY"] = "test-secret-key-must-be-long-enough-32-chars-at-least"
os.environ["ENVIRONMENT"] = "development"

from app.services.plugin_sdk import BasePlugin, DataSourcePlugin, WorkflowNodePlugin
from app.services.plugin_registry import PluginRegistry
from app.services.plugin_manager import PluginManager, plugin_manager
from app.services.workflow_engine import WorkflowEngine
from app.services.copilot_service import CopilotService
from fastapi.testclient import TestClient
from app.main import app
from app.core.security import get_current_user

@pytest.fixture
def anyio_backend():
    return "asyncio"


# 1. SDK Interfaces test
def test_sdk_base_classes():
    class DummyDataSource(DataSourcePlugin):
        @property
        def metadata(self):
            return {"name": "Dummy", "capability": "data_source"}
        @property
        def version(self):
            return "1.0.0"
        def validate_config(self, config):
            return True
        async def health_check(self):
            return {"status": "healthy"}
        async def fetch_data(self, config, params):
            return [{"id": 1, "val": "test"}]

    plugin = DummyDataSource()
    assert plugin.version == "1.0.0"
    assert plugin.metadata["name"] == "Dummy"
    assert plugin.validate_config({}) is True


# 2. Registry test
def test_registry_operations(tmp_path):
    registry_file = tmp_path / "registry.json"
    registry = PluginRegistry(str(registry_file))
    
    # Verify initial blueprints
    available = registry.list_available()
    assert "csv_import_plus" in available
    assert "kpi_library" in available
    
    # Test installation registering
    meta = {"name": "Test Plugin", "version": "1.0.0"}
    registry.register_installed("test_plugin", meta, enabled=True)
    
    installed = registry.list_installed()
    assert "test_plugin" in installed
    assert installed["test_plugin"]["enabled"] is True
    
    # Test enable/disable toggling
    registry.set_enabled("test_plugin", False)
    installed = registry.list_installed()
    assert installed["test_plugin"]["enabled"] is False
    
    # Test health check updates
    registry.update_health("test_plugin", "healthy", "System checks pass")
    installed = registry.list_installed()
    assert installed["test_plugin"]["health_status"] == "healthy"
    
    # Test unregistering
    registry.unregister_installed("test_plugin")
    installed = registry.list_installed()
    assert "test_plugin" not in installed


# 3. Manager topological sort and dependency checking
def test_manager_dependency_resolution():
    manager = PluginManager()
    
    # Mock candidate dictionary
    candidates = {
        "kpi_library": {"metadata": {"name": "KPI", "dependencies": []}},
        "forecast_helper": {"metadata": {"name": "Forecast", "dependencies": ["kpi_library"]}}
    }
    
    resolved = manager._resolve_dependencies(candidates)
    assert resolved == ["kpi_library", "forecast_helper"]


# 4. Mock manager installation and execution
@pytest.mark.anyio
async def test_manager_install_and_lifecycle():
    manager = PluginManager()
    
    # Install CSV Import Plus from catalog
    plugin_id = "csv_import_plus"
    manager.uninstall_plugin(plugin_id) # ensure clean state
    
    assert plugin_id not in manager.loaded_plugins
    
    manager.install_plugin(plugin_id)
    assert plugin_id in manager.loaded_plugins
    
    # Test enable/disable state reloading
    manager.disable_plugin(plugin_id)
    assert plugin_id not in manager.loaded_plugins
    
    manager.enable_plugin(plugin_id)
    assert plugin_id in manager.loaded_plugins
    
    # Test config validations
    plugin = manager.loaded_plugins[plugin_id]
    with pytest.raises(ValueError):
        plugin.validate_config({"delimiter": "too_long_delim"})
        
    # Run health check
    health_results = await manager.run_health_checks()
    csv_health = next(h for h in health_results if h["plugin_id"] == plugin_id)
    assert csv_health["status"] == "healthy"
    
    # Clean up
    manager.uninstall_plugin(plugin_id)


# 5. Workflow integration validation test
@pytest.mark.anyio
async def test_workflow_node_integration():
    manager = plugin_manager
    manager.install_plugin("data_quality")
    
    # Setup workflow execution contexts
    node = {
        "id": "data_quality_1",
        "type": "data_quality",
        "config": {
            "check_column": "salary",
            "max_null_percentage": 50.0,
            "check_uniqueness": False
        }
    }
    
    context = {
        "node_states": {
            "data_quality_1": {
                "status": "pending",
                "logs": []
            }
        },
        "outputs": {
            "sql_query_1": {
                "rows": [
                    {"name": "Alice", "salary": 5000},
                    {"name": "Bob", "salary": 6000},
                    {"name": "Charlie", "salary": None}
                ]
            }
        },
        "variables": {}
    }
    
    # Run dynamic validator and execution in workflow engine mock
    engine = WorkflowEngine()
    
    # Test validation
    await engine._validate_node_inputs(node, context)
    
    # Execute node
    res = await engine._execute_node_logic(node, context, user_id="test_user")
    assert res["column"] == "salary"
    assert res["null_percentage"] == 33.33  # 1 null out of 3 rows
    assert res["passed"] is True
    
    # Let's adjust null percentage limit to verify exception triggers correctly
    node_fail = {
        "id": "data_quality_1",
        "type": "data_quality",
        "config": {
            "check_column": "salary",
            "max_null_percentage": 10.0, # should fail since 33.33% > 10%
            "check_uniqueness": False
        }
    }
    with pytest.raises(ValueError):
        await engine._execute_node_logic(node_fail, context, user_id="test_user")
        
    manager.uninstall_plugin("data_quality")


# 6. Copilot integration intent detection
@pytest.mark.anyio
async def test_copilot_plugin_integration():
    manager = plugin_manager
    manager.install_plugin("kpi_library")
    
    copilot = CopilotService()
    
    # Intent heuristics should recognize KPI Library mentions
    intents = copilot._detect_intent_heuristics("Compute Gross Margin ratio for dataset")
    assert any(i["intent"] == "Plugin: kpi_library" for i in intents)
    
    # Test action orchestration mocks execution
    with patch("app.services.model_manager.model_manager.generate", new_callable=AsyncMock) as mock_gen:
        mock_gen.return_value = "Orchestrated KPI Library calculations summary answer."
        
        res = await copilot.orchestrate_action(
            intents=[{"intent": "Plugin: kpi_library", "confidence": 0.9}],
            question="Calculate margins using kpi_library",
            dataset_id=None,
            db_connection_id=None,
            user_id="test_user"
        )
        assert res["answer"] == "Orchestrated KPI Library calculations summary answer."
        assert "plugin_kpi_library_results" in res["context"]
        
    manager.uninstall_plugin("kpi_library")


# 7. Endpoint routes HTTP integrations
def test_plugin_api_endpoints():
    client = TestClient(app)
    token_headers = {"Authorization": "Bearer dummy_token"}
    
    # Setup dependency overrides for auth and mock permissions
    app.dependency_overrides[get_current_user] = lambda: {"id": "admin_user", "email": "admin@example.com", "role": "Admin"}
    
    try:
        # GET /api/v1/plugins
        response = client.get("/api/v1/plugins", headers=token_headers)
        assert response.status_code == 200
        data = response.json()
        assert any(p["id"] == "csv_import_plus" for p in data)
        
        # POST /api/v1/plugins/install
        response = client.post("/api/v1/plugins/install", json={"plugin_id": "csv_import_plus"}, headers=token_headers)
        assert response.status_code == 200
        
        # GET /api/v1/plugins/health
        response = client.get("/api/v1/plugins/health", headers=token_headers)
        assert response.status_code == 200
        assert "overall_status" in response.json()
        
        # POST /api/v1/plugins/disable
        response = client.post("/api/v1/plugins/disable", json={"plugin_id": "csv_import_plus"}, headers=token_headers)
        assert response.status_code == 200
        
        # POST /api/v1/plugins/enable
        response = client.post("/api/v1/plugins/enable", json={"plugin_id": "csv_import_plus"}, headers=token_headers)
        assert response.status_code == 200
        
        # POST /api/v1/plugins/upgrade
        response = client.post("/api/v1/plugins/upgrade", json={"plugin_id": "csv_import_plus"}, headers=token_headers)
        assert response.status_code == 200
        
        # POST /api/v1/plugins/rollback
        response = client.post("/api/v1/plugins/rollback", json={"plugin_id": "csv_import_plus"}, headers=token_headers)
        assert response.status_code == 200
        
        # POST /api/v1/plugins/uninstall
        response = client.post("/api/v1/plugins/uninstall", json={"plugin_id": "csv_import_plus"}, headers=token_headers)
        assert response.status_code == 200
        
    finally:
        app.dependency_overrides.clear()
