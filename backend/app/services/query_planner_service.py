import json
import logging
from typing import Any, Dict, List, Optional
from app.services.model_manager import model_manager

logger = logging.getLogger(__name__)

class QueryPlannerService:
    def __init__(self):
        self.system_prompt = (
            "You are a Distributed Multi-Database Query Planner.\n"
            "Given the Target Database Catalogs (which contain multiple separate connection engines) and the user's question, "
            "determine which databases hold the required tables, write clean and valid SQL subqueries for each target database connection, "
            "and describe how to combine the results in-memory (join or union).\n\n"
            "=== EXPECTED OUTPUT JSON SCHEMA ===\n"
            "{\n"
            "  \"subqueries\": [\n"
            "    {\n"
            "      \"db_connection_id\": \"target-connection-uuid\",\n"
            "      \"sql\": \"SELECT column1, column2 FROM table_name\",\n"
            "      \"alias\": \"t1\"\n"
            "    }\n"
            "  ],\n"
            "  \"merge_operations\": {\n"
            "    \"type\": \"join|union|union_all|single\",\n"
            "    \"join_type\": \"inner|left\",\n"
            "    \"left_table\": \"t1\",\n"
            "    \"right_table\": \"t2\",\n"
            "    \"left_on\": \"column_name_in_left\",\n"
            "    \"right_on\": \"column_name_in_right\",\n"
            "    \"projection\": [\"column1\", \"column2\"]\n"
            "  }\n"
            "}\n"
            "Ensure the output contains nothing but valid JSON. Do not include markdown code blocks around the JSON."
        )

    async def plan_query(self, question: str, catalog: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Formulates an execution plan mapping subqueries to database connections and planning in-memory merges."""
        catalog_str = json.dumps(catalog, indent=2)
        
        prompt = (
            f"{self.system_prompt}\n\n"
            f"=== TARGET UNIFIED CATALOG ===\n{catalog_str}\n\n"
            f"=== USER QUESTION ===\n{question}\n\n"
            f"Plan JSON:"
        )

        try:
            res = await model_manager.generate(prompt=prompt)
            clean_res = res.strip()
            if clean_res.startswith("```json"):
                clean_res = clean_res[7:]
            if clean_res.endswith("```"):
                clean_res = clean_res[:-3]
            clean_res = clean_res.strip()
            
            plan = json.loads(clean_res)
            logger.info("Distributed Query Planner successfully generated execution plan.")
            return plan
        except Exception as e:
            logger.warning(f"Distributed Query Planner JSON parsing or generation failure: {e}. Falling back to default plan.")
            
            # Simple rule-based fallback planner
            # Find any tables matching words in the question
            words = question.lower().split()
            matched_tables = []
            for item in catalog:
                tb_name = item["table_name"].lower()
                if tb_name in question.lower() or any(w in tb_name for w in words):
                    matched_tables.append(item)

            if len(matched_tables) >= 2:
                # Mock a join plan for first two matching tables
                t1 = matched_tables[0]
                t2 = matched_tables[1]
                return {
                    "subqueries": [
                        {
                            "db_connection_id": t1["connection_id"],
                            "sql": f"SELECT * FROM {t1['table_name']}",
                            "alias": "t1"
                        },
                        {
                            "db_connection_id": t2["connection_id"],
                            "sql": f"SELECT * FROM {t2['table_name']}",
                            "alias": "t2"
                        }
                    ],
                    "merge_operations": {
                        "type": "join",
                        "join_type": "inner",
                        "left_table": "t1",
                        "right_table": "t2",
                        "left_on": t1["columns"][0]["name"] if t1["columns"] else "id",
                        "right_on": t2["columns"][0]["name"] if t2["columns"] else "id",
                        "projection": []
                    }
                }
            elif len(matched_tables) == 1:
                t = matched_tables[0]
                return {
                    "subqueries": [
                        {
                            "db_connection_id": t["connection_id"],
                            "sql": f"SELECT * FROM {t['table_name']}",
                            "alias": "t1"
                        }
                    ],
                    "merge_operations": {
                        "type": "single",
                        "left_table": "t1"
                    }
                }
            else:
                raise ValueError("No database tables matched user question.")

query_planner_service = QueryPlannerService()
