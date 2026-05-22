"""Agent 9: Redaction / De-tokenization - final output shaping.

Restores only policy-permitted tokens, keeps the rest masked, and scrubs any
residual raw PII before the answer leaves the system.
"""
from app.schemas import PipelineContext
from app.services.detokenization_service import DetokenizationService
from app.utils.redaction_utils import scrub_pii


class RedactionAgent:
    name = "redaction_agent"

    def __init__(self, db) -> None:
        self.detok = DetokenizationService(db)

    def run(self, ctx: PipelineContext) -> PipelineContext:
        suspicious = (
            ctx.risk_level == "high"
            or bool(ctx.guard.get("flagged"))
            or ctx.verification.get("verdict") == "fail"
        )

        restored, detok_log = self.detok.restore(
            ctx.draft_answer, ctx.user, suspicious
        )
        cleaned, leaks = scrub_pii(restored)

        ctx.final_answer = cleaned
        ctx.detok_log = detok_log

        released = sum(1 for e in detok_log if e["action"] == "released")
        masked = len(detok_log) - released

        if ctx.status == "ok":
            if leaks:
                ctx.status = "redacted"
            elif masked:
                ctx.status = "partially_redacted"

        ctx.log(
            self.name,
            f"detok released={released}, masked={masked}, "
            f"leaks_scrubbed={len(leaks)}, suspicious={suspicious}",
            {"detok_log": detok_log},
        )
        return ctx
