"""Local SQLAlchemy database engine and session management."""
from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base, sessionmaker

from app.core.config import get_settings
from app.core.logger import get_logger

logger = get_logger(__name__)
_settings = get_settings()

_connect_args = (
    {"check_same_thread": False} if _settings.database_url.startswith("sqlite") else {}
)
engine = create_engine(_settings.database_url, connect_args=_connect_args, future=True)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


def get_db():
    """FastAPI dependency that yields a request-scoped session."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_db() -> None:
    """Create all tables. Imports models so they register with the metadata."""
    from app.models import (  # noqa: F401
        audit, chunk, document, policy, token, user,
    )

    Base.metadata.create_all(bind=engine)
    logger.info("Database initialized at %s", _settings.database_url)
