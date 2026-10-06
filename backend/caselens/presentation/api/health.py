from fastapi import APIRouter, Depends
from sqlalchemy import text
from sqlalchemy.orm import Session

from caselens.infrastructure.config import get_settings
from caselens.presentation.dependencies import get_session

router = APIRouter(tags=["health"])


@router.get("/health")
def health(session: Session = Depends(get_session)) -> dict:
    session.execute(text("SELECT 1"))
    desktop = get_settings().caselens_desktop  # the screen shows Settings (AI key, backup) only in the desktop app
    if session.get_bind().dialect.name != "postgresql":
        return {"status": "ok", "db": "ok", "pg_trgm": False, "database": "sqlite", "desktop": desktop}  # no extension needed
    has_trgm = session.execute(text("SELECT 1 FROM pg_extension WHERE extname = 'pg_trgm'")).scalar()
    return {"status": "ok", "db": "ok", "pg_trgm": bool(has_trgm), "database": "postgresql", "desktop": desktop}
