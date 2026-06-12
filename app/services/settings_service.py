from __future__ import annotations

from typing import Optional

from sqlalchemy.ext.asyncio import AsyncSession

from app.repositories.settings_repo import SettingsRepository

_DEFAULTS: dict[str, str] = {
    "publish_start_hour": "10",
    "publish_end_hour": "24",
    "min_publish_interval": "60",
    "max_publish_interval": "120",
    "daily_meme_limit": "2",
    "ad_limit_count": "2",
    "ad_limit_hours": "4",
    "banner_ad_price": "50000",
    "oneliner_ad_price": "30000",
    "card_number": "6037991234567890",
    "card_owner": "نام صاحب کارت",
    "support_id": "@support_username",
    "queue_paused": "false",
    "bot_locked": "false",
    "oneliner_sample_image": "",
    "oneliner_description": "برای مشاهده نمونه تبلیغات تک خطی به تصویر بالا توجه کنید.",
}


class SettingsService:
    def __init__(self, session: AsyncSession) -> None:
        self._repo = SettingsRepository(session)

    async def seed_defaults(self) -> None:
        for key, value in _DEFAULTS.items():
            existing = await self._repo.get(key)
            if existing is None:
                await self._repo.set(key, value)

    async def get(self, key: str) -> Optional[str]:
        return await self._repo.get(key)

    async def get_int(self, key: str, default: int = 0) -> int:
        val = await self._repo.get(key)
        try:
            return int(val) if val is not None else default
        except ValueError:
            return default

    async def get_float(self, key: str, default: float = 0.0) -> float:
        val = await self._repo.get(key)
        try:
            return float(val) if val is not None else default
        except ValueError:
            return default

    async def get_bool(self, key: str, default: bool = False) -> bool:
        val = await self._repo.get(key)
        if val is None:
            return default
        return val.lower() in ("true", "1", "yes")

    async def set(self, key: str, value: str) -> None:
        await self._repo.set(key, value)

    async def all(self) -> dict[str, str]:
        return await self._repo.get_all_as_dict()