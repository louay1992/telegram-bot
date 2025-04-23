#!/usr/bin/env python3
"""
وحدة السجلات المتقدمة - تدير السجلات مع تدوير الملفات والتنسيق المتقدم
"""
import os
import logging
import sys
from logging.handlers import RotatingFileHandler
import datetime
import traceback

# استيراد التكوين الموحد
try:
    from unified_config import get_config
except ImportError:
    # استخدام القيم الافتراضية إذا لم يكن ملف التكوين متاحاً
    def get_config(key=None):
        defaults = {
            "LOGS_DIR": "logs",
            "LOG_MAX_SIZE": 10 * 1024 * 1024,  # 10 ميغابايت
            "LOG_BACKUP_COUNT": 5,
            "DEBUG": False
        }
        if key is None:
            return defaults
        return defaults.get(key)

# الثوابت الافتراضية
DEFAULT_LOGS_DIR = "logs"
DEFAULT_LOG_MAX_SIZE = 10 * 1024 * 1024  # 10 ميغابايت
DEFAULT_LOG_BACKUP_COUNT = 5

# إنشاء مجلد السجلات إذا لم يكن موجوداً
def ensure_log_directory():
    """التأكد من وجود مجلد السجلات"""
    log_dir = get_config("LOGS_DIR")
    if not isinstance(log_dir, str):
        log_dir = DEFAULT_LOGS_DIR
    os.makedirs(log_dir, exist_ok=True)
    return log_dir

# تنسيق مخصص للسجلات
class CustomFormatter(logging.Formatter):
    """منسق مخصص للسجلات يستخدم ألواناً مختلفة للمستويات المختلفة"""
    
    COLORS = {
        'DEBUG': '\033[94m',    # أزرق
        'INFO': '\033[92m',     # أخضر
        'WARNING': '\033[93m',  # أصفر
        'ERROR': '\033[91m',    # أحمر
        'CRITICAL': '\033[91m\033[1m',  # أحمر غامق
        'RESET': '\033[0m'      # إعادة تعيين
    }
    
    def __init__(self, use_colors=True):
        super().__init__(
            fmt='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )
        self.use_colors = use_colors
    
    def format(self, record):
        original_msg = record.msg
        original_levelname = record.levelname
        
        if self.use_colors and record.levelname in self.COLORS:
            record.levelname = f"{self.COLORS[record.levelname]}{record.levelname}{self.COLORS['RESET']}"
            if isinstance(record.msg, str):
                record.msg = f"{self.COLORS[original_levelname]}{record.msg}{self.COLORS['RESET']}"
        
        result = super().format(record)
        
        # استعادة القيم الأصلية
        record.msg = original_msg
        record.levelname = original_levelname
        
        return result

def setup_logger(name, log_file=None, level=None, use_console=True, use_colors=True):
    """إعداد سجل معين"""
    # تحديد مستوى السجل
    if level is None:
        level = logging.DEBUG if get_config("DEBUG") else logging.INFO
    
    # إنشاء السجل
    logger = logging.getLogger(name)
    logger.setLevel(level)
    
    # إزالة جميع معالجات السجل الحالية
    for handler in logger.handlers[:]:
        logger.removeHandler(handler)
    
    # إضافة معالج ملف مدور
    if log_file:
        log_dir = ensure_log_directory()
        log_path = os.path.join(log_dir, log_file)
        
        # استخدام قيم محددة من التكوين مع التحقق من النوع
        max_size = get_config("LOG_MAX_SIZE")
        if not isinstance(max_size, int):
            max_size = 10 * 1024 * 1024  # 10 ميغابايت افتراضياً
            
        backup_count = get_config("LOG_BACKUP_COUNT")
        if not isinstance(backup_count, int):
            backup_count = 5  # 5 نسخ احتياطية افتراضياً
            
        file_handler = RotatingFileHandler(
            log_path,
            maxBytes=max_size,
            backupCount=backup_count,
            encoding='utf-8'
        )
        file_formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
        file_handler.setFormatter(file_formatter)
        logger.addHandler(file_handler)
    
    # إضافة معالج وحدة التحكم
    if use_console:
        console_handler = logging.StreamHandler(sys.stdout)
        console_formatter = CustomFormatter(use_colors=use_colors)
        console_handler.setFormatter(console_formatter)
        logger.addHandler(console_handler)
    
    return logger

def setup_root_logger(log_file="bot.log", level=None):
    """إعداد السجل الجذر"""
    return setup_logger("root", log_file, level)

def log_exception(logger, e, message="حدث خطأ غير متوقع:"):
    """تسجيل استثناء مع تفاصيل كاملة"""
    logger.error(f"{message} {str(e)}")
    logger.debug(f"تفاصيل الخطأ: {traceback.format_exc()}")

def get_logfiles():
    """الحصول على قائمة ملفات السجلات المتاحة"""
    log_dir = ensure_log_directory()
    log_files = []
    
    for file in os.listdir(log_dir):
        if file.endswith('.log'):
            file_path = os.path.join(log_dir, file)
            size = os.path.getsize(file_path)
            modified = datetime.datetime.fromtimestamp(os.path.getmtime(file_path))
            
            log_files.append({
                'name': file,
                'path': file_path,
                'size': size,
                'size_human': f"{size / 1024:.1f} KB",
                'modified': modified,
                'modified_human': modified.strftime('%Y-%m-%d %H:%M:%S')
            })
    
    return sorted(log_files, key=lambda x: x['modified'], reverse=True)

def clear_old_logs(max_age_days=30):
    """حذف ملفات السجلات القديمة"""
    log_dir = ensure_log_directory()
    now = datetime.datetime.now()
    deleted_count = 0
    
    for file in os.listdir(log_dir):
        if file.endswith('.log') and file != 'bot.log':  # لا تحذف السجل الرئيسي
            file_path = os.path.join(log_dir, file)
            modified = datetime.datetime.fromtimestamp(os.path.getmtime(file_path))
            age = (now - modified).days
            
            if age > max_age_days:
                try:
                    os.remove(file_path)
                    deleted_count += 1
                except Exception as e:
                    print(f"خطأ في حذف ملف السجل {file}: {e}")
    
    return deleted_count

# إعداد السجل الافتراضي
root_logger = setup_root_logger()

if __name__ == "__main__":
    # اختبار وحدة السجلات
    logger = setup_logger("test_logger", "test.log")
    
    logger.debug("هذه رسالة تصحيح")
    logger.info("هذه رسالة معلومات")
    logger.warning("هذه رسالة تحذير")
    logger.error("هذه رسالة خطأ")
    logger.critical("هذه رسالة حرجة")
    
    try:
        1/0
    except Exception as e:
        log_exception(logger, e, "خطأ في العملية الحسابية:")
    
    print("\nملفات السجلات المتاحة:")
    for log_file in get_logfiles():
        print(f"{log_file['name']} - {log_file['size_human']} - {log_file['modified_human']}")
    
    # تنظيف السجلات القديمة
    deleted = clear_old_logs(max_age_days=7)
    print(f"\nتم حذف {deleted} ملف سجل قديم")