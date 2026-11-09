from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    secret_key: str
    token_minutes: int = 60

    model_config = SettingsConfigDict(env_file=".env")


settings = Settings()