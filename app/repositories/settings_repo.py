from __future__ import annotations

from typing import Optional

from sqlalchemy import select

from app.models.settings import Setting
from app.repositories.base import BaseRepository


class SettingsRepository(BaseRepository[Setting]):
    model = Setting

    async def get(self, key: str) -> Optional[str]:
        result = await self.session.execute(
            select(Setting).where(Setting.key == key)
        )
        row = result.scalar_one_or_none()
        return row.value if row else None

    async def set(self, key: str, value: str) -> Setting:
        result = await self.session.execute(
            select(Setting).where(Setting.key == key)
        )
        row = result.scalar_one_or_none()
        if row:
            row.value = value
            await self.session.flush()
            return row
        row = Setting(key=key, value=value)
        self.session.add(row)
        await self.session.flush()
        return row

    async def get_all_as_dict(self) -> dict[str, str]:
        result = await self.session.execute(select(Setting))
        return {row.key: row.value for row in result.scalars().all()}