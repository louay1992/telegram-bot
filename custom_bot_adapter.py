#!/usr/bin/env python
"""
نظام التكامل بين البوت وخادم الويب في نظام واحد
"""

import os
import sys
import logging
import threading
import time
from datetime import datetime
import atexit

# إعداد السجلات
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("bot_adapter")

# المتغيرات العامة
bot_thread = None
bot_running = False
bot_start_time = None
DEFAULT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN", "7406580104:AAGG2JQeeNfsmcGVMCm7hxitIK-qm2yekVg")


def update_heartbeat():
    """تحديث ملف نبضات القلب للبوت"""
    try:
        with open("bot_heartbeat.txt", "w") as f:
            f.write(datetime.now().isoformat())
    except Exception as e:
        logger.error(f"خطأ في تحديث ملف نبضات القلب: {e}")


def get_token():
    """الحصول على توكن البوت"""
    return DEFAULT_TOKEN


def _run_bot():
    """تشغيل البوت في الخلفية"""
    global bot_running, bot_start_time

    # إنشاء حلقة asyncio جديدة في هذا الخيط
    try:
        import asyncio
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        logger.info("🛠️ تم إنشاء وضبط الحلقة الجديدة لخيط الخلفية")
    except Exception as e:
        logger.error(f"❌ خطأ أثناء إعداد الحلقة: {e}")
        return

    logger.info("🔄 بدء تشغيل البوت من الخيط")
    try:
        # تعيين وقت بدء التشغيل
        bot_start_time = datetime.now()
        bot_running = True

        # تحديث نبضات القلب مرة أولى
        update_heartbeat()

        # استدعاء bot.py
        logger.info("🛠️ استيراد وتشغيل الملف bot.py")
        try:
            import bot
            bot.start_bot()
        except ImportError:
            logger.warning("⚠️ لم يتم العثور على bot.py، محاولة استخدام bot_simplified.py")
            try:
                import bot_simplified as bot
                bot.main()
            except ImportError:
                logger.error("❌ فشل في استيراد أي ملف بوت")
                bot_running = False
                return

        # بعد تشغيل التطبيق (Run Polling) لن يصل إلى هنا إلا بعد التوقف
    except Exception as e:
        logger.error(f"❌ خطأ أثناء تشغيل البوت: {e}")
        import traceback
        logger.error(traceback.format_exc())
        bot_running = False


def start_bot_thread():
    """بدء تشغيل خيط البوت"""
    global bot_thread, bot_running

    if bot_thread and bot_thread.is_alive():
        logger.info("ℹ️ البوت يعمل بالفعل")
        return True

    try:
        bot_thread = threading.Thread(target=_run_bot, name="BotRunner")
        bot_thread.daemon = True
        bot_thread.start()

        # منح وقت قصير لبدء البوت
        time.sleep(2)
        if is_bot_running():
            logger.info("✅ تم بدء تشغيل خيط البوت بنجاح")
            atexit.register(stop_bot_thread)
            return True
        else:
            logger.error("❌ فشل في بدء تشغيل البوت ضمن الخيط")
            return False
    except Exception as e:
        logger.error(f"❌ خطأ في بدء تشغيل خيط البوت: {e}")
        return False


def stop_bot_thread():
    """إيقاف خيط البوت"""
    global bot_thread, bot_running
    if bot_thread and bot_thread.is_alive():
        logger.info("⏹️ جاري إيقاف البوت...")
        bot_running = False
        time.sleep(2)
        logger.info("✅ تم إيقاف البوت")
        return True
    logger.info("ℹ️ لا يوجد خيط بوت لتوقيفه")
    return False


def is_bot_running():
    """التحقق من حالة البوت"""
    global bot_thread, bot_running
    # تحقق من الحالة في الخيط
    if bot_thread and bot_thread.is_alive():
        return True
    # التحقق من نبضات القلب
    try:
        if not os.path.exists("bot_heartbeat.txt"):
            return False
        with open("bot_heartbeat.txt", 'r') as f:
            ts = f.read().strip()
        last = datetime.fromisoformat(ts)
        diff = (datetime.now() - last).total_seconds()
        logger.debug(f"وقت منذ آخر نبضة قلب: {diff:.1f}s")
        return diff < 180
    except Exception as e:
        logger.error(f"خطأ في التحقق من نبضات القلب: {e}")
        return False


def get_uptime():
    """مدة تشغيل البوت"""
    if not bot_start_time:
        return "غير متاح"
    delta = datetime.now() - bot_start_time
    # صياغة مبسطة
    return str(delta).split('.')[0]


if __name__ == '__main__':
    logger.info("⚙️ بدء تشغيل البوت في الوضع المباشر")
    start_bot_thread()
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        logger.info("🔌 تم إنهاء العملية عبر المستخدم")
        stop_bot_thread()
