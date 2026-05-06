from __future__ import annotations

from typing import Protocol

from wood_sava_bot.domain.models import InboundMessage, OutboundMessage, SessionSnapshot


class CustomerAdapter(Protocol):
    async def poll_forever(self) -> None: ...

    async def send_outbound(
        self,
        session: SessionSnapshot,
        outbound: OutboundMessage,
    ) -> None: ...

    async def prompt_start(
        self,
        chat_id: str,
    ) -> None: ...

    async def shutdown(self) -> None: ...


class AdminRelay(Protocol):
    async def ensure_topic(self, session: SessionSnapshot) -> int: ...

    async def relay_user_message(
        self,
        session: SessionSnapshot,
        message: InboundMessage,
        question: str | None,
    ) -> None: ...

    async def notify_topic(
        self,
        telegram_topic_id: int,
        text: str,
    ) -> None: ...

