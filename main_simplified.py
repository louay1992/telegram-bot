#!/usr/bin/env python
"""
نظام رئيسي موحد ومبسط لتشغيل بوت تيليجرام مع خادم Flask
------------------------------------------------------------
- يعمل كنقطة دخول موحدة لكافة أجزاء النظام
- يدمج وظائف خادم الويب ونظام نبضات القلب بطريقة مبسطة
- مع تحسين الأداء وتقليل استهلاك الموارد
"""

import os
import sys
import logging
import threading
import time
from datetime import datetime
from flask import Flask, render_template, jsonify, request, send_from_directory

# استيراد وحدة البوت - محسنة لمنع حلقات الاستيراد المتبادلة
BOT_MODULE = None  # سيتم استيراده لاحقاً في خيط منفصل

# متغيرات عامة
HEARTBEAT_FILE = "bot_heartbeat.txt"
SERVER_START_TIME = datetime.now()
bot_thread = None

# إعداد السجلات
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler("logs/server.log")
    ]
)
logger = logging.getLogger("main")

# التأكد من وجود المجلدات الأساسية
os.makedirs("logs", exist_ok=True)
os.makedirs("data", exist_ok=True)
os.makedirs("data/images", exist_ok=True)
os.makedirs("temp_media", exist_ok=True)

# إنشاء تطبيق Flask
app = Flask(__name__)
app.secret_key = os.environ.get("FLASK_SECRET_KEY", "naturecare_secret_key")

# وظائف إدارة البوت ونبضات القلب

def update_heartbeat():
    """تحديث ملف نبضات القلب للتأكد من أن البوت نشط"""
    try:
        with open(HEARTBEAT_FILE, "w") as f:
            f.write(str(time.time()))
        return True
    except Exception as e:
        logger.error(f"❌ خطأ في تحديث ملف نبضات القلب: {e}")
        return False

def is_bot_running():
    """التحقق مما إذا كان البوت نشطاً من خلال ملف نبضات القلب"""
    try:
        if not os.path.exists(HEARTBEAT_FILE):
            return False
            
        with open(HEARTBEAT_FILE, "r") as f:
            timestamp = f.read().strip()
        
        # تحليل الطابع الزمني
        last_heartbeat = datetime.fromtimestamp(float(timestamp))
        time_diff = (datetime.now() - last_heartbeat).total_seconds()
        
        # اعتبار البوت نشطاً إذا كان آخر نبضة قلب خلال 3 دقائق
        return time_diff < 180
    except Exception as e:
        logger.error(f"❌ خطأ في التحقق من حالة البوت: {e}")
        return False

def start_bot():
    """بدء تشغيل البوت في خيط منفصل"""
    global bot_thread
    
    def run_bot_thread():
        try:
            # استيراد وحدة البوت في سياق الخيط
            import custom_bot_adapter
            custom_bot_adapter.start_bot_thread()
            logger.info("✅ تم بدء تشغيل البوت بنجاح")
        except Exception as e:
            logger.error(f"❌ فشل في تشغيل البوت: {e}")
            import traceback
            logger.error(traceback.format_exc())
    
    # إنشاء وتشغيل خيط البوت
    bot_thread = threading.Thread(target=run_bot_thread)
    bot_thread.daemon = True  # ضمان إيقاف الخيط عند إيقاف البرنامج الرئيسي
    bot_thread.start()
    
    # انتظار قصير للتأكد من بدء البوت
    time.sleep(1)
    return is_bot_running()

def stop_bot():
    """إيقاف البوت (إذا كان يعمل)"""
    try:
        import custom_bot_adapter
        return custom_bot_adapter.stop_bot_thread()
    except Exception as e:
        logger.error(f"❌ فشل في إيقاف البوت: {e}")
        return False

# مسارات خادم الويب

@app.route('/')
def index():
    """الصفحة الرئيسية - لوحة تحكم حالة البوت"""
    bot_running = is_bot_running()
    
    return render_template(
        'status.html',
        bot_status=bot_running,
        status_class="status-ok" if bot_running else "status-error",
        last_update=datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        server_uptime=str(datetime.now() - SERVER_START_TIME).split('.')[0],
        last_heartbeat=datetime.fromtimestamp(os.path.getmtime(HEARTBEAT_FILE)).strftime("%Y-%m-%d %H:%M:%S") if os.path.exists(HEARTBEAT_FILE) else "غير متاح"
    ), 200, {
        "Cache-Control": "no-cache, no-store, must-revalidate",
        "Pragma": "no-cache",
        "Expires": "0"
    }

@app.route('/ping')
def ping():
    """نقطة نهاية مبسطة للمراقبة الخارجية - للاستخدام مع UptimeRobot"""
    update_heartbeat()  # تحديث ملف نبضات القلب عند كل طلب ping
    return "pong", 200

@app.route('/health')
def health():
    """فحص صحة النظام - API لاستخدام المراقبة"""
    bot_status = is_bot_running()
    
    return jsonify({
        "status": "healthy" if bot_status else "warning",
        "bot_running": bot_status,
        "uptime": str(datetime.now() - SERVER_START_TIME).split('.')[0]
    }), 200  # دائماً إرجاع 200 حتى لا يتم إعادة تشغيل Replit

@app.route('/restart-bot')
def restart_bot():
    """إعادة تشغيل البوت - API للتحكم"""
    try:
        stop_bot()
        time.sleep(1)  # انتظار قصير
        success = start_bot()
        
        return jsonify({
            "status": "success" if success else "error",
            "message": "تم إعادة تشغيل البوت بنجاح" if success else "فشل في إعادة تشغيل البوت"
        })
    except Exception as e:
        logger.error(f"❌ خطأ في إعادة تشغيل البوت: {e}")
        return jsonify({
            "status": "error",
            "message": f"حدث خطأ: {str(e)}"
        }), 500

@app.route('/media/<path:filename>')
def serve_media(filename):
    """تقديم ملفات الوسائط المستخدمة في النظام"""
    return send_from_directory('data/images', filename)

def init():
    """تهيئة النظام الكاملة"""
    # تحديث ملف نبضات القلب الأولي
    update_heartbeat()
    
    # بدء تشغيل البوت
    start_bot()
    
    # بدء خيط نبضات القلب المستقل
    def heartbeat_thread():
        while True:
            try:
                update_heartbeat()
                time.sleep(15)  # تحديث كل 15 ثانية
            except Exception as e:
                logger.error(f"❌ خطأ في خيط نبضات القلب: {e}")
    
    heartbeat = threading.Thread(target=heartbeat_thread)
    heartbeat.daemon = True
    heartbeat.start()
    
    logger.info("✅ اكتملت تهيئة النظام بنجاح")

# نقطة التشغيل الرئيسية
if __name__ == "__main__":
    # تشغيل وظيفة التهيئة في خيط منفصل
    threading.Thread(target=init).start()
    
    # تشغيل خادم Flask في العملية الرئيسية
    app.run(host='0.0.0.0', port=5000)