from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Configuración de la aplicación por variables de entorno."""

    app_env: str = "development"
    data_dir: Path = Path("data")
    max_upload_mb: int = 25

    model_config = SettingsConfigDict(env_file=".env", case_sensitive=False)

    @property
    def database_path(self) -> Path:
        return self.data_dir / "planillas.db"

    @property
    def uploads_dir(self) -> Path:
        return self.data_dir / "uploads"


@lru_cache
def get_settings() -> Settings:
    return Settings()
