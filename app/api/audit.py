"""Audit API - retrieve the full trace for a processed request."""
from fastapi import APIRouter, Depends, HTTPException

from app.api.deps import get_current_user
from app.core.constants import Role
from app.models.audit import AuditRecord
from app.schemas import UserContext
from app.storage.db import get_db

router = APIRouter()

_AUDIT_ROLES = {Role.ADMIN.value, Role.SECURITY_ANALYST.value}


@router.get("/{request_id}")
def get_audit(
    request_id: str,
    user: UserContext = Depends(get_current_user),
    db=Depends(get_db),
):
    if user.role not in _AUDIT_ROLES:
        raise HTTPException(
            status_code=403,
            detail="Audit access requires Admin or Security Analyst role",
        )

    record = (
        db.query(AuditRecord)
        .filter(AuditRecord.request_id == request_id)
        .first()
    )
    if record is None:
        raise HTTPException(
            status_code=404,
            detail=f"No audit record for request '{request_id}'",
        )

    return {
        "request_id": record.request_id,
        "user_id": record.user_id,
        "query_text": record.query_text,
        "retrieved_chunk_ids": record.retrieved_chunk_ids,
        "policy_decision": record.policy_decision,
        "redaction_applied": record.redaction_applied,
        "final_response_status": record.final_response_status,
        "timestamp": record.timestamp.isoformat() if record.timestamp else None,
        "trace": record.trace,
    }
