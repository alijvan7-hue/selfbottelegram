from __future__ import annotations

import logging

from aiogram import F, Router
from aiogram.filters import Command
from aiogram.types import CallbackQuery, Message

from app.core.config import config
from app.core.database import AsyncSessionFactory
from app.keyboards.admin_kb import admin_main_kb
from app.keyboards.user_kb import main_menu_kb
from app.services.queue_service import QueueService
from app.services.settings_service import SettingsService
from app.services.user_service import UserService
from app.utils.text_helper import fa_number

router = Router(name="admin_panel")
logger = logging.getLogger(__name__)


def _is_admin(user_id: int) -> bool:
    return user_id in config.admin_ids


@router.message(Command("admin"))
async def cmd_admin(message: Message, **kwargs) -> None:
    if not message.from_user or not _is_admin(message.from_user.id):
        await message.answer("❌ دسترسی ندارید.")
        return
    await _show_admin_panel(message)


@router.message(F.text == "🔐 پنل ادمین")
async def admin_panel_btn(message: Message, is_admin: bool, **kwargs) -> None:
    if not is_admin:
        return
    await _show_admin_panel(message)


async def _show_admin_panel(message: Message) -> None:
    async with AsyncSessionFactory() as session:
        settings_svc = SettingsService(session)
        queue_svc = QueueService(session)
        user_svc = UserService(session)

        paused = await settings_svc.get_bool("queue_paused")
        locked = await settings_svc.get_bool("bot_locked")
        queue_count = await queue_svc.count_waiting()
        user_count = await user_svc.count_all()

    queue_status = "⏸ متوقف" if paused else "▶️ فعال"
    lock_status = "🔒 قفل" if locked else "🔓 باز"

    await message.answer(
        f"🔐 <b>پنل ادمین</b>\n\n"
        f"📋 صف: <b>{queue_status}</b> ({fa_number(queue_count)} آیتم)\n"
        f"🔒 ربات: <b>{lock_status}</b>\n"
        f"👥 کاربران: <b>{fa_number(user_count)}</b>",
        reply_markup=admin_main_kb(),
    )


@router.message(F.text == "🔙 منوی اصلی")
async def back_to_main(message: Message, is_admin: bool, **kwargs) -> None:
    await message.answer("منوی اصلی:", reply_markup=main_menu_kb(is_admin=is_admin))


# ── سطوح ──────────────────────────────────────────────────────────────────────
@router.message(F.text == "🎯 سطوح")
async def levels_panel(message: Message, is_admin: bool, **kwargs) -> None:
    if not is_admin:
        return

    async with AsyncSessionFactory() as session:
        from app.repositories.level_repo import LevelRepository
        repo = LevelRepository(session)
        levels = await repo.get_all_ordered()

    if not levels:
        text = "🎯 <b>سطوح کاربران</b>\n\nهیچ سطحی تعریف نشده."
    else:
        lines = ["🎯 <b>سطوح کاربران</b>\n━━━━━━━━━━━━━━━\n"]
        for lvl in levels:
            lines.append(f"• <code>ID:{lvl.id}</code> <b>{lvl.name}</b> — از {fa_number(lvl.min_tokens)} توکن")
        text = "\n".join(lines)

    text += (
        "\n\n━━━━━━━━━━━━━━━\n"
        "➕ افزودن:\n<code>/addlevel مبتدی 5</code>\n\n"
        "🗑 حذف:\n<code>/dellevel 1</code>"
    )
    await message.answer(text)


@router.message(Command("addlevel"))
async def cmd_add_level(message: Message, **kwargs) -> None:
    if not message.from_user or not _is_admin(message.from_user.id):
        return

    parts = (message.text or "").split(maxsplit=2)
    if len(parts) < 3:
        await message.answer(
            "⚠️ <b>فرمت صحیح:</b>\n"
            "<code>/addlevel نام حداقل‌توکن</code>\n\n"
            "مثال:\n"
            "<code>/addlevel مبتدی 5</code>\n"
            "<code>/addlevel افسانه‌ای 100</code>"
        )
        return

    name = parts[1]
    if not parts[2].isdigit():
        await message.answer("❌ تعداد توکن باید عدد باشد.\n<code>/addlevel مبتدی 5</code>")
        return

    min_tokens = int(parts[2])

    async with AsyncSessionFactory() as session:
        from app.models.level import Level
        lvl = Level(name=name, min_tokens=min_tokens)
        session.add(lvl)
        try:
            await session.commit()
            await message.answer(f"✅ سطح <b>{name}</b> با {fa_number(min_tokens)} توکن اضافه شد.")
        except Exception:
            await session.rollback()
            await message.answer(f"❌ سطح با این تعداد توکن قبلاً وجود دارد.")


@router.message(Command("dellevel"))
async def cmd_del_level(message: Message, **kwargs) -> None:
    if not message.from_user or not _is_admin(message.from_user.id):
        return

    parts = (message.text or "").split()
    if len(parts) < 2 or not parts[1].isdigit():
        await message.answer(
            "⚠️ <b>فرمت صحیح:</b>\n"
            "<code>/dellevel 1</code>\n\n"
            "عدد = شناسه سطح (از دکمه 🎯 سطوح ببینید)"
        )
        return

    level_id = int(parts[1])
    async with AsyncSessionFactory() as session:
        from app.repositories.level_repo import LevelRepository
        repo = LevelRepository(session)
        lvl = await repo.get_by_id(level_id)
        if not lvl:
            await message.answer(f"❌ سطح با شناسه <code>{level_id}</code> یافت نشد.")
            return
        name = lvl.name
        await repo.delete(lvl)
        await session.commit()

    await message.answer(f"✅ سطح <b>{name}</b> حذف شد.")


# ── تخفیف‌ها ──────────────────────────────────────────────────────────────────
@router.message(F.text == "🏷 تخفیف‌ها")
async def discounts_panel(message: Message, is_admin: bool, **kwargs) -> None:
    if not is_admin:
        return

    async with AsyncSessionFactory() as session:
        from app.repositories.discount_repo import DiscountRepository
        repo = DiscountRepository(session)
        codes = await repo.get_all()

    if not codes:
        text = "🏷 <b>کدهای تخفیف</b>\n\nهیچ کدی وجود ندارد."
    else:
        lines = ["🏷 <b>کدهای تخفیف</b>\n━━━━━━━━━━━━━━━\n"]
        for dc in codes:
            status = "✅" if dc.is_active else "❌"
            type_fa = "درصدی" if dc.type == "percent" else "ثابت"
            val = f"{dc.value}٪" if dc.type == "percent" else f"{fa_number(dc.value)} تومان"
            uses = f"{dc.used_count}/{dc.max_uses}" if dc.max_uses else f"{dc.used_count}/∞"
            lines.append(f"{status} <code>{dc.code}</code> — {val} ({type_fa}) — {uses}")
        text = "\n".join(lines)

    text += (
        "\n\n━━━━━━━━━━━━━━━\n"
        "➕ افزودن درصدی:\n<code>/adddiscount SALE20 percent 20</code>\n\n"
        "➕ افزودن ثابت:\n<code>/adddiscount VIP fixed 10000</code>\n\n"
        "➕ با محدودیت تعداد:\n<code>/adddiscount CODE50 percent 50 10</code>\n\n"
        "🗑 حذف:\n<code>/deldiscount SALE20</code>\n\n"
        "🔄 فعال/غیرفعال:\n<code>/togglediscount SALE20</code>"
    )
    await message.answer(text)


@router.message(Command("adddiscount"))
async def cmd_add_discount(message: Message, **kwargs) -> None:
    if not message.from_user or not _is_admin(message.from_user.id):
        return

    parts = (message.text or "").split()
    if len(parts) < 4:
        await message.answer(
            "⚠️ <b>فرمت صحیح:</b>\n"
            "<code>/adddiscount کد نوع مقدار [حداکثر‌استفاده]</code>\n\n"
            "مثال‌ها:\n"
            "<code>/adddiscount SALE20 percent 20</code>\n"
            "<code>/adddiscount VIP fixed 10000</code>\n"
            "<code>/adddiscount CODE50 percent 50 10</code>"
        )
        return

    code = parts[1].upper()
    dtype = parts[2].lower()

    if dtype not in ("percent", "fixed"):
        await message.answer(
            "❌ نوع باید <code>percent</code> یا <code>fixed</code> باشد.\n\n"
            "مثال: <code>/adddiscount SALE20 percent 20</code>"
        )
        return

    try:
        value = float(parts[3])
    except ValueError:
        await message.answer(
            "❌ مقدار باید عدد باشد.\n"
            "مثال: <code>/adddiscount SALE20 percent 20</code>"
        )
        return

    max_uses = None
    if len(parts) > 4:
        if not parts[4].isdigit():
            await message.answer("❌ حداکثر استفاده باید عدد باشد.")
            return
        max_uses = int(parts[4])

    async with AsyncSessionFactory() as session:
        from app.models.discount import DiscountCode
        dc = DiscountCode(
            code=code,
            type=dtype,
            value=value,
            max_uses=max_uses,
            is_active=True,
        )
        session.add(dc)
        try:
            await session.commit()
            type_fa = "درصدی" if dtype == "percent" else "مبلغ ثابت"
            val_fa = f"{value}٪" if dtype == "percent" else f"{fa_number(value)} تومان"
            uses_fa = f"(حداکثر {max_uses} بار)" if max_uses else "(نامحدود)"
            await message.answer(
                f"✅ کد تخفیف اضافه شد!\n\n"
                f"کد: <code>{code}</code>\n"
                f"نوع: {type_fa}\n"
                f"مقدار: {val_fa}\n"
                f"استفاده: {uses_fa}"
            )
        except Exception:
            await session.rollback()
            await message.answer(f"❌ کد <code>{code}</code> قبلاً وجود دارد.")


@router.message(Command("deldiscount"))
async def cmd_del_discount(message: Message, **kwargs) -> None:
    if not message.from_user or not _is_admin(message.from_user.id):
        return

    parts = (message.text or "").split()
    if len(parts) < 2:
        await message.answer(
            "⚠️ <b>فرمت صحیح:</b>\n"
            "<code>/deldiscount کد</code>\n\n"
            "مثال: <code>/deldiscount SALE20</code>"
        )
        return

    code = parts[1].upper()
    async with AsyncSessionFactory() as session:
        from app.repositories.discount_repo import DiscountRepository
        repo = DiscountRepository(session)
        dc = await repo.get_by_code(code)
        if not dc:
            await message.answer(f"❌ کد <code>{code}</code> یافت نشد.")
            return
        await repo.delete(dc)
        await session.commit()

    await message.answer(f"✅ کد <code>{code}</code> حذف شد.")


@router.message(Command("togglediscount"))
async def cmd_toggle_discount(message: Message, **kwargs) -> None:
    if not message.from_user or not _is_admin(message.from_user.id):
        return

    parts = (message.text or "").split()
    if len(parts) < 2:
        await message.answer(
            "⚠️ <b>فرمت صحیح:</b>\n"
            "<code>/togglediscount کد</code>\n\n"
            "مثال: <code>/togglediscount SALE20</code>"
        )
        return

    code = parts[1].upper()
    async with AsyncSessionFactory() as session:
        from app.repositories.discount_repo import DiscountRepository
        repo = DiscountRepository(session)
        dc = await repo.get_by_code(code)
        if not dc:
            await message.answer(f"❌ کد <code>{code}</code> یافت نشد.")
            return
        dc.is_active = not dc.is_active
        await session.commit()
        status = "✅ فعال" if dc.is_active else "❌ غیرفعال"

    await message.answer(f"کد <code>{code}</code> {status} شد.")


# ── آمار ──────────────────────────────────────────────────────────────────────
@router.message(F.text == "📈 آمار")
async def stats_panel(message: Message, is_admin: bool, **kwargs) -> None:
    if not is_admin:
        return

    async with AsyncSessionFactory() as session:
        from app.services.statistics_service import StatisticsService
        svc = StatisticsService(session)
        stats = await svc.get_global_stats()
        revenue = await svc.get_revenue_breakdown()
        approval_rate = await svc.get_meme_approval_rate()
        new_users = await svc.get_new_users_today()
        jalali_month = await svc.get_jalali_month_revenue()

    await message.answer(
        f"📈 <b>آمار کلی سیستم</b>\n"
        f"━━━━━━━━━━━━━━━\n\n"
        f"👥 کاربران: <b>{fa_number(stats['total_users'])}</b> (+{fa_number(new_users)} امروز)\n\n"
        f"🎭 <b>میم‌ها</b>\n"
        f"  ثبت‌شده: {fa_number(stats['total_memes'])}\n"
        f"  منتشر: {fa_number(stats['published_memes'])}\n"
        f"  نرخ تایید: {approval_rate}٪\n\n"
        f"📢 <b>تبلیغات</b>\n"
        f"  منتشر: {fa_number(stats['published_ads'])}\n\n"
        f"💰 <b>درآمد</b>\n"
        f"  امروز: {fa_number(revenue['today'])} تومان\n"
        f"  هفته: {fa_number(revenue['week'])} تومان\n"
        f"  ماه شمسی: {fa_number(jalali_month)} تومان\n"
        f"  کل: {fa_number(revenue['total'])} تومان"
    )
