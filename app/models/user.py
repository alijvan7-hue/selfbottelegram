from __future__ import annotations

from datetime import datetime
from typing import List, Optional

from sqlalchemy import BigInteger, Boolean, DateTime, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    telegram_id: Mapped[int] = mapped_column(BigInteger, unique=True, nullable=False, index=True)
    username: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    full_name: Mapped[str] = mapped_column(String(512), nullable=False, default="")

    tokens: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    monthly_tokens: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    is_admin: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    is_banned: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    ban_type: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)
    ban_until: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)

    daily_meme_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    last_meme_date: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    custom_daily_limit: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    no_limit: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    ad_count_in_window: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    ad_window_start: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)

    joined_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)

    memes: Mapped[List["Meme"]] = relationship("Meme", back_populates="user", lazy="select")
    ads: Mapped[List["Ad"]] = relationship("Ad", back_populates="user", lazy="select")
