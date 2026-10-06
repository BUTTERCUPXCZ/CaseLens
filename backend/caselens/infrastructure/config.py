from functools import lru_cache

from pathlib import Path

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
    auto_digest_on_upload: bool = True  # start a digest for every case a reviewer cites as soon as it is checked
    digest_parallel_answers: int = 3  # how many answers of one digest are written at the same time
    question_daily_limit: int = 500  # questions the AI assistant may answer per day (a cost guard)
    digest_ai_daily_limit: int = 200  # digests that may get written explanations per day (a cost guard)
    # Case digests (the client's format) started per month: a cost guard for the queue. A month of 2,000 digests needs room above that.
    case_digest_monthly_limit: int = 2500
    # Tokens the model may spend thinking before it writes a case digest (billed as output). -1 = the model's own default (dynamic).
    case_digest_thinking_budget: int = -1

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
        if not self.gemini_api_key:  # the key the client pasted in Settings, from the computer's password store
            from caselens.desktop.ai_key import read_ai_key

            self.gemini_api_key = read_ai_key(self.caselens_data_dir)
        return self


@lru_cache
def get_settings() -> Settings:
    return Settings()
