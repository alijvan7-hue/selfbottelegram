from __future__ import annotations

from typing import List, Optional

from sqlalchemy import select

from app.models.level import Level
from app.repositories.base import BaseRepository


class LevelRepository(BaseRepository[Level]):
    model = Level

    async def get_all_ordered(self) -> List[Level]:
        result = await self.session.execute(
            select(Level).order_by(Level.min_tokens)
        )
        return list(result.scalars().all())

    async def get_level_for_tokens(self, tokens: int) -> Optional[Level]:
        result = await self.session.execute(
            select(Level)
            .where(Level.min_tokens <= tokens)
            .order_by(Level.min_tokens.desc())
            .limit(1)
        )
        return result.scalar_one_or_none()