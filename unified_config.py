#!/usr/bin/env python3
"""
وحدة التكوين الموحد للبوت
تتحكم هذه الوحدة في جميع إعدادات التكوين وتضمن استخدام نفس القيم في جميع أجزاء النظام
"""
import os
import json
import logging
from typing import Dict, Any, Optional, Union

# إعداد التسجيل
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# مسار ملف التكوين
CONFIG_FILE = "bot_config.json"

# القيم الافتراضية
DEFAULT_CONFIG = {
    "BOT_TOKEN": "7406580104:AAGG2JQeeNfsmcGVMCm7hxitIK-qm2yekVg",  # توكن البوت المضمن مباشرة
    "HEARTBEAT_FILE": "bot_heartbeat.txt",  # ملف نبضات القلب
    "MAX_HEARTBEAT_AGE": 120,  # العمر الأقصى لنبضات القلب (بالثواني)
    "WEBHOOK_MODE": False,  # وضع الويب هوك (True/False)
    "WEBHOOK_URL": "",  # URL للويب هوك (إذا كان مفعلاً)
    "ADMIN_IDS": [],  # قائمة معرّفات المشرفين
    "DEBUG": False,  # وضع التصحيح
    "LOGS_DIR": "logs",  # مجلد ملفات السجل
    "LOG_MAX_SIZE": 10 * 1024 * 1024,  # الحجم الأقصى لملف السجل (10 ميغابايت)
    "LOG_BACKUP_COUNT": 5,  # عدد نسخ ملفات السجل الاحتياطية
    "RETRY_MAX_ATTEMPTS": 3,  # الحد الأقصى لمحاولات إعادة المحاولة
    "RETRY_INITIAL_DELAY": 1,  # التأخير الأولي للمحاولة (بالثواني)
    "RETRY_BACKOFF_FACTOR": 2,  # معامل زيادة وقت الانتظار
    "RESOURCE_MONITOR_INTERVAL": 60,  # فترة مراقبة الموارد (بالثواني)
    "MAX_MEMORY_USAGE_MB": 500  # الحد الأقصى لاستخدام الذاكرة (بالميغابايت)
}

# المتغير العالمي للتكوين
_config = DEFAULT_CONFIG.copy()

def load_config() -> Dict[str, Any]:
    """تحميل التكوين من ملف التكوين"""
    global _config
    
    try:
        if os.path.exists(CONFIG_FILE):
            with open(CONFIG_FILE, 'r') as f:
                loaded_config = json.load(f)
                
                # دمج التكوين المحمل مع القيم الافتراضية
                for key, value in loaded_config.items():
                    _config[key] = value
                
                logger.info(f"تم تحميل التكوين من {CONFIG_FILE}")
        else:
            # إنشاء ملف تكوين جديد إذا لم يكن موجوداً
            save_config()
            logger.info(f"تم إنشاء ملف تكوين جديد في {CONFIG_FILE}")
    except Exception as e:
        logger.error(f"خطأ في تحميل التكوين: {e}")
    
    # تحديث متغيرات البيئة المهمة
    update_environment_variables()
    
    return _config

def save_config() -> bool:
    """حفظ التكوين في ملف التكوين"""
    try:
        with open(CONFIG_FILE, 'w') as f:
            json.dump(_config, f, indent=4)
        logger.info(f"تم حفظ التكوين في {CONFIG_FILE}")
        return True
    except Exception as e:
        logger.error(f"خطأ في حفظ التكوين: {e}")
        return False

def get_config(key: Optional[str] = None) -> Union[Dict[str, Any], Any]:
    """
    الحصول على قيمة تكوين معينة أو التكوين بأكمله
    
    المعلمات:
        key: مفتاح التكوين المطلوب. إذا كان None، يتم إرجاع التكوين بأكمله
        
    العوائد:
        قيمة التكوين للمفتاح المحدد أو التكوين بأكمله
    """
    global _config
    
    if key is None:
        return _config
    
    return _config.get(key)

def set_config(key: str, value: Any, save: bool = True) -> bool:
    """
    تعيين قيمة تكوين معينة
    
    المعلمات:
        key: مفتاح التكوين المراد تعيينه
        value: القيمة المراد تعيينها
        save: ما إذا كان يجب حفظ التكوين في الملف بعد التعيين
        
    العوائد:
        True إذا نجحت العملية، False خلاف ذلك
    """
    global _config
    
    try:
        _config[key] = value
        
        # تحديث متغيرات البيئة إذا تم تعيين مفتاح مهم
        if key == "BOT_TOKEN":
            update_environment_variables()
        
        if save:
            return save_config()
        
        return True
    except Exception as e:
        logger.error(f"خطأ في تعيين التكوين: {e}")
        return False

def update_environment_variables():
    """تحديث متغيرات البيئة المهمة من التكوين"""
    # تعيين توكن البوت كمتغير بيئة
    if "BOT_TOKEN" in _config:
        current_env_token = os.environ.get("TELEGRAM_BOT_TOKEN")
        config_token = _config["BOT_TOKEN"]
        
        if current_env_token and current_env_token != config_token:
            logger.warning("⚠️ التوكن الموجود في متغيرات البيئة مختلف عن التوكن في التكوين. سيتم تحديثه.")
        
        os.environ["TELEGRAM_BOT_TOKEN"] = config_token
        logger.info("تم تحديث متغير البيئة TELEGRAM_BOT_TOKEN")

def get_bot_token() -> str:
    """
    الحصول على توكن البوت من التكوين أو من متغيرات البيئة
    ستكون الأولوية للتوكن المضمن مباشرة إذا كان متوفراً
    """
    # الحصول على التوكن المضمن مباشرة
    embedded_token = get_config("BOT_TOKEN")
    if isinstance(embedded_token, dict) or not isinstance(embedded_token, str):
        embedded_token = None
    
    # الحصول على التوكن من متغير البيئة
    env_token = os.environ.get("TELEGRAM_BOT_TOKEN")
    
    # إذا كان التوكنان مختلفين، نعرض تحذيراً
    if env_token and embedded_token and env_token != embedded_token:
        logger.warning("⚠️ التوكن الموجود في متغيرات البيئة مختلف عن التوكن المضمن مباشرة. سيتم استخدام التوكن المضمن مباشرة.")
    
    # نستخدم التوكن المضمن مباشرة إذا كان متوفراً، وإلا نستخدم متغير البيئة
    token = embedded_token or env_token
    
    if not token:
        logger.error("❌ لم يتم العثور على توكن للبوت! تأكد من تعيين TELEGRAM_BOT_TOKEN أو BOT_TOKEN في ملف التكوين.")
        # استخدام توكن افتراضي (للتطوير فقط، لا يجب الاعتماد عليه في الإنتاج)
        token = "7406580104:AAGG2JQeeNfsmcGVMCm7hxitIK-qm2yekVg"
    
    # التأكد من أن القيمة المرجعة هي نص
    return str(token)

# تحميل التكوين عند استيراد الوحدة
load_config()

if __name__ == "__main__":
    # اختبار وحدة التكوين الموحد
    print("القيم الافتراضية للتكوين:")
    for key, value in DEFAULT_CONFIG.items():
        print(f"{key}: {value}")
    
    print("\nقيم التكوين الحالية:")
    current_config = get_config()
    for key, value in current_config.items():
        print(f"{key}: {value}")
    
    # اختبار تعيين واسترجاع قيمة
    print("\nاختبار تعيين واسترجاع قيمة:")
    test_key = "DEBUG"
    original_value = get_config(test_key)
    print(f"القيمة الأصلية لـ {test_key}: {original_value}")
    
    set_config(test_key, not original_value)
    new_value = get_config(test_key)
    print(f"القيمة الجديدة لـ {test_key}: {new_value}")
    
    # إعادة القيمة الأصلية
    set_config(test_key, original_value)
    reset_value = get_config(test_key)
    print(f"تم إعادة قيمة {test_key} إلى: {reset_value}")
    
    # اختبار الحصول على توكن البوت
    print("\nاختبار الحصول على توكن البوت:")
    bot_token = get_bot_token()
    print(f"توكن البوت: {bot_token[:10]}...{bot_token[-4:]}")