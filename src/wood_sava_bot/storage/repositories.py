from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from wood_sava_bot.domain.enums import FlowId, Platform
from wood_sava_bot.domain.models import AdminGroupSnapshot, FlowStepStateSnapshot, SessionSnapshot
from wood_sava_bot.storage.models import AdminGroupModel, Base, FlowStepStateModel, UserSessionModel


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

    async def get_step_state(
        self,
        platform: Platform,
        platform_user_id: str,
        step_index: int,
    ) -> FlowStepStateSnapshot | None:
        async with self._session_factory() as session:
            session_record = await self._get_session_record(session, platform, platform_user_id)
            if session_record is None:
                return None
            record = await session.scalar(
                select(FlowStepStateModel).where(
                    FlowStepStateModel.session_id == session_record.id,
                    FlowStepStateModel.step_index == step_index,
                )
            )
            return self._to_step_snapshot(record) if record else None

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
            await session.execute(
                FlowStepStateModel.__table__.delete().where(
                    FlowStepStateModel.session_id == record.id,
                )
            )
            await session.commit()
            await session.refresh(record)
            return self._to_snapshot(record)

    async def clear_topic_id(
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
                raise LookupError("Session not found for clear_topic_id")
            record.telegram_topic_id = None
            await session.commit()
            await session.refresh(record)
            return self._to_snapshot(record)

    async def save_step_state(
        self,
        platform: Platform,
        platform_user_id: str,
        step_index: int,
        answer_preview: str,
        admin_message_ids: list[int],
    ) -> FlowStepStateSnapshot:
        async with self._session_factory() as session:
            session_record = await self._require_session_record(session, platform, platform_user_id)
            record = await session.scalar(
                select(FlowStepStateModel).where(
                    FlowStepStateModel.session_id == session_record.id,
                    FlowStepStateModel.step_index == step_index,
                )
            )
            if record is None:
                record = FlowStepStateModel(
                    session_id=session_record.id,
                    step_index=step_index,
                    answer_preview=answer_preview,
                    admin_message_ids=admin_message_ids,
                )
                session.add(record)
            else:
                record.answer_preview = answer_preview
                record.admin_message_ids = admin_message_ids
            await session.commit()
            await session.refresh(record)
            return self._to_step_snapshot(record)

    async def clear_step_states_from(
        self,
        platform: Platform,
        platform_user_id: str,
        from_step_index: int,
    ) -> list[FlowStepStateSnapshot]:
        async with self._session_factory() as session:
            session_record = await self._require_session_record(session, platform, platform_user_id)
            records = (
                await session.scalars(
                    select(FlowStepStateModel).where(
                        FlowStepStateModel.session_id == session_record.id,
                        FlowStepStateModel.step_index >= from_step_index,
                    )
                )
            ).all()
            snapshots = [self._to_step_snapshot(record) for record in records]
            for record in records:
                await session.delete(record)
            await session.commit()
            return snapshots

    async def list_step_states(
        self,
        platform: Platform,
        platform_user_id: str,
    ) -> list[FlowStepStateSnapshot]:
        async with self._session_factory() as session:
            session_record = await self._get_session_record(session, platform, platform_user_id)
            if session_record is None:
                return []
            records = (
                await session.scalars(
                    select(FlowStepStateModel).where(
                        FlowStepStateModel.session_id == session_record.id,
                    ).order_by(FlowStepStateModel.step_index.asc())
                )
            ).all()
            return [self._to_step_snapshot(record) for record in records]

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

    def _to_step_snapshot(self, record: FlowStepStateModel) -> FlowStepStateSnapshot:
        return FlowStepStateSnapshot(
            step_index=record.step_index,
            answer_preview=record.answer_preview,
            admin_message_ids=[int(message_id) for message_id in (record.admin_message_ids or [])],
        )

    async def _get_session_record(
        self,
        session: AsyncSession,
        platform: Platform,
        platform_user_id: str,
    ) -> UserSessionModel | None:
        return await session.scalar(
            select(UserSessionModel).where(
                UserSessionModel.platform == platform.value,
                UserSessionModel.platform_user_id == platform_user_id,
            )
        )

    async def _require_session_record(
        self,
        session: AsyncSession,
        platform: Platform,
        platform_user_id: str,
    ) -> UserSessionModel:
        record = await self._get_session_record(session, platform, platform_user_id)
        if record is None:
            raise LookupError("Session not found")
        return record


class AdminGroupRepository:
    def __init__(self, session_factory: async_sessionmaker[AsyncSession]) -> None:
        self._session_factory = session_factory

    async def register_group(
        self,
        chat_id: int,
        title: str | None,
        chat_type: str,
        forum_enabled: bool,
    ) -> AdminGroupSnapshot:
        async with self._session_factory() as session:
            record = await session.scalar(
                select(AdminGroupModel).where(AdminGroupModel.chat_id == chat_id)
            )
            if record is None:
                record = AdminGroupModel(
                    chat_id=chat_id,
                    title=title,
                    chat_type=chat_type,
                    forum_enabled=forum_enabled,
                    is_active=True,
                )
                session.add(record)
            else:
                record.title = title
                record.chat_type = chat_type
                record.forum_enabled = forum_enabled
                record.is_active = True
            await session.commit()
            await session.refresh(record)
            return self._to_snapshot(record)

    async def deactivate_group(self, chat_id: int) -> None:
        async with self._session_factory() as session:
            record = await session.scalar(
                select(AdminGroupModel).where(AdminGroupModel.chat_id == chat_id)
            )
            if record is None:
                return
            record.is_active = False
            await session.commit()

    async def list_active_forum_supergroups(self) -> list[AdminGroupSnapshot]:
        async with self._session_factory() as session:
            records = (
                await session.scalars(
                    select(AdminGroupModel).where(
                        AdminGroupModel.is_active.is_(True),
                        AdminGroupModel.chat_type == "supergroup",
                        AdminGroupModel.forum_enabled.is_(True),
                    )
                )
            ).all()
            return [self._to_snapshot(record) for record in records]

    async def get_single_active_forum_supergroup(self) -> AdminGroupSnapshot | None:
        groups = await self.list_active_forum_supergroups()
        if len(groups) == 1:
            return groups[0]
        return None

    def _to_snapshot(self, record: AdminGroupModel) -> AdminGroupSnapshot:
        return AdminGroupSnapshot(
            chat_id=record.chat_id,
            title=record.title,
            chat_type=record.chat_type,
            forum_enabled=record.forum_enabled,
            is_active=record.is_active,
        )
