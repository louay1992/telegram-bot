#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
نظام إعادة التشغيل التلقائي المتقدم للبوت
--------------------------------------------------------------------
هذا النظام يوفر إعادة تشغيل ذكية وديناميكية للبوت في الحالات التالية:
1. تجاوز استخدام الموارد (CPU, RAM)
2. توقف نبضات القلب للبوت
3. أخطاء غير متوقعة في تنفيذ البوت
4. طلبات إعادة تشغيل من واجهة الإدارة

مع الميزات التالية:
- حماية من تكرار العمليات عبر instance_lock
- إشعارات متعددة القنوات (Telegram, WhatsApp عبر UltraMsg)
- تكامل مباشر مع custom_bot_adapter
- مراقبة الموارد في الوقت الحقيقي
"""

import os
import sys
import time
import psutil
import signal
import logging
import threading
import subprocess
import atexit
import json
import fcntl
import requests
import traceback
from datetime import datetime, timedelta

# إنشاء مجلد للسجلات إذا لم يكن موجودًا
os.makedirs('logs', exist_ok=True)

# إعداد نظام السجلات
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler("logs/auto_restart.log", encoding='utf-8')
    ]
)
logger = logging.getLogger("auto_restart")

# ملفات النظام
HEARTBEAT_FILE = "bot_heartbeat.txt"
BOT_RUNNING_FILE = "bot_process.pid"
INSTANCE_LOCK_FILE = "auto_restart.lock"
STATUS_FILE = ".keep_alive_status.json"

# حدود الموارد
MAX_CPU_PERCENT = 90.0  # الحد الأقصى لاستخدام المعالج (%)
MAX_MEMORY_PERCENT = 85.0  # الحد الأقصى لاستخدام الذاكرة (%)
MAX_HEARTBEAT_TIMEOUT = 180  # الحد الأقصى للانتظار قبل اعتبار البوت متوقفًا (ثوانية)

# فترات المراقبة
RESOURCE_CHECK_INTERVAL = 30  # فترة مراقبة الموارد (ثوانية)
HEARTBEAT_CHECK_INTERVAL = 30  # فترة مراقبة نبضات القلب (ثوانية)

# متغيرات عامة
bot_process = None
stop_monitor = False
resource_monitor_thread = None
heartbeat_monitor_thread = None
lock_file_handle = None
restart_count = 0
last_restart_time = None
max_restart_count = 5  # الحد الأقصى لعدد مرات إعادة التشغيل في فترة زمنية محددة
restart_period = 3600  # فترة إعادة ضبط عداد إعادة التشغيل (ثوانية)

# التحقق من وجود رموز الوصول للإشعارات
TELEGRAM_BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN")
ADMIN_CHAT_ID = os.environ.get("ADMIN_CHAT_ID", "")  # إذا كان غير محدد، استخدم قيمة فارغة
ULTRAMSG_TOKEN = os.environ.get("ULTRAMSG_TOKEN")
ULTRAMSG_INSTANCE_ID = os.environ.get("ULTRAMSG_INSTANCE_ID")
ADMIN_PHONE = os.environ.get("ADMIN_PHONE", "")  # رقم هاتف المسؤول لإرسال إشعارات WhatsApp


def acquire_lock():
    """
    الحصول على قفل لضمان تشغيل نسخة واحدة فقط من النظام
    """
    global lock_file_handle
    try:
        lock_file_handle = open(INSTANCE_LOCK_FILE, 'w')
        fcntl.flock(lock_file_handle, fcntl.LOCK_EX | fcntl.LOCK_NB)
        logger.info("تم الحصول على قفل النظام بنجاح")
        return True
    except IOError:
        logger.warning("فشل في الحصول على قفل النظام - يبدو أن هناك نسخة أخرى قيد التشغيل")
        return False


def release_lock():
    """
    تحرير القفل عند الانتهاء
    """
    global lock_file_handle
    if lock_file_handle:
        try:
            fcntl.flock(lock_file_handle, fcntl.LOCK_UN)
            lock_file_handle.close()
            os.remove(INSTANCE_LOCK_FILE)
            logger.info("تم تحرير قفل النظام")
        except Exception as e:
            logger.error(f"خطأ في تحرير قفل النظام: {e}")


def update_status(status, status_message=""):
    """
    تحديث ملف حالة النظام
    """
    try:
        status_data = {
            "timestamp": datetime.now().isoformat(),
            "status": status,
            "message": status_message,
            "last_restart": last_restart_time.isoformat() if last_restart_time else None,
            "restart_count": restart_count
        }
        
        with open(STATUS_FILE, 'w', encoding='utf-8') as f:
            json.dump(status_data, f, ensure_ascii=False, indent=2)
            
        logger.debug(f"تم تحديث ملف الحالة: {status} - {status_message}")
    except Exception as e:
        logger.error(f"فشل في تحديث ملف الحالة: {e}")


def send_telegram_notification(message):
    """
    إرسال إشعار عبر تيليجرام
    """
    if not TELEGRAM_BOT_TOKEN or not ADMIN_CHAT_ID:
        logger.warning("لم يتم تكوين رمز تيليجرام أو معرف المحادثة")
        return False
        
    try:
        url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
        data = {
            "chat_id": ADMIN_CHAT_ID,
            "text": f"🔄 إشعار نظام إعادة التشغيل:\n\n{message}",
            "parse_mode": "HTML"
        }
        response = requests.post(url, data=data, timeout=10)
        
        if response.status_code == 200:
            logger.info("تم إرسال إشعار تيليجرام بنجاح")
            return True
        else:
            logger.warning(f"فشل في إرسال إشعار تيليجرام: {response.text}")
            return False
    except Exception as e:
        logger.error(f"خطأ في إرسال إشعار تيليجرام: {e}")
        return False


def send_whatsapp_notification(message):
    """
    إرسال إشعار عبر WhatsApp باستخدام UltraMsg
    """
    if not ULTRAMSG_TOKEN or not ULTRAMSG_INSTANCE_ID or not ADMIN_PHONE:
        logger.warning("لم يتم تكوين بيانات UltraMsg أو رقم الهاتف")
        return False
        
    try:
        url = f"https://api.ultramsg.com/{ULTRAMSG_INSTANCE_ID}/messages/chat"
        
        # تنسيق الرسالة
        formatted_message = f"*🔄 إشعار نظام إعادة التشغيل*\n\n{message}"
        
        payload = {
            "token": ULTRAMSG_TOKEN,
            "to": ADMIN_PHONE,
            "body": formatted_message
        }
        
        headers = {'content-type': 'application/x-www-form-urlencoded'}
        response = requests.post(url, data=payload, headers=headers, timeout=10)
        
        if response.status_code == 200:
            logger.info("تم إرسال إشعار WhatsApp بنجاح")
            return True
        else:
            logger.warning(f"فشل في إرسال إشعار WhatsApp: {response.text}")
            return False
    except Exception as e:
        logger.error(f"خطأ في إرسال إشعار WhatsApp: {e}")
        return False


def send_notification(message, priority="normal"):
    """
    إرسال إشعار عبر قنوات متعددة حسب الأولوية
    """
    logger.info(f"إشعار ({priority}): {message}")
    
    # إرسال عبر تيليجرام
    telegram_sent = send_telegram_notification(message)
    
    # إرسال عبر WhatsApp للإشعارات عالية الأولوية فقط
    whatsapp_sent = False
    if priority == "high":
        whatsapp_sent = send_whatsapp_notification(message)
        
    return telegram_sent or whatsapp_sent


def check_bot_heartbeat():
    """
    التحقق من نبضات قلب البوت
    """
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


def check_system_resources():
    """
    فحص موارد النظام (CPU, RAM)
    """
    try:
        # الحصول على استخدام المعالج
        cpu_percent = psutil.cpu_percent(interval=1)
        
        # الحصول على استخدام الذاكرة
        memory = psutil.virtual_memory()
        memory_percent = memory.percent
        
        logger.debug(f"استخدام المعالج: {cpu_percent:.1f}%, استخدام الذاكرة: {memory_percent:.1f}%")
        
        # التحقق من تجاوز الحدود
        if cpu_percent > MAX_CPU_PERCENT:
            return False, f"استخدام المعالج مرتفع جدًا: {cpu_percent:.1f}% (الحد: {MAX_CPU_PERCENT}%)"
        
        if memory_percent > MAX_MEMORY_PERCENT:
            return False, f"استخدام الذاكرة مرتفع جدًا: {memory_percent:.1f}% (الحد: {MAX_MEMORY_PERCENT}%)"
            
        return True, f"استخدام الموارد ضمن الحدود المسموحة (CPU: {cpu_percent:.1f}%, RAM: {memory_percent:.1f}%)"
        
    except Exception as e:
        logger.error(f"خطأ في فحص موارد النظام: {e}")
        return False, f"خطأ في فحص الموارد: {str(e)}"


def load_custom_bot_adapter():
    """
    محاولة تحميل custom_bot_adapter إذا كان متاحًا
    """
    try:
        import custom_bot_adapter
        logger.info("تم تحميل custom_bot_adapter بنجاح")
        return custom_bot_adapter
    except ImportError:
        logger.warning("لم يتم العثور على custom_bot_adapter، سيتم استخدام الأسلوب المباشر")
        return None


def kill_existing_bot_process():
    """
    إنهاء عملية البوت الحالية إذا كانت قيد التشغيل
    """
    try:
        if os.path.exists(BOT_RUNNING_FILE):
            with open(BOT_RUNNING_FILE, "r") as f:
                pid = int(f.read().strip())
                
            try:
                process = psutil.Process(pid)
                process_name = process.name()
                
                # التأكد من أن العملية هي بالفعل عملية بوت
                if "python" in process_name.lower():
                    logger.info(f"إنهاء عملية البوت الحالية (PID: {pid})")
                    process.terminate()
                    
                    # الانتظار للإنهاء
                    try:
                        process.wait(timeout=5)
                    except psutil.TimeoutExpired:
                        logger.warning(f"انتهت مهلة إنهاء العملية، محاولة القتل القسري (PID: {pid})")
                        process.kill()
                        
                    logger.info(f"تم إنهاء عملية البوت السابقة (PID: {pid})")
                    return True
                else:
                    logger.warning(f"العملية ليست عملية بوت: {process_name}")
            except psutil.NoSuchProcess:
                logger.info(f"العملية غير موجودة (PID: {pid})")
            except Exception as e:
                logger.error(f"خطأ في إنهاء العملية: {e}")
                
            # حذف ملف PID القديم
            os.remove(BOT_RUNNING_FILE)
            
        return True
    except Exception as e:
        logger.error(f"خطأ في إنهاء عملية البوت الحالية: {e}")
        return False


def check_restart_rate_limit():
    """
    التحقق من حد معدل إعادة التشغيل لمنع دورات إعادة التشغيل المتكررة
    """
    global restart_count, last_restart_time
    
    current_time = datetime.now()
    
    # إذا كانت آخر مرة لإعادة التشغيل قبل فترة طويلة، إعادة ضبط العداد
    if last_restart_time and (current_time - last_restart_time).total_seconds() > restart_period:
        restart_count = 0
        logger.info("تم إعادة ضبط عداد إعادة التشغيل بعد انقضاء الفترة الزمنية")
    
    # التحقق من عدد مرات إعادة التشغيل
    if restart_count >= max_restart_count:
        logger.error(f"تم الوصول إلى الحد الأقصى لعدد مرات إعادة التشغيل ({max_restart_count}) خلال الفترة الزمنية")
        
        # إرسال إشعار بأولوية عالية
        send_notification(
            f"⚠️ <b>تحذير حرج</b>: تم الوصول إلى الحد الأقصى لعدد مرات إعادة التشغيل ({max_restart_count}). تم وقف محاولات إعادة التشغيل التلقائي لتجنب دورات التكرار المستمرة. يرجى التحقق من السجلات والتدخل اليدوي.",
            priority="high"
        )
        
        return False
    
    return True


def restart_bot():
    """
    إعادة تشغيل البوت باستخدام custom_bot_adapter إذا كان متاحًا،
    أو تشغيل البوت مباشرة إذا لم يكن متاحًا
    """
    global restart_count, last_restart_time, bot_process
    
    # التحقق من حد معدل إعادة التشغيل
    if not check_restart_rate_limit():
        return False
    
    # تحديث عداد إعادة التشغيل
    restart_count += 1
    last_restart_time = datetime.now()
    
    # تحديث ملف الحالة
    update_status("restarting", f"جاري إعادة تشغيل البوت (المحاولة {restart_count})")
    
    # إنهاء أي عملية بوت حالية
    kill_existing_bot_process()
    
    # إرسال إشعار
    send_notification(
        f"🔄 <b>جاري إعادة تشغيل البوت</b> (المحاولة {restart_count} من {max_restart_count})\n"
        f"🕒 الوقت: {last_restart_time.strftime('%Y-%m-%d %H:%M:%S')}"
    )
    
    logger.info(f"محاولة إعادة تشغيل البوت (المحاولة {restart_count} من {max_restart_count})")
    
    try:
        # محاولة استخدام custom_bot_adapter إذا كان متاحًا
        adapter = load_custom_bot_adapter()
        
        if adapter:
            # إعادة تشغيل باستخدام المحول
            result = adapter.start_bot_thread()
            
            if result:
                logger.info("تم إعادة تشغيل البوت بنجاح باستخدام custom_bot_adapter")
                update_status("running", "تم إعادة تشغيل البوت بنجاح")
                return True
            else:
                logger.error("فشل في إعادة تشغيل البوت باستخدام custom_bot_adapter")
        
        # الطريقة البديلة - تشغيل مباشر
        logger.info("محاولة تشغيل البوت مباشرة")
        
        # التأكد من وجود المجلدات الضرورية
        os.makedirs('logs', exist_ok=True)
        os.makedirs('data', exist_ok=True)
        os.makedirs('temp_media', exist_ok=True)
        
        # تشغيل البوت كعملية منفصلة
        bot_process = subprocess.Popen(
            [sys.executable, "bot.py"],
            stderr=subprocess.PIPE,
            stdout=subprocess.PIPE
        )
        
        # تسجيل رقم العملية
        with open(BOT_RUNNING_FILE, "w") as f:
            f.write(str(bot_process.pid))
        
        logger.info(f"تم بدء تشغيل البوت بنجاح، رقم العملية: {bot_process.pid}")
        
        # تحديث ملف الحالة
        update_status("running", f"تم إعادة تشغيل البوت بنجاح (PID: {bot_process.pid})")
        
        # الانتظار لحظة للتأكد من بدء التشغيل
        time.sleep(5)
        
        # التحقق من حالة العملية
        if bot_process.poll() is None:
            logger.info("البوت يعمل بشكل صحيح")
            return True
        else:
            # قراءة رسائل الخطأ
            stderr = bot_process.stderr.read().decode('utf-8', errors='ignore')
            logger.error(f"فشل في تشغيل البوت، رمز الخروج: {bot_process.returncode}")
            logger.error(f"رسائل الخطأ: {stderr}")
            
            # تحديث ملف الحالة
            update_status("error", f"فشل في إعادة تشغيل البوت (رمز الخروج: {bot_process.returncode})")
            
            # إرسال إشعار
            send_notification(
                f"❌ <b>فشل في إعادة تشغيل البوت</b>\nرمز الخروج: {bot_process.returncode}\nرسائل الخطأ: {stderr[:500]}...",
                priority="high"
            )
            
            return False
    except Exception as e:
        logger.error(f"خطأ أثناء إعادة تشغيل البوت: {e}")
        logger.error(traceback.format_exc())
        
        # تحديث ملف الحالة
        update_status("error", f"خطأ أثناء إعادة تشغيل البوت: {str(e)}")
        
        # إرسال إشعار
        send_notification(
            f"❌ <b>خطأ أثناء إعادة تشغيل البوت</b>\n{str(e)}\n{traceback.format_exc()[:500]}...",
            priority="high"
        )
        
        return False


def monitor_heartbeat():
    """
    مراقبة نبضات قلب البوت وإعادة تشغيله إذا توقف
    """
    global stop_monitor
    
    logger.info("بدء مراقبة نبضات قلب البوت")
    
    while not stop_monitor:
        try:
            # التحقق من نبضات القلب
            heartbeat_ok, status_message = check_bot_heartbeat()
            
            if not heartbeat_ok:
                logger.warning(f"البوت متوقف: {status_message}")
                
                # إرسال إشعار
                send_notification(
                    f"⚠️ <b>تحذير</b>: البوت متوقف\n{status_message}",
                    priority="high"
                )
                
                # إعادة تشغيل البوت
                restart_bot()
            else:
                logger.debug(f"البوت يعمل: {status_message}")
            
            # الانتظار قبل التحقق مرة أخرى
            time.sleep(HEARTBEAT_CHECK_INTERVAL)
            
        except Exception as e:
            logger.error(f"خطأ في مراقبة نبضات القلب: {e}")
            logger.error(traceback.format_exc())
            time.sleep(60)  # انتظار أطول في حالة حدوث خطأ


def monitor_resources():
    """
    مراقبة موارد النظام وإعادة تشغيل البوت إذا تجاوزت الحدود
    """
    global stop_monitor
    
    logger.info("بدء مراقبة موارد النظام")
    
    # الانتظار قليلاً قبل بدء المراقبة
    time.sleep(60)
    
    while not stop_monitor:
        try:
            # التحقق من حالة نبضات القلب أولاً
            heartbeat_ok, _ = check_bot_heartbeat()
            
            if heartbeat_ok:
                # التحقق من موارد النظام
                resources_ok, status_message = check_system_resources()
                
                if not resources_ok:
                    logger.warning(f"موارد النظام تجاوزت الحد: {status_message}")
                    
                    # إرسال إشعار
                    send_notification(
                        f"⚠️ <b>تحذير</b>: موارد النظام تجاوزت الحد\n{status_message}",
                        priority="high"
                    )
                    
                    # إعادة تشغيل البوت
                    restart_bot()
                else:
                    logger.debug(f"موارد النظام ضمن الحدود: {status_message}")
            
            # الانتظار قبل التحقق مرة أخرى
            time.sleep(RESOURCE_CHECK_INTERVAL)
            
        except Exception as e:
            logger.error(f"خطأ في مراقبة موارد النظام: {e}")
            logger.error(traceback.format_exc())
            time.sleep(60)  # انتظار أطول في حالة حدوث خطأ


def cleanup():
    """
    تنظيف الموارد عند الخروج
    """
    global stop_monitor, bot_process
    
    logger.info("تنظيف الموارد قبل الخروج")
    
    # إيقاف خيوط المراقبة
    stop_monitor = True
    
    # إنهاء عملية البوت إذا كانت موجودة
    if bot_process and bot_process.poll() is None:
        try:
            logger.info("إنهاء عملية البوت")
            bot_process.terminate()
            time.sleep(2)
            if bot_process.poll() is None:
                bot_process.kill()
        except:
            pass
    
    # تحرير القفل
    release_lock()
    
    # تحديث الحالة
    update_status("stopped", "تم إيقاف نظام المراقبة")


def signal_handler(sig, frame):
    """
    معالجة الإشارات
    """
    logger.info(f"تم استلام إشارة: {sig}")
    cleanup()
    sys.exit(0)


def main():
    """
    النقطة الرئيسية للتشغيل
    """
    global resource_monitor_thread, heartbeat_monitor_thread
    
    logger.info("بدء تشغيل نظام إعادة التشغيل التلقائي")
    
    # التحقق من القفل
    if not acquire_lock():
        logger.error("يوجد بالفعل نسخة من النظام قيد التشغيل. الخروج.")
        return 1
    
    # إعداد معالجات الإشارات
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    # تسجيل وظيفة التنظيف
    atexit.register(cleanup)
    
    try:
        # تحديث الحالة
        update_status("starting", "جاري بدء تشغيل نظام المراقبة")
        
        # بدء تشغيل البوت إذا لم يكن يعمل
        heartbeat_ok, _ = check_bot_heartbeat()
        if not heartbeat_ok:
            logger.info("البوت غير نشط، جاري تشغيله")
            restart_bot()
        else:
            logger.info("البوت يعمل بالفعل")
        
        # بدء خيط مراقبة نبضات القلب
        heartbeat_monitor_thread = threading.Thread(target=monitor_heartbeat)
        heartbeat_monitor_thread.daemon = True
        heartbeat_monitor_thread.start()
        
        # بدء خيط مراقبة الموارد
        resource_monitor_thread = threading.Thread(target=monitor_resources)
        resource_monitor_thread.daemon = True
        resource_monitor_thread.start()
        
        # تحديث الحالة
        update_status("running", "نظام المراقبة يعمل")
        
        # إرسال إشعار
        send_notification("✅ <b>تم بدء تشغيل نظام إعادة التشغيل التلقائي</b>")
        
        logger.info("تم بدء تشغيل نظام إعادة التشغيل التلقائي بنجاح")
        
        # استمرار تشغيل البرنامج في حلقة غير منتهية
        while True:
            # التحقق من حالة خيوط المراقبة
            if not heartbeat_monitor_thread.is_alive():
                logger.error("توقف خيط مراقبة نبضات القلب. إعادة تشغيله.")
                heartbeat_monitor_thread = threading.Thread(target=monitor_heartbeat)
                heartbeat_monitor_thread.daemon = True
                heartbeat_monitor_thread.start()
            
            if not resource_monitor_thread.is_alive():
                logger.error("توقف خيط مراقبة الموارد. إعادة تشغيله.")
                resource_monitor_thread = threading.Thread(target=monitor_resources)
                resource_monitor_thread.daemon = True
                resource_monitor_thread.start()
            
            # طباعة معلومات حالة البوت كل دقيقة
            bot_running, status_message = check_bot_heartbeat()
            if bot_running:
                logger.info(f"البوت يعمل: {status_message}")
            else:
                logger.warning(f"البوت متوقف: {status_message}")
            
            # انتظار
            time.sleep(60)
            
    except KeyboardInterrupt:
        logger.info("تم إيقاف البرنامج بواسطة المستخدم")
        cleanup()
        return 0
    except Exception as e:
        logger.error(f"خطأ عام: {e}")
        logger.error(traceback.format_exc())
        cleanup()
        
        # إرسال إشعار
        send_notification(
            f"❌ <b>خطأ في نظام إعادة التشغيل التلقائي</b>\n{str(e)}\n{traceback.format_exc()[:500]}...",
            priority="high"
        )
        
        return 1
    
    return 0


if __name__ == "__main__":
    sys.exit(main())