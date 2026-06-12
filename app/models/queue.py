from __future__ import annotations

from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base


class PublishQueue(Base):
    __tablename__ = "publish_queue"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    meme_id: Mapped[int] = mapped_column(Integer, ForeignKey("memes.id", ondelete="CASCADE"), nullable=False, unique=True, index=True)
    scheduled_time: Mapped[datetime] = mapped_column(DateTime, nullable=False, index=True)
    status: Mapped[str] = mapped_column(String(20), default="waiting", nullable=False, index=True)

    meme: Mapped["Meme"] = relationship("Meme", back_populates="queue_entry")
