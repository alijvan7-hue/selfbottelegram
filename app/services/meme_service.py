from __future__ import annotations

from datetime import datetime, timezone
from typing import List, Optional

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.meme import Meme
from app.repositories.meme_repo import MemeRepository


class MemeService:
    def __init__(self, session: AsyncSession) -> None:
        self._repo = MemeRepository(session)

    async def submit(
        self,
        user_id: int,
        file_id: str,
        file_type: str,
    ) -> Meme:
        now = datetime.now(timezone.utc)
        return await self._repo.create(
            user_id=user_id,
            file_id=file_id,
            file_type=file_type,
            status="pending",
            submitted_at=now,
            updated_at=now,
        )

    async def approve(self, meme: Meme) -> Meme:
        now = datetime.now(timezone.utc)
        meme.status = "approved"
        meme.reviewed_at = now
        meme.updated_at = now
        return await self._repo.save(meme)

    async def reject(self, meme: Meme) -> Meme:
        now = datetime.now(timezone.utc)
        meme.status = "rejected"
        meme.reviewed_at = now
        meme.updated_at = now
        return await self._repo.save(meme)

    async def mark_published(self, meme: Meme, channel_message_id: int) -> Meme:
        now = datetime.now(timezone.utc)
        meme.is_published = True
        meme.published_at = now
        meme.channel_message_id = channel_message_id
        meme.updated_at = now
        return await self._repo.save(meme)

    async def get_by_id(self, meme_id: int) -> Optional[Meme]:
        return await self._repo.get_by_id(meme_id)

    async def get_by_reviewer_message(self, message_id: int) -> Optional[Meme]:
        return await self._repo.get_by_reviewer_message(message_id)

    async def get_user_stats(self, user_id: int) -> dict:
        total = len(await self._repo.get_by_user(user_id))
        approved = await self._repo.count_by_user_and_status(user_id, "approved")
        rejected = await self._repo.count_by_user_and_status(user_id, "rejected")
        pending = await self._repo.count_by_user_and_status(user_id, "pending")
        return {
            "total": total,
            "approved": approved,
            "rejected": rejected,
            "pending": pending,
        }

    async def get_all_by_user(self, user_id: int) -> List[Meme]:
        return await self._repo.get_by_user(user_id)