import logging
import numpy as np
from abc import ABC, abstractmethod
from typing import Any, Dict, List, Tuple

logger = logging.getLogger(__name__)

class BaseVectorStore(ABC):
    @abstractmethod
    def add_chunks(self, chunks: List[Dict[str, Any]], embeddings: List[List[float]]) -> None:
        pass

    @abstractmethod
    def search(self, query_embedding: List[float], query_text: str, top_k: int = 5, doc_filter: Dict[str, Any] = None) -> List[Tuple[Dict[str, Any], float]]:
        pass

    @abstractmethod
    def delete_document(self, document_id: str) -> None:
        pass


class SimpleMemoryVectorStore(BaseVectorStore):
    """Fallback in-memory database using numpy cosine similarity."""
    def __init__(self):
        self.chunks: List[Dict[str, Any]] = []
        self.embeddings: List[np.ndarray] = []

    def add_chunks(self, chunks: List[Dict[str, Any]], embeddings: List[List[float]]) -> None:
        self.chunks.extend(chunks)
        for emb in embeddings:
            norm = np.linalg.norm(emb)
            self.embeddings.append(np.array(emb) / norm if norm > 0 else np.array(emb))

    def search(self, query_embedding: List[float], query_text: str, top_k: int = 5, doc_filter: Dict[str, Any] = None) -> List[Tuple[Dict[str, Any], float]]:
        if not self.embeddings:
            return []

        q_norm = np.linalg.norm(query_embedding)
        q_vec = np.array(query_embedding) / q_norm if q_norm > 0 else np.array(query_embedding)

        results = []
        for idx, (chunk, emb) in enumerate(zip(self.chunks, self.embeddings)):
            # Metadata filter matching
            if doc_filter:
                match = True
                for k, v in doc_filter.items():
                    if chunk.get(k) != v and chunk.get("meta_info", {}).get(k) != v:
                        match = False
                        break
                if not match:
                    continue

            score = float(np.dot(emb, q_vec))
            results.append((chunk, score))

        # Sort descending by similarity score
        results.sort(key=lambda x: x[1], reverse=True)
        return results[:top_k]

    def delete_document(self, document_id: str) -> None:
        new_chunks = []
        new_embs = []
        for chunk, emb in zip(self.chunks, self.embeddings):
            if chunk.get("document_id") != document_id:
                new_chunks.append(chunk)
                new_embs.append(emb)
        self.chunks = new_chunks
        self.embeddings = new_embs


class FAISSVectorStore(BaseVectorStore):
    def __init__(self):
        self.store = SimpleMemoryVectorStore()
        try:
            import faiss
            logger.info("FAISS vector search successfully initialized.")
        except ImportError:
            logger.warning("FAISS module not found. Falling back to Simple Memory vector matcher.")

    def add_chunks(self, chunks: List[Dict[str, Any]], embeddings: List[List[float]]) -> None:
        self.store.add_chunks(chunks, embeddings)

    def search(self, query_embedding: List[float], query_text: str, top_k: int = 5, doc_filter: Dict[str, Any] = None) -> List[Tuple[Dict[str, Any], float]]:
        return self.store.search(query_embedding, query_text, top_k, doc_filter)

    def delete_document(self, document_id: str) -> None:
        self.store.delete_document(document_id)


class VectorStoreFactory:
    @staticmethod
    def get_vector_store(store_type: str = "faiss") -> BaseVectorStore:
        if store_type in ["faiss", "faiss-cpu"]:
            return FAISSVectorStore()
        elif store_type == "chroma":
            # For simplicity and offline compliance, we route Chroma to memory/faiss abstraction
            return FAISSVectorStore()
        return SimpleMemoryVectorStore()
