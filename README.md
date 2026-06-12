# 🎭 Meme & Ads Manager Bot

یک ربات تلگرام حرفه‌ای برای مدیریت میم و تبلیغات با Python + Aiogram 3 + PostgreSQL

---

## 🚀 تکنولوژی‌ها

| ابزار | نسخه |
|-------|------|
| Python | 3.12 |
| Aiogram | 3.13.1 |
| SQLAlchemy Async | 2.0.36 |
| PostgreSQL | 14+ |
| Alembic | 1.14.0 |
| APScheduler | 3.10.4 |

---

## 📁 ساختار پروژه

```
meme_bot/
├── app/
│   ├── core/          # Config, Database, Bot instance
│   ├── models/        # SQLAlchemy ORM models
│   ├── repositories/  # Database access layer
│   ├── services/      # Business logic
│   ├── handlers/      # Telegram message handlers
│   │   ├── admin/     # Admin-only handlers
│   │   └── ads/       # Ad submission handlers
│   ├── keyboards/     # Reply & Inline keyboards
│   ├── states/        # FSM states
│   ├── middlewares/   # Auth & throttle
│   ├── scheduler/     # APScheduler jobs
│   └── utils/         # Helpers
├── alembic/           # Database migrations
├── Dockerfile
├── railway.json
├── requirements.txt
└── .env.example
```

---

## ⚙️ راه‌اندازی روی Railway

### ۱. ساخت پروژه در Railway

```bash
# Install Railway CLI
npm install -g @railway/cli

# Login
railway login

# Create new project
railway new
```

### ۲. اضافه کردن PostgreSQL

در داشبورد Railway:
1. روی **New** کلیک کنید
2. **Database → PostgreSQL** را انتخاب کنید
3. `DATABASE_URL` به صورت خودکار تنظیم می‌شود

### ۳. تنظیم متغیرهای محیطی

در داشبورد Railway → **Variables**:

```
BOT_TOKEN=your_bot_token
ADMIN_IDS=123456789
CHANNEL_ID=-1001234567890
LOG_CHANNEL_ID=-1001234567891
ADMIN_GROUP_ID=-1001234567892
DEBUG=false
TIMEZONE=Asia/Tehran
```

### ۴. Deploy

```bash
# Connect to project
railway link

# Deploy
railway up
```

---

## 🛠 راه‌اندازی محلی

### ۱. Clone و نصب

```bash
git clone <your-repo>
cd meme_bot

# Create virtual environment
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt
```

### ۲. تنظیم محیط

```bash
cp .env.example .env
# Edit .env with your values
```

### ۳. اجرای Migration

```bash
alembic upgrade head
```

### ۴. اجرای ربات

```bash
python -m app.main
```

---

## 🎛️ دستورات ادمین

| دستور | توضیح |
|-------|-------|
| `/admin` | پنل ادمین |
| `/publish_now <id>` | انتشار فوری میم |
| `/pause_queue` | توقف صف |
| `/resume_queue` | ادامه صف |
| `/lock` | قفل ربات |
| `/unlock` | بازکردن قفل |
| `/ban <id> <7d\|30d\|permanent>` | بن کاربر |
| `/unban <id>` | رفع بن |
| `/addtoken <id> <n>` | افزایش توکن |
| `/removetoken <id> <n>` | کاهش توکن |
| `/setlimit <id> <n\|unlimited>` | تنظیم محدودیت |
| `/user <id>` | اطلاعات کاربر |
| `/set <key> <value>` | تغییر تنظیم |
| `/addlevel <name> <tokens>` | افزودن سطح |
| `/dellevel <id>` | حذف سطح |
| `/adddiscount <code> <percent\|fixed> <value>` | کد تخفیف |
| `/deldiscount <code>` | حذف کد تخفیف |
| `/stats` | آمار کلی |
| `/revenue` | گزارش درآمد |
| `/logs [n]` | آخرین لاگ‌ها |

---

## ⚙️ تنظیمات قابل تغییر

با دستور `/set key value`:

| کلید | توضیح | پیش‌فرض |
|------|-------|---------|
| `publish_start_hour` | ساعت شروع انتشار | 10 |
| `publish_end_hour` | ساعت پایان انتشار | 24 |
| `min_publish_interval` | حداقل فاصله (دقیقه) | 60 |
| `max_publish_interval` | حداکثر فاصله (دقیقه) | 120 |
| `daily_meme_limit` | محدودیت روزانه | 2 |
| `banner_ad_price` | قیمت تبلیغ بنری | 50000 |
| `oneliner_ad_price` | قیمت تبلیغ تک‌خطی | 30000 |
| `card_number` | شماره کارت | — |
| `card_owner` | نام صاحب کارت | — |
| `support_id` | آیدی پشتیبانی | — |
| `queue_paused` | توقف صف | false |
| `bot_locked` | قفل ربات | false |

---

## 📊 معماری دیتابیس

```
users ─────────┬──── memes ──── publish_queue
               └──── ads ────── revenue_logs
settings
levels
discount_codes
system_logs
```

---

## 🔄 سیستم‌های خودکار (APScheduler)

| Job | فرکانس | عملکرد |
|-----|--------|--------|
| publish_queue | هر 5 دقیقه | انتشار میم از صف |
| ad_publish | هر 10 دقیقه | انتشار تبلیغات |
| ad_expiry | هر 1 ساعت | حذف تبلیغات منقضی |
| ad_reply | هر 2 دقیقه | ریپلای خودکار تبلیغ |
| monthly_reset | روزانه 00:05 | ریست لیدربرد ماهانه |
| daily_meme_reset | روزانه 00:01 | ریست شمارنده روزانه |

---

## 📝 لایسنس

MIT License