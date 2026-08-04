import logging
import time
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple

from sqlalchemy import select, desc
from app.core.database import AsyncSessionLocal
from app.models.rag import UserDocument, DocumentChunk, RAGConversation, RAGQuery
from app.services.embedding_service import EmbeddingService
from app.services.vector_store import VectorStoreFactory
from app.services.retrieval_service import RetrievalService
from app.services.model_manager import model_manager
from app.services.monitoring_service import monitoring_service

logger = logging.getLogger(__name__)


class RAGService:
    def __init__(self):
        self.embedding_service = EmbeddingService()
        self.vector_store = VectorStoreFactory.get_vector_store("faiss")
        self.retrieval_service = RetrievalService(self.vector_store)

    async def ingest_document(self, file_path: str, filename: str, doc_type: str, user_id: str) -> str:
        """Extracts, chunks, embeds, and indexes a business document."""
        from app.services.document_ingestion import DocumentIngestionService
        from app.services.chunking_service import ChunkingService

        ext = filename.split(".")[-1].lower() if "." in filename else ""
        
        # 1. Validate file
        if not DocumentIngestionService.validate_file(file_path, ext):
            raise ValueError(f"Corrupted or invalid document file: {filename}")

        # 2. Extract pages/text content
        pages = DocumentIngestionService.extract_text(file_path, ext)
        if not pages:
            raise ValueError(f"Document contains no readable text: {filename}")

        # 3. Create document record in DB
        async with AsyncSessionLocal() as session:
            doc = UserDocument(
                user_id=user_id,
                filename=filename,
                file_path=file_path,
                file_size=os.path.getsize(file_path) if os.path.exists(file_path) else 0,
                mime_type=f"application/{ext}",
                doc_type=doc_type
            )
            session.add(doc)
            await session.commit()
            await session.refresh(doc)
            doc_id = doc.id

        # 4. Generate text chunks
        chunks = ChunkingService.chunk_document(
            document_id=doc_id,
            filename=filename,
            source_path=file_path,
            pages=pages,
            chunk_size=800,
            chunk_overlap=150
        )

        if not chunks:
            raise ValueError("No chunks created from text.")

        # 5. Extract vector embeddings
        texts = [c["text_content"] for c in chunks]
        embeddings = self.embedding_service.get_embeddings(texts)

        # 6. Save chunks in vector index and SQLite DB
        self.vector_store.add_chunks(chunks, embeddings)

        async with AsyncSessionLocal() as session:
            for idx, c in enumerate(chunks):
                db_chunk = DocumentChunk(
                    document_id=doc_id,
                    chunk_index=c["chunk_index"],
                    text_content=c["text_content"],
                    page_number=c["page_number"],
                    meta_info=c["meta_info"]
                )
                session.add(db_chunk)
            await session.commit()

        logger.info(f"Successfully indexed document: {filename} ({doc_id})")
        return doc_id

    async def delete_document(self, document_id: str) -> None:
        """Deletes database documents, chunks, and index vectors."""
        self.vector_store.delete_document(document_id)

        async with AsyncSessionLocal() as session:
            doc = (await session.execute(
                select(UserDocument).where(UserDocument.id == document_id)
            )).scalar_one_or_none()

            if doc:
                await session.delete(doc)
                await session.commit()
                logger.info(f"Deleted document from database: {document_id}")

    async def retrieve_data_dictionary_context(self, query: str, query_emb: List[float]) -> str:
        """Implicitly retrieves business glossaries, schema metadata, and rules to ground instructions."""
        dictionary_chunks = self.retrieval_service.retrieve_relevant_chunks(
            query_text=query,
            query_embedding=query_emb,
            top_k=3,
            doc_filter={"doc_type": "data_dictionary"},
            alpha=0.6
        )
        if not dictionary_chunks:
            return ""
        
        ctx_list = []
        for c in dictionary_chunks:
            ctx_list.append(f"Dictionary Chunk: {c['text_content']}")
        return "\n".join(ctx_list)

    async def query_rag(
        self,
        conversation_id: str,
        question: str,
        user_id: str,
        top_k: int = 4
    ) -> Dict[str, Any]:
        """Resolves questions using hybrid search, citation lists, and conversation histories."""
        start_time = time.time()
        
        # 1. Embed query
        emb_start = time.time()
        query_emb = self.embedding_service.get_embedding(question)
        emb_latency = time.time() - emb_start

        # 2. Retrieve General context
        ret_start = time.time()
        general_chunks = self.retrieval_service.retrieve_relevant_chunks(
            query_text=question,
            query_embedding=query_emb,
            top_k=top_k,
            doc_filter={"doc_type": "general"},
            alpha=0.7
        )
        ret_latency = time.time() - ret_start

        # 3. Retrieve Data Dictionary context (Feature 8)
        data_dict_context = await self.retrieve_data_dictionary_context(question, query_emb)

        # 4. Fetch conversation memory (Feature 7)
        async with AsyncSessionLocal() as session:
            history_records = (await session.execute(
                select(RAGQuery)
                .where(RAGQuery.conversation_id == conversation_id)
                .order_by(desc(RAGQuery.created_at))
                .limit(4)  # context window
            )).scalars().all()

        chat_history = ""
        for prev in reversed(history_records):
            chat_history += f"User: {prev.question}\nAssistant: {prev.answer}\n"

        # Knowledge Graph & Glossary context retrieval
        kg_context_str = ""
        try:
            import json
            from app.services.semantic_layer_service import semantic_layer_service
            from app.models.knowledge import KnowledgeEntity, KnowledgeRelationship
            
            words = question.lower().split()
            resolved_terms = []
            for w in words:
                w_clean = "".join(c for c in w if c.isalnum())
                if w_clean:
                    syns = semantic_layer_service.resolve_synonyms(w_clean)
                    if syns:
                        resolved_terms.extend(syns)
                    resolved_terms.append(w_clean)
            
            if resolved_terms:
                async with AsyncSessionLocal() as session:
                    # Query entities matching resolved glossary terms
                    matching_entities = (await session.execute(
                        select(KnowledgeEntity)
                        .where(KnowledgeEntity.name.in_(resolved_terms))
                    )).scalars().all()
                    
                    kg_lines = []
                    for ent in matching_entities:
                        kg_lines.append(f"Entity: {ent.name} (Type: {ent.entity_type})")
                        props = json.loads(ent.properties) if ent.properties else {}
                        if "description" in props:
                            kg_lines.append(f"  Description: {props['description']}")
                        
                        # Find relationships
                        rels = (await session.execute(
                            select(KnowledgeRelationship)
                            .where((KnowledgeRelationship.source_id == ent.id) | (KnowledgeRelationship.target_id == ent.id))
                            .limit(3)
                        )).scalars().all()
                        
                        for r in rels:
                            other_id = r.target_id if r.source_id == ent.id else r.source_id
                            other = (await session.execute(
                                select(KnowledgeEntity).where(KnowledgeEntity.id == other_id)
                            )).scalar_one_or_none()
                            if other:
                                kg_lines.append(f"  Related to: {other.name} ({other.entity_type}) via {r.relationship_type}")
                    if kg_lines:
                        kg_context_str = "\n".join(kg_lines)
        except Exception as e:
            logger.error(f"Failed to query knowledge graph context for RAG: {e}")

        # 5. Build prompt
        context_str = "\n".join([f"Source: {c['meta_info']['filename']} (Page {c['page_number']})\nContent: {c['text_content']}" for c in general_chunks])

        prompt = (
            "You are an offline Enterprise RAG Assistant. Answer the question using the context and business rules provided.\n"
            "If the context contains the answer, use it and explain clearly. If not, state that the context lacks details.\n\n"
        )
        if kg_context_str:
            prompt += f"=== KNOWLEDGE GRAPH & SEMANTIC CONTEXT ===\n{kg_context_str}\n\n"
        if data_dict_context:
            prompt += f"=== BUSINESS GLOSSARY & DATA DICTIONARY ===\n{data_dict_context}\n\n"
        
        if chat_history:
            prompt += f"=== CONVERSATION HISTORY ===\n{chat_history}\n\n"
            
        prompt += f"=== DOCUMENT CONTEXT ===\n{context_str}\n\n"
        prompt += f"=== USER QUESTION ===\n{question}\n\nAnswer:"

        # 6. Inference
        gen_start = time.time()
        try:
            answer = await model_manager.generate(prompt=prompt)
            gen_latency = time.time() - gen_start
            success = True
        except Exception as e:
            logger.error(f"RAG LLM generation failed: {e}")
            answer = "Error: Local offline generation failed."
            gen_latency = 0.0
            success = False

        # 7. Construct citations & confidence
        citations = []
        scores = []
        for c in general_chunks:
            citations.append({
                "filename": c["meta_info"]["filename"],
                "page_number": c["page_number"],
                "text_content": c["text_content"]
            })
            scores.append(c.get("similarity_score", 0.5))

        confidence = float(sum(scores) / len(scores)) if scores else 0.5
        
        # Save query in DB
        async with AsyncSessionLocal() as session:
            db_query = RAGQuery(
                conversation_id=conversation_id,
                user_id=user_id,
                question=question,
                answer=answer,
                citations=citations,
                confidence_score=confidence
            )
            session.add(db_query)
            
            # Update updated_at timestamp on conversation
            conv = (await session.execute(
                select(RAGConversation).where(RAGConversation.id == conversation_id)
            )).scalar_one_or_none()
            if conv:
                conv.updated_at = datetime.utcnow()
                session.add(conv)
            
            await session.commit()

        # Telemetry updates (Feature 11)
        monitoring_service.record_rag_query(
            emb_latency=emb_latency,
            ret_latency=ret_latency,
            gen_latency=gen_latency,
            confidence=confidence,
            chunks_cnt=len(general_chunks),
            success=success
        )

        return {
            "answer": answer,
            "citations": citations,
            "confidence_score": confidence
        }

    async def list_documents(self) -> List[Dict[str, Any]]:
        """Returns document registers."""
        async with AsyncSessionLocal() as session:
            docs = (await session.execute(
                select(UserDocument).order_by(desc(UserDocument.created_at))
            )).scalars().all()
            return [
                {
                    "id": d.id,
                    "filename": d.filename,
                    "file_size": d.file_size,
                    "doc_type": d.doc_type,
                    "created_at": d.created_at.isoformat()
                }
                for d in docs
            ]

    async def get_or_create_conversation(self, user_id: str, conversation_id: Optional[str] = None) -> RAGConversation:
        """Retrieves or registers conversations thread."""
        async with AsyncSessionLocal() as session:
            if conversation_id:
                conv = (await session.execute(
                    select(RAGConversation).where(
                        RAGConversation.id == conversation_id,
                        RAGConversation.user_id == user_id
                    )
                )).scalar_one_or_none()
                if conv:
                    return conv

            new_conv = RAGConversation(user_id=user_id)
            session.add(new_conv)
            await session.commit()
            await session.refresh(new_conv)
            return new_conv

    async def list_conversations(self, user_id: str) -> List[Dict[str, Any]]:
        """Lists chat histories."""
        async with AsyncSessionLocal() as session:
            convs = (await session.execute(
                select(RAGConversation)
                .where(RAGConversation.user_id == user_id)
                .order_by(desc(RAGConversation.is_pinned), desc(RAGConversation.updated_at))
            )).scalars().all()

            return [
                {
                    "id": c.id,
                    "title": c.title,
                    "is_pinned": c.is_pinned,
                    "updated_at": c.updated_at.isoformat()
                }
                for c in convs
            ]
import os
