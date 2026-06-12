from __future__ import annotations

from datetime import datetime
from typing import List, Optional

from sqlalchemy import func, select

from app.models.meme import Meme
from app.repositories.base import BaseRepository


class MemeRepository(BaseRepository[Meme]):
    model = Meme

    async def get_by_user(self, user_id: int) -> List[Meme]:
        result = await self.session.execute(
            select(Meme).where(Meme.user_id == user_id).order_by(Meme.submitted_at.desc())
        )
        return list(result.scalars().all())

    async def count_by_user_and_status(self, user_id: int, status: str) -> int:
        result = await self.session.execute(
            select(func.count(Meme.id)).where(
                Meme.user_id == user_id, Meme.status == status
            )
        )
        return result.scalar_one()

    async def get_pending(self) -> List[Meme]:
        result = await self.session.execute(
            select(Meme).where(Meme.status == "pending").order_by(Meme.submitted_at)
        )
        return list(result.scalars().all())

    async def get_approved_unpublished(self) -> List[Meme]:
        result = await self.session.execute(
            select(Meme).where(
                Meme.status == "approved", Meme.is_published.is_(False)
            )
        )
        return list(result.scalars().all())

    async def count_today_by_user(self, user_id: int, today_start: datetime) -> int:
        result = await self.session.execute(
            select(func.count(Meme.id)).where(
                Meme.user_id == user_id,
                Meme.submitted_at >= today_start,
            )
        )
        return result.scalar_one()

    async def get_by_reviewer_message(self, message_id: int) -> Optional[Meme]:
        result = await self.session.execute(
            select(Meme).where(Meme.reviewer_message_id == message_id)
        )
        return result.scalar_one_or_none()