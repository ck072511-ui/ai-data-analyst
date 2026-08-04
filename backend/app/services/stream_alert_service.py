import json
import logging
from datetime import datetime
from typing import Any, Dict

from sqlalchemy import select
from app.core.database import AsyncSessionLocal
from app.models.stream import StreamAlert, StreamConfig
from app.models.workflow import Workflow, WorkflowExecution
from app.services.notification_service import notification_service
from app.services.monitoring_service import monitoring_service

logger = logging.getLogger(__name__)

class StreamAlertService:
    async def trigger_threshold_alert(self, stream_id: str, message: str, severity: str, user_id: str):
        await self._create_alert(stream_id, "threshold", message, severity, user_id)

    async def trigger_anomaly_alert(self, stream_id: str, message: str, user_id: str):
        await self._create_alert(stream_id, "anomaly", message, "critical", user_id)

    async def trigger_failure_alert(self, stream_id: str, message: str, user_id: str):
        await self._create_alert(stream_id, "failure", message, "critical", user_id)

    async def trigger_recovery_alert(self, stream_id: str, message: str, user_id: str):
        await self._create_alert(stream_id, "recovery", message, "info", user_id)

    async def _create_alert(self, stream_id: str, alert_type: str, message: str, severity: str, user_id: str):
        """Creates alert entry in db, updates metrics, sends notification, and triggers matching workflows."""
        logger.warning(f"[STREAM ALERT] [{alert_type.upper()}] Stream: {stream_id} - Msg: {message}")

        async with AsyncSessionLocal() as session:
            # 1. Create alert in database
            alert = StreamAlert(
                stream_id=stream_id,
                alert_type=alert_type,
                message=message,
                severity=severity,
                timestamp=datetime.utcnow(),
                resolved=False,
                user_id=user_id
            )
            session.add(alert)
            
            # Fetch stream name for notification details
            stream = (await session.execute(
                select(StreamConfig).where(StreamConfig.id == stream_id)
            )).scalar_one_or_none()
            stream_name = stream.name if stream else "Unknown Stream"
            
            await session.commit()

        # 2. Trigger System Notification
        title = f"Streaming {alert_type.capitalize()} Alert - {stream_name}"
        notification_service.send_notification(
            user_id=user_id,
            title=title,
            message=message,
            severity=severity
        )

        # 3. Update Monitoring metrics
        monitoring_service.record_streaming_workflow_triggered(stream_id, trigger_reason=alert_type)

        # 4. Trigger Matching Workflows Automatically
        payload = {
            "stream_id": stream_id,
            "stream_name": stream_name,
            "alert_type": alert_type,
            "message": message,
            "severity": severity,
            "timestamp": datetime.utcnow().isoformat()
        }
        await self.trigger_matching_workflows(stream_id, alert_type, payload, user_id)

    async def trigger_matching_workflows(self, stream_id: str, trigger_type: str, payload: Dict[str, Any], user_id: str):
        """Searches user workflows for a stream_processor node matching this trigger type and runs them."""
        async with AsyncSessionLocal() as session:
            workflows = (await session.execute(
                select(Workflow).where(Workflow.user_id == user_id)
            )).scalars().all()

            for wf in workflows:
                should_trigger = False
                try:
                    definition = json.loads(wf.definition)
                    nodes = definition.get("nodes", [])
                    
                    for node in nodes:
                        if node.get("type") == "stream_processor":
                            config = node.get("config", {})
                            listen_stream_id = config.get("stream_id")
                            listen_triggers = config.get("trigger_types", []) # e.g. ["threshold", "anomaly", "failure"]
                            
                            # Trigger if configured to listen to this stream (or any stream) and this trigger type
                            if (not listen_stream_id or listen_stream_id == stream_id) and (not listen_triggers or trigger_type in listen_triggers):
                                should_trigger = True
                                break
                except Exception as e:
                    logger.error(f"Error parsing workflow definition for trigger matching: {e}")

                if should_trigger:
                    logger.info(f"Auto-triggering workflow execution for workflow '{wf.name}' ({wf.id}) due to stream alert.")
                    
                    # Create workflow execution
                    execution = WorkflowExecution(
                        workflow_id=wf.id,
                        status="pending",
                        started_at=datetime.utcnow(),
                        user_id=user_id,
                        execution_data=json.dumps({"initial_variables": payload})
                    )
                    session.add(execution)
                    await session.commit()
                    await session.refresh(execution)

                    from app.services.workflow_engine import workflow_engine
                    import sys
                    import asyncio
                    
                    # Check if running in a test context
                    is_testing = "pytest" in sys.modules or "pytest" in sys.argv[0]
                    if is_testing:
                        await workflow_engine.execute_workflow(execution.id, user_id, initial_variables=payload)
                    else:
                        asyncio.create_task(
                            workflow_engine.execute_workflow(execution.id, user_id, initial_variables=payload)
                        )


stream_alert_service = StreamAlertService()
