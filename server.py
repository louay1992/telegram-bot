#!/usr/bin/env python3
"""
خادم Flask بسيط للحفاظ على نشاط التطبيق وتوفير نقاط نهاية للمراقبة
"""
import os
import time
import datetime
import json
import logging
import threading
from flask import Flask, jsonify, render_template_string

# استيراد التكوين الموحد
try:
    from unified_config import get_config
except ImportError:
    def get_config(key=None):
        defaults = {
            "HEARTBEAT_FILE": "bot_heartbeat.txt",
            "MAX_HEARTBEAT_AGE": 120
        }
        if key is None:
            return defaults
        return defaults.get(key)

# إعداد التسجيل
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("KeepAliveServer")

# إنشاء تطبيق Flask
app = Flask(__name__)

# قالب HTML للصفحة الرئيسية
HOME_TEMPLATE = """
<!DOCTYPE html>
<html lang="ar" dir="rtl">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>بوت الإشعارات - لوحة الحالة</title>
    <link href="https://cdn.replit.com/agent/bootstrap-agent-dark-theme.min.css" rel="stylesheet">
    <style>
        body {
            padding: 20px;
            background-color: #1a1a1a;
            color: #fff;
        }
        .status-card {
            border: none;
            margin-bottom: 20px;
        }
        .status-ok {
            background-color: #198754;
        }
        .status-warning {
            background-color: #ffc107;
            color: #000;
        }
        .status-error {
            background-color: #dc3545;
        }
        .heartbeat-pulse {
            display: inline-block;
            width: 10px;
            height: 10px;
            border-radius: 50%;
            background-color: #198754;
            margin-right: 10px;
            animation: pulse 1.5s infinite;
        }
        @keyframes pulse {
            0% { transform: scale(0.95); box-shadow: 0 0 0 0 rgba(25, 135, 84, 0.7); }
            70% { transform: scale(1); box-shadow: 0 0 0 10px rgba(25, 135, 84, 0); }
            100% { transform: scale(0.95); box-shadow: 0 0 0 0 rgba(25, 135, 84, 0); }
        }
        .timestamp {
            font-size: 0.8rem;
            color: #aaa;
        }
    </style>
</head>
<body>
    <div class="container">
        <div class="row mt-4">
            <div class="col-md-12">
                <h1 class="text-center mb-4">لوحة حالة بوت الإشعارات</h1>
                
                <div class="card status-card {{bot_status_class}}">
                    <div class="card-body">
                        <h5 class="card-title">
                            <div class="heartbeat-pulse"></div>
                            حالة البوت
                        </h5>
                        <p class="card-text">{{bot_status_message}}</p>
                        <p class="timestamp">آخر تحديث: {{current_time}}</p>
                    </div>
                </div>
                
                <div class="card status-card">
                    <div class="card-body">
                        <h5 class="card-title">معلومات النظام</h5>
                        <p class="card-text"><strong>وقت تشغيل الخادم:</strong> {{server_uptime}}</p>
                        <p class="card-text"><strong>آخر نبضة قلب:</strong> {{last_heartbeat_age}}</p>
                        <p class="card-text"><strong>عنوان IP:</strong> {{server_ip}}</p>
                    </div>
                </div>
                
                <div class="card status-card">
                    <div class="card-body">
                        <h5 class="card-title">الإحصائيات</h5>
                        <p class="card-text"><strong>عدد الإشعارات:</strong> {{notification_count}}</p>
                        <p class="card-text"><strong>عدد زيارات الصفحة:</strong> {{visit_count}}</p>
                    </div>
                </div>
            </div>
        </div>
    </div>
    <script>
        // تحديث الصفحة كل دقيقة
        setTimeout(function() {
            location.reload();
        }, 60000);
    </script>
</body>
</html>
"""

# متغيرات عالمية
server_start_time = datetime.datetime.now()
visit_count = 0

@app.route('/')
def index():
    """الصفحة الرئيسية للتطبيق"""
    global visit_count
    visit_count += 1
    
    # التحقق من حالة نبضات قلب البوت
    heartbeat_status, heartbeat_age = check_bot_heartbeat()
    
    if heartbeat_age is None:
        bot_status_message = "لم يتم العثور على ملف نبضات القلب"
        bot_status_class = "status-error"
        last_heartbeat_age = "غير متاح"
    elif heartbeat_age > get_config("MAX_HEARTBEAT_AGE"):
        bot_status_message = f"توقف البوت! آخر نبضة قلب قبل {int(heartbeat_age)} ثانية"
        bot_status_class = "status-error"
        last_heartbeat_age = f"{int(heartbeat_age)} ثانية مضت"
    elif heartbeat_age > 60:
        bot_status_message = f"البوت يعمل (تأخير في النبضات: {int(heartbeat_age)} ثانية)"
        bot_status_class = "status-warning"
        last_heartbeat_age = f"{int(heartbeat_age)} ثانية مضت"
    else:
        bot_status_message = "البوت يعمل بشكل طبيعي"
        bot_status_class = "status-ok"
        last_heartbeat_age = f"{int(heartbeat_age)} ثانية مضت"
    
    # حساب وقت تشغيل الخادم
    uptime = datetime.datetime.now() - server_start_time
    hours, remainder = divmod(uptime.total_seconds(), 3600)
    minutes, seconds = divmod(remainder, 60)
    server_uptime = f"{int(hours)} ساعة, {int(minutes)} دقيقة, {int(seconds)} ثانية"
    
    # عدد الإشعارات
    notification_count = get_notification_count()
    
    # الحصول على عنوان IP الخادم
    server_ip = get_server_ip()
    
    # توليد الصفحة
    return render_template_string(
        HOME_TEMPLATE,
        bot_status_message=bot_status_message,
        bot_status_class=bot_status_class,
        current_time=datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        server_uptime=server_uptime,
        last_heartbeat_age=last_heartbeat_age,
        notification_count=notification_count,
        visit_count=visit_count,
        server_ip=server_ip
    )

@app.route('/ping')
def ping():
    """نقطة نهاية للتحقق من حالة الخادم"""
    return jsonify({"status": "ok", "timestamp": time.time()})

@app.route('/api/status')
def status_api():
    """واجهة برمجة تطبيقات للحصول على حالة النظام بصيغة JSON"""
    # التحقق من حالة نبضات قلب البوت
    heartbeat_status, heartbeat_age = check_bot_heartbeat()
    
    # حساب وقت تشغيل الخادم
    uptime = datetime.datetime.now() - server_start_time
    
    # جمع معلومات النظام
    status_data = {
        "server": {
            "status": "ok",
            "uptime_seconds": uptime.total_seconds(),
            "start_time": server_start_time.isoformat(),
        },
        "bot": {
            "status": heartbeat_status,
            "last_heartbeat_age": heartbeat_age,
            "heartbeat_file_exists": os.path.exists(get_config("HEARTBEAT_FILE"))
        },
        "statistics": {
            "visit_count": visit_count,
            "notification_count": get_notification_count()
        },
        "timestamp": datetime.datetime.now().isoformat()
    }
    
    return jsonify(status_data)

@app.route('/healthz')
def health_check():
    """نقطة نهاية فحص الصحة لـ Replit Deployments"""
    # التحقق من حالة نبضات قلب البوت
    heartbeat_status, heartbeat_age = check_bot_heartbeat()
    
    if heartbeat_age is None or heartbeat_age > get_config("MAX_HEARTBEAT_AGE"):
        return jsonify({
            "status": "warning",
            "message": "البوت قد يكون متوقفاً",
            "timestamp": time.time()
        }), 200
    
    return jsonify({
        "status": "ok",
        "message": "الخادم والبوت يعملان بشكل طبيعي",
        "timestamp": time.time()
    }), 200

def check_bot_heartbeat():
    """التحقق من ملف نبضات قلب البوت"""
    heartbeat_file = get_config("HEARTBEAT_FILE")
    
    try:
        if os.path.exists(heartbeat_file):
            with open(heartbeat_file, 'r') as f:
                last_heartbeat = float(f.read().strip())
            
            heartbeat_age = time.time() - last_heartbeat
            
            if heartbeat_age > get_config("MAX_HEARTBEAT_AGE"):
                return "error", heartbeat_age
            elif heartbeat_age > 60:
                return "warning", heartbeat_age
            else:
                return "ok", heartbeat_age
        else:
            return "error", None
    except Exception as e:
        logger.error(f"خطأ في التحقق من نبضات القلب: {e}")
        return "error", None

def get_notification_count():
    """الحصول على عدد الإشعارات المحفوظة"""
    try:
        # محاولة الحصول على عدد الإشعارات من قاعدة البيانات
        from database import get_notification_count
        return get_notification_count()
    except:
        # إذا فشل، محاولة العد من ملفات JSON
        try:
            if os.path.exists("data/notifications.json"):
                with open("data/notifications.json", 'r') as f:
                    notifications = json.load(f)
                return len(notifications)
        except:
            pass
    
    return 0

def get_server_ip():
    """الحصول على عنوان IP الخادم"""
    try:
        import socket
        hostname = socket.gethostname()
        ip = socket.gethostbyname(hostname)
        return ip
    except:
        return "غير متاح"

def start_keep_alive_server():
    """بدء تشغيل خادم الحفاظ على النشاط"""
    port = int(os.environ.get("PORT", 8080))
    logger.info(f"بدء تشغيل خادم الحفاظ على النشاط على المنفذ {port}...")
    
    # تم تعطيل تشغيل خادم Flask هنا - يتم التشغيل الآن من main.py
    # threading.Thread(target=lambda: app.run(host='0.0.0.0', port=port, debug=False, use_reloader=False), daemon=True).start()
    
    logger.info("تم تعطيل تشغيل خادم Flask من server.py - يتم التشغيل الآن من main.py")

# استخدم هذا للتوافق مع استدعاء من main.py
start_server = start_keep_alive_server

if __name__ == "__main__":
    # بدء تشغيل خادم الحفاظ على النشاط
    start_keep_alive_server()
    
    # الحفاظ على تشغيل البرنامج الرئيسي
    try:
        while True:
            time.sleep(60)
    except KeyboardInterrupt:
        print("تم إيقاف الخادم")