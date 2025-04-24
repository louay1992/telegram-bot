import os
import sys
import logging
import psutil
import threading
import time
import asyncio
from datetime import datetime
from flask import Flask, render_template, jsonify, request, send_from_directory
from app_config import BOT_TOKEN, USE_ALWAYS_ON, FLASK_SECRET_KEY, setup_logging
from telegram import Update
from telegram.ext import Application
from bot import build_application
from telegram.ext import Application, CommandHandler, ContextTypes
from telegram import Update

# تعريف دالة الرد على أمر /start
async def start_command_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("مرحباً! تم تفعيل البوت بنجاح.")

# دالة بناء التطبيق وإضافة الـ handlers

def build_application():
    application = Application.builder().token(config.TELEGRAM_BOT_TOKEN).build()

    # إضافة الأمر /start
    application.add_handler(CommandHandler("start", start_command_handler))

    # إضافة جميع الـ handlers المستوردة
    for handler in (
        get_admin_handlers(),
        get_search_handlers(),
        get_stats_handlers(),
        get_delivery_handlers(),
        get_search_history_handler(),
        get_filter_handler(),
        get_advanced_search_handler(),
        get_permissions_handlers(),
        get_theme_handlers(),
        get_backup_handlers(),
        get_personality_handlers(),
        get_ai_handlers(),
        get_marketing_campaign_handlers(),
    ):
        application.add_handlers(handler if isinstance(handler, list) else [handler])

    return application

# إعداد السجلات
logger = setup_logging()

# إنشاء التطبيق الأساسي
TOKEN = BOT_TOKEN
logger.info(f"USE_ALWAYS_ON = {USE_ALWAYS_ON}")
logger.info(f"TELEGRAM_BOT_TOKEN = {TOKEN[:5]}...{TOKEN[-5:]}")

if not os.path.exists("logs"):
    os.makedirs("logs", exist_ok=True)

app = Flask(__name__)
app.secret_key = FLASK_SECRET_KEY

application: Application = build_application()

# --- Webhook Setup ---
async def init_webhook_once():
    webhook_url = os.getenv("WEBHOOK_URL")
    if not webhook_url:
        logger.warning("❌ لم يتم العثور على WEBHOOK_URL في المتغيرات البيئية.")
        return
    try:
        await application.initialize()
        await application.bot.set_webhook(webhook_url)
        logger.info(f"✅ Webhook تم تعيينه إلى: {webhook_url}")
    except Exception as e:
        logger.error(f"❌ فشل في تعيين Webhook: {e}")

@app.post("/webhook")
async def handle_webhook():
    if request.headers.get("Content-Type") == "application/json":
        data = request.get_json(force=True)
        update = Update.de_json(data, application.bot)
        await application.process_update(update)
    return "ok"

# --- System Utilities ---
visit_count = 0
bot_start_time = None

@app.route('/')
def index():
    global visit_count
    visit_count += 1
    return "Bot is running ✅", 200

@app.route('/api/ping')
def ping():
    return jsonify({"status": "ok", "service": "telegram-bot", "timestamp": datetime.utcnow().isoformat() + "Z"})

@app.route('/media/<path:filename>')
def serve_media(filename):
    media_folder = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'data/images')
    return send_from_directory(media_folder, filename)

def init():
    os.makedirs('logs', exist_ok=True)
    os.makedirs('data', exist_ok=True)
    os.makedirs('temp_media', exist_ok=True)
    os.makedirs('templates', exist_ok=True)
    try:
        with open("bot_heartbeat.txt", "w") as f:
            f.write(datetime.now().isoformat())
    except Exception as e:
        logger.error(f"❌ خطأ في إنشاء ملف نبضات القلب: {e}")

if __name__ == "__main__":
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    loop.run_until_complete(init_webhook_once())
    loop.close()

    threading.Thread(target=init).start()
    app.run(host='0.0.0.0', port=5000)

# متغيرات عامة
visit_count = 0
bot_start_time = None
bot_thread = None

def update_heartbeat():
    """تحديث ملف نبضات القلب"""
    try:
        with open("bot_heartbeat.txt", "w") as f:
            f.write(datetime.now().isoformat())
    except Exception as e:
        logger.error(f"خطأ في تحديث ملف نبضات القلب: {e}")

def start_bot_thread():
    """بدء تشغيل البوت في خيط منفصل"""
    global bot_start_time, bot_thread
    
    try:
        # استيراد الوحدات اللازمة
        import custom_bot_adapter
        
        # تعيين وقت بدء التشغيل
        bot_start_time = datetime.now()
        
        # بدء تشغيل البوت
        custom_bot_adapter.start_bot_thread()
        
        logger.info("✅ تم بدء تشغيل البوت بنجاح في خيط منفصل")
        return True
    except Exception as e:
        logger.error(f"❌ فشل في بدء تشغيل البوت: {e}")
        import traceback
        logger.error(traceback.format_exc())
        return False

def get_uptime():
    """حساب وقت تشغيل النظام"""
    if bot_start_time is None:
        return "غير متاح"
    
    uptime = datetime.now() - bot_start_time
    days = uptime.days
    hours, remainder = divmod(uptime.seconds, 3600)
    minutes, seconds = divmod(remainder, 60)
    
    if days > 0:
        return f"{days} يوم, {hours} ساعة, {minutes} دقيقة"
    elif hours > 0:
        return f"{hours} ساعة, {minutes} دقيقة"
    else:
        return f"{minutes} دقيقة, {seconds} ثانية"

def get_heartbeat_status():
    """قراءة حالة نبضات القلب"""
    try:
        heartbeat_file = "bot_heartbeat.txt"
        if not os.path.exists(heartbeat_file):
            logger.warning("ملف نبضات القلب غير موجود")
            return "غير متاح"
            
        with open(heartbeat_file, 'r') as f:
            timestamp = f.read().strip()
            
        logger.info(f"محتوى ملف نبضات القلب: {timestamp}")
            
        try:
            # محاولة تحليل الطابع الزمني بصيغة ISO
            last_heartbeat = datetime.fromisoformat(timestamp)
            logger.info(f"تم تحليل الطابع الزمني بصيغة ISO: {last_heartbeat}")
        except ValueError:
            try:
                # إذا كان التنسيق قديمًا (timestamp)
                last_heartbeat = datetime.fromtimestamp(float(timestamp))
                logger.info(f"تم تحليل الطابع الزمني بصيغة timestamp: {last_heartbeat}")
            except (ValueError, TypeError) as e:
                logger.error(f"خطأ في تحليل الطابع الزمني: {e}")
                return f"تنسيق غير صالح: {timestamp[:20]}..."
            
        time_diff = datetime.now() - last_heartbeat
        seconds_diff = time_diff.total_seconds()
        logger.info(f"الفرق الزمني: {seconds_diff:.2f} ثانية")
        
        # زيادة المدة المسموح بها قبل اعتبار البوت متوقفًا متوافقة مع cron.toml
        if seconds_diff < 180:  # أقل من 3 دقائق
            return last_heartbeat.strftime("%Y-%m-%d %H:%M:%S") + " (نشط)"
        else:
            minutes = int(seconds_diff / 60)
            return last_heartbeat.strftime("%Y-%m-%d %H:%M:%S") + f" (متوقف منذ {minutes} دقيقة)"
    except Exception as e:
        logger.error(f"خطأ في التحقق من حالة نبضات القلب: {e}")
        import traceback
        logger.error(traceback.format_exc())
        return "غير متاح بسبب خطأ"

def get_notification_count():
    """الحصول على عدد الإشعارات المخزنة"""
    try:
        # محاولة استيراد وحدة قاعدة البيانات
        import database
        notifications = database.get_all_notifications()
        return len(notifications)
    except Exception as e:
        logger.error(f"خطأ في الحصول على عدد الإشعارات: {e}")
        return "غير متاح"

def get_system_info():
    """الحصول على معلومات النظام"""
    try:
        # قراءة معلومات المعالج والذاكرة
        cpu_percent = psutil.cpu_percent(interval=0.1)
        memory = psutil.virtual_memory()
        memory_percent = memory.percent
        disk = psutil.disk_usage('/')
        disk_percent = disk.percent
        
        return {
            "cpu_percent": cpu_percent,
            "memory_percent": memory_percent,
            "memory_used": f"{memory.used / (1024 * 1024):.2f} MB",
            "memory_total": f"{memory.total / (1024 * 1024):.2f} MB",
            "disk_percent": disk_percent,
            "disk_used": f"{disk.used / (1024 * 1024 * 1024):.2f} GB",
            "disk_total": f"{disk.total / (1024 * 1024 * 1024):.2f} GB"
        }
    except Exception as e:
        logger.error(f"خطأ في الحصول على معلومات النظام: {e}")
        return {
            "cpu_percent": 0,
            "memory_percent": 0,
            "memory_used": "غير متاح",
            "memory_total": "غير متاح",
            "disk_percent": 0,
            "disk_used": "غير متاح",
            "disk_total": "غير متاح"
        }

def is_bot_running():
    """التحقق مما إذا كان البوت يعمل"""
    try:
        # تحقق أولاً من ملف نبضات القلب مباشرة لتحسين الدقة
        heartbeat_file = "bot_heartbeat.txt"
        if os.path.exists(heartbeat_file):
            try:
                with open(heartbeat_file, 'r') as f:
                    timestamp = f.read().strip()
                
                if timestamp:
                    try:
                        # محاولة تحليل الطابع الزمني
                        try:
                            last_heartbeat = datetime.fromisoformat(timestamp)
                        except ValueError:
                            last_heartbeat = datetime.fromtimestamp(float(timestamp))
                        
                        time_diff = (datetime.now() - last_heartbeat).total_seconds()
                        # زيادة المدة المسموح بها متوافقة مع cron.toml
                        if time_diff < 180:  # أقل من 3 دقائق
                            logger.info(f"البوت يعمل (آخر نبضة قبل {time_diff:.2f} ثانية)")
                            return True
                    except (ValueError, TypeError) as e:
                        logger.error(f"خطأ في تحليل ملف نبضات القلب: {e}")
            except Exception as e:
                logger.error(f"خطأ في قراءة ملف نبضات القلب: {e}")
        
        # كخطة بديلة، استخدم محول البوت المخصص
        try:
            import custom_bot_adapter
            bot_state = custom_bot_adapter.is_bot_running()
            logger.info(f"حالة البوت من محول البوت المخصص: {bot_state}")
            return bot_state
        except Exception as e:
            logger.error(f"خطأ في استدعاء محول البوت المخصص: {e}")
            
            # إجراء آخر - نتحقق من workflow
            try:
                process = os.popen("ps aux | grep telegram_bot | grep -v grep").read()
                if "bot.py" in process or "python" in process:
                    logger.info("تم العثور على عملية البوت في workflow")
                    return True
            except Exception as e:
                logger.error(f"خطأ في التحقق من عملية البوت: {e}")
                
            return False
    except Exception as e:
        logger.error(f"خطأ عام في التحقق من حالة البوت: {e}")
        import traceback
        logger.error(traceback.format_exc())
        return False

@app.route('/')
def index():
    """الصفحة الرئيسية"""
    global visit_count
    visit_count += 1
    
    # حصول على معلمة الوقت لمنع التخزين المؤقت (إن وجدت)
    timestamp = request.args.get('t', '')
    logger.info(f"طلب الصفحة الرئيسية مع معلمة t={timestamp}")
    
    # فحص ملف نبضات القلب مباشرة
    try:
        heartbeat_file = "bot_heartbeat.txt"
        if os.path.exists(heartbeat_file):
            with open(heartbeat_file, 'r') as f:
                timestamp_content = f.read().strip()
            logger.info(f"التحقق المباشر من ملف نبضات القلب: {timestamp_content}")
    except Exception as e:
        logger.error(f"خطأ في التحقق المباشر من ملف نبضات القلب: {e}")
    
    # التحقق من حالة البوت
    bot_running = is_bot_running()
    status_class = "status-ok" if bot_running else "status-error"
    
    # الحصول على معلومات النظام
    system_info = get_system_info()
    
    # تحديد آخر تحديث لنبضات القلب
    last_heartbeat = get_heartbeat_status()
    
    # وضع مزيد من السجلات للتشخيص
    logger.info(f"حالة البوت: {bot_running}")
    logger.info(f"آخر نبضة قلب: {last_heartbeat}")
    
    # تحضير بيانات القالب
    template_data = {
        "bot_status": bot_running,
        "status_class": status_class,
        "last_update": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "uptime": get_uptime(),
        "last_heartbeat": last_heartbeat,
        "system_info": system_info,
        "notification_count": get_notification_count(),
        "visit_count": visit_count,
        "always_on": USE_ALWAYS_ON,
        "bot_token": f"{TOKEN[:5]}...{TOKEN[-5:]}"
    }
    
    # تعيين رؤوس HTTP لمنع التخزين المؤقت - طريقة أخرى أكثر توافقية
    resp = render_template('status.html', **template_data)
    return resp, 200, {
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
        logger.error(f"خطأ في إعادة تشغيل البوت: {e}")
        import traceback
        logger.error(traceback.format_exc())
        return jsonify({
            "status": "error",
            "message": f"حدث خطأ: {str(e)}"
        }), 500

@app.route('/health')
def health_check():
    """نقطة نهاية لفحص الصحة - للاستخدام مع UptimeRobot"""
    # التحقق من حالة البوت
    bot_running = is_bot_running()
    
    if bot_running:
        return jsonify({"status": "healthy", "message": "البوت يعمل بشكل صحيح"}), 200
    else:
        # حتى لو كان البوت متوقفًا، نرجع حالة 200 لتجنب إعادة تشغيل Replit
        # UptimeRobot سيستمر في الاتصال وسيعمل نظام permanent_bot على إعادة تشغيل البوت
        return jsonify({"status": "warning", "message": "البوت متوقف"}), 200

@app.route('/api/ping')
def ping():
    """نقطة تحقق بسيطة لاختبار جاهزية السيرفر"""
    return jsonify({
        "status": "ok",
        "service": "telegram-bot",
        "timestamp": datetime.utcnow().isoformat() + "Z"
    }), 200

@app.route('/api/status')
def api_status():
    """واجهة برمجة التطبيقات لعرض حالة النظام"""
    # التحقق من حالة البوت
    bot_running = is_bot_running()
    system_info = get_system_info()
    
    return jsonify({
        "status": "ok" if bot_running else "error",
        "bot_running": bot_running,
        "last_heartbeat": get_heartbeat_status(),
        "uptime": get_uptime(),
        "system_info": system_info,
        "notification_count": get_notification_count()
    })

@app.route('/media/<path:filename>')
def serve_media(filename):
    """تقديم ملفات الوسائط"""
    media_folder = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'data/images')
    return send_from_directory(media_folder, filename)

def init():
    """تهيئة النظام"""
    # التأكد من وجود المجلدات الضرورية
    os.makedirs('logs', exist_ok=True)
    os.makedirs('data', exist_ok=True)
    os.makedirs('temp_media', exist_ok=True)
    os.makedirs('templates', exist_ok=True)
    
    # تحديث ملف نبضات القلب
    update_heartbeat()
    
    # بدء تشغيل البوت
    start_bot_thread()
    
    return app

import threading

def run_bot():
    """تشغيل البوت في خيط منفصل"""
    import bot
    # استخدام bot.py مباشرة بدلاً من custom_bot_adapter
    bot.start_bot()


    # تشغيل السيرفر
    threading.Thread(target=init).start()
    app.run(host='0.0.0.0', port=5000)
    

    # تعيين Webhook داخل event loop الرئيسي
    async def startup():
        webhook_url = os.getenv("WEBHOOK_URL")
        if not webhook_url:
            logger.warning("❌ لم يتم العثور على WEBHOOK_URL في المتغيرات البيئية.")
            return
        try:
            await application.initialize()
            await application.bot.set_webhook(webhook_url)
            logger.info(f"✅ Webhook تم تعيينه إلى: {webhook_url}")
        except Exception as e:
            logger.error(f"❌ فشل في تعيين Webhook: {e}")

    asyncio.run(startup())

    # تشغيل خادم Flask
    app.run(host='0.0.0.0', port=5000)
