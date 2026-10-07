from functools import lru_cache

from pathlib import Path
from typing import Literal

from pydantic import field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    database_url: str = "postgresql+psycopg://caselens:caselens@localhost:5434/caselens"
    # The desktop app (one user, everything on their computer): its own folder holds the SQLite database <data_dir>/caselens.db
    # (a server DATABASE_URL is ignored); jobs run as threads; there is no access code.
    caselens_desktop: bool = False
    caselens_data_dir: str | None = None
    # Background jobs: "rabbitmq" (separate workers), "threads" (inside the API, for a host without workers) or
    # "stub" (an in-memory broker for tests, nothing is sent anywhere).
    rabbitmq_url: str = "amqp://caselens:caselens@localhost:5675/"
    queue_backend: str = "rabbitmq"
    # With "threads": how many digests are written at the same time. The web version keeps 4 (its hosted database allows few
    # connections); the desktop app writes 12 at once (a bulk upload of 50 cases), which Gemini's per-minute limits allow.
    digest_threads: int = 4

    # A shared code the student gives to the people who may use the app. Empty = no gate (local development).
    access_code: str | None = None
    upload_max_mb: int = 5
    # Uploads (with their digests and original file) older than this are deleted to keep the database small. 0 = keep.
    upload_keep_days: int = 0

    lawphil_base_url: str = "https://lawphil.net"
    # Oldest year whose monthly lists are read into the searchable catalog.
    catalog_first_year: int = 1987
    lawphil_user_agent: str = "caselens-internal/0.1 (internal law-student tool)"
    lawphil_min_interval_seconds: float = 1.0
    lawphil_timeout_seconds: float = 30.0
    lawphil_max_retries: int = 3

    # AI that answers the digest's questions (explanations only; never the Court's own text).
    gemini_api_key: str | None = None
    gemini_writer_model: str = "gemini-3.5-flash"  # 2.5 is closed to new API keys (Google, Oct 2026)
    gemini_checker_model: str = "gemini-3.5-flash"  # judges what the writer drafted, in a separate call
    gemini_timeout_seconds: float = 120.0
    gemini_max_retries: int = 3
    # Tried in this order when the asked model stays overloaded (Google's 503 "model is overloaded"); same family and price.
    gemini_fallback_models: list[str] = ["gemini-3.7-flash", "gemini-3.6-flash", "gemini-3.8-flash"]
    # Groq and DeepSeek (OpenAI-style APIs). `ai_provider` writes first; the others with a key take over when it cannot answer.
    ai_provider: str = "gemini"  # groq | deepseek | gemini (the desktop app reads the client's choice from its folder)
    groq_api_key: str | None = None
    groq_model: str = "openai/gpt-oss-120b"  # strict JSON schema, 131K context, $0.15 in / $0.60 out per 1M tokens (Oct 2026)
    groq_checker_model: str = "openai/gpt-oss-120b"
    groq_reasoning_effort: str = "medium"  # low | medium | high (gpt-oss): thinking before answering, billed as output
    deepseek_api_key: str | None = None
    deepseek_model: str = "deepseek-flash"  # DeepSeek V4.1 Flash; JSON object mode (the schema goes in the prompt)
    deepseek_checker_model: str = "deepseek-flash"
    # OpenRouter (OpenAI-style API), with DeepSeek V4.1 Flash: a whole decision fits; thinking (reasoning) is on, billed as output.
    # Any OpenRouter model id can be set here instead (for example "openrouter/free" for its free models).
    openrouter_api_key: str | None = None
    openrouter_model: str = "deepseek/deepseek-v4.1-flash"
    openrouter_checker_model: str = "deepseek/deepseek-v4.1-flash"
    openrouter_reasoning: bool = True
    # Ask for `response_format: json_object`. None: by the model (see `infrastructure/ai/models.py`); some free models do not take it.
    openrouter_json_mode: bool | None = None
    # Only the chosen provider writes, with no other AI taking over when it cannot answer (one AI, one kind of digest and cost).
    ai_only_chosen: bool = False
    # How hard the writer thinks before writing the digest (billed as output): "minimal" | "low" | "medium" | "high".
    openrouter_reasoning_effort: str = "low"
    ai_timeout_seconds: float = 180.0
    auto_digest_on_upload: bool = True  # start a digest for every case a reviewer cites as soon as it is checked
    digest_parallel_answers: int = 3  # how many answers of one digest are written at the same time
    question_daily_limit: int = 500  # questions the AI assistant may answer per day (a cost guard)
    digest_ai_daily_limit: int = 200  # digests that may get written explanations per day (a cost guard)
    # Case digests (the client's format) started per month: a cost guard for the queue. A month of 2,000 digests needs room above that.
    case_digest_monthly_limit: int = 2500
    # Tokens the model may spend thinking before it writes a case digest (billed as output). -1 = the model's own default (dynamic).
    case_digest_thinking_budget: int = -1
    # Which digest sentences the second model judges: "risky_and_key" (those code flags, plus the bold key sentences) or "all" (every
    # cited sentence, as before; costs about 4 more calls per digest). Code checks every sentence either way.
    case_digest_check_mode: Literal["risky_and_key", "all"] = "risky_and_key"
    # A sentence with less than this share of its own words in the paragraphs it cites is sent to the second model (0 to 1).
    case_digest_coverage_min: float = 0.6

    @field_validator("database_url")
    @classmethod
    def _use_the_psycopg_driver(cls, url: str) -> str:
        """Hosts give `postgres://` or `postgresql://`; SQLAlchemy needs to be told to use psycopg 3."""
        for prefix in ("postgres://", "postgresql://"):
            if url.startswith(prefix):
                return "postgresql+psycopg://" + url[len(prefix):]
        return url

    @field_validator("access_code")
    @classmethod
    def _blank_code_means_no_gate(cls, code: str | None) -> str | None:
        return code.strip() or None if code else None

    @model_validator(mode="after")
    def _desktop_defaults(self) -> "Settings":
        """The desktop app: one user on their own computer. The database is a file in the app's folder, jobs run inside the app,
        and there is no access code."""
        if not self.caselens_desktop:
            return self
        # Always the local file: a server address found in a stray .env must never receive the client's library.
        if self.caselens_data_dir and not self.database_url.startswith("sqlite"):
            folder = Path(self.caselens_data_dir)
            folder.mkdir(parents=True, exist_ok=True)
            self.database_url = f"sqlite:///{(folder / 'caselens.db').as_posix()}"
        if "queue_backend" not in self.model_fields_set:
            self.queue_backend = "threads"
        if "digest_threads" not in self.model_fields_set:
            self.digest_threads = 12
        self.access_code = None
        # The keys the client pasted in Settings (the computer's password store) and the provider they chose.
        from caselens.desktop.ai_key import read_ai_key, read_provider

        for provider in ("gemini", "groq", "deepseek", "openrouter"):
            if not getattr(self, f"{provider}_api_key"):
                setattr(self, f"{provider}_api_key", read_ai_key(self.caselens_data_dir, provider))
        if "ai_provider" not in self.model_fields_set:
            self.ai_provider = read_provider(self.caselens_data_dir) or "groq"
        from caselens.desktop.ai_key import read_only_chosen, read_openrouter_model

        chosen_model = read_openrouter_model(self.caselens_data_dir)
        if chosen_model and "openrouter_model" not in self.model_fields_set:
            self.openrouter_model = chosen_model
        if chosen_model and "openrouter_checker_model" not in self.model_fields_set:
            self.openrouter_checker_model = chosen_model  # the chosen model writes AND checks: one model only
        if "ai_only_chosen" not in self.model_fields_set:
            self.ai_only_chosen = read_only_chosen(self.caselens_data_dir)
        if self.openrouter_model.endswith(":free") and "digest_threads" not in self.model_fields_set:
            self.digest_threads = 2  # free models allow few requests a minute: two digests at a time (read when the app starts)
        return self


@lru_cache
def get_settings() -> Settings:
    return Settings()
