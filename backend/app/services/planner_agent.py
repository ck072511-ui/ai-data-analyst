import json
import logging
from typing import Any, Dict, List
from app.services.model_manager import model_manager

logger = logging.getLogger(__name__)

class PlannerAgent:
    def __init__(self):
        self.system_prompt = (
            "You are a Staff Coordinator and Planner Agent.\n"
            "Your task is to break down a user's database analytical request into a sequential plan of agent tasks.\n"
            "The available agents you can delegate to are:\n"
            "- SchemaAgent: Inspects database layout and retrieves relations.\n"
            "- RAGAgent: Retrieves business glossary definitions or documents.\n"
            "- SQLAgent: Translates question to SQL and executes it.\n"
            "- VisualizationAgent: Suggests chart templates and dashboards.\n"
            "- InsightAgent: Evaluates data outputs to write business summaries.\n"
            "- CriticAgent: Double-checks results for hallucinations and inconsistencies.\n\n"
            "You must output JSON only in the following schema:\n"
            "{\n"
            "  \"reasoning\": \"Explanation of why this sequence is chosen.\",\n"
            "  \"tasks\": [\n"
            "    {\n"
            "      \"task_id\": 1,\n"
            "      \"agent\": \"SchemaAgent|RAGAgent|SQLAgent|VisualizationAgent|InsightAgent|CriticAgent\",\n"
            "      \"description\": \"Details of what this agent must do.\"\n"
            "    }\n"
            "  ]\n"
            "}\n"
            "Ensure the output contains nothing but valid JSON."
        )

    async def generate_plan(self, user_query: str) -> Dict[str, Any]:
        """Generates an orchestration plan for the agent manager loop."""
        
        kg_plan_context = ""
        try:
            import json
            from app.services.semantic_layer_service import semantic_layer_service
            from app.models.knowledge import KnowledgeEntity, KnowledgeRelationship
            from app.core.database import AsyncSessionLocal
            from sqlalchemy import select
            
            words = user_query.lower().split()
            resolved = []
            for w in words:
                w_clean = "".join(c for c in w if c.isalnum())
                if w_clean:
                    syns = semantic_layer_service.resolve_synonyms(w_clean)
                    if syns:
                        resolved.extend(syns)
                    resolved.append(w_clean)
            
            if resolved:
                async with AsyncSessionLocal() as session:
                    entities = (await session.execute(
                        select(KnowledgeEntity).where(KnowledgeEntity.name.in_(resolved))
                    )).scalars().all()
                    
                    kg_lines = []
                    for ent in entities:
                        kg_lines.append(f"- Entity '{ent.name}' is a {ent.entity_type}.")
                        rels = (await session.execute(
                            select(KnowledgeRelationship)
                            .where((KnowledgeRelationship.source_id == ent.id) | (KnowledgeRelationship.target_id == ent.id))
                            .limit(2)
                        )).scalars().all()
                        for r in rels:
                            other_id = r.target_id if r.source_id == ent.id else r.source_id
                            other = (await session.execute(
                                select(KnowledgeEntity).where(KnowledgeEntity.id == other_id)
                            )).scalar_one_or_none()
                            if other:
                                kg_lines.append(f"  * Rel: {ent.name} -> {other.name} ({r.relationship_type})")
                    if kg_lines:
                        kg_plan_context = "=== KNOWLEDGE GRAPH GUIDANCE ===\n" + "\n".join(kg_lines) + "\n\n"
        except Exception as e:
            logger.error(f"Failed to load KG plan context: {e}")

        prompt = f"{self.system_prompt}\n\n{kg_plan_context}=== User Query ===\n{user_query}\n\nPlan JSON:"
        
        try:
            res = await model_manager.generate(prompt=prompt)
            clean_res = res.strip()
            if clean_res.startswith("```json"):
                clean_res = clean_res[7:]
            if clean_res.endswith("```"):
                clean_res = clean_res[:-3]
            clean_res = clean_res.strip()
            parsed = json.loads(clean_res)
            logger.info("Planner Agent successfully generated plan.")
            return parsed
        except Exception as e:
            logger.warning(f"Planner Agent JSON parsing or generation failure: {e}. Falling back to default pipeline.")
            # Default pipeline fallback
            return {
                "reasoning": "Fallback default analytical sequence.",
                "tasks": [
                    {"task_id": 1, "agent": "SchemaAgent", "description": "Extract database columns schema layout context."},
                    {"task_id": 2, "agent": "RAGAgent", "description": "Verify business glossary definition files."},
                    {"task_id": 3, "agent": "SQLAgent", "description": "Generate and execute SQL matching query."},
                    {"task_id": 4, "agent": "VisualizationAgent", "description": "Determine chart templates for dataset."},
                    {"task_id": 5, "agent": "InsightAgent", "description": "Summarize result table and compute trend lines."},
                    {"task_id": 6, "agent": "CriticAgent", "description": "Audit the compiled final response for validity."}
                ]
            }
