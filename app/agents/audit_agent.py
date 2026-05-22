"""Audit Agent - persists a full trace of every request for compliance review."""
from app.core.logger import get_logger
from app.models.audit import AuditRecord
from app.schemas import PipelineContext

logger = get_logger(__name__)


class AuditAgent:
    name = "audit_agent"

    def __init__(self, db) -> None:
        self.db = db

    def run(self, ctx: PipelineContext) -> PipelineContext:
        record = AuditRecord(
            request_id=ctx.request_id,
            user_id=ctx.user.user_id,
            query_text=ctx.query,
            retrieved_chunk_ids=[c["chunk_id"] for c in ctx.reranked],
            policy_decision={
                "chunk_decisions": ctx.policy_decisions,
                "guard": ctx.guard,
                "verification": ctx.verification,
                "detokenization": ctx.detok_log,
            },
            redaction_applied=bool(ctx.detok_log)
            or ctx.status in ("redacted", "partially_redacted"),
            final_response_status=ctx.status,
            trace=ctx.trace,
        )
        self.db.add(record)
        self.db.commit()
        logger.info(
            "Audit recorded request=%s status=%s", ctx.request_id, ctx.status
        )
        ctx.log(self.name, "audit trace persisted")
        return ctx
