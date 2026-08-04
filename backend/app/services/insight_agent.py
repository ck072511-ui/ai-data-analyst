import json
import logging
from typing import Any, Dict
from app.services.model_manager import model_manager

logger = logging.getLogger(__name__)

class InsightAgent:
    async def execute_task(self, question: str, shared_memory: Dict[str, Any]) -> Dict[str, Any]:
        """Summarizes database execution records to extract trends, risk points and business tips."""
        logger.info("Insight Agent analyzing data points to extract analytical insights.")

        sql_output = shared_memory.get("SQLAgent", {})
        rows = sql_output.get("rows", [])
        columns = sql_output.get("columns", [])
        rag_output = shared_memory.get("RAGAgent", {})
        citations = rag_output.get("citations", [])

        # Format dataset summary
        dataset_summary = f"Columns: {columns}\nSample Rows count: {len(rows)}\n"
        if rows:
            dataset_summary += f"First sample row: {rows[0]}\n"

        citations_summary = "\n".join([c.get("text_content", "") for c in citations[:2]])

        prompt = (
            "You are an Expert Business Intelligence and Data Analytics Agent.\n"
            "Your task is to analyze SQL query results and document citations to extract clear business insights.\n\n"
            "=== ANALYSIS CONTEXT ===\n"
            f"User Question: {question}\n"
            f"SQL Results Summary:\n{dataset_summary}\n"
            f"Document Citations Summary:\n{citations_summary}\n\n"
            "You must output JSON only in the following schema:\n"
            "{\n"
            "  \"insights\": [\"Key data insight 1\", \"Key data insight 2\"],\n"
            "  \"trends\": [\"Identified data trend 1\", \"Identified data trend 2\"],\n"
            "  \"risks\": [\"Detected business risk 1\", \"Detected business risk 2\"],\n"
            "  \"opportunities\": [\"Spotted opportunity 1\", \"Spotted opportunity 2\"],\n"
            "  \"recommendations\": [\"Actionable recommendation 1\", \"Actionable recommendation 2\"]\n"
            "}\n"
            "Ensure the output contains nothing but valid JSON."
        )

        try:
            res = await model_manager.generate(prompt=prompt)
            clean_res = res.strip()
            if clean_res.startswith("```json"):
                clean_res = clean_res[7:]
            if clean_res.endswith("```"):
                clean_res = clean_res[:-3]
            clean_res = clean_res.strip()
            parsed = json.loads(clean_res)
            logger.info("Insight Agent successfully extracted insights.")
            return parsed
        except Exception as e:
            logger.warning(f"Insight Agent failed JSON extraction: {e}")
            return {
                "insights": ["Extracted database rows successfully."],
                "trends": ["Data output is constant or stable."],
                "risks": ["Potential lack of data volume to build trend calculations."],
                "opportunities": ["Leverage offline query models to parse raw reports."],
                "recommendations": ["Refine analytical queries to extract more sample columns."]
            }
        
import os
