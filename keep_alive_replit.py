#!/usr/bin/env python
"""
نظام متخصص للحفاظ على تشغيل الكود في Replit حتى بعد إغلاق المتصفح
يتغلب هذا النظام على محدودية Replit الأساسية بإيقاف العمليات بعد إغلاق المتصفح
"""

import os
import requests
import threading
import time
import datetime
import logging
import json
from flask import Flask, jsonify

# إعداد نظام السجلات
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("keep_alive")

# إنشاء تطبيق Flask صغير للحفاظ على خادم نشط
app = Flask(__name__)

# متغيرات التكوين
PING_INTERVAL = int(os.environ.get("PING_INTERVAL", 180))  # الفاصل الزمني بين عمليات الفحص (بالثواني)
REPLIT_DOMAIN = os.environ.get("REPLIT_DOMAIN", None)  # نطاق Replit (يتم ضبطه تلقائياً)
PROJECT_URL = os.environ.get("PROJECT_URL", None)  # عنوان URL الخاص بمشروعك
EXTERNAL_PING_URL = os.environ.get("EXTERNAL_PING_URL", None)  # عنوان URL للمراقبة الخارجية
SELF_PING = os.environ.get("SELF_PING", "True").lower() in ("true", "1", "yes")  # هل تريد أن يقوم النظام بطلب نفسه
UPT_ROBOT_TOKEN = os.environ.get("UPT_ROBOT_TOKEN", None)  # توكن UptimeRobot (اختياري)
KEEP_ALIVE_STATUS_FILE = ".keep_alive_status.json"  # ملف لتخزين حالة نظام الإبقاء على قيد الحياة

# حالة النظام
last_ping_time = None
ping_count = 0
app_start_time = datetime.datetime.now()
ping_history = []

# مسارات النظام
@app.route('/')
def home():
    """صفحة الترحيب الرئيسية"""
    return f"""
    <html>
    <head>
        <title>نظام الحفاظ على الاستمرارية لبوت تيليجرام</title>
        <meta http-equiv="refresh" content="30">
        <style>
            body {{ font-family: Arial, sans-serif; text-align: center; margin: 50px; direction: rtl; }}
            .status {{ padding: 20px; border-radius: 5px; margin: 20px; }}
            .active {{ background-color: #d4edda; color: #155724; }}
            .inactive {{ background-color: #f8d7da; color: #721c24; }}
            .container {{ max-width: 800px; margin: 0 auto; }}
            table {{ width: 100%; border-collapse: collapse; }}
            table, th, td {{ border: 1px solid #ddd; }}
            th, td {{ padding: 12px; text-align: center; }}
            th {{ background-color: #f2f2f2; }}
        </style>
    </head>
    <body>
        <div class="container">
            <h1>نظام الحفاظ على استمرارية البوت</h1>
            <div class="status {'active' if is_system_active() else 'inactive'}">
                <h2>الحالة: {'نشط' if is_system_active() else 'غير نشط'}</h2>
                <p>آخر فحص: {get_last_ping_formatted()}</p>
                <p>عدد عمليات الفحص: {ping_count}</p>
                <p>وقت بدء التشغيل: {app_start_time.strftime('%Y-%m-%d %H:%M:%S')}</p>
            </div>
            
            <h2>إعدادات النظام</h2>
            <table>
                <tr>
                    <th>الإعداد</th>
                    <th>القيمة</th>
                </tr>
                <tr>
                    <td>الفاصل الزمني للفحص</td>
                    <td>{PING_INTERVAL} ثانية</td>
                </tr>
                <tr>
                    <td>نطاق Replit</td>
                    <td>{REPLIT_DOMAIN or "لم يتم تكوينه"}</td>
                </tr>
                <tr>
                    <td>عنوان المشروع</td>
                    <td>{PROJECT_URL or "تلقائي"}</td>
                </tr>
                <tr>
                    <td>الفحص الذاتي</td>
                    <td>{"مفعل" if SELF_PING else "معطل"}</td>
                </tr>
                <tr>
                    <td>المراقبة الخارجية</td>
                    <td>{"مكونة" if EXTERNAL_PING_URL else "غير مكونة"}</td>
                </tr>
            </table>
            
            <h2>آخر 5 عمليات فحص</h2>
            <table>
                <tr>
                    <th>الوقت</th>
                    <th>الحالة</th>
                </tr>
                {"".join(f"<tr><td>{time}</td><td>{status}</td></tr>" for time, status in get_recent_pings())}
            </table>
            
            <p style="margin-top: 30px;">
                هذه الصفحة تتحدث تلقائياً كل 30 ثانية.
                <br>
                <small>وقت التحديث: {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</small>
            </p>
        </div>
    </body>
    </html>
    """

@app.route('/ping')
def ping():
    """نقطة نهاية للفحص البسيط"""
    global last_ping_time, ping_count
    last_ping_time = datetime.datetime.now()
    ping_count += 1
    
    # تحديث سجل الفحص
    ping_history.append((last_ping_time.strftime('%Y-%m-%d %H:%M:%S'), "ناجح"))
    if len(ping_history) > 20:  # الاحتفاظ بآخر 20 فحص فقط
        ping_history.pop(0)
    
    # حفظ الحالة
    save_status()
    
    return jsonify({
        "status": "ok",
        "timestamp": last_ping_time.isoformat(),
        "ping_count": ping_count
    })

@app.route('/status')
def status():
    """عرض حالة نظام الحفاظ على النشاط بصيغة JSON"""
    return jsonify({
        "active": is_system_active(),
        "last_ping": get_last_ping_formatted(),
        "ping_count": ping_count,
        "start_time": app_start_time.isoformat(),
        "uptime_seconds": (datetime.datetime.now() - app_start_time).total_seconds(),
        "configuration": {
            "ping_interval": PING_INTERVAL,
            "replit_domain": REPLIT_DOMAIN,
            "project_url": PROJECT_URL,
            "self_ping": SELF_PING,
            "external_monitoring": bool(EXTERNAL_PING_URL)
        }
    })

@app.route('/health')
def health():
    """نقطة نهاية لفحص الصحة"""
    is_active = is_system_active()
    return jsonify({
        "status": "ok" if is_active else "degraded",
        "active": is_active,
        "last_ping": get_last_ping_formatted()
    }), 200 if is_active else 200  # نعيد 200 حتى لو كان النظام متدهوراً لتجنب التنبيهات

def is_system_active():
    """التحقق مما إذا كان نظام الحفاظ على النشاط يعمل بشكل صحيح"""
    if last_ping_time is None:
        return False
    
    time_since_last_ping = (datetime.datetime.now() - last_ping_time).total_seconds()
    return time_since_last_ping < (PING_INTERVAL * 2)  # نعتبر النظام نشطاً إذا كان آخر فحص خلال ضعف الفاصل الزمني

def get_last_ping_formatted():
    """الحصول على وقت آخر فحص بتنسيق مقروء"""
    if last_ping_time is None:
        return "لم يتم بعد"
    
    time_since = (datetime.datetime.now() - last_ping_time).total_seconds()
    if time_since < 60:
        return f"{int(time_since)} ثانية مضت"
    elif time_since < 3600:
        return f"{int(time_since / 60)} دقيقة مضت"
    else:
        return f"{int(time_since / 3600)} ساعة مضت"

def get_recent_pings():
    """الحصول على آخر 5 عمليات فحص"""
    return ping_history[-5:] if ping_history else [("لا توجد بيانات", "--")]

def save_status():
    """حفظ حالة نظام الحفاظ على النشاط إلى ملف"""
    status_data = {
        "last_ping": last_ping_time.isoformat() if last_ping_time else None,
        "ping_count": ping_count,
        "start_time": app_start_time.isoformat(),
        "ping_history": ping_history
    }
    
    try:
        with open(KEEP_ALIVE_STATUS_FILE, "w") as f:
            json.dump(status_data, f)
    except Exception as e:
        logger.error(f"فشل في حفظ حالة نظام الحفاظ على النشاط: {e}")

def load_status():
    """تحميل حالة نظام الحفاظ على النشاط من ملف"""
    global last_ping_time, ping_count, app_start_time, ping_history
    
    try:
        if os.path.exists(KEEP_ALIVE_STATUS_FILE):
            with open(KEEP_ALIVE_STATUS_FILE, "r") as f:
                status_data = json.load(f)
                
            if status_data.get("last_ping"):
                last_ping_time = datetime.datetime.fromisoformat(status_data["last_ping"])
            ping_count = status_data.get("ping_count", 0)
            if status_data.get("start_time"):
                # حفظ وقت بدء التشغيل الأصلي إذا كان ضمن آخر 24 ساعة
                saved_start_time = datetime.datetime.fromisoformat(status_data["start_time"])
                if (datetime.datetime.now() - saved_start_time).total_seconds() < 86400:  # 24 ساعة
                    app_start_time = saved_start_time
            ping_history = status_data.get("ping_history", [])
    except Exception as e:
        logger.error(f"فشل في تحميل حالة نظام الحفاظ على النشاط: {e}")

def keep_alive_ping():
    """وظيفة الفحص الرئيسية التي تحافظ على نشاط التطبيق"""
    logger.info("بدء خيط الحفاظ على النشاط")
    
    # تحديد عنوان URL للمشروع
    project_url = PROJECT_URL
    if not project_url and REPLIT_DOMAIN:
        project_url = f"https://{REPLIT_DOMAIN}.repl.co"
    
    while True:
        current_time = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        # فحص ذاتي للتطبيق
        if SELF_PING and project_url:
            try:
                logger.info(f"[{current_time}] إرسال فحص ذاتي إلى {project_url}/ping")
                response = requests.get(f"{project_url}/ping", timeout=10)
                logger.info(f"استجابة الفحص الذاتي: {response.status_code}")
            except Exception as e:
                logger.error(f"فشل الفحص الذاتي: {e}")
        
        # فحص خارجي (UptimeRobot أو خدمة مماثلة)
        if EXTERNAL_PING_URL:
            try:
                logger.info(f"[{current_time}] إرسال فحص إلى مراقب خارجي: {EXTERNAL_PING_URL}")
                requests.get(EXTERNAL_PING_URL, timeout=10)
            except Exception as e:
                logger.error(f"فشل فحص المراقب الخارجي: {e}")
        
        # UptimeRobot API (إذا تم تكوينه)
        if UPT_ROBOT_TOKEN:
            try:
                logger.info(f"[{current_time}] إرسال فحص إلى UptimeRobot API")
                headers = {"Content-Type": "application/json"}
                response = requests.post(
                    "https://api.uptimerobot.com/v2/getMonitors",
                    headers=headers,
                    json={"api_key": UPT_ROBOT_TOKEN, "format": "json", "logs": 0}
                )
                logger.info(f"استجابة UptimeRobot: {response.status_code}")
            except Exception as e:
                logger.error(f"فشل فحص UptimeRobot: {e}")
        
        # الانتظار حتى الفحص التالي
        time.sleep(PING_INTERVAL)

def run_keep_alive_server(host="0.0.0.0", port=8080):
    """تشغيل خادم الحفاظ على النشاط"""
    try:
        # تحميل الحالة السابقة
        load_status()
        
        # بدء خيط الحفاظ على النشاط
        keep_alive_thread = threading.Thread(target=keep_alive_ping, daemon=True)
        keep_alive_thread.start()
        
        # تشغيل خادم الويب
        # تنبيه: هذا سيقوم بتشغيل خادم Flask في الخيط الرئيسي
        logger.info(f"بدء تشغيل خادم الحفاظ على النشاط على {host}:{port}")
        app.run(host=host, port=port)
    except Exception as e:
        logger.error(f"خطأ في تشغيل خادم الحفاظ على النشاط: {e}")
        import traceback
        logger.error(traceback.format_exc())

def setup_and_run(debug=False):
    """إعداد وتشغيل نظام الحفاظ على النشاط"""
    # تحديد عنوان Replit تلقائياً إذا لم يتم تحديده
    global REPLIT_DOMAIN
    if not REPLIT_DOMAIN:
        try:
            REPLIT_DOMAIN = os.environ.get("REPL_SLUG")
            logger.info(f"تم تحديد نطاق Replit تلقائياً: {REPLIT_DOMAIN}")
        except Exception as e:
            logger.warning(f"فشل في تحديد نطاق Replit تلقائياً: {e}")
    
    # تشغيل النظام
    run_keep_alive_server(port=8080)

if __name__ == "__main__":
    # تشغيل نظام الحفاظ على النشاط
    setup_and_run()