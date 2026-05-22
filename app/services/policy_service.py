"""RBAC policy engine.

Evaluates chunk-level access and token-level release decisions. This logic is
fully local and deterministic - security never depends on the LLM.
"""
from typing import List

from app.core.constants import (
    Role,
    SensitivityTier,
    tier_rank,
)
from app.models.policy import PolicyRule

ALLOW = "ALLOW"
DENY = "DENY"
REDACT = "REDACT"


def default_roles_for_tier(tier: str, owner_role: str) -> List[str]:
    """Sensible default allow-list when an uploader does not specify one."""
    privileged = [Role.ADMIN.value, Role.SECURITY_ANALYST.value]
    if tier == SensitivityTier.PUBLIC.value:
        return [r.value for r in Role]
    if tier == SensitivityTier.INTERNAL.value:
        return [r.value for r in Role if r != Role.GUEST]
    if tier == SensitivityTier.CONFIDENTIAL.value:
        roles = privileged + [owner_role, Role.MANAGER.value]
    else:  # STRICT_CONFIDENTIAL
        roles = privileged + [owner_role]
    return sorted(set(roles))


class PolicyService:
    def __init__(self, db) -> None:
        self.db = db
        self._rules = db.query(PolicyRule).all()

    def _rule_for(self, tier: str):
        for rule in self._rules:
            if rule.doc_sensitivity == tier:
                return rule
        return None

    def evaluate_chunk(self, user, chunk: dict) -> dict:
        """Decide chunk access. Returns {decision, reason}."""
        role = user.role
        tier = chunk.get("sensitivity_level", SensitivityTier.PUBLIC.value)
        allowed = list(chunk.get("allowed_roles", []))
        redact_roles: List[str] = []

        rule = self._rule_for(tier)
        if rule is not None:
            allowed = sorted(set(allowed) | set(rule.allowed_roles))
            redact_roles = list(rule.redact_roles)

        if role == Role.ADMIN.value:
            return {"decision": ALLOW, "reason": "admin override"}

        if role not in allowed:
            return {"decision": DENY,
                    "reason": "role not in document allow-list"}

        gap = tier_rank(user.clearance_level) - tier_rank(tier)
        if gap < 0:
            if role == Role.MANAGER.value and gap == -1:
                return {"decision": REDACT,
                        "reason": "manager partial access - tokens stay masked"}
            return {"decision": DENY,
                    "reason": "clearance below chunk sensitivity"}

        if role in redact_roles:
            return {"decision": REDACT, "reason": "policy rule: redacted role"}

        return {"decision": ALLOW, "reason": "role and clearance satisfied"}

    def evaluate_token(self, user, token, suspicious: bool) -> dict:
        """Decide whether a token may be de-tokenized. Returns {release, reason}."""
        if suspicious:
            return {"release": False, "reason": "request flagged as suspicious"}

        if user.role == Role.ADMIN.value:
            return {"release": True, "reason": "admin override"}

        if user.role not in list(token.allowed_roles):
            return {"release": False,
                    "reason": "role not permitted for this token"}

        if tier_rank(user.clearance_level) < tier_rank(token.release_policy):
            return {"release": False,
                    "reason": "clearance below token sensitivity class"}

        return {"release": True, "reason": "role and clearance satisfied"}
