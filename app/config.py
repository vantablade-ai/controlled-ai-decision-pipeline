from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")
    provider: str = "mock"
    database_path: str = "decision_audit.sqlite3"
    openai_api_key: str | None = None
    openai_model: str = "gpt-4o-mini"


settings = Settings()
