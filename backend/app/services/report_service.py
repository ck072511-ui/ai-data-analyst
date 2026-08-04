import os
import time
import logging
from datetime import datetime
from typing import Any, Dict, List
from sqlalchemy import select, desc

from app.core.database import AsyncSessionLocal
from app.models.report import GeneratedReport
from app.models.multi_agent import AgentExecution
from app.services.pdf_report_generator import PDFReportGenerator
from app.services.docx_report_generator import DOCXReportGenerator
from app.services.pptx_report_generator import PPTXReportGenerator
from app.services.monitoring_service import monitoring_service

logger = logging.getLogger(__name__)

class ReportService:
    def __init__(self):
        self.reports_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "data", "generated_documents"))
        os.makedirs(self.reports_dir, exist_ok=True)

    async def list_reports(self, user_id: str) -> List[Dict[str, Any]]:
        """Retrieves list of compiled report histories."""
        async with AsyncSessionLocal() as session:
            records = (await session.execute(
                select(GeneratedReport)
                .where(GeneratedReport.user_id == user_id)
                .order_by(desc(GeneratedReport.created_at))
            )).scalars().all()

            return [
                {
                    "id": r.id,
                    "title": r.title,
                    "report_type": r.report_type,
                    "file_format": r.file_format,
                    "status": r.status,
                    "created_at": r.created_at.isoformat(),
                    "error_message": r.error_message
                }
                for r in records
            ]

    async def get_report(self, report_id: str, user_id: str) -> Dict[str, Any]:
        """Inspects status details of a specific report query."""
        async with AsyncSessionLocal() as session:
            r = (await session.execute(
                select(GeneratedReport)
                .where(GeneratedReport.id == report_id, GeneratedReport.user_id == user_id)
            )).scalar_one_or_none()

            if not r:
                return {"error": "Report not found"}

            return {
                "id": r.id,
                "title": r.title,
                "report_type": r.report_type,
                "file_format": r.file_format,
                "status": r.status,
                "created_at": r.created_at.isoformat(),
                "error_message": r.error_message,
                "file_path": r.file_path
            }

    async def delete_report(self, report_id: str, user_id: str) -> Dict[str, Any]:
        """Deletes physical files and database entries."""
        async with AsyncSessionLocal() as session:
            r = (await session.execute(
                select(GeneratedReport)
                .where(GeneratedReport.id == report_id, GeneratedReport.user_id == user_id)
            )).scalar_one_or_none()

            if not r:
                return {"error": "Report not found"}

            if r.file_path and os.path.exists(r.file_path):
                try:
                    os.remove(r.file_path)
                except Exception as e:
                    logger.warning(f"Could not remove physical report file: {e}")

            await session.delete(r)
            await session.commit()
            return {"success": True, "message": "Report deleted successfully."}

    async def trigger_generation(
        self,
        execution_id: str,
        report_type: str,
        file_format: str,
        branding: Dict[str, Any],
        user_id: str
    ) -> Dict[str, Any]:
        """Pre-registers the report log as PENDING and returns the ID."""
        title = f"{report_type.replace('_', ' ').title()} Analysis Summary"
        
        async with AsyncSessionLocal() as session:
            report = GeneratedReport(
                user_id=user_id,
                execution_id=execution_id,
                title=title,
                report_type=report_type,
                file_format=file_format.lower(),
                branding=branding,
                status="pending"
            )
            session.add(report)
            await session.commit()
            await session.refresh(report)
            report_id = report.id

        return {
            "report_id": report_id,
            "title": title,
            "status": "pending"
        }

    async def execute_async_generation(self, report_id: str):
        """Asynchronously compiles PDF, DOCX, or PPTX assets."""
        start_time = time.time()
        
        async with AsyncSessionLocal() as session:
            r = (await session.execute(
                select(GeneratedReport).where(GeneratedReport.id == report_id)
            )).scalar_one_or_none()

            if not r:
                logger.error(f"Report ID {report_id} not found inside async generation scheduler.")
                return

            # Update to running
            r.status = "running"
            await session.commit()

            # Retrieve parent execution stats context
            exec_rec = None
            if r.execution_id:
                exec_rec = (await session.execute(
                    select(AgentExecution).where(AgentExecution.id == r.execution_id)
                )).scalar_one_or_none()

        if not exec_rec:
            logger.error(f"Execution record {r.execution_id} missing for report generation.")
            async with AsyncSessionLocal() as session:
                r_db = (await session.execute(select(GeneratedReport).where(GeneratedReport.id == report_id))).scalar_one()
                r_db.status = "failed"
                r_db.error_message = "Parent execution log metadata missing."
                await session.commit()
                monitoring_service.record_report_failure()
            return

        sm = exec_rec.shared_memory or {}
        
        # Compile data container
        data = {
            "title": r.title,
            "timestamp": datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S UTC"),
            "final_answer": exec_rec.final_answer,
            "sql": sm.get("SQLAgent", {}).get("sql", "No query executed."),
            "citations": sm.get("RAGAgent", {}).get("citations", []),
            "insights": sm.get("InsightAgent", {}).get("insights", []),
            "trends": sm.get("InsightAgent", {}).get("trends", []),
            "kpis": sm.get("VisualizationAgent", {}).get("kpis", [])
        }

        file_name = f"report_{r.id}.{r.file_format}"
        file_path = os.path.join(self.reports_dir, file_name)

        success = True
        err_msg = None

        try:
            if r.file_format == "pdf":
                PDFReportGenerator.generate(file_path, data, r.branding)
            elif r.file_format == "docx":
                DOCXReportGenerator.generate(file_path, data, r.branding)
            elif r.file_format == "pptx":
                PPTXReportGenerator.generate(file_path, data, r.branding)
            else:
                raise ValueError(f"Unsupported document layout configuration: {r.file_format}")

            # Check final size
            file_size = os.path.getsize(file_path) if os.path.exists(file_path) else 0
            
            # Record Prometheus metrics
            duration = time.time() - start_time
            monitoring_service.record_report_generation(r.file_format, duration, file_size)

        except Exception as e:
            logger.exception(f"Report compilation failed for ID {report_id}")
            success = False
            err_msg = str(e)
            monitoring_service.record_report_failure()

        # Update final state in DB
        async with AsyncSessionLocal() as session:
            r_db = (await session.execute(select(GeneratedReport).where(GeneratedReport.id == report_id))).scalar_one()
            if success:
                r_db.status = "completed"
                r_db.file_path = file_path
            else:
                r_db.status = "failed"
                r_db.error_message = err_msg
            await session.commit()
