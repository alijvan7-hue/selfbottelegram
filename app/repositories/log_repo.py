from __future__ import annotations

from typing import List, Optional

from sqlalchemy import select

from app.models.log import SystemLog
from app.repositories.base import BaseRepository


class LogRepository(BaseRepository[SystemLog]):
    model = SystemLog

    async def get_recent(self, limit: int = 50) -> List[SystemLog]:
        result = await self.session.execute(
            select(SystemLog)
            .order_by(SystemLog.created_at.desc())
            .limit(limit)
        )
        return list(result.scalars().all())

    async def get_by_event_type(
        self, event_type: str, limit: int = 20
    ) -> List[SystemLog]:
        result = await self.session.execute(
            select(SystemLog)
            .where(SystemLog.event_type == event_type)
            .order_by(SystemLog.created_at.desc())
            .limit(limit)
        )
        return list(result.scalars().all())

    async def get_by_user(
        self, user_id: int, limit: int = 20
    ) -> List[SystemLog]:
        result = await self.session.execute(
            select(SystemLog)
            .where(SystemLog.user_id == user_id)
            .order_by(SystemLog.created_at.desc())
            .limit(limit)
        )
        return list(result.scalars().all())