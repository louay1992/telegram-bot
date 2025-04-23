#!/usr/bin/env python
"""
نظام موحد لتشغيل بوت تيليجرام داخل Replit
- يعتمد على Flask للإبقاء على الجلسة نشطة
- تشغيل البوت داخل Thread منفصل
- مراقبة نبضات القلب
- جاهز للتكامل مع UptimeRobot

يجمع هذا الملف كل وظائف main.py و bot_launcher وأنظمة المراقبة في ملف واحد متكامل.
يستخدم كنقطة دخول وحيدة للنشر على Replit، ويعمل بكفاءة عالية.
"""

import os
import sys
import threading
import time
import logging
import json
import psutil
from datetime import datetime, timedelta
from flask import Flask, jsonify, render_template, send_from_directory, request, make_response

# إعداد السجلات
os.makedirs("logs", exist_ok=True)
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler("logs/launcher.log")
    ]
)
logger = logging.getLogger("naturecare_launcher")

# متغيرات عامة
BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN", "7406580104:AAGG2JQeeNfsmcGVMCm7hxitIK-qm2yekVg")
HEARTBEAT_FILE = "bot_heartbeat.txt"
BOT_STARTED = False
START_TIME = datetime.now()
NOTIFICATIONS_COUNT = 0  # سيتم تحديثه دوريًا
visit_count = 0  # عداد الزيارات للصفحة الرئيسية

# إعداد Flask
app = Flask(__name__)
app.secret_key = os.environ.get("FLASK_SECRET_KEY", "naturecare_secret_key")

# تحديث نبضات القلب
def update_heartbeat():
    try:
        with open(HEARTBEAT_FILE, 'w') as f:
            f.write(str(time.time()))
        logger.info("✅ تم تحديث ملف نبضات القلب")
    except Exception as e:
        logger.error(f"❌ خطأ في تحديث نبضات القلب: {e}")

# فحص حالة البوت من خلال ملف نبضات القلب
def is_bot_running():
    try:
        if not os.path.exists(HEARTBEAT_FILE):
            logger.warning("⚠️ ملف نبضات القلب غير موجود")
            return False
            
        with open(HEARTBEAT_FILE, "r") as f:
            timestamp = float(f.read().strip())
            
        last_heartbeat = datetime.fromtimestamp(timestamp)
        diff = (datetime.now() - last_heartbeat).total_seconds()
        
        # اعتبر البوت نشطًا إذا كان آخر نبضة قلب خلال 3 دقائق
        return diff < 180  # أقل من 3 دقائق
            
    except Exception as e:
        logger.error(f"❌ خطأ في التحقق من حالة البوت: {e}")
        import traceback
        logger.error(traceback.format_exc())
        return False

# تشغيل البوت باستخدام custom_bot_adapter
def start_bot():
    global BOT_STARTED
    
    try:
        import custom_bot_adapter
        logger.info("🚀 بدء تشغيل البوت في Thread مستقل...")
        custom_bot_adapter.start_bot_thread()
        BOT_STARTED = True
        
        # انتظار للتأكد من بدء التشغيل
        time.sleep(2)
        
        if is_bot_running():
            logger.info("✅ تم بدء تشغيل البوت بنجاح!")
        else:
            logger.warning("⚠️ تم بدء البوت ولكن لم يتم التحقق من نبضات القلب")
            
    except Exception as e:
        logger.error(f"❌ خطأ أثناء تشغيل البوت: {e}")
        import traceback
        logger.error(traceback.format_exc())
        BOT_STARTED = False

# مسارات الويب

@app.route("/ping")
def ping():
    """نقطة نهاية للمراقبة الخارجية"""
    update_heartbeat()
    return "pong", 200

@app.route("/health")
def health():
    """فحص صحة النظام"""
    bot_status = is_bot_running()
    status_code = 200  # دائمًا إرجاع 200 حتى لا يتم إعادة تشغيل Replit
    
    return jsonify({
        "status": "healthy" if bot_status else "warning",
        "bot_running": bot_status,
        "uptime": str(datetime.now() - START_TIME)
    }), status_code

@app.route("/")
def index():
    """الصفحة الرئيسية - لوحة تحكم حالة البوت"""
    global visit_count
    visit_count += 1

    # الحصول على معلومات النظام
    def get_system_info():
        try:
            cpu_percent = psutil.cpu_percent(interval=0.1)
            memory = psutil.virtual_memory()
            disk = psutil.disk_usage('/')
            return {
                "cpu_percent": cpu_percent,
                "memory_percent": memory.percent,
                "disk_percent": disk.percent,
                "memory_used": f"{memory.used / (1024 * 1024):.1f} MB",
                "memory_total": f"{memory.total / (1024 * 1024):.1f} MB",
                "disk_used": f"{disk.used / (1024 * 1024 * 1024):.1f} GB",
                "disk_total": f"{disk.total / (1024 * 1024 * 1024):.1f} GB"
            }
        except Exception as e:
            logger.error(f"خطأ في الحصول على معلومات النظام: {e}")
            return {
                "cpu_percent": 0,
                "memory_percent": 0,
                "disk_percent": 0,
                "memory_used": "غير متاح",
                "memory_total": "غير متاح",
                "disk_used": "غير متاح",
                "disk_total": "غير متاح"
            }
    
    # الحصول على عدد الإشعارات
    def get_notification_count():
        try:
            import database
            return len(database.get_all_notifications())
        except Exception as e:
            logger.error(f"خطأ في الحصول على عدد الإشعارات: {e}")
            return NOTIFICATIONS_COUNT

    # فحص حالة البوت
    bot_status = is_bot_running()
    system_info = get_system_info()
    
    # الحصول على الوقت الحالي لمنع التخزين المؤقت
    timestamp = int(time.time())
    
    # الحصول على آخر نبضة قلب
    try:
        if os.path.exists(HEARTBEAT_FILE):
            with open(HEARTBEAT_FILE, "r") as f:
                timestamp_str = f.read().strip()
                last_heartbeat = datetime.fromtimestamp(float(timestamp_str)).strftime("%Y-%m-%d %H:%M:%S")
        else:
            last_heartbeat = "غير متاح"
    except Exception as e:
        logger.error(f"خطأ في قراءة ملف نبضات القلب: {e}")
        last_heartbeat = "غير متاح"
    
    # تحضير بيانات القالب
    template_data = {
        "bot_status": bot_status,
        "last_update": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "uptime": str(datetime.now() - START_TIME).split('.')[0],
        "last_heartbeat": last_heartbeat,
        "system_info": system_info,
        "notification_count": get_notification_count(),
        "visit_count": visit_count,
        "timestamp": timestamp,
        "year": datetime.now().year
    }
    
    # تقديم القالب
    try:
        # استخدام القالب إذا كان موجوداً
        return render_template('status.html', **template_data), 200, {
            "Cache-Control": "no-cache, no-store, must-revalidate",
            "Pragma": "no-cache",
            "Expires": "0"
        }
    except Exception as e:
        logger.error(f"خطأ في تقديم القالب: {e}، استخدام النسخة المدمجة")
        
        # استخدام النسخة المدمجة كبديل
        return f"""
        <html>
        <head>
            <title>NatureCare Telegram Bot</title>
            <meta charset="UTF-8">
            <meta http-equiv="Cache-Control" content="no-cache, no-store, must-revalidate">
            <meta http-equiv="Pragma" content="no-cache">
            <meta http-equiv="Expires" content="0">
            <meta name="viewport" content="width=device-width, initial-scale=1">
            <style>
                body {{ direction: rtl; padding: 20px; font-family: sans-serif; }}
                .status {{ padding: 10px; border-radius: 5px; margin: 20px 0; }}
                .running {{ background-color: #d4edda; color: #155724; }}
                .stopped {{ background-color: #f8d7da; color: #721c24; }}
                button {{ padding: 10px; background: #007bff; color: white; border: none; border-radius: 5px; cursor: pointer; }}
            </style>
        </head>
        <body>
            <h1>بوت تيليجرام NatureCare</h1>
            <div class="status {'running' if bot_status else 'stopped'}">
                البوت حاليًا: {'يعمل ✅' if bot_status else 'متوقف ❌'}
            </div>
            <p>آخر تحديث: {template_data['last_update']}</p>
            <p>وقت التشغيل: {template_data['uptime']}</p>
            <button onclick="location.href='/restart-bot'">إعادة تشغيل البوت</button>
            <p><a href="/ping">نقطة مراقبة UptimeRobot</a></p>
        </body>
        </html>
        """, 200, {
            "Cache-Control": "no-cache, no-store, must-revalidate",
            "Pragma": "no-cache",
            "Expires": "0"
        }

@app.route('/restart-bot')
def restart_bot():
    """إعادة تشغيل البوت"""
    try:
        # إيقاف البوت الحالي
        import custom_bot_adapter
        custom_bot_adapter.stop_bot_thread()
        
        # الانتظار لثانية واحدة
        time.sleep(1)
        
        # إعادة تشغيل البوت
        success = custom_bot_adapter.start_bot_thread()
        
        return jsonify({
            "status": "success" if success else "error",
            "message": "تم إعادة تشغيل البوت بنجاح" if success else "فشل في إعادة تشغيل البوت"
        })
    except Exception as e:
        logger.error(f"❌ خطأ في إعادة تشغيل البوت: {e}")
        import traceback
        logger.error(traceback.format_exc())
        return jsonify({
            "status": "error",
            "message": f"حدث خطأ: {str(e)}"
        }), 500

# التهيئة الكاملة
def init():
    """تهيئة النظام بالكامل"""
    
    # إنشاء المجلدات الأساسية إذا لم تكن موجودة
    os.makedirs("logs", exist_ok=True)
    os.makedirs("data", exist_ok=True)
    os.makedirs("data/images", exist_ok=True)
    os.makedirs("temp_media", exist_ok=True)
    
    # إنشاء ملف نبضات القلب الأولي
    update_heartbeat()
    
    # بدء تشغيل البوت
    start_bot()
    
    # بدء خيط لتحديث نبضات القلب دوريًا
    # هذا يضمن أن ملف نبضات القلب سيتم تحديثه حتى لو كان البوت نفسه معلقًا
    def heartbeat_thread():
        while True:
            try:
                update_heartbeat()
                time.sleep(15)  # تحديث كل 15 ثانية
            except Exception as e:
                logger.error(f"❌ خطأ في خيط نبضات القلب: {e}")
    
    # بدء خيط نبضات القلب المستقل
    heartbeat = threading.Thread(target=heartbeat_thread)
    heartbeat.daemon = True  # ضمان إيقاف الخيط عند إيقاف البرنامج الرئيسي
    heartbeat.start()
    
    logger.info("✅ اكتملت تهيئة النظام بنجاح")
    return True

# نقطة التشغيل الرئيسية
if __name__ == "__main__":
    # بدء تهيئة النظام في خيط منفصل
    threading.Thread(target=init).start()  # تشغيل البوت والتهيئة في Thread
    
    # تشغيل خادم Flask في العملية الرئيسية
    # هذا يضمن استمرارية البوت حتى عند إغلاق متصفح Replit
    app.run(host='0.0.0.0', port=5000)