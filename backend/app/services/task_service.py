import json
import logging
import threading
import uuid
from datetime import datetime
from typing import List, Optional

from sqlalchemy import desc, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.celery_app import celery_run_task, check_celery_broker_available
from app.core.database import AsyncSessionLocal, get_sync_engine
from app.models.dataset import UserDataset
from app.models.task import Task
from app.services.notification_service import notification_service

logger = logging.getLogger(__name__)


class TaskService:
    async def create_task(
        self,
        task_type: str,
        user_id: str,
        dataset_id: Optional[str] = None,
        payload: Optional[dict] = None,
        session: Optional[AsyncSession] = None,
    ) -> Task:
        """Create a new background task database record and trigger execution"""
        payload_str = json.dumps(payload or {})

        db_task = Task(
            id=str(uuid.uuid4()),
            task_type=task_type,
            status="pending",
            progress=0,
            started_at=datetime.utcnow(),
            user_id=user_id,
            dataset_id=dataset_id,
            payload=payload_str,
        )

        should_commit = False
        if session is None:
            session = AsyncSessionLocal()
            should_commit = True

        try:
            session.add(db_task)
            await session.commit()
            await session.refresh(db_task)
        finally:
            if should_commit:
                await session.close()

        # Send starting notification
        notification_service.send_notification(
            user_id=user_id,
            title="Task Started",
            message=f"Background {task_type.replace('_', ' ')} has started processing.",
            severity="info",
        )

        # Trigger background execution
        await self.trigger_task_execution(db_task.id, task_type, payload or {})
        return db_task

    async def trigger_task_execution(self, task_id: str, task_type: str, payload: dict):
        """Sends the task to Celery or falls back to local thread execution if broker offline"""
        import sys

        from app.core.database import engine

        is_testing = (
            "pytest" in sys.modules or "pytest" in sys.argv[0] or "test_analytics" in str(engine.url)
        ) and not payload.get("skip_test_sync", False)

        if is_testing:
            logger.info(f"Test context detected. Running task {task_id} synchronously.")
            await self.execute_task_logic(task_id, task_type, payload)
            return

        if check_celery_broker_available():
            try:
                celery_run_task.delay(task_id, task_type, payload)
                logger.info(f"Queued task {task_id} in Celery successfully.")
                return
            except Exception as e:
                logger.warning(f"Failed to queue task {task_id} in Celery. Falling back to local run. Error: {e}")

        # Local Thread execution fallback
        self._run_task_locally(task_id, task_type, payload)

    def _run_task_locally(self, task_id: str, task_type: str, payload: dict):
        logger.info(f"Running task {task_id} locally in daemon thread.")

        def run_sync():
            import asyncio

            try:
                loop = asyncio.get_event_loop()
            except RuntimeError:
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)

            loop.run_until_complete(self.execute_task_logic(task_id, task_type, payload))

        t = threading.Thread(target=run_sync)
        t.daemon = True
        t.start()

    async def update_progress(self, task_id: str, progress: int, session: AsyncSession):
        """Update progress value in database"""
        from sqlalchemy import text

        await session.execute(
            text(f"UPDATE tasks SET progress = {progress}, status = 'running' WHERE id = '{task_id}'")
        )
        await session.commit()

    async def execute_task_logic(self, task_id: str, task_type: str, payload: dict):
        """Dispatches and runs the heavy operation logic"""
        async with AsyncSessionLocal() as session:
            # Get Task info
            task = (await session.execute(select(Task).where(Task.id == task_id))).scalar_one_or_none()

            if not task:
                logger.error(f"Task {task_id} not found in database.")
                return

            user_id = task.user_id
            dataset_id = task.dataset_id

            try:
                # Update status to running
                task.status = "running"
                task.progress = 5
                task.started_at = datetime.utcnow()
                session.add(task)
                await session.commit()
                import time
                started_time = time.time()

                # Import routes helper functions locally to avoid circular dependencies
                from app.api.routes.dataset import (
                    _load_dataframe_blocking,
                    _write_sql_blocking,
                    generate_eda_stats,
                    sanitize_column_name,
                )
                from app.services.profiling_service import generate_data_profile
                from app.services.versioning_service import create_initial_version_async

                if task_type == "dataset_profiling":
                    dataset = (
                        await session.execute(select(UserDataset).where(UserDataset.id == dataset_id))
                    ).scalar_one_or_none()
                    if not dataset:
                        raise ValueError("Dataset not found")

                    await self.update_progress(task_id, 15, session)
                    ext = dataset.filename.split(".")[-1].lower() if "." in dataset.filename else ""

                    df = _load_dataframe_blocking(dataset.file_path, ext)
                    df.columns = [sanitize_column_name(c) for c in df.columns]
                    df = df.loc[:, ~df.columns.str.startswith("unnamed")]

                    await self.update_progress(task_id, 45, session)
                    row_count = len(df)
                    col_count = len(df.columns)
                    columns_list = list(df.columns)
                    schema_info = generate_eda_stats(df)

                    await self.update_progress(task_id, 75, session)
                    profile_info = generate_data_profile(df, dataset.file_path)

                    await self.update_progress(task_id, 90, session)
                    _write_sql_blocking(df, dataset.table_name, get_sync_engine())

                    dataset.row_count = row_count
                    dataset.col_count = col_count
                    dataset.columns = columns_list
                    dataset.schema_info = schema_info
                    dataset.profile_info = profile_info
                    dataset.status = "active"
                    session.add(dataset)
                    await session.commit()
                    await session.refresh(dataset)

                    await create_initial_version_async(session, dataset)

                elif task_type == "data_cleaning":
                    dataset = (
                        await session.execute(select(UserDataset).where(UserDataset.id == dataset_id))
                    ).scalar_one_or_none()
                    if not dataset:
                        raise ValueError("Dataset not found")

                    await self.update_progress(task_id, 20, session)

                    from app.api.routes.dataset import cleaning_statuses

                    cleaning_statuses[dataset_id] = "cleaning"

                    ext = dataset.filename.split(".")[-1].lower() if "." in dataset.filename else ""
                    df = _load_dataframe_blocking(dataset.file_path, ext)
                    df.columns = [sanitize_column_name(c) for c in df.columns]
                    df = df.loc[:, ~df.columns.str.startswith("unnamed")]

                    await self.update_progress(task_id, 50, session)
                    quality_score_before = 0
                    if dataset.profile_info and isinstance(dataset.profile_info, dict):
                        quality_score_before = dataset.profile_info.get("quality_score", 0)

                    from app.services.cleaning_service import apply_cleaning_operations

                    df_cleaned, preview_report = apply_cleaning_operations(df, payload["config"])

                    await self.update_progress(task_id, 75, session)
                    _write_sql_blocking(df_cleaned, dataset.table_name, get_sync_engine())
                    new_eda = generate_eda_stats(df_cleaned)

                    def save_df_callback(path, extension):
                        if extension == "csv":
                            df_cleaned.to_csv(path, index=False)
                        elif extension in ["xlsx", "xls"]:
                            df_cleaned.to_excel(path, index=False)
                        elif extension == "json":
                            df_cleaned.to_json(path, orient="records")

                    await self.update_progress(task_id, 90, session)
                    from app.services.versioning_service import create_next_version_async

                    version_record = await create_next_version_async(
                        session=session,
                        dataset=dataset,
                        operations=preview_report.get("operations_to_apply", []),
                        row_count=len(df_cleaned),
                        col_count=len(df_cleaned.columns),
                        columns=list(df_cleaned.columns),
                        schema_info=new_eda,
                        profile_info=None,
                        save_df_callback=save_df_callback,
                    )

                    new_profile = generate_data_profile(df_cleaned, version_record.file_path)
                    version_record.profile_info = new_profile
                    dataset.profile_info = new_profile
                    session.add(version_record)
                    session.add(dataset)
                    await session.commit()

                    quality_score_after = new_profile.get("quality_score", 0) if new_profile else 0
                    rows_changed = preview_report.get("rows_before", 0) - preview_report.get("rows_after", 0)
                    cols_changed = preview_report.get("columns_before", 0) - preview_report.get("columns_after", 0)

                    from app.services.audit_service import log_audit_entry_async

                    await log_audit_entry_async(
                        session=session,
                        dataset=dataset,
                        user_id=user_id,
                        user_email=payload["user_email"],
                        operations_applied=preview_report.get("operations_to_apply", []),
                        rows_changed=rows_changed,
                        columns_changed=cols_changed,
                        quality_score_before=quality_score_before,
                        quality_score_after=quality_score_after,
                        version_created=version_record.version_number,
                    )

                    cleaning_statuses[dataset_id] = "completed"

                elif task_type == "ai_cleaning":
                    from app.models.ai_cleaning import AICleaningRecommendation
                    from app.services.ai_cleaning_service import apply_ai_transformations

                    rec_id = payload["recommendation_id"]
                    rec = (await session.execute(
                        select(AICleaningRecommendation).where(AICleaningRecommendation.id == rec_id)
                    )).scalar_one_or_none()
                    if not rec:
                        raise ValueError("Recommendation details not found")

                    dataset = (
                        await session.execute(select(UserDataset).where(UserDataset.id == dataset_id))
                    ).scalar_one_or_none()
                    if not dataset:
                        raise ValueError("Dataset not found")

                    await self.update_progress(task_id, 20, session)

                    ext = dataset.filename.split(".")[-1].lower() if "." in dataset.filename else ""
                    df = _load_dataframe_blocking(dataset.file_path, ext)
                    df.columns = [sanitize_column_name(c) for c in df.columns]
                    df = df.loc[:, ~df.columns.str.startswith("unnamed")]

                    await self.update_progress(task_id, 45, session)

                    approved_step_ids = rec.approved_steps or []
                    all_steps = rec.execution_plan or []
                    approved_steps = [s for s in all_steps if s.get("step_id") in approved_step_ids]

                    quality_score_before = 0
                    if dataset.profile_info and isinstance(dataset.profile_info, dict):
                        quality_score_before = dataset.profile_info.get("quality_score", 0)

                    df_cleaned, operations_applied = apply_ai_transformations(df, approved_steps)

                    await self.update_progress(task_id, 70, session)
                    _write_sql_blocking(df_cleaned, dataset.table_name, get_sync_engine())
                    new_eda = generate_eda_stats(df_cleaned)

                    def save_df_callback(path, extension):
                        if extension == "csv":
                            df_cleaned.to_csv(path, index=False)
                        elif extension in ["xlsx", "xls"]:
                            df_cleaned.to_excel(path, index=False)
                        elif extension == "json":
                            df_cleaned.to_json(path, orient="records")

                    await self.update_progress(task_id, 85, session)
                    from app.services.versioning_service import create_next_version_async

                    version_record = await create_next_version_async(
                        session=session,
                        dataset=dataset,
                        operations=operations_applied if operations_applied else ["AI Data Cleaning Applied"],
                        row_count=len(df_cleaned),
                        col_count=len(df_cleaned.columns),
                        columns=list(df_cleaned.columns),
                        schema_info=new_eda,
                        profile_info=None,
                        save_df_callback=save_df_callback,
                    )

                    new_profile = generate_data_profile(df_cleaned, version_record.file_path)
                    version_record.profile_info = new_profile
                    dataset.profile_info = new_profile

                    rec.status = "executed"
                    rec.executed_at = datetime.utcnow()

                    session.add(version_record)
                    session.add(dataset)
                    session.add(rec)
                    await session.commit()

                    quality_score_after = new_profile.get("quality_score", 0) if new_profile else 0
                    rows_changed = len(df) - len(df_cleaned)
                    cols_changed = len(df.columns) - len(df_cleaned.columns)

                    from app.services.audit_service import log_audit_entry_async

                    await log_audit_entry_async(
                        session=session,
                        dataset=dataset,
                        user_id=user_id,
                        user_email=payload.get("user_email", "ai_assistant@local.io"),
                        operations_applied=operations_applied if operations_applied else ["AI Data Cleaning Applied"],
                        rows_changed=rows_changed,
                        columns_changed=cols_changed,
                        quality_score_before=quality_score_before,
                        quality_score_after=quality_score_after,
                        version_created=version_record.version_number,
                    )

                    tx_types = [s.get("transformation") for s in approved_steps]
                    from app.services.monitoring_service import monitoring_service
                    monitoring_service.record_ai_cleaning_execution(time.time() - started_time, tx_types)

                elif task_type == "dashboard_generation":
                    dataset = (
                        await session.execute(select(UserDataset).where(UserDataset.id == dataset_id))
                    ).scalar_one_or_none()
                    if not dataset:
                        raise ValueError("Dataset not found")

                    await self.update_progress(task_id, 30, session)
                    dashboard_name = payload.get("name") or f"Dashboard: {dataset.filename}"

                    if payload.get("question") and payload["question"].strip():
                        dashboard_name = f"NL Dashboard: '{payload['question']}'"
                        from app.services.query_service import QueryService

                        query_service = QueryService()
                        query_res = await query_service.process_query(
                            user_id=user_id, question=payload["question"], dataset_id=dataset.id
                        )
                        if not query_res.get("success"):
                            raise ValueError(f"Query failed: {query_res.get('error')}")

                        rows = query_res.get("data", [])
                        sql = query_res.get("sql", "")
                        explanation = query_res.get("explanation", "")

                        import pandas as pd

                        df = pd.DataFrame(rows)
                        kpi_cards = []
                        charts = []

                        await self.update_progress(task_id, 70, session)
                        from app.services.dashboard_service import (
                            calculate_kpis_for_dataframe,
                            choose_optimal_chart,
                            format_chart_js_payload,
                        )

                        if not df.empty:
                            kpi_cards = calculate_kpis_for_dataframe(df)
                            chart_config = choose_optimal_chart(df)
                            chart_payload = format_chart_js_payload(df, chart_config)
                            charts.append(
                                {
                                    "id": "nl_chart_1",
                                    "title": f"Visualization for '{payload['question']}'",
                                    "chart_type": chart_config.get("chart_type"),
                                    "chart_data": chart_payload,
                                    "x_axis": chart_config.get("x_axis"),
                                    "y_axis": chart_config.get("y_axis"),
                                    "sql": sql,
                                    "explanation": explanation,
                                }
                            )
                        widgets = {
                            "metadata": {
                                "dataset_id": dataset.id,
                                "dataset_name": dataset.filename,
                                "generated_time": datetime.utcnow().isoformat(),
                                "number_of_charts": len(charts),
                                "number_of_kpis": len(kpi_cards),
                                "number_of_records": len(df),
                                "filters_applied": [{"type": "question", "val": payload["question"]}],
                            },
                            "kpi_cards": kpi_cards[:6],
                            "charts": charts,
                            "layout": {"grid_columns": 1},
                        }
                    else:
                        await self.update_progress(task_id, 70, session)
                        from app.services.dashboard_service import generate_default_dashboard

                        widgets = generate_default_dashboard(dataset)

                    await self.update_progress(task_id, 90, session)
                    from app.services.dashboard_service import save_dashboard_history

                    await save_dashboard_history(session=session, user_id=user_id, name=dashboard_name, widgets=widgets)

                elif task_type == "ai_insights":
                    await self.update_progress(task_id, 50, session)
                    from app.services.insight_service import generate_dataset_insights

                    await generate_dataset_insights(dataset_id, user_id, session)

                # Complete Task
                task.status = "completed"
                task.progress = 100
                task.finished_at = datetime.utcnow()
                session.add(task)
                await session.commit()

                # Send completed notification
                notification_service.send_notification(
                    user_id=user_id,
                    title="Task Completed",
                    message=f"Background {task_type.replace('_', ' ')} processed successfully.",
                    severity="success",
                )

            except Exception as e:
                logger.exception(f"Error running background task: {task_id}")
                task.status = "failed"
                task.finished_at = datetime.utcnow()
                task.error_message = str(e)
                session.add(task)
                await session.commit()

                if task_type == "data_cleaning" and dataset_id:
                    from app.api.routes.dataset import cleaning_statuses

                    cleaning_statuses[dataset_id] = "failed"

                # Send failed notification
                notification_service.send_notification(
                    user_id=user_id,
                    title="Task Failed",
                    message=f"Background {task_type.replace('_', ' ')} execution failed: {str(e)}",
                    severity="error",
                )

    async def list_tasks(self, user_id: str, session: AsyncSession) -> List[Task]:
        """Lists tasks for a specific user sorted by start time descending"""
        stmt = select(Task).where(Task.user_id == user_id).order_by(desc(Task.started_at))
        return (await session.execute(stmt)).scalars().all()

    async def get_task(self, task_id: str, session: AsyncSession) -> Optional[Task]:
        """Retrieves a single task detail"""
        return (await session.execute(select(Task).where(Task.id == task_id))).scalar_one_or_none()

    async def retry_task(self, task_id: str, session: AsyncSession) -> Task:
        """Reruns a failed background task using stored payload parameters"""
        task = (await session.execute(select(Task).where(Task.id == task_id))).scalar_one_or_none()
        if not task:
            raise ValueError("Task not found")

        payload = json.loads(task.payload or "{}")

        task.status = "pending"
        task.progress = 0
        task.started_at = datetime.utcnow()
        task.finished_at = None
        task.error_message = None
        session.add(task)
        await session.commit()
        await session.refresh(task)

        # Trigger execution again
        await self.trigger_task_execution(task.id, task.task_type, payload)

        notification_service.send_notification(
            user_id=task.user_id,
            title="Task Retried",
            message=f"Rerunning background task {task.task_type.replace('_', ' ')}.",
            severity="info",
        )
        return task

    async def delete_task(self, task_id: str, session: AsyncSession) -> bool:
        """Deletes task record or cancels execution if pending/running"""
        task = (await session.execute(select(Task).where(Task.id == task_id))).scalar_one_or_none()
        if not task:
            return False

        if task.status in ["pending", "running"]:
            task.status = "cancelled"
            task.finished_at = datetime.utcnow()
            session.add(task)
            await session.commit()
            return True

        await session.delete(task)
        await session.commit()
        return True


task_service = TaskService()
