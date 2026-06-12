from __future__ import annotations

import logging
from typing import Any, Awaitable, Callable, Dict

from aiogram import BaseMiddleware
from aiogram.types import CallbackQuery, Message, TelegramObject, Update

from app.core.config import config
from app.core.database import AsyncSessionFactory
from app.services.user_service import UserService

logger = logging.getLogger(__name__)


class AuthMiddleware(BaseMiddleware):
    """Registers/updates user on every incoming update."""

    async def __call__(
        self,
        handler: Callable[[TelegramObject, Dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: Dict[str, Any],
    ) -> Any:
        # Extract the from_user field
        from_user = None
        if isinstance(event, Message):
            from_user = event.from_user
        elif isinstance(event, CallbackQuery):
            from_user = event.from_user

        if from_user is None:
            return await handler(event, data)

        async with AsyncSessionFactory() as session:
            is_admin = from_user.id in config.admin_ids
            svc = UserService(session)
            user, created = await svc.get_or_create(
                telegram_id=from_user.id,
                username=from_user.username,
                full_name=from_user.full_name or "",
                is_admin=is_admin,
            )
            await session.commit()

            data["user"] = user
            data["is_admin"] = is_admin
            data["db_session"] = session

            if created:
                logger.info("New user registered: %s (%s)", from_user.id, from_user.username)

        return await handler(event, data)