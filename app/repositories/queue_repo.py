from __future__ import annotations

from datetime import datetime
from typing import List, Optional

from sqlalchemy import select

from app.models.queue import PublishQueue
from app.repositories.base import BaseRepository


class QueueRepository(BaseRepository[PublishQueue]):
    model = PublishQueue

    async def get_waiting(self) -> List[PublishQueue]:
        result = await self.session.execute(
            select(PublishQueue)
            .where(PublishQueue.status == "waiting")
            .order_by(PublishQueue.scheduled_time)
        )
        return list(result.scalars().all())

    async def get_next_due(self, now: datetime) -> Optional[PublishQueue]:
        result = await self.session.execute(
            select(PublishQueue)
            .where(
                PublishQueue.status == "waiting",
                PublishQueue.scheduled_time <= now,
            )
            .order_by(PublishQueue.scheduled_time)
            .limit(1)
        )
        return result.scalar_one_or_none()

    async def get_by_meme_id(self, meme_id: int) -> Optional[PublishQueue]:
        result = await self.session.execute(
            select(PublishQueue).where(PublishQueue.meme_id == meme_id)
        )
        return result.scalar_one_or_none()

    async def get_next_in_window(
        self, window_start_hour: int, window_end_hour: int
    ) -> Optional[PublishQueue]:
        """Find the earliest waiting queue entry whose scheduled_time falls in the given hour range."""
        from sqlalchemy import extract

        result = await self.session.execute(
            select(PublishQueue)
            .where(
                PublishQueue.status == "waiting",
                extract("hour", PublishQueue.scheduled_time) >= window_start_hour,
                extract("hour", PublishQueue.scheduled_time) < window_end_hour,
            )
            .order_by(PublishQueue.scheduled_time)
            .limit(1)
        )
        return result.scalar_one_or_none()

    async def count_waiting(self) -> int:
        from sqlalchemy import func
        result = await self.session.execute(
            select(func.count(PublishQueue.id)).where(PublishQueue.status == "waiting")
        )
        return result.scalar_one()