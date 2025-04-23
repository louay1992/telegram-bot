"""
ملف لإدارة إرسال رسائل WhatsApp بواسطة خدمة UltraMsg.com
"""
import json
import logging
import os
import time
import base64
import requests
from io import BytesIO
from database import get_message_template, get_image, get_verification_message_template

# بيانات الاتصال بـ UltraMsg
ULTRAMSG_INSTANCE_ID = os.environ.get("ULTRAMSG_INSTANCE_ID", "")
ULTRAMSG_TOKEN = os.environ.get("ULTRAMSG_TOKEN", "")
ULTRAMSG_API_URL = f"https://api.ultramsg.com/{ULTRAMSG_INSTANCE_ID}"

class UltraMsgService:
    """
    فئة لإدارة إرسال رسائل WhatsApp بواسطة خدمة UltraMsg.com
    """
    
    def __init__(self):
        self.instance_id = ULTRAMSG_INSTANCE_ID
        self.token = ULTRAMSG_TOKEN
        self.api_url = ULTRAMSG_API_URL
    
    def send_message(self, to_phone_number, message):
        """
        إرسال رسالة واتساب نصية إلى رقم هاتف.
        
        Args:
            to_phone_number (str): رقم الهاتف المستلم (بصيغة دولية مثل 963933000227)
            message (str): نص الرسالة
            
        Returns:
            bool: نجاح العملية أم لا
        """
        return send_whatsapp_message(to_phone_number, message)[0]
    
    def send_image_message(self, to_phone_number, image_path, caption=""):
        """
        إرسال صورة مع نص عبر واتساب.
        
        Args:
            to_phone_number (str): رقم الهاتف المستلم
            image_path (str): مسار الصورة على القرص
            caption (str): النص المرفق مع الصورة (اختياري)
            
        Returns:
            bool: نجاح العملية أم لا
        """
        try:
            with open(image_path, 'rb') as image_file:
                image_data = image_file.read()
                return send_whatsapp_image(to_phone_number, image_data, caption)[0]
        except Exception as e:
            logging.error(f"خطأ في قراءة الصورة من المسار {image_path}: {e}")
            return False
            
    def send_campaign_message(self, to_phone_number, message, image_path=None):
        """
        إرسال رسالة حملة تسويقية إلى رقم هاتف.
        
        Args:
            to_phone_number (str): رقم الهاتف المستلم
            message (str): نص الرسالة
            image_path (str, optional): مسار الصورة إذا كانت موجودة
            
        Returns:
            bool: نجاح العملية أم لا
        """
        if image_path and os.path.exists(image_path):
            return self.send_image_message(to_phone_number, image_path, caption=message)
        else:
            return self.send_message(to_phone_number, message)

def send_whatsapp_message(to_phone_number, message):
    """
    إرسال رسالة واتساب نصية إلى رقم هاتف.
    
    Args:
        to_phone_number (str): رقم الهاتف المستلم (بصيغة دولية مثل 963933000227)
        message (str): نص الرسالة
        
    Returns:
        tuple: (نجاح, نتيجة)
    """
    # التأكد من أن رقم الهاتف يبدأ بكود البلد (963)
    if to_phone_number.startswith('0'):
        to_phone_number = '963' + to_phone_number[1:]
    elif not to_phone_number.startswith('+') and not to_phone_number.startswith('963'):
        to_phone_number = '963' + to_phone_number
    
    if to_phone_number.startswith('+'):
        to_phone_number = to_phone_number[1:]  # إزالة علامة + إذا كانت موجودة
    
    url = f"{ULTRAMSG_API_URL}/messages/chat"
    
    payload = {
        'token': ULTRAMSG_TOKEN,
        'to': to_phone_number,
        'body': message
    }
    
    try:
        response = requests.post(url, data=payload)
        response_data = response.json()
        
        if response.status_code == 200 and response_data.get('sent') == 'true':
            return True, response_data
        else:
            logging.error(f"فشل إرسال رسالة الواتساب: {response.text}")
            return False, response_data
    
    except Exception as e:
        logging.error(f"حدث خطأ أثناء إرسال رسالة الواتساب: {str(e)}")
        return False, str(e)

def send_whatsapp_image(to_phone_number, image_data, caption=""):
    """
    إرسال صورة مع نص عبر واتساب.
    
    Args:
        to_phone_number (str): رقم الهاتف المستلم
        image_data (bytes): بيانات الصورة
        caption (str): النص المرفق مع الصورة (اختياري)
        
    Returns:
        tuple: (نجاح, نتيجة)
    """
    # التأكد من أن رقم الهاتف يبدأ بكود البلد (963)
    if to_phone_number.startswith('0'):
        to_phone_number = '963' + to_phone_number[1:]
    elif not to_phone_number.startswith('+') and not to_phone_number.startswith('963'):
        to_phone_number = '963' + to_phone_number
    
    if to_phone_number.startswith('+'):
        to_phone_number = to_phone_number[1:]  # إزالة علامة + إذا كانت موجودة
    
    url = f"{ULTRAMSG_API_URL}/messages/image"
    
    # تحويل بيانات الصورة إلى Base64
    image_base64 = base64.b64encode(image_data).decode('utf-8')
    
    payload = {
        'token': ULTRAMSG_TOKEN,
        'to': to_phone_number,
        'image': image_base64,
        'caption': caption
    }
    
    try:
        response = requests.post(url, data=payload)
        response_data = response.json()
        
        if response.status_code == 200 and response_data.get('sent') == 'true':
            return True, response_data
        else:
            logging.error(f"فشل إرسال صورة واتساب: {response.text}")
            return False, response_data
    
    except Exception as e:
        logging.error(f"حدث خطأ أثناء إرسال صورة عبر واتساب: {str(e)}")
        return False, str(e)

def send_welcome_message(customer_name, phone_number, notification_id):
    """
    إرسال رسالة ترحيبية فورية للعميل عند إضافة إشعار الشحن.
    
    Args:
        customer_name (str): اسم العميل
        phone_number (str): رقم هاتف العميل
        notification_id (str): معرف الإشعار
        
    Returns:
        tuple: (نجاح, نتيجة)
    """
    from database import get_welcome_message_template, get_image
    
    # الحصول على قالب الرسالة الترحيبية
    template = get_welcome_message_template()
    
    # استبدال المتغيرات في القالب
    message = template.replace("{{customer_name}}", customer_name)
    
    # الحصول على صورة الإشعار
    image_data = get_image(notification_id)
    
    if image_data:
        # إرسال الصورة مع نص الرسالة
        logging.info(f"Sending welcome message with image to {customer_name} ({phone_number})")
        return send_whatsapp_image(phone_number, image_data, caption=message)
    else:
        # إرسال رسالة نصية فقط إذا لم تكن الصورة متوفرة
        logging.info(f"Sending welcome message (text only) to {customer_name} ({phone_number})")
        return send_whatsapp_message(phone_number, message)

def send_reminder(customer_name, phone_number, notification_id):
    """
    إرسال رسالة تذكير للعميل بخصوص الشحنة.
    
    Args:
        customer_name (str): اسم العميل
        phone_number (str): رقم هاتف العميل
        notification_id (str): معرف الإشعار
        
    Returns:
        tuple: (نجاح, نتيجة)
    """
    from database import get_message_template, get_image
    
    # الحصول على قالب الرسالة
    template = get_message_template()
    
    # استبدال المتغيرات في القالب
    message = template.replace("{{customer_name}}", customer_name)
    
    # الحصول على صورة الإشعار
    image_data = get_image(notification_id)
    
    if image_data:
        # إرسال الصورة مع نص الرسالة
        return send_whatsapp_image(phone_number, image_data, caption=message)
    else:
        # إرسال رسالة نصية فقط إذا لم تكن الصورة متوفرة
        return send_whatsapp_message(phone_number, message)

def send_verification_message(customer_name, phone_number, notification_id):
    """
    إرسال رسالة تحقق من استلام الشحنة.
    
    Args:
        customer_name (str): اسم العميل
        phone_number (str): رقم هاتف العميل
        notification_id (str): معرف الإشعار
        
    Returns:
        tuple: (نجاح, نتيجة)
    """
    from database import get_verification_message_template, get_image
    
    # الحصول على قالب رسالة التحقق من الاستلام
    template = get_verification_message_template()
    
    # استبدال المتغيرات في القالب
    message = template.replace("{{customer_name}}", customer_name)
    
    # الحصول على صورة الإشعار
    image_data = get_image(notification_id)
    
    if image_data:
        # إرسال الصورة مع نص الرسالة
        logging.info(f"Sending verification message with image to {customer_name} ({phone_number})")
        return send_whatsapp_image(phone_number, image_data, caption=message)
    else:
        # إرسال رسالة نصية فقط إذا لم تكن الصورة متوفرة
        logging.info(f"Sending verification message (text only) to {customer_name} ({phone_number})")
        return send_whatsapp_message(phone_number, message)


def send_admin_alert(message):
    """
    إرسال إشعار للمسؤول الرئيسي عبر WhatsApp.
    
    Args:
        message (str): نص الرسالة المراد إرسالها
    
    Returns:
        tuple: (نجاح، نتيجة)
    """
    try:
        import database as db
        
        # الحصول على قائمة المسؤولين
        admins = db.get_admins()
        if not admins:
            logging.warning("لا يوجد مسؤولين مسجلين في النظام لإرسال الإشعار")
            return False, "لا يوجد مسؤولين مسجلين"
            
        # استخدام أول مسؤول (المسؤول الرئيسي)
        main_admin = admins[0]
        admin_id = main_admin.get('user_id')
        
        # الحصول على بيانات المسؤول
        admin_phone = db.get_admin_phone(admin_id)
        
        if not admin_phone:
            logging.warning(f"لا يوجد رقم هاتف مسجل للمسؤول {admin_id}")
            return False, "لا يوجد رقم هاتف للمسؤول"
            
        # إرسال الرسالة عبر WhatsApp
        logging.info(f"إرسال إشعار للمسؤول على الرقم {admin_phone}")
        return send_whatsapp_message(admin_phone, message)
    
    except Exception as e:
        logging.error(f"خطأ في إرسال إشعار للمسؤول: {e}")
        import traceback
        logging.error(traceback.format_exc())
        return False, str(e)


def check_and_send_scheduled_reminders(notifications, reminder_interval_hours=24):
    """
    فحص الإشعارات وإرسال التذكيرات المجدولة.
    
    Args:
        notifications (list): قائمة بالإشعارات
        reminder_interval_hours (int/float): الفترة بالساعات بعد إنشاء الإشعار
        
    Returns:
        int: عدد التذكيرات التي تم إرسالها
    """
    import database as db
    from datetime import datetime, timedelta
    
    sent_count = 0
    now = datetime.now()
    
    for notification in notifications:
        # تخطي الإشعارات التي تم إرسال تذكير لها بالفعل
        if notification.get('reminder_sent', False):
            logging.info(f"Skipping notification {notification['id']}: reminder already sent")
            continue
        
        # تخطي الإشعارات التي ليس لها وقت تذكير (reminder_hours = 0)
        if notification.get('reminder_hours', 0) <= 0:
            logging.info(f"Skipping notification {notification['id']}: reminder disabled (reminder_hours=0)")
            continue
        
        # حساب وقت التذكير
        created_at = datetime.fromisoformat(notification['created_at'])
        reminder_time = created_at + timedelta(hours=notification['reminder_hours'])
        
        logging.info(f"Checking notification {notification['id']}: created at {created_at}, "
                     f"reminder time {reminder_time}, now is {now}, reminder_sent: {notification.get('reminder_sent', False)}")
        
        # إذا حان وقت التذكير وكان الإشعار غير مرسل
        if now >= reminder_time and not notification.get('reminder_sent', False):
            logging.info(f"Sending reminder for notification {notification['id']}")
            
            # إرسال التذكير
            success, result = send_reminder(
                notification['customer_name'],
                notification['phone_number'],
                notification['id']
            )
            
            if success:
                # تحديث حالة الإشعار كمرسل - تحديث مباشر للكائن في الذاكرة
                notification['reminder_sent'] = True
                notification['reminder_sent_at'] = datetime.now().isoformat()
                
                # تحديث حالة الإشعار في قاعدة البيانات
                update_result = db.mark_reminder_sent(notification['id'])
                if update_result:
                    logging.info(f"Reminder sent successfully for {notification['customer_name']} and database updated")
                else:
                    logging.warning(f"Reminder sent successfully but failed to update database for {notification['id']}")
                
                sent_count += 1
            else:
                logging.error(f"Failed to send reminder for {notification['customer_name']}: {result}")
    
    return sent_count