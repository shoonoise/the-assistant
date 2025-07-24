"""Central application settings using Pydantic."""

from pathlib import Path

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application configuration loaded from environment variables."""

    # Core application
    log_level: str = Field("INFO", env="LOG_LEVEL")
    port: int = Field(8000, env="PORT")

    # Telegram
    telegram_token: str | None = Field(None, env="TELEGRAM_TOKEN")

    # Google
    google_credentials_path: Path = Field(
        Path("secrets/google.json"), env="GOOGLE_CREDENTIALS_PATH"
    )
    google_token_path: Path = Field(Path("secrets/token.json"), env="GOOGLE_TOKEN_PATH")
    google_calendar_id: str = Field("primary", env="GOOGLE_CALENDAR_ID")
    google_oauth_redirect_uri: str = Field(
        "http://localhost:9000/google/oauth2callback", env="GOOGLE_OAUTH_REDIRECT_URI"
    )
    google_oauth_scopes: list[str] = Field(
        default_factory=lambda: [
            "https://www.googleapis.com/auth/calendar.readonly",
            "https://www.googleapis.com/auth/gmail.readonly",
            "https://www.googleapis.com/auth/calendar.events.readonly",
        ]
    )

    # Obsidian
    obsidian_vault_path: Path | None = Field(Path("/vault"), env="OBSIDIAN_VAULT_PATH")

    # Temporal
    temporal_host: str = Field("localhost:7233", env="TEMPORAL_HOST")
    temporal_task_queue: str = Field("the-assistant", env="TEMPORAL_TASK_QUEUE")
    temporal_namespace: str = Field("default", env="TEMPORAL_NAMESPACE")

    # Storage / database
    database_url: str = Field(
        "postgresql+asyncpg://temporal:temporal@postgresql:5432/the_assistant",
        env="DATABASE_URL",
    )
    db_encryption_key: str = Field(..., env="DB_ENCRYPTION_KEY")

    # Security
    jwt_secret: str = Field(..., env="JWT_SECRET")

    # Observability
    langsmith_tracing: bool = Field(False, env="LANGSMITH_TRACING")
    langsmith_endpoint: str = Field(
        "https://api.smith.langchain.com", env="LANGSMITH_ENDPOINT"
    )
    langsmith_api_key: str | None = Field(None, env="LANGSMITH_API_KEY")
    langsmith_project: str | None = Field(None, env="LANGSMITH_PROJECT")

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    @field_validator(
        "google_credentials_path",
        "google_token_path",
        "obsidian_vault_path",
        mode="before",
    )
    @classmethod
    def expand_path(cls, v: str | Path | None) -> Path | None:
        if v is None:
            return None
        return Path(v).expanduser()


def get_settings() -> Settings:
    """Return application settings loaded from environment variables."""
    return Settings()
