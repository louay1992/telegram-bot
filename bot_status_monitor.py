"""
نظام مراقبة حالة البوت وإرسال إشعارات الطوارئ

هذا الملف يحتوي على وظائف لمراقبة حالة البوت وإرسال إشعارات واتساب
عند اكتشاف مشاكل أو توقف البوت.
"""

import os
import logging
import time
from datetime import datetime, timedelta
import requests
import json
import threading

# استيراد خدمة الواتساب
from ultramsg_service import send_whatsapp_message

# إعداد التسجيل
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# رقم هاتف المسؤول الرئيسي
ADMIN_PHONE_NUMBER = "+963933000227"

# فترة السماح قبل اعتبار البوت متوقفاً (بالثواني)
BOT_TIMEOUT_SECONDS = 90  # 1.5 دقيقة (تقليل من 5 دقائق لاستجابة أسرع)

# ملف تسجيل آخر نبضة قلب
HEARTBEAT_FILE = "bot_heartbeat.txt"

# ملف تسجيل آخر إشعار تم إرساله
LAST_NOTIFICATION_FILE = "last_whatsapp_notification.json"

# الحد الأقصى لعدد الإشعارات المرسلة في اليوم
MAX_NOTIFICATIONS_PER_DAY = 10

# متغير عام لتتبع حالة البوت السابقة
previous_bot_status = True

def read_heartbeat_file():
    """قراءة ملف نبضات القلب وإرجاع التاريخ"""
    try:
        if os.path.exists(HEARTBEAT_FILE):
            with open(HEARTBEAT_FILE, "r") as f:
                last_heartbeat_str = f.read().strip()
                # تحقق من التنسيق: إذا كان رقمًا عشريًا، فهو على الأرجح طابع زمني unix
                try:
                    # محاولة تحويل النص إلى رقم عشري (unix timestamp)
                    last_heartbeat_timestamp = float(last_heartbeat_str)
                    # تحويل unix timestamp إلى كائن datetime
                    return datetime.fromtimestamp(last_heartbeat_timestamp)
                except ValueError:
                    # إذا لم يكن الطابع الزمني بتنسيق unix، نحاول تحليله كتنسيق isoformat
                    return datetime.fromisoformat(last_heartbeat_str)
        return None
    except Exception as e:
        logger.error(f"خطأ في قراءة ملف نبضات القلب: {e}")
        return None

def is_bot_running():
    """التحقق مما إذا كان البوت يعمل بناءً على آخر نبضة قلب"""
    last_heartbeat = read_heartbeat_file()
    if not last_heartbeat:
        return False
    
    time_diff = datetime.now() - last_heartbeat
    return time_diff.total_seconds() < BOT_TIMEOUT_SECONDS

def read_notification_history():
    """قراءة سجل الإشعارات المرسلة"""
    try:
        if os.path.exists(LAST_NOTIFICATION_FILE):
            with open(LAST_NOTIFICATION_FILE, "r") as f:
                return json.load(f)
        return {"last_notification": None, "count_today": 0, "date": None}
    except Exception as e:
        logger.error(f"خطأ في قراءة سجل الإشعارات: {e}")
        return {"last_notification": None, "count_today": 0, "date": None}

def save_notification_history(data):
    """حفظ سجل الإشعارات المرسلة"""
    try:
        with open(LAST_NOTIFICATION_FILE, "w") as f:
            json.dump(data, f)
    except Exception as e:
        logger.error(f"خطأ في حفظ سجل الإشعارات: {e}")

def can_send_notification():
    """التحقق مما إذا كان يمكن إرسال إشعار جديد"""
    notification_history = read_notification_history()
    
    # إذا لم يكن هناك تاريخ مسجل، يمكن إرسال إشعار
    if not notification_history["date"]:
        return True
    
    # التحقق من التاريخ
    today = datetime.now().strftime("%Y-%m-%d")
    
    # إذا كان التاريخ مختلفاً (يوم جديد)، يعاد تعيين العداد
    if notification_history["date"] != today:
        notification_history["count_today"] = 0
        notification_history["date"] = today
        save_notification_history(notification_history)
        return True
    
    # التحقق من عدد الإشعارات المرسلة اليوم
    if notification_history["count_today"] < MAX_NOTIFICATIONS_PER_DAY:
        return True
    
    return False

def record_notification_sent():
    """تسجيل إرسال إشعار جديد"""
    notification_history = read_notification_history()
    today = datetime.now().strftime("%Y-%m-%d")
    
    # إذا كان التاريخ مختلفاً (يوم جديد)، يعاد تعيين العداد
    if notification_history["date"] != today:
        notification_history["count_today"] = 1
    else:
        notification_history["count_today"] += 1
    
    notification_history["date"] = today
    notification_history["last_notification"] = datetime.now().isoformat()
    
    save_notification_history(notification_history)

def send_bot_status_notification(is_down=True):
    """إرسال إشعار حالة البوت عبر الواتساب"""
    if not can_send_notification():
        logger.warning("تم تجاوز الحد الأقصى لعدد الإشعارات اليومية")
        return False
    
    try:
        if is_down:
            message = (
                "⚠️ *تنبيه هام* ⚠️\n\n"
                "توقف بوت إشعارات الشحن عن الاستجابة!\n\n"
                f"آخر نشاط: {read_heartbeat_file() or 'غير معروف'}\n"
                f"الوقت الحالي: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n"
                "يرجى التحقق من حالة البوت في أقرب وقت ممكن."
            )
        else:
            message = (
                "✅ *تم استعادة الاتصال* ✅\n\n"
                "عاد بوت إشعارات الشحن للعمل بشكل طبيعي.\n\n"
                f"الوقت الحالي: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
            )
        
        success = send_whatsapp_message(ADMIN_PHONE_NUMBER, message)
        
        if success:
            record_notification_sent()
            logger.info(f"تم إرسال إشعار حالة البوت بنجاح: {'متوقف' if is_down else 'يعمل'}")
            return True
        else:
            logger.error("فشل إرسال إشعار حالة البوت عبر الواتساب")
            return False
    
    except Exception as e:
        logger.error(f"خطأ في إرسال إشعار حالة البوت: {e}")
        return False

def check_bot_status_and_notify():
    """فحص حالة البوت وإرسال إشعار إذا كان متوقفاً أو عاد للعمل بعد توقف"""
    # متغير لحفظ حالة البوت السابقة
    global previous_bot_status
    
    # التحقق من حالة البوت الحالية
    bot_running = is_bot_running()
    
    # نستخدم المتغير العام الذي قمنا بتهيئته مسبقاً
    
    if not bot_running:
        # البوت متوقف الآن
        logger.warning("البوت متوقف عن الاستجابة، جاري إرسال إشعار")
        send_bot_status_notification(is_down=True)
        previous_bot_status = False
    elif not previous_bot_status and bot_running:
        # البوت كان متوقفاً وعاد للعمل
        logger.info("البوت عاد للعمل بعد توقف، جاري إرسال إشعار استعادة الاتصال")
        send_bot_status_notification(is_down=False)
        previous_bot_status = True
    else:
        # البوت يعمل بشكل طبيعي ولم يكن متوقفاً سابقاً
        logger.info("البوت يعمل بشكل طبيعي")
        previous_bot_status = True

def start_status_monitor(check_interval=300):
    """بدء مراقبة حالة البوت على فترات منتظمة"""
    def monitor_loop():
        while True:
            try:
                check_bot_status_and_notify()
                time.sleep(check_interval)
            except Exception as e:
                logger.error(f"خطأ في دورة المراقبة: {e}")
                time.sleep(60)  # انتظار دقيقة واحدة قبل المحاولة مرة أخرى
    
    monitor_thread = threading.Thread(target=monitor_loop, daemon=True)
    monitor_thread.start()
    logger.info(f"تم بدء نظام مراقبة حالة البوت (فترة الفحص: {check_interval} ثانية)")
    return monitor_thread

if __name__ == "__main__":
    # اختبار وظائف المراقبة
    print(f"هل البوت يعمل؟ {is_bot_running()}")
    check_bot_status_and_notify()