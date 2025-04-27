from typing import List, Optional, Union
from pydantic import PostgresDsn, validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env", env_file_encoding="utf-8", case_sensitive=True
    )

    # 應用設定
    APP_NAME: str = "NTUNHS_Equipment_System"
    APP_ENV: str = "development"
    DEBUG: bool = True
    API_PREFIX: str = "/api"
    API_V1_STR: str = "/api"

    # 伺服器設定
    HOST: str = "0.0.0.0"
    PORT: int = 8000

    # 資料庫設定
    POSTGRES_USER: str
    POSTGRES_PASSWORD: str
    POSTGRES_DB: str
    POSTGRES_HOST: str
    POSTGRES_PORT: str
    DATABASE_URL: Optional[PostgresDsn] = None

    @validator("DATABASE_URL", pre=True)
    def assemble_db_connection(cls, v: Optional[str], values: dict) -> str:
        if isinstance(v, str):
            return v
        return PostgresDsn.build(
            scheme="postgresql+asyncpg",
            username=values.get("POSTGRES_USER"),
            password=values.get("POSTGRES_PASSWORD"),
            host=values.get("POSTGRES_HOST"),
            port=values.get("POSTGRES_PORT"),
            path=f"/{values.get('POSTGRES_DB') or ''}",
        )

    # JWT 設定
    SECRET_KEY: str
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30

    # CORS 設定
    CORS_ORIGINS: List[str] = ["http://localhost:3000"]

    # LINE Bot 設定
    LINE_BOT_CHANNEL_ACCESS_TOKEN: Optional[str] = None
    LINE_BOT_CHANNEL_SECRET: Optional[str] = None
    LINE_BOT_WEBHOOK_URL: Optional[str] = None

    # SMTP 郵件設定
    SMTP_HOST: Optional[str] = None
    SMTP_PORT: Optional[int] = None
    SMTP_USER: Optional[str] = None
    SMTP_PASSWORD: Optional[str] = None
    SMTP_TLS: bool = True
    SMTP_SSL: bool = False
    SMTP_SENDER_EMAIL: Optional[str] = None
    SMTP_SENDER_NAME: Optional[str] = None

    # 系統參數
    REQUEST_EXPIRY_DAYS: int = 30
    RESPONSE_FORM_VALIDITY_HOURS: int = 48
    MAX_ITEMS_PER_REQUEST: int = 10
    ENABLE_EMAIL_NOTIFICATIONS: bool = True
    ENABLE_LINE_NOTIFICATIONS: bool = True
    SYSTEM_MAINTENANCE_MODE: bool = False

    # SSO 設定
    SSO_URL: Optional[str] = None
    SSO_CLIENT_ID: Optional[str] = None
    SSO_CLIENT_SECRET: Optional[str] = None
    SSO_REDIRECT_URI: Optional[str] = None


settings = Settings()