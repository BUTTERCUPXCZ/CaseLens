"""Which AI writes the digests, for the website's Settings page. The OpenRouter model can be picked there (one of the listed ones);
the key is set by whoever runs the site and is never shown."""
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from caselens.infrastructure.ai.calls import PROVIDER_NAMES, PROVIDERS, api_key_for, model_name
from caselens.infrastructure.ai.models import OPENROUTER_MODELS, openrouter_model
from caselens.infrastructure.config import get_settings
from caselens.infrastructure.db.app_settings import choose_openrouter_model, with_site_choices
from caselens.presentation.dependencies import get_session

router = APIRouter(tags=["settings"])


class ModelChoiceOut(BaseModel):
    id: str
    name: str
    free: bool


class AiInfoOut(BaseModel):
    provider: str  # "OpenRouter"
    model: str  # "Nemotron 3 Ultra (free, for testing)", or the model id when it is not one of the listed ones
    model_id: str
    free: bool  # a free model: OpenRouter allows only so many requests a day
    only_chosen: bool  # no other AI takes over when this one cannot answer
    ready: bool  # a key is set for it
    models: list[ModelChoiceOut] = []  # the models that can be picked here (OpenRouter only)


class ModelChoiceIn(BaseModel):
    model: str


@router.get("/ai-info", response_model=AiInfoOut)
def ai_info(session: Session = Depends(get_session)) -> AiInfoOut:
    settings = with_site_choices(get_settings(), session)
    provider = settings.ai_provider if settings.ai_provider in PROVIDERS else "gemini"
    model_id = model_name(settings, provider)
    listed = openrouter_model(model_id) if provider == "openrouter" else None
    can_pick = provider == "openrouter" and not settings.caselens_desktop  # the desktop app picks in its own Settings
    return AiInfoOut(
        provider=PROVIDER_NAMES[provider],
        model=listed.name if listed else model_id,
        model_id=model_id,
        free=model_id.endswith(":free"),
        only_chosen=settings.ai_only_chosen,
        ready=bool(api_key_for(settings, provider)),
        models=[ModelChoiceOut(id=m.id, name=m.name, free=m.free) for m in OPENROUTER_MODELS] if can_pick else [],
    )


@router.put("/ai-model", response_model=AiInfoOut)
def choose_model(body: ModelChoiceIn, session: Session = Depends(get_session)) -> AiInfoOut:
    """Pick the OpenRouter model for the next digests and questions (one already being written finishes with its model)."""
    settings = get_settings()
    if settings.caselens_desktop or settings.ai_provider != "openrouter":
        raise HTTPException(409, "The model can be picked here only on the website, when it uses OpenRouter.")
    try:
        choose_openrouter_model(session, body.model)
    except ValueError as exc:
        raise HTTPException(422, str(exc)) from exc
    session.commit()
    return ai_info(session)
