#!/usr/bin/env python3
"""
نسخة معززة من بوت تيليجرام - تستخدم جميع التحسينات لضمان استقرار وموثوقية أفضل
"""
import os
import sys
import time
import logging
import json
import datetime
import threading
import signal
import asyncio
from logging.handlers import RotatingFileHandler

# التأكد من تواجد نسخة واحدة فقط من البوت
from instance_lock import ensure_single_instance
lock_file_handle = ensure_single_instance()

# استيراد التكوين الموحد
from unified_config import get_config, set_config

# استيراد وحدة السجلات المتقدمة
from advanced_logging import setup_logger

# استيراد وحدة سياسة إعادة المحاولة
from api_retry import retry_on_error, telegram_rate_limiter

# استيراد وحدة مراقبة الموارد
from resource_monitor import start_monitoring, get_resource_summary, clean_memory

# إعداد السجل
logger = setup_logger("EnhancedBot", "enhanced_bot.log")

# استيراد باقي المكتبات اللازمة للبوت
try:
    import telegram
    from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
    from telegram.ext import (
        Application, CommandHandler, MessageHandler, CallbackQueryHandler,
        ConversationHandler, ContextTypes, filters
    )
    from telegram.error import NetworkError, Unauthorized, TelegramError
except ImportError:
    logger.error("فشل في استيراد مكتبة telegram. تأكد من تثبيتها باستخدام: pip install python-telegram-bot")
    sys.exit(1)

try:
    from apscheduler.schedulers.asyncio import AsyncIOScheduler
    from apscheduler.triggers.interval import IntervalTrigger
except ImportError:
    logger.error("فشل في استيراد مكتبة apscheduler. تأكد من تثبيتها باستخدام: pip install apscheduler")
    sys.exit(1)

# المتغيرات العالمية
BOT_TOKEN = get_config("BOT_TOKEN")
HEARTBEAT_FILE = get_config("HEARTBEAT_FILE")
HEARTBEAT_INTERVAL = get_config("HEARTBEAT_INTERVAL")
TELEGRAM_PING_INTERVAL = get_config("TELEGRAM_PING_INTERVAL")
scheduler = None
shutdown_event = asyncio.Event()
keep_running = True

# دوال إدارة نبضات القلب
def update_heartbeat():
    """تحديث ملف نبضات القلب"""
    try:
        with open(HEARTBEAT_FILE, 'w') as f:
            timestamp = time.time()
            f.write(str(timestamp))
        logger.debug(f"تم تحديث نبضات القلب في {datetime.datetime.now().isoformat()}")
        return timestamp
    except Exception as e:
        logger.error(f"خطأ في تحديث نبضات القلب: {e}")
        return None

# دوال معالجة الإشارات
def signal_handler(sig, frame):
    """معالج إشارات النظام"""
    global keep_running
    logger.info(f"تم استلام الإشارة {sig}، جارٍ إيقاف البوت...")
    keep_running = False
    
    # إعلام النظام بالإيقاف
    asyncio.run_coroutine_threadsafe(shutdown(), asyncio.get_event_loop())

async def shutdown():
    """إيقاف البوت بشكل آمن"""
    shutdown_event.set()
    
    try:
        if scheduler:
            scheduler.shutdown()
            logger.info("تم إيقاف المجدول")
    except Exception as e:
        logger.error(f"خطأ أثناء إيقاف المجدول: {e}")

# دوال البوت الأساسية
async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """معالجة أمر /start"""
    user_id = update.effective_user.id
    username = update.effective_user.username or "المستخدم"
    
    welcome_message = f"مرحباً {username}! أنا بوت الإشعارات المطور. "
    welcome_message += "يمكنك البحث عن إشعار عن طريق إدخال اسم العميل أو رقم الهاتف."
    
    logger.info(f"المستخدم {user_id} بدأ محادثة مع البوت")
    
    await update.message.reply_text(welcome_message)

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """معالجة أمر /help"""
    help_message = """*قائمة الأوامر المتاحة:*
/start - بدء استخدام البوت
/help - عرض هذه المساعدة
/status - عرض حالة النظام

لاستخدام البوت، ما عليك سوى إرسال اسم العميل أو رقم الهاتف للبحث عن الإشعار المرتبط به."""
    
    await update.message.reply_text(help_message, parse_mode=telegram.constants.ParseMode.MARKDOWN)

@retry_on_error(max_retries=3, initial_delay=1, backoff_factor=2)
async def status_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """معالجة أمر /status"""
    # إحضار معلومات النظام
    heartbeat_age = "غير متاح"
    try:
        with open(HEARTBEAT_FILE, 'r') as f:
            timestamp = float(f.read().strip())
            heartbeat_age = f"{time.time() - timestamp:.1f} ثانية"
    except:
        pass
    
    resource_summary = get_resource_summary()
    
    # تكوين رسالة الحالة
    status_message = "*حالة النظام:*\n"
    status_message += f"🟢 البوت يعمل منذ: {context.bot_data.get('start_time', 'غير معروف')}\n"
    status_message += f"💓 آخر نبضة قلب: {heartbeat_age}\n"
    
    if isinstance(resource_summary, dict):
        status_message += f"\n*استخدام الموارد:*\n"
        status_message += f"🧠 الذاكرة: {resource_summary['current']['memory_mb']:.1f} ميغابايت\n"
        status_message += f"⚙️ المعالج: {resource_summary['current']['cpu_percent']}%\n"
        status_message += f"🧵 الخيوط: {resource_summary['current']['threads']}\n"
    
    # إضافة معلومات إضافية
    status_message += f"\n*معلومات النظام:*\n"
    status_message += f"⏱️ وقت التشغيل: {context.bot_data.get('uptime', 'غير معروف')}\n"
    status_message += f"📊 عدد الطلبات: {context.bot_data.get('request_count', 0)}\n"
    status_message += f"🔄 نسخة البوت: النسخة المعززة {get_config('BOT_VERSION', '1.0.0')}\n"
    
    # زيادة عداد الطلبات
    context.bot_data["request_count"] = context.bot_data.get("request_count", 0) + 1
    
    telegram_rate_limiter()  # تطبيق حد معدل الطلبات
    await update.message.reply_text(status_message, parse_mode=telegram.constants.ParseMode.MARKDOWN)

# دوال المجدول
async def heartbeat_updater():
    """تحديث ملف نبضات القلب بشكل دوري"""
    if not shutdown_event.is_set():
        update_heartbeat()

async def telegram_self_ping():
    """إرسال نبضات إلى واجهة برمجة تطبيقات تيليجرام للحفاظ على النشاط"""
    if not shutdown_event.is_set():
        try:
            telegram_rate_limiter()  # تطبيق حد معدل الطلبات
            bot = Application.get_current().bot
            await bot.get_me()
            logger.debug("تم إرسال نبضة تيليجرام بنجاح")
        except Exception as e:
            logger.error(f"خطأ في إرسال نبضة تيليجرام: {e}")

async def memory_check():
    """فحص استخدام الذاكرة وتنظيفها إذا لزم الأمر"""
    if not shutdown_event.is_set():
        clean_memory()

async def check_system_health():
    """فحص صحة النظام بشكل دوري"""
    if not shutdown_event.is_set():
        try:
            # تحديث وقت التشغيل
            app = Application.get_current()
            start_time = app.bot_data.get("start_time_raw")
            if start_time:
                uptime_seconds = (datetime.datetime.now() - start_time).total_seconds()
                days, remainder = divmod(uptime_seconds, 86400)
                hours, remainder = divmod(remainder, 3600)
                minutes, seconds = divmod(remainder, 60)
                
                uptime_str = ""
                if days > 0:
                    uptime_str += f"{int(days)} يوم "
                if hours > 0:
                    uptime_str += f"{int(hours)} ساعة "
                if minutes > 0:
                    uptime_str += f"{int(minutes)} دقيقة "
                uptime_str += f"{int(seconds)} ثانية"
                
                app.bot_data["uptime"] = uptime_str
            
            # إجراء فحوصات صحة أخرى
            logger.debug("تم إجراء فحص صحة النظام")
        except Exception as e:
            logger.error(f"خطأ في فحص صحة النظام: {e}")

async def post_init(application: Application):
    """الإجراءات التي تتم بعد تهيئة التطبيق"""
    # تعيين زمن بدء التشغيل
    application.bot_data["start_time_raw"] = datetime.datetime.now()
    application.bot_data["start_time"] = application.bot_data["start_time_raw"].strftime("%Y-%m-%d %H:%M:%S")
    application.bot_data["request_count"] = 0
    
    # إنشاء المجدول
    global scheduler
    scheduler = AsyncIOScheduler()
    
    # جدولة المهام الدورية
    scheduler.add_job(
        heartbeat_updater,
        trigger=IntervalTrigger(seconds=HEARTBEAT_INTERVAL),
        id="heartbeat_updater",
        replace_existing=True
    )
    
    scheduler.add_job(
        telegram_self_ping,
        trigger=IntervalTrigger(seconds=TELEGRAM_PING_INTERVAL),
        id="telegram_self_ping",
        replace_existing=True
    )
    
    scheduler.add_job(
        memory_check,
        trigger=IntervalTrigger(seconds=3600),  # كل ساعة
        id="memory_check",
        replace_existing=True
    )
    
    scheduler.add_job(
        check_system_health,
        trigger=IntervalTrigger(seconds=300),  # كل 5 دقائق
        id="health_check",
        replace_existing=True
    )
    
    # بدء المجدول
    scheduler.start()
    logger.info("تم بدء المجدول وجدولة المهام الدورية")
    
    # بدء مراقبة الموارد
    start_monitoring()
    logger.info("تم بدء مراقبة الموارد")
    
    # تحديث نبضات القلب الأولي
    update_heartbeat()
    logger.info("تم تحديث نبضات القلب الأولية")

async def error_handler(update, context):
    """معالجة الأخطاء العامة"""
    if isinstance(context.error, NetworkError):
        logger.warning(f"خطأ في الشبكة: {context.error}")
    elif isinstance(context.error, Unauthorized):
        logger.error(f"خطأ في التفويض: {context.error}")
    else:
        logger.error(f"حدث خطأ غير متوقع: {context.error}")

def main():
    """الدالة الرئيسية للبوت"""
    # تسجيل معالجات الإشارات
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    logger.info("بدء تشغيل البوت المعزز...")
    
    # تهيئة البوت
    application = Application.builder().token(BOT_TOKEN).post_init(post_init).build()
    
    # إضافة معالجات الأوامر
    application.add_handler(CommandHandler("start", start_command))
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(CommandHandler("status", status_command))
    
    # إضافة معالج الأخطاء
    application.add_error_handler(error_handler)
    
    # بدء تشغيل البوت
    application.run_polling(allowed_updates=Update.ALL_TYPES)
    
    logger.info("تم إيقاف البوت")

if __name__ == "__main__":
    try:
        # تنظيف الذاكرة قبل البدء
        clean_memory(force=True)
        
        # تحديث نبضات القلب الأولي
        update_heartbeat()
        
        # بدء البوت
        main()
    except Exception as e:
        logger.critical(f"خطأ حرج أدى إلى توقف البوت: {e}", exc_info=True)
    finally:
        # تحرير قفل المثيل
        if lock_file_handle:
            try:
                import fcntl
                fcntl.flock(lock_file_handle, fcntl.LOCK_UN)
                lock_file_handle.close()
                logger.info("تم تحرير قفل المثيل")
            except:
                pass