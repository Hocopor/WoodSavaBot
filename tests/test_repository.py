from __future__ import annotations

from pathlib import Path

import pytest

from wood_sava_bot.domain.enums import FlowId, Platform
from wood_sava_bot.storage.db import build_engine, build_session_factory
from wood_sava_bot.storage.repositories import SessionRepository


@pytest.mark.asyncio
async def test_session_persists_user_topic_and_step(tmp_path: Path) -> None:
    db_path = tmp_path / "state.db"
    engine = build_engine(f"sqlite+aiosqlite:///{db_path}")
    session_factory = build_session_factory(engine)
    repository = SessionRepository(session_factory)
    await repository.init_schema(engine)

    session = await repository.upsert_user(
        Platform.TELEGRAM,
        "123",
        "123",
        "mako",
        "Олег",
    )
    assert session.telegram_topic_id is None
    assert session.current_flow is None

    session = await repository.mark_started(Platform.TELEGRAM, "123")
    session = await repository.set_topic_id(Platform.TELEGRAM, "123", 777)
    session = await repository.start_flow(Platform.TELEGRAM, "123", FlowId.READY_MADE)
    session = await repository.advance_flow(Platform.TELEGRAM, "123", 3)

    loaded = await repository.get_by_platform_user(Platform.TELEGRAM, "123")
    assert loaded is not None
    assert loaded.telegram_topic_id == 777
    assert loaded.current_flow is FlowId.READY_MADE
    assert loaded.current_step == 3
    assert loaded.is_started is True

    by_topic = await repository.get_by_topic_id(777)
    assert by_topic is not None
    assert by_topic.platform_user_id == "123"

    await engine.dispose()


@pytest.mark.asyncio
async def test_step_state_persists_and_can_be_cleared(tmp_path: Path) -> None:
    db_path = tmp_path / "state.db"
    engine = build_engine(f"sqlite+aiosqlite:///{db_path}")
    session_factory = build_session_factory(engine)
    repository = SessionRepository(session_factory)
    await repository.init_schema(engine)

    await repository.upsert_user(
        Platform.TELEGRAM,
        "123",
        "123",
        "mako",
        "Олег",
    )
    await repository.mark_started(Platform.TELEGRAM, "123")
    await repository.start_flow(Platform.TELEGRAM, "123", FlowId.READY_MADE)
    await repository.save_step_state(Platform.TELEGRAM, "123", 0, "Первый ответ", [101])
    await repository.save_step_state(Platform.TELEGRAM, "123", 1, "Второй ответ", [102, 103])

    step_state = await repository.get_step_state(Platform.TELEGRAM, "123", 1)
    assert step_state is not None
    assert step_state.answer_preview == "Второй ответ"
    assert step_state.admin_message_ids == [102, 103]

    cleared = await repository.clear_step_states_from(Platform.TELEGRAM, "123", 1)
    assert [state.step_index for state in cleared] == [1]

    remaining = await repository.list_step_states(Platform.TELEGRAM, "123")
    assert [state.step_index for state in remaining] == [0]

    await engine.dispose()
