from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

from nova_post_bot.core.settings.postgres import PostgresSettings


class Settings(BaseSettings):
    postgres: PostgresSettings = Field(default_factory=PostgresSettings)
    nova_post_timeout: float = Field(default=10.0, validation_alias='NOVA_POST_TIMEOUT', gt=0)
    nova_post_api_url: str = Field(validation_alias='NOVA_POST_API_URL')

    allowed_telegram_ids: dict[int, str] = Field(default_factory=dict, validation_alias='ALLOWED_TELEGRAM_IDS')



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

    def postgres_dsn(self):
        return (
            f"postgresql+asyncpg://"
            f"{self.postgres.user}:{self.postgres.password}"
            f"@{self.postgres.host}:{self.postgres.port}/{self.postgres.db}"
        )


settings = Settings()
