import threading
import time
import logging
import requests
import os
import json
from server import start_server
from datetime import datetime

# إعداد التسجيل
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("BotKeepAlive")

# الفواصل الزمنية (بالثواني)
LOCAL_PING_INTERVAL = 30  # ping المحلي كل 30 ثانية
EXTERNAL_PING_INTERVAL = 60  # ping الخارجي كل دقيقة
STATUS_UPDATE_INTERVAL = 300  # تحديث ملف الحالة كل 5 دقائق

def ping_server():
    """إرسال طلب ping للخادم المحلي للحفاظ على نشاطه."""
    try:
        response = requests.get("http://localhost:8080/health", timeout=5)
        if response.status_code == 200:
            logger.info("تم ping الخادم المحلي بنجاح.")
            return True
        else:
            logger.warning(f"فشل ping الخادم المحلي. الكود: {response.status_code}")
            return False
    except Exception as e:
        logger.error(f"خطأ في ping الخادم المحلي: {e}")
        return False

def ping_replit():
    """إرسال طلب إلى Replit لإبقاء الخدمة نشطة."""
    replit_url = os.environ.get("REPLIT_URL", f"https://{os.environ.get('REPL_SLUG')}.{os.environ.get('REPL_OWNER')}.repl.co")
    if replit_url:
        try:
            response = requests.get(f"{replit_url}/health", timeout=10)
            if response.status_code == 200:
                logger.info(f"تم ping Replit بنجاح على {replit_url}.")
                return True
            else:
                logger.warning(f"فشل ping Replit على {replit_url}. الكود: {response.status_code}")
                return False
        except Exception as e:
            logger.error(f"خطأ في ping Replit: {e}")
            return False
    else:
        logger.warning("لم يتم العثور على عنوان Replit. تخطي ping Replit.")
        return False

def ping_uptime_robot():
    """إرسال طلب إلى UptimeRobot لإبقاء رابط المراقبة نشطًا."""
    uptime_url = os.environ.get("UPTIME_MONITOR_URL")
    if uptime_url:
        try:
            response = requests.get(uptime_url, timeout=10)
            logger.info("تم ping UptimeRobot بنجاح.")
            return True
        except Exception as e:
            logger.error(f"خطأ في ping UptimeRobot: {e}")
            return False
    else:
        logger.debug("متغير UPTIME_MONITOR_URL غير موجود. تخطي ping UptimeRobot.")
        return False

def update_status_file(local_status, replit_status, uptime_status):
    """تحديث ملف حالة النظام."""
    try:
        status_data = {
            "timestamp": datetime.now().isoformat(),
            "local_server": {
                "status": "online" if local_status else "offline",
                "last_ping": datetime.now().isoformat()
            },
            "replit": {
                "status": "online" if replit_status else "offline",
                "last_ping": datetime.now().isoformat()
            },
            "uptime_robot": {
                "status": "online" if uptime_status else "offline",
                "last_ping": datetime.now().isoformat() if uptime_status is not None else "not_configured"
            }
        }
        
        with open(".keep_alive_status.json", "w", encoding="utf-8") as f:
            json.dump(status_data, f, ensure_ascii=False, indent=2)
            
        logger.info("تم تحديث ملف حالة النظام.")
    except Exception as e:
        logger.error(f"خطأ في تحديث ملف الحالة: {e}")

def keep_alive_loop():
    """حلقة تحافظ على نشاط البوت من خلال ping دوري."""
    last_external_ping = 0
    last_status_update = 0
    
    while True:
        try:
            current_time = time.time()
            
            # دائماً نقوم بـ ping المحلي
            local_status = ping_server()
            
            # نقوم بـ ping الخارجي وفقاً للفاصل الزمني
            if current_time - last_external_ping >= EXTERNAL_PING_INTERVAL:
                replit_status = ping_replit()
                uptime_status = ping_uptime_robot()
                last_external_ping = current_time
            else:
                # نستخدم القيم السابقة
                replit_status = None
                uptime_status = None
            
            # نقوم بتحديث ملف الحالة وفقاً للفاصل الزمني
            if current_time - last_status_update >= STATUS_UPDATE_INTERVAL:
                update_status_file(local_status, replit_status, uptime_status)
                last_status_update = current_time
                
        except Exception as e:
            logger.error(f"خطأ في حلقة الحفاظ على النشاط: {e}")
        
        # انتظار قبل الـ ping التالي
        time.sleep(LOCAL_PING_INTERVAL)

def start_keep_alive():
    """بدء خادم الويب وخيط الحفاظ على النشاط."""
    # بدء تشغيل خادم Flask
    server_thread = start_server()
    
    # تهيئة ملف الحالة
    update_status_file(True, None, None)
    
    # بدء خيط الحفاظ على النشاط
    keep_alive_thread = threading.Thread(target=keep_alive_loop)
    keep_alive_thread.daemon = True
    keep_alive_thread.start()
    
    logger.info("تم بدء نظام الحفاظ على نشاط البوت.")
    
    return server_thread, keep_alive_thread

if __name__ == "__main__":
    # تم تعطيل التشغيل المباشر هنا - يتم التشغيل الآن من main.py
    logger.info("تم تعطيل تشغيل keep_bot_alive.py مباشرة - يتم التشغيل الآن من main.py")
    
    # لغرض الاختبار فقط
    # logger.info("بدء تشغيل نظام الحفاظ على النشاط...")
    # start_keep_alive()
    #
    # try:
    #    while True:
    #        time.sleep(60)
    # except KeyboardInterrupt:
    #    logger.info("تم إيقاف نظام الحفاظ على النشاط.")