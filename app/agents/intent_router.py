"""Agent 1: Intent Router - classifies the request and sets a risk level."""
from app.schemas import PipelineContext

_SUMMARY_KW = {"summarize", "summary", "overview", "recap", "digest"}
_ANALYTICAL_KW = {
    "compare", "analyze", "analyse", "explain", "why", "evaluate",
    "difference", "differences", "versus", "relationship", "tradeoff",
}
_SENSITIVE_KW = [
    "salary", "compensation", "password", "secret", "ssn", "api key",
    "account number", "contract", "personal", "email address",
    "phone number", "confidential", "unmask", "raw value",
]


class IntentRouterAgent:
    name = "intent_router"

    def run(self, ctx: PipelineContext) -> PipelineContext:
        query = ctx.query.lower()
        words = set(query.replace("?", " ").split())

        if _SUMMARY_KW & words:
            intent = "summarization"
        elif _ANALYTICAL_KW & words:
            intent = "analytical"
        else:
            intent = "factual"

        sensitive = any(kw in query for kw in _SENSITIVE_KW)
        ctx.intent = intent
        ctx.risk_level = "medium" if sensitive else "low"
        ctx.routing = "full_pipeline"
        ctx.log(
            self.name,
            f"classified intent={intent}, risk={ctx.risk_level}",
            {"intent": intent, "sensitive_terms": sensitive},
        )
        return ctx
