from abc import ABC, abstractmethod
from typing import Dict, Any, List

class BasePlugin(ABC):
    """Base class for all plugins in the system."""

    @property
    @abstractmethod
    def metadata(self) -> Dict[str, Any]:
        """Returns metadata of the plugin.
        Expected keys: name, description, author, capability, compatible_versions
        """
        pass

    @property
    @abstractmethod
    def version(self) -> str:
        """Returns the version string (e.g., '1.0.0')."""
        pass

    @property
    def dependencies(self) -> List[str]:
        """Returns a list of other plugin names this plugin depends on."""
        return []

    @property
    def config_schema(self) -> Dict[str, Any]:
        """Returns JSON schema for the plugin's configuration options."""
        return {}

    @abstractmethod
    def validate_config(self, config: Dict[str, Any]) -> bool:
        """Validates configuration values. Raises ValueError on failure."""
        pass

    @abstractmethod
    async def health_check(self) -> Dict[str, Any]:
        """Performs diagnostics on the plugin.
        Returns:
            Dict containing 'status' ('healthy' or 'unhealthy') and 'details' dictionary.
        """
        return {"status": "healthy", "details": {}}


class DataSourcePlugin(BasePlugin):
    """Base interface for custom Data Source plugins (e.g., CSV Import Plus)."""

    @abstractmethod
    async def fetch_data(self, config: Dict[str, Any], params: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Fetch records from the data source.
        Returns:
            List of dictionaries representing database rows.
        """
        pass


class WorkflowNodePlugin(BasePlugin):
    """Base interface for custom Workflow nodes (e.g., Data Quality Rules)."""

    @abstractmethod
    async def execute(self, node_config: Dict[str, Any], context: Dict[str, Any], user_id: str) -> Dict[str, Any]:
        """Executes workflow node logic.
        Returns:
            Dictionary output from node execution.
        """
        pass


class AIToolPlugin(BasePlugin):
    """Base interface for AI Copilot custom tools (e.g., KPI Library)."""

    @abstractmethod
    async def run_tool(self, inputs: Dict[str, Any], user_id: str) -> Dict[str, Any]:
        """Executes AI capability.
        Returns:
            Dictionary output containing 'result', 'explanation', and other metrics.
        """
        pass


class ReportPlugin(BasePlugin):
    """Base interface for compiling custom templates/formats reports."""

    @abstractmethod
    async def generate_report(self, data: Dict[str, Any], config: Dict[str, Any]) -> Dict[str, Any]:
        """Compiles report document.
        Returns:
            Dictionary containing 'file_path', 'filename', and 'status'.
        """
        pass


class VisualizationPlugin(BasePlugin):
    """Base interface for custom chart configurations or renderings (e.g., Advanced Charts)."""

    @abstractmethod
    def generate_chart_spec(self, data: List[Dict[str, Any]], config: Dict[str, Any]) -> Dict[str, Any]:
        """Generates chart configuration specs for rendering on frontend.
        Returns:
            Dictionary of chart config specifications.
        """
        pass


class AnalyticsPlugin(BasePlugin):
    """Base interface for custom analytics algorithms (e.g., Forecast Helper)."""

    @abstractmethod
    async def run_analytics(self, data: List[Dict[str, Any]], config: Dict[str, Any]) -> Dict[str, Any]:
        """Runs analytic algorithms.
        Returns:
            Dictionary including 'result', 'metrics', and other outputs.
        """
        pass
