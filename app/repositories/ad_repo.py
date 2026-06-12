from __future__ import annotations

from datetime import datetime
from typing import List, Optional

from sqlalchemy import select

from app.models.ad import Ad
from app.repositories.base import BaseRepository


class AdRepository(BaseRepository[Ad]):
    model = Ad

    async def get_by_user(self, user_id: int) -> List[Ad]:
        result = await self.session.execute(
            select(Ad).where(Ad.user_id == user_id).order_by(Ad.submitted_at.desc())
        )
        return list(result.scalars().all())

    async def get_pending(self) -> List[Ad]:
        result = await self.session.execute(
            select(Ad).where(Ad.status == "pending").order_by(Ad.submitted_at)
        )
        return list(result.scalars().all())

    async def get_payment_pending(self) -> List[Ad]:
        result = await self.session.execute(
            select(Ad).where(Ad.status == "payment_pending").order_by(Ad.submitted_at)
        )
        return list(result.scalars().all())

    async def get_scheduled(self) -> List[Ad]:
        result = await self.session.execute(
            select(Ad)
            .where(Ad.status == "payment_approved", Ad.publish_at.isnot(None))
            .order_by(Ad.publish_at)
        )
        return list(result.scalars().all())

    async def get_due_for_publishing(self, now: datetime) -> List[Ad]:
        result = await self.session.execute(
            select(Ad).where(
                Ad.status == "payment_approved",
                Ad.publish_at <= now,
                Ad.publish_at.isnot(None),
            )
        )
        return list(result.scalars().all())

    async def get_expired(self, now: datetime) -> List[Ad]:
        result = await self.session.execute(
            select(Ad).where(
                Ad.status == "published",
                Ad.expires_at <= now,
            )
        )
        return list(result.scalars().all())

    async def get_by_reviewer_message(self, message_id: int) -> Optional[Ad]:
        result = await self.session.execute(
            select(Ad).where(Ad.reviewer_message_id == message_id)
        )
        return result.scalar_one_or_none()

    async def get_pending_reply(self, now: datetime) -> List[Ad]:
        """Ads published but reply not yet sent (reply_message_id == -1) and reply due."""
        result = await self.session.execute(
            select(Ad).where(
                Ad.status == "published",
                Ad.reply_message_id == -1,
                Ad.publish_at <= now,
                Ad.reply_text.isnot(None),
            )
        )
        return list(result.scalars().all())