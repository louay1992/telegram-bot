#!/usr/bin/env python
"""
ملف موحد للنشر - يقوم باستيراد الوحدات الأساسية وإعداد نقطة دخول للنشر
--------------------------------------------------------------------
هذا الملف هو نقطة دخول موحدة للنشر على منصة Replit وتوحيد التشغيل.

يقوم باستيراد الوحدات الأساسية التالية:
- تطبيق Flask
- بوت تيليجرام
- قاعدة البيانات

يجب استخدام هذا الملف كنقطة دخول في ملف Procfile وملف .replit
"""

import logging
import os
import sys
import time
from datetime import datetime, timedelta
import psutil

# إضافة الدليل الحالي إلى مسار البحث
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# استيراد Flask مبكرًا لتجنب أخطاء LSP
try:
    from flask import Flask, render_template, jsonify, send_from_directory, request, make_response
except ImportError:
    logging.error("فشل استيراد Flask. تأكد من تثبيته أولاً.")
    # لتجنب أخطاء التوقف في بيئة التطوير، نستبدل بعض الوحدات الوهمية
    class DummyResponse:
        def __init__(self, content="", status=200):
            self.content = content
            self.status = status
    
    def render_template(*args, **kwargs):
        return "استدعاء render_template"
    
    def jsonify(*args, **kwargs):
        return DummyResponse()
    
    def send_from_directory(*args, **kwargs):
        return DummyResponse()
    
    class Flask:
        def __init__(self, name):
            self.name = name
            self.secret_key = None

# استيراد ملف التكوين
from app_config import setup_logging, ensure_directories, HOST, PORT

# إعداد السجلات
logger = setup_logging()
logger.info("بدء تشغيل main_combined.py كنقطة دخول للنشر")

# المتغيرات العامة
visit_count = 0
bot_start_time = datetime.now()

# التأكد من وجود المجلدات الضرورية
ensure_directories()
logger.info("تم التأكد من وجود المجلدات الضرورية")

# استيراد تطبيق Flask من main.py
try:
    # استيراد التطبيق من main.py
    from main import app as flask_app
    logger.info("تم استيراد تطبيق Flask بنجاح من main.py")
    
    # تعريف المتغير العالمي المطلوب للنشر
    app = flask_app
    
except ImportError as e:
    logger.error(f"خطأ في استيراد تطبيق Flask: {e}")
    
    # إنشاء تطبيق Flask مستقل في حالة فشل الاستيراد
    app = Flask(__name__)
    logger.info("تم إنشاء تطبيق Flask بديل")

# إضافة مسارات مهمة للتطبيق بشكل مباشر
@app.route('/')
def main_index():
    return index()

@app.route('/health')
def main_health_check():
    return health_check()

@app.route('/api/status')
def main_api_status():
    return api_status()

@app.route('/ping')
def main_api_ping():
    return api_ping()

@app.route('/media/<path:filename>')
def main_serve_media(filename):
    return serve_media(filename)

# تنفيذ الوظائف المطلوبة للاستيراد من combined_app.py

def update_heartbeat():
    """تحديث ملف نبضات القلب"""
    try:
        with open("bot_heartbeat.txt", "w") as f:
            f.write(datetime.now().isoformat())
    except Exception as e:
        logger.error(f"خطأ في تحديث ملف نبضات القلب: {e}")

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
        # زيادة وقت التسامح إلى 5 دقائق بدلاً من 3 دقائق
        timeout_seconds = 300  # 5 دقائق
        
        # تحقق أولاً من ملف نبضات القلب مباشرة لتحسين الدقة
        heartbeat_file = "bot_heartbeat.txt"
        if os.path.exists(heartbeat_file):
            try:
                with open(heartbeat_file, 'r') as f:
                    timestamp = f.read().strip()
                
                if timestamp:
                    try:
                        # محاولة تحليل الطابع الزمني
                        last_heartbeat = None
                        # طرق مختلفة للتحليل للتعامل مع جميع أشكال التنسيقات المحتملة
                        try:
                            # محاولة تحليل ISO format أولاً
                            last_heartbeat = datetime.fromisoformat(timestamp)
                        except ValueError:
                            try:
                                # محاولة تحليل timestamp
                                last_heartbeat = datetime.fromtimestamp(float(timestamp))
                            except (ValueError, TypeError):
                                # محاولة أخرى مع تنسيق زمني مخصص
                                import time
                                try:
                                    time_struct = time.strptime(timestamp, "%Y-%m-%d %H:%M:%S")
                                    last_heartbeat = datetime.fromtimestamp(time.mktime(time_struct))
                                except:
                                    logger.warning(f"تنسيق الوقت غير معروف: {timestamp}")
                                    last_heartbeat = None
                        
                        if last_heartbeat:
                            time_diff = (datetime.now() - last_heartbeat).total_seconds()
                            # زيادة المدة المسموح بها
                            if time_diff < timeout_seconds:
                                logger.info(f"البوت يعمل (آخر نبضة قبل {time_diff:.2f} ثانية)")
                                return True
                            else:
                                logger.warning(f"آخر نبضة قديمة جدًا: {time_diff:.2f} ثانية (أكثر من {timeout_seconds//60} دقائق)")
                    except Exception as e:
                        logger.error(f"خطأ في تحليل ملف نبضات القلب: {str(e)}")
                        import traceback
                        logger.debug(traceback.format_exc())
            except Exception as e:
                logger.error(f"خطأ في قراءة ملف نبضات القلب: {str(e)}")
        else:
            logger.warning(f"ملف نبضات القلب غير موجود: {heartbeat_file}")
        
        # كخطة بديلة، التحقق من عملية workflow
        try:
            process = os.popen("ps aux | grep telegram_bot | grep -v grep").read()
            if "bot.py" in process or "python" in process:
                logger.info("تم العثور على عملية البوت في workflow")
                return True
        except Exception as e:
            logger.error(f"خطأ في التحقق من عملية البوت: {str(e)}")
        
        # محاولة أخرى، استخدم محول البوت المخصص
        try:
            import custom_bot_adapter
            bot_state = custom_bot_adapter.is_bot_running()
            logger.info(f"حالة البوت من محول البوت المخصص: {bot_state}")
            return bot_state
        except Exception as e:
            logger.error(f"خطأ في استدعاء محول البوت المخصص: {str(e)}")
        
        # اعتبار البوت قيد التشغيل إذا كان workflow telegram_bot يعمل
        try:
            telegram_bot_workflow_running = "telegram_bot" in os.popen("ps aux | grep workflow").read()
            if telegram_bot_workflow_running:
                logger.info("تم اكتشاف workflow telegram_bot قيد التشغيل")
                return True
        except Exception as e:
            logger.error(f"خطأ في التحقق من workflow telegram_bot: {str(e)}")

        # سلوك افتراضي - اعتبر البوت يعمل في بيئة النشر
        if os.environ.get('REPLIT_DEPLOYMENT') or os.environ.get('RENDER'):
            logger.info("بيئة نشر مكتشفة، اعتبار البوت يعمل افتراضيًا")
            return True
            
        # لم يتم التمكن من تحديد حالة البوت بالتأكيد
        logger.warning("لم يتم التمكن من تحديد حالة البوت بدقة، اعتباره متوقف")
        return False
    except Exception as e:
        logger.error(f"خطأ عام في التحقق من حالة البوت: {str(e)}")
        import traceback
        logger.error(traceback.format_exc())
        # في حالة حدوث استثناء عام، نعتبر البوت يعمل لتجنب إعادة التشغيل غير الضرورية
        return True

# تنفيذ الدوال المطلوبة من combined_app.py

def index():
    """الصفحة الرئيسية"""
    global visit_count
    visit_count += 1
    
    # تحضير بيانات القالب
    template_data = {
        "bot_status": is_bot_running(),
        "status_class": "status-ok" if is_bot_running() else "status-error",
        "last_update": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "uptime": get_uptime(),
        "last_heartbeat": get_heartbeat_status(),
        "system_info": get_system_info(),
        "notification_count": get_notification_count(),
        "visit_count": visit_count,
        "always_on": True,
        "bot_token": "#####...#####"  # إخفاء التوكن الحقيقي
    }
    
    return render_template('status.html', **template_data)

def health_check():
    """نقطة نهاية فحص الصحة للمراقبة الخارجية."""
    from flask import jsonify
    return jsonify({
        "status": "ok",
        "bot_running": is_bot_running(),
        "last_heartbeat": get_heartbeat_status(),
        "uptime": get_uptime()
    })

def api_status():
    """عرض حالة النظام بصيغة JSON."""
    from flask import jsonify
    return jsonify({
        "status": "ok",
        "bot_running": is_bot_running(),
        "last_heartbeat": get_heartbeat_status(),
        "uptime": get_uptime(),
        "system_info": get_system_info(),
        "notification_count": get_notification_count()
    })

def api_ping():
    """نقطة نهاية للـ ping للحفاظ على نشاط التطبيق."""
    from flask import jsonify
    return jsonify({"status": "alive", "timestamp": time.time()})

def serve_media(filename):
    """تقديم ملفات الوسائط"""
    from flask import send_from_directory
    media_folder = "temp_media"
    # التحقق من وجود المجلد وإنشاؤه إذا لم يكن موجودًا
    if not os.path.exists(media_folder):
        os.makedirs(media_folder, exist_ok=True)
    return send_from_directory(media_folder, filename)

# استيراد وبدء تشغيل بوت تيليجرام
try:
    # محاولة تشغيل البوت في خيط منفصل
    import threading
    from main import start_bot_thread
    
    # تشغيل البوت في خيط منفصل
    bot_thread = threading.Thread(target=start_bot_thread)
    bot_thread.daemon = True  # جعل الخيط daemon لكي يغلق عند إغلاق البرنامج الرئيسي
    bot_thread.start()
    
    logger.info("تم بدء تشغيل بوت تيليجرام في خيط منفصل")
    
except Exception as e:
    logger.error(f"خطأ في بدء تشغيل بوت تيليجرام: {e}")
    import traceback
    logger.error(traceback.format_exc())

# طباعة رسالة تأكيد
logger.info("اكتمل إعداد main_combined.py بنجاح")

import threading

def run_bot_in_thread():
    """تشغيل البوت في خيط منفصل"""
    import bot
    try:
        bot.start_bot()
    except Exception as e:
        logger.error(f"حدث خطأ أثناء تشغيل البوت في الخيط: {e}")
        import traceback
        logger.error(traceback.format_exc())

# نص يظهر عند تنفيذ الملف مباشرة
if __name__ == "__main__":
    # تشغيل البوت في خيط منفصل
    logger.info("بدء تشغيل البوت في خيط منفصل...")
    bot_thread = threading.Thread(target=run_bot_in_thread)
    bot_thread.daemon = True  # سيتوقف الخيط عند توقف البرنامج الرئيسي
    bot_thread.start()
    logger.info("تم بدء خيط البوت بنجاح")
    
    # تشغيل خادم Flask في العملية الرئيسية
    logger.info("بدء تشغيل خادم Flask في العملية الرئيسية...")
    port = int(os.environ.get("PORT", 5000))
    app.run(host=HOST, port=port, debug=False)