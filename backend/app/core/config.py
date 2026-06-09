from functools import lru_cache
from pathlib import Path

from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

# config.py は backend/app/core/ にあるため、4階層上がリポジトリルート
_ENV_FILE = Path(__file__).resolve().parent.parent.parent.parent / ".env.local"


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=str(_ENV_FILE),
        env_file_encoding="utf-8",
        extra="ignore",
    )

    supabase_url: str = ""
    supabase_service_role_key: str
    supabase_jwt_secret: str

    r2_endpoint_url: str = ""
    r2_access_key_id: str = ""
    r2_secret_access_key: str
    r2_bucket_name: str = ""

    openrouter_api_key: str
    openrouter_model: str = "google/gemma-4-26b-a4b-it:free"
    ocr_backend: str = "openrouter"

    allowed_origins: str = "http://localhost:3000"
    max_upload_size_mb: int = 2048

    @field_validator("max_upload_size_mb", mode="before")
    @classmethod
    def _coerce_empty_int(cls, v: str | int) -> str | int:
        """環境変数が空文字の場合はデフォルト値を使用する。"""
        if isinstance(v, str) and not v.strip():
            return 2048
        return v

    @field_validator("allowed_origins", mode="before")
    @classmethod
    def _coerce_empty_origins(cls, v: str) -> str:
        """環境変数が空文字の場合はデフォルト値を使用する。"""
        if not v.strip():
            return "http://localhost:3000"
        return v


@lru_cache
def get_settings() -> Settings:
    return Settings()
