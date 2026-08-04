# Developer Guide: Building Custom Offline Plugins

This guide explains how to construct, package, and deploy a custom extension plugin for the AI Data Analyst platform.

## Plugin Anatomy
A plugin consists of a single directory containing two files:
1. `metadata.json`: Declares name, version, author, dependencies, capability, and validation configuration schemas.
2. `main.py`: Contains the python class implementing one of the SDK capability interfaces.

---

## Step 1: Create `metadata.json`
Define the unique ID and capability mappings. Example for a visual outlier detector:

```json
{
  "name": "Outlier Isolation Detector",
  "description": "Uses isolation forests to locate multi-dimensional anomalies in dataset variables.",
  "version": "1.0.0",
  "author": "Data Security Lab",
  "capability": "analytics",
  "dependencies": ["kpi_library"],
  "config_schema": {
    "type": "object",
    "properties": {
      "contamination": {
        "type": "number",
        "default": 0.05,
        "description": "Proportion of outliers in the dataset"
      },
      "n_estimators": {
        "type": "integer",
        "default": 100,
        "description": "Number of trees in the forest"
      }
    },
    "required": ["contamination"]
  }
}
```

---

## Step 2: Implement Class in `main.py`
Inherit from the capability base class and override all abstract properties and methods:

```python
from typing import Dict, Any
from app.services.plugin_sdk import AnalyticsPlugin

class OutlierIsolationPlugin(AnalyticsPlugin):
    @property
    def metadata(self) -> Dict[str, Any]:
        return {
            "name": "Outlier Isolation Detector",
            "capability": "analytics"
        }
        
    @property
    def version(self) -> str:
        return "1.0.0"

    def validate_config(self, config: Dict[str, Any]) -> bool:
        contamination = config.get("contamination", 0.05)
        if not (0.0 < contamination <= 0.5):
            raise ValueError("Contamination must be between 0.0 and 0.5")
        return True

    async def health_check(self) -> Dict[str, Any]:
        try:
            import sklearn
            return {"status": "healthy", "details": {"scikit_version": sklearn.__version__}}
        except ImportError:
            return {"status": "unhealthy", "details": {"error": "scikit-learn is missing"}}

    async def run_analytics(self, data: Dict[str, Any], config: Dict[str, Any]) -> Dict[str, Any]:
        self.validate_config(config)
        # Custom logic goes here
        return {
            "outliers_found": 3,
            "indices": [12, 45, 98],
            "algorithm": "IsolationForest"
        }
```

---

## Step 3: Deploy Locally
1. Place the folder under `backend/app/plugins_store/marketplace/your_plugin_name/`.
2. Start the application. The plugin will be detected on start and made available for installation in the Marketplace UI view.
