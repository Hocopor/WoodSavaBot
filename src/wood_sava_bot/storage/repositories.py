from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from wood_sava_bot.domain.enums import FlowId, Platform
from wood_sava_bot.domain.models import SessionSnapshot
from wood_sava_bot.storage.models import Base, UserSessionModel


class SessionRepository:
    def __init__(self, session_factory: async_sessionmaker[AsyncSession]) -> None:
        self._session_factory = session_factory

    async def init_schema(self, engine) -> None:
        async with engine.begin() as connection:
            await connection.run_sync(Base.metadata.create_all)

    async def get_by_platform_user(
        self,
        platform: Platform,
        platform_user_id: str,
    ) -> SessionSnapshot | None:
        async with self._session_factory() as session:
            query = select(UserSessionModel).where(
                UserSessionModel.platform == platform.value,
                UserSessionModel.platform_user_id == platform_user_id,
            )
            record = await session.scalar(query)
            return self._to_snapshot(record) if record else None

    async def get_by_topic_id(self, telegram_topic_id: int) -> SessionSnapshot | None:
        async with self._session_factory() as session:
            query = select(UserSessionModel).where(
                UserSessionModel.telegram_topic_id == telegram_topic_id,
            )
            record = await session.scalar(query)
            return self._to_snapshot(record) if record else None

    async def upsert_user(
        self,
        platform: Platform,
        platform_user_id: str,
        platform_chat_id: str,
        username: str | None,
        display_name: str | None,
    ) -> SessionSnapshot:
        async with self._session_factory() as session:
            query = select(UserSessionModel).where(
                UserSessionModel.platform == platform.value,
                UserSessionModel.platform_user_id == platform_user_id,
            )
            record = await session.scalar(query)
            if record is None:
                record = UserSessionModel(
                    platform=platform.value,
                    platform_user_id=platform_user_id,
                    platform_chat_id=platform_chat_id,
                    username=username,
                    display_name=display_name,
                )
                session.add(record)
            else:
                record.platform_chat_id = platform_chat_id
                record.username = username or record.username
                record.display_name = display_name or record.display_name
            await session.commit()
            await session.refresh(record)
            return self._to_snapshot(record)

    async def mark_started(
        self,
        platform: Platform,
        platform_user_id: str,
    ) -> SessionSnapshot:
        async with self._session_factory() as session:
            record = await session.scalar(
                select(UserSessionModel).where(
                    UserSessionModel.platform == platform.value,
                    UserSessionModel.platform_user_id == platform_user_id,
                )
            )
            if record is None:
                raise LookupError("Session not found for mark_started")
            record.is_started = True
            record.current_flow = None
            record.current_step = 0
            record.flow_status = None
            await session.commit()
            await session.refresh(record)
            return self._to_snapshot(record)

    async def set_topic_id(
        self,
        platform: Platform,
        platform_user_id: str,
        telegram_topic_id: int,
    ) -> SessionSnapshot:
        async with self._session_factory() as session:
            record = await session.scalar(
                select(UserSessionModel).where(
                    UserSessionModel.platform == platform.value,
                    UserSessionModel.platform_user_id == platform_user_id,
                )
            )
            if record is None:
                raise LookupError("Session not found for set_topic_id")
            record.telegram_topic_id = telegram_topic_id
            await session.commit()
            await session.refresh(record)
            return self._to_snapshot(record)

    async def start_flow(
        self,
        platform: Platform,
        platform_user_id: str,
        flow_id: FlowId,
    ) -> SessionSnapshot:
        async with self._session_factory() as session:
            record = await session.scalar(
                select(UserSessionModel).where(
                    UserSessionModel.platform == platform.value,
                    UserSessionModel.platform_user_id == platform_user_id,
                )
            )
            if record is None:
                raise LookupError("Session not found for start_flow")
            record.current_flow = flow_id.value
            record.current_step = 0
            record.flow_status = "in_progress"
            await session.commit()
            await session.refresh(record)
            return self._to_snapshot(record)

    async def advance_flow(
        self,
        platform: Platform,
        platform_user_id: str,
        next_step: int,
    ) -> SessionSnapshot:
        async with self._session_factory() as session:
            record = await session.scalar(
                select(UserSessionModel).where(
                    UserSessionModel.platform == platform.value,
                    UserSessionModel.platform_user_id == platform_user_id,
                )
            )
            if record is None:
                raise LookupError("Session not found for advance_flow")
            record.current_step = next_step
            await session.commit()
            await session.refresh(record)
            return self._to_snapshot(record)

    async def reset_flow(
        self,
        platform: Platform,
        platform_user_id: str,
    ) -> SessionSnapshot:
        async with self._session_factory() as session:
            record = await session.scalar(
                select(UserSessionModel).where(
                    UserSessionModel.platform == platform.value,
                    UserSessionModel.platform_user_id == platform_user_id,
                )
            )
            if record is None:
                raise LookupError("Session not found for reset_flow")
            record.current_flow = None
            record.current_step = 0
            record.flow_status = None
            await session.commit()
            await session.refresh(record)
            return self._to_snapshot(record)

    def _to_snapshot(self, record: UserSessionModel) -> SessionSnapshot:
        return SessionSnapshot(
            platform=Platform(record.platform),
            platform_user_id=record.platform_user_id,
            platform_chat_id=record.platform_chat_id,
            username=record.username,
            display_name=record.display_name,
            is_started=record.is_started,
            telegram_topic_id=record.telegram_topic_id,
            current_flow=FlowId(record.current_flow) if record.current_flow else None,
            current_step=record.current_step,
        )

