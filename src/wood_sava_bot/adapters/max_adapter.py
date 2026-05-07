from __future__ import annotations

import asyncio
import logging
from pathlib import Path
from typing import Any

import httpx

from wood_sava_bot.config import Settings
from wood_sava_bot.domain.enums import AttachmentKind, Platform
from wood_sava_bot.domain.flows import (
    BUTTON_BACK,
    BUTTON_CANCEL,
    BUTTON_HOME,
    BUTTON_NEXT,
    BUTTON_START,
    detect_flow_from_text,
    start_buttons,
)
from wood_sava_bot.domain.models import Attachment, InboundMessage, OutboundMessage, SessionSnapshot

LOGGER = logging.getLogger(__name__)


class MaxCustomerAdapter:
    def __init__(self, settings: Settings, event_handler, telegram_api=None) -> None:
        self._settings = settings
        self._event_handler = event_handler
        self._telegram_api = telegram_api
        self._client = httpx.AsyncClient(timeout=settings.http_timeout_seconds)
        self._running = True
        self._marker: int | None = None

    async def poll_forever(self) -> None:
        if not self._settings.max_enabled:
            LOGGER.info("MAX adapter disabled because credentials are missing")
            return

        while self._running:
            try:
                params: dict[str, Any] = {
                    "timeout": 30,
                    "types": ["message_created", "bot_started"],
                }
                if self._marker is not None:
                    params["marker"] = self._marker
                response = await self._request("GET", "/updates", params=params)
                self._marker = response.get("marker")
                for update in response.get("updates", []):
                    parsed = self._parse_update(update)
                    if parsed:
                        await self._event_handler(parsed)
            except Exception:
                LOGGER.exception("MAX polling loop failed")
                await asyncio.sleep(self._settings.polling_sleep_seconds)

    async def send_outbound(
        self,
        session: SessionSnapshot,
        outbound: OutboundMessage,
    ) -> None:
        attachments = []
        for attachment in outbound.attachments:
            uploaded = await self._upload_attachment(attachment)
            if uploaded:
                attachments.append(uploaded)

        payload: dict[str, Any] = {}
        if outbound.text:
            payload["text"] = outbound.text
        if outbound.buttons:
            attachments.append(
                {
                    "type": "inline_keyboard",
                    "payload": {
                        "buttons": [
                            [
                                {
                                    "type": "message",
                                    "text": button.label,
                                }
                                for button in row
                            ]
                            for row in outbound.buttons
                        ]
                    },
                }
            )
        if attachments:
            payload["attachments"] = attachments
        await self._request("POST", "/messages", params={"chat_id": session.platform_chat_id}, json=payload)

    async def prompt_start(self, chat_id: str) -> None:
        await self.send_outbound(
            SessionSnapshot(
                platform=Platform.MAX,
                platform_user_id=chat_id,
                platform_chat_id=chat_id,
                username=None,
                display_name=None,
                is_started=False,
                telegram_topic_id=None,
                current_flow=None,
                current_step=0,
            ),
            OutboundMessage(
                text="Здравствуйте! Нажмите кнопку «Старт», чтобы запустить бота.",
                buttons=start_buttons(Platform.MAX),
            ),
        )

    async def shutdown(self) -> None:
        self._running = False
        await self._client.aclose()

    async def _request(
        self,
        method: str,
        path: str,
        *,
        params: dict[str, Any] | None = None,
        json: dict[str, Any] | None = None,
        files: dict[str, Any] | None = None,
        absolute_url: str | None = None,
    ) -> dict[str, Any]:
        if not self._settings.max_access_token:
            raise RuntimeError("MAX access token is not configured")
        response = await self._client.request(
            method,
            absolute_url or f"{self._settings.max_api_base_url}{path}",
            params=params,
            json=json,
            files=files,
            headers={"Authorization": self._settings.max_access_token},
        )
        response.raise_for_status()
        if not response.content:
            return {}
        return response.json()

    def _parse_update(self, update: dict[str, Any]) -> InboundMessage | None:
        update_type = update.get("update_type")
        if update_type == "bot_started":
            user = update["user"]
            return InboundMessage(
                platform=Platform.MAX,
                user_id=str(user["user_id"]),
                chat_id=str(update["chat_id"]),
                username=user.get("username"),
                display_name=user.get("name"),
                is_start=True,
                raw_event=update,
            )
        if update_type != "message_created":
            return None

        message = update["message"]
        sender = message.get("sender") or {}
        body = message.get("body") or {}
        text = (body.get("text") or "").strip()
        return InboundMessage(
            platform=Platform.MAX,
            user_id=str(sender["user_id"]),
            chat_id=str(message["recipient"]["chat_id"]),
            text=body.get("text"),
            username=sender.get("username"),
            display_name=sender.get("name"),
            message_id=message.get("message_id"),
            attachments=_parse_max_attachments(body.get("attachments", [])),
            is_start=text.lower() == BUTTON_START.lower(),
            is_cancel=text.lower() == BUTTON_CANCEL.lower(),
            is_home=text.lower() == BUTTON_HOME.lower(),
            is_back=text.lower() == BUTTON_BACK.lower(),
            is_next=text.lower() == BUTTON_NEXT.lower(),
            selected_flow=detect_flow_from_text(text),
            raw_event=update,
        )

    async def _upload_attachment(self, attachment: Attachment) -> dict[str, Any] | None:
        data, filename, mime_type = await self._materialize_attachment(attachment)
        if data is None:
            return None
        upload_type = "image" if attachment.kind is AttachmentKind.IMAGE else "file"
        upload_meta = await self._request("POST", "/uploads", params={"type": upload_type})
        upload = await self._request(
            "POST",
            "",
            absolute_url=upload_meta["url"],
            files={"data": (filename or attachment.name or "file.bin", data, mime_type or "application/octet-stream")},
        )
        payload = upload.get("payload") or upload
        return {"type": upload_type, "payload": payload}

    async def _materialize_attachment(
        self,
        attachment: Attachment,
    ) -> tuple[bytes | None, str | None, str | None]:
        if attachment.url:
            response = await self._client.get(attachment.url)
            response.raise_for_status()
            return response.content, attachment.name, attachment.mime_type
        if attachment.source_file_id and self._telegram_api is not None:
            data, file_path = await self._telegram_api.download_file(attachment.source_file_id)
            return data, Path(file_path).name, attachment.mime_type
        return None, None, None


def _parse_max_attachments(items: list[dict[str, Any]]) -> list[Attachment]:
    attachments: list[Attachment] = []
    for item in items:
        kind = item.get("type")
        payload = item.get("payload") or {}
        if kind == "image":
            attachments.append(
                Attachment(
                    kind=AttachmentKind.IMAGE,
                    url=payload.get("url"),
                    platform_payload=payload,
                )
            )
        elif kind not in {"inline_keyboard"}:
            attachments.append(
                Attachment(
                    kind=AttachmentKind.DOCUMENT,
                    name=payload.get("name"),
                    url=payload.get("url"),
                    platform_payload=payload,
                )
            )
    return attachments
