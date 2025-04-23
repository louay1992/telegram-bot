#!/usr/bin/env python3
"""
سكريبت لجدولة تشغيل البوت (telegram_bot) كل 3 دقائق على منصة Replit.
هذا السكريبت يعمل على:
1. إدارة التشغيل الدوري للبوت
2. مراقبة حالة البوت والتأكد من عمله
3. تسجيل عمليات إعادة التشغيل

كيفية الاستخدام:
1. تشغيل هذا السكريبت مرة واحدة عند بدء النظام
2. سيتولى السكريبت إعادة تشغيل البوت كل 3 دقائق تلقائيًا
"""

import os
import time
import datetime
import threading
import logging
import subprocess
import signal
import sys
import json
from pathlib import Path

# إعداد التسجيل
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    handlers=[
        logging.FileHandler("cron_scheduler.log"),
        logging.StreamHandler()
    ]
)

logger = logging.getLogger("CronScheduler")

# المتغيرات
SCHEDULE_INTERVAL = 180  # 3 دقائق (بالثواني)
BOT_COMMAND = "python bot.py"
BOT_SCRIPT_PATH = "bot.py"
RESTART_LOG_FILE = "scheduler_restart_log.json"
MAX_FAILED_ATTEMPTS = 5
HEARTBEAT_FILE = "bot_heartbeat.txt"
HEARTBEAT_TIMEOUT = 60  # 60 ثانية

# للحفاظ على سجل المحاولات الفاشلة المتتالية
failed_attempts = 0
last_restart_time = None

def load_restart_log():
    """تحميل سجل إعادة التشغيل من الملف"""
    try:
        if not os.path.exists(RESTART_LOG_FILE):
            return []
            
        with open(RESTART_LOG_FILE, 'r') as f:
            data = json.load(f)
            return data
    except Exception as e:
        logger.error(f"خطأ في تحميل سجل إعادة التشغيل: {e}")
        return []

def save_restart_log(log_data):
    """حفظ سجل إعادة التشغيل إلى الملف"""
    try:
        with open(RESTART_LOG_FILE, 'w') as f:
            json.dump(log_data, f, indent=2)
    except Exception as e:
        logger.error(f"خطأ في حفظ سجل إعادة التشغيل: {e}")

def log_restart_attempt(success, reason=None, error=None):
    """تسجيل محاولة إعادة تشغيل في السجل"""
    global last_restart_time
    
    restart_log = load_restart_log()
    now = datetime.datetime.now()
    
    # الحد الأقصى هو 100 سجل
    if len(restart_log) >= 100:
        restart_log = restart_log[-99:]
        
    entry = {
        "timestamp": now.strftime("%Y-%m-%d %H:%M:%S"),
        "success": success,
        "reason": reason if reason else "جدولة دورية"
    }
    
    if error:
        entry["error"] = str(error)
        
    if last_restart_time:
        time_diff = (now - last_restart_time).total_seconds()
        entry["time_since_last_restart"] = f"{time_diff:.1f} ثانية"
        
    restart_log.append(entry)
    last_restart_time = now
    
    save_restart_log(restart_log)

def is_bot_running():
    """التحقق مما إذا كان البوت قيد التشغيل"""
    # الطريقة 1: التحقق من وجود عملية بايثون تشغل bot.py
    try:
        result = subprocess.run(['ps', 'aux'], capture_output=True, text=True)
        if BOT_SCRIPT_PATH in result.stdout:
            return True
    except Exception as e:
        logger.error(f"خطأ في التحقق من حالة العملية: {e}")
    
    # الطريقة 2: التحقق من ملف نبضات القلب
    try:
        if os.path.exists(HEARTBEAT_FILE):
            last_modified = os.path.getmtime(HEARTBEAT_FILE)
            now = time.time()
            
            if (now - last_modified) < HEARTBEAT_TIMEOUT:
                return True
    except Exception as e:
        logger.error(f"خطأ في التحقق من ملف نبضات القلب: {e}")
        
    return False

def restart_bot():
    """إعادة تشغيل البوت"""
    global failed_attempts
    
    try:
        # إيقاف أي عمليات للبوت قد تكون قيد التشغيل
        try:
            result = subprocess.run(['pkill', '-f', BOT_SCRIPT_PATH], capture_output=True)
            logger.info(f"محاولة إيقاف العمليات الحالية للبوت، النتيجة: {result.returncode}")
            # ننتظر لحظة للتأكد من إغلاق العمليات
            time.sleep(2)
        except Exception as kill_error:
            logger.warning(f"خطأ في محاولة إيقاف العمليات الحالية: {kill_error}")
        
        # بدء تشغيل البوت
        process = subprocess.Popen(
            BOT_COMMAND,
            shell=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            preexec_fn=os.setsid
        )
        
        # ننتظر لحظة للتأكد من بدء التشغيل
        time.sleep(5)
        
        # التحقق من نجاح بدء التشغيل
        if process.poll() is None:  # لا تزال العملية قيد التشغيل
            logger.info("✅ تم إعادة تشغيل البوت بنجاح")
            log_restart_attempt(success=True)
            failed_attempts = 0
            return True
        else:
            # قراءة أي أخطاء حدثت
            stderr = process.stderr.read()
            logger.error(f"❌ فشل بدء تشغيل البوت. الخطأ: {stderr}")
            log_restart_attempt(success=False, reason="فشل بدء التشغيل", error=stderr)
            failed_attempts += 1
            return False
            
    except Exception as e:
        logger.error(f"❌ خطأ في إعادة تشغيل البوت: {e}")
        log_restart_attempt(success=False, reason="خطأ في عملية إعادة التشغيل", error=str(e))
        failed_attempts += 1
        return False

def scheduler_loop():
    """الحلقة الرئيسية للجدولة"""
    global failed_attempts
    
    logger.info("🚀 بدء تشغيل نظام الجدولة")
    
    while True:
        try:
            now = datetime.datetime.now()
            logger.info(f"⏰ فحص حالة البوت في {now.strftime('%Y-%m-%d %H:%M:%S')}")
            
            # التحقق مما إذا كان البوت قيد التشغيل
            bot_running = is_bot_running()
            
            if not bot_running:
                logger.warning("⚠️ البوت ليس قيد التشغيل، محاولة إعادة التشغيل...")
                restart_success = restart_bot()
                
                if not restart_success and failed_attempts >= MAX_FAILED_ATTEMPTS:
                    logger.critical(f"🔴 تجاوز عدد محاولات إعادة التشغيل الفاشلة الحد الأقصى ({MAX_FAILED_ATTEMPTS})")
                    # ننتظر فترة أطول قبل المحاولة مرة أخرى
                    time.sleep(SCHEDULE_INTERVAL * 2)
                    failed_attempts = 0  # إعادة تعيين العداد للسماح بمحاولات جديدة
            else:
                # إذا كانت آخر محاولة تشغيل منذ أكثر من 3 دقائق، نقوم بإعادة التشغيل
                if last_restart_time:
                    time_diff = (now - last_restart_time).total_seconds()
                    if time_diff >= SCHEDULE_INTERVAL:
                        logger.info(f"🔄 مر {time_diff:.1f} ثانية منذ آخر إعادة تشغيل، جدولة إعادة تشغيل روتينية")
                        restart_bot()
                else:
                    # لم يتم تسجيل أي محاولة تشغيل سابقة، نقوم بالتشغيل الأول
                    logger.info("🔄 لم يتم تسجيل أي محاولة تشغيل سابقة، بدء التشغيل الأول")
                    restart_bot()
            
            # ننتظر حتى الفحص التالي (كل 3 دقائق)
            logger.info(f"⏳ انتظار {SCHEDULE_INTERVAL} ثانية حتى الفحص التالي")
            time.sleep(SCHEDULE_INTERVAL)
            
        except KeyboardInterrupt:
            logger.info("🛑 تم إيقاف نظام الجدولة بواسطة المستخدم")
            break
        except Exception as e:
            logger.error(f"❌ خطأ في حلقة الجدولة: {e}")
            # ننتظر فترة قصيرة قبل المحاولة مرة أخرى
            time.sleep(30)

def signal_handler(sig, frame):
    """معالج إشارات النظام (مثل SIGINT وSIGTERM)"""
    logger.info(f"🛑 تم استلام إشارة {sig}، إيقاف نظام الجدولة...")
    sys.exit(0)

if __name__ == "__main__":
    # تسجيل معالجي الإشارات
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    # بدء حلقة الجدولة
    scheduler_loop()