"""Admin API - user role assignment and policy rule management."""
import uuid

from fastapi import APIRouter, Depends, HTTPException

from app.api.deps import require_admin
from app.core.constants import ALL_ROLES, ROLE_CLEARANCE, TIER_ORDER
from app.models.policy import PolicyRule
from app.models.user import User
from app.schemas import PolicyRuleRequest, UserContext, UserRoleRequest
from app.storage.db import get_db

router = APIRouter()


@router.post("/user-role")
def set_user_role(
    body: UserRoleRequest,
    admin: UserContext = Depends(require_admin),
    db=Depends(get_db),
):
    """Create a user or update their role, department, and clearance."""
    if body.role not in ALL_ROLES:
        raise HTTPException(status_code=400,
                            detail=f"Unknown role. Use one of {ALL_ROLES}")

    clearance = body.clearance_level or ROLE_CLEARANCE[body.role]
    if clearance not in TIER_ORDER:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid clearance_level. Use one of {list(TIER_ORDER)}",
        )

    user = db.query(User).filter(User.username == body.username).first()
    created = user is None
    if user is None:
        user = User(user_id=body.user_id or body.username, username=body.username)
        db.add(user)
    user.role = body.role
    user.department = body.department
    user.clearance_level = clearance
    db.commit()

    return {
        "status": "created" if created else "updated",
        "user_id": user.user_id,
        "username": user.username,
        "role": user.role,
        "department": user.department,
        "clearance_level": user.clearance_level,
    }


@router.get("/users")
def list_users(
    admin: UserContext = Depends(require_admin),
    db=Depends(get_db),
):
    return [
        {
            "user_id": u.user_id,
            "username": u.username,
            "role": u.role,
            "department": u.department,
            "clearance_level": u.clearance_level,
        }
        for u in db.query(User).all()
    ]


@router.post("/policy-rule")
def add_policy_rule(
    body: PolicyRuleRequest,
    admin: UserContext = Depends(require_admin),
    db=Depends(get_db),
):
    """Add a sensitivity-tier policy override applied on top of default RBAC."""
    if body.doc_sensitivity not in TIER_ORDER:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid doc_sensitivity. Use one of {list(TIER_ORDER)}",
        )
    invalid = [
        r for r in (body.allowed_roles + body.redact_roles) if r not in ALL_ROLES
    ]
    if invalid:
        raise HTTPException(status_code=400, detail=f"Unknown roles: {invalid}")

    rule = PolicyRule(
        rule_id=str(uuid.uuid4()),
        name=body.name,
        doc_sensitivity=body.doc_sensitivity,
        allowed_roles=body.allowed_roles,
        redact_roles=body.redact_roles,
    )
    db.add(rule)
    db.commit()
    return {"status": "created", "rule_id": rule.rule_id, "name": rule.name}
