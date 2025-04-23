#!/usr/bin/env python3
"""
نظام شامل للحفاظ على استمرارية تشغيل البوت

هذا السكريبت يقوم بتشغيل نظام متكامل للحفاظ على استمرارية عمل البوت حتى بعد إغلاق الـ agent
أو انقطاع الاتصال. يتكون النظام من عدة طبقات:

1. خدمة KeepAlive على المنفذ 8080 (HTTP Ping)
2. سكريبت مراقبة للبوت (يعيد تشغيله إذا توقف)
3. آلية نبضات قلب لتسجيل نشاط البوت
4. تشغيل البوت المعدل مع التوكن الجديد
5. إشعارات تيليجرام للمسؤول عند حدوث أي مشكلة
"""
import os
import sys
import time
import signal
import logging
import subprocess
import threading
import http.server
import socketserver
import json
from datetime import datetime, timedelta
import requests

# إعداد التسجيل
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    filename='keepalive_system.log'
)

# تكوين النظام
BOT_SCRIPT = "custom_bot.py"  # استخدام البوت المعدل مع التوكن الجديد
TELEGRAM_TOKEN = "7406580104:AAGG2JQeeNfsmcGVMCm7hxitIK-qm2yekVg"
ADMIN_CHAT_ID = None  # سيتم تحديده تلقائياً من خلال التفاعل مع البوت
KEEP_ALIVE_PORT = 8080
HEARTBEAT_FILE = "bot_heartbeat.txt"
HEARTBEAT_TIMEOUT = 60  # ثوانٍ
CHECK_INTERVAL = 30  # ثوانٍ
MAX_RESTART_ATTEMPTS = 5
STATUS_FILE = ".keep_alive_status.json"

# الحالة العامة للنظام
keep_alive_running = True
bot_process = None
last_restart_time = None
restart_count = 0

class KeepAliveHandler(http.server.SimpleHTTPRequestHandler):
    """معالج طلبات خدمة KeepAlive."""
    
    def do_GET(self):
        """استجابة لطلبات GET."""
        if self.path == '/status':
            self.send_response(200)
            self.send_header('Content-type', 'application/json')
            self.end_headers()
            
            status = check_system_status()
            self.wfile.write(json.dumps(status).encode())
        elif self.path == '/ping':
            self.send_response(200)
            self.send_header('Content-type', 'text/plain')
            self.end_headers()
            self.wfile.write(b"pong")
        else:
            self.send_response(200)
            self.send_header('Content-type', 'text/html')
            self.end_headers()
            
            heartbeat_age = get_heartbeat_age()
            bot_status = "✅ نشط" if heartbeat_age < HEARTBEAT_TIMEOUT else f"❌ متوقف (آخر نشاط منذ {heartbeat_age} ثانية)"
            
            html = f"""
            <!DOCTYPE html>
            <html dir="rtl">
            <head>
                <meta charset="utf-8">
                <meta name="viewport" content="width=device-width, initial-scale=1">
                <title>حالة البوت</title>
                <style>
                    body {{ font-family: Arial, sans-serif; margin: 0; padding: 20px; background: #f7f7f7; }}
                    .container {{ max-width: 800px; margin: 0 auto; background: white; padding: 20px; border-radius: 10px; box-shadow: 0 0 10px rgba(0,0,0,0.1); }}
                    h1 {{ color: #333; text-align: center; }}
                    .status {{ margin: 20px 0; padding: 15px; border-radius: 5px; }}
                    .active {{ background-color: #d4edda; color: #155724; }}
                    .inactive {{ background-color: #f8d7da; color: #721c24; }}
                    .info {{ background-color: #d1ecf1; color: #0c5460; padding: 15px; border-radius: 5px; margin-bottom: 10px; }}
                    .stats {{ margin-top: 20px; }}
                    .refresh {{ display: block; text-align: center; margin-top: 20px; }}
                </style>
            </head>
            <body>
                <div class="container">
                    <h1>نظام مراقبة بوت تيليجرام</h1>
                    
                    <div class="status {'active' if heartbeat_age < HEARTBEAT_TIMEOUT else 'inactive'}">
                        <h2>حالة البوت: {bot_status}</h2>
                        <p>آخر نشاط: {heartbeat_age:.1f} ثانية مضت</p>
                    </div>
                    
                    <div class="info">
                        <h3>معلومات النظام:</h3>
                        <ul>
                            <li>سكريبت البوت: {BOT_SCRIPT}</li>
                            <li>فاصل زمني للفحص: {CHECK_INTERVAL} ثانية</li>
                            <li>مهلة نبضات القلب: {HEARTBEAT_TIMEOUT} ثانية</li>
                            <li>عدد إعادة التشغيل: {restart_count}</li>
                            <li>آخر إعادة تشغيل: {last_restart_time if last_restart_time else 'لا يوجد'}</li>
                        </ul>
                    </div>
                    
                    <a href="/status" class="refresh">تحديث الحالة</a>
                </div>
                
                <script>
                    setTimeout(function() {{
                        window.location.reload();
                    }}, 30000);
                </script>
            </body>
            </html>
            """
            
            self.wfile.write(html.encode())
    
    def log_message(self, format, *args):
        """تسجيل رسائل الخادم."""
        logging.info(f"KeepAlive Server: {format % args}")

def start_keep_alive_server():
    """بدء تشغيل خادم KeepAlive."""
    try:
        logging.info(f"بدء تشغيل خادم الحفاظ على النشاط على المنفذ {KEEP_ALIVE_PORT}...")
        server = socketserver.TCPServer(("0.0.0.0", KEEP_ALIVE_PORT), KeepAliveHandler)
        server_thread = threading.Thread(target=server.serve_forever)
        server_thread.daemon = True
        server_thread.start()
        logging.info("تم بدء تشغيل خادم الحفاظ على النشاط بنجاح!")
        return server
    except Exception as e:
        logging.error(f"خطأ في بدء تشغيل خادم الحفاظ على النشاط: {e}")
        return None

def update_heartbeat():
    """تحديث ملف نبضات القلب."""
    try:
        with open(HEARTBEAT_FILE, 'w') as f:
            f.write(datetime.now().isoformat())
        return True
    except Exception as e:
        logging.error(f"خطأ في تحديث ملف نبضات القلب: {e}")
        return False

def get_heartbeat_age():
    """الحصول على عمر آخر نبضة قلب بالثواني."""
    try:
        if not os.path.exists(HEARTBEAT_FILE):
            return float('inf')
        
        with open(HEARTBEAT_FILE, 'r') as f:
            heartbeat_time = datetime.fromisoformat(f.read().strip())
        
        age_seconds = (datetime.now() - heartbeat_time).total_seconds()
        return age_seconds
    except Exception as e:
        logging.error(f"خطأ في قراءة ملف نبضات القلب: {e}")
        return float('inf')

def check_bot_running():
    """التحقق مما إذا كان البوت يعمل."""
    heartbeat_age = get_heartbeat_age()
    return heartbeat_age < HEARTBEAT_TIMEOUT

def start_bot():
    """بدء تشغيل البوت."""
    global bot_process, last_restart_time, restart_count
    
    try:
        # إيقاف العملية السابقة إذا كانت موجودة
        if bot_process and bot_process.poll() is None:
            try:
                bot_process.terminate()
                time.sleep(2)
            except Exception:
                pass
        
        # تهيئة متغيرات البيئة
        env = os.environ.copy()
        env["TELEGRAM_BOT_TOKEN"] = TELEGRAM_TOKEN
        
        # بدء عملية البوت
        logging.info(f"بدء تشغيل البوت باستخدام: {BOT_SCRIPT}")
        bot_process = subprocess.Popen(['python', BOT_SCRIPT], env=env)
        
        # تسجيل إعادة التشغيل
        last_restart_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        restart_count += 1
        save_status()
        
        # إرسال إشعار للمسؤول
        if restart_count > 1:  # لا نرسل إشعاراً في المرة الأولى
            notify_admin(f"🔄 تم إعادة تشغيل البوت (المحاولة #{restart_count})\nالوقت: {last_restart_time}")
        
        return True
    except Exception as e:
        logging.error(f"خطأ في بدء تشغيل البوت: {e}")
        return False

def stop_bot():
    """إيقاف البوت."""
    global bot_process
    
    if bot_process and bot_process.poll() is None:
        try:
            logging.info("إيقاف البوت...")
            bot_process.terminate()
            time.sleep(2)
            if bot_process.poll() is None:
                bot_process.kill()
            logging.info("تم إيقاف البوت بنجاح")
            return True
        except Exception as e:
            logging.error(f"خطأ في إيقاف البوت: {e}")
    
    return False

def notify_admin(message):
    """إرسال إشعار للمسؤول عبر تيليجرام."""
    global ADMIN_CHAT_ID
    
    # البحث عن معرف المسؤول إذا لم يكن محدداً
    if ADMIN_CHAT_ID is None:
        try:
            ADMIN_CHAT_ID = find_admin_chat_id()
        except Exception as e:
            logging.error(f"لم يتم العثور على معرف المسؤول: {e}")
            return False
    
    if not ADMIN_CHAT_ID:
        logging.warning("لم يتم تحديد معرف المسؤول. لا يمكن إرسال الإشعارات.")
        return False
    
    try:
        url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
        params = {
            "chat_id": ADMIN_CHAT_ID,
            "text": message,
            "parse_mode": "HTML"
        }
        response = requests.post(url, json=params)
        return response.status_code == 200
    except Exception as e:
        logging.error(f"خطأ في إرسال إشعار للمسؤول: {e}")
        return False

def find_admin_chat_id():
    """البحث عن معرف المسؤول من ملف المسؤولين."""
    try:
        # محاولة قراءة معرف المسؤول من ملف المسؤولين
        admins_file = "data/admins.json"
        if os.path.exists(admins_file):
            with open(admins_file, 'r') as f:
                admins = json.load(f)
                
            if admins and len(admins) > 0:
                # استخدام أول مسؤول في القائمة
                admin_id = admins[0]
                logging.info(f"تم العثور على معرف المسؤول: {admin_id}")
                return admin_id
    except Exception as e:
        logging.error(f"خطأ في البحث عن معرف المسؤول: {e}")
    
    return None

def monitor_bot():
    """مراقبة حالة البوت وإعادة تشغيله إذا توقف."""
    global restart_count, last_restart_time
    
    logging.info("بدء نظام مراقبة البوت...")
    update_heartbeat()  # تحديث ملف نبضات القلب عند بدء المراقبة
    
    while keep_alive_running:
        try:
            # التحقق من حالة البوت
            if not check_bot_running():
                logging.warning(f"❌ البوت متوقف! آخر نبضة قلب: {get_heartbeat_age():.1f} ثانية مضت")
                
                # التحقق من عدد محاولات إعادة التشغيل
                if restart_count >= MAX_RESTART_ATTEMPTS:
                    if last_restart_time and (datetime.now() - datetime.strptime(last_restart_time, "%Y-%m-%d %H:%M:%S")).total_seconds() > 3600:
                        # إعادة ضبط العداد بعد ساعة من آخر إعادة تشغيل
                        restart_count = 0
                        logging.info("تم إعادة ضبط عداد إعادة التشغيل بعد مرور ساعة")
                    else:
                        # إرسال إشعار للمسؤول بعد الوصول للحد الأقصى
                        notify_admin(f"⚠️ تم الوصول للحد الأقصى من محاولات إعادة التشغيل ({MAX_RESTART_ATTEMPTS}).\nآخر محاولة: {last_restart_time}\nيرجى التحقق من البوت يدوياً.")
                        logging.error(f"تم الوصول للحد الأقصى من محاولات إعادة التشغيل ({MAX_RESTART_ATTEMPTS})")
                        time.sleep(600)  # انتظار 10 دقائق قبل المحاولة مرة أخرى
                        continue
                
                # محاولة إعادة تشغيل البوت
                logging.info("🔄 إعادة تشغيل البوت...")
                
                # تنفيذ وظيفة تنظيف
                clean_environment()
                
                # إعادة تشغيل البوت
                if start_bot():
                    logging.info("✅ تم إعادة تشغيل البوت بنجاح!")
                else:
                    logging.error("❌ فشل في إعادة تشغيل البوت!")
            else:
                # تحديث ملف نبضات القلب
                update_heartbeat()
            
            # حفظ الحالة
            save_status()
        except Exception as e:
            logging.error(f"خطأ في مراقبة البوت: {e}")
        
        # الانتظار قبل الفحص التالي
        time.sleep(CHECK_INTERVAL)

def clean_environment():
    """تنظيف البيئة قبل إعادة تشغيل البوت."""
    try:
        # حذف ملفات العلامات
        markers = [
            "bot_shutdown_marker",
            "watchdog_ping",
            "bot_restart_marker",
            "restart_requested.log"
        ]
        
        for marker in markers:
            if os.path.exists(marker):
                try:
                    os.remove(marker)
                    logging.info(f"تم حذف ملف العلامة: {marker}")
                except Exception as e:
                    logging.error(f"خطأ في حذف ملف العلامة {marker}: {e}")
    except Exception as e:
        logging.error(f"خطأ في تنظيف البيئة: {e}")

def save_status():
    """حفظ حالة النظام."""
    try:
        status = {
            "heartbeat_age": get_heartbeat_age(),
            "bot_running": check_bot_running(),
            "restart_count": restart_count,
            "last_restart": last_restart_time,
            "last_update": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        }
        
        with open(STATUS_FILE, 'w') as f:
            json.dump(status, f, indent=2)
    except Exception as e:
        logging.error(f"خطأ في حفظ حالة النظام: {e}")

def check_system_status():
    """التحقق من حالة النظام وإعداد تقرير شامل."""
    heartbeat_age = get_heartbeat_age()
    bot_running = check_bot_running()
    
    # التحقق من عملية البوت
    bot_process_status = "غير معروف"
    if bot_process:
        if bot_process.poll() is None:
            bot_process_status = "نشط"
        else:
            bot_process_status = f"متوقف (كود الخروج: {bot_process.poll()})"
    
    # جمع معلومات النظام
    system_info = {
        "meminfo": {
            "total": 0,
            "free": 0,
            "used": 0
        },
        "cpu_usage": 0
    }
    
    try:
        import psutil
        memory = psutil.virtual_memory()
        system_info["meminfo"] = {
            "total": memory.total / (1024 * 1024),  # MB
            "free": memory.available / (1024 * 1024),  # MB
            "used": memory.used / (1024 * 1024)  # MB
        }
        system_info["cpu_usage"] = psutil.cpu_percent(interval=1)
    except ImportError:
        pass
    
    return {
        "status": "ok" if bot_running else "error",
        "heartbeat": {
            "age_seconds": heartbeat_age,
            "last_update": time.time() - heartbeat_age
        },
        "bot": {
            "script": BOT_SCRIPT,
            "running": bot_running,
            "process_status": bot_process_status,
            "restart_count": restart_count,
            "last_restart": last_restart_time
        },
        "system": system_info,
        "timestamp": time.time()
    }

def signal_handler(sig, frame):
    """معالج إشارات النظام لإيقاف النظام بشكل آمن."""
    global keep_alive_running
    
    logging.info("تم استلام إشارة إيقاف. جاري إيقاف النظام...")
    keep_alive_running = False
    
    # إيقاف البوت
    stop_bot()
    
    # حفظ الحالة النهائية
    save_status()
    
    logging.info("تم إيقاف النظام بنجاح!")
    sys.exit(0)

def main():
    """الوظيفة الرئيسية للسكريبت."""
    global keep_alive_running
    
    # تسجيل معالجات الإشارات
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    print("🤖 نظام الحفاظ على استمرارية البوت 🤖")
    print("====================================")
    
    try:
        # إنشاء المجلدات المطلوبة
        os.makedirs("data", exist_ok=True)
        
        # بدء خادم KeepAlive
        server = start_keep_alive_server()
        if not server:
            logging.error("فشل في بدء خادم الحفاظ على النشاط!")
            return
        
        # بدء تشغيل البوت
        if not start_bot():
            logging.error("فشل في بدء تشغيل البوت!")
            return
        
        # بدء مراقبة البوت في خيط منفصل
        monitor_thread = threading.Thread(target=monitor_bot)
        monitor_thread.daemon = True
        monitor_thread.start()
        
        print("✅ تم بدء نظام الحفاظ على استمرارية البوت بنجاح!")
        print(f"📌 خادم الحفاظ على النشاط يعمل على المنفذ {KEEP_ALIVE_PORT}")
        print(f"📌 البوت يعمل باستخدام: {BOT_SCRIPT}")
        print(f"📌 تتم مراقبة البوت كل {CHECK_INTERVAL} ثانية")
        print(f"📌 مهلة نبضات القلب: {HEARTBEAT_TIMEOUT} ثانية")
        print()
        print("ℹ️ اضغط Ctrl+C لإيقاف النظام")
        
        # إرسال إشعار بدء التشغيل
        notify_admin("🚀 تم بدء نظام الحفاظ على استمرارية البوت بنجاح!")
        
        # الانتظار حتى يتم إيقاف النظام
        while keep_alive_running:
            time.sleep(1)
    except KeyboardInterrupt:
        print("\nتم استلام طلب إيقاف من المستخدم...")
    except Exception as e:
        logging.error(f"خطأ غير متوقع: {e}")
    finally:
        # إيقاف النظام بأمان
        keep_alive_running = False
        stop_bot()
        logging.info("تم إيقاف نظام الحفاظ على استمرارية البوت")
        print("👋 تم إيقاف نظام الحفاظ على استمرارية البوت. مع السلامة!")

if __name__ == "__main__":
    main()