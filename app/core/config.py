from __future__ import annotations

import os
from dataclasses import dataclass
from typing import List

from dotenv import load_dotenv

load_dotenv()


def _parse_admin_ids(raw: str) -> List[int]:
    if not raw:
        return []
    return [int(x.strip()) for x in raw.split(",") if x.strip().isdigit()]


@dataclass(frozen=True)
class Config:
    bot_token: str
    admin_ids: List[int]
    database_url: str
    channel_id: int
    log_channel_id: int
    admin_group_id: int
    debug: bool
    timezone: str


def load_config() -> Config:
    bot_token = os.getenv("BOT_TOKEN", "")
    if not bot_token:
        raise EnvironmentError("BOT_TOKEN is not set.")

    raw_admin_ids = os.getenv("ADMIN_IDS", "")
    admin_ids = _parse_admin_ids(raw_admin_ids)
    if not admin_ids:
        raise EnvironmentError("ADMIN_IDS is not set or invalid.")

    # SQLite path - data folder for persistence
    db_path = os.getenv("DATABASE_PATH", "data/bot.db")
    # Ensure directory exists
    os.makedirs(os.path.dirname(db_path) if os.path.dirname(db_path) else ".", exist_ok=True)
    database_url = f"sqlite+aiosqlite:///{db_path}"

    channel_id = int(os.getenv("CHANNEL_ID", "0"))
    log_channel_id = int(os.getenv("LOG_CHANNEL_ID", "0"))
    admin_group_id = int(os.getenv("ADMIN_GROUP_ID", "0"))

    return Config(
        bot_token=bot_token,
        admin_ids=admin_ids,
        database_url=database_url,
        channel_id=channel_id,
        log_channel_id=log_channel_id,
        admin_group_id=admin_group_id,
        debug=os.getenv("DEBUG", "false").lower() == "true",
        timezone=os.getenv("TIMEZONE", "Asia/Tehran"),
    )


config: Config = load_config()
