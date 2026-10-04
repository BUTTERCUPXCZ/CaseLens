from functools import lru_cache

from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    database_url: str = "postgresql+psycopg://caselens:caselens@localhost:5434/caselens"
    # Background jobs: "rabbitmq" (separate workers), "threads" (inside the API, for a host without workers) or
    # "stub" (an in-memory broker for tests, nothing is sent anywhere).
    rabbitmq_url: str = "amqp://caselens:caselens@localhost:5675/"
    queue_backend: str = "rabbitmq"

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
    gemini_writer_model: str = "gemini-2.5-flash"
    gemini_checker_model: str = "gemini-3.5-flash"  # a separate, stronger model judges what the writer drafted
    gemini_timeout_seconds: float = 120.0
    gemini_max_retries: int = 3
    auto_digest_on_upload: bool = True  # start a digest for every case a reviewer cites as soon as it is checked
    digest_parallel_answers: int = 3  # how many answers of one digest are written at the same time
    digest_ai_daily_limit: int = 200  # digests that may get written explanations per day (a cost guard)

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


@lru_cache
def get_settings() -> Settings:
    return Settings()
