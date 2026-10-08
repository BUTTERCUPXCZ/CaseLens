"""Which AI writes the digests, for the website's Settings page (read only: the key is set by whoever runs the site, never shown)."""
from fastapi import APIRouter
from pydantic import BaseModel

from caselens.infrastructure.ai.calls import PROVIDER_NAMES, PROVIDERS, api_key_for, model_name
from caselens.infrastructure.ai.models import openrouter_model
from caselens.infrastructure.config import get_settings

router = APIRouter(tags=["settings"])


class AiInfoOut(BaseModel):
    provider: str  # "OpenRouter"
    model: str  # "Nemotron 3 Ultra (free, for testing)", or the model id when it is not one of the listed ones
    free: bool  # a free model: OpenRouter allows only so many requests a day
    only_chosen: bool  # no other AI takes over when this one cannot answer
    ready: bool  # a key is set for it


@router.get("/ai-info", response_model=AiInfoOut)
def ai_info() -> AiInfoOut:
    settings = get_settings()
    provider = settings.ai_provider if settings.ai_provider in PROVIDERS else "gemini"
    model_id = model_name(settings, provider)
    listed = openrouter_model(model_id) if provider == "openrouter" else None
    return AiInfoOut(
        provider=PROVIDER_NAMES[provider],
        model=listed.name if listed else model_id,
        free=model_id.endswith(":free"),
        only_chosen=settings.ai_only_chosen,
        ready=bool(api_key_for(settings, provider)),
    )
