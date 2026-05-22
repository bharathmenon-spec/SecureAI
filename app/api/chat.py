"""Chat API - submit a question through the multi-agent query pipeline."""
from fastapi import APIRouter, Depends

from app.agents.pipeline import run_query_pipeline
from app.api.deps import get_current_user
from app.schemas import QueryRequest, UserContext
from app.storage.db import get_db

router = APIRouter()


@router.post("/query")
def chat_query(
    body: QueryRequest,
    user: UserContext = Depends(get_current_user),
    db=Depends(get_db),
):
    ctx = run_query_pipeline(db, user, body.query)
    return {
        "request_id": ctx.request_id,
        "status": ctx.status,
        "answer": ctx.final_answer,
        "intent": ctx.intent,
        "risk_level": ctx.risk_level,
        "subqueries": ctx.subqueries,
        "injection_guard": ctx.guard,
        "retrieved_chunks": [
            {
                "chunk_id": d["chunk_id"],
                "document_id": d["document_id"],
                "sensitivity_level": d["sensitivity_level"],
                "decision": d["decision"],
                "reason": d["reason"],
                "injection_in_chunk": d["injection_in_chunk"],
            }
            for d in ctx.policy_decisions
        ],
        "evidence_items": len(ctx.evidence_pack),
        "verification": ctx.verification,
        "detokenization": ctx.detok_log,
        "trace": ctx.trace,
    }
