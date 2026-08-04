import asyncio
import json
import logging
import time
from datetime import datetime
from typing import Any, Dict, List, Set, Optional

from sqlalchemy import select
from app.core.database import AsyncSessionLocal, get_sync_engine
from app.models.workflow import Workflow, WorkflowExecution
from app.services.notification_service import notification_service

# Import other services inside functions to avoid circular imports

logger = logging.getLogger(__name__)

class WorkflowEngine:
    def __init__(self):
        self.running_executions: Dict[str, asyncio.Task] = {}

    async def execute_workflow(self, execution_id: str, user_id: str, initial_variables: Optional[Dict[str, Any]] = None):
        """Main execution entry point for running a workflow DAG asynchronously."""
        async with AsyncSessionLocal() as session:
            execution = (await session.execute(
                select(WorkflowExecution).where(WorkflowExecution.id == execution_id)
            )).scalar_one_or_none()
            
            if not execution:
                logger.error(f"Workflow execution {execution_id} not found.")
                return

            workflow = (await session.execute(
                select(Workflow).where(Workflow.id == execution.workflow_id)
            )).scalar_one_or_none()

            if not workflow:
                execution.status = "failed"
                execution.finished_at = datetime.utcnow()
                execution.error_message = "Workflow configuration not found."
                session.add(execution)
                await session.commit()
                return

            # Update status to running
            execution.status = "running"
            execution.started_at = datetime.utcnow()
            session.add(execution)
            await session.commit()

        # Load graph definitions
        try:
            definition = json.loads(workflow.definition)
            nodes = {n["id"]: n for n in definition.get("nodes", [])}
            edges = definition.get("edges", [])
        except Exception as e:
            await self._fail_execution(execution_id, f"Invalid workflow JSON definition: {str(e)}")
            return

        # Build dependency graph
        # in_degrees maps node_id -> set of dependency node_ids
        in_degrees: Dict[str, Set[str]] = {nid: set() for nid in nodes}
        out_edges: Dict[str, List[Dict[str, Any]]] = {nid: [] for nid in nodes}

        for edge in edges:
            source = edge.get("source")
            target = edge.get("target")
            if source in nodes and target in nodes:
                # Store target handles and conditional branches metadata if any
                out_edges[source].append(edge)
                in_degrees[target].add(source)

        # Merge initial variables from execution_data and parameter
        merged_variables = {}
        if execution.execution_data:
            try:
                exec_data_parsed = json.loads(execution.execution_data)
                merged_variables.update(exec_data_parsed.get("initial_variables", {}))
            except Exception:
                pass
        if initial_variables:
            merged_variables.update(initial_variables)

        # Context to store node executions status, durations, logs, and outputs
        context: Dict[str, Any] = {
            "node_states": {
                nid: {
                    "status": "pending",
                    "started_at": None,
                    "finished_at": None,
                    "duration": 0.0,
                    "retries": 0,
                    "logs": [],
                    "error": None
                }
                for nid in nodes
            },
            "outputs": {}, # node_id -> output payload
            "variables": merged_variables # globally shared workflow execution variables
        }


        # Queue of nodes that are ready (in_degree is 0)
        ready_nodes = [nid for nid, deps in in_degrees.items() if len(deps) == 0]
        completed_nodes: Set[str] = set()
        failed_nodes: Set[str] = set()

        logger.info(f"Starting workflow execution {execution_id} with entry nodes: {ready_nodes}")

        try:
            # Main execution loop
            while ready_nodes or self._has_active_nodes(context):
                # Start ready nodes in parallel
                futures = []
                nodes_to_run = list(ready_nodes)
                ready_nodes.clear()

                for nid in nodes_to_run:
                    node = nodes[nid]
                    context["node_states"][nid]["status"] = "running"
                    context["node_states"][nid]["started_at"] = datetime.utcnow().isoformat()
                    # Trigger async execution of node
                    futures.append(self._run_node_with_retry_and_timeout(node, execution_id, context, user_id))

                if futures:
                    # Run current batch of independent nodes in parallel
                    results = await asyncio.gather(*futures, return_exceptions=True)

                    for res in results:
                        if isinstance(res, Exception):
                            logger.error(f"Node execution raised exception: {res}")
                            continue

                        node_id, success, output_data = res
                        node_state = context["node_states"][node_id]
                        node_state["finished_at"] = datetime.utcnow().isoformat()
                        
                        start_t = datetime.fromisoformat(node_state["started_at"])
                        end_t = datetime.fromisoformat(node_state["finished_at"])
                        node_state["duration"] = round((end_t - start_t).total_seconds(), 2)

                        if success:
                            node_state["status"] = "completed"
                            completed_nodes.add(node_id)
                            context["outputs"][node_id] = output_data
                            
                            # Log completion
                            self._log_to_node(context, node_id, f"Node completed successfully in {node_state['duration']}s.")
                            
                            # Handle conditional branching outputs
                            activated_downstream = self._resolve_downstream_nodes(
                                node_id, nodes[node_id], output_data, out_edges[node_id], context
                            )
                            
                            for next_nid in activated_downstream:
                                # Remove current completed node from incoming dependencies of downstream
                                if next_nid in in_degrees:
                                    in_degrees[next_nid].discard(node_id)
                                    if len(in_degrees[next_nid]) == 0 and next_nid not in completed_nodes and next_nid not in failed_nodes and next_nid not in ready_nodes:
                                        ready_nodes.append(next_nid)
                        else:
                            node_state["status"] = "failed"
                            failed_nodes.add(node_id)
                            
                            # Check for a specific 'failure' branch connected to this node
                            failure_branches = [edge for edge in out_edges[node_id] if edge.get("sourceHandle") == "failure"]
                            if failure_branches:
                                self._log_to_node(context, node_id, "Node failed. Branching to failure execution handles.")
                                for edge in failure_branches:
                                    target = edge.get("target")
                                    if target in in_degrees:
                                        in_degrees[target].discard(node_id)
                                        if len(in_degrees[target]) == 0:
                                            ready_nodes.append(target)
                            else:
                                # No failure branch: fail the entire workflow execution
                                raise ValueError(f"Node {node_id} ({nodes[node_id]['label']}) failed and has no failure recovery branch.")

                # Save execution intermediate state periodically
                await self._save_execution_progress(execution_id, "running", context)
                await asyncio.sleep(0.5)

            # Check if all nodes finished successfully
            if failed_nodes and not any(edge.get("sourceHandle") == "failure" for edge in edges if edge.get("source") in failed_nodes):
                raise ValueError("One or more workflow nodes failed execution.")

            await self._complete_execution(execution_id, context)

        except Exception as e:
            logger.exception(f"Workflow execution {execution_id} aborted.")
            await self._fail_execution(execution_id, str(e), context)

    def _has_active_nodes(self, context: Dict[str, Any]) -> bool:
        return any(state["status"] == "running" for state in context["node_states"].values())

    async def _run_node_with_retry_and_timeout(
        self, node: Dict[str, Any], execution_id: str, context: Dict[str, Any], user_id: str
    ) -> tuple:
        node_id = node["id"]
        node_type = node["type"]
        config = node.get("config", {})
        
        # Policy configurations
        retry_policy = config.get("retry_policy", {})
        max_retries = int(retry_policy.get("max_retries", 0))
        delay = float(retry_policy.get("delay", 1.0))
        timeout = float(config.get("timeout", 60.0))

        success = False
        output_data = {}
        last_error = None

        for attempt in range(max_retries + 1):
            if attempt > 0:
                context["node_states"][node_id]["retries"] = attempt
                self._log_to_node(context, node_id, f"Retrying execution (Attempt {attempt}/{max_retries}) after {delay}s...")
                await asyncio.sleep(delay)

            self._log_to_node(context, node_id, f"Executing node '{node.get('label', node_id)}' (type: {node_type})...")
            
            config = node.get("config", {})
            execution_mode = config.get("execution_mode", "local")
            preferred_capability = config.get("preferred_capability")
            priority = config.get("priority", "medium")

            try:
                # Wrap node execution logic inside a timeout block
                async with asyncio.timeout(timeout):
                    if execution_mode == "distributed":
                        from app.services.cluster_manager import cluster_manager
                        from app.services.distributed_scheduler import distributed_scheduler
                        
                        active_workers = cluster_manager.get_active_workers(preferred_capability)
                        if not active_workers:
                            self._log_to_node(context, node_id, "No active cluster nodes support this capability. Falling back to local execution...")
                            output_data = await self._execute_node_logic(node, context, user_id)
                        else:
                            self._log_to_node(context, node_id, f"Scheduling distributed node run on cluster [Priority: {priority}, Capability: {preferred_capability or 'Any'}]...")
                            
                            clean_context = {
                                "node_states": {nid: {"logs": [], "status": "pending"} for nid in context.get("node_states", {})},
                                "outputs": context.get("outputs", {}),
                                "variables": context.get("variables", {})
                            }
                            
                            job_id = await distributed_scheduler.submit_job(
                                task_type="workflow",
                                payload={"node": node, "context": clean_context, "user_id": user_id},
                                priority=priority,
                                preferred_capability=preferred_capability
                            )
                            
                            last_log_idx = 0
                            job_completed = False
                            
                            while not job_completed:
                                await asyncio.sleep(0.05)
                                job_info = distributed_scheduler.get_job(job_id)
                                if not job_info:
                                    continue
                                    
                                current_logs = job_info.get("logs", [])
                                if len(current_logs) > last_log_idx:
                                    for log_line in current_logs[last_log_idx:]:
                                        # Clean log prefix before appending
                                        self._log_to_node(context, node_id, f"[Remote] {log_line}")
                                    last_log_idx = len(current_logs)
                                    
                                if job_info["status"] == "completed":
                                    output_data = job_info.get("output", {})
                                    context["node_states"][node_id]["executed_by_worker"] = job_info.get("worker_id")
                                    job_completed = True
                                elif job_info["status"] == "failed":
                                    raise ValueError(f"Distributed execution failed: {job_info.get('output', {}).get('error', 'Unknown error')}")
                    else:
                        output_data = await self._execute_node_logic(node, context, user_id)
                success = True
                break
            except asyncio.TimeoutError:
                last_error = f"Execution timed out after {timeout} seconds."
                self._log_to_node(context, node_id, f"Error: {last_error}")
            except Exception as e:
                logger.exception(f"Error executing node {node_id}")
                last_error = str(e)
                self._log_to_node(context, node_id, f"Error: {last_error}")

        if not success:
            context["node_states"][node_id]["error"] = last_error

        return node_id, success, output_data

    async def _execute_node_logic(self, node: Dict[str, Any], context: Dict[str, Any], user_id: str) -> Dict[str, Any]:
        node_type = node["type"]
        config = node.get("config", {})
        node_id = node["id"]

        # Validate node inputs
        await self._validate_node_inputs(node, context)

        # Execute based on node type
        if node_type == "dataset_upload":
            dataset_id = config.get("dataset_id")
            if not dataset_id:
                raise ValueError("dataset_id is missing in configuration.")
            
            from sqlalchemy import text
            async with AsyncSessionLocal() as session:
                # Verify dataset exists
                res = await session.execute(
                    text(f"SELECT id, filename, table_name FROM user_datasets WHERE id = '{dataset_id}'")
                )
                dataset = res.fetchone()
                if not dataset:
                    raise ValueError(f"Dataset '{dataset_id}' not found.")
            
            self._log_to_node(context, node_id, f"Selected dataset: {dataset[1]} (Table: {dataset[2]})")
            return {"dataset_id": dataset_id, "table_name": dataset[2]}

        elif node_type == "data_profiling":
            # Read input from variables or previous nodes
            dataset_id = self._resolve_input("dataset_id", node, context)
            if not dataset_id:
                raise ValueError("dataset_id is missing.")
            
            from app.services.profiling_service import generate_data_profile
            from app.api.routes.dataset import _load_dataframe_blocking, sanitize_column_name
            
            async with AsyncSessionLocal() as session:
                from app.models.dataset import UserDataset
                dataset = (await session.execute(
                    select(UserDataset).where(UserDataset.id == dataset_id)
                )).scalar_one_or_none()
                
                if not dataset:
                    raise ValueError("Dataset not found.")
            
            ext = dataset.filename.split(".")[-1].lower() if "." in dataset.filename else ""
            df = _load_dataframe_blocking(dataset.file_path, ext)
            df.columns = [sanitize_column_name(c) for c in df.columns]
            
            profile = generate_data_profile(df, dataset.file_path)
            
            # Save profile to dataset
            async with AsyncSessionLocal() as session:
                dataset_db = (await session.execute(
                    select(UserDataset).where(UserDataset.id == dataset_id)
                )).scalar_one()
                dataset_db.profile_info = profile
                await session.commit()

            self._log_to_node(context, node_id, f"Dataset profile generated. Quality score: {profile.get('quality_score', 0)}%")
            return {"dataset_id": dataset_id, "quality_score": profile.get("quality_score", 0), "profile_info": profile}

        elif node_type == "data_cleaning":
            dataset_id = self._resolve_input("dataset_id", node, context)
            cleaning_rules = config.get("cleaning_config", {})
            if not dataset_id:
                raise ValueError("dataset_id is missing.")
            
            from app.api.routes.dataset import _load_dataframe_blocking, sanitize_column_name, generate_eda_stats, get_sync_engine, _write_sql_blocking
            from app.services.cleaning_service import apply_cleaning_operations
            from app.services.profiling_service import generate_data_profile
            from app.services.versioning_service import create_next_version_async
            from app.models.dataset import UserDataset

            async with AsyncSessionLocal() as session:
                dataset = (await session.execute(
                    select(UserDataset).where(UserDataset.id == dataset_id)
                )).scalar_one_or_none()
                if not dataset:
                    raise ValueError("Dataset not found.")

            ext = dataset.filename.split(".")[-1].lower() if "." in dataset.filename else ""
            df = _load_dataframe_blocking(dataset.file_path, ext)
            df.columns = [sanitize_column_name(c) for c in df.columns]

            df_cleaned, preview_report = apply_cleaning_operations(df, cleaning_rules)
            
            async with AsyncSessionLocal() as session:
                dataset_db = (await session.execute(
                    select(UserDataset).where(UserDataset.id == dataset_id)
                )).scalar_one()
                
                # Write to database table
                _write_sql_blocking(df_cleaned, dataset_db.table_name, get_sync_engine())
                new_eda = generate_eda_stats(df_cleaned)

                def save_df_callback(path, extension):
                    if extension == "csv":
                        df_cleaned.to_csv(path, index=False)
                    elif extension in ["xlsx", "xls"]:
                        df_cleaned.to_excel(path, index=False)
                    elif extension == "json":
                        df_cleaned.to_json(path, orient="records")

                version_record = await create_next_version_async(
                    session=session,
                    dataset=dataset_db,
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
                dataset_db.profile_info = new_profile
                
                session.add(version_record)
                session.add(dataset_db)
                await session.commit()

            self._log_to_node(context, node_id, f"Dataset cleaned and version snapshot created.")
            return {"dataset_id": dataset_id, "quality_score": new_profile.get("quality_score", 0)}

        elif node_type == "sql_query":
            db_conn_id = config.get("db_connection_id")
            sql = config.get("query_sql")
            
            if not sql:
                raise ValueError("query_sql configuration is required.")

            from app.core.connection_manager import connection_manager
            
            # Execute dynamically
            if db_conn_id:
                async with AsyncSessionLocal() as session:
                    from app.models.db_connection import DatabaseConnection
                    conn = (await session.execute(
                        select(DatabaseConnection).where(DatabaseConnection.id == db_conn_id)
                    )).scalar_one_or_none()
                    if not conn:
                        raise ValueError(f"Database connection {db_conn_id} not found.")
                
                # Decrypt credentials and execute
                from app.utils.crypto import decrypt_password
                pwd = decrypt_password(conn.password) if conn.password else ""
                
                self._log_to_node(context, node_id, f"Executing SQL query on database '{conn.database_name}'...")
                res = await connection_manager.execute_query(
                    dialect=conn.db_type,
                    host=conn.host,
                    port=conn.port,
                    user=conn.username,
                    password=pwd,
                    database=conn.database_name,
                    query=sql
                )
                rows = res.get("data", [])
            else:
                # Fallback to local SQLite default db
                from sqlalchemy import text
                self._log_to_node(context, node_id, "Executing SQL query on local SQLite database...")
                async with AsyncSessionLocal() as session:
                    res = await session.execute(text(sql))
                    rows = [dict(row._mapping) for row in res.all()]

            self._log_to_node(context, node_id, f"Query returned {len(rows)} records.")
            return {"rows": rows, "count": len(rows)}

        elif node_type == "federated_query":
            query = config.get("query") or self._resolve_input("query", node, context)
            if not query:
                raise ValueError("query is missing.")

            from app.services.federation_service import federation_service
            self._log_to_node(context, node_id, f"Executing distributed federated query: '{query}'...")
            res = await federation_service.execute_federated_query(query, user_id)
            if not res.get("success"):
                raise ValueError(res.get("error", "Federated query execution failed."))
                
            self._log_to_node(context, node_id, f"Federated query executed successfully. Mapped {len(res.get('rows', []))} rows.")
            return {
                "columns": res.get("columns"),
                "rows": res.get("rows"),
                "warnings": res.get("warning")
            }

        elif node_type == "rag_query":
            question = config.get("query") or self._resolve_input("query", node, context)
            if not question:
                raise ValueError("query question is missing.")

            from app.services.rag_service import RAGService
            rag_service = RAGService()
            
            import uuid
            conv_id = str(uuid.uuid4())
            self._log_to_node(context, node_id, f"Querying RAG with question: '{question}'...")
            res = await rag_service.query_rag(conversation_id=conv_id, question=question, user_id=user_id)
            
            self._log_to_node(context, node_id, "RAG query response generated successfully.")
            return {
                "answer": res.get("answer"),
                "citations": res.get("citations", []),
                "confidence_score": res.get("confidence_score", 0.5)
            }

        elif node_type == "multi_agent_analysis":
            query = config.get("query") or self._resolve_input("query", node, context)
            if not query:
                raise ValueError("query intent is missing.")

            from app.services.agent_manager import agent_manager
            
            self._log_to_node(context, node_id, f"Starting collaborative Multi-agent Analyst run for: '{query}'...")
            res = await agent_manager.execute_query(user_id=user_id, query=query)
            
            self._log_to_node(context, node_id, f"Collaborative analysis completed. Score: {res.get('critic_score', 0)}")
            return {
                "execution_id": res.get("execution_id"),
                "final_answer": res.get("final_answer"),
                "critic_score": res.get("critic_score", 0),
                "shared_memory": res.get("shared_memory", {})
            }

        elif node_type == "explainability":
            sql = config.get("sql") or self._resolve_input("sql", node, context)
            query = config.get("query") or self._resolve_input("query", node, context)
            
            from app.services.xai_service import XAIService
            xai_service = XAIService()
            
            self._log_to_node(context, node_id, "Generating programmatic explainability audit report...")
            res = await xai_service.generate_sql_explanation(sql=sql, question=query, schema_context={})
            
            return {
                "explanation": res.get("explanation"),
                "confidence": res.get("confidence_score", 0.5),
                "audits": res.get("security_audits", [])
            }

        elif node_type == "report_generation":
            execution_id_input = config.get("agent_execution_id") or self._resolve_input("execution_id", node, context)
            report_type = config.get("report_type", "sales_analytics")
            file_format = config.get("file_format", "pdf")
            branding = config.get("branding", {})

            if not execution_id_input:
                raise ValueError("agent_execution_id is required for report generation.")

            from app.services.report_service import ReportService
            report_service = ReportService()
            
            self._log_to_node(context, node_id, f"Triggering report compilation ({file_format.upper()}) for execution {execution_id_input}...")
            trigger_res = await report_service.trigger_generation(
                execution_id=execution_id_input,
                report_type=report_type,
                file_format=file_format,
                branding=branding,
                user_id=user_id
            )
            
            report_id = trigger_res["report_id"]
            # Compile report synchronously inside engine run
            await report_service.execute_async_generation(report_id)
            
            report_details = await report_service.get_report(report_id, user_id)
            if report_details.get("status") == "failed":
                raise ValueError(f"Report generation failed: {report_details.get('error_message')}")

            self._log_to_node(context, node_id, f"Report file compiled: {report_details.get('file_path')}")
            return {
                "report_id": report_id,
                "file_path": report_details.get("file_path"),
                "status": "completed"
            }

        elif node_type == "notification":
            title = config.get("title", "Workflow Alert")
            message = config.get("message", "Alert triggered by workflow node.")
            severity = config.get("severity", "info")
            
            notification_service.send_notification(
                user_id=user_id,
                title=title,
                message=message,
                severity=severity
            )
            
            self._log_to_node(context, node_id, f"Notification sent: '{title}' ({severity})")
            return {"notified": True}

        elif node_type == "export":
            dataset_id = self._resolve_input("dataset_id", node, context)
            export_format = config.get("format", "csv")
            
            if not dataset_id:
                raise ValueError("dataset_id input is missing for export.")

            from app.services.export_service import ExportService
            from app.models.dataset import UserDataset
            export_service = ExportService()
            
            async with AsyncSessionLocal() as session:
                dataset = (await session.execute(
                    select(UserDataset).where(UserDataset.id == dataset_id)
                )).scalar_one_or_none()
                if not dataset:
                    raise ValueError("Dataset not found.")

            self._log_to_node(context, node_id, f"Exporting dataset '{dataset.filename}' as {export_format.upper()}...")
            # Implement copy to exports or similar
            export_dir = os.path.abspath(os.path.join("backend", "data", "exports")) if os.path.exists("backend") else os.path.abspath(os.path.join("data", "exports"))
            os.makedirs(export_dir, exist_ok=True)
            
            import shutil
            filename = f"export_{dataset_id}.{export_format}"
            dest_path = os.path.join(export_dir, filename)
            shutil.copy(dataset.file_path, dest_path)
            
            self._log_to_node(context, node_id, f"File successfully exported to: {dest_path}")
            return {"file_path": dest_path, "filename": filename}

        elif node_type == "stream_processor":
            action = config.get("action", "get_stats") # start, stop, get_stats
            stream_id = config.get("stream_id") or self._resolve_input("stream_id", node, context)
            
            if not stream_id:
                raise ValueError("stream_id configuration or input is required.")
                
            from app.services.streaming_service import streaming_service
            
            if action == "start":
                self._log_to_node(context, node_id, f"Triggering startup for stream config '{stream_id}'...")
                await streaming_service.start_stream(stream_id, user_id)
                return {"stream_id": stream_id, "status": "started"}
            elif action == "stop":
                self._log_to_node(context, node_id, f"Triggering shutdown for stream config '{stream_id}'...")
                await streaming_service.stop_stream(stream_id, user_id)
                return {"stream_id": stream_id, "status": "stopped"}
            elif action == "get_stats":
                self._log_to_node(context, node_id, f"Fetching statistics for stream '{stream_id}'...")
                from app.services.stream_analytics_service import stream_analytics_service
                stats = await stream_analytics_service.get_running_metrics(stream_id)
                return {"stream_id": stream_id, "metrics": stats}
            else:
                raise ValueError(f"Unsupported stream_processor action '{action}'")

        elif node_type == "model_training":
            dataset_id = config.get("dataset_id") or self._resolve_input("dataset_id", node, context)
            target = config.get("target_variable") or self._resolve_input("target_variable", node, context)
            task_type = config.get("task_type") or self._resolve_input("task_type", node, context) or "classification"
            
            if not dataset_id:
                raise ValueError("dataset_id is required for model_training.")
            if not target and task_type != "clustering":
                raise ValueError("target_variable is required for model_training.")

            from app.services.predictive_analytics_service import predictive_analytics_service
            self._log_to_node(context, node_id, f"Orchestrating AutoML training for target: {target} (task: {task_type})...")
            res = await predictive_analytics_service.train_automl_model(
                dataset_id=dataset_id,
                target=target or "None",
                task_type=task_type,
                user_id=user_id
            )
            self._log_to_node(context, node_id, f"AutoML Model '{res.get('model_name')}' trained successfully. Best score: {res.get('metrics', {}).get('best_score')}")
            return res

        elif node_type == "prediction":
            model_id = config.get("model_id") or self._resolve_input("model_id", node, context)
            dataset_id = config.get("dataset_id") or self._resolve_input("dataset_id", node, context)

            if not model_id:
                raise ValueError("model_id is required for prediction.")
            if not dataset_id:
                raise ValueError("dataset_id is required for prediction.")

            from app.services.predictive_analytics_service import predictive_analytics_service
            self._log_to_node(context, node_id, f"Running model inference (model: {model_id}) on dataset {dataset_id}...")
            res = await predictive_analytics_service.generate_predictions(
                model_id=model_id,
                dataset_id=dataset_id
            )
            self._log_to_node(context, node_id, f"Generated {res.get('predictions_count')} predictions successfully.")
            
            # Record workflow execution metric
            try:
                from app.services.monitoring_service import monitoring_service
                monitoring_service.record_workflow_prediction_execution()
            except Exception:
                pass
                
            return res

        elif node_type == "prescriptive_analysis":
            model_id = config.get("model_id") or self._resolve_input("model_id", node, context)
            base_features = config.get("base_features") or self._resolve_input("base_features", node, context) or {}
            actionable_features = config.get("actionable_features") or self._resolve_input("actionable_features", node, context) or []
            business_rules = config.get("business_rules") or self._resolve_input("business_rules", node, context) or {}
            target_direction = config.get("target_direction", "minimize")

            if not model_id:
                raise ValueError("model_id is required for prescriptive_analysis.")

            from app.services.prescriptive_service import prescriptive_service
            self._log_to_node(context, node_id, "Running prescriptive simulation optimization...")
            res = await prescriptive_service.generate_prescriptive_actions(
                model_id=model_id,
                base_features=base_features,
                actionable_features=actionable_features,
                business_rules=business_rules,
                target_direction=target_direction
            )
            self._log_to_node(context, node_id, f"Suggested {res.get('recommendation_count')} ranked optimization actions.")
            return res

        # Handle Conditional / Loop nodes
        elif node_type in ["if", "switch", "loop"]:
            # These are control structures, they do not have separate heavy logic.
            # We evaluate them during execution and resolve downstream.
            return {"control": True}

        else:
            from app.services.plugin_manager import plugin_manager
            if plugin_manager.has_node_type(node_type):
                self._log_to_node(context, node_id, f"Delegating to custom plugin node: '{node_type}'...")
                res = await plugin_manager.execute_node(node_type, node, context, user_id)
                self._log_to_node(context, node_id, f"Custom plugin node '{node_type}' executed successfully.")
                return res
            else:
                raise NotImplementedError(f"Unsupported node type: {node_type}")

    async def _validate_node_inputs(self, node: Dict[str, Any], context: Dict[str, Any]):
        # Custom input validation rules check via plugin manager
        node_type = node.get("type")
        from app.services.plugin_manager import plugin_manager
        if plugin_manager.has_node_type(node_type):
            await plugin_manager.validate_node_config(node_type, node, context)

    def _resolve_input(self, field_name: str, node: Dict[str, Any], context: Dict[str, Any]) -> Any:
        # Check node configurations first
        config = node.get("config", {})
        if field_name in config and config[field_name]:
            return config[field_name]

        # Check outputs of upstream nodes that are linked to this node
        # For simple mappings, we check all completed nodes outputs keys
        for nid, output in context["outputs"].items():
            if isinstance(output, dict) and field_name in output:
                return output[field_name]
        return None

    def _log_to_node(self, context: Dict[str, Any], node_id: str, message: str):
        timestamp = datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S")
        context["node_states"][node_id]["logs"].append(f"[{timestamp}] {message}")
        logger.info(f"[{node_id}] {message}")

    def _resolve_downstream_nodes(
        self, node_id: str, node: Dict[str, Any], output_data: Dict[str, Any], out_edges: List[Dict[str, Any]], context: Dict[str, Any]
    ) -> List[str]:
        node_type = node["type"]
        config = node.get("config", {})

        if node_type == "if":
            # Evaluate condition
            condition_field = config.get("condition_field")
            operator = config.get("operator", "==")
            target_value = config.get("value")

            # Resolve actual value of condition_field from variables/outputs
            actual_val = output_data.get(condition_field)
            if actual_val is None:
                # Try from general outputs of any completed nodes in context
                for prev_node_id, prev_output in context.get("outputs", {}).items():
                    if isinstance(prev_output, dict) and condition_field in prev_output:
                        actual_val = prev_output[condition_field]
                        break
            if actual_val is None:
                # Try variables
                actual_val = context.get("variables", {}).get(condition_field)
            
            # Simple condition validator
            condition_met = False
            try:
                if operator == "==":
                    condition_met = (str(actual_val) == str(target_value))
                elif operator == "!=":
                    condition_met = (str(actual_val) != str(target_value))
                elif operator == "<":
                    condition_met = (float(actual_val) < float(target_value))
                elif operator == ">":
                    condition_met = (float(actual_val) > float(target_value))
                elif operator == "<=":
                    condition_met = (float(actual_val) <= float(target_value))
                elif operator == ">=":
                    condition_met = (float(actual_val) >= float(target_value))
                elif operator == "contains":
                    condition_met = (str(target_value) in str(actual_val))
            except Exception as e:
                logger.error(f"Failed to evaluate IF condition logic: {e}")
                condition_met = False

            branch = "true" if condition_met else "false"
            logger.info(f"Evaluating IF node {node_id}: {actual_val} {operator} {target_value} -> {branch}")

            # Return only target nodes connected to the matching sourceHandle branch
            return [edge["target"] for edge in out_edges if edge.get("sourceHandle") == branch]

        elif node_type == "switch":
            switch_field = config.get("switch_field")
            actual_val = str(output_data.get(switch_field, ""))

            activated = []
            matched = False
            for edge in out_edges:
                handle = edge.get("sourceHandle")
                if handle == actual_val:
                    activated.append(edge["target"])
                    matched = True

            if not matched:
                # Fallback to default branch
                default_nodes = [edge["target"] for edge in out_edges if edge.get("sourceHandle") == "default"]
                activated.extend(default_nodes)

            return activated

        # Default sequential routing
        return [edge["target"] for edge in out_edges if edge.get("sourceHandle") not in ["failure"]]

    async def _save_execution_progress(self, execution_id: str, status: str, context: Dict[str, Any], error_msg: Optional[str] = None):
        async with AsyncSessionLocal() as session:
            exec_rec = (await session.execute(
                select(WorkflowExecution).where(WorkflowExecution.id == execution_id)
            )).scalar_one_or_none()

            if exec_rec:
                exec_rec.status = status
                exec_rec.execution_data = json.dumps(context)
                if error_msg:
                    exec_rec.error_message = error_msg
                await session.commit()

    async def _complete_execution(self, execution_id: str, context: Dict[str, Any]):
        async with AsyncSessionLocal() as session:
            exec_rec = (await session.execute(
                select(WorkflowExecution).where(WorkflowExecution.id == execution_id)
            )).scalar_one_or_none()

            if exec_rec:
                exec_rec.status = "completed"
                exec_rec.finished_at = datetime.utcnow()
                exec_rec.execution_data = json.dumps(context)
                await session.commit()
                
                # Send completion notification
                notification_service.send_notification(
                    user_id=exec_rec.user_id,
                    title="Workflow Completed",
                    message=f"Workflow run succeeded.",
                    severity="success"
                )

    async def _fail_execution(self, execution_id: str, error_msg: str, context: Optional[Dict[str, Any]] = None):
        async with AsyncSessionLocal() as session:
            exec_rec = (await session.execute(
                select(WorkflowExecution).where(WorkflowExecution.id == execution_id)
            )).scalar_one_or_none()

            if exec_rec:
                exec_rec.status = "failed"
                exec_rec.finished_at = datetime.utcnow()
                exec_rec.error_message = error_msg
                if context:
                    exec_rec.execution_data = json.dumps(context)
                await session.commit()

                # Send failure notification
                notification_service.send_notification(
                    user_id=exec_rec.user_id,
                    title="Workflow Failed",
                    message=f"Workflow execution failed: {error_msg[:100]}",
                    severity="error"
                )

workflow_engine = WorkflowEngine()
import os
