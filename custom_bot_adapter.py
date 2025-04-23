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
DEFAULT_TOKEN = "7406580104:AAGG2JQeeNfsmcGVMCm7hxitIK-qm2yekVg"

def update_heartbeat():
    """تحديث ملف نبضات القلب للبوت"""
    try:
        with open("bot_heartbeat.txt", "w") as f:
            f.write(datetime.now().isoformat())
    except Exception as e:
        logger.error(f"خطأ في تحديث ملف نبضات القلب: {e}")

def get_token():
    """الحصول على توكن البوت"""
    return os.environ.get("TELEGRAM_BOT_TOKEN", DEFAULT_TOKEN)

def _run_bot():
    """تشغيل البوت في الخلفية"""
    global bot_running, bot_start_time

    # 1. إنشاء حلقة asyncio جديدة وربطها بخيط الخلفية
    try:
        import asyncio
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        # تعطيل تسجيل معالجات الإشارات كي لا يحاول set_wakeup_fd في خيط فرعي
        setattr(loop, 'add_signal_handler', lambda *args, **kwargs: None)
        logger.info("🛠️ تم إنشاء وربط حلقة asyncio جديدة لخيط الخلفية")
    except Exception as e:
        logger.warning(f"⚠️ تعذّر إعداد حلقة asyncio للخلفية: {e}")

    logger.info("🔄 بدء تشغيل البوت من الخيط")
    bot_start_time = datetime.now()
    bot_running = True
    update_heartbeat()

    try:
        # 2. استيراد ملف البوت وتشغيله
        import bot
        logger.info("🛠️ استيراد وتشغيل ملف bot.py")
        bot.start_bot()

        # 3. جدولة تحديث نبضات القلب كل 15 ثانية
        def heartbeat_updater():
            while bot_running:
                update_heartbeat()
                time.sleep(15)

        hb_thread = threading.Thread(target=heartbeat_updater)
        hb_thread.daemon = True
        hb_thread.start()

        logger.info("✅ البوت يعمل الآن في الخلفية")
    except Exception as e:
        logger.error(f"❌ خطأ أثناء تشغيل البوت: {e}")
        import traceback
        logger.error(traceback.format_exc())
        bot_running = False

def start_bot_thread():
    """بدء تشغيل خيط البوت"""
    global bot_thread, bot_running

    if bot_thread and bot_thread.is_alive():
        logger.info("البوت يعمل بالفعل")
        return True

    try:
        bot_thread = threading.Thread(target=_run_bot, name="BotThread")
        bot_thread.daemon = True
        bot_thread.start()

        # ننتظر لحظة ليتأكد الخيط أنّه بدأ
        time.sleep(2)

        if is_bot_running():
            logger.info("✅ تم بدء تشغيل خيط البوت بنجاح")
            atexit.register(stop_bot_thread)
            return True
        else:
            logger.error("❌ فشل في بدء تشغيل البوت")
            return False
    except Exception as e:
        logger.error(f"❌ خطأ في بدء تشغيل خيط البوت: {e}")
        return False

def stop_bot_thread():
    """إيقاف خيط البوت"""
    global bot_thread, bot_running

    if bot_thread and bot_thread.is_alive():
        logger.info("جاري إيقاف البوت...")
        bot_running = False
        time.sleep(2)
        logger.info("تم إيقاف البوت")
        return True
    else:
        logger.info("البوت غير متاح للإيقاف")
        return False

def is_bot_running():
    """التحقق من حالة البوت عبر حالة الخيط وملف النبضات"""
    global bot_running, bot_thread

    if bot_thread and bot_thread.is_alive():
        return True

    try:
        if not os.path.exists("bot_heartbeat.txt"):
            return False
        ts = open("bot_heartbeat.txt").read().strip()
        try:
            last = datetime.fromisoformat(ts)
        except ValueError:
            last = datetime.fromtimestamp(float(ts))
        diff = (datetime.now() - last).total_seconds()
        logger.info(f"الفرق منذ آخر نبضة قلب: {diff:.2f} ثانية")
        return diff < 180
    except Exception as e:
        logger.error(f"خطأ في التحقق من حالة البوت: {e}")
        return False

def get_uptime():
    """الحصول على مدة تشغيل البوت"""
    if not bot_start_time:
        return "غير متاح"
    delta = datetime.now() - bot_start_time
    days = delta.days
    hours, rem = divmod(delta.seconds, 3600)
    mins, secs = divmod(rem, 60)
    if days:
        return f"{days} يوم، {hours} ساعة"
    if hours:
        return f"{hours} ساعة، {mins} دقيقة"
    return f"{mins} دقيقة، {secs} ثانية"

if __name__ == "__main__":
    logger.info("بدء تشغيل البوت مباشرة")
    if not start_bot_thread():
        logger.error("تعذّر بدء بوت التيليجرام")
        sys.exit(1)
    try:
        # إبقاء البرنامج الرئيسي قيد التشغيل
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        logger.info("تم طلب الإيقاف من المستخدم")
        stop_bot_thread()
