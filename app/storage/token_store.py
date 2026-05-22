"""Access-controlled token map storage.

Raw sensitive values are encrypted at rest. Reveal is only ever called by the
de-tokenization service after an explicit policy check.
"""
import uuid
from typing import List, Optional

from app.core.security import decrypt, encrypt
from app.models.token import TokenMap


class TokenStore:
    def __init__(self, db) -> None:
        self.db = db

    def create(
        self,
        token_label: str,
        raw_value: str,
        entity_type: str,
        document_id: str,
        allowed_roles: List[str],
        release_policy: str,
    ) -> TokenMap:
        entry = TokenMap(
            token_id=str(uuid.uuid4()),
            token_label=token_label,
            raw_value_encrypted=encrypt(raw_value),
            entity_type=entity_type,
            document_id=document_id,
            allowed_roles=list(allowed_roles),
            release_policy=release_policy,
        )
        self.db.add(entry)
        return entry

    def get_by_label(self, token_label: str) -> Optional[TokenMap]:
        return (
            self.db.query(TokenMap)
            .filter(TokenMap.token_label == token_label)
            .first()
        )

    def get_for_document(self, document_id: str) -> List[TokenMap]:
        return (
            self.db.query(TokenMap)
            .filter(TokenMap.document_id == document_id)
            .all()
        )

    @staticmethod
    def reveal(entry: TokenMap) -> str:
        """Decrypt a raw value. Callers must enforce policy beforehand."""
        return decrypt(entry.raw_value_encrypted)
