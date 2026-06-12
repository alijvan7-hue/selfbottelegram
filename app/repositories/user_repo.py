from __future__ import annotations

from datetime import datetime
from typing import List, Optional

from sqlalchemy import func, select, update

from app.models.user import User
from app.repositories.base import BaseRepository


class UserRepository(BaseRepository[User]):
    model = User

    async def get_by_telegram_id(self, telegram_id: int) -> Optional[User]:
        result = await self.session.execute(
            select(User).where(User.telegram_id == telegram_id)
        )
        return result.scalar_one_or_none()

    async def get_or_create(
        self,
        telegram_id: int,
        username: Optional[str],
        full_name: str,
        is_admin: bool = False,
    ) -> tuple[User, bool]:
        user = await self.get_by_telegram_id(telegram_id)
        if user:
            # Update mutable fields
            user.username = username
            user.full_name = full_name
            await self.session.flush()
            return user, False

        user = User(
            telegram_id=telegram_id,
            username=username,
            full_name=full_name,
            is_admin=is_admin,
            joined_at=datetime.utcnow(),
            updated_at=datetime.utcnow(),
        )
        self.session.add(user)
        await self.session.flush()
        await self.session.refresh(user)
        return user, True

    async def get_top_by_tokens(self, limit: int = 10) -> List[User]:
        result = await self.session.execute(
            select(User)
            .where(User.is_admin.is_(False))
            .order_by(User.tokens.desc())
            .limit(limit)
        )
        return list(result.scalars().all())

    async def get_top_by_monthly_tokens(self, limit: int = 10) -> List[User]:
        result = await self.session.execute(
            select(User)
            .where(User.is_admin.is_(False))
            .order_by(User.monthly_tokens.desc())
            .limit(limit)
        )
        return list(result.scalars().all())

    async def count_all(self) -> int:
        result = await self.session.execute(select(func.count(User.id)))
        return result.scalar_one()

    async def reset_all_monthly_tokens(self) -> None:
        await self.session.execute(
            update(User).values(monthly_tokens=0)
        )
        await self.session.flush()

    async def get_all_users(self) -> List[User]:
        result = await self.session.execute(select(User))
        return list(result.scalars().all())