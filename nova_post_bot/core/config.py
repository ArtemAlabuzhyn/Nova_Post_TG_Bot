from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

from nova_post_bot.core.settings.postgres import PostgresSettings


class Settings(BaseSettings):
    postgres: PostgresSettings = Field(default_factory=PostgresSettings)

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
