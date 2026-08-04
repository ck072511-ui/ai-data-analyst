import logging
from typing import Any, Dict, List

logger = logging.getLogger(__name__)

class RecursiveCharacterTextSplitter:
    def __init__(self, chunk_size: int = 1000, chunk_overlap: int = 200, separators: List[str] = None):
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap
        self.separators = separators or ["\n\n", "\n", " ", ""]

    def split_text(self, text: str) -> List[str]:
        """Recursively splits a text into chunks based on character lengths and separators."""
        if len(text) <= self.chunk_size:
            return [text]

        # Choose the first separator that appears in text
        separator = self.separators[-1]
        for sep in self.separators:
            if sep in text:
                separator = sep
                break

        splits = text.split(separator) if separator else list(text)
        chunks = []
        current_chunk = ""

        for split in splits:
            if len(split) > self.chunk_size:
                # If a single split block exceeds chunk size, split it recursively
                if current_chunk:
                    chunks.append(current_chunk.strip())
                    current_chunk = ""
                chunks.extend(self.split_text(split))
                continue

            # Check length with separator
            potential_len = len(current_chunk) + (len(separator) if current_chunk else 0) + len(split)
            if potential_len <= self.chunk_size:
                current_chunk = (current_chunk + separator + split) if current_chunk else split
            else:
                if current_chunk:
                    chunks.append(current_chunk.strip())
                
                # Setup chunk overlap by cutting from end of current split chunk
                overlap_idx = max(0, len(current_chunk) - self.chunk_overlap)
                overlap_text = current_chunk[overlap_idx:]
                current_chunk = (overlap_text + separator + split) if overlap_text else split

        if current_chunk:
            chunks.append(current_chunk.strip())

        return chunks


class ChunkingService:
    @staticmethod
    def chunk_document(
        document_id: str,
        filename: str,
        source_path: str,
        pages: List[tuple],
        chunk_size: int = 1000,
        chunk_overlap: int = 200
    ) -> List[Dict[str, Any]]:
        """Processes extracted pages, chunks them, and formats metadata payloads."""
        splitter = RecursiveCharacterTextSplitter(chunk_size=chunk_size, chunk_overlap=chunk_overlap)
        chunk_records = []
        chunk_index = 0

        for page_num, text in pages:
            if not text.strip():
                continue
            
            sub_chunks = splitter.split_text(text)
            for sub_text in sub_chunks:
                if not sub_text.strip():
                    continue
                
                chunk_records.append({
                    "document_id": document_id,
                    "chunk_index": chunk_index,
                    "text_content": sub_text,
                    "page_number": page_num,
                    "meta_info": {
                        "filename": filename,
                        "source_path": source_path,
                        "page_number": page_num,
                        "document_id": document_id
                    }
                })
                chunk_index += 1

        logger.info(f"Split document {filename} into {len(chunk_records)} chunks.")
        return chunk_records
