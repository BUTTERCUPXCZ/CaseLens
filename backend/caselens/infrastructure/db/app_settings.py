"""Settings the website's Settings page can change, kept in the database so every worker and the next deploy see them. Only the
OpenRouter model, and only one of the listed ones; keys stay in the host's environment."""
from sqlalchemy import func, select
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.dialects.sqlite import insert as sqlite_insert
from sqlalchemy.orm import Session

from caselens.infrastructure.ai.models import openrouter_model
from caselens.infrastructure.config import Settings
from caselens.infrastructure.db.orm_models import AppSettingModel

OPENROUTER_MODEL_KEY = "openrouter_model"


def chosen_openrouter_model(session: Session) -> str | None:
    """The model picked on the Settings page, if it is still one of the listed ones."""
    chosen = session.scalar(select(AppSettingModel.value).where(AppSettingModel.key == OPENROUTER_MODEL_KEY))
    return chosen if chosen and openrouter_model(chosen) else None


def choose_openrouter_model(session: Session, model_id: str) -> None:
    if openrouter_model(model_id) is None:
        raise ValueError(f"{model_id} is not one of the models that can be chosen")
    insert = pg_insert if session.get_bind().dialect.name == "postgresql" else sqlite_insert
    statement = insert(AppSettingModel).values(key=OPENROUTER_MODEL_KEY, value=model_id)
    session.execute(statement.on_conflict_do_update(index_elements=["key"], set_={"value": model_id, "updated_at": func.now()}))


def with_site_choices(settings: Settings, session: Session) -> Settings:
    """The host's settings with the website's own choice on top: the picked model writes AND checks (one model only)."""
    if settings.caselens_desktop:
        return settings  # the desktop app keeps its choice in its own folder
    chosen = chosen_openrouter_model(session)
    if not chosen or chosen == settings.openrouter_model:
        return settings
    return settings.model_copy(update={"openrouter_model": chosen, "openrouter_checker_model": chosen})
