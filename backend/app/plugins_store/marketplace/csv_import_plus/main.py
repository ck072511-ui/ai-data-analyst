import os
import csv
from typing import Dict, Any, List
from app.services.plugin_sdk import DataSourcePlugin

class CSVImportPlusPlugin(DataSourcePlugin):
    @property
    def metadata(self) -> Dict[str, Any]:
        return {
            "name": "CSV Import Plus",
            "description": "Enhanced CSV parsing data source with customizable delimiters, character encoding selectors, and header sanitizers.",
            "author": "Platform Team",
            "capability": "data_source",
            "compatible_versions": ["1.0.0"]
        }

    @property
    def version(self) -> str:
        return "1.0.0"

    def validate_config(self, config: Dict[str, Any]) -> bool:
        delim = config.get("delimiter", ",")
        if len(delim) != 1:
            raise ValueError("Delimiter must be a single character.")
        return True

    async def health_check(self) -> Dict[str, Any]:
        return {"status": "healthy", "details": {"delimiter_validated": True}}

    async def fetch_data(self, config: Dict[str, Any], params: Dict[str, Any]) -> List[Dict[str, Any]]:
        self.validate_config(config)
        filepath = params.get("file_path")
        if not filepath or not os.path.exists(filepath):
            raise ValueError(f"File path '{filepath}' does not exist.")
        
        delim = config.get("delimiter", ",")
        encoding = config.get("encoding", "utf-8")
        skip_rows = int(config.get("skip_rows", 0))
        
        rows = []
        with open(filepath, 'r', encoding=encoding) as f:
            for _ in range(skip_rows):
                next(f, None)
            reader = csv.DictReader(f, delimiter=delim)
            for row in reader:
                rows.append(dict(row))
        return rows
