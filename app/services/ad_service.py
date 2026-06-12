from __future__ import annotations

import logging
import random
from datetime import datetime, timedelta, timezone
from typing import Optional

import pytz
from aiogram import Bot

from app.core.config import config
from app.models.ad import Ad
from app.repositories.ad_repo import AdRepository
from app.repositories.queue_repo import QueueRepository
from app.services.settings_service import SettingsService

logger = logging.getLogger(__name__)
_TEHRAN = pytz.timezone("Asia/Tehran")


class AdService:
    def __init__(self, session) -> None:
        self._repo = AdRepository(session)
        self._session = session

    async def create_banner_ad(
        self,
        user_id: int,
        text: str,
        image_file_id: Optional[str],
        extra_description: Optional[str],
        duration_hours: int,
        wants_reply: bool,
        wants_pin: bool,
        base_price: float,
        reply_price: float,
        pin_price: float,
        final_price: float,
    ) -> Ad:
        now = datetime.utcnow()
        return await self._repo.create(
            user_id=user_id,
            ad_type="banner",
            text=text,
            image_file_id=image_file_id,
            extra_description=extra_description,
            duration_hours=duration_hours,
            wants_reply=wants_reply,
            wants_pin=wants_pin,
            base_price=base_price,
            reply_price=reply_price,
            pin_price=pin_price,
            final_price=final_price,
            status="pending",
            submitted_at=now,
            updated_at=now,
        )

    async def create_oneliner_ad(
        self,
        user_id: int,
        text: str,
        link: str,
        duration_days: int,
        base_price: float,
        discount_amount: float,
        final_price: float,
    ) -> Ad:
        now = datetime.utcnow()
        return await self._repo.create(
            user_id=user_id,
            ad_type="oneliner",
            text=text,
            link=link,
            duration_days=duration_days,
            base_price=base_price,
            discount_amount=discount_amount,
            final_price=final_price,
            status="pending",
            submitted_at=now,
            updated_at=now,
        )

    async def approve_ad(self, ad: Ad) -> Ad:
        ad.status = "approved"
        ad.approved_at = datetime.utcnow()
        ad.updated_at = datetime.utcnow()
        return await self._repo.save(ad)

    async def reject_ad(self, ad: Ad) -> Ad:
        ad.status = "rejected"
        ad.updated_at = datetime.utcnow()
        return await self._repo.save(ad)

    async def apply_discount(
        self, ad: Ad, code: str, discount_type: str, discount_value: float
    ) -> Ad:
        if discount_type == "percent":
            discount_amount = ad.base_price * (discount_value / 100)
        else:
            discount_amount = discount_value

        ad.discount_code = code
        ad.discount_amount = min(discount_amount, ad.base_price)
        ad.final_price = max(0.0, ad.base_price - ad.discount_amount)
        ad.updated_at = datetime.utcnow()
        return await self._repo.save(ad)

    async def submit_payment(self, ad: Ad, receipt_file_id: str) -> Ad:
        ad.payment_receipt_file_id = receipt_file_id
        ad.status = "payment_pending"
        ad.updated_at = datetime.utcnow()
        return await self._repo.save(ad)

    async def approve_payment(
        self, ad: Ad, reply_text: Optional[str] = None
    ) -> Ad:
        now = datetime.utcnow()
        ad.status = "payment_approved"
        ad.payment_approved_at = now
        ad.updated_at = now
        if reply_text:
            ad.reply_text = reply_text

        if ad.ad_type == "banner":
            publish_at = await self._calculate_banner_publish_time()
            ad.publish_at = publish_at

        return await self._repo.save(ad)

    async def reject_payment(self, ad: Ad) -> Ad:
        ad.status = "rejected"
        ad.updated_at = datetime.utcnow()
        return await self._repo.save(ad)

    async def _calculate_banner_publish_time(self) -> Optional[datetime]:
        queue_repo = QueueRepository(self._session)
        entry = await queue_repo.get_next_in_window(17, 20)
        if entry:
            publish_at = entry.scheduled_time - timedelta(minutes=30)
            if publish_at < datetime.now(timezone.utc):
                publish_at = datetime.now(timezone.utc) + timedelta(minutes=5)
            return publish_at
        return datetime.now(timezone.utc) + timedelta(minutes=30)

    async def publish_ad(self, ad: Ad, bot: Bot) -> bool:
        if not config.channel_id:
            return False
        try:
            sent = await self._publish_banner(ad, bot)
            if not sent:
                return False

            now = datetime.utcnow()
            ad.status = "published"
            ad.published_at = now
            ad.channel_message_id = sent.message_id
            ad.updated_at = now

            if ad.duration_hours:
                ad.expires_at = datetime.now(timezone.utc) + timedelta(hours=ad.duration_hours)

            # اگر پین می‌خواهد
            if ad.wants_pin and config.channel_id:
                try:
                    await bot.pin_chat_message(
                        config.channel_id,
                        sent.message_id,
                        disable_notification=True,
                    )
                except Exception as e:
                    logger.warning("پین ناموفق: %s", e)

            # زمان ریپلای (10-15 دقیقه بعد)
            if ad.wants_reply and ad.reply_text:
                reply_delay = random.randint(10, 15)
                ad.publish_at = datetime.now(timezone.utc) + timedelta(minutes=reply_delay)
                ad.reply_message_id = -1  # pending reply

            await self._repo.save(ad)
            return True

        except Exception as exc:
            logger.error("خطا در انتشار تبلیغ %s: %s", ad.id, exc)
            return False

    async def _publish_banner(self, ad: Ad, bot: Bot):
        caption_parts = [ad.text]
        if ad.extra_description:
            caption_parts.append(f"\n{ad.extra_description}")
        caption = "\n".join(caption_parts)

        if ad.image_file_id:
            return await bot.send_photo(
                config.channel_id,
                photo=ad.image_file_id,
                caption=caption,
            )
        else:
            return await bot.send_message(config.channel_id, text=caption)

    async def send_auto_reply(self, ad: Ad, bot: Bot) -> bool:
        if not ad.reply_text or not ad.channel_message_id:
            return False
        try:
            sent = await bot.send_message(
                config.channel_id,
                text=ad.reply_text,
                reply_to_message_id=ad.channel_message_id,
            )
            ad.reply_message_id = sent.message_id
            ad.updated_at = datetime.utcnow()
            await self._repo.save(ad)
            return True
        except Exception as exc:
            logger.error("ریپلای ناموفق: %s", exc)
            return False

    async def expire_ad(self, ad: Ad, bot: Bot) -> None:
        try:
            if ad.channel_message_id and config.channel_id:
                try:
                    await bot.delete_message(config.channel_id, ad.channel_message_id)
                except Exception:
                    pass
            if ad.reply_message_id and ad.reply_message_id > 0 and config.channel_id:
                try:
                    await bot.delete_message(config.channel_id, ad.reply_message_id)
                except Exception:
                    pass

            ad.status = "expired"
            ad.updated_at = datetime.utcnow()
            await self._repo.save(ad)
        except Exception as exc:
            logger.error("خطا در انقضا تبلیغ %s: %s", ad.id, exc)

    async def get_by_id(self, ad_id: int) -> Optional[Ad]:
        return await self._repo.get_by_id(ad_id)

    async def check_ad_spam_limit(
        self, user_id: int, settings_svc: SettingsService
    ) -> tuple[bool, int]:
        from app.repositories.user_repo import UserRepository
        user_repo = UserRepository(self._session)
        user = await user_repo.get_by_id(user_id)
        if not user:
            return False, 0

        limit_count = await settings_svc.get_int("ad_limit_count", 2)
        limit_hours = await settings_svc.get_int("ad_limit_hours", 4)
        now = datetime.now(timezone.utc)

        if user.ad_window_start is None:
            return True, 0

        window_start = user.ad_window_start
        if window_start.tzinfo is None:
            window_start = window_start.replace(tzinfo=timezone.utc)

        window_end = window_start + timedelta(hours=limit_hours)

        if now > window_end:
            user.ad_count_in_window = 0
            user.ad_window_start = None
            await user_repo.save(user)
            return True, 0

        if user.ad_count_in_window >= limit_count:
            return False, int((window_end - now).total_seconds())

        return True, 0

    async def increment_ad_counter(self, user_id: int) -> None:
        from app.repositories.user_repo import UserRepository
        user_repo = UserRepository(self._session)
        user = await user_repo.get_by_id(user_id)
        if not user:
            return
        now = datetime.now(timezone.utc)
        if user.ad_window_start is None:
            user.ad_window_start = now
            user.ad_count_in_window = 1
        else:
            user.ad_count_in_window += 1
        await user_repo.save(user)