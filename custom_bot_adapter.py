#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
نظام التكامل بين البوت وخادم الويب في نظام واحد
"""

import os
import sys
import logging
import threading
import time
import asyncio
import atexit
from datetime import datetime

# ==== إعدادات السجلات ====
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("bot_adapter")

# ==== الإعدادات العامة ====
bot_thread = None
_stop_event = threading.Event()

# مسار ونافذة تحديث نبضات القلب
HEARTBEAT_FILE = os.environ.get("BOT_HEARTBEAT_FILE", "bot_heartbeat.txt")
HEARTBEAT_INTERVAL = int(os.environ.get("BOT_HEARTBEAT_INTERVAL", 15))
DEFAULT_TOKEN = "7406580104:AAGG2JQeeNfsmcGVMCm7hxitIK-qm2yekVg"


def update_heartbeat():
    """تحديث ملف نبضات القلب بأحدث توقيت UTC"""
    try:
        # ضمان وجود المجلد
        directory = os.path.dirname(HEARTBEAT_FILE) or '.'
        os.makedirs(directory, exist_ok=True)
        with open(HEARTBEAT_FILE, "w") as f:
            f.write(datetime.utcnow().isoformat())
    except Exception:
        logger.exception("خطأ في تحديث ملف نبضات القلب")


def _run_bot():
    """تشغيل البوت داخل حلقة asyncio جديدة في خيط منفصل"""
    # إنشاء حلقة جديدة وربطها بالخيط
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    # تعطيل معالجات الإشارات لتجنب set_wakeup_fd
    loop.add_signal_handler = lambda *args, **kwargs: None

    # ضبط التوكن قبل استيراد bot.py
    token = os.environ.get("TELEGRAM_BOT_TOKEN", DEFAULT_TOKEN)
    os.environ["TELEGRAM_BOT_TOKEN"] = token

    logger.info("🔄 بدء تشغيل البوت في الخلفية")
    update_heartbeat()

    try:
        import bot  # استيراد ملف البوت الرئيسي

        # إذا كانت الدالة build_application موجودة، نستخدمها
        if hasattr(bot, "build_application"):
            application = bot.build_application()
            # تشغيل polling ضمن الحلقة
            loop.create_task(application.run_polling())
        else:
            # بديل: استدعاء start_bot في Executor
            loop.run_in_executor(None, bot.start_bot)

        # جدولة نبضات القلب بشكل دوري
        def heartbeat_loop():
            while not _stop_event.wait(HEARTBEAT_INTERVAL):
                update_heartbeat()

        threading.Thread(target=heartbeat_loop, daemon=True).start()

        # تشغيل الحلقة إلى الأبد
        loop.run_forever()
    except Exception:
        logger.exception("❌ خطأ أثناء تشغيل البوت")
    finally:
        try:
            loop.stop()
        except Exception:
            pass


def start_bot_thread():
    """بدء خيط تشغيل البوت إذا لم يكن قيد التشغيل"""
    global bot_thread
    if bot_thread and bot_thread.is_alive():
        logger.info("البوت يعمل بالفعل")
        return True

    _stop_event.clear()
    bot_thread = threading.Thread(target=_run_bot, name="BotThread", daemon=True)
    bot_thread.start()
    time.sleep(2)

    if not is_bot_running():
        logger.error("❌ فشل في بدء بوت التيليجرام")
        return False

    atexit.register(stop_bot_thread)
    logger.info("✅ تم بدء بوت التيليجرام في خيط خلفي")
    return True


def stop_bot_thread():
    """إيقاف خيط البوت وإغلاق الحلقة"""
    _stop_event.set()
    if bot_thread:
        bot_thread.join(timeout=2)
    logger.info("✅ تم إيقاف بوت التيليجرام")
    return True


def is_bot_running():
    """التحقق من حالة البوت عبر الخيط وملف نبضات القلب"""
    if bot_thread and bot_thread.is_alive():
        return True

    try:
        with open(HEARTBEAT_FILE) as f:
            ts = f.read().strip()
        last = datetime.fromisoformat(ts)
        delta = (datetime.utcnow() - last).total_seconds()
        logger.debug(f"الفرق منذ آخر نبضة قلب: {delta:.2f} ثوانٍ")
        return delta < HEARTBEAT_INTERVAL * 3
    except Exception:
        return False


def get_uptime():
    """إرجاع مدة تشغيل البوت بناءً على آخر نبضة قلب"""
    try:
        with open(HEARTBEAT_FILE) as f:
            ts = f.read().strip()
        last = datetime.fromisoformat(ts)
        uptime = datetime.utcnow() - last
        days = uptime.days
        hrs, rem = divmod(uptime.seconds, 3600)
        mins, secs = divmod(rem, 60)
        if days:
            return f"{days} يوم، {hrs} ساعة"
        if hrs:
            return f"{hrs} ساعة، {mins} دقيقة"
        return f"{mins} دقيقة، {secs} ثانية"
    except Exception:
        return "غير متاح"


if __name__ == "__main__":
    if not start_bot_thread():
        sys.exit(1)
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        stop_bot_thread()
