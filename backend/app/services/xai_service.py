import logging
import re
from typing import Any, Dict, List

logger = logging.getLogger(__name__)

class XAIService:
    @staticmethod
    def parse_sql_explanation(sql: str) -> Dict[str, Any]:
        """Programmatically analyzes SQL queries to formulate user explanations."""
        if not sql:
            return {
                "why_generated": "No database query was initiated.",
                "tables": [],
                "columns": [],
                "filters": [],
                "joins": [],
                "complexity": "None"
            }

        # Programmatic analysis
        tables = re.findall(r"\bfrom\s+([a-zA-Z0-9_]+)", sql.lower())
        joins = re.findall(r"\bjoin\s+([a-zA-Z0-9_]+)", sql.lower())
        all_tables = list(set(tables + joins))

        # Check for joins explanation
        join_explanations = []
        for j in joins:
            join_explanations.append(f"Linked data from table '{j}' using a join relation.")

        # Complexity
        complexity = "Low"
        if len(joins) > 1:
            complexity = "High"
        elif len(joins) == 1:
            complexity = "Medium"

        # Check columns
        select_match = re.search(r"select\s+(.+?)\s+from", sql.lower(), re.DOTALL)
        columns = []
        if select_match:
            cols_raw = select_match.group(1).split(",")
            columns = [c.strip().split(" as ")[-1] for c in cols_raw]

        # Filters
        where_match = re.search(r"where\s+(.+?)(?:group|order|limit|$)", sql.lower(), re.DOTALL)
        filters = []
        if where_match:
            filters.append(where_match.group(1).strip())

        return {
            "why_generated": f"Extracted metrics from dataset table '{all_tables[0] if all_tables else 'dataset'}' to answer the user's prompt.",
            "tables": all_tables,
            "columns": columns,
            "filters": filters,
            "joins": join_explanations,
            "complexity": complexity
        }

    @staticmethod
    def parse_rag_explanation(citations: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Aggregates citations similarity scores and issues missing evidence warnings."""
        if not citations:
            return {
                "cited_sources_count": 0,
                "warning": "Uncertainty warning: No offline manual documents or business glossaries were cited for this answer.",
                "chunks_selected_reason": "No document segments matched query parameters."
            }

        filenames = list(set([c.get("filename") for c in citations if c.get("filename")]))
        return {
            "cited_sources_count": len(citations),
            "unique_documents": filenames,
            "warning": None,
            "chunks_selected_reason": "Selected high-similarity context passages matching user's query keywords."
        }

    @staticmethod
    def parse_agent_explanation(timeline: List[Dict[str, Any]], critic_memory: Dict[str, Any]) -> Dict[str, Any]:
        """Summarizes multi-agent planning details and Critic outputs."""
        planner_decisions = []
        for step in timeline:
            planner_decisions.append(f"Delegated task '{step.get('description')}' to agent {step.get('agent')}.")

        return {
            "planner_decisions": planner_decisions,
            "critic_validation_summary": "Passed Critic validation check. No discrepancies flagged." if critic_memory.get("is_valid", True) else "Critic flagged potential discrepancies requiring recovery.",
            "re_planning_events_count": sum(1 for step in timeline if "replanning" in step.get("description", "").lower())
        }

    @staticmethod
    def parse_business_explanation(insight_memory: Dict[str, Any]) -> Dict[str, Any]:
        """Structures business opportunities and risks."""
        return {
            "statistical_basis": "Database query statistics and citations records.",
            "risks": insight_memory.get("risks", ["Potential data volume thresholds."]),
            "recommendations": insight_memory.get("recommendations", ["Review queries."])
        }
