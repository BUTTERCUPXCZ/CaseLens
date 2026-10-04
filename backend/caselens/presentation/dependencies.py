"""FastAPI dependencies. Routers ask for `Services`; they never build adapters themselves."""
from fastapi import Depends
from sqlalchemy.orm import Session

from caselens.composition import Services
from caselens.infrastructure.db.session import get_session


def get_services(session: Session = Depends(get_session)) -> Services:
    return Services(session)


__all__ = ["get_services", "get_session"]
