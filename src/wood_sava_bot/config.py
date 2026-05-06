from __future__ import annotations

from functools import lru_cache

from pydantic import Field, PositiveInt
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    app_env: str = "development"
    log_level: str = "INFO"
    database_url: str = "sqlite+aiosqlite:///./wood_sava_bot.db"

    telegram_bot_token: str = Field(alias="TELEGRAM_BOT_TOKEN")
    telegram_admin_chat_id: int = Field(alias="TELEGRAM_ADMIN_CHAT_ID")
    telegram_start_description: str = Field(
        default=(
            "Здравствуйте! Чтобы начать работу с ботом, нажмите кнопку "
            "«Старт» внизу экрана или отправьте команду /start."
        ),
        alias="TELEGRAM_START_DESCRIPTION",
    )
    telegram_short_description: str = Field(
        default="Wood_Sava_Bot для сбора заявок и общения с менеджером.",
        alias="TELEGRAM_SHORT_DESCRIPTION",
    )

    vk_group_id: int | None = Field(default=None, alias="VK_GROUP_ID")
    vk_access_token: str | None = Field(default=None, alias="VK_ACCESS_TOKEN")
    vk_api_version: str = Field(default="5.199", alias="VK_API_VERSION")

    max_access_token: str | None = Field(default=None, alias="MAX_ACCESS_TOKEN")
    max_api_base_url: str = Field(
        default="https://platform-api.max.ru",
        alias="MAX_API_BASE_URL",
    )

    http_timeout_seconds: PositiveInt = Field(
        default=30,
        alias="HTTP_TIMEOUT_SECONDS",
    )
    polling_sleep_seconds: PositiveInt = Field(
        default=2,
        alias="POLLING_SLEEP_SECONDS",
    )

    @property
    def vk_enabled(self) -> bool:
        return bool(self.vk_group_id and self.vk_access_token)

    @property
    def max_enabled(self) -> bool:
        return bool(self.max_access_token)


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()

