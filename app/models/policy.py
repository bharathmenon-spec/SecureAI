"""Admin-managed policy rule overrides applied on top of default RBAC."""
from datetime import datetime

from sqlalchemy import Column, DateTime, JSON, String

from app.storage.db import Base


class PolicyRule(Base):
    __tablename__ = "policy_rules"

    rule_id = Column(String, primary_key=True)
    name = Column(String, nullable=False)
    doc_sensitivity = Column(String, nullable=False)
    allowed_roles = Column(JSON, nullable=False, default=list)
    redact_roles = Column(JSON, nullable=False, default=list)
    created_at = Column(DateTime, default=datetime.utcnow)
