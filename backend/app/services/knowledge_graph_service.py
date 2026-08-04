import json
import logging
import uuid
from datetime import datetime
from typing import Any, Dict, List, Set, Optional

from sqlalchemy import select, delete
from app.core.database import AsyncSessionLocal
from app.models.dataset import UserDataset
from app.models.db_connection import DatabaseConnection
from app.models.rag import UserDocument
from app.models.report import GeneratedReport
from app.models.workflow import Workflow
from app.models.knowledge import KnowledgeEntity, KnowledgeRelationship
from app.models.stream import StreamConfig
from app.services.semantic_layer_service import semantic_layer_service

logger = logging.getLogger(__name__)

class KnowledgeGraphService:
    async def build_graph(self, user_id: str) -> Dict[str, Any]:
        """Automatically discovers entities and relationships across datasets, SQL database engines, documents, and workflows."""
        start_time = datetime.utcnow()
        logger.info(f"Triggering automated offline Knowledge Graph build for user {user_id}...")

        # 1. Rebuild or merge: For simplicity, we drop existing entries and build clean states
        async with AsyncSessionLocal() as session:
            await session.execute(delete(KnowledgeRelationship).where(KnowledgeRelationship.user_id == user_id))
            await session.execute(delete(KnowledgeEntity).where(KnowledgeEntity.user_id == user_id))
            await session.commit()

        # Storage for newly discovered entities to map relationships
        # entity_type_key -> entity_name/id -> entity_db_record
        discovered_entities: Dict[str, Dict[str, KnowledgeEntity]] = {
            "dataset": {},
            "table": {},
            "column": {},
            "document": {},
            "workflow": {},
            "report": {},
            "business_term": {}
        }

        async with AsyncSessionLocal() as session:
            # 2. Discover business terms from Semantic Layer
            glossary = semantic_layer_service.get_business_glossary()
            for term, term_info in glossary.items():
                ent = KnowledgeEntity(
                    id=str(uuid.uuid4()),
                    name=term,
                    entity_type="Business Term",
                    properties=json.dumps({
                        "description": term_info.get("description", ""),
                        "category": term_info.get("category", "General"),
                        "synonyms": term_info.get("synonyms", [])
                    }),
                    user_id=user_id
                )
                session.add(ent)
                discovered_entities["business_term"][term.lower()] = ent

            # Discover metrics and KPIs
            kpis = semantic_layer_service.get_kpi_catalog()
            for kpi, kpi_info in kpis.items():
                ent = KnowledgeEntity(
                    id=str(uuid.uuid4()),
                    name=kpi,
                    entity_type="KPI",
                    properties=json.dumps({
                        "description": kpi_info.get("description", ""),
                        "formula": kpi_info.get("formula", ""),
                        "dimensions": kpi_info.get("dimensions", [])
                    }),
                    user_id=user_id
                )
                session.add(ent)
                discovered_entities["business_term"][kpi.lower()] = ent # map metrics under term matching

            await session.commit()

            # 3. Discover Datasets, Tables and Columns
            datasets = (await session.execute(
                select(UserDataset).where(UserDataset.user_id == user_id)
            )).scalars().all()

            for ds in datasets:
                # Create Dataset entity
                ds_ent = KnowledgeEntity(
                    id=str(uuid.uuid4()),
                    name=ds.filename,
                    entity_type="Dataset",
                    properties=json.dumps({
                        "filename": ds.filename,
                        "table_name": ds.table_name,
                        "row_count": ds.row_count,
                        "col_count": ds.col_count
                    }),
                    source_id=ds.id,
                    user_id=user_id
                )
                session.add(ds_ent)
                discovered_entities["dataset"][ds.id] = ds_ent

                # Create Table entity
                tb_ent = KnowledgeEntity(
                    id=str(uuid.uuid4()),
                    name=ds.table_name,
                    entity_type="Table",
                    properties=json.dumps({
                        "table_name": ds.table_name,
                        "source": "uploaded_dataset"
                    }),
                    source_id=ds.table_name,
                    user_id=user_id
                )
                session.add(tb_ent)
                discovered_entities["table"][ds.table_name.lower()] = tb_ent

                # Column entities
                cols = ds.columns or []
                for col in cols:
                    col_key = f"{ds.table_name}.{col}".lower()
                    col_ent = KnowledgeEntity(
                        id=str(uuid.uuid4()),
                        name=col,
                        entity_type="Column",
                        properties=json.dumps({
                            "table_name": ds.table_name,
                            "column_name": col,
                            "data_type": ds.schema_info.get(col, {}).get("dtype", "unknown") if ds.schema_info else "unknown"
                        }),
                        source_id=col_key,
                        user_id=user_id
                    )
                    session.add(col_ent)
                    discovered_entities["column"][col_key] = col_ent

            # 4. Discover connected remote Database Connections tables and schemas
            db_conns = (await session.execute(
                select(DatabaseConnection).where(DatabaseConnection.user_id == user_id)
            )).scalars().all()

            for conn in db_conns:
                # Tables schema caching
                from app.core.connection_manager import connection_manager
                # Attempt to retrieve cached tables schema
                try:
                    schema_cache = connection_manager.schema_cache.get(conn.id, {})
                except Exception:
                    schema_cache = {}

                for tb_name, cols in schema_cache.items():
                    tb_ent = KnowledgeEntity(
                        id=str(uuid.uuid4()),
                        name=tb_name,
                        entity_type="Table",
                        properties=json.dumps({
                            "table_name": tb_name,
                            "connection_id": conn.id,
                            "database_name": conn.database_name,
                            "source": "remote_database"
                        }),
                        source_id=tb_name,
                        user_id=user_id
                    )
                    session.add(tb_ent)
                    discovered_entities["table"][tb_name.lower()] = tb_ent

                    for col_meta in cols:
                        col_name = col_meta.get("name")
                        col_key = f"{tb_name}.{col_name}".lower()
                        col_ent = KnowledgeEntity(
                            id=str(uuid.uuid4()),
                            name=col_name,
                            entity_type="Column",
                            properties=json.dumps({
                                "table_name": tb_name,
                                "column_name": col_name,
                                "data_type": col_meta.get("type", "unknown")
                            }),
                            source_id=col_key,
                            user_id=user_id
                        )
                        session.add(col_ent)
                        discovered_entities["column"][col_key] = col_ent

            # 5. Discover Documents
            docs = (await session.execute(
                select(UserDocument).where(UserDocument.user_id == user_id)
            )).scalars().all()

            for doc in docs:
                doc_ent = KnowledgeEntity(
                    id=str(uuid.uuid4()),
                    name=doc.filename,
                    entity_type="Document",
                    properties=json.dumps({
                        "filename": doc.filename,
                        "file_path": doc.file_path,
                        "file_size": doc.file_size,
                        "doc_type": doc.doc_type
                    }),
                    source_id=doc.id,
                    user_id=user_id
                )
                session.add(doc_ent)
                discovered_entities["document"][doc.id] = doc_ent

            # 6. Discover Workflows
            wfs = (await session.execute(
                select(Workflow).where(Workflow.user_id == user_id)
            )).scalars().all()

            for wf in wfs:
                wf_ent = KnowledgeEntity(
                    id=str(uuid.uuid4()),
                    name=wf.name,
                    entity_type="Workflow",
                    properties=json.dumps({
                        "workflow_name": wf.name,
                        "description": wf.description
                    }),
                    source_id=wf.id,
                    user_id=user_id
                )
                session.add(wf_ent)
                discovered_entities["workflow"][wf.id] = wf_ent

            # 7. Discover Generated Reports
            reps = (await session.execute(
                select(GeneratedReport).where(GeneratedReport.user_id == user_id)
            )).scalars().all()

            for rep in reps:
                rep_ent = KnowledgeEntity(
                    id=str(uuid.uuid4()),
                    name=rep.title,
                    entity_type="Report",
                    properties=json.dumps({
                        "title": rep.title,
                        "report_type": rep.report_type,
                        "file_format": rep.file_format,
                        "status": rep.status
                    }),
                    source_id=rep.id,
                    user_id=user_id
                )
                session.add(rep_ent)
                discovered_entities["report"][rep.id] = rep_ent

            await session.commit()

            # 8. Infer Relationships and dependencies
            # Lineage mappings (Column belongs to Table, Table belongs to Dataset)
            for col_key, col_ent in discovered_entities["column"].items():
                tb_name = col_key.split(".")[0]
                if tb_name in discovered_entities["table"]:
                    tb_ent = discovered_entities["table"][tb_name]
                    # Link Column -> Table
                    rel = KnowledgeRelationship(
                        id=str(uuid.uuid4()),
                        source_id=col_ent.id,
                        target_id=tb_ent.id,
                        relationship_type="lineage",
                        confidence=1.0,
                        properties=json.dumps({"description": "Column belongs to Table"}),
                        user_id=user_id
                    )
                    session.add(rel)

            for ds_id, ds_ent in discovered_entities["dataset"].items():
                # Read properties to get table_name
                props = json.loads(ds_ent.properties)
                tb_name = props.get("table_name", "").lower()
                if tb_name in discovered_entities["table"]:
                    tb_ent = discovered_entities["table"][tb_name]
                    # Link Table -> Dataset
                    rel = KnowledgeRelationship(
                        id=str(uuid.uuid4()),
                        source_id=tb_ent.id,
                        target_id=ds_ent.id,
                        relationship_type="lineage",
                        confidence=1.0,
                        properties=json.dumps({"description": "Table represents Dataset version upload"}),
                        user_id=user_id
                    )
                    session.add(rel)

            # Foreign Keys inference: Match identical column names across tables
            columns_by_name: Dict[str, List[KnowledgeEntity]] = {}
            for col_key, col_ent in discovered_entities["column"].items():
                col_name = col_ent.name.lower()
                if col_name not in ["id", "name", "status", "created_at", "updated_at", "type", "value", "date"]:
                    if col_name not in columns_by_name:
                        columns_by_name[col_name] = []
                    columns_by_name[col_name].append(col_ent)

            for col_name, ents in columns_by_name.items():
                if len(ents) > 1:
                    for i in range(len(ents)):
                        for j in range(i + 1, len(ents)):
                            rel = KnowledgeRelationship(
                                id=str(uuid.uuid4()),
                                source_id=ents[i].id,
                                target_id=ents[j].id,
                                relationship_type="foreign_key",
                                confidence=0.85,
                                properties=json.dumps({"description": f"Inferred matching column name reference '{col_name}'"}),
                                user_id=user_id
                            )
                            session.add(rel)

            # Business Glossary mapping & Semantic Aliases
            for term_name, term_ent in discovered_entities["business_term"].items():
                # Get synonyms from term metadata
                props = json.loads(term_ent.properties)
                synonyms = [s.lower() for s in props.get("synonyms", [])]
                synonyms.append(term_name.lower())

                for col_key, col_ent in discovered_entities["column"].items():
                    col_name = col_ent.name.lower()
                    if col_name in synonyms:
                        rel = KnowledgeRelationship(
                            id=str(uuid.uuid4()),
                            source_id=col_ent.id,
                            target_id=term_ent.id,
                            relationship_type="glossary_mapping",
                            confidence=0.90,
                            properties=json.dumps({"description": "Column maps directly to business term synonym"}),
                            user_id=user_id
                        )
                        session.add(rel)

            # Workflow dependencies: Parse SQL / dataset links in workflows definition
            for wf_id, wf_ent in discovered_entities["workflow"].items():
                wf_record = (await session.execute(
                    select(Workflow).where(Workflow.id == wf_id)
                )).scalar_one_or_none()

                if wf_record:
                    try:
                        definition = json.loads(wf_record.definition)
                        nodes = definition.get("nodes", [])
                        for node in nodes:
                            config = node.get("config", {})
                            dataset_id = config.get("dataset_id")
                            if dataset_id and dataset_id in discovered_entities["dataset"]:
                                ds_ent = discovered_entities["dataset"][dataset_id]
                                rel = KnowledgeRelationship(
                                    id=str(uuid.uuid4()),
                                    source_id=wf_ent.id,
                                    target_id=ds_ent.id,
                                    relationship_type="workflow_dependency",
                                    confidence=1.0,
                                    properties=json.dumps({"description": f"Workflow reads dataset '{ds_ent.name}'"}),
                                    user_id=user_id
                                )
                                session.add(rel)

                            query_sql = config.get("query_sql", "").lower()
                            if query_sql:
                                for tb_name, tb_ent in discovered_entities["table"].items():
                                    if tb_name in query_sql:
                                        rel = KnowledgeRelationship(
                                            id=str(uuid.uuid4()),
                                            source_id=wf_ent.id,
                                            target_id=tb_ent.id,
                                            relationship_type="workflow_dependency",
                                            confidence=0.95,
                                            properties=json.dumps({"description": f"Workflow query references table '{tb_name}'"}),
                                            user_id=user_id
                                        )
                                        session.add(rel)
                    except Exception as e:
                        logger.error(f"Failed to infer workflow relationship dependencies: {e}")

            # Report dependencies: Map execution ids
            for rep_id, rep_ent in discovered_entities["report"].items():
                rep_record = (await session.execute(
                    select(GeneratedReport).where(GeneratedReport.id == rep_id)
                )).scalar_one_or_none()

                if rep_record and rep_record.execution_id:
                    # Link to multi-agent task or workflow runs if matches source ID
                    for wf_id, wf_ent in discovered_entities["workflow"].items():
                        rel = KnowledgeRelationship(
                            id=str(uuid.uuid4()),
                            source_id=rep_ent.id,
                            target_id=wf_ent.id,
                            relationship_type="report_dependency",
                            confidence=0.90,
                            properties=json.dumps({"description": "Report compiles workflow analytical output results"}),
                            user_id=user_id
                        )
                        session.add(rel)

            await session.commit()

        duration = (datetime.utcnow() - start_time).total_seconds()
        logger.info(f"Knowledge Graph build finished in {duration}s.")
        return {"success": True, "duration_seconds": duration}

    async def get_lineage(self, entity_id: str, user_id: str) -> List[Dict[str, Any]]:
        """Traverses upstream edges to find lineage coordinates of a column/table."""
        paths = []
        visited = set()
        
        async def traverse(curr_id: str, depth: int):
            if curr_id in visited or depth > 4:
                return
            visited.add(curr_id)

            async with AsyncSessionLocal() as session:
                # Find relationships where curr_id is the source (Column -> Table -> Dataset)
                rels = (await session.execute(
                    select(KnowledgeRelationship)
                    .where(KnowledgeRelationship.source_id == curr_id, KnowledgeRelationship.user_id == user_id)
                )).scalars().all()

                for r in rels:
                    target = (await session.execute(
                        select(KnowledgeEntity)
                        .where(KnowledgeEntity.id == r.target_id, KnowledgeEntity.user_id == user_id)
                    )).scalar_one_or_none()

                    if target:
                        paths.append({
                            "source_id": curr_id,
                            "target_id": target.id,
                            "target_name": target.name,
                            "target_type": target.entity_type,
                            "relationship_type": r.relationship_type,
                            "confidence": r.confidence,
                            "depth": depth
                        })
                        await traverse(target.id, depth + 1)

        await traverse(entity_id, 1)
        return paths

    async def get_impact(self, entity_id: str, user_id: str) -> List[Dict[str, Any]]:
        """Traverses downstream connections to trace what depends on this entity (Table -> Report/Workflow)."""
        paths = []
        visited = set()

        async def traverse(curr_id: str, depth: int):
            if curr_id in visited or depth > 4:
                return
            visited.add(curr_id)

            async with AsyncSessionLocal() as session:
                # Find relationships where curr_id is the target (Column <- Table, Table <- Workflow etc.)
                rels = (await session.execute(
                    select(KnowledgeRelationship)
                    .where(KnowledgeRelationship.target_id == curr_id, KnowledgeRelationship.user_id == user_id)
                )).scalars().all()

                for r in rels:
                    source = (await session.execute(
                        select(KnowledgeEntity)
                        .where(KnowledgeEntity.id == r.source_id, KnowledgeEntity.user_id == user_id)
                    )).scalar_one_or_none()

                    if source:
                        paths.append({
                            "target_id": curr_id,
                            "source_id": source.id,
                            "source_name": source.name,
                            "source_type": source.entity_type,
                            "relationship_type": r.relationship_type,
                            "confidence": r.confidence,
                            "depth": depth
                        })
                        await traverse(source.id, depth + 1)

        await traverse(entity_id, 1)
        return paths

    async def register_stream_incrementally(self, stream: StreamConfig, user_id: str):
        """Saves stream configuration & schema elements dynamically into the Knowledge Graph."""
        async with AsyncSessionLocal() as session:
            # 1. Create or update Stream entity
            stream_source_id = f"stream_{stream.id}"
            stream_ent = (await session.execute(
                select(KnowledgeEntity).where(KnowledgeEntity.source_id == stream_source_id, KnowledgeEntity.user_id == user_id)
            )).scalar_one_or_none()

            properties_data = {
                "name": stream.name,
                "source_type": stream.source_type,
                "window_type": stream.window_type,
                "window_size_sec": stream.window_size_sec,
            }

            if not stream_ent:
                stream_ent = KnowledgeEntity(
                    id=str(uuid.uuid4()),
                    name=stream.name,
                    entity_type="Dataset",  # reuse Dataset category for visual listing/compatibility
                    properties=json.dumps(properties_data),
                    source_id=stream_source_id,
                    user_id=user_id
                )
                session.add(stream_ent)
                await session.flush()  # get ID
            else:
                stream_ent.properties = json.dumps(properties_data)
                stream_ent.name = stream.name
                session.add(stream_ent)

            # 2. Register schema columns if present
            if stream.schema_definition:
                try:
                    schema = json.loads(stream.schema_definition)
                except Exception:
                    schema = {}
                
                for col_name, col_type in schema.items():
                    col_source_id = f"col_{stream.id}_{col_name}"
                    col_ent = (await session.execute(
                        select(KnowledgeEntity).where(KnowledgeEntity.source_id == col_source_id, KnowledgeEntity.user_id == user_id)
                    )).scalar_one_or_none()

                    if not col_ent:
                        col_ent = KnowledgeEntity(
                            id=str(uuid.uuid4()),
                            name=col_name,
                            entity_type="Column",
                            properties=json.dumps({
                                "column_name": col_name,
                                "data_type": col_type,
                                "stream_id": stream.id
                            }),
                            source_id=col_source_id,
                            user_id=user_id
                        )
                        session.add(col_ent)
                        await session.flush()
                        
                        # Add Lineage Relationship (Column -> Stream)
                        rel = KnowledgeRelationship(
                            id=str(uuid.uuid4()),
                            source_id=col_ent.id,
                            target_id=stream_ent.id,
                            relationship_type="lineage",
                            confidence=1.0,
                            properties=json.dumps({"description": "Stream schema column reference"}),
                            user_id=user_id
                        )
                        session.add(rel)
            
            await session.commit()

    async def register_derived_metric_incrementally(self, stream_id: str, metric_name: str, formula: str):
        """Links computed window metrics dynamically back to their source streams in the KG."""
        async with AsyncSessionLocal() as session:
            # Resolve stream entity
            stream_source_id = f"stream_{stream_id}"
            stream_ent = (await session.execute(
                select(KnowledgeEntity).where(KnowledgeEntity.source_id == stream_source_id)
            )).scalar_one_or_none()
            
            if not stream_ent:
                return  # Stream not registered yet
                
            user_id = stream_ent.user_id

            # Create or update KPI / Metric entity
            metric_source_id = f"metric_{stream_id}_{metric_name}"
            metric_ent = (await session.execute(
                select(KnowledgeEntity).where(KnowledgeEntity.source_id == metric_source_id, KnowledgeEntity.user_id == user_id)
            )).scalar_one_or_none()

            properties_data = {
                "description": f"Continuous real-time aggregate metric: {metric_name}",
                "formula": formula,
                "stream_id": stream_id
            }

            if not metric_ent:
                metric_ent = KnowledgeEntity(
                    id=str(uuid.uuid4()),
                    name=metric_name,
                    entity_type="KPI",
                    properties=json.dumps(properties_data),
                    source_id=metric_source_id,
                    user_id=user_id
                )
                session.add(metric_ent)
                await session.flush()

                # Add KPI Dependency Relationship (KPI -> Stream)
                rel = KnowledgeRelationship(
                    id=str(uuid.uuid4()),
                    source_id=metric_ent.id,
                    target_id=stream_ent.id,
                    relationship_type="kpi_dependency",
                    confidence=1.0,
                    properties=json.dumps({"description": "KPI derived from live stream"}),
                    user_id=user_id
                )
                session.add(rel)
            else:
                metric_ent.properties = json.dumps(properties_data)
                session.add(metric_ent)

            await session.commit()


knowledge_graph_service = KnowledgeGraphService()

