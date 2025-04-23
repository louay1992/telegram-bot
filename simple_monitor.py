#!/usr/bin/env python3
"""
مراقب بسيط لسير العمل - يعمل باستمرار للتأكد من استمرار عمل التطبيق والبوت
تصميم بسيط ومباشر لضمان الثبات
"""

import os
import time
import subprocess
import requests
import logging
from datetime import datetime

# إعداد التسجيل
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler("monitor.log")
    ]
)

def check_web_server():
    """التحقق مما إذا كان خادم الويب Flask يعمل"""
    try:
        # التحقق أولاً من API ping
        try:
            response = requests.get("http://localhost:5000/api/ping", timeout=3)
            if response.status_code == 200:
                logging.info("✅ خادم الويب يعمل (نقطة النهاية ping تستجيب)")
                return True
        except Exception:
            pass
        
        # التحقق من وجود عملية gunicorn
        result = subprocess.run("ps aux | grep -v grep | grep -E 'gunicorn'", 
                               shell=True, capture_output=True, text=True)
        if "gunicorn" in result.stdout:
            logging.info("✅ خادم الويب يعمل (عملية gunicorn موجودة)")
            return True
            
        logging.warning("❌ خادم الويب متوقف")
        return False
    except Exception as e:
        logging.error(f"خطأ أثناء التحقق من خادم الويب: {e}")
        return False

def check_telegram_bot():
    """التحقق مما إذا كان بوت تيليجرام يعمل"""
    try:
        # التحقق من وجود عملية بوت تيليجرام
        result = subprocess.run("ps aux | grep -v grep | grep 'python' | grep 'bot.py'", 
                               shell=True, capture_output=True, text=True)
        if result.stdout.strip():
            logging.info("✅ بوت تيليجرام يعمل")
            return True
            
        logging.warning("❌ بوت تيليجرام متوقف")
        return False
    except Exception as e:
        logging.error(f"خطأ أثناء التحقق من بوت تيليجرام: {e}")
        return False

def restart_web_server():
    """إعادة تشغيل خادم الويب Flask"""
    try:
        logging.info("🔄 محاولة إعادة تشغيل خادم الويب...")
        
        # إيقاف أي نسخة قائمة
        subprocess.run("pkill -f 'gunicorn'", shell=True)
        time.sleep(2)
        
        # بدء تشغيل جديد
        subprocess.Popen(
            "gunicorn --bind 0.0.0.0:5000 --reuse-port --reload main:app",
            shell=True, 
            stdout=open("web_server_stdout.log", "a"),
            stderr=open("web_server_stderr.log", "a")
        )
        
        # انتظار للتأكد من بدء التشغيل
        time.sleep(5)
        
        # التحقق من نجاح إعادة التشغيل
        if check_web_server():
            logging.info("✅ تم إعادة تشغيل خادم الويب بنجاح")
            return True
        else:
            logging.error("❌ فشل في إعادة تشغيل خادم الويب")
            return False
    except Exception as e:
        logging.error(f"خطأ أثناء إعادة تشغيل خادم الويب: {e}")
        return False

def restart_telegram_bot():
    """إعادة تشغيل بوت تيليجرام"""
    try:
        logging.info("🔄 محاولة إعادة تشغيل بوت تيليجرام...")
        
        # إيقاف أي نسخة قائمة
        subprocess.run("pkill -f 'python.*bot.py'", shell=True)
        time.sleep(2)
        
        # بدء تشغيل جديد
        subprocess.Popen(
            "python bot.py", 
            shell=True, 
            stdout=open("bot_stdout.log", "a"),
            stderr=open("bot_stderr.log", "a")
        )
        
        # انتظار للتأكد من بدء التشغيل
        time.sleep(5)
        
        # التحقق من نجاح إعادة التشغيل
        if check_telegram_bot():
            logging.info("✅ تم إعادة تشغيل بوت تيليجرام بنجاح")
            return True
        else:
            logging.error("❌ فشل في إعادة تشغيل بوت تيليجرام")
            return False
    except Exception as e:
        logging.error(f"خطأ أثناء إعادة تشغيل بوت تيليجرام: {e}")
        return False

def main():
    """الوظيفة الرئيسية للمراقب"""
    logging.info("🚀 بدء تشغيل مراقب سير العمل البسيط...")
    
    # طباعة معلومات البيئة
    logging.info(f"🔍 الدليل الحالي: {os.getcwd()}")
    
    # إنشاء ملف PID
    with open("simple_monitor.pid", "w") as f:
        f.write(str(os.getpid()))
    logging.info(f"📝 تم كتابة PID {os.getpid()} إلى simple_monitor.pid")
    
    check_interval = 30  # فحص كل 30 ثانية
    
    try:
        run_count = 0
        while True:
            run_count += 1
            logging.info(f"🔄 دورة فحص #{run_count} - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
            
            # التحقق من خادم الويب
            if not check_web_server():
                restart_web_server()
            
            # التحقق من بوت تيليجرام
            if not check_telegram_bot():
                restart_telegram_bot()
            
            # انتظار قبل الفحص التالي
            logging.info(f"⏱️ انتظار {check_interval} ثانية حتى الفحص التالي...")
            time.sleep(check_interval)
    except KeyboardInterrupt:
        logging.info("👋 تم إيقاف المراقب بواسطة المستخدم")
    except Exception as e:
        logging.error(f"❌ حدث خطأ عام في المراقب: {e}")
    finally:
        # تنظيف ملف PID عند الخروج
        if os.path.exists("simple_monitor.pid"):
            os.remove("simple_monitor.pid")
            logging.info("🧹 تم تنظيف ملف PID")

if __name__ == "__main__":
    main()