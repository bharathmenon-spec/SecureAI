"""User table holding role and clearance for RBAC."""
from sqlalchemy import Column, String

from app.storage.db import Base


class User(Base):
    __tablename__ = "users"

    user_id = Column(String, primary_key=True)
    username = Column(String, unique=True, nullable=False)
    role = Column(String, nullable=False)
    department = Column(String, nullable=False)
    clearance_level = Column(String, nullable=False)
