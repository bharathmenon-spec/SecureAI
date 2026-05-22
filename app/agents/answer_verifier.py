"""Agent 8: Answer Verifier - grounding, leakage, and injection checks."""
from app.agents.prompt_guard import scan_for_injection
from app.schemas import PipelineContext
from app.utils.chunk_utils import keyword_set
from app.utils.redaction_utils import find_pii_leaks


class AnswerVerifierAgent:
    name = "answer_verifier"
    min_grounding = 0.3

    def run(self, ctx: PipelineContext) -> PipelineContext:
        answer = ctx.draft_answer or ""
        issues = []

        evidence_keywords = set()
        for item in ctx.evidence_pack:
            evidence_keywords |= keyword_set(item["text"])
        answer_keywords = keyword_set(answer)
        grounding = (
            len(answer_keywords & evidence_keywords) / len(answer_keywords)
            if answer_keywords
            else 1.0
        )
        if ctx.evidence_pack and grounding < self.min_grounding:
            issues.append("low grounding: answer may contain unsupported claims")

        leaks = find_pii_leaks(answer)
        if leaks:
            issues.append(f"raw PII detected in answer ({len(leaks)} item(s))")

        injection = scan_for_injection(answer)
        if injection["flagged"]:
            issues.append("possible prompt-injection traces in answer")

        if leaks or injection["flagged"]:
            verdict = "fail"
        elif issues:
            verdict = "warn"
        else:
            verdict = "pass"

        ctx.verification = {
            "verdict": verdict,
            "grounding": round(grounding, 3),
            "issues": issues,
            "leak_count": len(leaks),
        }
        ctx.log(self.name, f"verification verdict={verdict}", ctx.verification)
        return ctx
