#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
نقطة الدخول الرئيسية لبوت تيليجرام المميز - مُحسن للاستمرارية 24/7

هذا الملف مصمم خصيصاً للعمل مع Replit Always-On، حيث يجمع بين:
1. تشغيل البوت في خيط منفصل 
2. تشغيل خادم Flask في العملية الرئيسية
3. دعم للمراقبة الخارجية

⭐ ميزات هذا الإصدار:
- استمرارية 24/7 حتى بعد إغلاق متصفح Replit
- دعم خدمات المراقبة الخارجية (UptimeRobot)
- معالجة أخطاء الإغلاق المفاجئ
- تكامل مع نظام المراقبة الداخلي
- تجنب مشاكل asyncio في الخيوط
"""

import os
import sys
import time
import logging
import threading
import atexit
import signal
from datetime import datetime
from flask import Flask, render_template, redirect, jsonify

# التأكد من وجود المجلدات اللازمة
os.makedirs('logs', exist_ok=True)
os.makedirs('data', exist_ok=True)
os.makedirs('temp_media', exist_ok=True)
os.makedirs('templates', exist_ok=True)

# إعداد السجلات
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler("logs/start_bot.log")
    ]
)
logger = logging.getLogger("start_bot")

# إنشاء تطبيق Flask
app = Flask(__name__)

# ملف نبضات القلب
HEARTBEAT_FILE = "bot_heartbeat.txt"
PID_FILE = "bot_process.pid"
bot_thread = None
bot_start_time = None

def update_heartbeat():
    """تحديث ملف نبضات القلب"""
    try:
        with open(HEARTBEAT_FILE, "w") as f:
            f.write(str(time.time()))
    except Exception as e:
        logger.error(f"خطأ في تحديث ملف نبضات القلب: {e}")

def create_pid_file():
    """إنشاء ملف PID"""
    with open(PID_FILE, "w") as f:
        f.write(str(os.getpid()))
    logger.info(f"تم إنشاء ملف PID: {os.getpid()}")

def cleanup():
    """تنظيف الموارد عند الخروج"""
    logger.info("تنظيف الموارد قبل الخروج...")
    try:
        if os.path.exists(PID_FILE):
            os.remove(PID_FILE)
    except Exception as e:
        logger.error(f"خطأ في تنظيف الموارد: {e}")

def signal_handler(sig, frame):
    """معالج الإشارات"""
    logger.info(f"تم استلام إشارة: {sig}")
    cleanup()
    sys.exit(0)

def is_bot_running():
    """التحقق من حالة البوت"""
    try:
        if not os.path.exists(HEARTBEAT_FILE):
            return False, "No heartbeat file"
            
        with open(HEARTBEAT_FILE, "r") as f:
            timestamp = f.read().strip()
            
        try:
            last_heartbeat = datetime.fromtimestamp(float(timestamp))
            diff = (datetime.now() - last_heartbeat).total_seconds()
            
            # اعتبار البوت نشطًا إذا كان آخر نبضة قلب خلال 3 دقائق
            if diff < 180:
                return True, last_heartbeat.strftime("%Y-%m-%d %H:%M:%S")
            else:
                return False, last_heartbeat.strftime("%Y-%m-%d %H:%M:%S") + f" (last seen {int(diff/60)} min ago)"
                
        except (ValueError, TypeError) as e:
            logger.error(f"خطأ في تحليل الطابع الزمني: {e}")
            return False, "Invalid timestamp format"
                
    except Exception as e:
        logger.error(f"خطأ عام في التحقق من حالة البوت: {e}")
        return False, str(e)

def run_bot():
    """تشغيل البوت في خيط منفصل"""
    global bot_start_time
    
    logger.info("بدء تشغيل البوت في خيط منفصل...")
    bot_start_time = datetime.now()
    
    # تحديث ملف نبضات القلب
    update_heartbeat()
    
    try:
        # استيراد وحدة main - ستقوم بتشغيل البوت وخادم Flask
        import main
        
        # بدء تشغيل وظيفة init - سيقوم بتهيئة النظام وبدء البوت
        result = main.init()
        logger.info(f"نتيجة تشغيل البوت: {result}")
        
    except Exception as e:
        logger.error(f"خطأ في تشغيل البوت: {e}")
        import traceback
        logger.error(traceback.format_exc())

@app.route('/')
def home():
    """الصفحة الرئيسية"""
    bot_status, last_heartbeat = is_bot_running()
    
    # حساب وقت التشغيل
    uptime = "غير متاح"
    if bot_start_time:
        uptime_duration = datetime.now() - bot_start_time
        days = uptime_duration.days
        hours, remainder = divmod(uptime_duration.seconds, 3600)
        minutes, seconds = divmod(remainder, 60)
        
        if days > 0:
            uptime = f"{days} يوم, {hours} ساعة, {minutes} دقيقة"
        elif hours > 0:
            uptime = f"{hours} ساعة, {minutes} دقيقة"
        else:
            uptime = f"{minutes} دقيقة, {seconds} ثانية"
    
    # تحديث ملف نبضات القلب عند زيارة الصفحة
    update_heartbeat()
    
    # إرجاع نص بسيط
    return f"""
    <html>
    <head>
        <title>Bot Status - Always On</title>
        <meta http-equiv="refresh" content="30">
        <style>
            body {{ font-family: Arial, sans-serif; margin: 40px; line-height: 1.6; }}
            .container {{ max-width: 800px; margin: 0 auto; }}
            h1 {{ color: #4285f4; }}
            .status {{ padding: 10px; border-radius: 3px; margin: 20px 0; }}
            .running {{ background-color: #d4edda; color: #155724; }}
            .stopped {{ background-color: #f8d7da; color: #721c24; }}
        </style>
    </head>
    <body>
        <div class="container">
            <h1>Telegram Bot Status - Always On</h1>
            <div class="status {'running' if bot_status else 'stopped'}">
                <strong>Status:</strong> {'Running' if bot_status else 'Stopped'}
            </div>
            <div>
                <strong>Last Heartbeat:</strong> {last_heartbeat}
            </div>
            <div>
                <strong>Uptime:</strong> {uptime}
            </div>
            <div>
                <strong>Generated at:</strong> {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}
            </div>
            <div>
                <p>
                    <a href="/ping">Ping Server</a> | 
                    <a href="/health">Check Health</a> | 
                    <a href="/restart-bot">Restart Bot</a>
                </p>
            </div>
        </div>
    </body>
    </html>
    """

@app.route('/ping')
def ping():
    """نقطة نهاية بسيطة للاستجابة إلى خدمات المراقبة مثل UptimeRobot"""
    # تحديث ملف نبضات القلب عند كل ping
    update_heartbeat()
    return "pong", 200

@app.route('/health')
def health():
    """نقطة نهاية تفصيلية لحالة البوت"""
    bot_running, last_heartbeat = is_bot_running()
    return jsonify({
        'status': 'ok' if bot_running else 'error',
        'running': bot_running,
        'last_heartbeat': last_heartbeat,
        'timestamp': datetime.now().isoformat()
    }), 200 if bot_running else 503

@app.route('/restart-bot')
def restart_bot():
    """إعادة تشغيل البوت"""
    try:
        # استيراد وحدة التكامل
        import custom_bot_adapter
        
        # إيقاف البوت الحالي
        custom_bot_adapter.stop_bot_thread()
        
        # انتظار قليلاً
        time.sleep(1)
        
        # إعادة تشغيل البوت
        success = custom_bot_adapter.start_bot_thread()
        
        if success:
            return "تم إعادة تشغيل البوت بنجاح", 200
        else:
            return "فشل في إعادة تشغيل البوت", 500
    except Exception as e:
        logger.error(f"خطأ في إعادة تشغيل البوت: {e}")
        return str(e), 500

def main():
    """الوظيفة الرئيسية"""
    # إعداد معالجات الإشارات
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    # تسجيل وظيفة التنظيف عند الخروج
    atexit.register(cleanup)
    
    # إنشاء ملف PID
    create_pid_file()
    
    # تحديث ملف نبضات القلب
    update_heartbeat()
    
    # بدء تشغيل البوت في خيط منفصل
    global bot_thread
    bot_thread = threading.Thread(target=run_bot)
    bot_thread.daemon = True
    bot_thread.start()
    
    # تشغيل خادم Flask في العملية الرئيسية
    logger.info("بدء تشغيل خادم Flask على المنفذ 5000")
    app.run(host='0.0.0.0', port=5000)

if __name__ == "__main__":
    main()