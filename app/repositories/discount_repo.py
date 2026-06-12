from __future__ import annotations

from datetime import datetime
from typing import List, Optional

from sqlalchemy import select

from app.models.discount import DiscountCode
from app.repositories.base import BaseRepository


class DiscountRepository(BaseRepository[DiscountCode]):
    model = DiscountCode

    async def get_by_code(self, code: str) -> Optional[DiscountCode]:
        result = await self.session.execute(
            select(DiscountCode).where(DiscountCode.code == code.upper())
        )
        return result.scalar_one_or_none()

    async def get_valid_code(self, code: str, now: datetime) -> Optional[DiscountCode]:
        result = await self.session.execute(
            select(DiscountCode).where(
                DiscountCode.code == code.upper(),
                DiscountCode.is_active.is_(True),
            )
        )
        dc = result.scalar_one_or_none()
        if not dc:
            return None
        if dc.expires_at and dc.expires_at < now:
            return None
        if dc.max_uses is not None and dc.used_count >= dc.max_uses:
            return None
        return dc

    async def get_all(self) -> List[DiscountCode]:
        result = await self.session.execute(select(DiscountCode).order_by(DiscountCode.id))
        return list(result.scalars().all())