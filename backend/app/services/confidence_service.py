import logging
from typing import Any, Dict, Tuple

logger = logging.getLogger(__name__)

class ConfidenceService:
    @staticmethod
    def calculate_confidence(shared_memory: Dict[str, Any], timeline: list) -> Tuple[float, str]:
        """Calculates final confidence score (0-100) and maps to level tags."""
        sql_out = shared_memory.get("SQLAgent", {})
        rag_out = shared_memory.get("RAGAgent", {})
        schema_out = shared_memory.get("SchemaAgent", {})

        # 1. SQL Success (25%)
        sql_score = 0.0
        if sql_out.get("sql") and not sql_out.get("error"):
            sql_score = 100.0

        # 2. Schema Match Quality (20%)
        schema_score = 0.0
        if schema_out.get("schema_context"):
            schema_score = 100.0

        # 3. Citation Coverage & Quality (20%)
        citation_score = 0.0
        citations = rag_out.get("citations", [])
        if citations:
            citation_score = 95.0
        elif rag_out.get("dictionary_context"):
            # glossary match
            citation_score = 80.0

        # 4. Agent Agreement / Timeline Success (20%)
        agent_score = 0.0
        if timeline:
            success_steps = sum(1 for s in timeline if s.get("status") == "completed")
            agent_score = (success_steps / len(timeline)) * 100.0

        # 5. Data Completeness (15%)
        data_score = 0.0
        if sql_out.get("rows"):
            data_score = 100.0
        elif sql_out.get("sql") and not sql_out.get("error"):
            # query completed successfully but returned 0 rows
            data_score = 50.0

        # Weighted calculation
        overall_score = (
            (0.25 * sql_score) +
            (0.20 * schema_score) +
            (0.20 * citation_score) +
            (0.20 * agent_score) +
            (0.15 * data_score)
        )
        
        overall_score = max(0.0, min(100.0, overall_score))

        # Classify Level
        if overall_score >= 80.0:
            level = "High"
        elif overall_score >= 50.0:
            level = "Medium"
        else:
            level = "Low"

        logger.info(f"Confidence score computed: {overall_score} ({level})")
        return round(overall_score, 1), level
