"""Token map table. Raw values are stored encrypted and access controlled."""
from sqlalchemy import Column, JSON, String

from app.storage.db import Base


class TokenMap(Base):
    __tablename__ = "token_map"

    token_id = Column(String, primary_key=True)
    token_label = Column(String, index=True, unique=True, nullable=False)
    raw_value_encrypted = Column(String, nullable=False)
    entity_type = Column(String, nullable=False)
    document_id = Column(String, index=True, nullable=False)
    allowed_roles = Column(JSON, nullable=False, default=list)
    release_policy = Column(String, nullable=False)
