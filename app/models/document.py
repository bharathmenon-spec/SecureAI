"""Document metadata table."""
from datetime import datetime

from sqlalchemy import Column, DateTime, String

from app.storage.db import Base


class Document(Base):
    __tablename__ = "documents"

    document_id = Column(String, primary_key=True)
    filename = Column(String, nullable=False)
    source_type = Column(String, nullable=False)
    owner_user_id = Column(String, nullable=False)
    sensitivity_level = Column(String, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    content_hash = Column(String, nullable=False)
