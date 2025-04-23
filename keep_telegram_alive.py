#!/usr/bin/env python
"""
نظام الحفاظ على نشاط بوت تيليجرام - Keep Telegram Alive System

يقوم هذا السكريبت بإرسال نبضات منتظمة إلى API تيليجرام للحفاظ على نشاط البوت
ويعمل بشكل منفصل ومستقل عن البوت الرئيسي كطبقة إضافية من الحماية.
"""

import asyncio
import logging
import os
import random
import sys
import time
from datetime import datetime

import telegram
from telegram.error import NetworkError, TimedOut, BadRequest, Unauthorized

# إعداد التسجيل
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger("TelegramKeepAlive")

# قراءة توكن البوت من ملف الإعدادات
try:
    import config
    BOT_TOKEN = config.TOKEN
except ImportError:
    try:
        # إذا لم يتم العثور على ملف الإعدادات، نحاول قراءة التوكن من المتغيرات البيئية
        BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN")
    except:
        logger.error("❌ لم يتم العثور على توكن البوت!")
        sys.exit(1)

# الفاصل الزمني بين النبضات (بالثواني)
PING_INTERVAL = 15
MAX_RETRIES = 3
MAX_BACKOFF_TIME = 60  # أقصى وقت للتأخير (بالثواني)

async def send_telegram_ping():
    """إرسال نبضة إلى API تيليجرام"""
    try:
        bot = telegram.Bot(token=BOT_TOKEN)
        me = await bot.get_me()
        logger.info(f"✓ نبضة ناجحة لبوت تيليجرام: {me.username} (ID: {me.id})")
        return True
    except (NetworkError, TimedOut) as e:
        logger.warning(f"⚠️ خطأ شبكة أثناء نبضة تيليجرام: {e}")
        return False
    except (BadRequest, Unauthorized) as e:
        logger.error(f"❌ خطأ في توكن البوت أو صلاحيات API: {e}")
        # في حالة خطأ التوكن، نتوقف عن المحاولة
        sys.exit(1)
    except Exception as e:
        logger.error(f"❌ خطأ غير متوقع: {e}")
        return False

async def backoff_retry(func, max_retries=MAX_RETRIES):
    """تنفيذ الدالة مع آلية التأخير والمحاولة مرة أخرى"""
    for attempt in range(1, max_retries + 1):
        success = await func()
        if success:
            return True
            
        # حساب وقت التأخير مع إضافة عنصر عشوائي (exponential backoff with jitter)
        delay = min(MAX_BACKOFF_TIME, (2 ** attempt) + random.uniform(0, 1))
        logger.warning(f"محاولة فاشلة {attempt}/{max_retries}. المحاولة مرة أخرى بعد {delay:.2f} ثواني...")
        await asyncio.sleep(delay)
    
    logger.error(f"❌ فشلت جميع المحاولات بعد {max_retries} محاولات")
    return False

async def keep_alive_loop():
    """الحلقة الرئيسية للحفاظ على نشاط البوت"""
    logger.info("🚀 بدء نظام الحفاظ على نشاط بوت تيليجرام...")
    consecutive_failures = 0
    
    while True:
        start_time = time.time()
        success = await backoff_retry(send_telegram_ping)
        
        if success:
            consecutive_failures = 0
        else:
            consecutive_failures += 1
            if consecutive_failures >= 3:
                logger.critical(f"❌❌❌ {consecutive_failures} فشل متتالي. يجب التحقق من حالة البوت!")
        
        # حساب الوقت المستغرق والنوم حتى الفاصل الزمني التالي
        elapsed = time.time() - start_time
        sleep_time = max(1, PING_INTERVAL - elapsed)
        logger.debug(f"النوم لمدة {sleep_time:.2f} ثواني حتى النبضة التالية...")
        await asyncio.sleep(sleep_time)

def write_status_file(status, message):
    """كتابة حالة النبضات إلى ملف"""
    try:
        with open("telegram_alive_status.json", "w") as f:
            import json
            json.dump({
                "status": status,
                "last_check": datetime.now().isoformat(),
                "message": message
            }, f)
    except Exception as e:
        logger.error(f"❌ خطأ في كتابة ملف الحالة: {e}")

async def main():
    """الدالة الرئيسية"""
    try:
        # محاولة أولية للتحقق من صحة التوكن
        logger.info("🔍 التحقق من توكن البوت...")
        success = await send_telegram_ping()
        
        if success:
            logger.info("✅ تم التحقق من صحة التوكن بنجاح")
            write_status_file("OK", "تم التحقق من صحة التوكن بنجاح")
            
            # بدء حلقة الحفاظ على النشاط
            await keep_alive_loop()
        else:
            logger.error("❌ فشل التحقق من صحة التوكن")
            write_status_file("ERROR", "فشل التحقق من صحة التوكن")
            sys.exit(1)
            
    except KeyboardInterrupt:
        logger.info("👋 تم إيقاف نظام الحفاظ على النشاط")
        write_status_file("STOPPED", "تم إيقاف النظام بواسطة المستخدم")
    except Exception as e:
        logger.error(f"❌ خطأ غير متوقع في الدالة الرئيسية: {e}")
        write_status_file("ERROR", f"خطأ غير متوقع: {str(e)}")
        sys.exit(1)

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except Exception as e:
        logger.critical(f"❌❌ فشل تشغيل النظام: {e}")
        write_status_file("FATAL", f"فشل تشغيل النظام: {str(e)}")
        sys.exit(1)