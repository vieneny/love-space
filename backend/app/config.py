from functools import lru_cache
from pathlib import Path
import secrets

from pydantic import model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")
    environment: str = "development"
    database_url: str = "sqlite:///./data/love-space.db"
    jwt_secret: str = ""
    dev_login_enabled: bool = True
    admin_username: str = "admin"
    admin_password: str = ""
    wechat_appid: str = ""
    wechat_secret: str = ""
    media_root: Path = Path("data/media")
    media_max_bytes: int = 10 * 1024 * 1024
    media_token_minutes: int = 30
    access_token_minutes: int = 24 * 60
    invite_minutes: int = 30
    public_base_url: str = "http://127.0.0.1:18100"
    cors_origins: str = "http://localhost:15173,http://127.0.0.1:15173,http://localhost:15174,http://127.0.0.1:15174"

    @model_validator(mode="after")
    def production_validation(self):
        if self.environment not in {"development", "test", "production"}:
            raise ValueError("ENVIRONMENT must be development, test, or production")
        if self.environment == "production":
            if len(self.jwt_secret.encode()) < 32:
                raise ValueError("Production requires JWT_SECRET of at least 32 bytes")
            if self.dev_login_enabled:
                raise ValueError("Production requires DEV_LOGIN_ENABLED=false")
            if len(self.admin_password) < 12:
                raise ValueError("Production requires ADMIN_PASSWORD of at least 12 characters")
            if not self.database_url.startswith("postgresql"):
                raise ValueError("Production requires PostgreSQL")
        if not self.jwt_secret:
            self.jwt_secret = secrets.token_urlsafe(48)
        return self


@lru_cache
def get_settings():
    return Settings()
