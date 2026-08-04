import logging
from typing import Any, Dict, List, Optional
from app.services.vector_store import BaseVectorStore

logger = logging.getLogger(__name__)

def compute_lexical_score(text: str, query: str) -> float:
    """Calculates keyword match overlap ratio (lexical metric)."""
    q_tokens = set(query.lower().split())
    if not q_tokens:
        return 0.0
    
    text_tokens = set(text.lower().split())
    overlap = len(q_tokens.intersection(text_tokens))
    return overlap / len(q_tokens)


class RetrievalService:
    def __init__(self, vector_store: BaseVectorStore):
        self.vector_store = vector_store

    def retrieve_relevant_chunks(
        self,
        query_text: str,
        query_embedding: List[float],
        top_k: int = 5,
        doc_filter: Optional[Dict[str, Any]] = None,
        alpha: float = 0.7
    ) -> List[Dict[str, Any]]:
        """Retrieves and ranks chunks using semantic-lexical hybrid scoring and deduplication."""
        # 1. Fetch candidates from vector index
        raw_results = self.vector_store.search(
            query_embedding=query_embedding,
            query_text=query_text,
            top_k=top_k * 2,  # Pull more candidates for hybrid scoring and deduplication
            doc_filter=doc_filter
        )

        ranked_results = []
        seen_texts = set()

        for chunk, semantic_score in raw_results:
            text = chunk.get("text_content", "")
            
            # Simple content deduplication
            if text in seen_texts:
                continue
            seen_texts.add(text)

            # Compute lexical keyword overlap
            lexical_score = compute_lexical_score(text, query_text)

            # Hybrid linear combination ranking
            hybrid_score = (alpha * semantic_score) + ((1.0 - alpha) * lexical_score)

            # Keep score bounds safe [0.0, 1.0]
            hybrid_score = max(0.0, min(1.0, hybrid_score))
            
            ranked_results.append({
                "chunk": chunk,
                "score": hybrid_score
            })

        # Sort descending by hybrid rank score
        ranked_results.sort(key=lambda x: x["score"], reverse=True)

        # Retrieve top K matched records
        top_results = []
        for item in ranked_results[:top_k]:
            chunk_data = item["chunk"]
            chunk_data["similarity_score"] = round(item["score"], 4)
            top_results.append(chunk_data)

        logger.info(f"Retrieved {len(top_results)} unique chunks matching query.")
        return top_results
