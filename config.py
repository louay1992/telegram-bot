import os
import logging

# Configure logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)

# Telegram Bot Token - استخدام التوكن من متغيرات البيئة
DEFAULT_TOKEN = "7406580104:AAGG2JQeeNfsmcGVMCm7hxitIK-qm2yekVg"
TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN", DEFAULT_TOKEN)

# سجل قيمة التوكن المستخدمة
logging.info(f"استخدام توكن بوت تيليجرام: {TOKEN[:5]}...{TOKEN[-5:]}")

# OpenAI API Key from environment variable
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "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")

# UltraMsg.com WhatsApp API credentials
ULTRAMSG_INSTANCE_ID = os.getenv("ULTRAMSG_INSTANCE_ID", "")
ULTRAMSG_TOKEN = os.getenv("ULTRAMSG_TOKEN", "")

# Data storage paths
NOTIFICATIONS_DB = "data/notifications.json"
ADMINS_DB = "data/admins.json"
SETTINGS_DB = "data/settings.json"
PERMISSIONS_DB = "data/user_permissions.json"
THEME_SETTINGS_DB = "data/theme_settings.json"
MESSAGE_TEMPLATE_FILE = "data/message_template.txt"
WELCOME_MESSAGE_TEMPLATE_FILE = "data/welcome_message_template.txt"
VERIFICATION_MESSAGE_TEMPLATE_FILE = "data/verification_message_template.txt"

# User permission types
PERMISSION_SEARCH_BY_NAME = "search_by_name"
PERMISSION_TYPES = [PERMISSION_SEARCH_BY_NAME]

# Theme default settings
DEFAULT_THEME = {
    "primary_color": "#1e88e5",     # اللون الرئيسي - أزرق
    "secondary_color": "#26a69a",   # اللون الثانوي - أخضر فاتح
    "accent_color": "#ff5722",      # لون التمييز - برتقالي
    "success_color": "#4caf50",     # لون النجاح - أخضر
    "warning_color": "#ffc107",     # لون التحذير - أصفر
    "error_color": "#e53935",       # لون الخطأ - أحمر
    "company_name": "NatureCare",   # اسم الشركة الافتراضي
    "company_logo": None,           # شعار الشركة - افتراضي بدون شعار
    "logo_mode": "text"             # وضع الشعار: نص فقط، صورة فقط، أو كلاهما
}

# Image directory
IMAGES_DIR = "data/images"

# القالب الافتراضي للرسالة النصية (للتذكير)
DEFAULT_SMS_TEMPLATE = "مرحباً {{customer_name}}،\n\nهذا تذكير بأن لديك شحنة جاهزة للاستلام.\n\nمع تحيات NatureCare."

# القالب الافتراضي للرسالة الترحيبية الفورية
DEFAULT_WELCOME_TEMPLATE = """مرحباً {{customer_name}}،

تم شحن طلبك بنجاح! الطلب الآن في طريقه إليك.

ستجد صورة إشعار الشحن مرفقة مع هذه الرسالة للاطلاع عليها.

مع تحيات NatureCare 🚚"""

# القالب الافتراضي لرسالة التحقق من الاستلام
DEFAULT_VERIFICATION_TEMPLATE = """مرحباً {{customer_name}}،

نود التأكد من استلامك للطلب الخاص بك.
هل تم استلام الشحنة بنجاح؟

يرجى الرد بـ "نعم" إذا تم الاستلام أو "لا" إذا لم يتم الاستلام بعد.

شكراً لتعاونكم،
فريق خدمة العملاء في NatureCare 📦"""

# Ensure data directories exist
os.makedirs(IMAGES_DIR, exist_ok=True)
os.makedirs(os.path.dirname(NOTIFICATIONS_DB), exist_ok=True)
