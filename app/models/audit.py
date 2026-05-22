"""Audit table - one row per query request, with full pipeline trace."""
from datetime import datetime

from sqlalchemy import Boolean, Column, DateTime, JSON, String, Text

from app.storage.db import Base


class AuditRecord(Base):
    __tablename__ = "audit"

    request_id = Column(String, primary_key=True)
    user_id = Column(String, index=True, nullable=False)
    query_text = Column(Text, nullable=False)
    retrieved_chunk_ids = Column(JSON, default=list)
    policy_decision = Column(JSON, default=dict)
    redaction_applied = Column(Boolean, default=False)
    final_response_status = Column(String, nullable=False)
    timestamp = Column(DateTime, default=datetime.utcnow)
    trace = Column(JSON, default=list)
