from fastapi import APIRouter, Depends
from sqlalchemy import text
from sqlalchemy.orm import Session

from caselens.presentation.dependencies import get_session

router = APIRouter(tags=["health"])


@router.get("/health")
def health(session: Session = Depends(get_session)) -> dict:
    session.execute(text("SELECT 1"))
    has_trgm = session.execute(
        text("SELECT 1 FROM pg_extension WHERE extname = 'pg_trgm'")
    ).scalar()
    return {"status": "ok", "db": "ok", "pg_trgm": bool(has_trgm)}
