"""Agent 4: Policy Agent - RBAC enforcement on retrieved chunks.

Security decisions are made here, not by the LLM. Also screens each chunk's
text for embedded injection content (untrusted-data defense).
"""
from app.agents.prompt_guard import scan_for_injection
from app.schemas import PipelineContext
from app.services.policy_service import DENY, PolicyService


class PolicyAgent:
    name = "policy_agent"

    def __init__(self, db) -> None:
        self.policy = PolicyService(db)

    def run(self, ctx: PipelineContext) -> PipelineContext:
        decisions = []
        approved = []

        for chunk in ctx.reranked:
            verdict = self.policy.evaluate_chunk(ctx.user, chunk)
            injection = scan_for_injection(chunk["text"])

            decisions.append({
                "chunk_id": chunk["chunk_id"],
                "document_id": chunk["document_id"],
                "sensitivity_level": chunk["sensitivity_level"],
                "decision": verdict["decision"],
                "reason": verdict["reason"],
                "injection_in_chunk": injection["flagged"],
            })

            if verdict["decision"] != DENY:
                enriched = dict(chunk)
                enriched["policy_decision"] = verdict["decision"]
                enriched["chunk_injection_flagged"] = injection["flagged"]
                approved.append(enriched)

        ctx.policy_decisions = decisions
        ctx.approved_chunks = approved
        denied = len(decisions) - len(approved)
        ctx.log(
            self.name,
            f"approved {len(approved)} chunk(s), denied {denied}",
            {"decisions": decisions},
        )
        return ctx
