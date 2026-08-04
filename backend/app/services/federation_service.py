import time
import json
import logging
import pandas as pd
import asyncio
from datetime import datetime
from typing import Any, Dict, List, Tuple, Optional

from sqlalchemy import select
from app.core.database import AsyncSessionLocal
from app.models.db_connection import DatabaseConnection
from app.models.federation import FederatedQueryRecord
from app.core.connection_manager import ConnectionManager
from app.services.query_planner_service import query_planner_service
from app.services.semantic_layer_service import semantic_layer_service
from app.models.knowledge import KnowledgeEntity

logger = logging.getLogger(__name__)

class FederationService:
    def __init__(self):
        self.stats = {
            "query_count": 0,
            "success_count": 0,
            "partial_failure_count": 0,
            "failure_count": 0,
            "total_latency_ms": 0.0,
            "total_join_time_ms": 0.0
        }

    async def get_unified_catalog(self, user_id: str) -> List[Dict[str, Any]]:
        """Compiles structural schemas, connections, semantic layer, and KG paths into a unified catalog."""
        catalog = []
        async with AsyncSessionLocal() as session:
            # 1. Fetch connections
            db_conns = (await session.execute(
                select(DatabaseConnection).where(DatabaseConnection.user_id == user_id)
            )).scalars().all()

            conn_manager = ConnectionManager()
            for conn in db_conns:
                # Tables schema caching
                try:
                    schema_cache = conn_manager.schema_cache.get(conn.id, {})
                except Exception:
                    schema_cache = {}

                for tb_name, cols in schema_cache.items():
                    columns_meta = []
                    for c in cols:
                        col_name = c.get("name")
                        # Look up synonyms from semantic layer
                        syns = semantic_layer_service.resolve_synonyms(col_name)
                        columns_meta.append({
                            "name": col_name,
                            "type": c.get("type", "unknown"),
                            "synonyms": syns
                        })

                    catalog.append({
                        "connection_id": conn.id,
                        "database_name": conn.database_name,
                        "dialect": conn.db_type,
                        "table_name": tb_name,
                        "columns": columns_meta
                    })
        return catalog

    async def execute_federated_query(self, question: str, user_id: str) -> Dict[str, Any]:
        """Orchestrates query planning, parallel subquery executions, and in-memory merges."""
        start_time = time.time()
        self.stats["query_count"] += 1
        
        catalog = await self.get_unified_catalog(user_id)
        if not catalog:
            self.stats["failure_count"] += 1
            return {
                "success": False,
                "error": "No database connections or cached schemas available to query.",
                "execution_plan": {},
                "columns": [],
                "rows": [],
                "warning": []
            }

        # 1. Plan query
        try:
            plan = await query_planner_service.plan_query(question, catalog)
        except Exception as e:
            logger.error(f"Failed to plan query: {e}")
            self.stats["failure_count"] += 1
            return {
                "success": False,
                "error": f"Failed to formulate execution plan: {str(e)}",
                "execution_plan": {},
                "columns": [],
                "rows": [],
                "warning": []
            }

        # 2. Execute subqueries in parallel
        subqueries = plan.get("subqueries", [])
        tasks = []
        warnings = []
        
        async def run_subquery(sub: Dict[str, Any]) -> Tuple[str, pd.DataFrame, Optional[str]]:
            db_conn_id = sub.get("db_connection_id")
            sql = sub.get("sql")
            alias = sub.get("alias")
            
            async with AsyncSessionLocal() as session:
                conn = (await session.execute(
                    select(DatabaseConnection).where(DatabaseConnection.id == db_conn_id, DatabaseConnection.user_id == user_id)
                )).scalar_one_or_none()
                
                if not conn:
                    return alias, pd.DataFrame(), f"Connection '{db_conn_id}' not found."
                
                try:
                    # Execute on engine
                    conn_manager = ConnectionManager()
                    engine = conn_manager.get_engine(conn.id, conn)
                    # We run the pandas query in executor thread since read_sql is synchronous
                    from fastapi.concurrency import run_in_threadpool
                    def fetch():
                        # Use pandas read_sql to load directly into DataFrame
                        with engine.connect() as con:
                            return pd.read_sql(sql, con)
                    
                    df = await run_in_threadpool(fetch)
                    return alias, df, None
                except Exception as ex:
                    logger.error(f"Subquery on connection {db_conn_id} failed: {ex}")
                    return alias, pd.DataFrame(), f"Database '{conn.database_name}' failed: {str(ex)}"

        for sub in subqueries:
            tasks.append(run_subquery(sub))

        results_list = await asyncio.gather(*tasks)
        
        dfs: Dict[str, pd.DataFrame] = {}
        for alias, df, err in results_list:
            if err:
                warnings.append(err)
            else:
                dfs[alias] = df

        # 3. Merge outputs
        merge_ops = plan.get("merge_operations", {})
        op_type = merge_ops.get("type", "single")
        
        join_start = time.time()
        merged_df = pd.DataFrame()
        
        try:
            if not dfs:
                raise ValueError("All database connections returned empty or failed.")

            if op_type == "single" or len(dfs) == 1:
                # Find first non-empty dataframe
                first_alias = list(dfs.keys())[0]
                merged_df = dfs[first_alias]
            
            elif op_type == "join":
                left_alias = merge_ops.get("left_table")
                right_alias = merge_ops.get("right_table")
                join_type = merge_ops.get("join_type", "inner")
                left_on = merge_ops.get("left_on")
                right_on = merge_ops.get("right_on")
                
                if left_alias in dfs and right_alias in dfs:
                    ldf = dfs[left_alias]
                    rdf = dfs[right_alias]
                    
                    # Convert join columns to same type if necessary
                    if left_on in ldf.columns and right_on in rdf.columns:
                        ldf[left_on] = ldf[left_on].astype(str)
                        rdf[right_on] = rdf[right_on].astype(str)
                        
                        merged_df = pd.merge(
                            ldf, rdf, 
                            left_on=left_on, right_on=right_on, 
                            how=join_type,
                            suffixes=(f"_{left_alias}", f"_{right_alias}")
                        )
                    else:
                        raise ValueError(f"Join columns '{left_on}' or '{right_on}' missing in subquery results.")
                else:
                    raise ValueError("One or both join subqueries failed to execute.")
            
            elif op_type in ["union", "union_all"]:
                # Stack dataframes vertical
                merged_df = pd.concat(list(dfs.values()), ignore_index=True)
                if op_type == "union":
                    merged_df = merged_df.drop_duplicates()

            # Projection filters
            proj = merge_ops.get("projection", [])
            if proj and not merged_df.empty:
                # Keep matching columns
                valid_proj = [c for c in proj if c in merged_df.columns]
                if valid_proj:
                    merged_df = merged_df[valid_proj]

            self.stats["total_join_time_ms"] += (time.time() - join_start) * 1000.0
            
        except Exception as e:
            logger.error(f"In-memory merge failed: {e}")
            warnings.append(f"Merge error: {str(e)}")
            self.stats["failure_count"] += 1
            return {
                "success": False,
                "error": f"Failed merging distributed datasets: {str(e)}",
                "execution_plan": plan,
                "columns": [],
                "rows": [],
                "warning": warnings
            }

        latency_ms = (time.time() - start_time) * 1000.0
        self.stats["total_latency_ms"] += latency_ms

        # Final columns and rows conversion
        columns = list(merged_df.columns)
        # Convert date types to string serializable
        for col in columns:
            if pd.api.types.is_datetime64_any_dtype(merged_df[col]):
                merged_df[col] = merged_df[col].dt.strftime("%Y-%m-%d %H:%M:%S")

        # Handle null values for JSON serialization
        merged_df = merged_df.where(pd.notnull(merged_df), None)
        rows = merged_df.values.tolist()

        status = "success"
        try:
            from app.services.monitoring_service import (
                FEDERATION_LATENCY_SECONDS,
                FEDERATION_JOIN_TIME_SECONDS,
                FEDERATION_SUCCESS_TOTAL,
                FEDERATION_PARTIAL_FAILURES_TOTAL
            )
            FEDERATION_LATENCY_SECONDS.observe(latency_ms / 1000.0)
            FEDERATION_JOIN_TIME_SECONDS.observe((time.time() - join_start) / 1000.0)
            if warnings:
                FEDERATION_PARTIAL_FAILURES_TOTAL.inc()
            else:
                FEDERATION_SUCCESS_TOTAL.inc()
        except Exception:
            pass

        if warnings:
            status = "partial_failure"
            self.stats["partial_failure_count"] += 1
        else:
            self.stats["success_count"] += 1

        # 4. Save Query Log Record
        async with AsyncSessionLocal() as session:
            record = FederatedQueryRecord(
                question=question,
                execution_plan=json.dumps(plan),
                status=status,
                error_message=" | ".join(warnings) if warnings else None,
                latency_ms=latency_ms,
                user_id=user_id
            )
            session.add(record)
            await session.commit()

        return {
            "success": True,
            "execution_plan": plan,
            "columns": columns,
            "rows": rows,
            "warning": warnings,
            "latency_ms": latency_ms
        }

    def get_statistics(self) -> Dict[str, Any]:
        """Retrieves performance stats metrics indicators."""
        return self.stats

federation_service = FederationService()
