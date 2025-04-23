"""
نظام النسخ الاحتياطي التلقائي لقاعدة البيانات.

يقوم هذا السكريبت بإنشاء نسخة احتياطية لقاعدة البيانات بشكل دوري
للحفاظ على البيانات من الفقدان في حالة حدوث مشاكل في النظام.

يمكن تشغيل هذا السكريبت يدوياً أو من خلال مجدول المهام:
- للتشغيل اليدوي: python auto_backup.py
- يفضل دمجه مع نظام المراقبة لضمان النسخ الاحتياطي بشكل تلقائي

الخصائص:
- إنشاء نسخة احتياطية لقاعدة البيانات SQLite
- ضغط النسخة الاحتياطية لتوفير المساحة
- الاحتفاظ بعدد محدد من النسخ الاحتياطية
- سجل تفصيلي للعمليات المنفذة
"""

import os
import sys
import time
import shutil
import logging
import datetime
import sqlite3
import zipfile
import json
from pathlib import Path

# إعداد التسجيل
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("backup.log"),
        logging.StreamHandler(sys.stdout)
    ]
)

logger = logging.getLogger("BackupSystem")

# إعدادات عامة
DB_FILE = "shipping_bot.db"              # ملف قاعدة البيانات
BACKUP_DIR = "backup"                    # مجلد النسخ الاحتياطية
MAX_BACKUPS = 10                         # الحد الأقصى للنسخ الاحتياطية المحتفظ بها
BACKUP_INTERVAL = 24 * 60 * 60           # فترة النسخ الاحتياطي (24 ساعة)
BACKUP_METRICS_FILE = "backup_metrics.json"  # ملف إحصائيات النسخ الاحتياطي


def ensure_backup_dir():
    """التأكد من وجود مجلد النسخ الاحتياطية."""
    if not os.path.exists(BACKUP_DIR):
        try:
            os.makedirs(BACKUP_DIR)
            logger.info(f"تم إنشاء مجلد النسخ الاحتياطية: {BACKUP_DIR}")
        except Exception as e:
            logger.error(f"خطأ في إنشاء مجلد النسخ الاحتياطية: {e}")
            return False
    return True


def create_backup_filename():
    """إنشاء اسم ملف النسخة الاحتياطية."""
    timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    return f"backup_{timestamp}.zip"


def backup_database():
    """إنشاء نسخة احتياطية من قاعدة البيانات."""
    # التأكد من وجود مجلد النسخ الاحتياطية
    if not ensure_backup_dir():
        return False, "فشل في إنشاء مجلد النسخ الاحتياطية"

    # التأكد من وجود ملف قاعدة البيانات
    if not os.path.exists(DB_FILE):
        logger.error(f"ملف قاعدة البيانات غير موجود: {DB_FILE}")
        return False, f"ملف قاعدة البيانات غير موجود: {DB_FILE}"

    # إنشاء ملف النسخة الاحتياطية
    backup_filename = create_backup_filename()
    backup_path = os.path.join(BACKUP_DIR, backup_filename)

    try:
        # نسخ قاعدة البيانات أولاً إلى ملف مؤقت للتأكد من عدم تغييرها أثناء النسخ
        temp_db = f"{DB_FILE}_temp"
        
        # إذا كانت قاعدة البيانات مفتوحة، استخدم اتصال مباشر لعمل نسخة احتياطية
        try:
            # محاولة استخدام sqlite3 لإنشاء نسخة احتياطية
            conn = sqlite3.connect(DB_FILE)
            backup_conn = sqlite3.connect(temp_db)
            conn.backup(backup_conn)
            conn.close()
            backup_conn.close()
            logger.info(f"تم نسخ قاعدة البيانات إلى ملف مؤقت: {temp_db}")
        except Exception as backup_error:
            # في حالة فشل النسخ المباشر، استخدم النسخ العادي
            logger.warning(f"فشل النسخ المباشر، جاري استخدام النسخ العادي: {backup_error}")
            shutil.copy2(DB_FILE, temp_db)
            logger.info(f"تم نسخ قاعدة البيانات بطريقة عادية إلى ملف مؤقت: {temp_db}")
        
        # إنشاء ملف ZIP مع الملفات المهمة
        with zipfile.ZipFile(backup_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
            # إضافة قاعدة البيانات
            zipf.write(temp_db, os.path.basename(DB_FILE))
            
            # إضافة ملفات التكوين المهمة إن وجدت
            config_files = [
                "config.py",
                "strings.py",
                "restart_log.json"
            ]
            
            for config_file in config_files:
                if os.path.exists(config_file):
                    zipf.write(config_file, config_file)
            
            # إضافة مجلدات المحتوى إن وجدت
            content_dirs = [
                "temp_media"
            ]
            
            for content_dir in content_dirs:
                if os.path.exists(content_dir):
                    for root, _, files in os.walk(content_dir):
                        for file in files:
                            file_path = os.path.join(root, file)
                            zipf.write(file_path, file_path)
        
        # حذف الملف المؤقت
        if os.path.exists(temp_db):
            os.remove(temp_db)
        
        # التحقق من حجم النسخة الاحتياطية
        backup_size = os.path.getsize(backup_path)
        logger.info(f"تم إنشاء نسخة احتياطية بنجاح: {backup_path} (الحجم: {backup_size / 1024:.2f} كيلوبايت)")
        
        # تسجيل معلومات النسخة الاحتياطية
        update_backup_metrics(backup_filename, backup_size)
        
        # حذف النسخ الاحتياطية القديمة إذا تجاوز العدد الحد الأقصى
        cleanup_old_backups()
        
        return True, backup_path
    
    except Exception as e:
        logger.error(f"خطأ في إنشاء النسخة الاحتياطية: {e}")
        import traceback
        logger.error(traceback.format_exc())
        return False, f"خطأ في إنشاء النسخة الاحتياطية: {e}"


def update_backup_metrics(backup_filename, backup_size):
    """تحديث إحصائيات النسخ الاحتياطية."""
    metrics_path = os.path.join(BACKUP_DIR, BACKUP_METRICS_FILE)
    metrics = {
        "backups": [],
        "last_backup": "",
        "total_backups": 0,
        "total_size": 0
    }
    
    # قراءة الملف الحالي إذا كان موجوداً
    if os.path.exists(metrics_path):
        try:
            with open(metrics_path, 'r', encoding='utf-8') as f:
                metrics = json.load(f)
        except Exception as e:
            logger.error(f"خطأ في قراءة ملف إحصائيات النسخ الاحتياطية: {e}")
    
    # تحديث البيانات
    timestamp = datetime.datetime.now().isoformat()
    
    new_backup = {
        "filename": backup_filename,
        "timestamp": timestamp,
        "size": backup_size,
        "size_formatted": f"{backup_size / 1024:.2f} كيلوبايت"
    }
    
    metrics["backups"].append(new_backup)
    metrics["last_backup"] = timestamp
    metrics["total_backups"] = len(metrics["backups"])
    metrics["total_size"] = sum(b["size"] for b in metrics["backups"])
    
    # حفظ البيانات المحدثة
    try:
        with open(metrics_path, 'w', encoding='utf-8') as f:
            json.dump(metrics, f, ensure_ascii=False, indent=2)
        logger.info(f"تم تحديث إحصائيات النسخ الاحتياطية بنجاح")
    except Exception as e:
        logger.error(f"خطأ في حفظ ملف إحصائيات النسخ الاحتياطية: {e}")


def cleanup_old_backups():
    """حذف النسخ الاحتياطية القديمة إذا تجاوز العدد الحد الأقصى."""
    try:
        # الحصول على قائمة ملفات النسخ الاحتياطية
        backup_files = []
        for file in os.listdir(BACKUP_DIR):
            if file.startswith("backup_") and file.endswith(".zip"):
                file_path = os.path.join(BACKUP_DIR, file)
                backup_files.append((file_path, os.path.getmtime(file_path)))
        
        # ترتيب الملفات حسب تاريخ التعديل (الأقدم أولاً)
        backup_files.sort(key=lambda x: x[1])
        
        # حذف الملفات القديمة إذا تجاوز العدد الحد الأقصى
        if len(backup_files) > MAX_BACKUPS:
            files_to_delete = backup_files[:-MAX_BACKUPS]
            for file_path, _ in files_to_delete:
                try:
                    os.remove(file_path)
                    logger.info(f"تم حذف النسخة الاحتياطية القديمة: {os.path.basename(file_path)}")
                except Exception as e:
                    logger.error(f"خطأ في حذف النسخة الاحتياطية القديمة: {file_path}: {e}")
    
    except Exception as e:
        logger.error(f"خطأ في تنظيف النسخ الاحتياطية القديمة: {e}")


def check_last_backup():
    """التحقق من تاريخ آخر نسخة احتياطية."""
    metrics_path = os.path.join(BACKUP_DIR, BACKUP_METRICS_FILE)
    
    if not os.path.exists(metrics_path):
        return True, "لم يتم العثور على سجل النسخ الاحتياطية، سيتم إنشاء نسخة جديدة"
    
    try:
        with open(metrics_path, 'r', encoding='utf-8') as f:
            metrics = json.load(f)
        
        last_backup = metrics.get("last_backup", "")
        
        if not last_backup:
            return True, "لم يتم العثور على تاريخ آخر نسخة احتياطية، سيتم إنشاء نسخة جديدة"
        
        last_backup_time = datetime.datetime.fromisoformat(last_backup)
        now = datetime.datetime.now()
        time_diff = (now - last_backup_time).total_seconds()
        
        if time_diff >= BACKUP_INTERVAL:
            return True, f"مر {time_diff / 3600:.1f} ساعة منذ آخر نسخة احتياطية، سيتم إنشاء نسخة جديدة"
        else:
            return False, f"آخر نسخة احتياطية تمت قبل {time_diff / 3600:.1f} ساعة، لا حاجة لنسخة جديدة الآن"
    
    except Exception as e:
        logger.error(f"خطأ في التحقق من تاريخ آخر نسخة احتياطية: {e}")
        return True, f"خطأ في التحقق من تاريخ آخر نسخة احتياطية: {e}"


def restore_backup(backup_file):
    """استعادة قاعدة البيانات من نسخة احتياطية."""
    if not os.path.exists(backup_file):
        logger.error(f"ملف النسخة الاحتياطية غير موجود: {backup_file}")
        return False, f"ملف النسخة الاحتياطية غير موجود: {backup_file}"
    
    try:
        # إنشاء مجلد مؤقت لاستخراج الملفات
        temp_dir = "temp_restore"
        if os.path.exists(temp_dir):
            shutil.rmtree(temp_dir)
        os.makedirs(temp_dir)
        
        # استخراج الملفات
        with zipfile.ZipFile(backup_file, 'r') as zipf:
            zipf.extractall(temp_dir)
        
        # التأكد من وجود ملف قاعدة البيانات في الملفات المستخرجة
        extracted_db = os.path.join(temp_dir, os.path.basename(DB_FILE))
        if not os.path.exists(extracted_db):
            logger.error(f"لم يتم العثور على ملف قاعدة البيانات في النسخة الاحتياطية: {backup_file}")
            return False, f"لم يتم العثور على ملف قاعدة البيانات في النسخة الاحتياطية"
        
        # إنشاء نسخة احتياطية من قاعدة البيانات الحالية قبل الاستعادة
        if os.path.exists(DB_FILE):
            backup_current = f"{DB_FILE}_before_restore_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}"
            shutil.copy2(DB_FILE, backup_current)
            logger.info(f"تم إنشاء نسخة احتياطية من قاعدة البيانات الحالية: {backup_current}")
        
        # استعادة قاعدة البيانات
        shutil.copy2(extracted_db, DB_FILE)
        logger.info(f"تم استعادة قاعدة البيانات من النسخة الاحتياطية: {backup_file}")
        
        # استعادة ملفات التكوين المهمة
        config_files = [
            "config.py",
            "strings.py",
            "restart_log.json"
        ]
        
        for config_file in config_files:
            extracted_config = os.path.join(temp_dir, config_file)
            if os.path.exists(extracted_config):
                # النسخ الاحتياطي للملف الحالي
                if os.path.exists(config_file):
                    backup_current = f"{config_file}_before_restore_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}"
                    shutil.copy2(config_file, backup_current)
                
                # استعادة الملف
                shutil.copy2(extracted_config, config_file)
                logger.info(f"تم استعادة ملف التكوين: {config_file}")
        
        # استعادة محتوى المجلدات إن وجدت
        content_dirs = [
            "temp_media"
        ]
        
        for content_dir in content_dirs:
            extracted_dir = os.path.join(temp_dir, content_dir)
            if os.path.exists(extracted_dir):
                # إنشاء المجلد إذا لم يكن موجوداً
                if not os.path.exists(content_dir):
                    os.makedirs(content_dir)
                
                # نسخ المحتوى
                for root, _, files in os.walk(extracted_dir):
                    rel_path = os.path.relpath(root, extracted_dir)
                    target_dir = os.path.join(content_dir, rel_path)
                    
                    if not os.path.exists(target_dir):
                        os.makedirs(target_dir)
                    
                    for file in files:
                        src_file = os.path.join(root, file)
                        dst_file = os.path.join(target_dir, file)
                        shutil.copy2(src_file, dst_file)
                
                logger.info(f"تم استعادة محتوى المجلد: {content_dir}")
        
        # تنظيف المجلد المؤقت
        shutil.rmtree(temp_dir)
        
        return True, f"تم استعادة النسخة الاحتياطية بنجاح: {os.path.basename(backup_file)}"
    
    except Exception as e:
        logger.error(f"خطأ في استعادة النسخة الاحتياطية: {e}")
        import traceback
        logger.error(traceback.format_exc())
        return False, f"خطأ في استعادة النسخة الاحتياطية: {e}"


def list_available_backups():
    """الحصول على قائمة النسخ الاحتياطية المتاحة."""
    if not os.path.exists(BACKUP_DIR):
        return []
    
    backups = []
    for file in os.listdir(BACKUP_DIR):
        if file.startswith("backup_") and file.endswith(".zip"):
            file_path = os.path.join(BACKUP_DIR, file)
            file_size = os.path.getsize(file_path)
            file_date = datetime.datetime.fromtimestamp(os.path.getmtime(file_path))
            
            backups.append({
                "filename": file,
                "path": file_path,
                "size": file_size,
                "size_formatted": f"{file_size / 1024:.2f} كيلوبايت",
                "date": file_date.isoformat(),
                "date_formatted": file_date.strftime("%Y-%m-%d %H:%M:%S")
            })
    
    # ترتيب النسخ الاحتياطية حسب التاريخ (الأحدث أولاً)
    backups.sort(key=lambda x: x["date"], reverse=True)
    
    return backups


def notify_admin_about_backup(success, message, admin_id=None):
    """إرسال إشعار للمسؤول حول حالة النسخ الاحتياطي."""
    try:
        if admin_id:
            # استخدام واجهة برمجة التطبيقات تيليجرام لإرسال رسالة للمسؤول
            # هذه الوظيفة تتطلب تكامل إضافي مع البوت
            logger.info(f"إرسال إشعار للمسؤول {admin_id} حول النسخ الاحتياطي: {message}")
        else:
            logger.info(f"معرف المسؤول غير متوفر، لن يتم إرسال إشعار")
    except Exception as e:
        logger.error(f"خطأ في إرسال إشعار للمسؤول: {e}")


def run_backup():
    """تشغيل عملية النسخ الاحتياطي."""
    logger.info("بدء عملية النسخ الاحتياطي التلقائية")
    
    # التحقق من الحاجة لنسخة احتياطية جديدة
    need_backup, reason = check_last_backup()
    logger.info(f"التحقق من الحاجة لنسخة احتياطية جديدة: {need_backup}, السبب: {reason}")
    
    if need_backup:
        # إنشاء نسخة احتياطية
        success, result = backup_database()
        
        if success:
            logger.info(f"تم إنشاء النسخة الاحتياطية بنجاح: {result}")
            return True, f"تم إنشاء النسخة الاحتياطية بنجاح: {os.path.basename(result)}"
        else:
            logger.error(f"فشل في إنشاء النسخة الاحتياطية: {result}")
            return False, f"فشل في إنشاء النسخة الاحتياطية: {result}"
    else:
        logger.info(f"لا حاجة لنسخة احتياطية جديدة: {reason}")
        return True, reason


def main():
    """الوظيفة الرئيسية للسكريبت."""
    logger.info("بدء تشغيل نظام النسخ الاحتياطي التلقائي")
    
    # التأكد من وجود مجلد النسخ الاحتياطية
    ensure_backup_dir()
    
    # تشغيل عملية النسخ الاحتياطي
    success, message = run_backup()
    
    # عرض النتيجة
    if success:
        logger.info(f"تمت عملية النسخ الاحتياطي بنجاح: {message}")
    else:
        logger.error(f"فشلت عملية النسخ الاحتياطي: {message}")
    
    return success, message


def scheduled_backup_check():
    """وظيفة للتحقق من النسخ الاحتياطي بشكل دوري."""
    logger.info("بدء التحقق الدوري من النسخ الاحتياطي")
    
    while True:
        try:
            # تشغيل النسخ الاحتياطي
            success, message = run_backup()
            
            if success:
                logger.info(f"تم التحقق من النسخ الاحتياطي بنجاح: {message}")
            else:
                logger.warning(f"مشكلة في التحقق من النسخ الاحتياطي: {message}")
        
        except Exception as e:
            logger.error(f"خطأ أثناء التحقق الدوري من النسخ الاحتياطي: {e}")
        
        # الانتظار حتى الفحص التالي
        time.sleep(BACKUP_INTERVAL)


if __name__ == "__main__":
    # تشغيل وظيفة النسخ الاحتياطي فقط عند استدعاء السكريبت مباشرة
    main()