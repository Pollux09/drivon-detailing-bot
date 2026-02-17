from __future__ import annotations

from aiogram.filters import BaseFilter
from aiogram.types import CallbackQuery, Message

from app.config import Settings


class IsAdminFilter(BaseFilter):
    async def __call__(self, event: Message | CallbackQuery, settings: Settings) -> bool:
        user = event.from_user
        if user is None:
            return False
        return user.id in settings.admin_ids
