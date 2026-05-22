"""Agent 5: Context Compression - builds a compact evidence pack for Gemini."""
from app.schemas import PipelineContext
from app.utils.chunk_utils import keyword_set, split_sentences


class ContextCompressionAgent:
    name = "context_compressor"
    max_sentences = 14
    fallback_chunks = 4

    def run(self, ctx: PipelineContext) -> PipelineContext:
        query_keywords = keyword_set(ctx.query)

        scored = []
        for chunk in ctx.approved_chunks:
            for sentence in split_sentences(chunk["text"]):
                overlap = len(query_keywords & keyword_set(sentence))
                if overlap > 0:
                    scored.append((overlap, chunk["chunk_id"], sentence))

        scored.sort(key=lambda item: item[0], reverse=True)

        pack = []
        seen = set()
        for _overlap, chunk_id, sentence in scored:
            norm = sentence.lower().strip()
            if norm in seen:
                continue
            seen.add(norm)
            pack.append({"chunk_id": chunk_id, "text": sentence})
            if len(pack) >= self.max_sentences:
                break

        if not pack and ctx.approved_chunks:
            pack = [
                {"chunk_id": c["chunk_id"], "text": c["text"]}
                for c in ctx.approved_chunks[: self.fallback_chunks]
            ]

        ctx.evidence_pack = pack
        ctx.log(
            self.name,
            f"compressed evidence to {len(pack)} item(s)",
            {"evidence_chunk_ids": sorted({p['chunk_id'] for p in pack})},
        )
        return ctx
