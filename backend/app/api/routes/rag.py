import os
import shutil
import re
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, File, UploadFile, Form
from pydantic import BaseModel
from sqlalchemy import select

from app.core.security import get_current_user
from app.services.permission_service import require_permission
from app.services.rag_service import RAGService

router = APIRouter(prefix="/rag", tags=["RAG Document Assistant"])
rag_service = RAGService()

# Ensure storage path exists
UPLOAD_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "..", "data", "uploads", "rag_documents"))
os.makedirs(UPLOAD_DIR, exist_ok=True)


class QueryRequest(BaseModel):
    question: str
    conversation_id: Optional[str] = None


class PinRequest(BaseModel):
    conversation_id: str
    is_pinned: bool


@router.post("/upload", dependencies=[Depends(require_permission("upload"))])
async def upload_document(
    file: UploadFile = File(...),
    doc_type: str = Form("general"),  # "general" or "data_dictionary"
    current_user: dict = Depends(get_current_user)
):
    """Saves business files or data dictionaries, parses text, and populates index vectors."""
    # Sanitize file name
    raw_filename = os.path.basename(file.filename)
    filename = re.sub(r"[^a-zA-Z0-9_.-]", "_", raw_filename)
    
    ext = filename.split(".")[-1].lower() if "." in filename else ""
    if ext not in ["pdf", "docx", "txt", "md", "markdown", "csv"]:
        raise HTTPException(status_code=400, detail="Document format not supported.")

    file_path = os.path.join(UPLOAD_DIR, filename)
    try:
        with open(file_path, "wb") as f:
            shutil.copyfileobj(file.file, f)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to save file: {e}")

    try:
        doc_id = await rag_service.ingest_document(
            file_path=file_path,
            filename=filename,
            doc_type=doc_type,
            user_id=current_user["id"]
        )
        return {"success": True, "document_id": doc_id, "filename": filename}
    except Exception as e:
        # Cleanup uploaded file on parsing failures
        if os.path.exists(file_path):
            os.remove(file_path)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/documents", dependencies=[Depends(require_permission("view"))])
async def list_documents(current_user: dict = Depends(get_current_user)):
    """Retrieve all indexed documents."""
    return await rag_service.list_documents()


@router.delete("/document/{document_id}", dependencies=[Depends(require_permission("upload"))])
async def delete_document(document_id: str, current_user: dict = Depends(get_current_user)):
    """Remove target documents and clean chunk indices."""
    await rag_service.delete_document(document_id)
    return {"success": True, "message": "Document deleted successfully."}


@router.post("/query", dependencies=[Depends(require_permission("view"))])
async def query_rag_engine(
    request: QueryRequest,
    current_user: dict = Depends(get_current_user)
):
    """Executes RAG semantic searches and returns citation references and model outputs."""
    # Resolve or create active conversation thread
    conv = await rag_service.get_or_create_conversation(
        user_id=current_user["id"],
        conversation_id=request.conversation_id
    )
    
    res = await rag_service.query_rag(
        conversation_id=conv.id,
        question=request.question,
        user_id=current_user["id"]
    )
    
    res["conversation_id"] = conv.id
    return res


@router.get("/history", dependencies=[Depends(require_permission("view"))])
async def get_conversations_history(current_user: dict = Depends(get_current_user)):
    """Returns multi-turn conversations list."""
    return await rag_service.list_conversations(user_id=current_user["id"])


@router.post("/conversation/pin", dependencies=[Depends(require_permission("view"))])
async def pin_conversation(
    request: PinRequest,
    current_user: dict = Depends(get_current_user)
):
    """Toggles pinning on chat history items."""
    from app.core.database import AsyncSessionLocal
    from app.models.rag import RAGConversation
    
    async with AsyncSessionLocal() as session:
        conv = (await session.execute(
            select(RAGConversation).where(
                RAGConversation.id == request.conversation_id,
                RAGConversation.user_id == current_user["id"]
            )
        )).scalar_one_or_none()
        if not conv:
            raise HTTPException(status_code=404, detail="Conversation thread not found.")
        
        conv.is_pinned = request.is_pinned
        session.add(conv)
        await session.commit()
    
    return {"success": True}
