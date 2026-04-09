from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env", env_file_encoding="utf-8", extra="ignore"
    )

    DATABASE_URL: str = "postgresql+asyncpg://whats_bot:whats_bot@localhost:5432/whats_bot"
    SYNC_DATABASE_URL: str = "postgresql+psycopg2://whats_bot:whats_bot@localhost:5432/whats_bot"
    REDIS_URL: str = "redis://localhost:6379/0"

    META_VERIFY_TOKEN: str = "vibecode"
    META_API_TOKEN: str = ""
    META_PHONE_NUMBER_ID: str = ""

    GEMINI_API_KEY: str = "N Tem ainda :("


settings = Settings()
