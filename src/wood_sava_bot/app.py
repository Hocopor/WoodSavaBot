from __future__ import annotations

import asyncio
import logging

from wood_sava_bot.adapters.max_adapter import MaxCustomerAdapter
from wood_sava_bot.adapters.telegram import TelegramAdminHub, TelegramBotAPI, TelegramCustomerAdapter
from wood_sava_bot.adapters.vk import VKCustomerAdapter
from wood_sava_bot.config import Settings
from wood_sava_bot.domain.enums import Platform
from wood_sava_bot.services.bot_service import BotService
from wood_sava_bot.storage.db import build_engine, build_session_factory
from wood_sava_bot.storage.repositories import SessionRepository

LOGGER = logging.getLogger(__name__)


class Application:
    def __init__(self, settings: Settings) -> None:
        self._settings = settings
        self._engine = build_engine(settings.database_url)
        self._session_factory = build_session_factory(self._engine)
        self._repository = SessionRepository(self._session_factory)

        self._telegram_api = TelegramBotAPI(
            settings.telegram_bot_token,
            settings.http_timeout_seconds,
        )
        self._admin_hub = TelegramAdminHub(
            self._telegram_api,
            settings.telegram_admin_chat_id,
        )
        self._service: BotService | None = None
        self._adapters: dict[Platform, object] = {}

    async def startup(self) -> None:
        await self._repository.init_schema(self._engine)

        async def customer_handler(message):
            await self._service.handle_customer_message(message)

        async def admin_handler(message):
            await self._service.handle_admin_message(message)

        telegram_adapter = TelegramCustomerAdapter(
            self._settings,
            self._telegram_api,
            customer_handler,
            admin_handler,
        )
        vk_adapter = VKCustomerAdapter(self._settings, customer_handler, telegram_api=self._telegram_api)
        max_adapter = MaxCustomerAdapter(self._settings, customer_handler, telegram_api=self._telegram_api)
        self._adapters = {
            Platform.TELEGRAM: telegram_adapter,
            Platform.VK: vk_adapter,
            Platform.MAX: max_adapter,
        }
        self._service = BotService(self._repository, self._admin_hub, self._adapters)

    async def run(self) -> None:
        if self._service is None:
            await self.startup()

        telegram_adapter = self._adapters[Platform.TELEGRAM]
        vk_adapter = self._adapters[Platform.VK]
        max_adapter = self._adapters[Platform.MAX]

        async with asyncio.TaskGroup() as group:
            group.create_task(telegram_adapter.poll_forever())
            group.create_task(vk_adapter.poll_forever())
            group.create_task(max_adapter.poll_forever())

    async def shutdown(self) -> None:
        for adapter in self._adapters.values():
            await adapter.shutdown()
        await self._engine.dispose()
