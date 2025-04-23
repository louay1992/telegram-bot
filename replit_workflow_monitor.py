#!/usr/bin/env python3
"""
مراقب سير العمل لـ Replit - يعمل مع نظام Cron Jobs
يتحقق من استجابة نقطة النهاية /api/ping ويعيد تشغيل workflows إذا كانت هناك مشكلة
"""

import os
import sys
import time
import logging
import requests
import subprocess
import json
from datetime import datetime, timedelta

# إعداد التسجيل
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler("replit_monitor.log")
    ]
)
logger = logging.getLogger("replit_monitor")

# القيم الثابتة
API_ENDPOINTS = [
    "http://localhost:5000/api/ping",  # المنفذ الرئيسي (gunicorn)
    "http://localhost:8080/api/ping"   # المنفذ الثانوي (Flask المضمّن)
]
MAX_RETRY_ATTEMPTS = 3
RETRY_DELAY = 5  # ثوانٍ
HEARTBEAT_FILE = "bot_heartbeat.txt"  # ملف نبضات القلب
MAX_HEARTBEAT_AGE = 180  # الحد الأقصى لعمر نبضة القلب بالثواني (3 دقائق)
ALERT_STATUS_FILE = "monitor_alert_status.json"  # ملف حالة التنبيهات

# إعدادات Telegram للإشعارات
TELEGRAM_BOT_TOKEN = os.environ.get("ADMIN_BOT_TOKEN", os.environ.get("TELEGRAM_BOT_TOKEN"))
ADMIN_CHAT_ID = os.environ.get("ADMIN_CHAT_ID")

def check_api_endpoint():
    """التحقق من استجابة نقاط النهاية /api/ping"""
    for endpoint in API_ENDPOINTS:
        logger.info(f"🔍 محاولة الاتصال بـ {endpoint}")
        
        for attempt in range(1, MAX_RETRY_ATTEMPTS + 1):
            try:
                logger.info(f"  محاولة {attempt}/{MAX_RETRY_ATTEMPTS}")
                response = requests.get(endpoint, timeout=10)
                
                if response.status_code == 200:
                    logger.info(f"✅ نقطة النهاية {endpoint} تستجيب: {response.status_code}, {response.text[:100]}")
                    return True
                else:
                    logger.warning(f"⚠️ نقطة النهاية تستجيب بكود خطأ: {response.status_code}")
            except Exception as e:
                logger.warning(f"❌ خطأ في الاتصال بنقطة النهاية {endpoint}: {e}")
            
            if attempt < MAX_RETRY_ATTEMPTS:
                logger.info(f"⏱️ انتظار {RETRY_DELAY} ثوانٍ قبل المحاولة التالية...")
                time.sleep(RETRY_DELAY)
    
    # إذا وصلنا إلى هنا، فهذا يعني أن جميع النقاط النهائية غير مستجيبة
    logger.error("❌ جميع نقاط النهاية غير مستجيبة!")
    return False

def restart_workflows():
    """إعادة تشغيل سير العمل في Replit"""
    try:
        # إعادة تشغيل workflow "Start application"
        logger.info("🔄 محاولة إعادة تشغيل سير العمل 'Start application'...")
        subprocess.run("workflow.run \"Start application\"", shell=True, check=True)
        logger.info("✅ تم إرسال طلب إعادة تشغيل 'Start application'")
        
        # انتظار لإعطاء وقت لبدء التشغيل
        time.sleep(10)
        
        # إعادة تشغيل workflow "telegram_bot"
        logger.info("🔄 محاولة إعادة تشغيل سير العمل 'telegram_bot'...")
        subprocess.run("workflow.run telegram_bot", shell=True, check=True)
        logger.info("✅ تم إرسال طلب إعادة تشغيل 'telegram_bot'")
        
        return True
    except Exception as e:
        logger.error(f"❌ خطأ أثناء إعادة تشغيل سير العمل: {e}")
        return False

def notify_admin(message, alert_type="warning"):
    """
    إرسال إشعارات للمشرف عبر Telegram
    
    Args:
        message (str): نص الرسالة
        alert_type (str): نوع التنبيه (error/warning/info/success)
    """
    if not TELEGRAM_BOT_TOKEN or not ADMIN_CHAT_ID:
        logger.warning("⚠️ لم يتم تكوين رمز البوت أو معرف الدردشة للإشعارات.")
        return
    
    # إضافة رموز تعبيرية حسب نوع التنبيه
    icon = {
        "error": "🚨",
        "warning": "⚠️",
        "info": "ℹ️",
        "success": "✅"
    }.get(alert_type, "ℹ️")
    
    # تكوين الرسالة النهائية
    formatted_message = f"{icon} *إشعار من مراقب البوت* {icon}\n\n{message}\n\n⏰ {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
    
    try:
        url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
        data = {
            "chat_id": ADMIN_CHAT_ID,
            "text": formatted_message,
            "parse_mode": "Markdown"
        }
        response = requests.post(url, data=data, timeout=10)
        
        if response.status_code == 200:
            logger.info(f"✅ تم إرسال الإشعار بنجاح إلى المشرف (كود {response.status_code})")
            return True
        else:
            logger.warning(f"⚠️ فشل في إرسال الإشعار (كود {response.status_code}): {response.text}")
            return False
    except Exception as e:
        logger.error(f"❌ خطأ أثناء إرسال الإشعار: {e}")
        return False


def check_heartbeat():
    """
    التحقق من نبضات القلب للبوت
    يتأكد من وجود ملف نبضات القلب ويقرأ تاريخ آخر نبضة
    إذا كانت آخر نبضة قديمة جدًا، يعتبر البوت متوقفًا
    
    Returns:
        tuple: (is_healthy, last_heartbeat, age_seconds)
    """
    if not os.path.exists(HEARTBEAT_FILE):
        logger.warning(f"⚠️ ملف نبضات القلب '{HEARTBEAT_FILE}' غير موجود")
        return False, None, None
    
    try:
        with open(HEARTBEAT_FILE, "r") as f:
            content = f.read().strip()
        
        # محاولة تحليل المحتوى بعدة طرق - يمكن أن يكون بتنسيق ISO أو timestamp
        try:
            # محاولة التحليل كـ ISO format
            last_time = datetime.fromisoformat(content)
            last_heartbeat = content
        except ValueError:
            try:
                # محاولة التحليل كـ timestamp
                timestamp = float(content)
                last_time = datetime.fromtimestamp(timestamp)
                last_heartbeat = last_time.isoformat()
            except ValueError:
                logger.error(f"❌ تنسيق غير معروف في ملف نبضات القلب: {content}")
                return False, content, None
        
        time_diff = datetime.now() - last_time
        age_seconds = time_diff.total_seconds()
        
        is_healthy = age_seconds < MAX_HEARTBEAT_AGE
        
        if not is_healthy:
            logger.warning(f"⚠️ نبضات القلب قديمة جدًا! آخر نبضة: {last_heartbeat}, العمر: {age_seconds:.1f} ثانية")
        else:
            logger.info(f"✅ نبضات القلب طبيعية. آخر نبضة: {last_heartbeat}, العمر: {age_seconds:.1f} ثانية")
            
        return is_healthy, last_heartbeat, age_seconds
    except Exception as e:
        logger.error(f"❌ خطأ أثناء قراءة ملف نبضات القلب: {e}")
        return False, None, None


def manage_alert_status(alert_key, is_active):
    """
    إدارة حالة التنبيهات لتجنب إرسال إشعارات متكررة
    
    Args:
        alert_key (str): مفتاح التنبيه
        is_active (bool): ما إذا كان التنبيه نشطًا
    
    Returns:
        bool: ما إذا كان يجب إرسال إشعار
    """
    status = {}
    
    # قراءة حالة التنبيهات الحالية
    if os.path.exists(ALERT_STATUS_FILE):
        try:
            with open(ALERT_STATUS_FILE, 'r') as f:
                status = json.load(f)
        except:
            status = {}
    
    # فحص ما إذا كان يجب إرسال إشعار
    should_notify = False
    
    if is_active:
        # إذا كان التنبيه نشطًا والحالة السابقة غير نشطة، أرسل إشعارًا
        if alert_key not in status or status.get(alert_key) == False:
            should_notify = True
    else:
        # إذا كان التنبيه غير نشط والحالة السابقة نشطة، أرسل إشعار استعادة
        if alert_key in status and status.get(alert_key) == True:
            should_notify = True
    
    # تحديث الحالة
    status[alert_key] = is_active
    
    # حفظ الحالة
    try:
        with open(ALERT_STATUS_FILE, 'w') as f:
            json.dump(status, f)
    except Exception as e:
        logger.error(f"❌ خطأ أثناء حفظ حالة التنبيهات: {e}")
    
    return should_notify


def ping_uptimerobot():
    """
    إرسال ping إلى UptimeRobot باستخدام API الخاص بك
    يمكن للمستخدم إعداد العنوان الخاص به للتكامل مع UptimeRobot
    """
    try:
        uptimerobot_url = os.environ.get("UPTIMEROBOT_URL")
        if uptimerobot_url:
            logger.info(f"🔔 إرسال ping إلى UptimeRobot: {uptimerobot_url}")
            requests.get(uptimerobot_url, timeout=10)
            logger.info("✅ تم إرسال ping إلى UptimeRobot بنجاح")
    except Exception as e:
        logger.warning(f"⚠️ خطأ أثناء إرسال ping إلى UptimeRobot: {e}")

def main():
    """الوظيفة الرئيسية"""
    logger.info(f"🚀 بدء فحص مراقب Replit - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    # مراقبة أخطاء متعددة
    errors_detected = []
    restart_needed = False
    
    # 1. التحقق من نبضات القلب
    heartbeat_ok, last_heartbeat, age_seconds = check_heartbeat()
    if not heartbeat_ok:
        age_display = "غير معروف"
        if age_seconds is not None:
            age_display = f"{int(age_seconds)}"
            
        error_msg = f"❌ مشكلة في نبضات القلب: آخر نبضة منذ {age_display} ثانية"
        errors_detected.append(error_msg)
        restart_needed = True
        
        # إرسال إشعار إذا تم تغيير الحالة (من صحيح إلى خطأ)
        if manage_alert_status("heartbeat", True):
            notify_admin(
                f"⏰ *مشكلة في نبضات القلب*\n\nلم يتم اكتشاف نبضات قلب حديثة للبوت!\nآخر نبضة: {last_heartbeat or 'غير معروفة'}\nالعمر: {age_display} ثانية.",
                "error"
            )
    else:
        # إرسال إشعار استعادة إذا كانت الحالة سابقًا خطأ
        if manage_alert_status("heartbeat", False):
            age_display = "غير معروف"
            if age_seconds is not None:
                age_display = f"{int(age_seconds)}"
                
            notify_admin(
                f"✅ *استعادة نبضات القلب*\n\nتم استئناف نبضات قلب البوت بنجاح.\nآخر نبضة: {last_heartbeat}\nالعمر: {age_display} ثانية.",
                "success"
            )
    
    # 2. التحقق من استجابة نقاط النهاية
    endpoints_ok = check_api_endpoint()
    if not endpoints_ok:
        error_msg = "❌ جميع نقاط النهاية لا تستجيب!"
        errors_detected.append(error_msg)
        restart_needed = True
        
        # إرسال إشعار إذا تم تغيير الحالة (من صحيح إلى خطأ)
        if manage_alert_status("endpoints", True):
            notify_admin(
                "🔌 *خطأ في نقاط النهاية*\n\nجميع نقاط النهاية (/api/ping) لا تستجيب! سيتم محاولة إعادة تشغيل سير العمل.",
                "error"
            )
    else:
        # إرسال إشعار استعادة إذا كانت الحالة سابقًا خطأ
        if manage_alert_status("endpoints", False):
            notify_admin(
                "✅ *استعادة نقاط النهاية*\n\nتم استئناف استجابة نقاط النهاية (/api/ping) بنجاح.",
                "success"
            )
    
    # إعادة تشغيل workflows إذا كان ضروريًا
    if restart_needed:
        combined_errors = "\n".join(errors_detected)
        logger.warning(f"⚠️ تم اكتشاف مشاكل تتطلب إعادة التشغيل:\n{combined_errors}")
        logger.warning("🔄 محاولة إعادة تشغيل سير العمل...")
        
        if restart_workflows():
            success_msg = "✅ تم إرسال طلبات إعادة التشغيل بنجاح"
            logger.info(success_msg)
            notify_admin(f"🔄 *إعادة تشغيل تلقائية*\n\n{combined_errors}\n\n{success_msg}", "info")
        else:
            error_msg = "❌ فشل في إعادة تشغيل سير العمل"
            logger.error(error_msg)
            notify_admin(f"⚠️ *فشل إعادة التشغيل*\n\n{combined_errors}\n\n{error_msg}", "error")
    else:
        logger.info("✅ جميع فحوصات المراقبة ناجحة")
    
    # محاولة إرسال ping إلى UptimeRobot
    ping_uptimerobot()
    
    logger.info(f"🏁 انتهاء فحص مراقب Replit - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

if __name__ == "__main__":
    main()