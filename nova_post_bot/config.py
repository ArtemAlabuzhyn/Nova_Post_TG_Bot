from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_env: str = Field(
        default="development",
        validation_alias='APP_ENV',
    )
    log_level: str = Field(
        default="INFO",
        validation_alias='LOG_LEVEL',
    )
    telegram_bot_token: str = Field(
        validation_alias='TELEGRAM_BOT_TOKEN',
    )
    nova_post_api_key: str = Field(
        validation_alias='NOVA_POST_API_KEY',
    )

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra='ignore'
    )

settings = Settings()

