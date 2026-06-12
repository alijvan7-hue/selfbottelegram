from __future__ import annotations

from datetime import datetime, timezone
from typing import Optional

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.level import Level
from app.models.user import User
from app.repositories.level_repo import LevelRepository
from app.repositories.user_repo import UserRepository


class UserService:
    def __init__(self, session: AsyncSession) -> None:
        self._users = UserRepository(session)
        self._levels = LevelRepository(session)

    async def get_or_create(
        self,
        telegram_id: int,
        username: Optional[str],
        full_name: str,
        is_admin: bool = False,
    ) -> tuple[User, bool]:
        return await self._users.get_or_create(telegram_id, username, full_name, is_admin)

    async def get_by_telegram_id(self, telegram_id: int) -> Optional[User]:
        return await self._users.get_by_telegram_id(telegram_id)

    async def get_by_id(self, user_id: int) -> Optional[User]:
        return await self._users.get_by_id(user_id)

    async def add_tokens(self, user: User, amount: int) -> None:
        user.tokens += amount
        user.monthly_tokens += amount
        user.updated_at = datetime.now(timezone.utc)
        await self._users.save(user)

    async def remove_tokens(self, user: User, amount: int) -> None:
        user.tokens = max(0, user.tokens - amount)
        user.monthly_tokens = max(0, user.monthly_tokens - amount)
        user.updated_at = datetime.now(timezone.utc)
        await self._users.save(user)

    async def get_level(self, user: User) -> Optional[Level]:
        return await self._levels.get_level_for_tokens(user.tokens)

    async def get_all_levels(self):
        return await self._levels.get_all_ordered()

    async def get_top_overall(self, limit: int = 10):
        return await self._users.get_top_by_tokens(limit)

    async def get_top_monthly(self, limit: int = 10):
        return await self._users.get_top_by_monthly_tokens(limit)

    async def ban_user(
        self,
        user: User,
        ban_type: str,
        ban_until: Optional[datetime] = None,
    ) -> None:
        user.is_banned = True
        user.ban_type = ban_type
        user.ban_until = ban_until
        user.updated_at = datetime.now(timezone.utc)
        await self._users.save(user)

    async def unban_user(self, user: User) -> None:
        user.is_banned = False
        user.ban_type = None
        user.ban_until = None
        user.updated_at = datetime.now(timezone.utc)
        await self._users.save(user)

    async def is_effectively_banned(self, user: User) -> bool:
        if not user.is_banned:
            return False
        if user.ban_type == "permanent":
            return True
        if user.ban_until and user.ban_until < datetime.now(timezone.utc):
            await self.unban_user(user)
            return False
        return True

    async def reset_all_monthly_tokens(self) -> None:
        await self._users.reset_all_monthly_tokens()

    async def count_all(self) -> int:
        return await self._users.count_all()