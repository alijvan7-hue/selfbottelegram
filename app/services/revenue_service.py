from __future__ import annotations

from datetime import date, datetime, timedelta
from typing import Optional

from sqlalchemy.ext.asyncio import AsyncSession

from app.repositories.revenue_repo import RevenueRepository


class RevenueService:
    def __init__(self, session: AsyncSession) -> None:
        self._repo = RevenueRepository(session)

    async def record(
        self,
        ad_id: Optional[int],
        user_id: Optional[int],
        amount: float,
        ad_type: str,
        date: date,
    ) -> None:
        await self._repo.create(
            ad_id=ad_id,
            user_id=user_id,
            amount=amount,
            type=ad_type,
            date=date,
        )

    async def get_today(self) -> float:
        today = date.today()
        return await self._repo.today(today)

    async def get_week(self) -> float:
        today = date.today()
        start = today - timedelta(days=6)
        return await self._repo.total_by_date_range(start, today)

    async def get_month(self) -> float:
        today = date.today()
        start = today.replace(day=1)
        return await self._repo.total_by_date_range(start, today)

    async def get_total(self) -> float:
        return await self._repo.total()