from __future__ import annotations

from datetime import date
from typing import List, Optional

from sqlalchemy import func, select

from app.models.revenue import RevenueLog
from app.repositories.base import BaseRepository


class RevenueRepository(BaseRepository[RevenueLog]):
    model = RevenueLog

    async def total(self) -> float:
        result = await self.session.execute(
            select(func.coalesce(func.sum(RevenueLog.amount), 0))
        )
        return float(result.scalar_one())

    async def total_by_date_range(self, start: date, end: date) -> float:
        result = await self.session.execute(
            select(func.coalesce(func.sum(RevenueLog.amount), 0)).where(
                RevenueLog.date >= start,
                RevenueLog.date <= end,
            )
        )
        return float(result.scalar_one())

    async def today(self, today: date) -> float:
        return await self.total_by_date_range(today, today)

    async def get_by_date_range(self, start: date, end: date) -> List[RevenueLog]:
        result = await self.session.execute(
            select(RevenueLog)
            .where(RevenueLog.date >= start, RevenueLog.date <= end)
            .order_by(RevenueLog.date.desc())
        )
        return list(result.scalars().all())

    async def get_recent(self, limit: int = 20) -> List[RevenueLog]:
        result = await self.session.execute(
            select(RevenueLog)
            .order_by(RevenueLog.created_at.desc())
            .limit(limit)
        )
        return list(result.scalars().all())