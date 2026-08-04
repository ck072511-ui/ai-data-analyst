import logging
import time
from datetime import datetime
from typing import Any, Dict, List, Optional
from sqlalchemy import select, desc

from app.core.database import AsyncSessionLocal
from app.models.multi_agent import AgentExecution
from app.services.planner_agent import PlannerAgent
from app.services.schema_agent import SchemaAgent
from app.services.sql_agent import SQLAgent
from app.services.rag_agent import RAGAgent
from app.services.visualization_agent import VisualizationAgent
from app.services.insight_agent import InsightAgent
from app.services.critic_agent import CriticAgent
from app.services.monitoring_service import monitoring_service

logger = logging.getLogger(__name__)


class AgentManager:
    def __init__(self):
        self.planner = PlannerAgent()
        self.schema_agent = SchemaAgent()
        self.sql_agent = SQLAgent()
        self.rag_agent = RAGAgent()
        self.visualization_agent = VisualizationAgent()
        self.insight_agent = InsightAgent()
        self.critic_agent = CriticAgent()

    async def run_analytics_query(self, user_query: str, dataset_id: str, user_id: str) -> Dict[str, Any]:
        """Orchestrates collaborative task executions, managing Critic feedback loops and shared memories."""
        start_time = time.time()
        
        shared_memory: Dict[str, Any] = {}
        timeline: List[Dict[str, Any]] = []
        
        loop_cnt = 0
        max_loops = 2
        final_critic_report = {}
        plan_explanation = "Initial Planning"
        
        # 1. Main Planner loop
        while loop_cnt < max_loops:
            loop_cnt += 1
            logger.info(f"Multi-Agent execution loop {loop_cnt} starting for user question: {user_query}")
            
            # Step A: Run Planner Agent
            plan_start = time.time()
            plan_data = await self.planner.generate_plan(user_query)
            plan_latency = time.time() - plan_start
            
            plan_explanation = plan_data.get("reasoning", "Collaborative analytical sequence.")
            tasks = plan_data.get("tasks", [])
            
            # Step B: Run sequential tasks
            for task in tasks:
                agent_name = task.get("agent")
                desc_text = task.get("description", "")
                
                logger.info(f"Invoking {agent_name} for task: {desc_text}")
                agent_start = time.time()
                
                agent_output = {}
                success = True
                
                try:
                    if agent_name == "SchemaAgent":
                        agent_output = await self.schema_agent.execute_task(dataset_id, shared_memory)
                    elif agent_name == "RAGAgent":
                        agent_output = await self.rag_agent.execute_task(user_query, shared_memory)
                    elif agent_name == "SQLAgent":
                        agent_output = await self.sql_agent.execute_task(dataset_id, user_query, shared_memory)
                    elif agent_name == "VisualizationAgent":
                        agent_output = await self.visualization_agent.execute_task(shared_memory)
                    elif agent_name == "InsightAgent":
                        agent_output = await self.insight_agent.execute_task(user_query, shared_memory)
                    elif agent_name == "CriticAgent":
                        agent_output = await self.critic_agent.execute_task(user_query, shared_memory)
                        final_critic_report = agent_output
                    else:
                        logger.warning(f"Unknown agent type encountered: {agent_name}")
                        success = False
                except Exception as ex:
                    logger.exception(f"Exception during execution of agent {agent_name}")
                    agent_output = {"error": str(ex)}
                    success = False
                    
                agent_latency = time.time() - agent_start
                
                # Update metrics
                monitoring_service.record_agent_execution(agent_name, agent_latency, success)
                
                # Save output in shared context
                shared_memory[agent_name] = agent_output
                
                # Log step in execution timeline
                timeline.append({
                    "step_id": len(timeline) + 1,
                    "agent": agent_name,
                    "status": "completed" if success else "failed",
                    "duration_ms": int(agent_latency * 1000),
                    "description": desc_text
                })

            # Check Critic Audit
            if final_critic_report.get("needs_replanning") and loop_cnt < max_loops:
                logger.warning(f"Critic Agent rejected execution outputs. Reason: {final_critic_report.get('replanning_reason')}")
                monitoring_service.record_critic_reject()
                # Feed critique back to Planner for recovery
                user_query += f" (Note: Prior plan execution was rejected due to: {final_critic_report.get('replanning_reason')})"
                continue
            else:
                break

        duration_ms = int((time.time() - start_time) * 1000)
        status = "completed" if final_critic_report.get("is_valid", True) else "critic_rejected"
        
        # 2. Commit log record to DB
        async with AsyncSessionLocal() as session:
            exec_record = AgentExecution(
                user_id=user_id,
                prompt=user_query,
                execution_plan=tasks,
                timeline=timeline,
                shared_memory=shared_memory,
                final_answer=final_critic_report.get("final_synthesized_answer", "Analyzed dataset successfully."),
                confidence_score=final_critic_report.get("confidence", 0.8),
                duration_ms=duration_ms,
                status=status
            )
            session.add(exec_record)
            await session.commit()
            await session.refresh(exec_record)
            exec_id = exec_record.id

        return {
            "execution_id": exec_id,
            "reasoning": plan_explanation,
            "timeline": timeline,
            "final_answer": final_critic_report.get("final_synthesized_answer", "Analyzed dataset successfully."),
            "confidence_score": final_critic_report.get("confidence", 0.8),
            "sql": shared_memory.get("SQLAgent", {}).get("sql", ""),
            "citations": shared_memory.get("RAGAgent", {}).get("citations", []),
            "chart_type": shared_memory.get("VisualizationAgent", {}).get("chart_type"),
            "chart_data": shared_memory.get("VisualizationAgent", {}).get("chart_data"),
            "kpis": shared_memory.get("VisualizationAgent", {}).get("kpis", []),
            "insights": shared_memory.get("InsightAgent", {}).get("insights", []),
            "trends": shared_memory.get("InsightAgent", {}).get("trends", []),
            "duration_ms": duration_ms
        }

    async def list_history(self, user_id: str) -> List[Dict[str, Any]]:
        """Returns execution logs list."""
        async with AsyncSessionLocal() as session:
            records = (await session.execute(
                select(AgentExecution)
                .where(AgentExecution.user_id == user_id)
                .order_by(desc(AgentExecution.created_at))
            )).scalars().all()

            return [
                {
                    "id": r.id,
                    "prompt": r.prompt,
                    "final_answer": r.final_answer,
                    "confidence_score": r.confidence_score,
                    "status": r.status,
                    "duration_ms": r.duration_ms,
                    "created_at": r.created_at.isoformat()
                }
                for r in records
            ]

    async def get_execution_status(self, execution_id: str) -> Dict[str, Any]:
        """Inspects status of running/completed query steps."""
        async with AsyncSessionLocal() as session:
            rec = (await session.execute(
                select(AgentExecution).where(AgentExecution.id == execution_id)
            )).scalar_one_or_none()

            if not rec:
                return {"error": "Execution not found"}
            
            return {
                "id": rec.id,
                "status": rec.status,
                "timeline": rec.timeline,
                "confidence_score": rec.confidence_score,
                "duration_ms": rec.duration_ms
            }

    async def replay_execution(self, execution_id: str) -> Dict[str, Any]:
        """Loads and returns prior completed executions parameters directly."""
        async with AsyncSessionLocal() as session:
            rec = (await session.execute(
                select(AgentExecution).where(AgentExecution.id == execution_id)
            )).scalar_one_or_none()

            if not rec:
                return {"error": "Execution not found"}
            
            sm = rec.shared_memory or {}
            return {
                "execution_id": rec.id,
                "reasoning": "Replayed Execution Record",
                "timeline": rec.timeline,
                "final_answer": rec.final_answer,
                "confidence_score": rec.confidence_score,
                "sql": sm.get("SQLAgent", {}).get("sql", ""),
                "citations": sm.get("RAGAgent", {}).get("citations", []),
                "chart_type": sm.get("VisualizationAgent", {}).get("chart_type"),
                "chart_data": sm.get("VisualizationAgent", {}).get("chart_data"),
                "kpis": sm.get("VisualizationAgent", {}).get("kpis", []),
                "insights": sm.get("InsightAgent", {}).get("insights", []),
                "trends": sm.get("InsightAgent", {}).get("trends", []),
                "duration_ms": rec.duration_ms
            }
