from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from wood_sava_bot.domain.enums import AttachmentKind, FlowId, Platform


@dataclass(slots=True)
class Attachment:
    kind: AttachmentKind
    name: str | None = None
    mime_type: str | None = None
    url: str | None = None
    source_file_id: str | None = None
    source_message_id: int | str | None = None
    source_chat_id: int | str | None = None
    platform_payload: dict[str, Any] | None = None


@dataclass(slots=True)
class Button:
    label: str
    value: str | None = None


@dataclass(slots=True)
class OutboundMessage:
    text: str | None = None
    buttons: list[list[Button]] = field(default_factory=list)
    attachments: list[Attachment] = field(default_factory=list)
    remove_keyboard: bool = False
    copy_source_chat_id: int | str | None = None
    copy_source_message_id: int | str | None = None


@dataclass(slots=True)
class InboundMessage:
    platform: Platform
    user_id: str
    chat_id: str
    text: str | None = None
    username: str | None = None
    display_name: str | None = None
    message_id: int | str | None = None
    attachments: list[Attachment] = field(default_factory=list)
    is_start: bool = False
    is_cancel: bool = False
    is_home: bool = False
    is_back: bool = False
    is_next: bool = False
    selected_flow: FlowId | None = None
    thread_id: int | None = None
    callback_query_id: str | None = None
    raw_event: dict[str, Any] | None = None


@dataclass(slots=True)
class SessionSnapshot:
    platform: Platform
    platform_user_id: str
    platform_chat_id: str
    username: str | None
    display_name: str | None
    is_started: bool
    telegram_topic_id: int | None
    current_flow: FlowId | None
    current_step: int


@dataclass(slots=True)
class AdminGroupSnapshot:
    chat_id: int
    title: str | None
    chat_type: str
    forum_enabled: bool
    is_active: bool


@dataclass(slots=True)
class FlowStepStateSnapshot:
    step_index: int
    answer_preview: str
    admin_message_ids: list[int]
