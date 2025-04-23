#!/usr/bin/env python
"""
سكريبت إعداد نظام Always-On لبوت تيليجرام

هذا السكريبت يقوم بتكوين البيئة اللازمة لتشغيل البوت في وضع Always-On
على منصة Replit مع ضمان استمراريته حتى بعد إغلاق متصفح Replit
"""

import os
import sys
import json
import logging
import subprocess
import shutil
from pathlib import Path
from datetime import datetime

# إعداد السجلات
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger('AlwaysOnSetup')

# القيم الافتراضية
TEMPLATE_FOLDER = "templates"
CONFIG_FILE = "bot_config.json"
BOT_TOKEN = "7406580104:AAGG2JQeeNfsmcGVMCm7hxitIK-qm2yekVg"  # التوكن المضمن
REPLIT_FILE = ".replit"
REPLIT_NIX_FILE = "replit.nix"

def create_directory_if_not_exists(directory):
    """إنشاء مجلد إذا لم يكن موجودًا"""
    try:
        os.makedirs(directory, exist_ok=True)
        logger.info(f"✅ تم التأكد من وجود المجلد: {directory}")
        return True
    except Exception as e:
        logger.error(f"❌ خطأ في إنشاء المجلد {directory}: {e}")
        return False

def update_env_file():
    """تحديث ملف البيئة .env"""
    try:
        env_content = f"""# ملف متغيرات البيئة لنظام بوت تيليجرام مع Always-On
# تم تحديثه بواسطة سكريبت always_on_setup.py في {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

# تفعيل وضع Always-On
USE_ALWAYS_ON=True

# توكن بوت تيليجرام
TELEGRAM_BOT_TOKEN={BOT_TOKEN}
"""
        with open(".env", "w", encoding="utf-8") as f:
            f.write(env_content)
            
        logger.info("✅ تم تحديث ملف البيئة .env بنجاح")
        return True
    except Exception as e:
        logger.error(f"❌ خطأ في تحديث ملف البيئة .env: {e}")
        return False

def update_bot_config():
    """تحديث أو إنشاء ملف تكوين البوت"""
    try:
        if os.path.exists(CONFIG_FILE):
            # تحميل التكوين الحالي
            with open(CONFIG_FILE, 'r', encoding='utf-8') as f:
                config = json.load(f)
            
            # تحديث التوكن والتكوين
            config["bot_token"] = BOT_TOKEN
            config["LAST_UPDATED"] = datetime.now().isoformat()
            config["USE_ALWAYS_ON"] = True
            
            # إضافة أي بيانات تكوين مهمة أخرى
            if "HEARTBEAT_INTERVAL" not in config:
                config["HEARTBEAT_INTERVAL"] = 15
            if "TELEGRAM_PING_INTERVAL" not in config:
                config["TELEGRAM_PING_INTERVAL"] = 10
            if "MONITOR_CHECK_INTERVAL" not in config:
                config["MONITOR_CHECK_INTERVAL"] = 60
        else:
            # إنشاء ملف تكوين جديد
            config = {
                "bot_token": BOT_TOKEN,
                "HEARTBEAT_INTERVAL": 15,
                "TELEGRAM_PING_INTERVAL": 10,
                "MONITOR_CHECK_INTERVAL": 60,
                "MAX_HEARTBEAT_AGE": 120,
                "HEARTBEAT_FILE": "bot_heartbeat.txt",
                "LOGS_DIR": "logs",
                "TEMP_MEDIA_DIR": "temp_media",
                "DATA_DIR": "data",
                "MEMORY_CHECK_INTERVAL": 3600,
                "MEMORY_THRESHOLD": 200,
                "LOG_MAX_SIZE": 10485760,
                "LOG_BACKUP_COUNT": 5,
                "API_RETRY_COUNT": 5,
                "API_RETRY_DELAY": 1,
                "API_RETRY_BACKOFF_FACTOR": 2,
                "ENVIRONMENT": "production",
                "DEBUG": False,
                "BOT_VERSION": "1.0.0",
                "USE_ALWAYS_ON": True,
                "LAST_UPDATED": datetime.now().isoformat()
            }
        
        # حفظ التكوين
        with open(CONFIG_FILE, 'w', encoding='utf-8') as f:
            json.dump(config, f, indent=4, ensure_ascii=False)
            
        logger.info(f"✅ تم تحديث ملف تكوين البوت {CONFIG_FILE} بنجاح")
        return True
    except Exception as e:
        logger.error(f"❌ خطأ في تحديث ملف تكوين البوت: {e}")
        return False

def check_required_files():
    """التحقق من وجود الملفات الضرورية وإنشاؤها إذا لزم الأمر"""
    required_files = [
        "combined_app.py",
        "main_combined.py",
        "custom_bot_adapter.py",
        "start_combined_app.sh"
    ]
    
    missing_files = []
    for file in required_files:
        if not os.path.exists(file):
            missing_files.append(file)
    
    if missing_files:
        logger.warning(f"⚠️ الملفات التالية غير موجودة: {', '.join(missing_files)}")
        return False
    else:
        logger.info("✅ جميع الملفات الضرورية موجودة")
        return True

def make_script_executable(script_path):
    """جعل الملف النصي قابل للتنفيذ"""
    try:
        subprocess.run(["chmod", "+x", script_path], check=True)
        logger.info(f"✅ تم جعل الملف {script_path} قابل للتنفيذ")
        return True
    except Exception as e:
        logger.error(f"❌ خطأ في جعل الملف {script_path} قابل للتنفيذ: {e}")
        return False

def update_heartbeat_file():
    """تحديث ملف نبضات القلب"""
    try:
        with open("bot_heartbeat.txt", "w") as f:
            f.write(str(datetime.now().timestamp()))
        logger.info("✅ تم تحديث ملف نبضات القلب")
        return True
    except Exception as e:
        logger.error(f"❌ خطأ في تحديث ملف نبضات القلب: {e}")
        return False

def main():
    """الوظيفة الرئيسية للسكريبت"""
    logger.info("==== بدء إعداد نظام Always-On لبوت تيليجرام ====")
    
    # التأكد من وجود المجلدات الضرورية
    create_directory_if_not_exists("logs")
    create_directory_if_not_exists("data")
    create_directory_if_not_exists("temp_media")
    create_directory_if_not_exists(TEMPLATE_FOLDER)
    
    # تحديث ملفات التكوين
    update_env_file()
    update_bot_config()
    
    # التحقق من الملفات المطلوبة
    if not check_required_files():
        logger.error("❌ بعض الملفات الضرورية غير موجودة. الرجاء إعادة تنفيذ عملية التثبيت")
        return False
    
    # جعل السكريبت قابل للتنفيذ
    make_script_executable("start_combined_app.sh")
    
    # تحديث ملف نبضات القلب
    update_heartbeat_file()
    
    logger.info("==== تم الانتهاء من إعداد نظام Always-On بنجاح! ====")
    logger.info("➡️ لبدء تشغيل النظام الموحد، استخدم الأمر التالي:")
    logger.info("./start_combined_app.sh")
    
    print("\n\n")
    print("✅ تم إعداد نظام Always-On بنجاح!")
    print("➡️ لبدء تشغيل النظام الموحد، استخدم الأمر التالي:")
    print("./start_combined_app.sh")
    print("\n")
    
    return True

if __name__ == "__main__":
    main()