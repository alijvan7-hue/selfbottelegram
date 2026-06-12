from __future__ import annotations

import logging

from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.fsm.storage.memory import MemoryStorage

from app.core.config import config

logger = logging.getLogger(__name__)

# ── Bot instance ──────────────────────────────────────────────────────────────
bot: Bot = Bot(
    token=config.bot_token,
    default=DefaultBotProperties(parse_mode=ParseMode.HTML),
)

# ── Dispatcher ────────────────────────────────────────────────────────────────
# MemoryStorage is fine for a single-process Railway deployment.
# For multi-replica setups swap to RedisStorage.
storage = MemoryStorage()
dp: Dispatcher = Dispatcher(storage=storage)