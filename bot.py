#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os
import sys
import logging
import threading
import time
import asyncio
import psutil
from datetime import datetime, timedelta

from telegram import (
    Update,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    ReplyKeyboardMarkup,
    KeyboardButton,
    error as telegram_error
)
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    CallbackQueryHandler,
    ContextTypes,
    filters
)

# استيراد نظام قفل المثيل
from instance_lock import check_single_instance

import config
import strings as st
import database as db
import ultramsg_service as sms_service  # خدمة UltraMsg للواتساب

# استيراد جميع Handlers
from admin_handlers import (
    get_admin_handlers, add_notification, list_notifications,
    admin_help, manage_admins,
    message_template_command, welcome_template_command,
    received_name, received_phone, received_image,
    NAME, PHONE, IMAGE, REMINDER_HOURS, received_reminder_hours
)
from search_handlers import get_search_handlers, AWAITING_SEARCH_QUERY, received_search_query
from stats_handlers import get_stats_handlers
from delivery_handlers import get_delivery_handlers
from search_history_handlers import get_search_history_handler
from filter_handlers import get_filter_handlers
from advanced_search_handlers import get_advanced_search_handler
from permissions_handlers import get_permissions_handlers
from theme_handlers import get_theme_handlers
from backup_handlers import get_backup_handlers
from personality_handlers import get_personality_handlers
from ai_handlers import get_ai_handlers, ai_start, handle_chat_message, handle_ai_callback, handle_image_upload

# إعداد السجلات
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

HEARTBEAT_FILE = "bot_heartbeat.txt"
HEARTBEAT_INTERVAL = 30  # ثوانٍ

def update_heartbeat_file() -> bool:
    """تحديث نبضة القلب بملف نصي."""
    try:
        with open(HEARTBEAT_FILE, 'w') as f:
            f.write(str(datetime.now().timestamp()))
        return True
    except Exception as e:
        logger.error(f"فشل في تحديث نبضات القلب: {e}")
        return False

async def heartbeat_updater(context: ContextTypes.DEFAULT_TYPE):
    """تعديل دوري لنبضات القلب ومراقبة الذاكرة."""
    update_heartbeat_file()
    # مراقبة الذاكرة:
    try:
        mem = psutil.Process(os.getpid()).memory_info().rss / 1024**2
        if mem > 250:
            logger.warning(f"استخدام الذاكرة {mem:.1f}MiB > 250MiB، سيُعاد التشغيل")
            with open("force_restart", "w") as f:
                f.write(f"Memory exceeded: {mem:.1f}MiB at {datetime.now().isoformat()}")
            # إرسال إشعار واتساب:
            try:
                from bot_status_monitor import send_bot_status_notification
                send_bot_status_notification(is_down=True)
            except Exception as e:
                logger.error(f"فشل إرسال إشعار الواتساب: {e}")
    except Exception as e:
        logger.error(f"خطأ مراقبة الذاكرة: {e}")

async def telegram_self_ping(context: ContextTypes.DEFAULT_TYPE) -> bool:
    """نبض Telegram API ثلاثي الأوجه للحفاظ على الاتصال."""
    max_attempts = 5
    success = False

    # طريقة 1: getMe
    for i in range(max_attempts):
        try:
            await context.bot.get_me()
            success = True
            break
        except (telegram_error.NetworkError, telegram_error.TimedOut):
            await asyncio.sleep(0.5 * (i+1))
        except Exception:
            await asyncio.sleep(1)

    # طريقة 2: send_chat_action
    if not success:
        admin_id = db.get_main_admin_id()
        if admin_id:
            action = ["typing","upload_photo","record_voice","upload_document","find_location"][0]
            try:
                await context.bot.send_chat_action(admin_id, action)
                success = True
            except Exception:
                pass

    # طريقة 3: getUpdates
    if not success:
        try:
            await context.bot.get_updates(limit=1, timeout=1, offset=-1)
            success = True
        except Exception:
            pass

    update_heartbeat_file()
    if not success:
        logger.error("فشلت جميع محاولات نبض Telegram")
    return success

def create_admin_keyboard() -> ReplyKeyboardMarkup:
    kb = [
        [KeyboardButton("➕ إضافة إشعار"), KeyboardButton("📋 قائمة الإشعارات")],
        [KeyboardButton("🔍 تصفية الإشعارات"), KeyboardButton("🔍 البحث المتقدم")],
        [KeyboardButton("📋 قائمة الشحنات المستلمة"), KeyboardButton("📊 الإحصائيات")],
        [KeyboardButton("👥 إدارة المسؤولين"), KeyboardButton("🛡️ إدارة الصلاحيات")],
        [KeyboardButton("✏️ قالب الرسالة"), KeyboardButton("✏️ قالب الترحيب")],
        [KeyboardButton("🎨 إعدادات السمة"), KeyboardButton("🤖 شخصية البوت")],
        [KeyboardButton("🚀 الحملات التسويقية"), KeyboardButton("💾 النسخ الاحتياطي")],
        [KeyboardButton("🧠 المساعد الذكي"), KeyboardButton("❓ مساعدة المسؤول")],
        [KeyboardButton(st.MAIN_MENU_BUTTON)]
    ]
    return ReplyKeyboardMarkup(kb, resize_keyboard=True)

def create_user_keyboard() -> ReplyKeyboardMarkup:
    kb = [
        [KeyboardButton("🔍 بحث باسم العميل"), KeyboardButton("📱 بحث برقم الهاتف")],
        [KeyboardButton("📋 سجلات البحث السابقة"), KeyboardButton("✅ تأكيد استلام زبون")],
        [KeyboardButton("📋 قائمة الشحنات المستلمة"), KeyboardButton("🧠 المساعد الذكي")],
        [KeyboardButton("❓ المساعدة"), KeyboardButton(st.MAIN_MENU_BUTTON)]
    ]
    return ReplyKeyboardMarkup(kb, resize_keyboard=True)

# ———————————————————————————————————————————
# هنا تُعرَّف جميع دوال الأوامر: /start, /help, cancel, restart_command, handle_keyboard_buttons, handle_unknown_command, error_handler
# قدّمتها سابقًا بالكامل ولا حاجة لتكرارها هنا
# ———————————————————————————————————————————

def build_application() -> Application:
    """إنشاء وضبط الـ Application وكل Handlers."""
    # التحقق من المثيل الوحيد:
    if not check_single_instance():
        logger.error("مثيل آخر يعمل بالفعل. الخروج.")
        sys.exit(1)

    cleanup_marker_files()
    os.makedirs("data", exist_ok=True)
    os.makedirs("data/images", exist_ok=True)

    # Keep-Alive HTTP server (اختياري)
    try:
        import keep_alive
        keep_alive.start_keep_alive_service()
    except ImportError:
        pass

    # بناء التطبيق
    token = None
    try:
        from unified_config import get_bot_token
        token = get_bot_token()
    except ImportError:
        token = config.TOKEN

    app = Application.builder().token(token).build()

    # إضافة JobQueue للنبضات والتذكيرات
    app.job_queue.run_repeating(heartbeat_updater, interval=15, first=5)
    app.job_queue.run_repeating(telegram_self_ping, interval=10, first=5)
    app.job_queue.run_repeating(check_for_reminders, interval=60, first=10)

    # تسجيل كل Handlers
    # — أوامر أساسية
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("help", help_command))
    app.add_handler(CommandHandler("cancel", cancel_command))
    app.add_handler(CommandHandler("restart", restart_command))
    app.add_handler(CommandHandler(st.MAIN_MENU_COMMAND, main_menu_command))
    # — بقية CommandHandlers (permissions, theme, marketing...)
    # — كل Handlers من get_admin_handlers(), get_search_handlers(), ...
    for h in get_admin_handlers():       app.add_handler(h)
    for h in get_search_handlers():      app.add_handler(h)
    for h in get_stats_handlers():       app.add_handler(h)
    for h in get_delivery_handlers():    app.add_handler(h)
    app.add_handler(get_search_history_handler())
    for h in get_filter_handlers():      app.add_handler(h)
    app.add_handler(get_advanced_search_handler())
    for h in get_permissions_handlers(): app.add_handler(h)
    for h in get_theme_handlers():       app.add_handler(h)
    for h in get_personality_handlers(): app.add_handler(h)
    for h in get_backup_handlers():      app.add_handler(h)
    for h in get_ai_handlers():          app.add_handler(h)

    # MessageHandlers و CallbackQueryHandlers
    app.add_handler(MessageHandler(filters.PHOTO, handle_photos))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_keyboard_buttons))
    app.add_handler(MessageHandler(filters.COMMAND, handle_unknown_command))
    app.add_error_handler(error_handler)

    return app

def start_bot():
    """نقطة الدخول لتشغيل Polling مرة واحدة."""
    application = build_application()
    logger.info("🔄 Starting polling...")
    application.run_polling()
    logger.info("✅ Polling stopped.")

def cleanup_marker_files():
    """إزالة ملفات العلامات من عمليات سابقة."""
    for fname in (
        "bot_shutdown_marker", "watchdog_ping",
        "bot_restart_marker", "restart_requested.log", "bot_start_clean"
    ):
        try:
            if os.path.exists(fname):
                os.remove(fname)
        except Exception:
            pass

if __name__ == "__main__":
    start_bot()
