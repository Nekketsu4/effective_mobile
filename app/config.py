from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", case_sensitive=True)

    # DATABASE_URL: str

    JWT_SECRET: str
    JWT_EXPIRES_SECONDS: int



settings = Settings()