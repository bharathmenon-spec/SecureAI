"""FastAPI application entrypoint for the Privacy-First RAG prototype."""
from pathlib import Path

from fastapi import FastAPI
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from app.api import admin, audit, chat, ingest
from app.core.config import get_settings
from app.core.constants import ROLE_CLEARANCE, Role
from app.core.logger import get_logger
from app.models.user import User
from app.storage.db import SessionLocal, init_db

logger = get_logger("app.main")

# static/ sits next to app/ inside the project root.
_STATIC_DIR = Path(__file__).resolve().parent.parent / "static"

# (username, role, department) for the prototype's pre-seeded users.
_DEFAULT_USERS = [
    ("admin", Role.ADMIN.value, "IT"),
    ("analyst", Role.SECURITY_ANALYST.value, "Security"),
    ("hr_user", Role.HR.value, "HR"),
    ("finance_user", Role.FINANCE.value, "Finance"),
    ("eng_user", Role.ENGINEERING.value, "Engineering"),
    ("manager_user", Role.MANAGER.value, "Operations"),
    ("employee_user", Role.EMPLOYEE.value, "Operations"),
    ("guest_user", Role.GUEST.value, "External"),
]


def seed_default_users() -> None:
    """Seed one user per role on first run so the prototype is usable."""
    db = SessionLocal()
    try:
        if db.query(User).count() > 0:
            return
        for username, role, department in _DEFAULT_USERS:
            db.add(User(
                user_id=username,
                username=username,
                role=role,
                department=department,
                clearance_level=ROLE_CLEARANCE[role],
            ))
        db.commit()
        logger.info("Seeded %d default users", len(_DEFAULT_USERS))
    finally:
        db.close()


def create_app() -> FastAPI:
    settings = get_settings()
    if not settings.gemini_api_key:
        raise RuntimeError(
            "GEMINI_API_KEY is required. Set it in .env before starting the app."
        )

    app = FastAPI(
        title="Privacy-First RAG Prototype",
        version="0.1.0",
        description=(
            "Local-first enterprise RAG with sensitive-data masking, RBAC "
            "enforcement, and multi-agent query orchestration. Gemini is the "
            "only external dependency and only ever sees sanitized context."
        ),
    )
    app.include_router(ingest.router, prefix="/ingest", tags=["ingest"])
    app.include_router(chat.router, prefix="/chat", tags=["chat"])
    app.include_router(admin.router, prefix="/admin", tags=["admin"])
    app.include_router(audit.router, prefix="/audit", tags=["audit"])

    # Serve the testing console (static single-page app).
    if _STATIC_DIR.is_dir():
        app.mount(
            "/static",
            StaticFiles(directory=str(_STATIC_DIR)),
            name="static",
        )

        @app.get("/", include_in_schema=False)
        def console() -> FileResponse:
            return FileResponse(str(_STATIC_DIR / "index.html"))

    @app.on_event("startup")
    def _startup() -> None:
        init_db()
        seed_default_users()
        logger.info("Privacy-First RAG prototype started")

    @app.get("/health", tags=["health"])
    def health() -> dict:
        return {"status": "ok"}

    return app


app = create_app()
