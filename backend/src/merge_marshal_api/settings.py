"""Application configuration loaded from backend/.env via Pydantic."""

from __future__ import annotations

from pathlib import Path

from pydantic import Field, field_validator
from pydantic_settings import (
    BaseSettings,
    PydanticBaseSettingsSource,
    SettingsConfigDict,
)

BACKEND_PATH = Path(__file__).resolve().parents[2]
DEFAULT_REPOSITORY_PATH = Path(__file__).resolve().parents[3]
DOTENV_PATH = BACKEND_PATH / ".env"


class Settings(BaseSettings):
    """Immutable runtime settings with deterministic configuration sources."""

    model_config = SettingsConfigDict(
        env_file=DOTENV_PATH,
        env_file_encoding="utf-8",
        extra="ignore",
        populate_by_name=True,
        frozen=True,
    )

    repository_path: Path = Field(
        default=DEFAULT_REPOSITORY_PATH,
        validation_alias="MERGE_MARSHAL_REPO_PATH",
    )

    @field_validator("repository_path")
    @classmethod
    def resolve_repository_path(cls, repository_path: Path) -> Path:
        """Resolve relative dotenv paths from the backend directory."""
        resolved_path = repository_path.expanduser()
        if not resolved_path.is_absolute():
            resolved_path = BACKEND_PATH / resolved_path
        return resolved_path.resolve()

    @classmethod
    def settings_customise_sources(
        cls,
        settings_cls: type[BaseSettings],
        init_settings: PydanticBaseSettingsSource,
        env_settings: PydanticBaseSettingsSource,
        dotenv_settings: PydanticBaseSettingsSource,
        file_secret_settings: PydanticBaseSettingsSource,
    ) -> tuple[PydanticBaseSettingsSource, ...]:
        # Constructor overrides support tests; runtime values come only from .env.
        # OS environment variables and file-based secrets are intentionally ignored.
        del settings_cls, env_settings, file_secret_settings
        return init_settings, dotenv_settings

    @property
    def graph_path(self) -> Path:
        return self.repository_path / ".graph" / "graph.json"
