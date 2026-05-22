"""Shared API dependencies - user resolution and role gating."""
from fastapi import Depends, Header, HTTPException
from sqlalchemy import or_

from app.core.constants import Role
from app.models.user import User
from app.schemas import UserContext
from app.storage.db import get_db


def get_current_user(
    x_user_id: str = Header(..., alias="X-User-Id"),
    db=Depends(get_db),
) -> UserContext:
    """Resolve the caller from the X-User-Id header (user_id or username)."""
    user = (
        db.query(User)
        .filter(or_(User.user_id == x_user_id, User.username == x_user_id))
        .first()
    )
    if user is None:
        raise HTTPException(status_code=401, detail=f"Unknown user '{x_user_id}'")
    return UserContext(
        user_id=user.user_id,
        username=user.username,
        role=user.role,
        department=user.department,
        clearance_level=user.clearance_level,
    )


def require_admin(
    user: UserContext = Depends(get_current_user),
) -> UserContext:
    if user.role != Role.ADMIN.value:
        raise HTTPException(status_code=403, detail="Admin role required")
    return user
