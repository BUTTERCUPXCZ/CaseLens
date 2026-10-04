from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    database_url: str = "postgresql+psycopg://caselens:caselens@localhost:5434/caselens"
    # Background jobs go through RabbitMQ. "stub" is an in-memory broker for tests (nothing is sent anywhere).
    rabbitmq_url: str = "amqp://caselens:caselens@localhost:5675/"
    queue_backend: str = "rabbitmq"

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


@lru_cache
def get_settings() -> Settings:
    return Settings()
