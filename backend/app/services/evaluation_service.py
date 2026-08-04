import time
import logging
import random
from typing import Any, Dict, List
from sqlalchemy import select, desc
from app.core.database import AsyncSessionLocal
from app.models.prompt_registry import EvaluationRecord, PromptTemplate
from app.services.model_manager import model_manager
from app.services.monitoring_service import monitoring_service

logger = logging.getLogger(__name__)

class EvaluationService:
    @staticmethod
    def run_metrics_score(
        sql: str,
        citations: List[Any],
        latency_ms: int,
        answer: str
    ) -> Dict[str, float]:
        """Runs a deterministic offline metrics scoring check on outputs."""
        # 1. Answer Relevance (30%)
        relevance = 90.0 if len(answer) > 50 else 50.0

        # 2. SQL Correctness (30%)
        sql_score = 100.0 if sql and "select" in sql.lower() else 0.0

        # 3. Citation Coverage (20%)
        citation_score = 100.0 if citations else 0.0

        # 4. Latency Penalty (20%)
        # Cap score. Under 3s = 100.0, linear decrease to 0 at 10s.
        latency_score = 100.0
        if latency_ms > 3000:
            latency_score = max(0.0, 100.0 - ((latency_ms - 3000) / 70.0))

        overall = (
            (0.3 * relevance) +
            (0.3 * sql_score) +
            (0.2 * citation_score) +
            (0.2 * latency_score)
        )

        return {
            "answer_relevance": relevance,
            "sql_correctness": sql_score,
            "citation_coverage": citation_score,
            "overall_score": round(overall, 1)
        }

    async def list_history(self) -> List[Dict[str, Any]]:
        """Retrieves list of benchmark histories."""
        async with AsyncSessionLocal() as session:
            records = (await session.execute(
                select(EvaluationRecord)
                .order_by(desc(EvaluationRecord.created_at))
            )).scalars().all()

            return [
                {
                    "id": r.id,
                    "prompt_id": r.prompt_id,
                    "model_name": r.model_name,
                    "answer_relevance": r.answer_relevance,
                    "sql_correctness": r.sql_correctness,
                    "citation_coverage": r.citation_coverage,
                    "overall_score": r.overall_score,
                    "execution_latency_ms": r.execution_latency_ms,
                    "created_at": r.created_at.isoformat()
                }
                for r in records
            ]

    async def run_evaluation(self, prompt_id: str, model_name: str) -> Dict[str, Any]:
        """Runs a localized offline model execution and rates output parameters."""
        start_time = time.time()
        
        async with AsyncSessionLocal() as session:
            p = (await session.execute(
                select(PromptTemplate).where(PromptTemplate.id == prompt_id)
            )).scalar_one_or_none()

        if not p:
            return {"error": "Prompt template not found"}

        # Simulate execution on selected active local model
        prompt_text = f"You are running evaluation on model '{model_name}'. Answer this prompt:\n{p.content}"
        
        try:
            res = await model_manager.generate(prompt=prompt_text)
            latency_ms = int((time.time() - start_time) * 1000)

            # Simulated schema context attributes for scoring
            sql = "SELECT id FROM users" if "sql" in p.category.lower() else ""
            citations = [{"filename": "grounding.txt"}] if "rag" in p.category.lower() else []

            scores = self.run_metrics_score(sql, citations, latency_ms, res)
            
            # Save evaluation logs
            async with AsyncSessionLocal() as session:
                record = EvaluationRecord(
                    prompt_id=p.id,
                    model_name=model_name,
                    answer_relevance=scores["answer_relevance"],
                    sql_correctness=scores["sql_correctness"],
                    citation_coverage=scores["citation_coverage"],
                    overall_score=scores["overall_score"],
                    execution_latency_ms=latency_ms
                )
                session.add(record)
                await session.commit()
                await session.refresh(record)
                eval_id = record.id

            # Update Prometheus latency & score benchmarks
            monitoring_service.record_evaluation_run(
                duration_sec=(latency_ms / 1000.0),
                score=scores["overall_score"]
            )

            return {
                "evaluation_id": eval_id,
                "model_name": model_name,
                "answer": res,
                "sql": sql,
                "citations": citations,
                "latency_ms": latency_ms,
                "scores": scores
            }

        except Exception as e:
            logger.exception(f"Evaluation model generation failed: {e}")
            return {"error": f"Evaluation runner failed: {e}"}

    async def run_ab_comparison(self, prompt_id: str, model_a: str, model_b: str) -> Dict[str, Any]:
        """Runs side-by-side A/B comparisons of same prompt on two different local models."""
        logger.info(f"Triggering A/B model compare for models {model_a} vs {model_b}")
        
        res_a = await self.run_evaluation(prompt_id, model_a)
        res_b = await self.run_evaluation(prompt_id, model_b)

        return {
            "model_a": res_a,
            "model_b": res_b
        }
