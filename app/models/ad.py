from __future__ import annotations

from datetime import datetime
from typing import Optional

from sqlalchemy import BigInteger, Boolean, DateTime, Float, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base


class Ad(Base):
    __tablename__ = "ads"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    ad_type: Mapped[str] = mapped_column(String(20), nullable=False)  # banner / oneliner

    # Content
    text: Mapped[str] = mapped_column(Text, nullable=False)
    link: Mapped[Optional[str]] = mapped_column(String(2048), nullable=True)
    image_file_id: Mapped[Optional[str]] = mapped_column(String(512), nullable=True)
    extra_description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Banner specific
    duration_hours: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)  # 12 / 24 / 72
    wants_reply: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    wants_pin: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    reply_text: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Oneliner specific
    duration_days: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)

    # Status
    # pending / approved / rejected / payment_pending / payment_approved / published / expired
    status: Mapped[str] = mapped_column(String(30), default="pending", nullable=False, index=True)

    # Pricing
    base_price: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    reply_price: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    pin_price: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    discount_code: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    discount_amount: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    final_price: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)

    # Payment
    payment_receipt_file_id: Mapped[Optional[str]] = mapped_column(String(512), nullable=True)
    payment_approved_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)

    # Timestamps
    submitted_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=datetime.utcnow)
    approved_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    publish_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    published_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    expires_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    updated_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)

    # Channel references
    channel_message_id: Mapped[Optional[int]] = mapped_column(BigInteger, nullable=True)
    reply_message_id: Mapped[Optional[int]] = mapped_column(BigInteger, nullable=True)
    reviewer_message_id: Mapped[Optional[int]] = mapped_column(BigInteger, nullable=True)

    # Relationships
    user: Mapped["User"] = relationship("User", back_populates="ads")
    revenue_log: Mapped[Optional["RevenueLog"]] = relationship(
        "RevenueLog", back_populates="ad", uselist=False
    )

    def __repr__(self) -> str:
        return f"<Ad id={self.id} type={self.ad_type} status={self.status}>"
