from __future__ import annotations

import logging
import os
from typing import AsyncGenerator

from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from app.core.config import config

logger = logging.getLogger(__name__)

# ── Engine ─────────────────────────────────────────────────────────────────────
engine: AsyncEngine = create_async_engine(
    config.database_url,
    echo=config.debug,
    # SQLite specific settings
    connect_args={"check_same_thread": False},
    pool_pre_ping=True,
)

# ── Session Factory ────────────────────────────────────────────────────────────
AsyncSessionFactory: async_sessionmaker[AsyncSession] = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autoflush=False,
    autocommit=False,
)


async def get_session() -> AsyncGenerator[AsyncSession, None]:
    async with AsyncSessionFactory() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()


async def create_all_tables() -> None:
    from app.models.base import Base
    import app.models.user
    import app.models.meme
    import app.models.ad
    import app.models.queue
    import app.models.settings
    import app.models.level
    import app.models.discount
    import app.models.revenue
    import app.models.log

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    logger.info("All database tables created.")

    # Seed default data
    await _seed_initial_data()


async def _seed_initial_data() -> None:
    """Insert default settings and levels if not exist."""
    async with AsyncSessionFactory() as session:
        from app.models.settings import Setting
        from app.models.level import Level
        from sqlalchemy import select

        # Default settings
        defaults = {
            "publish_start_hour": "10",
            "publish_end_hour": "24",
            "min_publish_interval": "60",
            "max_publish_interval": "120",
            "daily_meme_limit": "2",
            "ad_limit_count": "2",
            "ad_limit_hours": "4",
            "banner_price_12h": "50000",
            "banner_price_24h": "80000",
            "banner_price_72h": "150000",
            "banner_reply_price": "20000",
            "banner_pin_price": "30000",
            "card_number": "6037991234567890",
            "card_owner": "نام صاحب کارت",
            "support_id": "@support_username",
            "queue_paused": "false",
            "bot_locked": "false",
            "oneliner_sample_image": "",
            "oneliner_description": "برای مشاهده نمونه تبلیغات تک خطی به تصویر بالا توجه کنید.",
        }

        for key, value in defaults.items():
            result = await session.execute(
                select(Setting).where(Setting.key == key)
            )
            if not result.scalar_one_or_none():
                session.add(Setting(key=key, value=value))

        # Default levels
        result = await session.execute(select(Level))
        if not result.scalars().first():
            levels = [
                Level(name="مبتدی", min_tokens=5),
                Level(name="فعال", min_tokens=20),
                Level(name="حرفه‌ای", min_tokens=50),
                Level(name="افسانه‌ای", min_tokens=100),
            ]
            session.add_all(levels)

        await session.commit()
    logger.info("Default data seeded.")


async def dispose_engine() -> None:
    await engine.dispose()
    logger.info("Database engine disposed.")
