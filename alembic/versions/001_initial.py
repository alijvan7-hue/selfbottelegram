"""Initial schema

Revision ID: 001
Revises:
Create Date: 2024-01-01 00:00:00.000000
"""
from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "001"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ── users ─────────────────────────────────────────────────────────────
    op.create_table(
        "users",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("telegram_id", sa.BigInteger(), nullable=False),
        sa.Column("username", sa.String(255), nullable=True),
        sa.Column("full_name", sa.String(512), nullable=False, server_default=""),
        sa.Column("tokens", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("monthly_tokens", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("is_admin", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("is_banned", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("ban_type", sa.String(20), nullable=True),
        sa.Column("ban_until", sa.DateTime(timezone=True), nullable=True),
        sa.Column("daily_meme_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("last_meme_date", sa.DateTime(timezone=True), nullable=True),
        sa.Column("custom_daily_limit", sa.Integer(), nullable=True),
        sa.Column("no_limit", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("ad_count_in_window", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("ad_window_start", sa.DateTime(timezone=True), nullable=True),
        sa.Column("joined_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_users_telegram_id", "users", ["telegram_id"], unique=True)

    # ── memes ─────────────────────────────────────────────────────────────
    op.create_table(
        "memes",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("file_id", sa.String(512), nullable=False),
        sa.Column("file_type", sa.String(20), nullable=False),
        sa.Column("status", sa.String(20), nullable=False, server_default="pending"),
        sa.Column("reviewed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("reviewer_message_id", sa.BigInteger(), nullable=True),
        sa.Column("is_published", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("published_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("channel_message_id", sa.BigInteger(), nullable=True),
        sa.Column("submitted_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_memes_user_id", "memes", ["user_id"])
    op.create_index("ix_memes_status", "memes", ["status"])

    # ── ads ───────────────────────────────────────────────────────────────
    op.create_table(
        "ads",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("ad_type", sa.String(20), nullable=False),
        sa.Column("text", sa.Text(), nullable=False),
        sa.Column("link", sa.String(2048), nullable=True),
        sa.Column("image_file_id", sa.String(512), nullable=True),
        sa.Column("extra_description", sa.Text(), nullable=True),
        sa.Column("duration_days", sa.Integer(), nullable=True),
        sa.Column("status", sa.String(30), nullable=False, server_default="pending"),
        sa.Column("base_price", sa.Float(), nullable=False, server_default="0"),
        sa.Column("discount_code", sa.String(100), nullable=True),
        sa.Column("discount_amount", sa.Float(), nullable=False, server_default="0"),
        sa.Column("final_price", sa.Float(), nullable=False, server_default="0"),
        sa.Column("payment_receipt_file_id", sa.String(512), nullable=True),
        sa.Column("payment_approved_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("reply_text", sa.Text(), nullable=True),
        sa.Column("submitted_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("approved_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("publish_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("published_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("channel_message_id", sa.BigInteger(), nullable=True),
        sa.Column("reply_message_id", sa.BigInteger(), nullable=True),
        sa.Column("reviewer_message_id", sa.BigInteger(), nullable=True),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_ads_user_id", "ads", ["user_id"])
    op.create_index("ix_ads_status", "ads", ["status"])

    # ── publish_queue ─────────────────────────────────────────────────────
    op.create_table(
        "publish_queue",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("meme_id", sa.Integer(), nullable=False),
        sa.Column("scheduled_time", sa.DateTime(timezone=True), nullable=False),
        sa.Column("status", sa.String(20), nullable=False, server_default="waiting"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["meme_id"], ["memes.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("meme_id"),
    )
    op.create_index("ix_publish_queue_meme_id", "publish_queue", ["meme_id"])
    op.create_index("ix_publish_queue_scheduled_time", "publish_queue", ["scheduled_time"])
    op.create_index("ix_publish_queue_status", "publish_queue", ["status"])

    # ── settings ──────────────────────────────────────────────────────────
    op.create_table(
        "settings",
        sa.Column("key", sa.String(128), nullable=False),
        sa.Column("value", sa.Text(), nullable=False, server_default=""),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint("key"),
    )

    # ── levels ────────────────────────────────────────────────────────────
    op.create_table(
        "levels",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("name", sa.String(128), nullable=False),
        sa.Column("min_tokens", sa.Integer(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("min_tokens"),
    )

    # ── discount_codes ────────────────────────────────────────────────────
    op.create_table(
        "discount_codes",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("code", sa.String(100), nullable=False),
        sa.Column("type", sa.String(10), nullable=False),
        sa.Column("value", sa.Float(), nullable=False),
        sa.Column("max_uses", sa.Integer(), nullable=True),
        sa.Column("used_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default="true"),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("code"),
    )
    op.create_index("ix_discount_codes_code", "discount_codes", ["code"], unique=True)

    # ── revenue_logs ──────────────────────────────────────────────────────
    op.create_table(
        "revenue_logs",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("ad_id", sa.Integer(), nullable=True),
        sa.Column("user_id", sa.Integer(), nullable=True),
        sa.Column("amount", sa.Float(), nullable=False),
        sa.Column("type", sa.String(20), nullable=False),
        sa.Column("date", sa.Date(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["ad_id"], ["ads.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_revenue_logs_ad_id", "revenue_logs", ["ad_id"])
    op.create_index("ix_revenue_logs_user_id", "revenue_logs", ["user_id"])
    op.create_index("ix_revenue_logs_date", "revenue_logs", ["date"])

    # ── system_logs ───────────────────────────────────────────────────────
    op.create_table(
        "system_logs",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("event_type", sa.String(64), nullable=False),
        sa.Column("user_id", sa.BigInteger(), nullable=True),
        sa.Column("admin_id", sa.BigInteger(), nullable=True),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("extra_data", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_system_logs_event_type", "system_logs", ["event_type"])
    op.create_index("ix_system_logs_user_id", "system_logs", ["user_id"])

    # ── seed default settings ─────────────────────────────────────────────
    op.bulk_insert(
        sa.table(
            "settings",
            sa.column("key", sa.String),
            sa.column("value", sa.Text),
        ),
        [
            {"key": "publish_start_hour", "value": "10"},
            {"key": "publish_end_hour", "value": "24"},
            {"key": "min_publish_interval", "value": "60"},
            {"key": "max_publish_interval", "value": "120"},
            {"key": "daily_meme_limit", "value": "2"},
            {"key": "ad_limit_count", "value": "2"},
            {"key": "ad_limit_hours", "value": "4"},
            {"key": "banner_ad_price", "value": "50000"},
            {"key": "oneliner_ad_price", "value": "30000"},
            {"key": "card_number", "value": "6037991234567890"},
            {"key": "card_owner", "value": "نام صاحب کارت"},
            {"key": "support_id", "value": "@support_username"},
            {"key": "queue_paused", "value": "false"},
            {"key": "bot_locked", "value": "false"},
            {"key": "oneliner_sample_image", "value": ""},
            {"key": "oneliner_description", "value": "برای مشاهده نمونه تبلیغات تک خطی به تصویر بالا توجه کنید."},
        ],
    )

    # ── seed default levels ───────────────────────────────────────────────
    op.bulk_insert(
        sa.table(
            "levels",
            sa.column("name", sa.String),
            sa.column("min_tokens", sa.Integer),
        ),
        [
            {"name": "مبتدی", "min_tokens": 5},
            {"name": "فعال", "min_tokens": 20},
            {"name": "حرفه‌ای", "min_tokens": 50},
            {"name": "افسانه‌ای", "min_tokens": 100},
        ],
    )


def downgrade() -> None:
    op.drop_table("system_logs")
    op.drop_table("revenue_logs")
    op.drop_table("discount_codes")
    op.drop_table("levels")
    op.drop_table("settings")
    op.drop_table("publish_queue")
    op.drop_table("ads")
    op.drop_table("memes")
    op.drop_table("users")