#!/usr/bin/env python
"""
نظام المراقبة الخارجي - External Monitoring System

هذا السكريبت مصمم للتشغيل على خادم خارجي للتحقق من حالة بوت التيليجرام
واتخاذ الإجراءات اللازمة للحفاظ على استمرارية عمله.

يمكن تشغيل هذا السكريبت كمهمة cron (مثلاً كل 5 دقائق) على خادم خارجي
للتأكد من أن البوت لا يزال يعمل.
"""

import argparse
import json
import logging
import os
import requests
import smtplib
import time
from datetime import datetime
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

# --- الإعدادات الأساسية ---
# يمكن تغييرها مباشرة هنا أو تمريرها كوسائط عبر الأوامر

# عنوان URL للبوت الذي سيتم مراقبته (صفحة صحة النظام)
URL_TO_MONITOR = "https://clienttrackerpro.your-username.repl.co/health"

# عنوان URL لإعادة تنشيط البوت (صفحة ping)
PING_URL = "https://clienttrackerpro.your-username.repl.co/ping"

# عدد محاولات الاتصال قبل اعتبار البوت غير متاح
MAX_RETRIES = 3

# الفاصل الزمني بين المحاولات (بالثواني)
RETRY_INTERVAL = 30

# --- إعدادات البريد الإلكتروني للإشعارات ---
EMAIL_ENABLED = False  # تعيين القيمة إلى True لتفعيل الإشعارات عبر البريد
EMAIL_FROM = "your-email@gmail.com"  # عنوان البريد المرسل
EMAIL_TO = "admin-email@example.com"  # عنوان البريد المستلم
EMAIL_SUBJECT = "تنبيه: البوت غير متاح!"  # موضوع البريد
EMAIL_SMTP_SERVER = "smtp.gmail.com"  # خادم SMTP
EMAIL_SMTP_PORT = 587  # منفذ SMTP
EMAIL_USERNAME = "your-email@gmail.com"  # اسم المستخدم
EMAIL_PASSWORD = "your-app-password"  # كلمة المرور (يفضل استخدام كلمة مرور التطبيق)

# --- إعداد التسجيل ---
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO,
    filename='external_monitor.log'
)
logger = logging.getLogger("ExternalMonitor")

# إضافة معالج لعرض السجلات في وحدة التحكم أيضاً
console_handler = logging.StreamHandler()
console_handler.setLevel(logging.INFO)
console_formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
console_handler.setFormatter(console_formatter)
logger.addHandler(console_handler)

def check_bot_status(url):
    """التحقق من حالة البوت باستخدام URL الصحة"""
    for attempt in range(1, MAX_RETRIES + 1):
        try:
            logger.info(f"محاولة {attempt}/{MAX_RETRIES} للاتصال بـ {url}")
            response = requests.get(url, timeout=10)
            
            if response.status_code == 200:
                logger.info(f"✅ البوت متاح ويعمل بشكل جيد! الاستجابة: {response.text}")
                return True
            else:
                logger.warning(f"⚠️ البوت متاح ولكن يعيد رمز حالة غير متوقع: {response.status_code}")
                
        except requests.exceptions.RequestException as e:
            logger.error(f"❌ فشل الاتصال بالبوت (محاولة {attempt}/{MAX_RETRIES}): {e}")
            
        # إذا لم تكن هذه المحاولة الأخيرة، انتظر قبل المحاولة التالية
        if attempt < MAX_RETRIES:
            logger.info(f"انتظار {RETRY_INTERVAL} ثواني قبل المحاولة التالية...")
            time.sleep(RETRY_INTERVAL)
    
    # إذا وصلنا إلى هنا، فهذا يعني فشل جميع المحاولات
    logger.error(f"❌❌❌ البوت غير متاح بعد {MAX_RETRIES} محاولات!")
    return False

def ping_bot(url):
    """إرسال طلب ping إلى البوت لمحاولة إعادة تنشيطه"""
    try:
        logger.info(f"محاولة إرسال ping إلى البوت على {url}...")
        response = requests.get(url, timeout=15)
        
        if response.status_code == 200:
            logger.info(f"✅ تم إرسال ping بنجاح! الاستجابة: {response.text}")
            return True
        else:
            logger.warning(f"⚠️ تم استلام رمز حالة غير متوقع من ping: {response.status_code}")
            return False
            
    except requests.exceptions.RequestException as e:
        logger.error(f"❌ فشل إرسال ping إلى البوت: {e}")
        return False

def send_notification_email(bot_status):
    """إرسال إشعار بالبريد الإلكتروني عن حالة البوت"""
    if not EMAIL_ENABLED:
        logger.info("إشعارات البريد الإلكتروني غير مفعلة. تخطي الإرسال.")
        return
    
    try:
        # إنشاء رسالة البريد
        message = MIMEMultipart()
        message["From"] = EMAIL_FROM
        message["To"] = EMAIL_TO
        message["Subject"] = EMAIL_SUBJECT
        
        # إعداد محتوى البريد
        body = f"""
        <html>
        <body>
            <h2>تنبيه: حالة بوت التيليجرام</h2>
            <p><strong>الوقت:</strong> {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</p>
            <p><strong>الحالة:</strong> {'✅ متاح' if bot_status else '❌ غير متاح'}</p>
            <p><strong>URL المراقبة:</strong> {URL_TO_MONITOR}</p>
            <hr>
            <p>تم إرسال هذا الإشعار تلقائياً بواسطة نظام المراقبة الخارجي.</p>
        </body>
        </html>
        """
        
        message.attach(MIMEText(body, "html"))
        
        # الاتصال بخادم SMTP وإرسال البريد
        with smtplib.SMTP(EMAIL_SMTP_SERVER, EMAIL_SMTP_PORT) as server:
            server.starttls()
            server.login(EMAIL_USERNAME, EMAIL_PASSWORD)
            server.send_message(message)
            
        logger.info("✅ تم إرسال إشعار البريد الإلكتروني بنجاح!")
        
    except Exception as e:
        logger.error(f"❌ فشل إرسال إشعار البريد الإلكتروني: {e}")

def update_status_log(status):
    """تحديث سجل حالة المراقبة"""
    try:
        status_data = {
            "timestamp": datetime.now().isoformat(),
            "status": "online" if status else "offline",
            "url_monitored": URL_TO_MONITOR,
            "max_retries": MAX_RETRIES,
            "retry_interval": RETRY_INTERVAL
        }
        
        with open("external_monitor_status.json", "w", encoding="utf-8") as f:
            json.dump(status_data, f, ensure_ascii=False, indent=2)
            
        logger.info("✅ تم تحديث سجل حالة المراقبة بنجاح!")
        
    except Exception as e:
        logger.error(f"❌ فشل تحديث سجل حالة المراقبة: {e}")

def main():
    """الوظيفة الرئيسية للسكريبت"""
    parser = argparse.ArgumentParser(description="نظام المراقبة الخارجي لبوت التيليجرام")
    parser.add_argument("--url", help="عنوان URL للمراقبة", default=URL_TO_MONITOR)
    parser.add_argument("--ping", help="عنوان URL للـ ping", default=PING_URL)
    parser.add_argument("--retries", type=int, help="عدد محاولات الاتصال", default=MAX_RETRIES)
    parser.add_argument("--interval", type=int, help="الفاصل الزمني بين المحاولات (بالثواني)", default=RETRY_INTERVAL)
    parser.add_argument("--email", action="store_true", help="تفعيل إشعارات البريد الإلكتروني")
    
    args = parser.parse_args()
    
    # تحديث المتغيرات العالمية إذا تم تمرير وسائط مختلفة
    global URL_TO_MONITOR, PING_URL, MAX_RETRIES, RETRY_INTERVAL, EMAIL_ENABLED
    URL_TO_MONITOR = args.url
    PING_URL = args.ping
    MAX_RETRIES = args.retries
    RETRY_INTERVAL = args.interval
    EMAIL_ENABLED = args.email or EMAIL_ENABLED
    
    logger.info("🚀 بدء تشغيل نظام المراقبة الخارجي...")
    logger.info(f"URL للمراقبة: {URL_TO_MONITOR}")
    logger.info(f"URL للـ ping: {PING_URL}")
    logger.info(f"عدد المحاولات: {MAX_RETRIES}")
    logger.info(f"الفاصل الزمني بين المحاولات: {RETRY_INTERVAL} ثواني")
    logger.info(f"إشعارات البريد الإلكتروني: {'مفعلة' if EMAIL_ENABLED else 'غير مفعلة'}")
    
    # التحقق من حالة البوت
    bot_status = check_bot_status(URL_TO_MONITOR)
    
    # إذا كان البوت غير متاح، محاولة إعادة تنشيطه
    if not bot_status:
        logger.info("⚠️ البوت غير متاح. محاولة إرسال ping لإعادة تنشيطه...")
        ping_success = ping_bot(PING_URL)
        
        if ping_success:
            logger.info("🔄 انتظار 30 ثانية للتحقق من حالة البوت بعد ping...")
            time.sleep(30)
            
            # التحقق من حالة البوت مرة أخرى بعد ping
            bot_status = check_bot_status(URL_TO_MONITOR)
            
            if bot_status:
                logger.info("✅✅ تم إعادة تنشيط البوت بنجاح!")
            else:
                logger.error("❌❌ فشل في إعادة تنشيط البوت حتى بعد ping!")
        else:
            logger.error("❌❌ فشل في إرسال ping إلى البوت!")
    
    # تحديث سجل الحالة
    update_status_log(bot_status)
    
    # إرسال إشعار بالبريد الإلكتروني إذا كان البوت غير متاح
    if not bot_status:
        send_notification_email(bot_status)
    
    logger.info("✓ اكتملت عملية المراقبة!")

if __name__ == "__main__":
    main()