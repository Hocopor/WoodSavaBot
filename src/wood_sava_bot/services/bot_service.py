from __future__ import annotations

import logging
from typing import Any

from wood_sava_bot.domain.enums import FlowId, Platform
from wood_sava_bot.domain.flows import (
    BUTTON_BACK,
    BUTTON_HOME,
    BUTTON_NEXT,
    BUTTON_START,
    FLOW_DEFINITIONS,
    START_TEXT,
    THANK_YOU_TEXT,
    WELCOME_TEXT,
    cancel_buttons,
    format_question_text,
    flow_selection_text,
    home_buttons,
    main_menu_buttons,
    question_buttons,
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

        if message.is_back and session.current_flow is not None:
            if session.current_step <= 0:
                await self._send_current_question(session)
                return
            session = await self._repository.advance_flow(
                message.platform,
                message.user_id,
                session.current_step - 1,
            )
            await self._send_current_question(session)
            return

        if message.is_next and session.current_flow is not None:
            current_state = await self._repository.get_step_state(
                message.platform,
                message.user_id,
                session.current_step,
            )
            if current_state is None:
                await self._send_current_question(session)
                return
            flow_definition = FLOW_DEFINITIONS[session.current_flow]
            next_step = session.current_step + 1
            if next_step >= len(flow_definition.questions):
                await self._send_current_question(session)
                return
            session = await self._repository.advance_flow(
                message.platform,
                message.user_id,
                next_step,
            )
            await self._send_current_question(session)
            return

        if session.current_flow is None:
            flow = message.selected_flow
            if flow is None:
                await self._send_welcome(session)
                if session.telegram_topic_id:
                    await self._relay_customer_message(session, message, question=None)
                return
            session = await self._ensure_topic(session)
            session = await self._notify_topic(session, flow_selection_text(flow))
            session = await self._repository.start_flow(message.platform, message.user_id, flow)
            await self._send_current_question(session)
            return

        flow_definition = FLOW_DEFINITIONS[session.current_flow]
        question = flow_definition.questions[session.current_step]
        session = await self._ensure_topic(session)
        await self._replace_step_answer(session, message, question)
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
    ) -> list[int]:
        try:
            return await self._admin_hub.relay_user_message(session, message, question)
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
            return await self._admin_hub.relay_user_message(session, message, question)

    async def _notify_topic(self, session: SessionSnapshot, text: str) -> SessionSnapshot:
        if session.telegram_topic_id is None:
            raise RuntimeError("Telegram topic is not linked to session")
        try:
            await self._admin_hub.notify_topic(session.telegram_topic_id, text)
            return session
        except Exception as exc:
            if not self._admin_hub.is_missing_topic_error(exc):
                raise
            LOGGER.warning(
                "Telegram topic %s is missing for %s:%s during service notice, recreating",
                session.telegram_topic_id,
                session.platform.value,
                session.platform_user_id,
            )
            session = await self._repository.clear_topic_id(
                session.platform,
                session.platform_user_id,
            )
            session = await self._ensure_topic(session)
            await self._admin_hub.notify_topic(session.telegram_topic_id, text)
            return session

    async def _send_welcome(self, session: SessionSnapshot) -> None:
        await self._adapters[session.platform].send_outbound(
            session,
            OutboundMessage(text=WELCOME_TEXT, buttons=main_menu_buttons()),
        )

    async def _send_current_question(self, session: SessionSnapshot) -> None:
        if session.current_flow is None:
            raise RuntimeError("Current flow is not set")
        flow = FLOW_DEFINITIONS[session.current_flow]
        current_state = await self._repository.get_step_state(
            session.platform,
            session.platform_user_id,
            session.current_step,
        )
        await self._adapters[session.platform].send_outbound(
            session,
            OutboundMessage(
                text=format_question_text(
                    flow.questions[session.current_step],
                    previous_answer=current_state.answer_preview if current_state else None,
                ),
                buttons=question_buttons(
                    can_go_back=session.current_step > 0,
                    can_go_next=current_state is not None,
                ),
            ),
        )

    async def _replace_step_answer(
        self,
        session: SessionSnapshot,
        message: InboundMessage,
        question: str,
    ) -> None:
        obsolete_state = await self._repository.clear_step_state(
            session.platform,
            session.platform_user_id,
            session.current_step,
        )
        obsolete_message_ids = obsolete_state.admin_message_ids if obsolete_state else []
        if obsolete_message_ids:
            await self._admin_hub.delete_topic_messages(obsolete_message_ids)

        admin_message_ids = await self._relay_customer_message(session, message, question)
        await self._repository.save_step_state(
            session.platform,
            session.platform_user_id,
            session.current_step,
            self._answer_preview(message),
            admin_message_ids,
        )

    @staticmethod
    def _answer_preview(message: InboundMessage) -> str:
        if message.text and message.attachments:
            return f"{message.text} (+ {len(message.attachments)} влож.)"
        if message.text:
            return message.text
        if message.attachments:
            names = [attachment.name or attachment.kind.value for attachment in message.attachments]
            return ", ".join(names)
        return "пустой ответ"
