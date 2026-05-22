"""Chunking service - splits sanitized text into retrieval chunks."""
from typing import List

from app.core.config import get_settings
from app.utils.chunk_utils import chunk_text


class ChunkingService:
    def __init__(self) -> None:
        settings = get_settings()
        self.chunk_size = settings.chunk_size
        self.overlap = settings.chunk_overlap

    def split(self, sanitized_text: str) -> List[dict]:
        chunks = chunk_text(sanitized_text, self.chunk_size, self.overlap)
        if not chunks and sanitized_text.strip():
            # Degenerate input with no sentence boundaries - keep as one chunk.
            chunks = [{
                "text": sanitized_text.strip(),
                "token_count": len(sanitized_text.split()),
            }]
        return chunks
