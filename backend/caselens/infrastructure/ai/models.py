"""The OpenRouter models the client can pick in Settings, and what each one supports. Kept apart (no imports) so the settings can read it."""
from dataclasses import dataclass


@dataclass(frozen=True)
class OpenRouterModel:
    id: str
    name: str
    json_mode: bool  # takes `response_format: json_object`; without it the shape is asked for in the instructions and checked in code
    free: bool  # costs nothing, but OpenRouter limits how many requests a day and a minute


OPENROUTER_MODELS: tuple[OpenRouterModel, ...] = (
    OpenRouterModel("deepseek/deepseek-v4.1-flash", "DeepSeek V4.1 Flash", json_mode=True, free=False),
    # For testing: free, but OpenRouter limits free models (about 20 requests a minute, and 50 a day without bought credit), and NVIDIA
    # logs what it receives (CaseLens only sends the public court decision).
    OpenRouterModel("nvidia/nemotron-3-ultra-550b-a55b:free", "Nemotron 3 Ultra (free, for testing)", json_mode=False, free=True),
)
DEFAULT_OPENROUTER_MODEL = OPENROUTER_MODELS[0].id


def openrouter_model(model_id: str) -> OpenRouterModel | None:
    return next((m for m in OPENROUTER_MODELS if m.id == model_id), None)
