#!/usr/bin/env python3
"""
أداة تحضير نشر بوت التيليجرام على Replit Deployments
تقوم هذه الأداة بتحضير المشروع للنشر على Replit Deployments بتنفيذ الخطوات الآتية:
- التحقق من تكوين البوت الصحيح
- التحقق من توفر التوكن وصحته
- تنظيف الملفات المؤقتة وملفات السجلات القديمة
- إنشاء نسخة احتياطية من قاعدة البيانات
- التحقق من نظام قفل المثيل
"""
import os
import sys
import json
import shutil
import logging
import datetime
import subprocess
from typing import List, Dict, Any, Optional

# إعدادات التسجيل
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# المجلدات التي يجب تنظيفها
CLEANUP_DIRS = [
    "logs",
    "temp_media",
]

# امتدادات ملفات السجلات للتنظيف
LOG_EXTENSIONS = [
    ".log",
    ".log.1",
    ".log.2",
    ".log.3",
]

# ملفات العلامات المؤقتة التي يجب حذفها
MARKER_FILES = [
    "bot_shutdown_marker",
    "watchdog_ping",
    "force_restart",
    "restart_requested.log",
]

# ملفات قاعدة البيانات للنسخ الاحتياطي
DB_FILES = [
    "data/notifications.json",
    "data/admins.json",
    "data/delivery_confirmations.json",
    "data/permissions.json",
    "data/search_history.json",
    "data/settings.json",
    "data/marketing_campaigns.json",
    "data/theme_settings.json",
]

def check_bot_token() -> bool:
    """
    التحقق من توفر وصحة توكن البوت
    
    العوائد:
        True إذا كان التوكن صحيح، False خلاف ذلك
    """
    logger.info("التحقق من توكن البوت...")
    
    # التحقق من التكوين الموحد
    try:
        from unified_config import get_bot_token
        token = get_bot_token()
        logger.info("✅ تم الحصول على التوكن من نظام التكوين الموحد")
        
        if not token:
            logger.error("❌ التوكن فارغ في نظام التكوين الموحد")
            return False
            
        # التحقق من صحة التوكن
        if ":" not in token:
            logger.error("❌ تنسيق التوكن غير صحيح (يجب أن يحتوي على ':')")
            return False
            
        logger.info("✅ تنسيق التوكن يبدو صحيحاً")
        return True
    except ImportError:
        logger.warning("⚠️ لم يتم العثور على نظام التكوين الموحد، جاري التحقق من متغيرات البيئة...")
        
        # التحقق من متغيرات البيئة
        token = os.environ.get("TELEGRAM_BOT_TOKEN")
        if not token:
            logger.error("❌ لم يتم تعيين متغير البيئة TELEGRAM_BOT_TOKEN")
            return False
            
        # التحقق من صحة التوكن
        if ":" not in token:
            logger.error("❌ تنسيق التوكن غير صحيح (يجب أن يحتوي على ':')")
            return False
            
        logger.info("✅ تنسيق التوكن يبدو صحيحاً")
        return True
    except Exception as e:
        logger.error(f"❌ خطأ في التحقق من التوكن: {e}")
        return False

def cleanup_old_logs() -> int:
    """
    تنظيف ملفات السجلات القديمة
    
    العوائد:
        عدد الملفات التي تم حذفها
    """
    logger.info("تنظيف ملفات السجلات القديمة...")
    count = 0
    
    # تنظيف المجلدات
    for dir_path in CLEANUP_DIRS:
        if not os.path.exists(dir_path):
            continue
            
        for filename in os.listdir(dir_path):
            file_path = os.path.join(dir_path, filename)
            
            # التحقق من امتداد الملف
            if any(filename.endswith(ext) for ext in LOG_EXTENSIONS):
                try:
                    os.remove(file_path)
                    logger.info(f"✅ تم حذف الملف: {file_path}")
                    count += 1
                except Exception as e:
                    logger.error(f"❌ خطأ في حذف الملف {file_path}: {e}")
    
    # حذف ملفات العلامات المؤقتة
    for marker_file in MARKER_FILES:
        if os.path.exists(marker_file):
            try:
                os.remove(marker_file)
                logger.info(f"✅ تم حذف ملف العلامة: {marker_file}")
                count += 1
            except Exception as e:
                logger.error(f"❌ خطأ في حذف ملف العلامة {marker_file}: {e}")
    
    logger.info(f"✅ تم حذف {count} ملف خلال عملية التنظيف")
    return count

def backup_database() -> bool:
    """
    إنشاء نسخة احتياطية من قاعدة البيانات
    
    العوائد:
        True إذا تمت النسخة الاحتياطية بنجاح، False خلاف ذلك
    """
    logger.info("إنشاء نسخة احتياطية من قاعدة البيانات...")
    
    # إنشاء مجلد النسخ الاحتياطي إذا لم يكن موجوداً
    backup_dir = "backup"
    if not os.path.exists(backup_dir):
        os.makedirs(backup_dir)
    
    # الحصول على الطابع الزمني
    timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_path = os.path.join(backup_dir, f"db_backup_{timestamp}")
    os.makedirs(backup_path, exist_ok=True)
    
    # نسخ ملفات قاعدة البيانات
    for db_file in DB_FILES:
        if os.path.exists(db_file):
            try:
                # إنشاء المجلدات المطلوبة
                dest_file = os.path.join(backup_path, os.path.basename(db_file))
                dest_dir = os.path.dirname(dest_file)
                if not os.path.exists(dest_dir):
                    os.makedirs(dest_dir)
                
                # نسخ الملف
                shutil.copy2(db_file, dest_file)
                logger.info(f"✅ تم نسخ {db_file} إلى {dest_file}")
            except Exception as e:
                logger.error(f"❌ خطأ في نسخ {db_file}: {e}")
                return False
    
    logger.info(f"✅ تم إنشاء نسخة احتياطية من قاعدة البيانات في: {backup_path}")
    return True

def check_instance_lock() -> bool:
    """
    التحقق من نظام قفل المثيل
    
    العوائد:
        True إذا كان نظام قفل المثيل يعمل بشكل صحيح، False خلاف ذلك
    """
    logger.info("التحقق من نظام قفل المثيل...")
    
    try:
        import instance_lock
        logger.info("✅ تم استيراد وحدة قفل المثيل بنجاح")
        return True
    except ImportError:
        logger.error("❌ لم يتم العثور على وحدة قفل المثيل")
        return False
    except Exception as e:
        logger.error(f"❌ خطأ في التحقق من نظام قفل المثيل: {e}")
        return False

def check_bot_config() -> bool:
    """
    التحقق من ملفات تكوين البوت
    
    العوائد:
        True إذا كان التكوين صحيحاً، False خلاف ذلك
    """
    logger.info("التحقق من ملفات تكوين البوت...")
    
    # التحقق من وجود ملف تكوين البوت
    config_file = "bot_config.json"
    if not os.path.exists(config_file):
        logger.warning(f"⚠️ ملف التكوين {config_file} غير موجود")
        return False
    
    # التحقق من صحة ملف التكوين
    try:
        with open(config_file, "r") as f:
            config_data = json.load(f)
            
        # التحقق من وجود التوكن في التكوين
        if "bot_token" not in config_data:
            logger.error("❌ لم يتم العثور على bot_token في ملف التكوين")
            return False
            
        # التحقق من وجود إعدادات القوالب
        if "message_template" not in config_data:
            logger.warning("⚠️ لم يتم العثور على message_template في ملف التكوين")
            
        if "welcome_template" not in config_data:
            logger.warning("⚠️ لم يتم العثور على welcome_template في ملف التكوين")
            
        logger.info("✅ تم التحقق من ملف التكوين بنجاح")
        return True
    except Exception as e:
        logger.error(f"❌ خطأ في قراءة ملف التكوين: {e}")
        return False

def main():
    """الدالة الرئيسية لتحضير النشر"""
    logger.info("=== بدء تحضير النشر على Replit Deployments ===")
    
    # التحقق من توكن البوت
    if not check_bot_token():
        logger.error("❌ فشل التحقق من توكن البوت، يرجى تصحيح المشكلة قبل النشر")
        return False
    
    # التحقق من تكوين البوت
    if not check_bot_config():
        logger.warning("⚠️ هناك مشكلة في تكوين البوت، قد يؤدي ذلك إلى مشاكل بعد النشر")
    
    # التحقق من نظام قفل المثيل
    if not check_instance_lock():
        logger.error("❌ نظام قفل المثيل غير متوفر، هذا قد يؤدي إلى تشغيل عدة مثيلات من البوت")
        return False
    
    # إنشاء نسخة احتياطية من قاعدة البيانات
    if not backup_database():
        logger.error("❌ فشل إنشاء نسخة احتياطية من قاعدة البيانات")
        return False
    
    # تنظيف ملفات السجلات القديمة
    cleanup_old_logs()
    
    logger.info("✅ تم تحضير المشروع للنشر بنجاح!")
    logger.info("الخطوات التالية:")
    logger.info("1. انقر على زر [Deploy] في واجهة Replit")
    logger.info("2. انتظر اكتمال عملية النشر")
    logger.info("3. قم بالوصول إلى البوت المنشور عبر الرابط المقدم")
    
    return True

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)