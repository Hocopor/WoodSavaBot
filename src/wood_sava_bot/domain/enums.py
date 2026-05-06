from __future__ import annotations

from enum import Enum


class Platform(str, Enum):
    TELEGRAM = "telegram"
    VK = "vk"
    MAX = "max"


class FlowId(str, Enum):
    READY_MADE = "ready_made"
    DESIGNER_PROJECT = "designer_project"
    CUSTOM_DIMENSIONS = "custom_dimensions"


class AttachmentKind(str, Enum):
    IMAGE = "image"
    DOCUMENT = "document"
    VIDEO = "video"
    AUDIO = "audio"
    UNKNOWN = "unknown"

