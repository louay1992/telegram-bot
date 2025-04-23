"""
مراقب سير العمل - يحافظ على استمرار تشغيل التطبيق والبوت

هذا السكريبت يقوم بمراقبة حالة سير العمل (workflows) ويعيد تشغيلها
إذا توقفت عن العمل، مما يساعد على ضمان توفر البوت حتى عند إغلاق صفحة Replit.
"""

import os
import sys
import time
import logging
import json
import subprocess
import requests
from datetime import datetime, timedelta

# ضمان وجود المجلد للسجلات
LOG_DIR = "logs"
if not os.path.exists(LOG_DIR):
    os.makedirs(LOG_DIR)

# إعداد التسجيل
LOG_FILE = os.path.join(LOG_DIR, "workflow_monitor.log")
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler(LOG_FILE)
    ]
)
logger = logging.getLogger("workflow_monitor")

# قائمة بـ workflows التي يجب مراقبتها
WORKFLOWS = [
    "Start application",
    "telegram_bot"
]

# مسار ملف حالة المراقبة
STATUS_FILE = os.path.join(LOG_DIR, "workflow_monitor_status.json")

# عدد محاولات إعادة التشغيل قبل الانتظار
MAX_RESTART_ATTEMPTS = 3

# فترة الانتظار (بالثواني) بعد وصول عدد المحاولات إلى الحد الأقصى
COOLDOWN_PERIOD = 1800  # 30 دقيقة

# فترة الفحص (بالثواني)
CHECK_INTERVAL = 60  # فحص كل دقيقة

def get_workflow_status(workflow_name):
    """
    التحقق من حالة سير العمل (workflow)

    يستخدم هذا طريقة بسيطة لفحص ما إذا كان سير العمل يعمل
    من خلال محاولة فحص عمليات النظام
    """
    try:
        logger.debug(f"التحقق من حالة {workflow_name}...")
        # إذا كان workflow_name هو "Start application"، تحقق من توفر الخادم
        if workflow_name == "Start application":
            try:
                # محاولة إرسال طلب ping إلى خادم Flask
                response = requests.get("http://localhost:5000/api/ping", timeout=3)
                if response.status_code == 200:
                    logger.debug(f"نقطة نهاية Ping لـ {workflow_name} تستجيب بشكل طبيعي")
                    return True
            except Exception as e:
                logger.debug(f"نقطة نهاية Ping لـ {workflow_name} لا تستجيب: {e}")
                # في حالة فشل الطلب، افترض أن سير العمل متوقف لكن استمر في الفحص
                pass
        
        # تحقق من العمليات القائمة
        if workflow_name == "Start application":
            # ابحث عن عمليات gunicorn أو Flask
            result = subprocess.run("ps aux | grep -v grep | grep -E 'gunicorn|main.py|flask'", 
                                   shell=True, capture_output=True, text=True)
            output = result.stdout.strip()
            if output and ("gunicorn" in output or "main.py" in output or "flask" in output):
                logger.debug(f"عملية {workflow_name} موجودة: {output[:100]}...")
                return True
        elif workflow_name == "telegram_bot":
            # ابحث عن عمليات تشغيل بوت تيليجرام
            result = subprocess.run("ps aux | grep -v grep | grep 'python' | grep 'bot.py'", 
                                   shell=True, capture_output=True, text=True)
            output = result.stdout.strip()
            if output:
                logger.debug(f"عملية {workflow_name} موجودة: {output[:100]}...")
                return True
        
        logger.debug(f"لم يتم العثور على عملية {workflow_name}")
        return False
    
    except Exception as e:
        logger.error(f"خطأ أثناء التحقق من حالة سير العمل {workflow_name}: {e}")
        return False

def restart_workflow(workflow_name):
    """
    إعادة تشغيل سير العمل (workflow)
    """
    try:
        if workflow_name == "Start application":
            # إعادة تشغيل خادم الويب Flask
            logger.info(f"محاولة إعادة تشغيل {workflow_name}...")
            
            # إيقاف أي نسخة قائمة
            try:
                logger.debug("محاولة إيقاف أي عمليات قائمة لخادم الويب...")
                subprocess.run("pkill -f 'gunicorn|main.py|flask'", shell=True)
                time.sleep(2)
            except Exception as e:
                logger.warning(f"خطأ عند محاولة إيقاف عمليات خادم الويب: {e}")
            
            # بدء تشغيل جديد
            try:
                logger.debug("بدء تشغيل خادم الويب...")
                subprocess.Popen(
                    "gunicorn --bind 0.0.0.0:5000 --reuse-port --reload main:app",
                    shell=True, 
                    stdout=open(os.path.join(LOG_DIR, "gunicorn_stdout.log"), "a"),
                    stderr=open(os.path.join(LOG_DIR, "gunicorn_stderr.log"), "a")
                )
                time.sleep(5)  # انتظار قليلاً للتأكد من بدء التشغيل
                
                # التحقق من نجاح إعادة التشغيل
                if get_workflow_status(workflow_name):
                    logger.info(f"تم إعادة تشغيل {workflow_name} بنجاح")
                    return True
                else:
                    logger.warning(f"تم تشغيل الأمر لكن {workflow_name} لم يبدأ بنجاح")
            except Exception as e:
                logger.error(f"خطأ عند محاولة بدء تشغيل خادم الويب: {e}")
        
        elif workflow_name == "telegram_bot":
            # إعادة تشغيل بوت تيليجرام
            logger.info(f"محاولة إعادة تشغيل {workflow_name}...")
            
            # إيقاف أي نسخة قائمة
            try:
                logger.debug("محاولة إيقاف أي عمليات قائمة للبوت...")
                subprocess.run("pkill -f 'python.*bot.py'", shell=True)
                time.sleep(2)
            except Exception as e:
                logger.warning(f"خطأ عند محاولة إيقاف عمليات البوت: {e}")
            
            # بدء تشغيل جديد
            try:
                logger.debug("بدء تشغيل البوت...")
                subprocess.Popen(
                    "python bot.py", 
                    shell=True, 
                    stdout=open(os.path.join(LOG_DIR, "bot_stdout.log"), "a"),
                    stderr=open(os.path.join(LOG_DIR, "bot_stderr.log"), "a")
                )
                time.sleep(5)  # انتظار قليلاً للتأكد من بدء التشغيل
                
                # التحقق من نجاح إعادة التشغيل
                if get_workflow_status(workflow_name):
                    logger.info(f"تم إعادة تشغيل {workflow_name} بنجاح")
                    return True
                else:
                    logger.warning(f"تم تشغيل الأمر لكن {workflow_name} لم يبدأ بنجاح")
            except Exception as e:
                logger.error(f"خطأ عند محاولة بدء تشغيل البوت: {e}")
    
    except Exception as e:
        logger.error(f"خطأ أثناء إعادة تشغيل {workflow_name}: {e}")
    
    return False

def load_status():
    """
    تحميل حالة المراقبة من الملف
    """
    try:
        if os.path.exists(STATUS_FILE):
            try:
                with open(STATUS_FILE, 'r') as f:
                    return json.load(f)
            except Exception as e:
                logger.error(f"خطأ أثناء قراءة ملف الحالة: {e}")
    except Exception as e:
        logger.error(f"خطأ عام أثناء محاولة تحميل الحالة: {e}")
    
    # إنشاء بنية افتراضية في حالة عدم وجود الملف أو حدوث خطأ
    return {
        "last_check": datetime.now().isoformat(),
        "workflows": {
            workflow: {
                "running": False,
                "restart_attempts": 0,
                "last_restart_attempt": None,
                "cooldown_until": None
            } for workflow in WORKFLOWS
        }
    }

def save_status(status):
    """
    حفظ حالة المراقبة إلى ملف
    """
    try:
        with open(STATUS_FILE, 'w') as f:
            json.dump(status, f, indent=2)
        logger.debug("تم حفظ ملف الحالة بنجاح")
    except Exception as e:
        logger.error(f"خطأ أثناء حفظ ملف الحالة: {e}")

def check_and_restart_workflows():
    """
    التحقق من حالة جميع سير العمل وإعادة تشغيلها إذا لزم الأمر
    """
    try:
        status = load_status()
        now = datetime.now()
        status["last_check"] = now.isoformat()
        
        for workflow_name in WORKFLOWS:
            workflow_status = status["workflows"][workflow_name]
            
            # التحقق مما إذا كان في فترة التهدئة
            if workflow_status.get("cooldown_until"):
                cooldown_until = datetime.fromisoformat(workflow_status["cooldown_until"])
                if now < cooldown_until:
                    logger.info(f"{workflow_name} في فترة التهدئة حتى {cooldown_until.isoformat()}")
                    continue
                else:
                    # انتهت فترة التهدئة
                    logger.info(f"انتهت فترة التهدئة لـ {workflow_name}. استئناف المراقبة.")
                    workflow_status["cooldown_until"] = None
                    workflow_status["restart_attempts"] = 0
            
            # التحقق من حالة سير العمل
            is_running = get_workflow_status(workflow_name)
            workflow_status["running"] = is_running
            
            if not is_running:
                logger.warning(f"{workflow_name} متوقف. محاولة إعادة التشغيل...")
                
                # زيادة عداد محاولات إعادة التشغيل
                workflow_status["restart_attempts"] += 1
                workflow_status["last_restart_attempt"] = now.isoformat()
                
                # محاولة إعادة التشغيل
                restart_success = restart_workflow(workflow_name)
                
                if restart_success:
                    logger.info(f"تم إعادة تشغيل {workflow_name} بنجاح")
                    workflow_status["restart_attempts"] = 0
                else:
                    logger.error(f"فشل في إعادة تشغيل {workflow_name}")
                    
                    # التحقق من عدد محاولات إعادة التشغيل
                    if workflow_status["restart_attempts"] >= MAX_RESTART_ATTEMPTS:
                        logger.warning(f"تم الوصول إلى الحد الأقصى من محاولات إعادة التشغيل لـ {workflow_name}. الدخول في فترة التهدئة.")
                        cooldown_until = now + timedelta(seconds=COOLDOWN_PERIOD)
                        workflow_status["cooldown_until"] = cooldown_until.isoformat()
            else:
                logger.info(f"{workflow_name} يعمل بشكل طبيعي")
                # إعادة تعيين عداد المحاولات إذا كان يعمل
                if workflow_status["restart_attempts"] > 0:
                    workflow_status["restart_attempts"] = 0
                    logger.info(f"إعادة تعيين عداد محاولات إعادة التشغيل لـ {workflow_name} لأنه يعمل الآن")
        
        # حفظ الحالة
        save_status(status)
    except Exception as e:
        logger.error(f"خطأ عام أثناء فحص وإعادة تشغيل workflows: {e}")

def run_monitor():
    """
    تشغيل حلقة المراقبة
    """
    logger.info("بدء مراقب سير العمل...")
    logger.info(f"سيتم حفظ السجلات في: {LOG_FILE}")
    logger.info(f"فترة الفحص: {CHECK_INTERVAL} ثانية")
    
    # طباعة حالة الـ workflows الحالية
    for workflow_name in WORKFLOWS:
        is_running = get_workflow_status(workflow_name)
        status_text = "يعمل" if is_running else "متوقف"
        logger.info(f"الحالة الأولية لـ {workflow_name}: {status_text}")
    
    try:
        # كتابة PID الخاص بالعملية إلى ملف، تجنب المشاكل إذا كان الملف موجودًا بالفعل
        with open("monitor.pid", "w") as f:
            f.write(str(os.getpid()))
        logger.info(f"تم كتابة PID {os.getpid()} إلى monitor.pid")
        
        # حلقة المراقبة الرئيسية
        while True:
            logger.info("بدء دورة فحص جديدة...")
            check_and_restart_workflows()
            logger.info(f"اكتملت دورة الفحص. انتظار {CHECK_INTERVAL} ثانية...")
            # انتظار قبل الفحص التالي
            time.sleep(CHECK_INTERVAL)
    except KeyboardInterrupt:
        logger.info("تم إيقاف مراقب سير العمل بواسطة المستخدم")
    except Exception as e:
        logger.error(f"حدث خطأ عام في حلقة المراقبة: {e}")
    finally:
        # إزالة ملف PID عند الخروج
        try:
            if os.path.exists("monitor.pid"):
                os.remove("monitor.pid")
                logger.info("تم إزالة ملف monitor.pid")
        except Exception as e:
            logger.error(f"خطأ أثناء محاولة إزالة ملف monitor.pid: {e}")

if __name__ == "__main__":
    run_monitor()