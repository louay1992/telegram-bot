import json
import os
import uuid
import base64
from datetime import datetime
import logging
import sqlite3
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, scoped_session
from config import NOTIFICATIONS_DB, ADMINS_DB, IMAGES_DIR, MESSAGE_TEMPLATE_FILE, DEFAULT_SMS_TEMPLATE

# استخدام URI قاعدة البيانات من المتغيرات البيئية
DATABASE_URL = os.environ.get('DATABASE_URL')

if not DATABASE_URL:
    logging.warning("DATABASE_URL is not set. Using SQLite as fallback.")
    DATABASE_URL = 'sqlite:///shipping_bot.db'

# إنشاء محرك قاعدة البيانات
engine = create_engine(DATABASE_URL)

# إنشاء جلسة
SessionLocal = scoped_session(sessionmaker(autocommit=False, autoflush=False, bind=engine))

def get_db_session():
    """
    الحصول على جلسة لقاعدة البيانات
    
    Returns:
        sqlalchemy.orm.Session: جلسة قاعدة البيانات
    """
    try:
        db = SessionLocal()
        return db
    except Exception as e:
        logging.error(f"Error getting database session: {e}")
        return None

def load_json(file_path, default=None):
    """Load JSON data from file, creating it with default value if it doesn't exist."""
    if default is None:
        default = {}
    
    try:
        if not os.path.exists(file_path):
            os.makedirs(os.path.dirname(file_path), exist_ok=True)
            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(default, f, ensure_ascii=False)
            return default
        
        with open(file_path, 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception as e:
        logging.error(f"Error loading JSON from {file_path}: {e}")
        return default

def save_json(file_path, data):
    """Save JSON data to file."""
    try:
        os.makedirs(os.path.dirname(file_path), exist_ok=True)
        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        return True
    except Exception as e:
        logging.error(f"Error saving JSON to {file_path}: {e}")
        return False

def save_image(image_data, notification_id):
    """Save image data to filesystem."""
    try:
        # Create a unique filename for the image
        file_path = os.path.join(IMAGES_DIR, f"{notification_id}.jpg")
        
        # Make sure directory exists
        os.makedirs(os.path.dirname(file_path), exist_ok=True)
        
        # Save the image
        with open(file_path, 'wb') as f:
            f.write(image_data)
        
        return file_path
    except Exception as e:
        logging.error(f"Error saving image: {e}")
        return None

def get_image(notification_id):
    """Get image data from filesystem."""
    try:
        # زيادة التسجيل للتشخيص
        logging.info(f"Attempting to get image for notification ID: {notification_id}")
        
        # بناء مسار الملف
        file_path = os.path.join(IMAGES_DIR, f"{notification_id}.jpg")
        logging.info(f"Generated image path: {file_path}")
        
        # التحقق من وجود الملف
        if not os.path.exists(file_path):
            logging.warning(f"Image file does not exist: {file_path}")
            
            # محاولة إيجاد أي ملفات صورة مرتبطة بهذا الإشعار
            dir_path = os.path.dirname(file_path)
            if os.path.exists(dir_path):
                related_files = [f for f in os.listdir(dir_path) if notification_id in f]
                if related_files:
                    logging.info(f"Found related image files: {related_files}")
                    # استخدام أول ملف مرتبط إذا وجد
                    alt_file_path = os.path.join(dir_path, related_files[0])
                    logging.info(f"Trying alternative image file: {alt_file_path}")
                    with open(alt_file_path, 'rb') as f:
                        return f.read()
                else:
                    logging.warning(f"No related image files found in {dir_path}")
            else:
                logging.warning(f"Directory does not exist: {dir_path}")
            
            return None
        
        # قراءة الملف إذا وجد
        with open(file_path, 'rb') as f:
            data = f.read()
            logging.info(f"Successfully read image file, size: {len(data)} bytes")
            return data
    except Exception as e:
        logging.error(f"Error getting image: {e}")
        import traceback
        logging.error(traceback.format_exc())
        return None

def add_notification(customer_name, phone_number, image_data, reminder_hours=24):
    """
    Add a new shipping notification to the database.
    
    Args:
        customer_name (str): Customer's name
        phone_number (str): Customer's phone number
        image_data (bytes): Image data for the notification
        reminder_hours (float): Hours after which to send a reminder (default: 24 hours)
    
    Returns:
        tuple: (success, notification_id or error message)
    """
    try:
        notifications = load_json(NOTIFICATIONS_DB, {"notifications": []})
        
        # Generate a unique ID for the notification
        notification_id = str(uuid.uuid4())
        
        # Save the image
        image_path = save_image(image_data, notification_id)
        
        if not image_path:
            return False, "Failed to save image"
        
        # Create notification record with reminder settings
        notification = {
            "id": notification_id,
            "customer_name": customer_name,
            "phone_number": phone_number,
            "image_path": image_path,
            "created_at": datetime.now().isoformat(),
            "reminder_hours": reminder_hours,
            "reminder_sent": False  # Flag to track if reminder has been sent
        }
        
        notifications["notifications"].append(notification)
        
        # Save updated notifications
        if save_json(NOTIFICATIONS_DB, notifications):
            return True, notification_id
        else:
            return False, "Failed to save notification data"
    
    except Exception as e:
        logging.error(f"Error adding notification: {e}")
        return False, str(e)

def search_notifications_by_name(customer_name):
    """Search for notifications by customer name."""
    try:
        notifications = load_json(NOTIFICATIONS_DB, {"notifications": []})
        
        results = []
        search_term = customer_name.lower()
        
        for notification in notifications["notifications"]:
            if search_term in notification["customer_name"].lower():
                results.append(notification)
        
        return results
    except Exception as e:
        logging.error(f"Error searching notifications by name: {e}")
        return []

def search_notifications_by_phone(phone_number):
    """Search for notifications by phone number."""
    try:
        import input_validator as validator
        notifications = load_json(NOTIFICATIONS_DB, {"notifications": []})
        
        results = []
        
        # Remove spaces, dashes, etc. for more flexible matching
        search_digits = ''.join(filter(str.isdigit, phone_number))
        
        # Handle multiple formats in search
        search_patterns = [
            search_digits,  # Original digits only
        ]
        
        # If starts with 0, add version with 963 prefix replacing the 0
        if search_digits.startswith('0'):
            search_patterns.append('963' + search_digits[1:])
        
        # If starts with 963, add version with 0 prefix replacing the 963
        if search_digits.startswith('963'):
            search_patterns.append('0' + search_digits[3:])
            
        logging.info(f"البحث عن رقم الهاتف باستخدام الأنماط: {search_patterns}")
        
        for notification in notifications["notifications"]:
            notification_digits = ''.join(filter(str.isdigit, notification["phone_number"]))
            
            # Check if any search pattern matches
            for pattern in search_patterns:
                if pattern in notification_digits or notification_digits in pattern:
                    results.append(notification)
                    break  # Avoid duplicates
        
        return results
    except Exception as e:
        logging.error(f"Error searching notifications by phone: {e}")
        return []

def get_all_notifications():
    """Get all notifications."""
    try:
        data = load_json(NOTIFICATIONS_DB, {"notifications": []})
        return data["notifications"]
    except Exception as e:
        logging.error(f"Error getting all notifications: {e}")
        return []

def get_notification(notification_id):
    """
    استرجاع إشعار محدد بواسطة المعرف.
    
    Args:
        notification_id (str): معرف الإشعار
        
    Returns:
        dict: بيانات الإشعار إذا وجد، None خلاف ذلك
    """
    try:
        data = load_json(NOTIFICATIONS_DB, {"notifications": []})
        notifications = data["notifications"]
        
        for notification in notifications:
            if notification["id"] == notification_id:
                return notification
                
        logging.warning(f"لم يتم العثور على إشعار بالمعرف: {notification_id}")
        return None
    except Exception as e:
        logging.error(f"خطأ في استرجاع الإشعار: {e}")
        return None

def delete_notification(notification_id):
    """Delete a notification by its ID."""
    try:
        notifications = load_json(NOTIFICATIONS_DB, {"notifications": []})
        
        # Find the notification to delete
        for i, notification in enumerate(notifications["notifications"]):
            if notification["id"] == notification_id:
                # Remove the notification from the list
                deleted = notifications["notifications"].pop(i)
                
                # Delete the image file if it exists
                image_path = deleted.get("image_path")
                if image_path and os.path.exists(image_path):
                    os.remove(image_path)
                
                # Save the updated notifications
                if save_json(NOTIFICATIONS_DB, notifications):
                    return True
                else:
                    return False
        
        # If we got here, the notification wasn't found
        return False
    except Exception as e:
        logging.error(f"Error deleting notification: {e}")
        return False

def is_admin(user_id):
    """Check if a user is an admin."""
    try:
        admins = load_json(ADMINS_DB, {"admins": [], "main_admin": None})
        return str(user_id) in admins["admins"]
    except Exception as e:
        logging.error(f"Error checking admin status: {e}")
        return False

def is_main_admin(user_id):
    """Check if a user is the main admin."""
    try:
        admins = load_json(ADMINS_DB, {"admins": [], "main_admin": None})
        return str(user_id) == admins.get("main_admin")
    except Exception as e:
        logging.error(f"Error checking main admin status: {e}")
        return False

def set_main_admin_if_none(user_id):
    """
    Set the user as main admin if there is none.
    This is only called for the first user to access the bot after all admins are deleted.
    """
    try:
        admins = load_json(ADMINS_DB, {"admins": [], "main_admin": None})
        user_id = str(user_id)
        
        # If there's no main admin, set this user as main admin
        if not admins.get("main_admin"):
            logging.info(f"Setting user {user_id} as the main admin (first after reset)")
            admins["main_admin"] = user_id
            
            # Also add to regular admins list if not already there
            if user_id not in admins["admins"]:
                admins["admins"].append(user_id)
                
            return save_json(ADMINS_DB, admins)
        
        return False  # There's already a main admin
    except Exception as e:
        logging.error(f"Error setting main admin: {e}")
        return False

def add_admin(user_id):
    """Add a user to the admins list."""
    try:
        admins = load_json(ADMINS_DB, {"admins": [], "main_admin": None})
        
        # Convert to string for consistency
        user_id = str(user_id)
        
        if user_id not in admins["admins"]:
            admins["admins"].append(user_id)
            return save_json(ADMINS_DB, admins)
        
        return True  # Already an admin
    except Exception as e:
        logging.error(f"Error adding admin: {e}")
        return False

def remove_admin(user_id):
    """Remove a user from the admins list."""
    try:
        admins = load_json(ADMINS_DB, {"admins": [], "main_admin": None})
        
        # Convert to string for consistency
        user_id = str(user_id)
        
        # Cannot remove the main admin
        if user_id == admins.get("main_admin"):
            return False
        
        if user_id in admins["admins"]:
            admins["admins"].remove(user_id)
            return save_json(ADMINS_DB, admins)
        
        return True  # Not an admin anyway
    except Exception as e:
        logging.error(f"Error removing admin: {e}")
        return False

def get_all_admins():
    """Get all admins with their statuses."""
    try:
        admins_data = load_json(ADMINS_DB, {"admins": [], "main_admin": None})
        
        result = []
        for admin_id in admins_data["admins"]:
            is_main = admin_id == admins_data.get("main_admin")
            result.append({
                "id": admin_id,
                "is_main": is_main
            })
        
        return result
    except Exception as e:
        logging.error(f"Error getting all admins: {e}")
        return []
        
def get_main_admin_id():
    """الحصول على معرف المسؤول الرئيسي."""
    try:
        # محاولة الحصول على المعرف من ملف JSON
        admins_data = load_json(ADMINS_DB, {"admins": [], "main_admin": None})
        main_admin = admins_data.get("main_admin")
        if main_admin:
            return main_admin
            
        # محاولة الحصول على المعرف من قاعدة البيانات SQL إذا كانت متاحة
        try:
            db_file = "shipping_bot.db"
            if os.path.exists(db_file):
                conn = sqlite3.connect(db_file)
                cursor = conn.cursor()
                cursor.execute("SELECT user_id FROM admins LIMIT 1")
                admin_result = cursor.fetchone()
                conn.close()
                
                if admin_result:
                    return str(admin_result[0])
        except Exception as sql_err:
            logging.error(f"خطأ في الوصول لقاعدة البيانات SQL للحصول على المسؤول: {sql_err}")
            
        # إذا وصلنا إلى هنا، لا يوجد مسؤول رئيسي
        return None
    except Exception as e:
        logging.error(f"خطأ في الحصول على معرف المسؤول الرئيسي: {e}")
        return None

def delete_all_admins():
    """Delete all admins from the system."""
    try:
        # Create an empty admins json
        empty_admins = {"admins": [], "main_admin": None}
        success = save_json(ADMINS_DB, empty_admins)
        logging.info(f"All admins deleted. Success: {success}")
        return success
    except Exception as e:
        logging.error(f"Error deleting all admins: {e}")
        return False

def update_notification(notification_id, updates):
    """
    Update a notification with new data.
    
    Args:
        notification_id (str): ID of the notification to update
        updates (dict): Dictionary of fields to update
    
    Returns:
        bool: True if successful, False otherwise
    """
    try:
        notifications = load_json(NOTIFICATIONS_DB, {"notifications": []})
        
        # Find the notification to update
        for notification in notifications["notifications"]:
            if notification["id"] == notification_id:
                # Update fields
                for key, value in updates.items():
                    notification[key] = value
                
                # Save updated notifications
                return save_json(NOTIFICATIONS_DB, notifications)
        
        # If we got here, the notification wasn't found
        logging.warning(f"Notification {notification_id} not found for update")
        return False
    
    except Exception as e:
        logging.error(f"Error updating notification: {e}")
        return False

def mark_reminder_sent(notification_id):
    """
    Mark a notification as having had its reminder sent.
    
    Args:
        notification_id (str): ID of the notification
    
    Returns:
        bool: True if successful, False otherwise
    """
    updates = {
        "reminder_sent": True,
        "reminder_sent_at": datetime.now().isoformat()
    }
    
    return update_notification(notification_id, updates)

def get_message_template():
    """
    الحصول على قالب الرسالة الحالي.
    إذا لم يكن القالب موجوداً، سيتم استخدام القالب الافتراضي.
    
    Returns:
        str: نص قالب الرسالة
    """
    try:
        # التحقق من وجود ملف القالب
        if os.path.exists(MESSAGE_TEMPLATE_FILE):
            with open(MESSAGE_TEMPLATE_FILE, "r", encoding="utf-8") as f:
                template = f.read().strip()
                if template:  # التحقق من أن القالب ليس فارغًا
                    return template
                
        # إذا لم يكن الملف موجودًا أو كان فارغًا، إنشاء ملف جديد بالقالب الافتراضي
        os.makedirs(os.path.dirname(MESSAGE_TEMPLATE_FILE), exist_ok=True)
        with open(MESSAGE_TEMPLATE_FILE, "w", encoding="utf-8") as f:
            f.write(DEFAULT_SMS_TEMPLATE)
            
        return DEFAULT_SMS_TEMPLATE
        
    except Exception as e:
        logging.error(f"Error loading message template: {e}")
        return DEFAULT_SMS_TEMPLATE

def update_message_template(new_template):
    """
    تحديث قالب الرسالة.
    
    Args:
        new_template (str): نص القالب الجديد
        
    Returns:
        bool: True إذا تم التحديث بنجاح، False خلاف ذلك
    """
    try:
        # التأكد من وجود مجلد البيانات
        os.makedirs(os.path.dirname(MESSAGE_TEMPLATE_FILE), exist_ok=True)
        
        # حفظ القالب الجديد
        with open(MESSAGE_TEMPLATE_FILE, "w", encoding="utf-8") as f:
            f.write(new_template)
            
        return True
        
    except Exception as e:
        logging.error(f"Error updating message template: {e}")
        return False

def reset_message_template():
    """
    إعادة ضبط قالب الرسالة إلى القالب الافتراضي.
    
    Returns:
        bool: True إذا تم إعادة الضبط بنجاح، False خلاف ذلك
    """
    return update_message_template(DEFAULT_SMS_TEMPLATE)

def get_welcome_message_template():
    """
    الحصول على قالب رسالة الترحيب الفورية الحالي.
    إذا لم يكن القالب موجوداً، سيتم استخدام القالب الافتراضي.
    
    Returns:
        str: نص قالب رسالة الترحيب
    """
    import config
    try:
        # التحقق من وجود ملف القالب
        if os.path.exists(config.WELCOME_MESSAGE_TEMPLATE_FILE):
            with open(config.WELCOME_MESSAGE_TEMPLATE_FILE, "r", encoding="utf-8") as f:
                template = f.read().strip()
                if template:  # التحقق من أن القالب ليس فارغًا
                    return template
                
        # إذا لم يكن الملف موجودًا أو كان فارغًا، إنشاء ملف جديد بالقالب الافتراضي
        os.makedirs(os.path.dirname(config.WELCOME_MESSAGE_TEMPLATE_FILE), exist_ok=True)
        with open(config.WELCOME_MESSAGE_TEMPLATE_FILE, "w", encoding="utf-8") as f:
            f.write(config.DEFAULT_WELCOME_TEMPLATE)
            
        return config.DEFAULT_WELCOME_TEMPLATE
        
    except Exception as e:
        logging.error(f"Error loading welcome message template: {e}")
        return config.DEFAULT_WELCOME_TEMPLATE

def update_welcome_message_template(new_template):
    """
    تحديث قالب رسالة الترحيب الفورية.
    
    Args:
        new_template (str): نص القالب الجديد
        
    Returns:
        bool: True إذا تم التحديث بنجاح، False خلاف ذلك
    """
    import config
    try:
        # التأكد من وجود مجلد البيانات
        os.makedirs(os.path.dirname(config.WELCOME_MESSAGE_TEMPLATE_FILE), exist_ok=True)
        
        # حفظ القالب الجديد
        with open(config.WELCOME_MESSAGE_TEMPLATE_FILE, "w", encoding="utf-8") as f:
            f.write(new_template)
            
        return True
        
    except Exception as e:
        logging.error(f"Error updating welcome message template: {e}")
        return False


def get_verification_message_template():
    """
    الحصول على قالب رسالة التحقق من الاستلام الحالي.
    إذا لم يكن القالب موجوداً، سيتم استخدام القالب الافتراضي.
    
    Returns:
        str: نص قالب رسالة التحقق من الاستلام
    """
    import config
    try:
        # التحقق من وجود ملف القالب
        if os.path.exists(config.VERIFICATION_MESSAGE_TEMPLATE_FILE):
            with open(config.VERIFICATION_MESSAGE_TEMPLATE_FILE, "r", encoding="utf-8") as f:
                template = f.read().strip()
                if template:  # التحقق من أن القالب ليس فارغًا
                    return template
                
        # إذا لم يكن الملف موجودًا أو كان فارغًا، إنشاء ملف جديد بالقالب الافتراضي
        os.makedirs(os.path.dirname(config.VERIFICATION_MESSAGE_TEMPLATE_FILE), exist_ok=True)
        with open(config.VERIFICATION_MESSAGE_TEMPLATE_FILE, "w", encoding="utf-8") as f:
            f.write(config.DEFAULT_VERIFICATION_TEMPLATE)
            
        return config.DEFAULT_VERIFICATION_TEMPLATE
        
    except Exception as e:
        logging.error(f"Error loading verification message template: {e}")
        return config.DEFAULT_VERIFICATION_TEMPLATE


def update_verification_message_template(new_template):
    """
    تحديث قالب رسالة التحقق من الاستلام.
    
    Args:
        new_template (str): نص القالب الجديد
        
    Returns:
        bool: True إذا تم التحديث بنجاح، False خلاف ذلك
    """
    import config
    try:
        # التأكد من وجود مجلد البيانات
        os.makedirs(os.path.dirname(config.VERIFICATION_MESSAGE_TEMPLATE_FILE), exist_ok=True)
        
        # حفظ القالب الجديد
        with open(config.VERIFICATION_MESSAGE_TEMPLATE_FILE, "w", encoding="utf-8") as f:
            f.write(new_template)
            
        return True
        
    except Exception as e:
        logging.error(f"Error updating verification message template: {e}")
        return False


# ------------------- User Permissions Functions -------------------

def has_permission(user_id, permission_type):
    """
    التحقق مما إذا كان المستخدم يملك صلاحية معينة.
    المسؤولين يملكون جميع الصلاحيات تلقائياً.
    
    Args:
        user_id (int): معرف المستخدم
        permission_type (str): نوع الصلاحية للتحقق
        
    Returns:
        bool: True إذا كان المستخدم يملك الصلاحية، False خلاف ذلك
    """
    # المسؤولين يملكون جميع الصلاحيات
    if is_admin(user_id):
        return True
        
    try:
        import config
        # تحميل بيانات الصلاحيات
        permissions_data = load_json(config.PERMISSIONS_DB, {"users": {}})
        
        # التحقق مما إذا كان المستخدم موجوداً ويملك الصلاحية
        str_user_id = str(user_id)  # تحويل معرف المستخدم إلى نص للاستخدام كمفتاح
        
        if str_user_id in permissions_data["users"]:
            user_permissions = permissions_data["users"][str_user_id]
            return permission_type in user_permissions.get("permissions", [])
            
        return False
    except Exception as e:
        logging.error(f"Error checking permission for user {user_id}: {e}")
        return False

def get_all_users_with_permissions():
    """
    الحصول على قائمة بجميع المستخدمين مع صلاحياتهم.
    
    Returns:
        list: قائمة قواميس تحتوي على معلومات المستخدمين وصلاحياتهم
    """
    try:
        import config
        # تحميل بيانات الصلاحيات
        permissions_data = load_json(config.PERMISSIONS_DB, {"users": {}})
        
        # تحويل البيانات إلى قائمة لسهولة الاستخدام
        users_list = []
        for user_id, user_data in permissions_data["users"].items():
            users_list.append({
                "id": int(user_id),
                "username": user_data.get("username", "غير معروف"),
                "first_name": user_data.get("first_name", ""),
                "permissions": user_data.get("permissions", [])
            })
            
        return users_list
    except Exception as e:
        logging.error(f"Error getting users with permissions: {e}")
        return []

def add_permission_to_user(user_id, username, first_name, permission_type):
    """
    إضافة صلاحية لمستخدم.
    
    Args:
        user_id (int): معرف المستخدم
        username (str): اسم المستخدم
        first_name (str): الاسم الأول للمستخدم
        permission_type (str): نوع الصلاحية للإضافة
        
    Returns:
        bool: True إذا تمت الإضافة بنجاح، False خلاف ذلك
    """
    try:
        import config
        # التحقق مما إذا كانت الصلاحية صالحة
        if permission_type not in config.PERMISSION_TYPES:
            logging.error(f"Invalid permission type: {permission_type}")
            return False
        
        # تحميل بيانات الصلاحيات
        permissions_data = load_json(config.PERMISSIONS_DB, {"users": {}})
        
        # تحويل معرف المستخدم إلى نص للاستخدام كمفتاح
        str_user_id = str(user_id)
        
        # إضافة أو تحديث بيانات المستخدم
        if str_user_id not in permissions_data["users"]:
            permissions_data["users"][str_user_id] = {
                "username": username,
                "first_name": first_name,
                "permissions": []
            }
            
        # إضافة الصلاحية إذا لم تكن موجودة بالفعل
        if permission_type not in permissions_data["users"][str_user_id].get("permissions", []):
            if "permissions" not in permissions_data["users"][str_user_id]:
                permissions_data["users"][str_user_id]["permissions"] = []
                
            permissions_data["users"][str_user_id]["permissions"].append(permission_type)
            
        # حفظ البيانات
        return save_json(config.PERMISSIONS_DB, permissions_data)
    except Exception as e:
        logging.error(f"Error adding permission to user {user_id}: {e}")
        return False

def remove_permission_from_user(user_id, permission_type):
    """
    إزالة صلاحية من مستخدم.
    
    Args:
        user_id (int): معرف المستخدم
        permission_type (str): نوع الصلاحية للإزالة
        
    Returns:
        bool: True إذا تمت الإزالة بنجاح، False خلاف ذلك
    """
    try:
        import config
        # تحميل بيانات الصلاحيات
        permissions_data = load_json(config.PERMISSIONS_DB, {"users": {}})
        
        # تحويل معرف المستخدم إلى نص للاستخدام كمفتاح
        str_user_id = str(user_id)
        
        # التحقق مما إذا كان المستخدم موجوداً
        if str_user_id not in permissions_data["users"]:
            logging.warning(f"User {user_id} not found in permissions database")
            return False
            
        # إزالة الصلاحية إذا كانت موجودة
        if permission_type in permissions_data["users"][str_user_id].get("permissions", []):
            permissions_data["users"][str_user_id]["permissions"].remove(permission_type)
            
            # إذا لم يعد لدى المستخدم أي صلاحيات، يمكن إزالته من قاعدة البيانات
            if not permissions_data["users"][str_user_id]["permissions"]:
                del permissions_data["users"][str_user_id]
            
        # حفظ البيانات
        return save_json(config.PERMISSIONS_DB, permissions_data)
    except Exception as e:
        logging.error(f"Error removing permission from user {user_id}: {e}")
        return False

def get_user_permissions(user_id):
    """
    الحصول على صلاحيات مستخدم معين.
    
    Args:
        user_id (int): معرف المستخدم
        
    Returns:
        list: قائمة بالصلاحيات التي يملكها المستخدم
    """
    try:
        import config
        # تحميل بيانات الصلاحيات
        permissions_data = load_json(config.PERMISSIONS_DB, {"users": {}})
        
        # تحويل معرف المستخدم إلى نص للاستخدام كمفتاح
        str_user_id = str(user_id)
        
        # التحقق مما إذا كان المستخدم موجوداً
        if str_user_id in permissions_data["users"]:
            return permissions_data["users"][str_user_id].get("permissions", [])
            
        return []
    except Exception as e:
        logging.error(f"Error getting permissions for user {user_id}: {e}")
        return []


# ------------------- Theme Settings Functions -------------------

def get_theme_settings():
    """
    الحصول على إعدادات السمة الحالية.
    
    Returns:
        dict: إعدادات السمة الحالية
    """
    try:
        import config
        # تحميل إعدادات السمة، وإذا لم توجد فاستخدم الإعدادات الافتراضية
        theme_settings = load_json(config.THEME_SETTINGS_DB, {"theme": config.DEFAULT_THEME})
        return theme_settings["theme"]
    except Exception as e:
        logging.error(f"Error loading theme settings: {e}")
        import config
        return config.DEFAULT_THEME

def update_theme_settings(updated_settings):
    """
    تحديث إعدادات السمة.
    
    Args:
        updated_settings (dict): الإعدادات المحدثة للسمة
        
    Returns:
        bool: True إذا تم التحديث بنجاح، False خلاف ذلك
    """
    try:
        import config
        # تحميل الإعدادات الحالية
        current_settings = load_json(config.THEME_SETTINGS_DB, {"theme": config.DEFAULT_THEME})
        
        # تحديث الإعدادات بالقيم الجديدة
        current_settings["theme"].update(updated_settings)
        
        # حفظ الإعدادات المحدثة
        return save_json(config.THEME_SETTINGS_DB, current_settings)
    except Exception as e:
        logging.error(f"Error updating theme settings: {e}")
        return False

def reset_theme_settings():
    """
    إعادة ضبط إعدادات السمة إلى الإعدادات الافتراضية.
    
    Returns:
        bool: True إذا تمت إعادة الضبط بنجاح، False خلاف ذلك
    """
    try:
        import config
        # إنشاء إعدادات جديدة باستخدام القيم الافتراضية
        default_settings = {"theme": config.DEFAULT_THEME}
        
        # حفظ الإعدادات الافتراضية
        return save_json(config.THEME_SETTINGS_DB, default_settings)
    except Exception as e:
        logging.error(f"Error resetting theme settings: {e}")
        return False

def update_company_logo(logo_data):
    """
    تحديث شعار الشركة.
    
    Args:
        logo_data (bytes): بيانات الشعار كصورة
        
    Returns:
        tuple: (success, logo_id) حيث logo_id هو معرف الشعار المخزن
    """
    try:
        import config
        import uuid
        
        # إنشاء معرف فريد للشعار
        logo_id = str(uuid.uuid4())
        
        # حفظ الشعار في ملف
        logo_path = os.path.join(IMAGES_DIR, f"company_logo_{logo_id}.png")
        
        # التأكد من وجود المجلد
        os.makedirs(os.path.dirname(logo_path), exist_ok=True)
        
        # حفظ الصورة
        with open(logo_path, 'wb') as f:
            f.write(logo_data)
        
        # تحديث إعدادات السمة بمعرف الشعار الجديد
        update_theme_settings({"company_logo": logo_id})
        
        return True, logo_id
    except Exception as e:
        logging.error(f"Error updating company logo: {e}")
        return False, None

def get_company_logo():
    """
    الحصول على شعار الشركة الحالي.
    
    Returns:
        bytes: بيانات الشعار كصورة
    """
    try:
        # الحصول على إعدادات السمة الحالية
        theme_settings = get_theme_settings()
        
        # التحقق مما إذا كان هناك شعار محدد
        if not theme_settings.get("company_logo"):
            return None
        
        # استرجاع معرف الشعار
        logo_id = theme_settings["company_logo"]
        
        # تحديد مسار ملف الشعار
        logo_path = os.path.join(IMAGES_DIR, f"company_logo_{logo_id}.png")
        
        # التحقق من وجود الملف
        if not os.path.exists(logo_path):
            logging.warning(f"Company logo file not found: {logo_path}")
            return None
        
        # قراءة بيانات الشعار
        with open(logo_path, 'rb') as f:
            logo_data = f.read()
        
        return logo_data
    except Exception as e:
        logging.error(f"Error getting company logo: {e}")
        return None


def backup_database():
    """
    إنشاء نسخة احتياطية يدوية لقاعدة البيانات.
    
    Returns:
        tuple: (نجاح, رسالة/مسار النسخة الاحتياطية)
    """
    try:
        import auto_backup
        return auto_backup.backup_database()
    except ImportError:
        import logging
        logging.error("لم يتم العثور على وحدة النسخ الاحتياطي")
        return False, "لم يتم العثور على وحدة النسخ الاحتياطي"
    except Exception as e:
        import logging
        logging.error(f"خطأ في إنشاء نسخة احتياطية: {e}")
        return False, f"خطأ في إنشاء نسخة احتياطية: {e}"


def get_backup_list():
    """
    الحصول على قائمة النسخ الاحتياطية المتاحة.
    
    Returns:
        list: قائمة النسخ الاحتياطية المتاحة
    """
    try:
        import auto_backup
        return auto_backup.list_available_backups()
    except ImportError:
        import logging
        logging.error("لم يتم العثور على وحدة النسخ الاحتياطي")
        return []
    except Exception as e:
        import logging
        logging.error(f"خطأ في الحصول على قائمة النسخ الاحتياطية: {e}")
        return []


def restore_backup(backup_name):
    """
    استعادة قاعدة البيانات من نسخة احتياطية.
    
    Args:
        backup_name (str): اسم ملف النسخة الاحتياطية
        
    Returns:
        tuple: (نجاح, رسالة)
    """
    try:
        import auto_backup
        backup_path = f"backup/{backup_name}"
        return auto_backup.restore_backup(backup_path)
    except ImportError:
        import logging
        logging.error("لم يتم العثور على وحدة النسخ الاحتياطي")
        return False, "لم يتم العثور على وحدة النسخ الاحتياطي"
    except Exception as e:
        import logging
        logging.error(f"خطأ في استعادة النسخة الاحتياطية: {e}")
        return False, f"خطأ في استعادة النسخة الاحتياطية: {e}"


def get_admin_phone(admin_id=None):
    """
    الحصول على رقم هاتف المسؤول.
    
    Args:
        admin_id (int, optional): معرف المسؤول. إذا كانت القيمة None، قم بإرجاع رقم هاتف المسؤول الرئيسي.
        
    Returns:
        str: رقم هاتف المسؤول
    """
    admin_data = load_json('data/admins.json', default={'admins': [], 'main_admin': None})
    
    if admin_id:
        # محاولة الحصول على رقم هاتف المسؤول المحدد
        admins_data = load_json('data/admin_data.json', default={})
        if str(admin_id) in admins_data and 'phone' in admins_data[str(admin_id)]:
            return admins_data[str(admin_id)]['phone']
    
    # محاولة الحصول على رقم هاتف المسؤول الرئيسي
    main_admin = admin_data.get('main_admin')
    if main_admin:
        admins_data = load_json('data/admin_data.json', default={})
        if str(main_admin) in admins_data and 'phone' in admins_data[str(main_admin)]:
            return admins_data[str(main_admin)]['phone']
    
    return None


def update_admin_phone(admin_id, phone_number):
    """
    تحديث رقم هاتف المسؤول.
    
    Args:
        admin_id (int): معرف المسؤول
        phone_number (str): رقم الهاتف الجديد
        
    Returns:
        bool: True إذا تم التحديث بنجاح، False خلاف ذلك
    """
    try:
        admins_data = load_json('data/admin_data.json', default={})
        
        # التأكد من أن المستخدم مسؤول
        if not is_admin(admin_id):
            return False
            
        # إنشاء أو تحديث بيانات المسؤول
        if str(admin_id) not in admins_data:
            admins_data[str(admin_id)] = {}
            
        admins_data[str(admin_id)]['phone'] = phone_number
        
        # حفظ البيانات
        save_json('data/admin_data.json', admins_data)
        return True
    
    except Exception as e:
        import logging
        logging.error(f"خطأ في تحديث رقم هاتف المسؤول: {e}")
        return False


# ------------------- وظائف إدارة شخصية البوت -------------------

def get_bot_personality():
    """
    الحصول على شخصية البوت النشطة حالياً.
    
    Returns:
        dict: قاموس يحتوي على معلومات شخصية البوت النشطة، أو شخصية افتراضية إذا لم تكن هناك شخصية نشطة
    """
    try:
        from models import BotPersonality
        
        db = get_db_session()
        if not db:
            raise Exception("فشل الاتصال بقاعدة البيانات")
            
        # البحث عن شخصية نشطة
        active_personality = db.query(BotPersonality).filter(BotPersonality.is_active == True).first()
        
        if active_personality:
            result = active_personality.to_dict()
        else:
            # إنشاء شخصية افتراضية إذا لم تكن هناك شخصية نشطة
            import json
            default_settings = {
                "formality": 5,  # 1-10 (غير رسمي - رسمي جداً)
                "friendliness": 5,  # 1-10 (محايد - ودود جداً)
                "helpfulness": 8,  # 1-10 (موجز - مفصل جداً)
                "enthusiasm": 5,  # 1-10 (هادئ - متحمس جداً)
                "emoji_usage": 3,  # 1-10 (لا رموز تعبيرية - كثير من الرموز التعبيرية)
            }
            
            default_personality = {
                "id": 0,
                "mood_type": "متوازن",
                "settings": default_settings,
                "greeting": "مرحباً! أنا مساعدك في إدارة إشعارات الشحن. كيف يمكنني مساعدتك اليوم؟",
                "farewell": "شكراً لاستخدامك نظام إشعارات الشحن. أتمنى لك يوماً سعيداً!",
                "is_active": True,
                "created_at": datetime.now().isoformat(),
                "created_by": None
            }
            
            # حفظ الشخصية الافتراضية في قاعدة البيانات
            try:
                new_personality = BotPersonality(
                    mood_type=default_personality["mood_type"],
                    settings=json.dumps(default_settings, ensure_ascii=False),
                    greeting=default_personality["greeting"],
                    farewell=default_personality["farewell"],
                    is_active=True,
                    created_by=None
                )
                
                db.add(new_personality)
                db.commit()
                
                # تحديث المعرف في الشخصية الافتراضية
                default_personality["id"] = new_personality.id
                
            except Exception as e:
                db.rollback()
                logging.error(f"Error creating default personality: {e}")
            
            result = default_personality
            
        db.close()
        return result
        
    except Exception as e:
        logging.error(f"Error getting bot personality: {e}")
        import json
        
        # إرجاع شخصية افتراضية في حالة حدوث خطأ
        default_settings = {
            "formality": 5,
            "friendliness": 5,
            "helpfulness": 8,
            "enthusiasm": 5,
            "emoji_usage": 3,
        }
        
        return {
            "id": 0,
            "mood_type": "متوازن",
            "settings": default_settings,
            "greeting": "مرحباً! أنا مساعدك في إدارة إشعارات الشحن. كيف يمكنني مساعدتك اليوم؟",
            "farewell": "شكراً لاستخدامك نظام إشعارات الشحن. أتمنى لك يوماً سعيداً!",
            "is_active": True,
            "created_at": datetime.now().isoformat(),
            "created_by": None
        }


def update_bot_personality(personality_id, updates):
    """
    تحديث شخصية البوت.
    
    Args:
        personality_id (int): معرف الشخصية
        updates (dict): قاموس يحتوي على الحقول المراد تحديثها
        
    Returns:
        bool: True إذا تم التحديث بنجاح، False خلاف ذلك
    """
    try:
        from models import BotPersonality
        
        db = get_db_session()
        if not db:
            return False
            
        # البحث عن الشخصية
        personality = db.query(BotPersonality).filter(BotPersonality.id == personality_id).first()
        
        if not personality:
            db.close()
            return False
            
        # تحديث الحقول
        if "mood_type" in updates:
            personality.mood_type = updates["mood_type"]
            
        if "settings" in updates:
            import json
            if isinstance(updates["settings"], dict):
                personality.settings = json.dumps(updates["settings"], ensure_ascii=False)
            else:
                personality.settings = updates["settings"]
                
        if "greeting" in updates:
            personality.greeting = updates["greeting"]
            
        if "farewell" in updates:
            personality.farewell = updates["farewell"]
            
        if "is_active" in updates:
            # إذا كانت هذه الشخصية ستصبح نشطة، يجب إلغاء تنشيط الشخصيات الأخرى
            if updates["is_active"]:
                other_personalities = db.query(BotPersonality).filter(BotPersonality.id != personality_id).all()
                for other in other_personalities:
                    other.is_active = False
                    
            personality.is_active = updates["is_active"]
            
        # حفظ التغييرات
        db.commit()
        db.close()
        return True
        
    except Exception as e:
        logging.error(f"Error updating bot personality: {e}")
        if db:
            db.rollback()
            db.close()
        return False


def create_bot_personality(mood_type, settings, greeting, farewell, created_by, is_active=False):
    """
    إنشاء شخصية جديدة للبوت.
    
    Args:
        mood_type (str): نوع المزاج
        settings (dict): إعدادات الشخصية
        greeting (str): رسالة الترحيب
        farewell (str): رسالة الوداع
        created_by (int): معرف المستخدم الذي أنشأ الشخصية
        is_active (bool): هل هذه الشخصية نشطة؟
        
    Returns:
        tuple: (نجاح، معرف الشخصية أو رسالة الخطأ)
    """
    try:
        from models import BotPersonality
        
        db = get_db_session()
        if not db:
            return (False, "فشل الاتصال بقاعدة البيانات")
            
        # تحويل الإعدادات إلى JSON إذا لزم الأمر
        import json
        if isinstance(settings, dict):
            settings_json = json.dumps(settings, ensure_ascii=False)
        else:
            settings_json = settings
            
        # إنشاء الشخصية الجديدة
        new_personality = BotPersonality(
            mood_type=mood_type,
            settings=settings_json,
            greeting=greeting,
            farewell=farewell,
            is_active=is_active,
            created_by=created_by
        )
        
        # إذا كانت هذه الشخصية نشطة، قم بإلغاء تنشيط الشخصيات الأخرى
        if is_active:
            other_personalities = db.query(BotPersonality).all()
            for other in other_personalities:
                other.is_active = False
        
        # حفظ الشخصية الجديدة
        db.add(new_personality)
        db.commit()
        
        personality_id = new_personality.id
        db.close()
        
        return (True, personality_id)
        
    except Exception as e:
        logging.error(f"Error creating bot personality: {e}")
        if db:
            db.rollback()
            db.close()
        return (False, str(e))


def get_all_bot_personalities():
    """
    الحصول على جميع شخصيات البوت.
    
    Returns:
        list: قائمة بجميع شخصيات البوت
    """
    try:
        from models import BotPersonality
        
        db = get_db_session()
        if not db:
            return []
            
        # الحصول على جميع الشخصيات
        personalities = db.query(BotPersonality).all()
        
        # تحويل الشخصيات إلى قواميس
        result = [p.to_dict() for p in personalities]
        
        db.close()
        return result
        
    except Exception as e:
        logging.error(f"Error getting all bot personalities: {e}")
        if db:
            db.close()
        return []


def delete_bot_personality(personality_id):
    """
    حذف شخصية البوت.
    
    Args:
        personality_id (int): معرف الشخصية
        
    Returns:
        bool: True إذا تم الحذف بنجاح، False خلاف ذلك
    """
    try:
        from models import BotPersonality
        
        db = get_db_session()
        if not db:
            return False
            
        # البحث عن الشخصية
        personality = db.query(BotPersonality).filter(BotPersonality.id == personality_id).first()
        
        if not personality:
            db.close()
            return False
            
        # إذا كانت الشخصية نشطة، ابحث عن شخصية أخرى لتنشيطها
        if personality.is_active:
            other_personality = db.query(BotPersonality).filter(BotPersonality.id != personality_id).first()
            if other_personality:
                other_personality.is_active = True
                
        # حذف الشخصية
        db.delete(personality)
        db.commit()
        db.close()
        
        return True
        
    except Exception as e:
        logging.error(f"Error deleting bot personality: {e}")
        if db:
            db.rollback()
            db.close()
        return False
