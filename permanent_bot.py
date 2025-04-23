#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
نظام تشغيل البوت الدائم - Permanent Bot Launcher
--------------------------------------------------------------------
هذا الملف هو نظام خارجي يقوم بتشغيل bot.py ومراقبة نبضات القلب، وإعادة التشغيل
تلقائيًا في حالة توقف البوت. يعمل كطبقة إضافية للاستمرارية فوق نظام نبضات القلب
الموجود في bot.py.

تسلسل العمل:
1. بدء خيط لمراقبة نبضات القلب
2. تشغيل البوت في خيط منفصل
3. مراقبة ملف نبضات القلب باستمرار
4. إعادة تشغيل البوت تلقائيًا إذا توقفت نبضات القلب
5. تسجيل كافة الأحداث للتحقق من الأخطاء
"""

import os
import sys
import time
import logging
import threading
import subprocess
import signal
import atexit
from datetime import datetime

# إنشاء مجلد للسجلات إذا لم يكن موجودًا
os.makedirs('logs', exist_ok=True)

# إعداد نظام السجلات
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler("logs/permanent_bot.log", encoding='utf-8')
    ]
)
logger = logging.getLogger("permanent_bot")

# ملف نبضات القلب
HEARTBEAT_FILE = "bot_heartbeat.txt"
# ملف حالة تشغيل البوت
BOT_RUNNING_FILE = "bot_process.pid"
# المهلة القصوى للانتظار قبل اعتبار البوت متوقفًا (بالثواني)
MAX_HEARTBEAT_TIMEOUT = 180  # 3 دقائق
# عدد مرات إعادة المحاولة قبل التوقف
MAX_RETRIES = 5
# وقت الانتظار بين المحاولات (بالثواني)
RETRY_WAIT_TIME = 60

# متغيرات عامة
bot_process = None
stop_monitor = False
monitor_thread = None
last_restart_time = None
restart_count = 0

def update_heartbeat():
    """تحديث ملف نبضات القلب"""
    try:
        with open(HEARTBEAT_FILE, "w") as f:
            f.write(str(time.time()))
        logger.debug("تم تحديث ملف نبضات القلب")
    except Exception as e:
        logger.error(f"خطأ في تحديث ملف نبضات القلب: {e}")

def is_bot_running():
    """التحقق من حالة البوت باستخدام ملف نبضات القلب"""
    try:
        if not os.path.exists(HEARTBEAT_FILE):
            logger.warning("ملف نبضات القلب غير موجود")
            return False, "ملف نبضات القلب غير موجود"
            
        with open(HEARTBEAT_FILE, "r") as f:
            timestamp = f.read().strip()
            
        try:
            last_heartbeat = datetime.fromtimestamp(float(timestamp))
            diff = (datetime.now() - last_heartbeat).total_seconds()
            
            # سجل في السجلات زمن آخر نبضة قلب والفرق الزمني
            logger.debug(f"آخر نبضة قلب: {last_heartbeat.strftime('%Y-%m-%d %H:%M:%S')}, الفرق: {diff:.2f} ثانية")
            
            # اعتبار البوت نشطًا إذا كان آخر نبضة قلب خلال المهلة المحددة
            if diff < MAX_HEARTBEAT_TIMEOUT:
                return True, last_heartbeat.strftime("%Y-%m-%d %H:%M:%S")
            else:
                return False, f"آخر نبضة قلب منذ {int(diff)} ثانية، وهي أكبر من الحد المسموح ({MAX_HEARTBEAT_TIMEOUT} ثانية)"
                
        except (ValueError, TypeError) as e:
            logger.error(f"خطأ في تحليل الطابع الزمني: {e}")
            return False, "خطأ في تنسيق الطابع الزمني"
                
    except Exception as e:
        logger.error(f"خطأ عام في التحقق من حالة البوت: {e}")
        return False, str(e)

def start_bot_module():
    """تشغيل البوت باستخدام الوحدة البرمجية bot مباشرة"""
    logger.info("بدء تشغيل البوت باستخدام الوحدة البرمجية")
    try:
        import bot
        bot.start_bot()
        return True
    except ImportError:
        logger.error("فشل في استيراد وحدة bot.py")
        return False
    except Exception as e:
        logger.error(f"خطأ في تشغيل البوت: {e}")
        return False

def start_bot_process():
    """تشغيل البوت كعملية منفصلة"""
    global bot_process
    
    logger.info("بدء تشغيل البوت كعملية منفصلة")
    try:
        # تنظيف أي عمليات سابقة
        if bot_process and bot_process.poll() is None:
            logger.info("إنهاء العملية السابقة")
            try:
                bot_process.terminate()
                time.sleep(2)
            except:
                pass
        
        # تشغيل البوت كعملية منفصلة
        bot_process = subprocess.Popen([sys.executable, "bot.py"], 
                                      stderr=subprocess.PIPE,
                                      stdout=subprocess.PIPE)
        
        # تحديث ملف حالة تشغيل البوت
        with open(BOT_RUNNING_FILE, "w") as f:
            f.write(str(bot_process.pid))
        
        logger.info(f"تم بدء تشغيل البوت بنجاح، رقم العملية: {bot_process.pid}")
        
        # انتظار لحظة للتأكد من بدء التشغيل
        time.sleep(5)
        
        # تحديث ملف نبضات القلب مبدئيًا
        update_heartbeat()
        
        return True
    except Exception as e:
        logger.error(f"خطأ في بدء تشغيل البوت: {e}")
        return False

def monitor_heartbeat():
    """مراقبة نبضات قلب البوت وإعادة تشغيله إذا توقف"""
    global restart_count, last_restart_time, stop_monitor
    
    logger.info("بدء مراقبة نبضات قلب البوت")
    
    while not stop_monitor:
        try:
            bot_running, status_message = is_bot_running()
            
            if not bot_running:
                logger.warning(f"البوت متوقف: {status_message}")
                
                # إعادة تشغيل البوت
                if last_restart_time:
                    time_since_last_restart = (datetime.now() - last_restart_time).total_seconds()
                    # إذا كانت المحاولة الأخيرة لإعادة التشغيل خلال RETRY_WAIT_TIME، انتظر أكثر
                    if time_since_last_restart < RETRY_WAIT_TIME:
                        wait_time = RETRY_WAIT_TIME - time_since_last_restart
                        logger.info(f"الانتظار {wait_time:.0f} ثانية قبل إعادة المحاولة")
                        time.sleep(wait_time)
                
                # التحقق من عدد مرات إعادة المحاولة
                if restart_count >= MAX_RETRIES:
                    logger.error(f"تم الوصول إلى الحد الأقصى من محاولات إعادة التشغيل ({MAX_RETRIES}). توقف المراقبة.")
                    stop_monitor = True
                    continue
                
                # تسجيل وقت إعادة التشغيل
                last_restart_time = datetime.now()
                restart_count += 1
                
                logger.info(f"محاولة إعادة تشغيل البوت (المحاولة {restart_count} من {MAX_RETRIES})")
                
                # محاولة إعادة تشغيل البوت
                result = start_bot_process()
                
                if result:
                    logger.info("تم إعادة تشغيل البوت بنجاح")
                else:
                    logger.error("فشل في إعادة تشغيل البوت")
                    # انتظار قبل المحاولة التالية
                    time.sleep(RETRY_WAIT_TIME)
            else:
                # إذا كان البوت يعمل، يمكن إعادة ضبط عدد محاولات إعادة التشغيل
                # لكن فقط إذا مرت فترة كافية من الوقت منذ آخر إعادة تشغيل
                if last_restart_time and (datetime.now() - last_restart_time).total_seconds() > 3600:  # ساعة
                    restart_count = 0
                    logger.info("تم إعادة ضبط عداد محاولات إعادة التشغيل")
                
                logger.debug(f"البوت يعمل: {status_message}")
            
            # الانتظار قبل التحقق مرة أخرى
            time.sleep(30)
            
        except Exception as e:
            logger.error(f"خطأ في مراقبة نبضات القلب: {e}")
            time.sleep(60)  # انتظار أطول في حالة حدوث خطأ

def cleanup():
    """تنظيف الموارد عند الخروج"""
    global stop_monitor, bot_process
    
    logger.info("تنظيف الموارد قبل الخروج")
    
    # إيقاف خيط المراقبة
    stop_monitor = True
    
    # إيقاف عملية البوت
    if bot_process and bot_process.poll() is None:
        try:
            logger.info("إنهاء عملية البوت")
            bot_process.terminate()
            time.sleep(2)
            if bot_process.poll() is None:
                bot_process.kill()
        except:
            pass
    
    # حذف ملف حالة تشغيل البوت
    if os.path.exists(BOT_RUNNING_FILE):
        try:
            os.remove(BOT_RUNNING_FILE)
        except:
            pass

def signal_handler(sig, frame):
    """معالج الإشارات"""
    logger.info(f"تم استلام إشارة: {sig}")
    cleanup()
    sys.exit(0)

def main():
    """الوظيفة الرئيسية"""
    global monitor_thread
    
    logger.info("بدء تشغيل نظام البوت الدائم")
    
    # إعداد معالجات الإشارات
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    # تسجيل وظيفة التنظيف عند الخروج
    atexit.register(cleanup)
    
    try:
        # تشغيل البوت أولًا
        result = start_bot_process()
        
        if not result:
            logger.error("فشل في بدء تشغيل البوت. إنهاء البرنامج.")
            return 1
        
        # بدء خيط مراقبة نبضات القلب
        monitor_thread = threading.Thread(target=monitor_heartbeat)
        monitor_thread.daemon = True
        monitor_thread.start()
        
        logger.info("تم بدء تشغيل نظام المراقبة")
        
        # الاستمرار في تشغيل البرنامج الرئيسي
        while True:
            # التحقق من حالة خيط المراقبة
            if not monitor_thread.is_alive():
                logger.error("توقف خيط المراقبة. إعادة تشغيله.")
                monitor_thread = threading.Thread(target=monitor_heartbeat)
                monitor_thread.daemon = True
                monitor_thread.start()
            
            # انتظار
            time.sleep(60)
            
            # طباعة معلومات حالة البوت كل دقيقة
            bot_running, status_message = is_bot_running()
            if bot_running:
                logger.info(f"البوت يعمل: {status_message}")
            else:
                logger.warning(f"البوت متوقف: {status_message}")
                
    except KeyboardInterrupt:
        logger.info("تم إيقاف البرنامج بواسطة المستخدم")
        cleanup()
    except Exception as e:
        logger.error(f"خطأ عام: {e}")
        cleanup()
        return 1
        
    return 0

if __name__ == "__main__":
    sys.exit(main())