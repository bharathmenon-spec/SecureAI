"""Agent 6: Evidence Reranker - re-scores candidates by relevance fit."""
from app.core.config import get_settings
from app.schemas import PipelineContext
from app.utils.chunk_utils import keyword_overlap


class EvidenceRerankerAgent:
    name = "reranker"

    def __init__(self) -> None:
        self.top_k = get_settings().top_k

    def run(self, ctx: PipelineContext) -> PipelineContext:
        for candidate in ctx.candidates:
            overlap = keyword_overlap(ctx.query, candidate["text"])
            candidate["keyword_overlap"] = round(overlap, 3)
            candidate["rerank_score"] = round(
                0.65 * candidate["score"] + 0.35 * overlap, 4
            )

        ctx.reranked = sorted(
            ctx.candidates, key=lambda c: c["rerank_score"], reverse=True
        )[: self.top_k]
        ctx.log(
            self.name,
            f"reranked to top {len(ctx.reranked)} chunk(s)",
            {"chunk_ids": [c["chunk_id"] for c in ctx.reranked]},
        )
        return ctx
