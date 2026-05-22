"""Sanitized retrieval chunk table. Stores only masked text - never raw values."""
from datetime import datetime

from sqlalchemy import Column, DateTime, Integer, JSON, String, Text

from app.storage.db import Base


class Chunk(Base):
    __tablename__ = "chunks"

    chunk_id = Column(String, primary_key=True)
    document_id = Column(String, index=True, nullable=False)
    chunk_text_sanitized = Column(Text, nullable=False)
    embedding_ref = Column(String, nullable=False)
    sensitivity_level = Column(String, nullable=False)
    allowed_roles = Column(JSON, nullable=False, default=list)
    source_page = Column(Integer, default=0)
    token_count = Column(Integer, default=0)
    created_at = Column(DateTime, default=datetime.utcnow)
