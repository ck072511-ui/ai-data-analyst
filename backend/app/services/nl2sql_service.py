import logging
import json
import re
import time
from datetime import datetime, date
from decimal import Decimal
from typing import Any, Dict, List, Optional, Tuple

from fastapi import HTTPException
from sqlalchemy import select, text

from app.core.database import AsyncSessionLocal
from app.models.db_connection import DatabaseConnection
from app.models.nl2sql import NL2SQLConversation, NL2SQLQuery
from app.core.connection_manager import ConnectionManager
from app.services.model_manager import model_manager
from app.services.schema_intelligence import SchemaIntelligenceService
from app.services.prompt_builder import PromptBuilder
from app.services.monitoring_service import monitoring_service

logger = logging.getLogger(__name__)


class SQLSafetyLayer:
    @staticmethod
    def inspect_safety(sql: str, schema_data: Dict[str, Any]) -> Tuple[bool, str]:
        # 1. Clean comments
        clean_sql = re.sub(r"--.*", "", sql)
        clean_sql = re.sub(r"/\*.*?\*/", "", clean_sql, flags=re.DOTALL)
        clean_sql = clean_sql.strip()
        sql_upper = clean_sql.upper()

        # 2. Check forbidden modification keywords
        forbidden = [
            r"\bDROP\b", r"\bDELETE\b", r"\bTRUNCATE\b", r"\bALTER\b", 
            r"\bUPDATE\b", r"\bINSERT\b", r"\bCREATE\b", r"\bEXEC\b", 
            r"\bEXECUTE\b", r"\bGRANT\b", r"\bREVOKE\b"
        ]
        for pattern in forbidden:
            if re.search(pattern, sql_upper):
                keyword = pattern.replace(r"\b", "")
                return False, f"Blocked unsafe query structure: contains forbidden keyword '{keyword}'."

        # 3. Allow only SELECT queries
        if not sql_upper.startswith("SELECT") and not sql_upper.startswith("WITH"):
            return False, "Blocked unsafe query: Only SELECT read-only queries are allowed."

        # 4. Check for system table references
        system_patterns = [
            r"\bpg_", r"\binformation_schema\b", r"\bsqlite_", 
            r"\bmysql\b", r"\bperformance_schema\b", r"\bsys\b"
        ]
        sql_lower = clean_sql.lower()
        valid_tables = [t.lower() for t in schema_data.keys()]
        
        # Verify tokens
        for tok in re.findall(r"\b[a-zA-Z0-9_]+\b", sql_lower):
            for sys_pat in ["pg_", "sqlite_", "information_schema", "performance_schema", "mysql", "sys"]:
                if tok.startswith(sys_pat) and tok not in valid_tables:
                    return False, f"Blocked unsafe query: Accessing system schema or catalog table '{tok}' is forbidden."

        # 5. Check for unsafe joins
        if "cross join" in sql_lower:
            return False, "Blocked unsafe query: CROSS JOIN operations are prohibited to protect server performance."

        # 6. Check for SQL Injection patterns
        injection_patterns = [
            r"\bor\s+\d+\s*=\s*\d+", # OR 1=1
            r"\bunion\s+all\b",      # UNION ALL
            r"\bunion\s+select\b",   # UNION SELECT
            r";\s*select\b",         # Multi-statement select
        ]
        for pattern in injection_patterns:
            if re.search(pattern, sql_lower):
                return False, f"Blocked query: Potential SQL injection pattern detected."

        return True, "Safe query"


class NL2SQLService:
    def __init__(self):
        self.conn_manager = ConnectionManager()
        self.schema_service = SchemaIntelligenceService()
        self.prompt_builder = PromptBuilder()

    async def process_query(self, user_id: str, db_connection_id: str, question: str, conversation_id: Optional[str] = None) -> Dict[str, Any]:
        # Fetch connection details
        async with AsyncSessionLocal() as session:
            db_conn = (await session.execute(
                select(DatabaseConnection).where(DatabaseConnection.id == db_connection_id)
            )).scalar_one_or_none()
            
        if not db_conn:
            raise HTTPException(status_code=404, detail="Database connection not found.")
            
        # Discover schema
        schema_data = await self.schema_service.discover_schema(db_connection_id, db_conn)
        schema_context = self.schema_service.build_schema_context(schema_data)
        
        # Retrieve or Create Conversation
        if not conversation_id:
            async with AsyncSessionLocal() as session:
                conv = NL2SQLConversation(
                    user_id=user_id,
                    db_connection_id=db_connection_id,
                    title=question[:40] + "..." if len(question) > 40 else question
                )
                session.add(conv)
                await session.commit()
                conversation_id = conv.id
                
        # History
        history_messages = []
        async with AsyncSessionLocal() as session:
            hist_queries = (await session.execute(
                select(NL2SQLQuery)
                .where(NL2SQLQuery.conversation_id == conversation_id)
                .order_by(NL2SQLQuery.created_at.asc())
            )).scalars().all()
            for h in hist_queries:
                history_messages.append({"role": "user", "content": h.question})
                history_messages.append({"role": "assistant", "content": f"SQL: {h.generated_sql}"})
                
        # Build SQL Prompt
        prompt = self.prompt_builder.build_sql_generation_prompt(
            schema_context=schema_context,
            question=question,
            history=history_messages,
            dialect=db_conn.db_type,
            business_rules=["Limit non-aggregate result sets to 500 rows."]
        )
        
        # Generate
        start_time = time.time()
        try:
            generated_text = await model_manager.generate(prompt=prompt)
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"LLM SQL generation failed: {e}")
            
        # Parse JSON output
        try:
            json_text = generated_text.strip()
            if json_text.startswith("```json"):
                json_text = json_text[7:]
            if json_text.endswith("```"):
                json_text = json_text[:-3]
            json_text = json_text.strip()
            parsed = json.loads(json_text)
            sql = parsed.get("sql", "").strip()
            confidence = parsed.get("confidence_score", 0.8)
            explanation = parsed.get("explanation", "")
        except Exception:
            sql = generated_text.strip()
            confidence = 0.7
            explanation = "SQL query generated."
            
        sql = re.sub(r"```sql\s*", "", sql)
        sql = re.sub(r"```\s*", "", sql)
        sql = sql.strip()
        
        # Safety Check
        is_safe, safety_msg = SQLSafetyLayer.inspect_safety(sql, schema_data)
        if not is_safe:
            monitoring_service.record_nl2sql_query(0.0, 0.0, blocked=True)
            return {
                "success": False,
                "error": f"Safety Violation: {safety_msg}",
                "sql": sql,
                "confidence_score": 0.0,
                "conversation_id": conversation_id
            }
            
        # Validation
        is_valid, validation_msg, cost = await self._validate_sql_details(db_connection_id, db_conn, sql, schema_data)
        if not is_valid:
            monitoring_service.record_nl2sql_query(0.0, 0.0, validation_failed=True)
            return {
                "success": False,
                "error": f"SQL Validation Error: {validation_msg}",
                "sql": sql,
                "confidence_score": 0.0,
                "conversation_id": conversation_id
            }
            
        # Execution
        exec_start = time.time()
        try:
            engine = self.conn_manager.get_engine(db_connection_id, db_conn)
            def run_query():
                with engine.connect() as conn:
                    res = conn.execute(text(sql))
                    columns = list(res.keys())
                    rows = res.fetchall()
                    out = []
                    for row in rows:
                        row_dict = {}
                        for col, val in zip(columns, row):
                            if isinstance(val, (datetime, date)):
                                row_dict[col] = val.isoformat()
                            elif isinstance(val, Decimal):
                                row_dict[col] = float(val)
                            else:
                                row_dict[col] = val
                        out.append(row_dict)
                    return columns, out
            
            from fastapi.concurrency import run_in_threadpool
            columns, results = await run_in_threadpool(run_query)
            latency = time.time() - start_time
            monitoring_service.record_nl2sql_query(latency, confidence)
        except Exception as e:
            monitoring_service.record_nl2sql_query(0.0, 0.0, validation_failed=True)
            return {
                "success": False,
                "error": f"Database Execution Error: {e}",
                "sql": sql,
                "confidence_score": confidence,
                "conversation_id": conversation_id
            }
            
        # Generate explanation dynamically if not populated
        if not explanation or explanation == "SQL query generated.":
            explain_prompt = self.prompt_builder.build_explain_prompt(sql, schema_context)
            try:
                explanation = await model_manager.generate(prompt=explain_prompt)
            except Exception:
                pass
                
        # Optimize query automatically
        optimized_sql = sql
        is_optimized = False
        performance_impact = "No optimization needed."
        explain_plan = await self.get_explain_plan(db_connection_id, db_conn, sql)
        
        opt_prompt = self.prompt_builder.build_optimize_prompt(sql, schema_context, db_conn.db_type, explain_plan)
        try:
            opt_res = await model_manager.generate(prompt=opt_prompt)
            opt_json_text = opt_res.strip()
            if opt_json_text.startswith("```json"):
                opt_json_text = opt_json_text[7:]
            if opt_json_text.endswith("```"):
                opt_json_text = opt_json_text[:-3]
            opt_json_text = opt_json_text.strip()
            opt_parsed = json.loads(opt_json_text)
            
            candidate_opt_sql = opt_parsed.get("optimized_sql", "").strip()
            # Verify candidate safety and validity
            if candidate_opt_sql and candidate_opt_sql != sql:
                cand_safe, _ = SQLSafetyLayer.inspect_safety(candidate_opt_sql, schema_data)
                if cand_safe:
                    cand_valid, _, _ = await self._validate_sql_details(db_connection_id, db_conn, candidate_opt_sql, schema_data)
                    if cand_valid:
                        optimized_sql = candidate_opt_sql
                        is_optimized = True
                        performance_impact = opt_parsed.get("performance_impact", "")
        except Exception:
            pass
            
        # Save history to database
        async with AsyncSessionLocal() as session:
            new_query = NL2SQLQuery(
                conversation_id=conversation_id,
                user_id=user_id,
                question=question,
                generated_sql=sql,
                optimized_sql=optimized_sql,
                explanation=explanation,
                confidence_score=confidence,
                execution_time_ms=int((time.time() - exec_start) * 1000),
                row_count=len(results),
                success=True,
                is_optimized=is_optimized,
                explain_plan=explain_plan
            )
            session.add(new_query)
            await session.commit()
            
        return {
            "success": True,
            "conversation_id": conversation_id,
            "sql": sql,
            "optimized_sql": optimized_sql,
            "is_optimized": is_optimized,
            "performance_impact": performance_impact,
            "confidence_score": confidence,
            "explanation": explanation,
            "columns": columns,
            "data": results,
            "execution_time_ms": int((time.time() - exec_start) * 1000),
            "estimated_cost": cost,
            "explain_plan": explain_plan
        }

    async def stream_query(self, user_id: str, db_connection_id: str, question: str, conversation_id: Optional[str] = None):
        # 1. Fetch connection details
        async with AsyncSessionLocal() as session:
            db_conn = (await session.execute(
                select(DatabaseConnection).where(DatabaseConnection.id == db_connection_id)
            )).scalar_one_or_none()
            
        if not db_conn:
            yield json.dumps({"type": "error", "message": "Database connection not found."})
            return
            
        # 2. Schema Discovery
        yield json.dumps({"type": "status", "status": "Discovering structural schemas..."})
        schema_data = await self.schema_service.discover_schema(db_connection_id, db_conn)
        schema_context = self.schema_service.build_schema_context(schema_data)
        
        # 3. Retrieve or Create Conversation
        if not conversation_id:
            async with AsyncSessionLocal() as session:
                conv = NL2SQLConversation(
                    user_id=user_id,
                    db_connection_id=db_connection_id,
                    title=question[:40] + "..." if len(question) > 40 else question
                )
                session.add(conv)
                await session.commit()
                conversation_id = conv.id
                yield json.dumps({"type": "conversation_id", "conversation_id": conversation_id})
                
        # Fetch conversation history
        history_messages = []
        async with AsyncSessionLocal() as session:
            hist_queries = (await session.execute(
                select(NL2SQLQuery)
                .where(NL2SQLQuery.conversation_id == conversation_id)
                .order_by(NL2SQLQuery.created_at.asc())
            )).scalars().all()
            for h in hist_queries:
                history_messages.append({"role": "user", "content": h.question})
                history_messages.append({"role": "assistant", "content": f"SQL: {h.generated_sql}"})
                
        # 4. Generate SQL Prompt
        prompt = self.prompt_builder.build_sql_generation_prompt(
            schema_context=schema_context,
            question=question,
            history=history_messages,
            dialect=db_conn.db_type,
            business_rules=["Limit non-aggregate result sets to 500 rows."]
        )
        
        yield json.dumps({"type": "status", "status": "Generating SQL query..."})
        
        # Generate stream
        generated_text = ""
        try:
            async for chunk in model_manager.stream_generate(prompt=prompt):
                generated_text += chunk
                yield json.dumps({"type": "sql_token", "token": chunk})
        except Exception as e:
            yield json.dumps({"type": "error", "message": f"SQL generation failed: {e}"})
            return
            
        # Parse the JSON response
        try:
            json_text = generated_text.strip()
            if json_text.startswith("```json"):
                json_text = json_text[7:]
            if json_text.endswith("```"):
                json_text = json_text[:-3]
            json_text = json_text.strip()
            
            parsed = json.loads(json_text)
            sql = parsed.get("sql", "").strip()
            confidence = parsed.get("confidence_score", 0.8)
            explanation = parsed.get("explanation", "")
        except Exception:
            sql = generated_text.strip()
            confidence = 0.7
            explanation = "SQL query generated."
            
        sql = re.sub(r"```sql\s*", "", sql)
        sql = re.sub(r"```\s*", "", sql)
        sql = sql.strip()
        
        yield json.dumps({"type": "sql_complete", "sql": sql, "confidence_score": confidence})
        
        # 5. Safety Layer Check
        is_safe, safety_msg = SQLSafetyLayer.inspect_safety(sql, schema_data)
        if not is_safe:
            monitoring_service.record_nl2sql_query(0.0, 0.0, blocked=True)
            yield json.dumps({"type": "error", "message": f"Safety Violation: {safety_msg}"})
            return
            
        # 6. Syntax and existence validation
        is_valid, validation_msg, cost = await self._validate_sql_details(db_connection_id, db_conn, sql, schema_data)
        if not is_valid:
            monitoring_service.record_nl2sql_query(0.0, 0.0, validation_failed=True)
            yield json.dumps({"type": "error", "message": f"SQL Validation Error: {validation_msg}"})
            return
            
        # 7. Execution Cost & Plan
        yield json.dumps({"type": "status", "status": "Executing SQL query..."})
        
        start_time = time.time()
        # Execute query
        try:
            engine = self.conn_manager.get_engine(db_connection_id, db_conn)
            def run_query():
                with engine.connect() as conn:
                    res = conn.execute(text(sql))
                    columns = list(res.keys())
                    rows = res.fetchall()
                    out = []
                    for row in rows:
                        row_dict = {}
                        for col, val in zip(columns, row):
                            if isinstance(val, (datetime, date)):
                                row_dict[col] = val.isoformat()
                            elif isinstance(val, Decimal):
                                row_dict[col] = float(val)
                            else:
                                row_dict[col] = val
                        out.append(row_dict)
                    return columns, out
            
            from fastapi.concurrency import run_in_threadpool
            columns, results = await run_in_threadpool(run_query)
            latency = time.time() - start_time
            monitoring_service.record_nl2sql_query(latency, confidence)
            
            yield json.dumps({
                "type": "results",
                "columns": columns,
                "row_count": len(results),
                "data": results[:100]
            })
        except Exception as e:
            monitoring_service.record_nl2sql_query(0.0, 0.0, validation_failed=True)
            yield json.dumps({"type": "error", "message": f"Execution Error: {e}"})
            return
            
        # 8. Explanation generation
        yield json.dumps({"type": "status", "status": "Compiling insights..."})
        explain_prompt = self.prompt_builder.build_explain_prompt(sql, schema_context)
        explanation_content = ""
        try:
            async for chunk in model_manager.stream_generate(prompt=explain_prompt):
                explanation_content += chunk
                yield json.dumps({"type": "explain_token", "token": chunk})
        except Exception:
            explanation_content = explanation
            yield json.dumps({"type": "explain_token", "token": explanation})
            
        # 9. Save history to database
        async with AsyncSessionLocal() as session:
            new_query = NL2SQLQuery(
                conversation_id=conversation_id,
                user_id=user_id,
                question=question,
                generated_sql=sql,
                explanation=explanation_content,
                confidence_score=confidence,
                execution_time_ms=int(latency * 1000),
                row_count=len(results),
                success=True
            )
            session.add(new_query)
            await session.commit()
            
        yield json.dumps({"type": "complete", "message": "Query completed successfully."})

    async def explain_sql(self, connection_id: str, sql: str) -> Dict[str, Any]:
        async with AsyncSessionLocal() as session:
            db_conn = (await session.execute(
                select(DatabaseConnection).where(DatabaseConnection.id == connection_id)
            )).scalar_one_or_none()
        if not db_conn:
            raise HTTPException(status_code=404, detail="Database connection not found.")

        schema_data = await self.schema_service.discover_schema(connection_id, db_conn)
        schema_context = self.schema_service.build_schema_context(schema_data)
        
        prompt = self.prompt_builder.build_explain_prompt(sql, schema_context)
        try:
            explanation = await model_manager.generate(prompt=prompt)
            return {"success": True, "explanation": explanation.strip()}
        except Exception as e:
            return {"success": False, "error": str(e)}

    async def validate_sql(self, connection_id: str, sql: str) -> Dict[str, Any]:
        async with AsyncSessionLocal() as session:
            db_conn = (await session.execute(
                select(DatabaseConnection).where(DatabaseConnection.id == connection_id)
            )).scalar_one_or_none()
        if not db_conn:
            raise HTTPException(status_code=404, detail="Database connection not found.")

        schema_data = await self.schema_service.discover_schema(connection_id, db_conn)
        
        is_safe, safety_msg = SQLSafetyLayer.inspect_safety(sql, schema_data)
        if not is_safe:
            return {"success": False, "valid": False, "error": f"Safety Violation: {safety_msg}"}
            
        is_valid, validation_msg, cost = await self._validate_sql_details(connection_id, db_conn, sql, schema_data)
        return {
            "success": True,
            "valid": is_valid,
            "error": None if is_valid else validation_msg,
            "estimated_cost": cost
        }

    async def list_conversations(self, user_id: str) -> List[Dict[str, Any]]:
        async with AsyncSessionLocal() as session:
            res = await session.execute(
                select(NL2SQLConversation)
                .where(NL2SQLConversation.user_id == user_id)
                .order_by(NL2SQLConversation.is_pinned.desc(), NL2SQLConversation.updated_at.desc())
            )
            conversations = res.scalars().all()
            return [
                {
                    "id": c.id,
                    "title": c.title,
                    "is_pinned": c.is_pinned,
                    "db_connection_id": c.db_connection_id,
                    "created_at": c.created_at.isoformat(),
                    "updated_at": c.updated_at.isoformat()
                }
                for c in conversations
            ]

    async def get_conversation_history(self, conversation_id: str, user_id: str) -> List[Dict[str, Any]]:
        async with AsyncSessionLocal() as session:
            res = await session.execute(
                select(NL2SQLQuery)
                .where(NL2SQLQuery.conversation_id == conversation_id, NL2SQLQuery.user_id == user_id)
                .order_by(NL2SQLQuery.created_at.asc())
            )
            queries = res.scalars().all()
            return [
                {
                    "id": q.id,
                    "question": q.question,
                    "generated_sql": q.generated_sql,
                    "optimized_sql": q.optimized_sql,
                    "explanation": q.explanation,
                    "confidence_score": q.confidence_score,
                    "execution_time_ms": q.execution_time_ms,
                    "row_count": q.row_count,
                    "success": q.success,
                    "error_message": q.error_message,
                    "is_optimized": q.is_optimized,
                    "created_at": q.created_at.isoformat()
                }
                for q in queries
            ]

    async def toggle_pin_conversation(self, conversation_id: str, user_id: str) -> Dict[str, Any]:
        async with AsyncSessionLocal() as session:
            conv = (await session.execute(
                select(NL2SQLConversation).where(
                    NL2SQLConversation.id == conversation_id,
                    NL2SQLConversation.user_id == user_id
                )
            )).scalar_one_or_none()
            if not conv:
                raise HTTPException(status_code=404, detail="Conversation not found.")
            
            conv.is_pinned = not conv.is_pinned
            await session.commit()
            return {"success": True, "is_pinned": conv.is_pinned}

    async def delete_conversation(self, conversation_id: str, user_id: str) -> Dict[str, Any]:
        async with AsyncSessionLocal() as session:
            conv = (await session.execute(
                select(NL2SQLConversation).where(
                    NL2SQLConversation.id == conversation_id,
                    NL2SQLConversation.user_id == user_id
                )
            )).scalar_one_or_none()
            if not conv:
                raise HTTPException(status_code=404, detail="Conversation not found.")
            
            await session.delete(conv)
            await session.commit()
            return {"success": True, "message": "Conversation deleted."}

    async def get_explain_plan(self, connection_id: str, db_conn, sql: str) -> str:
        engine = self.conn_manager.get_engine(connection_id, db_conn)
        db_type = db_conn.db_type.lower()
        
        def run_explain():
            with engine.connect() as conn:
                if db_type == "sqlite":
                    res = conn.execute(text(f"EXPLAIN QUERY PLAN {sql}"))
                    rows = res.fetchall()
                    return "\n".join(f"{row[0]} | {row[1]} | {row[2]} | {row[3]}" if len(row) >= 4 else str(row) for row in rows)
                elif db_type == "postgresql":
                    res = conn.execute(text(f"EXPLAIN {sql}"))
                    rows = res.fetchall()
                    return "\n".join(str(row[0]) for row in rows)
                elif db_type == "mysql":
                    res = conn.execute(text(f"EXPLAIN {sql}"))
                    rows = res.fetchall()
                    return "\n".join(str(row) for row in rows)
                return "Explain not supported for this database type."
                
        from fastapi.concurrency import run_in_threadpool
        try:
            return await run_in_threadpool(run_explain)
        except Exception as e:
            return f"Failed to retrieve explain plan: {e}"

    def parse_explain_cost(self, explain_plan: str, db_type: str) -> float:
        db_type = db_type.lower()
        if db_type == "postgresql":
            match = re.search(r"cost=\d+\.\d+\.\.(\d+\.\d+)", explain_plan)
            if match:
                return float(match.group(1))
        # Count operations in SQLite/MySQL query plan
        if "SCAN" in explain_plan:
            scans = explain_plan.count("SCAN")
            searches = explain_plan.count("SEARCH")
            return float(scans * 100 + searches * 10)
        return 50.0

    async def _validate_sql_details(self, connection_id: str, db_conn, sql: str, schema_data: Dict[str, Any]) -> Tuple[bool, str, float]:
        # 1. Table existence check
        sql_lower = sql.lower()
        valid_tables = [t.lower() for t in schema_data.keys()]
        from_join_pattern = r"\b(?:from|join)\s+([a-zA-Z0-9_]+)"
        referenced_tables = re.findall(from_join_pattern, sql_lower)
        for tbl in referenced_tables:
            if tbl not in valid_tables:
                return False, f"Table '{tbl}' does not exist in the database.", 0.0

        # Column existence check
        all_tokens = set(re.findall(r"\b[a-zA-Z0-9_]+\b", sql_lower))
        all_db_columns = {}
        for tbl, tbl_info in schema_data.items():
            for col in tbl_info["columns"]:
                col_name = col["name"].lower()
                if col_name not in all_db_columns:
                    all_db_columns[col_name] = []
                all_db_columns[col_name].append(tbl.lower())

        for token in all_tokens:
            if token in all_db_columns:
                belongs_to_referenced = any(tbl in referenced_tables for tbl in all_db_columns[token])
                if not belongs_to_referenced and referenced_tables:
                    return False, f"Column '{token}' is referenced but its table is not part of the query.", 0.0

        # 2. Syntax validation via explain plan
        explain_plan = await self.get_explain_plan(connection_id, db_conn, sql)
        if explain_plan.startswith("Failed to retrieve explain plan"):
            return False, f"Database Syntax Error: {explain_plan}", 0.0
            
        cost = self.parse_explain_cost(explain_plan, db_conn.db_type)
        return True, "Valid SQL query plan", cost
