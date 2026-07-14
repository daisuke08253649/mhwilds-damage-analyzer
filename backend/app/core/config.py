import os
from dataclasses import dataclass, field
from functools import lru_cache
from pathlib import Path

from dotenv import load_dotenv

_ENV_FILE = Path(__file__).resolve().parent.parent.parent.parent / ".env.local"
load_dotenv(_ENV_FILE)


@dataclass
class Settings:
    supabase_url: str = field(default_factory=lambda: os.getenv("SUPABASE_URL", ""))
    supabase_service_role_key: str = field(default_factory=lambda: os.getenv("SUPABASE_SERVICE_ROLE_KEY", ""))
    supabase_jwt_secret: str = field(default_factory=lambda: os.getenv("SUPABASE_JWT_SECRET", ""))

    r2_endpoint_url: str = field(default_factory=lambda: os.getenv("R2_ENDPOINT_URL", ""))
    r2_access_key_id: str = field(default_factory=lambda: os.getenv("R2_ACCESS_KEY_ID", ""))
    r2_secret_access_key: str = field(default_factory=lambda: os.getenv("R2_SECRET_ACCESS_KEY", ""))
    r2_bucket_name: str = field(default_factory=lambda: os.getenv("R2_BUCKET_NAME", ""))

    gemini_api_key: str = field(default_factory=lambda: os.getenv("GEMINI_API_KEY", ""))
    gemini_model: str = field(default_factory=lambda: os.getenv("GEMINI_MODEL", "gemma-4-26b-a4b-it"))
    ocr_backend: str = field(default_factory=lambda: os.getenv("OCR_BACKEND", "gemini"))

    allowed_origins: str = field(default_factory=lambda: os.getenv("ALLOWED_ORIGINS", "") or "http://localhost:3000")
    max_upload_size_mb: int = field(default_factory=lambda: int(os.getenv("MAX_UPLOAD_SIZE_MB", "") or 2048))
    frame_max_width: int = field(default_factory=lambda: int(os.getenv("FRAME_MAX_WIDTH", "") or 1280))

    # Netscape 形式の YouTube Cookie ファイルを base64 エンコードした値。
    # 改行を含む Cookie ファイルを環境変数で安全に渡すために base64 を使用する。
    youtube_cookies_b64: str = field(default_factory=lambda: os.getenv("YOUTUBE_COOKIES_B64", ""))

    def __post_init__(self) -> None:
        if self.frame_max_width <= 0:
            raise ValueError(
                f"FRAME_MAX_WIDTH must be a positive integer, got {self.frame_max_width}"
            )


@lru_cache
def get_settings() -> Settings:
    return Settings()
