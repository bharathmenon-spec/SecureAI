"""Retrieval service - semantic search over sanitized chunks only.

Applies a role/sensitivity pre-filter at the vector store. This is a
defense-in-depth layer; the Policy Agent remains the authoritative check.
"""
from typing import List

from app.core.constants import Role, SensitivityTier, tier_rank
from app.models.chunk import Chunk
from app.schemas import UserContext
from app.services.embedding_service import get_embedding_service
from app.storage.vector_store import get_vector_store


class RetrievalService:
    def __init__(self, db) -> None:
        self.db = db
        self.embed = get_embedding_service()
        self.vector_store = get_vector_store()

    def _predicate(self, user: UserContext):
        def check(meta: dict) -> bool:
            if user.role == Role.ADMIN.value:
                return True
            if user.role not in meta.get("allowed_roles", []):
                return False
            chunk_tier = meta.get("sensitivity_level", SensitivityTier.PUBLIC.value)
            return tier_rank(user.clearance_level) >= tier_rank(chunk_tier)

        return check

    def search(self, query: str, user: UserContext, top_k: int) -> List[dict]:
        query_vector = self.embed.embed_one(query)
        hits = self.vector_store.search(
            query_vector, top_k=top_k, predicate=self._predicate(user)
        )

        results: List[dict] = []
        for chunk_id, score, _meta in hits:
            chunk = (
                self.db.query(Chunk)
                .filter(Chunk.chunk_id == chunk_id)
                .first()
            )
            if chunk is None:
                continue
            results.append({
                "chunk_id": chunk.chunk_id,
                "document_id": chunk.document_id,
                "score": score,
                "text": chunk.chunk_text_sanitized,
                "sensitivity_level": chunk.sensitivity_level,
                "allowed_roles": list(chunk.allowed_roles or []),
                "source_page": chunk.source_page,
                "token_count": chunk.token_count,
            })
        return results
