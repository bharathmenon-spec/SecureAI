"""Multi-agent query orchestration pipeline.

All agents run in-process inside the monolith. The Audit Agent always runs,
even when an upstream agent fails, so every request is recorded.
"""
import uuid

from app.agents.answer_composer import AnswerComposerAgent
from app.agents.answer_verifier import AnswerVerifierAgent
from app.agents.audit_agent import AuditAgent
from app.agents.context_compressor import ContextCompressionAgent
from app.agents.intent_router import IntentRouterAgent
from app.agents.policy_agent import PolicyAgent
from app.agents.prompt_guard import PromptGuardAgent
from app.agents.query_planner import QueryPlannerAgent
from app.agents.redaction_agent import RedactionAgent
from app.agents.reranker import EvidenceRerankerAgent
from app.agents.retriever import RetrieverAgent
from app.core.logger import get_logger
from app.schemas import PipelineContext, UserContext

logger = get_logger(__name__)


def run_query_pipeline(db, user: UserContext, query: str) -> PipelineContext:
    """Execute the full query pipeline and return the populated context."""
    ctx = PipelineContext(request_id=str(uuid.uuid4()), user=user, query=query)

    try:
        # Intent Router -> Query Planner -> Prompt Guard -> Retriever ->
        # Reranker -> Policy -> Context Compression -> Answer Composer ->
        # Answer Verifier -> Redaction / De-tokenization.
        IntentRouterAgent().run(ctx)
        QueryPlannerAgent().run(ctx)
        PromptGuardAgent().run(ctx)
        RetrieverAgent(db).run(ctx)
        EvidenceRerankerAgent().run(ctx)
        PolicyAgent(db).run(ctx)
        ContextCompressionAgent().run(ctx)
        AnswerComposerAgent().run(ctx)
        AnswerVerifierAgent().run(ctx)
        RedactionAgent(db).run(ctx)
    except Exception as exc:  # keep the request auditable on failure
        logger.exception("pipeline failure for request %s", ctx.request_id)
        ctx.status = "error"
        ctx.log("pipeline", f"unhandled error: {exc}")
        if not ctx.final_answer:
            ctx.final_answer = (
                "An internal error occurred while processing this request."
            )

    try:
        AuditAgent(db).run(ctx)
    except Exception as exc:
        logger.error("audit write failed for %s: %s", ctx.request_id, exc)

    return ctx
