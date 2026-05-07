from __future__ import annotations

import logging
from typing import Any

from wood_sava_bot.domain.enums import FlowId, Platform
from wood_sava_bot.domain.flows import (
    BUTTON_HOME,
    BUTTON_START,
    FLOW_DEFINITIONS,
    START_TEXT,
    THANK_YOU_TEXT,
    WELCOME_TEXT,
    cancel_buttons,
    home_buttons,
    main_menu_buttons,
)
from wood_sava_bot.domain.models import InboundMessage, OutboundMessage, SessionSnapshot
from wood_sava_bot.storage.repositories import SessionRepository

LOGGER = logging.getLogger(__name__)


class BotService:
    def __init__(
        self,
        repository: SessionRepository,
        admin_hub,
        adapters: dict[Platform, Any],
    ) -> None:
        self._repository = repository
        self._admin_hub = admin_hub
        self._adapters = adapters

    async def handle_customer_message(self, message: InboundMessage) -> None:
        session = await self._repository.upsert_user(
            message.platform,
            message.user_id,
            message.chat_id,
            message.username,
            message.display_name,
        )

        if not session.is_started and not message.is_start:
            await self._adapters[message.platform].prompt_start(message.chat_id)
            return

        if message.is_start:
            session = await self._repository.mark_started(message.platform, message.user_id)
            session = await self._ensure_topic(session)
            await self._send_welcome(session)
            return

        if message.is_cancel or message.is_home:
            session = await self._repository.reset_flow(message.platform, message.user_id)
            await self._send_welcome(session)
            return

        if not session.is_started:
            await self._adapters[message.platform].prompt_start(message.chat_id)
            return

        if session.current_flow is None:
            flow = message.selected_flow
            if flow is None:
                await self._send_welcome(session)
                if session.telegram_topic_id:
                    await self._relay_customer_message(session, message, question=None)
                return
            session = await self._repository.start_flow(message.platform, message.user_id, flow)
            await self._send_current_question(session)
            return

        flow_definition = FLOW_DEFINITIONS[session.current_flow]
        question = flow_definition.questions[session.current_step]
        session = await self._ensure_topic(session)
        await self._relay_customer_message(session, message, question)
        next_step = session.current_step + 1

        if next_step >= len(flow_definition.questions):
            session = await self._repository.reset_flow(message.platform, message.user_id)
            await self._adapters[message.platform].send_outbound(
                session,
                OutboundMessage(text=THANK_YOU_TEXT, buttons=home_buttons()),
            )
            return

        session = await self._repository.advance_flow(message.platform, message.user_id, next_step)
        await self._send_current_question(session)

    async def handle_admin_message(self, message: InboundMessage) -> None:
        if message.thread_id is None:
            return
        session = await self._repository.get_by_topic_id(message.thread_id)
        if session is None:
            return

        outbound = OutboundMessage(
            text=message.text,
            attachments=message.attachments,
        )
        if message.platform is Platform.TELEGRAM and message.message_id is not None:
            outbound.copy_source_chat_id = message.chat_id
            outbound.copy_source_message_id = message.message_id
        try:
            await self._adapters[session.platform].send_outbound(session, outbound)
        except Exception as exc:
            LOGGER.exception("Failed to relay admin message to customer")
            await self._admin_hub.notify_topic(
                session.telegram_topic_id,
                f"Не удалось отправить сообщение пользователю: {exc}",
            )

    async def _ensure_topic(self, session: SessionSnapshot) -> SessionSnapshot:
        if session.telegram_topic_id is not None:
            return session
        topic_id = await self._admin_hub.ensure_topic(session)
        return await self._repository.set_topic_id(
            session.platform,
            session.platform_user_id,
            topic_id,
        )

    async def _relay_customer_message(
        self,
        session: SessionSnapshot,
        message: InboundMessage,
        question: str | None,
    ) -> None:
        try:
            await self._admin_hub.relay_user_message(session, message, question)
        except Exception as exc:
            if not self._admin_hub.is_missing_topic_error(exc):
                raise
            LOGGER.warning(
                "Telegram topic %s is missing for %s:%s, recreating",
                session.telegram_topic_id,
                session.platform.value,
                session.platform_user_id,
            )
            session = await self._repository.clear_topic_id(
                session.platform,
                session.platform_user_id,
            )
            session = await self._ensure_topic(session)
            await self._admin_hub.relay_user_message(session, message, question)

    async def _send_welcome(self, session: SessionSnapshot) -> None:
        await self._adapters[session.platform].send_outbound(
            session,
            OutboundMessage(text=WELCOME_TEXT, buttons=main_menu_buttons()),
        )

    async def _send_current_question(self, session: SessionSnapshot) -> None:
        if session.current_flow is None:
            raise RuntimeError("Current flow is not set")
        flow = FLOW_DEFINITIONS[session.current_flow]
        await self._adapters[session.platform].send_outbound(
            session,
            OutboundMessage(
                text=flow.questions[session.current_step],
                buttons=cancel_buttons(),
            ),
        )
