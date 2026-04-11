from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env", env_file_encoding="utf-8", extra="ignore"
    )

    DATABASE_URL: str = "postgresql+asyncpg://whats_bot:whats_bot@localhost:5432/whats_bot"
    SYNC_DATABASE_URL: str = "postgresql+psycopg2://whats_bot:whats_bot@localhost:5432/whats_bot"
    REDIS_URL: str = "redis://localhost:6379/0"

    # Twilio
    TWILIO_ACCOUNT_SID: str = ""
    TWILIO_AUTH_TOKEN: str = ""
    TWILIO_PHONE_NUMBER: str = ""

    # Google Gemini
    GEMINI_API_KEY: str = ""


settings = Settings()
