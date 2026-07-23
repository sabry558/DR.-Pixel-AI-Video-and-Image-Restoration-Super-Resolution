from functools import lru_cache
from pathlib import Path

from pydantic import computed_field
from pydantic_settings import BaseSettings, SettingsConfigDict

BASE_DIR = Path(__file__).resolve().parent.parent.parent

class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=(
            BASE_DIR / ".env",
            BASE_DIR / ".env.Database",
        ),
        env_file_encoding="utf-8",
        extra="ignore",
    )
    CELERY_BROKER_URL: str = "amqp://admin:password@localhost:5672//"


    POSTGRES_USER: str
    POSTGRES_PASSWORD: str
    POSTGRES_DB: str
    POSTGRES_HOST: str = "localhost"
    POSTGRES_PORT: int = 5433
    BASE_DIR: Path = Path(__file__).resolve().parent.parent.parent  # -> backend/
    ML_ARTIFACTS_DIR: Path = BASE_DIR / "ml_artifacts"
    CLASSIFIER_MODEL_PATH: Path = ML_ARTIFACTS_DIR / "best_model.pth"
    SECRET_KEY: str
    ALGORITHM: str
    ACCESS_TOKEN_EXPIRE_MINUTES: int
    REFRESH_TOKEN_EXPIRE_DAYS: int
    UPLOAD_CHUNK_SIZE: int 
    STORAGE_DIR:Path
    FAL_API_KEY: str
    @computed_field
    @property
    def database_url(self) -> str:
        return (
            f"postgresql://{self.POSTGRES_USER}:{self.POSTGRES_PASSWORD}"
            f"@{self.POSTGRES_HOST}:{self.POSTGRES_PORT}/{self.POSTGRES_DB}"
        )

@lru_cache
def get_settings():
    return Settings()