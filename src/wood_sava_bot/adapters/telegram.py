from __future__ import annotations

import asyncio
import logging
from typing import Any

import httpx

from wood_sava_bot.config import Settings
from wood_sava_bot.domain.enums import AttachmentKind, FlowId, Platform
from wood_sava_bot.domain.flows import (
    BUTTON_CANCEL,
    BUTTON_HOME,
    BUTTON_START,
    cancel_buttons,
    detect_flow_from_text,
    home_buttons,
    main_menu_buttons,
    start_buttons,
    topic_title,
)
from wood_sava_bot.domain.models import Attachment, InboundMessage, OutboundMessage, SessionSnapshot

LOGGER = logging.getLogger(__name__)


class TelegramBotAPI:
    def __init__(self, token: str, timeout_seconds: int) -> None:
        self._token = token
        self._base_url = f"https://api.telegram.org/bot{token}"
        self._file_base_url = f"https://api.telegram.org/file/bot{token}"
        self._client = httpx.AsyncClient(timeout=timeout_seconds)

    async def close(self) -> None:
        await self._client.aclose()

    async def get_me(self) -> dict[str, Any]:
        return await self._request("getMe")

    async def get_updates(
        self,
        offset: int | None,
        timeout: int = 30,
    ) -> list[dict[str, Any]]:
        payload: dict[str, Any] = {
            "timeout": timeout,
            "allowed_updates": ["message", "my_chat_member"],
        }
        if offset is not None:
            payload["offset"] = offset
        response = await self._request("getUpdates", payload)
        return response

    async def send_message(
        self,
        chat_id: int | str,
        text: str,
        *,
        message_thread_id: int | None = None,
        reply_markup: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        payload: dict[str, Any] = {"chat_id": chat_id, "text": text}
        if message_thread_id is not None:
            payload["message_thread_id"] = message_thread_id
        if reply_markup is not None:
            payload["reply_markup"] = reply_markup
        return await self._request("sendMessage", payload)

    async def send_photo(
        self,
        chat_id: int | str,
        photo: str,
        *,
        caption: str | None = None,
        message_thread_id: int | None = None,
    ) -> dict[str, Any]:
        payload: dict[str, Any] = {"chat_id": chat_id, "photo": photo}
        if caption:
            payload["caption"] = caption
        if message_thread_id is not None:
            payload["message_thread_id"] = message_thread_id
        return await self._request("sendPhoto", payload)

    async def send_document(
        self,
        chat_id: int | str,
        document: str,
        *,
        caption: str | None = None,
        message_thread_id: int | None = None,
    ) -> dict[str, Any]:
        payload: dict[str, Any] = {"chat_id": chat_id, "document": document}
        if caption:
            payload["caption"] = caption
        if message_thread_id is not None:
            payload["message_thread_id"] = message_thread_id
        return await self._request("sendDocument", payload)

    async def copy_message(
        self,
        chat_id: int | str,
        from_chat_id: int | str,
        message_id: int | str,
        *,
        message_thread_id: int | None = None,
    ) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "chat_id": chat_id,
            "from_chat_id": from_chat_id,
            "message_id": message_id,
        }
        if message_thread_id is not None:
            payload["message_thread_id"] = message_thread_id
        return await self._request("copyMessage", payload)

    async def create_forum_topic(
        self,
        chat_id: int,
        name: str,
    ) -> dict[str, Any]:
        return await self._request("createForumTopic", {"chat_id": chat_id, "name": name})

    async def set_my_description(self, description: str) -> None:
        await self._request("setMyDescription", {"description": description})

    async def set_my_short_description(self, short_description: str) -> None:
        await self._request(
            "setMyShortDescription",
            {"short_description": short_description},
        )

    async def get_file(self, file_id: str) -> dict[str, Any]:
        return await self._request("getFile", {"file_id": file_id})

    async def get_chat(self, chat_id: int | str) -> dict[str, Any]:
        return await self._request("getChat", {"chat_id": chat_id})

    async def download_file(self, file_id: str) -> tuple[bytes, str]:
        payload = await self.get_file(file_id)
        file_path = payload["file_path"]
        response = await self._client.get(f"{self._file_base_url}/{file_path}")
        response.raise_for_status()
        return response.content, file_path

    async def _request(self, method: str, payload: dict[str, Any] | None = None) -> Any:
        response = await self._client.post(f"{self._base_url}/{method}", json=payload or {})
        response.raise_for_status()
        body = response.json()
        if not body.get("ok", False):
            raise RuntimeError(f"Telegram API error for {method}: {body}")
        return body["result"]


def _reply_keyboard(button_rows: list[list[str]]) -> dict[str, Any]:
    return {
        "keyboard": [[{"text": label} for label in row] for row in button_rows],
        "resize_keyboard": True,
        "is_persistent": True,
    }


def _remove_keyboard() -> dict[str, Any]:
    return {"remove_keyboard": True}


class TelegramAdminHub:
    def __init__(self, api: TelegramBotAPI, admin_chat_resolver) -> None:
        self._api = api
        self._admin_chat_resolver = admin_chat_resolver

    async def ensure_topic(self, session: SessionSnapshot) -> int:
        if session.telegram_topic_id is not None:
            return session.telegram_topic_id
        admin_chat_id = await self._admin_chat_resolver.get_required_admin_chat_id()
        topic = await self._api.create_forum_topic(
            admin_chat_id,
            topic_title(session.platform, session.display_name, session.username),
        )
        return topic["message_thread_id"]

    async def relay_user_message(
        self,
        session: SessionSnapshot,
        message: InboundMessage,
        question: str | None,
    ) -> None:
        if session.telegram_topic_id is None:
            raise RuntimeError("Telegram topic is not linked to session")
        admin_chat_id = await self._admin_chat_resolver.get_required_admin_chat_id()

        if question:
            answer = summarize_answer(message)
            await self._api.send_message(
                admin_chat_id,
                f"{question}: {answer}",
                message_thread_id=session.telegram_topic_id,
            )
        elif message.text:
            await self._api.send_message(
                admin_chat_id,
                message.text,
                message_thread_id=session.telegram_topic_id,
            )

        for attachment in message.attachments:
            await self._relay_attachment(session.telegram_topic_id, attachment)

    async def notify_topic(self, telegram_topic_id: int, text: str) -> None:
        admin_chat_id = await self._admin_chat_resolver.get_required_admin_chat_id()
        await self._api.send_message(
            admin_chat_id,
            text,
            message_thread_id=telegram_topic_id,
        )

    async def _relay_attachment(self, topic_id: int, attachment: Attachment) -> None:
        if attachment.source_chat_id and attachment.source_message_id and attachment.source_file_id:
            admin_chat_id = await self._admin_chat_resolver.get_required_admin_chat_id()
            await self._api.copy_message(
                admin_chat_id,
                attachment.source_chat_id,
                attachment.source_message_id,
                message_thread_id=topic_id,
            )
            return
        if attachment.url:
            if attachment.kind is AttachmentKind.IMAGE:
                admin_chat_id = await self._admin_chat_resolver.get_required_admin_chat_id()
                await self._api.send_photo(
                    admin_chat_id,
                    attachment.url,
                    caption=attachment.name,
                    message_thread_id=topic_id,
                )
            else:
                admin_chat_id = await self._admin_chat_resolver.get_required_admin_chat_id()
                await self._api.send_document(
                    admin_chat_id,
                    attachment.url,
                    caption=attachment.name,
                    message_thread_id=topic_id,
                )
            return
        await self.notify_topic(topic_id, "Не удалось переслать вложение в Telegram-тему.")


class TelegramCustomerAdapter:
    def __init__(
        self,
        settings: Settings,
        api: TelegramBotAPI,
        event_handler,
        admin_message_handler,
        group_event_handler,
    ) -> None:
        self._settings = settings
        self._api = api
        self._event_handler = event_handler
        self._admin_message_handler = admin_message_handler
        self._group_event_handler = group_event_handler
        self._bot_user_id: int | None = None
        self._offset: int | None = None
        self._running = True

    async def bootstrap(self) -> None:
        me = await self._api.get_me()
        self._bot_user_id = me["id"]
        await self._api.set_my_description(self._settings.telegram_start_description)
        await self._api.set_my_short_description(self._settings.telegram_short_description)

    async def poll_forever(self) -> None:
        while self._running:
            try:
                if self._bot_user_id is None:
                    await self.bootstrap()
                updates = await self._api.get_updates(self._offset, timeout=30)
                for update in updates:
                    self._offset = update["update_id"] + 1
                    if my_chat_member := update.get("my_chat_member"):
                        await self._group_event_handler(my_chat_member, from_membership=True)
                        continue
                    message = update.get("message")
                    if not message:
                        continue
                    parsed = self._parse_message(message)
                    if parsed is None:
                        continue
                    chat = message.get("chat") or {}
                    if chat.get("type") in {"group", "supergroup"}:
                        await self._group_event_handler(message, from_membership=False)
                    else:
                        await self._event_handler(parsed)
            except Exception:
                LOGGER.exception("Telegram polling loop failed")
                await asyncio.sleep(self._settings.polling_sleep_seconds)

    async def send_outbound(
        self,
        session: SessionSnapshot,
        outbound: OutboundMessage,
    ) -> None:
        if outbound.copy_source_chat_id and outbound.copy_source_message_id:
            await self._api.copy_message(
                session.platform_chat_id,
                outbound.copy_source_chat_id,
                outbound.copy_source_message_id,
            )
            return

        reply_markup = None
        if outbound.remove_keyboard:
            reply_markup = _remove_keyboard()
        elif outbound.buttons:
            reply_markup = _reply_keyboard(
                [[button.label for button in row] for row in outbound.buttons]
            )

        if outbound.attachments:
            first = outbound.attachments[0]
            if first.kind is AttachmentKind.IMAGE and first.url:
                await self._api.send_photo(
                    session.platform_chat_id,
                    first.url,
                    caption=outbound.text,
                )
                return
            if first.url:
                await self._api.send_document(
                    session.platform_chat_id,
                    first.url,
                    caption=outbound.text,
                )
                return

        if outbound.text:
            await self._api.send_message(
                session.platform_chat_id,
                outbound.text,
                reply_markup=reply_markup,
            )

    async def prompt_start(self, chat_id: str) -> None:
        await self._api.send_message(
            chat_id,
            "Здравствуйте! Нажмите кнопку «Старт», чтобы запустить бота.",
            reply_markup=_reply_keyboard([[button.label for button in row] for row in start_buttons(Platform.TELEGRAM)]),
        )

    async def shutdown(self) -> None:
        self._running = False
        await self._api.close()

    def _parse_message(self, payload: dict[str, Any]) -> InboundMessage | None:
        sender = payload.get("from") or {}
        if sender.get("is_bot") and sender.get("id") == self._bot_user_id:
            return None

        chat = payload.get("chat") or {}
        text = payload.get("text")
        attachments: list[Attachment] = []
        if photos := payload.get("photo"):
            largest = photos[-1]
            attachments.append(
                Attachment(
                    kind=AttachmentKind.IMAGE,
                    source_file_id=largest["file_id"],
                    source_message_id=payload["message_id"],
                    source_chat_id=chat["id"],
                )
            )
        if document := payload.get("document"):
            attachments.append(
                Attachment(
                    kind=AttachmentKind.DOCUMENT,
                    name=document.get("file_name"),
                    mime_type=document.get("mime_type"),
                    source_file_id=document["file_id"],
                    source_message_id=payload["message_id"],
                    source_chat_id=chat["id"],
                )
            )

        normalized_text = (text or "").strip()
        flow = detect_flow_from_text(normalized_text)
        return InboundMessage(
            platform=Platform.TELEGRAM,
            user_id=str(sender.get("id", chat.get("id"))),
            chat_id=str(chat["id"]),
            text=text,
            username=sender.get("username"),
            display_name=sender.get("first_name") or sender.get("last_name"),
            message_id=payload["message_id"],
            attachments=attachments,
            is_start=normalized_text == "/start" or normalized_text.lower() == BUTTON_START.lower(),
            is_cancel=normalized_text.lower() == BUTTON_CANCEL.lower(),
            is_home=normalized_text.lower() == BUTTON_HOME.lower(),
            selected_flow=flow,
            thread_id=payload.get("message_thread_id"),
            raw_event=payload,
        )


def summarize_answer(message: InboundMessage) -> str:
    if message.text and message.attachments:
        return f"{message.text} (+ {len(message.attachments)} влож.)"
    if message.text:
        return message.text
    if message.attachments:
        names = [attachment.name or attachment.kind.value for attachment in message.attachments]
        return ", ".join(names)
    return "пустой ответ"
