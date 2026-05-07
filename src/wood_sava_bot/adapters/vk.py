from __future__ import annotations

import asyncio
import json
import logging
import random
from pathlib import Path
from typing import Any

import httpx

from wood_sava_bot.config import Settings
from wood_sava_bot.domain.enums import AttachmentKind, Platform
from wood_sava_bot.domain.flows import BUTTON_CANCEL, BUTTON_HOME, BUTTON_START, detect_flow_from_text, start_buttons
from wood_sava_bot.domain.models import Attachment, InboundMessage, OutboundMessage, SessionSnapshot

LOGGER = logging.getLogger(__name__)


class VKCustomerAdapter:
    def __init__(self, settings: Settings, event_handler, telegram_api=None) -> None:
        self._settings = settings
        self._event_handler = event_handler
        self._telegram_api = telegram_api
        self._client = httpx.AsyncClient(timeout=settings.http_timeout_seconds)
        self._running = True
        self._user_cache: dict[str, tuple[str | None, str | None]] = {}

    async def poll_forever(self) -> None:
        if not self._settings.vk_enabled:
            LOGGER.info("VK adapter disabled because credentials are missing")
            return

        ts = None
        while self._running:
            try:
                server_info = await self._api("groups.getLongPollServer", {"group_id": self._settings.vk_group_id})
                server = server_info["server"]
                key = server_info["key"]
                ts = server_info["ts"] if ts is None else ts
                while self._running:
                    response = await self._client.get(
                        server,
                        params={"act": "a_check", "key": key, "ts": ts, "wait": 25},
                    )
                    response.raise_for_status()
                    body = response.json()
                    if "failed" in body:
                        ts = None
                        break
                    ts = body["ts"]
                    for update in body.get("updates", []):
                        parsed = await self._parse_update(update)
                        if parsed:
                            await self._event_handler(parsed)
            except Exception:
                LOGGER.exception("VK polling loop failed")
                await asyncio.sleep(self._settings.polling_sleep_seconds)

    async def send_outbound(
        self,
        session: SessionSnapshot,
        outbound: OutboundMessage,
    ) -> None:
        attachment_value = None
        if outbound.attachments:
            attachment_value = await self._upload_attachment(outbound.attachments[0], session)

        payload: dict[str, Any] = {
            "user_id": session.platform_user_id,
            "random_id": random.randint(1, 2_000_000_000),
        }
        if outbound.text:
            payload["message"] = outbound.text
        if outbound.buttons:
            payload["keyboard"] = json.dumps(_vk_keyboard(outbound))
        if attachment_value:
            payload["attachment"] = attachment_value
        await self._api("messages.send", payload)

    async def prompt_start(self, chat_id: str) -> None:
        await self._api(
            "messages.send",
            {
                "user_id": chat_id,
                "random_id": random.randint(1, 2_000_000_000),
                "message": "Здравствуйте! Нажмите кнопку «Старт», чтобы запустить бота.",
                "keyboard": json.dumps(
                    _vk_keyboard(
                        OutboundMessage(
                            buttons=start_buttons(Platform.VK),
                        )
                    )
                ),
            },
        )

    async def shutdown(self) -> None:
        self._running = False
        await self._client.aclose()

    async def _api(self, method: str, params: dict[str, Any]) -> dict[str, Any]:
        if not self._settings.vk_access_token:
            raise RuntimeError("VK access token is not configured")
        payload = {
            **params,
            "access_token": self._settings.vk_access_token,
            "v": self._settings.vk_api_version,
        }
        response = await self._client.post(f"https://api.vk.com/method/{method}", data=payload)
        response.raise_for_status()
        body = response.json()
        if "error" in body:
            raise RuntimeError(f"VK API error for {method}: {body['error']}")
        return body["response"]

    async def _parse_update(self, update: dict[str, Any]) -> InboundMessage | None:
        if update.get("type") != "message_new":
            return None
        message = update["object"]["message"]
        text = (message.get("text") or "").strip()
        attachments = _parse_vk_attachments(message.get("attachments", []))
        user_id = str(message["from_id"])
        display_name, username = await self._get_user_identity(user_id)
        return InboundMessage(
            platform=Platform.VK,
            user_id=user_id,
            chat_id=user_id,
            text=message.get("text"),
            display_name=display_name,
            username=username,
            message_id=message.get("id"),
            attachments=attachments,
            is_start=text.lower() == BUTTON_START.lower(),
            is_cancel=text.lower() == BUTTON_CANCEL.lower(),
            is_home=text.lower() == BUTTON_HOME.lower(),
            selected_flow=detect_flow_from_text(text),
            raw_event=update,
        )

    async def _get_user_identity(self, user_id: str) -> tuple[str | None, str | None]:
        cached = self._user_cache.get(user_id)
        if cached is not None:
            return cached

        try:
            users = await self._api(
                "users.get",
                {
                    "user_ids": user_id,
                    "fields": "screen_name",
                },
            )
        except Exception:
            LOGGER.exception("Failed to load VK user profile for %s", user_id)
            return None, None

        if not users:
            return None, None

        user = users[0]
        first_name = user.get("first_name")
        last_name = user.get("last_name")
        display_name = " ".join(part for part in [first_name, last_name] if part) or None
        screen_name = user.get("screen_name")
        username = f"vk.com/{screen_name}" if screen_name else f"vk.com/id{user_id}"
        result = (display_name, username)
        self._user_cache[user_id] = result
        return result

    async def _upload_attachment(self, attachment: Attachment, session: SessionSnapshot) -> str | None:
        data, filename, mime_type = await self._materialize_attachment(attachment)
        if data is None:
            return None

        if attachment.kind is AttachmentKind.IMAGE:
            server = await self._api("photos.getMessagesUploadServer", {"peer_id": session.platform_user_id})
            files = {"photo": (filename or "image.jpg", data, mime_type or "image/jpeg")}
            response = await self._client.post(server["upload_url"], files=files)
            response.raise_for_status()
            uploaded = response.json()
            saved = await self._api(
                "photos.saveMessagesPhoto",
                {
                    "photo": uploaded["photo"],
                    "server": uploaded["server"],
                    "hash": uploaded["hash"],
                },
            )
            photo = saved[0]
            return f"photo{photo['owner_id']}_{photo['id']}"

        if data is not None:
            server = await self._api("docs.getMessagesUploadServer", {"type": "doc", "peer_id": session.platform_user_id})
            files = {"file": (filename or attachment.name or "document.bin", data, mime_type or "application/octet-stream")}
            response = await self._client.post(server["upload_url"], files=files)
            response.raise_for_status()
            uploaded = response.json()
            saved = await self._api("docs.save", {"file": uploaded["file"]})
            doc = saved["doc"]
            return f"doc{doc['owner_id']}_{doc['id']}"
        return None

    async def _materialize_attachment(
        self,
        attachment: Attachment,
    ) -> tuple[bytes | None, str | None, str | None]:
        if attachment.url:
            data = await _download_for_upload(self._client, attachment.url)
            return data, attachment.name, attachment.mime_type
        if attachment.source_file_id and self._telegram_api is not None:
            data, file_path = await self._telegram_api.download_file(attachment.source_file_id)
            return data, Path(file_path).name, attachment.mime_type
        return None, None, None


def _vk_keyboard(outbound: OutboundMessage) -> dict[str, Any]:
    return {
        "one_time": False,
        "buttons": [
            [
                {
                    "action": {"type": "text", "label": button.label},
                    "color": "primary",
                }
                for button in row
            ]
            for row in outbound.buttons
        ],
    }


def _parse_vk_attachments(items: list[dict[str, Any]]) -> list[Attachment]:
    attachments: list[Attachment] = []
    for item in items:
        kind = item.get("type")
        if kind == "photo":
            sizes = item["photo"].get("sizes", [])
            url = sizes[-1]["url"] if sizes else None
            attachments.append(Attachment(kind=AttachmentKind.IMAGE, url=url))
        elif kind == "doc":
            doc = item["doc"]
            attachments.append(
                Attachment(
                    kind=AttachmentKind.DOCUMENT,
                    name=doc.get("title"),
                    url=doc.get("url"),
                    mime_type=doc.get("ext"),
                )
            )
    return attachments


async def _download_for_upload(client: httpx.AsyncClient, url: str | None) -> bytes:
    if not url:
        raise RuntimeError("Attachment URL is required for upload")
    response = await client.get(url)
    response.raise_for_status()
    return response.content
