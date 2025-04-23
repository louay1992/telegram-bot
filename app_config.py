"""
ملف تكوين التطبيق الأساسي - يحتوي على كافة الإعدادات الرئيسية
"""

import os
import logging
import sys

# توكن بوت تيليجرام
BOT_TOKEN = os.environ.get('TELEGRAM_BOT_TOKEN', '7406580104:AAGG2JQeeNfsmcGVMCm7hxitIK-qm2yekVg')

# تفعيل وضع Always-On
USE_ALWAYS_ON = os.environ.get('USE_ALWAYS_ON', 'True').lower() in ('true', 'yes', '1')

# مفتاح سري للتطبيق
FLASK_SECRET_KEY = os.environ.get('FLASK_SECRET_KEY', 'a-very-secret-key-123456789')

# رابط قاعدة البيانات
DATABASE_URL = os.environ.get('DATABASE_URL')

# إعدادات المنفذ
PORT = int(os.environ.get('PORT', 5000))
HOST = '0.0.0.0'  # الاستماع على جميع الواجهات

# إعدادات الويبهوك
WEBHOOK_ENABLED = os.environ.get('WEBHOOK_ENABLED', 'False').lower() in ('true', 'yes', '1')
WEBHOOK_URL = os.environ.get('WEBHOOK_URL', '')

# إعدادات رسائل WhatsApp
WHATSAPP_ENABLED = os.environ.get('WHATSAPP_ENABLED', 'False').lower() in ('true', 'yes', '1')
ULTRAMSG_TOKEN = os.environ.get('ULTRAMSG_TOKEN', '')
ULTRAMSG_INSTANCE_ID = os.environ.get('ULTRAMSG_INSTANCE_ID', '')

# إعدادات Twilio
TWILIO_ENABLED = os.environ.get('TWILIO_ENABLED', 'False').lower() in ('true', 'yes', '1')
TWILIO_ACCOUNT_SID = os.environ.get('TWILIO_ACCOUNT_SID', '')
TWILIO_AUTH_TOKEN = os.environ.get('TWILIO_AUTH_TOKEN', '')
TWILIO_PHONE_NUMBER = os.environ.get('TWILIO_PHONE_NUMBER', '')

# إعدادات السجلات
LOG_LEVEL = os.environ.get('LOG_LEVEL', 'INFO')
LOG_FILE = os.environ.get('LOG_FILE', 'logs/app.log')
LOG_FORMAT = '%(asctime)s - %(name)s - %(levelname)s - %(message)s'

# إعدادات المسؤول
SUPER_ADMIN_ID = os.environ.get('SUPER_ADMIN_ID', '')  # معرف المسؤول الرئيسي (إذا وجد)

# مسارات المجلدات
LOGS_DIR = 'logs'
MEDIA_DIR = 'temp_media'
BACKUP_DIR = 'data/backup'

# التأكد من وجود المجلدات الضرورية
def ensure_directories():
    """التأكد من وجود المجلدات اللازمة للتطبيق"""
    directories = [LOGS_DIR, MEDIA_DIR, BACKUP_DIR]
    for directory in directories:
        if not os.path.exists(directory):
            os.makedirs(directory, exist_ok=True)

# إعداد نظام السجلات
def setup_logging():
    """إعداد نظام السجلات"""
    # التأكد من وجود مجلد السجلات
    ensure_directories()
    
    # إنشاء منسق سجلات موحد
    log_format = logging.Formatter(LOG_FORMAT)
    
    # إعداد مستوى السجلات
    log_level = getattr(logging, LOG_LEVEL.upper(), logging.INFO)
    
    # إنشاء سجل رئيسي
    logger = logging.getLogger('app_config')
    logger.setLevel(log_level)
    
    # إضافة معالج للطباعة على وحدة التحكم
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(log_format)
    logger.addHandler(console_handler)
    
    # إضافة معالج لحفظ السجلات في ملف
    try:
        file_handler = logging.FileHandler(LOG_FILE)
        file_handler.setFormatter(log_format)
        logger.addHandler(file_handler)
    except Exception as e:
        logger.error(f"فشل في إعداد ملف السجلات: {e}")
    
    # تسجيل معلومات الإعداد
    logger.info(f"USE_ALWAYS_ON = {USE_ALWAYS_ON}")
    logger.info(f"TELEGRAM_BOT_TOKEN = {BOT_TOKEN[:5]}...{BOT_TOKEN[-5:]}")
    
    return logger

# إعداد المتغيرات الأخرى حسب البيئة
def configure_for_environment():
    """إعداد المتغيرات الخاصة بالبيئة المستضيفة"""
    is_replit = os.environ.get('REPL_ID') is not None
    is_render = os.environ.get('RENDER') is not None
    
    # إذا كانت البيئة هي Replit
    if is_replit:
        # إعدادات خاصة بـ Replit
        pass
    
    # إذا كانت البيئة هي Render
    if is_render:
        # إعدادات خاصة بـ Render
        pass

# تنفيذ الإعداد عند استيراد الملف
ensure_directories()
configure_for_environment()