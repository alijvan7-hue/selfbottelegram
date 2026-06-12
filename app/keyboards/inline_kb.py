from __future__ import annotations

from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup
from aiogram.utils.keyboard import InlineKeyboardBuilder


def meme_review_kb(meme_id: int) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(text="✅ تایید", callback_data=f"meme_approve:{meme_id}"),
        InlineKeyboardButton(text="❌ رد", callback_data=f"meme_reject:{meme_id}"),
    )
    return builder.as_markup()


def ad_review_kb(ad_id: int) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(text="✅ تایید تبلیغ", callback_data=f"ad_approve:{ad_id}"),
        InlineKeyboardButton(text="❌ رد تبلیغ", callback_data=f"ad_reject:{ad_id}"),
    )
    return builder.as_markup()


def payment_review_kb(ad_id: int) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(text="✅ تایید پرداخت", callback_data=f"pay_approve:{ad_id}"),
        InlineKeyboardButton(text="❌ رد پرداخت", callback_data=f"pay_reject:{ad_id}"),
    )
    return builder.as_markup()


def payment_options_kb(ad_id: int) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(text="🏷 کد تخفیف", callback_data=f"discount:{ad_id}"),
        InlineKeyboardButton(text="💳 پرداخت", callback_data=f"proceed_pay:{ad_id}"),
    )
    return builder.as_markup()


def queue_item_kb(queue_id: int, meme_id: int) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(text="🚀 انتشار فوری", callback_data=f"q_publish_now:{meme_id}"),
        InlineKeyboardButton(text="🗑 حذف از صف", callback_data=f"q_remove:{queue_id}"),
    )
    return builder.as_markup()
