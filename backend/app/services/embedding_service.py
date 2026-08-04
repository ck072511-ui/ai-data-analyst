import logging
from abc import ABC, abstractmethod
from typing import List

logger = logging.getLogger(__name__)

class BaseEmbeddingProvider(ABC):
    @abstractmethod
    def get_embedding(self, text: str) -> List[float]:
        pass

    @abstractmethod
    def get_embeddings(self, texts: List[str]) -> List[List[float]]:
        pass


class SentenceTransformersEmbeddingProvider(BaseEmbeddingProvider):
    def __init__(self, model_name: str = "all-MiniLM-L6-v2"):
        self.model_name = model_name
        self.model = None
        try:
            from sentence_transformers import SentenceTransformer
            # Automatically downloads or loads from local cache folder
            self.model = SentenceTransformer(model_name)
            logger.info(f"Loaded SentenceTransformers model: {model_name}")
        except Exception as e:
            logger.warning(f"Could not load SentenceTransformers model ({e}). Fallback to local TF-IDF matcher.")

    def get_embedding(self, text: str) -> List[float]:
        if self.model:
            return self.model.encode([text])[0].tolist()
        return self._fallback_vector(text)

    def get_embeddings(self, texts: List[str]) -> List[List[float]]:
        if self.model:
            return self.model.encode(texts).tolist()
        return [self._fallback_vector(t) for t in texts]

    def _fallback_vector(self, text: str) -> List[float]:
        # Simple ASCII frequency representation for fallback vector matching (dimension 384)
        vector = [0.0] * 384
        words = text.lower().split()
        for word in words:
            # Hash words to match vector space
            idx = hash(word) % 384
            vector[idx] += 1.0
        return vector


class EmbeddingService:
    def __init__(self, provider: str = "sentence-transformers", model_name: str = "all-MiniLM-L6-v2"):
        if provider == "sentence-transformers":
            self.provider = SentenceTransformersEmbeddingProvider(model_name)
        else:
            raise ValueError(f"Unknown embedding provider: {provider}")

    def get_embedding(self, text: str) -> List[float]:
        return self.provider.get_embedding(text)

    def get_embeddings(self, texts: List[str]) -> List[List[float]]:
        return self.provider.get_embeddings(texts)
