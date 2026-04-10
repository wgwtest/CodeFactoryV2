from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "knowledge-warehouse"
    api_prefix: str = "/api"

    model_config = SettingsConfigDict(env_file=".env", env_prefix="KW_")


settings = Settings()
