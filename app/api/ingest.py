"""Ingestion API - upload a document or raw text for local processing."""
from typing import Optional

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile

from app.api.deps import get_current_user
from app.core.constants import ALL_ROLES, Role, TIER_ORDER
from app.schemas import UserContext
from app.services.ingestion_service import IngestionService
from app.services.policy_service import default_roles_for_tier
from app.storage.db import get_db
from app.utils.text_extract import detect_source_type

router = APIRouter()


@router.post("/document")
async def ingest_document(
    file: Optional[UploadFile] = File(None),
    raw_text: Optional[str] = Form(None),
    filename: Optional[str] = Form(None),
    sensitivity_level: str = Form("INTERNAL"),
    allowed_roles: Optional[str] = Form(None),
    user: UserContext = Depends(get_current_user),
    db=Depends(get_db),
):
    """Ingest a document. Provide a multipart ``file`` or a ``raw_text`` field.

    ``allowed_roles`` is an optional comma-separated role allow-list; if omitted
    a sensible default is derived from ``sensitivity_level``.
    """
    if user.role == Role.GUEST.value:
        raise HTTPException(status_code=403,
                            detail="Guests cannot ingest documents")

    if sensitivity_level not in TIER_ORDER:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid sensitivity_level. Use one of {list(TIER_ORDER)}",
        )

    if file is not None:
        data = await file.read()
        resolved_name = filename or file.filename or "upload"
        source_type = detect_source_type(resolved_name)
    elif raw_text:
        data = raw_text
        resolved_name = filename or "raw_text.txt"
        source_type = "txt"
    else:
        raise HTTPException(status_code=400,
                            detail="Provide either a file or raw_text")

    if allowed_roles:
        roles = [r.strip() for r in allowed_roles.split(",") if r.strip()]
        invalid = [r for r in roles if r not in ALL_ROLES]
        if invalid:
            raise HTTPException(status_code=400,
                                detail=f"Unknown roles: {invalid}")
    else:
        roles = default_roles_for_tier(sensitivity_level, user.role)

    try:
        return IngestionService(db).ingest(
            filename=resolved_name,
            data=data,
            owner=user,
            sensitivity_level=sensitivity_level,
            allowed_roles=roles,
            source_type=source_type,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
