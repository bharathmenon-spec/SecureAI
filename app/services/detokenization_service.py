"""De-tokenization service.

Restores raw values for sanitized markers only when policy permits. Markers
that are masked, hashed, dropped, unknown, or not permitted are replaced with
a generic redaction placeholder.
"""
from typing import List, Tuple

from app.schemas import UserContext
from app.services.policy_service import PolicyService
from app.storage.token_store import TokenStore
from app.utils.redaction_utils import TOKEN_MARKER_RE

_NON_TOKEN_PREFIXES = ("REDACTED:", "HASH:")


class DetokenizationService:
    def __init__(self, db) -> None:
        self.db = db
        self.token_store = TokenStore(db)
        self.policy = PolicyService(db)

    def restore(
        self, text: str, user: UserContext, suspicious: bool
    ) -> Tuple[str, List[dict]]:
        """Return (restored_text, detok_log)."""
        log: List[dict] = []

        def replace(match) -> str:
            label = match.group(1).strip()

            if label == "REMOVED" or label.startswith(_NON_TOKEN_PREFIXES):
                return "[redacted]"

            entry = self.token_store.get_by_label(label)
            if entry is None:
                log.append({"token": label, "action": "masked",
                            "reason": "unknown marker"})
                return "[redacted]"

            decision = self.policy.evaluate_token(user, entry, suspicious)
            if decision["release"]:
                log.append({"token": label, "action": "released",
                            "reason": decision["reason"]})
                return TokenStore.reveal(entry)

            log.append({"token": label, "action": "masked",
                        "reason": decision["reason"]})
            return "[restricted]"

        return TOKEN_MARKER_RE.sub(replace, text), log
