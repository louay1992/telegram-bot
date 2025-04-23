#!/usr/bin/env python
"""
نظام مراقبة وإشراف على بوت تيليجرام - Telegram Bot Supervisor

يقوم هذا السكريبت بمراقبة عمليات البوت وإعادة تشغيله في حالة الخمول أو التوقف.
يعمل كطبقة إضافية من الحماية والإشراف.
"""

import json
import logging
import os
import signal
import subprocess
import sys
import time
import threading
from datetime import datetime, timedelta

# إعداد التسجيل
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO,
    filename='supervisor.log'
)
logger = logging.getLogger("TelegramSupervisor")

# إعدادات المراقبة
CHECK_INTERVAL = 60  # الفاصل الزمني للفحص (بالثواني)
INACTIVITY_THRESHOLD = 120  # فترة الخمول المسموح بها قبل إعادة التشغيل (بالثواني)
MAX_MEMORY_USAGE_MB = 300  # الحد الأقصى لاستخدام الذاكرة قبل إعادة التشغيل (بالميغابايت)
RESTART_ATTEMPTS_THRESHOLD = 5  # عدد محاولات إعادة التشغيل قبل الإشعار

# ملفات المراقبة
HEARTBEAT_FILE = "bot_heartbeat.txt"
TELEGRAM_ALIVE_STATUS = "telegram_alive_status.json"
BOT_PROCESS_FILE = "bot_process.pid"
RESTART_LOG_FILE = "restart_supervisor.log"

def log_restart_event(reason):
    """تسجيل حدث إعادة التشغيل"""
    try:
        with open(RESTART_LOG_FILE, "a") as f:
            timestamp = datetime.now().isoformat()
            f.write(f"{timestamp} - {reason}\n")
    except Exception as e:
        logger.error(f"خطأ في تسجيل حدث إعادة التشغيل: {e}")

def get_last_heartbeat_time():
    """الحصول على آخر وقت نبضة قلب للبوت"""
    try:
        if os.path.exists(HEARTBEAT_FILE):
            with open(HEARTBEAT_FILE, 'r') as f:
                timestamp = float(f.read().strip())
                return datetime.fromtimestamp(timestamp)
        return None
    except Exception as e:
        logger.error(f"خطأ في قراءة ملف نبضات القلب: {e}")
        return None

def get_telegram_alive_status():
    """الحصول على حالة نظام الحفاظ على نشاط تيليجرام"""
    try:
        if os.path.exists(TELEGRAM_ALIVE_STATUS):
            with open(TELEGRAM_ALIVE_STATUS, 'r') as f:
                status_data = json.load(f)
                last_check = datetime.fromisoformat(status_data.get('last_check'))
                status = status_data.get('status')
                return status, last_check
        return None, None
    except Exception as e:
        logger.error(f"خطأ في قراءة ملف حالة نظام الحفاظ على نشاط تيليجرام: {e}")
        return None, None

def is_bot_process_running(pid=None):
    """التحقق مما إذا كانت عملية البوت قيد التشغيل"""
    if pid is None:
        try:
            if os.path.exists(BOT_PROCESS_FILE):
                with open(BOT_PROCESS_FILE, 'r') as f:
                    pid = int(f.read().strip())
            else:
                return False
        except Exception as e:
            logger.error(f"خطأ في قراءة ملف PID: {e}")
            return False
    
    try:
        # التحقق من وجود العملية
        os.kill(pid, 0)
        return True
    except OSError:
        return False
    except Exception as e:
        logger.error(f"خطأ في التحقق من حالة العملية: {e}")
        return False

def get_bot_memory_usage(pid=None):
    """الحصول على استخدام الذاكرة لعملية البوت (بالميغابايت)"""
    if pid is None:
        try:
            if os.path.exists(BOT_PROCESS_FILE):
                with open(BOT_PROCESS_FILE, 'r') as f:
                    pid = int(f.read().strip())
            else:
                return 0
        except Exception as e:
            logger.error(f"خطأ في قراءة ملف PID: {e}")
            return 0
    
    try:
        if sys.platform == 'linux':
            # قراءة استخدام الذاكرة من /proc في لينكس
            with open(f'/proc/{pid}/status', 'r') as f:
                for line in f:
                    if line.startswith('VmRSS:'):
                        memory_kb = int(line.split()[1])
                        return memory_kb / 1024.0  # تحويل إلى ميغابايت
        else:
            # استخدام psutil في أنظمة التشغيل الأخرى (يتطلب تثبيت psutil)
            try:
                import psutil
                process = psutil.Process(pid)
                memory_info = process.memory_info()
                return memory_info.rss / (1024 * 1024)  # تحويل إلى ميغابايت
            except ImportError:
                logger.warning("لم يتم العثور على psutil، لا يمكن قياس استخدام الذاكرة في نظام التشغيل هذا")
                return 0
    except Exception as e:
        logger.error(f"خطأ في قراءة استخدام الذاكرة: {e}")
        return 0
    
    return 0

def start_bot_telegram_alive():
    """بدء تشغيل البوت ونظام الحفاظ على نشاط تيليجرام"""
    try:
        # بدء تشغيل البوت
        bot_process = subprocess.Popen(
            [sys.executable, 'bot.py'],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE
        )
        
        # حفظ PID
        with open(BOT_PROCESS_FILE, 'w') as f:
            f.write(str(bot_process.pid))
        
        logger.info(f"✅ تم بدء تشغيل البوت بنجاح (PID: {bot_process.pid})")
        
        # بدء تشغيل نظام الحفاظ على نشاط تيليجرام
        alive_process = subprocess.Popen(
            [sys.executable, 'keep_telegram_alive.py'],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE
        )
        
        logger.info(f"✅ تم بدء تشغيل نظام الحفاظ على نشاط تيليجرام بنجاح (PID: {alive_process.pid})")
        
        return bot_process.pid
    except Exception as e:
        logger.error(f"❌ خطأ في بدء تشغيل البوت: {e}")
        return None

def stop_bot_process(pid=None):
    """إيقاف عملية البوت"""
    if pid is None:
        try:
            if os.path.exists(BOT_PROCESS_FILE):
                with open(BOT_PROCESS_FILE, 'r') as f:
                    pid = int(f.read().strip())
            else:
                logger.warning("⚠️ لم يتم العثور على ملف PID للبوت")
                return False
        except Exception as e:
            logger.error(f"خطأ في قراءة ملف PID: {e}")
            return False
    
    try:
        if is_bot_process_running(pid):
            # أولاً نحاول إرسال إشارة SIGTERM للإغلاق الآمن
            os.kill(pid, signal.SIGTERM)
            
            # ننتظر 5 ثواني للإغلاق الآمن
            for _ in range(5):
                time.sleep(1)
                if not is_bot_process_running(pid):
                    logger.info(f"✅ تم إيقاف البوت بنجاح (PID: {pid})")
                    return True
            
            # إذا لم يتم إغلاق العملية، نجرب إشارة SIGKILL
            os.kill(pid, signal.SIGKILL)
            logger.warning(f"⚠️ تم إجبار البوت على التوقف باستخدام SIGKILL (PID: {pid})")
            return True
        else:
            logger.info(f"ℹ️ عملية البوت غير نشطة حالياً (PID: {pid})")
            return True
    except Exception as e:
        logger.error(f"❌ خطأ في إيقاف عملية البوت: {e}")
        return False

def restart_bot():
    """إعادة تشغيل البوت"""
    try:
        logger.info("🔄 جاري إعادة تشغيل البوت...")
        
        # إيقاف العملية الحالية
        stop_bot_process()
        
        # انتظار لحظة قبل بدء العملية الجديدة
        time.sleep(2)
        
        # بدء تشغيل العملية الجديدة
        new_pid = start_bot_telegram_alive()
        
        if new_pid:
            log_restart_event("إعادة تشغيل ناجحة من قِبل المراقب")
            logger.info(f"✅ تمت إعادة تشغيل البوت بنجاح (PID الجديد: {new_pid})")
            return True
        else:
            log_restart_event("فشل في إعادة تشغيل البوت")
            logger.error("❌ فشل في إعادة تشغيل البوت")
            return False
    except Exception as e:
        log_restart_event(f"خطأ في إعادة تشغيل البوت: {str(e)}")
        logger.error(f"❌ خطأ في إعادة تشغيل البوت: {e}")
        return False

def check_bot_health():
    """فحص صحة البوت واتخاذ الإجراء المناسب"""
    try:
        logger.debug("جاري فحص صحة البوت...")
        
        # التحقق مما إذا كانت العملية قيد التشغيل
        if not is_bot_process_running():
            logger.warning("⚠️ البوت غير نشط! جاري إعادة التشغيل...")
            log_restart_event("البوت غير نشط")
            return restart_bot()
        
        # التحقق من نبضات القلب
        last_heartbeat = get_last_heartbeat_time()
        now = datetime.now()
        
        if last_heartbeat is None:
            logger.warning("⚠️ لم يتم العثور على ملف نبضات القلب! جاري إعادة التشغيل...")
            log_restart_event("ملف نبضات القلب غير موجود")
            return restart_bot()
        
        time_since_last_heartbeat = (now - last_heartbeat).total_seconds()
        
        if time_since_last_heartbeat > INACTIVITY_THRESHOLD:
            logger.warning(f"⚠️ البوت خامل منذ {time_since_last_heartbeat:.2f} ثانية! جاري إعادة التشغيل...")
            log_restart_event(f"خمول لمدة {time_since_last_heartbeat:.2f} ثانية")
            return restart_bot()
        
        # التحقق من استخدام الذاكرة
        memory_usage = get_bot_memory_usage()
        if memory_usage > MAX_MEMORY_USAGE_MB:
            logger.warning(f"⚠️ استخدام الذاكرة مرتفع ({memory_usage:.2f} ميغابايت)! جاري إعادة التشغيل...")
            log_restart_event(f"استخدام ذاكرة مرتفع: {memory_usage:.2f} ميغابايت")
            return restart_bot()
        
        # التحقق من حالة نظام الحفاظ على نشاط تيليجرام
        telegram_status, last_telegram_check = get_telegram_alive_status()
        
        if telegram_status is None or last_telegram_check is None:
            logger.info("ℹ️ لم يتم العثور على ملف حالة نظام الحفاظ على نشاط تيليجرام. يتم تجاهل الفحص...")
        elif telegram_status != "OK":
            logger.warning(f"⚠️ حالة نظام الحفاظ على نشاط تيليجرام: {telegram_status}! جاري إعادة التشغيل...")
            log_restart_event(f"حالة نظام الحفاظ على نشاط تيليجرام: {telegram_status}")
            return restart_bot()
        elif (now - last_telegram_check).total_seconds() > INACTIVITY_THRESHOLD:
            logger.warning(f"⚠️ نظام الحفاظ على نشاط تيليجرام خامل منذ {(now - last_telegram_check).total_seconds():.2f} ثانية! جاري إعادة التشغيل...")
            log_restart_event(f"خمول نظام الحفاظ على نشاط تيليجرام لمدة {(now - last_telegram_check).total_seconds():.2f} ثانية")
            return restart_bot()
        
        logger.debug(f"✓ البوت يعمل بشكل طبيعي (آخر نبضة قلب: {last_heartbeat.strftime('%H:%M:%S')}, استخدام الذاكرة: {memory_usage:.2f} ميغابايت)")
        return True
    except Exception as e:
        logger.error(f"❌ خطأ في فحص صحة البوت: {e}")
        return False

def start_monitoring():
    """بدء مراقبة البوت"""
    restart_attempts = 0
    consecutive_failures = 0
    
    try:
        # أولاً، نتحقق مما إذا كان البوت يعمل بالفعل
        if not is_bot_process_running():
            logger.info("🚀 البوت غير نشط، جاري بدء التشغيل...")
            start_bot_telegram_alive()
        else:
            logger.info("ℹ️ البوت يعمل بالفعل")
        
        logger.info("🔍 بدء مراقبة البوت...")
        
        while True:
            try:
                health_status = check_bot_health()
                
                if health_status:
                    consecutive_failures = 0
                else:
                    consecutive_failures += 1
                
                if consecutive_failures >= 3:
                    logger.critical(f"‼️ {consecutive_failures} فشل متتالي في فحص صحة البوت")
                    restart_attempts += 1
                    
                    if restart_attempts >= RESTART_ATTEMPTS_THRESHOLD:
                        logger.critical(f"‼️ تجاوز عدد محاولات إعادة التشغيل الحد الأقصى ({restart_attempts}/{RESTART_ATTEMPTS_THRESHOLD})")
                        # هنا يمكن إضافة كود لإشعار المسؤول عبر WhatsApp أو البريد الإلكتروني
                        restart_attempts = 0  # إعادة ضبط العداد
                
                time.sleep(CHECK_INTERVAL)
            except KeyboardInterrupt:
                logger.info("👋 تم إيقاف المراقبة بواسطة المستخدم")
                return
            except Exception as e:
                logger.error(f"❌ خطأ في حلقة المراقبة: {e}")
                time.sleep(CHECK_INTERVAL)
    except KeyboardInterrupt:
        logger.info("👋 تم إيقاف المراقبة بواسطة المستخدم")
    except Exception as e:
        logger.error(f"❌ خطأ غير متوقع: {e}")

if __name__ == "__main__":
    logger.info("🚀 بدء تشغيل نظام مراقبة وإشراف بوت تيليجرام...")
    
    try:
        # بدء المراقبة في خيط منفصل
        monitoring_thread = threading.Thread(target=start_monitoring)
        monitoring_thread.daemon = True
        monitoring_thread.start()
        
        # الانتظار للإيقاف بواسطة Ctrl+C
        while monitoring_thread.is_alive():
            time.sleep(1)
    except KeyboardInterrupt:
        logger.info("👋 تم إيقاف نظام المراقبة بواسطة المستخدم")
    except Exception as e:
        logger.error(f"❌ خطأ في الدالة الرئيسية: {e}")