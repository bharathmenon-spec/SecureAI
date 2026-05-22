"""Ingestion service - orchestrates the local document processing pipeline.

extract -> detect -> mask/tokenize -> chunk -> embed -> store. Only sanitized
content reaches the vector store and chunk table; raw values are encrypted in
the token map.
"""
import uuid
from typing import List, Optional, Union

from app.core.config import get_settings
from app.core.constants import tier_rank
from app.core.logger import get_logger
from app.core.security import sha256
from app.models.chunk import Chunk
from app.models.document import Document
from app.schemas import UserContext
from app.services.chunking_service import ChunkingService
from app.services.embedding_service import get_embedding_service
from app.services.masking_service import sanitize
from app.storage.token_store import TokenStore
from app.storage.vector_store import get_vector_store
from app.utils.pii_detect import detect_entities
from app.utils.redaction_utils import find_token_markers
from app.utils.text_extract import detect_source_type, extract_text

logger = get_logger(__name__)


class IngestionService:
    def __init__(self, db) -> None:
        self.db = db
        self.settings = get_settings()
        self.embed = get_embedding_service()
        self.vector_store = get_vector_store()
        self.token_store = TokenStore(db)
        self.chunker = ChunkingService()

    def ingest(
        self,
        *,
        filename: str,
        data: Union[bytes, str],
        owner: UserContext,
        sensitivity_level: str,
        allowed_roles: List[str],
        source_type: Optional[str] = None,
        project_names: Optional[List[str]] = None,
    ) -> dict:
        document_id = str(uuid.uuid4())
        doc_short = document_id.split("-")[0]
        source_type = source_type or detect_source_type(filename)

        text = extract_text(data, source_type, filename)
        if not text.strip():
            raise ValueError("No extractable text found in the document")

        content_hash = sha256(text)
        detections = detect_entities(text, project_names)
        masking = sanitize(text, detections, doc_short)

        self.db.add(Document(
            document_id=document_id,
            filename=filename,
            source_type=source_type,
            owner_user_id=owner.user_id,
            sensitivity_level=sensitivity_level,
            content_hash=content_hash,
        ))

        token_tier = {}
        for entry in masking.token_entries:
            self.token_store.create(
                token_label=entry.token_label,
                raw_value=entry.raw_value,
                entity_type=entry.entity_type,
                document_id=document_id,
                allowed_roles=allowed_roles,
                release_policy=entry.release_tier,
            )
            token_tier[entry.token_label] = entry.release_tier

        chunk_dicts = self.chunker.split(masking.sanitized_text)
        texts = [c["text"] for c in chunk_dicts]
        vectors = self.embed.embed(texts) if texts else []

        vector_items = []
        for idx, chunk in enumerate(chunk_dicts):
            chunk_id = f"{doc_short}-c{idx:03d}"
            # A chunk inherits the strictest tier of any token it contains.
            chunk_tier = sensitivity_level
            for marker in find_token_markers(chunk["text"]):
                marker_tier = token_tier.get(marker)
                if marker_tier and tier_rank(marker_tier) > tier_rank(chunk_tier):
                    chunk_tier = marker_tier

            self.db.add(Chunk(
                chunk_id=chunk_id,
                document_id=document_id,
                chunk_text_sanitized=chunk["text"],
                embedding_ref=chunk_id,
                sensitivity_level=chunk_tier,
                allowed_roles=list(allowed_roles),
                source_page=0,
                token_count=chunk["token_count"],
            ))
            vector_items.append((chunk_id, vectors[idx], {
                "document_id": document_id,
                "sensitivity_level": chunk_tier,
                "allowed_roles": list(allowed_roles),
            }))

        if vector_items:
            self.vector_store.add_batch(vector_items)
        self.db.commit()

        logger.info(
            "Ingested document %s (%d chunks, %d tokens)",
            document_id, len(chunk_dicts), len(masking.token_entries),
        )
        return {
            "document_id": document_id,
            "filename": filename,
            "source_type": source_type,
            "sensitivity_level": sensitivity_level,
            "allowed_roles": list(allowed_roles),
            "chunks_indexed": len(chunk_dicts),
            "tokens_created": len(masking.token_entries),
            "sensitive_spans_detected": len(detections),
            "masking_stats": masking.stats,
        }
