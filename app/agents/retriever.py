"""Agent 3: Retriever - semantic search over sanitized chunks."""
from app.core.config import get_settings
from app.schemas import PipelineContext
from app.services.retrieval_service import RetrievalService


class RetrieverAgent:
    name = "retriever"

    def __init__(self, db) -> None:
        self.service = RetrievalService(db)
        self.top_k = get_settings().top_k

    def run(self, ctx: PipelineContext) -> PipelineContext:
        merged = {}
        for subquery in ctx.subqueries:
            for candidate in self.service.search(subquery, ctx.user, self.top_k):
                chunk_id = candidate["chunk_id"]
                if (
                    chunk_id not in merged
                    or candidate["score"] > merged[chunk_id]["score"]
                ):
                    merged[chunk_id] = candidate

        ctx.candidates = sorted(
            merged.values(), key=lambda c: c["score"], reverse=True
        )
        ctx.log(
            self.name,
            f"retrieved {len(ctx.candidates)} candidate chunk(s)",
            {"chunk_ids": [c["chunk_id"] for c in ctx.candidates]},
        )
        return ctx
