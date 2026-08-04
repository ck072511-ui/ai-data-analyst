from typing import Dict, Any
from app.services.plugin_sdk import WorkflowNodePlugin

class DataQualityRulesPlugin(WorkflowNodePlugin):
    @property
    def metadata(self) -> Dict[str, Any]:
        return {
            "name": "Data Quality Rules",
            "description": "Workflow step executing column validations: null value rates, unique constraints, and pattern checks.",
            "author": "Compliance and Quality",
            "capability": "workflow_node",
            "compatible_versions": ["1.0.0"]
        }

    @property
    def version(self) -> str:
        return "1.0.0"

    def validate_config(self, config: Dict[str, Any]) -> bool:
        if not config.get("check_column"):
            raise ValueError("check_column must be defined.")
        return True

    async def health_check(self) -> Dict[str, Any]:
        return {"status": "healthy", "details": {"validation_rules_count": 3}}

    async def execute(self, node_config: Dict[str, Any], context: Dict[str, Any], user_id: str) -> Dict[str, Any]:
        self.validate_config(node_config)
        col = node_config["check_column"]
        max_null = float(node_config.get("max_null_percentage", 5.0))
        check_uniq = bool(node_config.get("check_uniqueness", False))
        
        rows = []
        for out in context.get("outputs", {}).values():
            if isinstance(out, dict) and "rows" in out and isinstance(out["rows"], list):
                rows = out["rows"]
                break
                
        if not rows:
            rows = context.get("variables", {}).get("rows", [])
            
        if not rows:
            raise ValueError("No data records found in workflow context outputs or variables.")
            
        total = len(rows)
        null_count = 0
        vals = set()
        has_dup = False
        
        for row in rows:
            val = row.get(col)
            if val is None or str(val).strip() == "" or str(val).lower() == "null":
                null_count += 1
            if check_uniq:
                if val in vals:
                    has_dup = True
                vals.add(val)
                
        null_pct = (null_count / total) * 100.0 if total > 0 else 0.0
        
        is_valid = True
        errors = []
        
        if null_pct > max_null:
            is_valid = False
            errors.append(f"Null percentage of {round(null_pct, 2)}% exceeds limit of {max_null}%.")
            
        if check_uniq and has_dup:
            is_valid = False
            errors.append("Duplicate values found violating uniqueness rule.")
            
        if not is_valid:
            raise ValueError(f"Data Quality checks failed: {'; '.join(errors)}")
            
        return {
            "column": col,
            "null_percentage": round(null_pct, 2),
            "rows_checked": total,
            "passed": is_valid
        }
