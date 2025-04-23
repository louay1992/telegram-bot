from flask import Flask
from threading import Thread
import os
import logging
import datetime
import json

# إعداد التسجيل
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("KeepAliveService")

app = Flask('')

@app.route('/')
def home():
    return "NatureCare Bot is Alive!"

@app.route('/health')
def health_check():
    """نقطة نهاية فحص الصحة للمراقبة الخارجية."""
    return "OK", 200

@app.route('/status')
def status():
    """عرض حالة النظام."""
    return {
        "status": "online",
        "service": "NatureCare Bot",
        "version": "2.1.0"
    }

@app.route('/ping')
def ping():
    """نقطة نهاية للـ ping للتأكد من أن الخدمة نشطة."""
    status_file = "keep_alive_status.json"
    status_data = {
        "last_ping": datetime.datetime.now().isoformat(),
        "status": "active"
    }
    
    try:
        with open(status_file, 'w') as f:
            json.dump(status_data, f)
    except Exception as e:
        logger.error(f"خطأ في كتابة ملف الحالة: {e}")
    
    return {"status": "active", "timestamp": status_data["last_ping"]}

def run():
    """تشغيل تطبيق Flask - معطل، يتم التشغيل الآن من main.py."""
    # معطل - لا تقم بتشغيل خادم Flask هنا
    # port = int(os.environ.get('PORT', 8080))
    # app.run(host='0.0.0.0', port=port)
    logger.info("تم تعطيل تشغيل خادم Flask من keep_alive.py - يتم التشغيل الآن من main.py")

def keep_alive():
    """بدء تشغيل خادم Flask في خيط منفصل."""
    logger.info("بدء تشغيل خدمة Keep-Alive...")
    t = Thread(target=run)
    t.daemon = True  # تعيين الخيط كخيط شبح يتوقف عند توقف البرنامج الرئيسي
    t.start()
    logger.info(f"تم بدء خدمة Keep-Alive على المنفذ {os.environ.get('PORT', 8080)}")
    
def start_keep_alive_service():
    """بدء تشغيل خدمة Keep-Alive - واجهة متوافقة مع الإصدار السابق."""
    try:
        keep_alive()
        return True
    except Exception as e:
        logger.error(f"خطأ في بدء خدمة Keep-Alive: {e}")
        return False