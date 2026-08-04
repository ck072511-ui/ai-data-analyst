import logging
from typing import Any, Dict
from app.services.rag_service import RAGService

logger = logging.getLogger(__name__)

class RAGAgent:
    def __init__(self):
        self.rag_service = RAGService()

    async def execute_task(self, question: str, shared_memory: Dict[str, Any]) -> Dict[str, Any]:
        """Queries the vector index to extract cited contexts from docs and glossaries."""
        logger.info(f"RAG Agent searching documents matching: {question}")
        
        try:
            # Generate query embedding
            query_emb = self.rag_service.embedding_service.get_embedding(question)
            
            # Fetch general chunks
            general_chunks = self.rag_service.retrieval_service.retrieve_relevant_chunks(
                query_text=question,
                query_embedding=query_emb,
                top_k=3,
                doc_filter={"doc_type": "general"},
                alpha=0.7
            )
            
            # Fetch glossary / dictionary contexts
            data_dict_context = await self.rag_service.retrieve_data_dictionary_context(question, query_emb)

            citations = []
            for c in general_chunks:
                citations.append({
                    "filename": c["meta_info"]["filename"],
                    "page_number": c["page_number"],
                    "text_content": c["text_content"]
                })

            return {
                "citations": citations,
                "dictionary_context": data_dict_context,
                "confidence": 0.85
            }
        except Exception as e:
            logger.warning(f"RAG Agent failed context retrieval: {e}")
            return {
                "citations": [],
                "dictionary_context": "",
                "confidence": 0.0
            }
