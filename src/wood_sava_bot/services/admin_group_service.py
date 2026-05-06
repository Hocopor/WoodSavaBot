from __future__ import annotations

from dataclasses import dataclass

from wood_sava_bot.storage.repositories import AdminGroupRepository


@dataclass(slots=True)
class GroupEvent:
    chat_id: int
    title: str | None
    chat_type: str
    forum_enabled: bool
    bot_is_member: bool


class AdminChatResolver:
    def __init__(
        self,
        configured_chat_id: int | None,
        repository: AdminGroupRepository,
        telegram_api,
    ) -> None:
        self._configured_chat_id = configured_chat_id
        self._repository = repository
        self._telegram_api = telegram_api

    async def get_required_admin_chat_id(self) -> int:
        if self._configured_chat_id is not None:
            return self._configured_chat_id
        group = await self._repository.get_single_active_forum_supergroup()
        if group is None:
            raise RuntimeError(
                "Админская Telegram-группа не определена. Добавьте бота ровно в одну супергруппу с включенными темами "
                "или укажите TELEGRAM_ADMIN_CHAT_ID вручную."
            )
        return group.chat_id

    async def handle_group_event(self, event: GroupEvent) -> None:
        if not event.bot_is_member:
            await self._repository.deactivate_group(event.chat_id)
            return

        if event.chat_type != "supergroup" or not event.forum_enabled:
            return

        await self._repository.register_group(
            event.chat_id,
            event.title,
            event.chat_type,
            event.forum_enabled,
        )
        await self._maybe_warn_about_multiple_groups()

    async def is_admin_group(self, chat_id: int) -> bool:
        try:
            return chat_id == await self.get_required_admin_chat_id()
        except RuntimeError:
            groups = await self._repository.list_active_forum_supergroups()
            return any(group.chat_id == chat_id for group in groups)

    async def _maybe_warn_about_multiple_groups(self) -> None:
        if self._configured_chat_id is not None:
            return
        groups = await self._repository.list_active_forum_supergroups()
        if len(groups) <= 1:
            return
        text = (
            "Ошибка настройки: бот найден более чем в одной супергруппе с темами. "
            "Удалите бота из лишних групп или укажите TELEGRAM_ADMIN_CHAT_ID вручную."
        )
        for group in groups:
            await self._telegram_api.send_message(group.chat_id, text)
