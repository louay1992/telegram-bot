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
    
    logger.info("بدء تشغيل البوت من الخيط")
    
    try:
        # تعيين وقت بدء التشغيل
        bot_start_time = datetime.now()
        bot_running = True
        
        # تحديث ملف نبضات القلب
        update_heartbeat()
        
        # استدعاء bot.py بشكل غير مباشر
        logger.info("استدعاء البوت من الخيط...")
        
        # يمكننا استخدام استيراد ديناميكي للبوت
        try:
            import bot
            logger.info("تم استيراد بوت تيليجرام")
            # استخدام وظيفة start_bot الجديدة بدلاً من الاستدعاء المباشر
            bot.start_bot()
        except ImportError:
            logger.error("فشل في استيراد ملف bot.py، محاولة استخدام bot_simplified.py")
            try:
                import bot_simplified as bot
                logger.info("تم استيراد بوت تيليجرام المبسط")
                bot.main()
            except ImportError:
                logger.error("فشل في استيراد ملفات البوت")
                bot_running = False
                return
        
        # إنشاء خيط لتحديث ملف نبضات القلب بشكل دوري
        def heartbeat_updater():
            while bot_running:
                update_heartbeat()
                time.sleep(15)  # تحديث كل 15 ثانية
                
        heartbeat_thread = threading.Thread(target=heartbeat_updater)
        heartbeat_thread.daemon = True
        heartbeat_thread.start()
        
        # البوت يعمل الآن في الخلفية
        logger.info("✅ البوت يعمل الآن في الخلفية")
        
    except Exception as e:
        logger.error(f"❌ خطأ أثناء تشغيل البوت: {e}")
        import traceback
        logger.error(traceback.format_exc())
        bot_running = False

def start_bot_thread():
    """بدء تشغيل خيط البوت"""
    global bot_thread, bot_running
    
    if bot_thread is not None and bot_thread.is_alive():
        logger.info("البوت يعمل بالفعل")
        return True
    
    try:
        # إنشاء خيط جديد لتشغيل البوت
        bot_thread = threading.Thread(target=_run_bot)
        bot_thread.daemon = True  # جعل الخيط daemon لكي يتم إيقافه عند إنهاء البرنامج الرئيسي
        bot_thread.start()
        
        # انتظار بدء البوت
        time.sleep(2)
        
        if is_bot_running():
            logger.info("✅ تم بدء تشغيل خيط البوت بنجاح")
            # تسجيل دالة لإيقاف البوت عند الخروج
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
    
    if bot_thread is not None and bot_thread.is_alive():
        logger.info("جاري إيقاف البوت...")
        bot_running = False
        
        # ملاحظة: لا يمكننا استخدام join هنا لأن خيط daemon لا يمكن إيقافه بهذه الطريقة
        time.sleep(2)
        
        logger.info("تم إيقاف البوت")
        return True
    else:
        logger.info("البوت غير متاح للإيقاف")
        return False

def is_bot_running():
    """التحقق من حالة البوت"""
    global bot_running, bot_thread
    
    # تحقق مما إذا كان خيط البوت موجودًا ونشطًا
    if bot_thread is not None and bot_thread.is_alive():
        return True
    
    # هناك حالة حيث يكون bot_thread غير نشط ولكن البوت يعمل في workflow منفصل
    # لذلك سنتحقق من ملف نبضات القلب أيضًا
    try:
        if not os.path.exists("bot_heartbeat.txt"):
            logger.warning("ملف نبضات القلب غير موجود")
            return False
            
        with open("bot_heartbeat.txt", "r") as f:
            timestamp = f.read().strip()
            
        try:
            # محاولة تحليل الطابع الزمني بصيغة ISO
            last_heartbeat = datetime.fromisoformat(timestamp)
        except ValueError:
            # إذا كان بصيغة الطابع الزمني العادي
            try:
                last_heartbeat = datetime.fromtimestamp(float(timestamp))
            except (ValueError, TypeError):
                logger.error("تنسيق ملف نبضات القلب غير صالح")
                return False
            
        # تحقق من الفرق الزمني - زيادة المدة إلى 3 دقائق نظرًا لأن مهام cron
        # تعمل كل 3 دقائق في cron.toml
        diff = (datetime.now() - last_heartbeat).total_seconds()
        
        # تسجيل الفرق الزمني للتشخيص
        logger.info(f"الفرق الزمني منذ آخر نبضة قلب: {diff:.2f} ثانية")
        
        # زيادة المدة المسموح بها قبل اعتبار البوت متوقفًا
        return diff < 180  # أقل من 3 دقائق
            
    except Exception as e:
        logger.error(f"خطأ في التحقق من حالة البوت: {e}")
        import traceback
        logger.error(traceback.format_exc())
        return False

def get_uptime():
    """الحصول على مدة تشغيل البوت"""
    global bot_start_time
    
    if bot_start_time is None:
        return "غير متاح"
        
    uptime = datetime.now() - bot_start_time
    days = uptime.days
    hours, remainder = divmod(uptime.seconds, 3600)
    minutes, seconds = divmod(remainder, 60)
    
    if days > 0:
        return f"{days} يوم, {hours} ساعة, {minutes} دقيقة"
    elif hours > 0:
        return f"{hours} ساعة, {minutes} دقيقة"
    else:
        return f"{minutes} دقيقة, {seconds} ثانية"

if __name__ == "__main__":
    # تشغيل البوت مباشرة
    logger.info("بدء تشغيل البوت مباشرة")
    start_bot_thread()
    
    try:
        # الحفاظ على البرنامج الرئيسي قيد التشغيل
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        logger.info("تم طلب الإيقاف من المستخدم")
        stop_bot_thread()