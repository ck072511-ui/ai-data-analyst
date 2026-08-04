import os
import sys
import pytest
from unittest.mock import AsyncMock, patch, MagicMock

# Adjust path to find backend
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

# Set environment variables for testing
os.environ["DATABASE_URL"] = "sqlite:///./test_analytics.db"
os.environ["SECRET_KEY"] = "test-secret-key-must-be-long-enough-32-chars-at-least"
os.environ["ENVIRONMENT"] = "development"

from app.services.chunking_service import RecursiveCharacterTextSplitter, ChunkingService
from app.services.embedding_service import EmbeddingService
from app.services.vector_store import SimpleMemoryVectorStore
from app.services.retrieval_service import RetrievalService, compute_lexical_score
from app.services.rag_service import RAGService


@pytest.fixture
def anyio_backend():
    return "asyncio"


def test_recursive_chunking_strategy():
    splitter = RecursiveCharacterTextSplitter(chunk_size=50, chunk_overlap=10)
    text = "This is a simple text that needs splitting recursively. It will be broken down."
    
    chunks = splitter.split_text(text)
    assert len(chunks) > 1
    for chunk in chunks:
        assert len(chunk) <= 50


def test_lexical_keyword_overlap_score():
    text = "The quick brown fox jumps over the lazy dog"
    query_1 = "brown fox"
    query_2 = "blue cat"
    
    score_1 = compute_lexical_score(text, query_1)
    score_2 = compute_lexical_score(text, query_2)
    
    assert score_1 > 0.0
    assert score_2 == 0.0


def test_memory_vector_store():
    store = SimpleMemoryVectorStore()
    chunks = [
        {"document_id": "doc_1", "text_content": "Offline databases are very useful.", "page_number": 1},
        {"document_id": "doc_2", "text_content": "Deepmind designs state-of-the-art coding agents.", "page_number": 2}
    ]
    # Simple mock embeddings
    embeddings = [
        [1.0 if i == 0 else 0.0 for i in range(384)],
        [1.0 if i == 1 else 0.0 for i in range(384)]
    ]
    
    store.add_chunks(chunks, embeddings)
    
    # Query matching doc_1
    query_emb = [1.0 if i == 0 else 0.0 for i in range(384)]
    results = store.search(query_embedding=query_emb, query_text="Offline databases", top_k=1)
    
    assert len(results) == 1
    assert results[0][0]["document_id"] == "doc_1"


@pytest.mark.anyio
async def test_rag_query_compilation(anyio_backend):
    rag_service = RAGService()
    
    # Mock database session query results
    mock_conv = MagicMock()
    mock_conv.id = "conv-id"
    mock_conv.title = "Document Q&A"
    
    mock_doc = MagicMock()
    mock_doc.filename = "manual.txt"
    mock_doc.created_at = MagicMock()
    
    mock_chunk = {
        "text_content": "Local models run completely offline on business servers.",
        "page_number": 1,
        "meta_info": {"filename": "manual.txt"},
        "similarity_score": 0.95
    }

    with patch("app.services.rag_service.AsyncSessionLocal") as mock_session_class, \
         patch("app.services.rag_service.model_manager.generate", new_callable=AsyncMock) as mock_generate, \
         patch.object(rag_service.retrieval_service, "retrieve_relevant_chunks") as mock_retrieve, \
         patch.object(rag_service, "retrieve_data_dictionary_context") as mock_dict:
        
        mock_generate.return_value = "Offline models are fully local and private."
        mock_retrieve.return_value = [mock_chunk]
        mock_dict.return_value = "Business Glossary context"
        
        mock_session = AsyncMock()
        mock_session_class.return_value.__aenter__.return_value = mock_session
        
        # Setup db query returns
        mock_execute_res = MagicMock()
        mock_execute_res.scalars.return_value.all.return_value = []  # no history
        mock_execute_res.scalar_one_or_none.return_value = mock_conv
        mock_session.execute.return_value = mock_execute_res

        res = await rag_service.query_rag(
            conversation_id="conv-id",
            question="Do offline models run locally?",
            user_id="user-id"
        )

        assert "answer" in res
        assert "citations" in res
        assert res["answer"] == "Offline models are fully local and private."
        assert len(res["citations"]) == 1
        assert res["citations"][0]["filename"] == "manual.txt"
