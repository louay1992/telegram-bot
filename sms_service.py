"""
ملف لإدارة إرسال رسائل SMS بواسطة خدمة Twilio.
"""
import os
import logging
from twilio.rest import Client
from datetime import datetime, timedelta

# استيراد معلومات حساب Twilio من المتغيرات البيئية
TWILIO_ACCOUNT_SID = os.environ.get("TWILIO_ACCOUNT_SID")
TWILIO_AUTH_TOKEN = os.environ.get("TWILIO_AUTH_TOKEN")
TWILIO_PHONE_NUMBER = os.environ.get("TWILIO_PHONE_NUMBER")

def send_sms(to_phone_number, message):
    """
    إرسال رسالة SMS إلى رقم هاتف.
    
    Args:
        to_phone_number (str): رقم الهاتف المستلم
        message (str): نص الرسالة
        
    Returns:
        tuple: (نجاح, نتيجة)
    """
    if not all([TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN, TWILIO_PHONE_NUMBER]):
        logging.error("Twilio configuration missing")
        return False, "معلومات حساب Twilio غير مكتملة."
    
    try:
        # تنظيف رقم الهاتف (إزالة الأحرف غير الرقمية)
        cleaned_phone = ''.join(filter(str.isdigit, to_phone_number))
        
        # التحقق من إضافة رمز البلد
        if cleaned_phone.startswith('0'):
            # إزالة الصفر من البداية وإضافة رمز البلد السوري +963
            cleaned_phone = '963' + cleaned_phone[1:]
        
        # إضافة علامة + في بداية الرقم إذا لم تكن موجودة
        if not cleaned_phone.startswith('+'):
            cleaned_phone = '+' + cleaned_phone
        
        logging.info(f"Formatted phone number: {cleaned_phone}")
        
        # إنشاء عميل Twilio
        client = Client(TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN)
        
        # إرسال الرسالة
        message_obj = client.messages.create(
            body=message,
            from_=TWILIO_PHONE_NUMBER,
            to=cleaned_phone
        )
        
        logging.info(f"SMS sent to {cleaned_phone}, SID: {message_obj.sid}")
        return True, message_obj.sid
    
    except Exception as e:
        logging.error(f"Error sending SMS: {e}")
        return False, str(e)

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
    from database import get_message_template
    
    # الحصول على قالب الرسالة
    template = get_message_template()
    
    # استبدال اسم العميل في القالب
    message = template.format(customer_name=customer_name)
    
    logging.info(f"Sending reminder message to {customer_name} using template")
    
    return send_sms(phone_number, message)

def check_and_send_scheduled_reminders(notifications, reminder_interval_hours=24):
    """
    فحص الإشعارات وإرسال التذكيرات المجدولة.
    
    Args:
        notifications (list): قائمة بالإشعارات
        reminder_interval_hours (int/float): الفترة بالساعات بعد إنشاء الإشعار (للتجربة: سنستخدم قيمة أقل من ساعة)
        
    Returns:
        int: عدد التذكيرات التي تم إرسالها
    """
    sent_count = 0
    now = datetime.now()
    
    for notification in notifications:
        # استخراج وقت التذكير من الإشعار (قد يكون بالدقائق للتجربة)
        reminder_hours = notification.get("reminder_hours", reminder_interval_hours)
        
        # تحويل تاريخ الإنشاء من نص إلى كائن datetime
        created_at = datetime.fromisoformat(notification["created_at"])
        
        # التحقق من وقت التذكير
        reminder_time = created_at + timedelta(hours=reminder_hours)
        
        # تحديد نافذة التحقق (ساعة كاملة للتأكد من عدم فوات فرصة إرسال الرسالة)
        check_window = timedelta(hours=1)
        
        logging.info(f"Checking notification {notification['id']}: created at {created_at}, "
                    f"reminder time {reminder_time}, now is {now}, "
                    f"reminder_sent: {notification.get('reminder_sent', False)}")
        
        # فحص ما إذا كان الوقت الحالي بعد وقت التذكير
        # وأن الإشعار لم يتم إرسال تذكير له من قبل
        if (now >= reminder_time and 
            not notification.get("reminder_sent", False)):
            
            logging.info(f"Sending reminder for notification {notification['id']}")
            
            # إرسال التذكير
            success, result = send_reminder(
                notification["customer_name"],
                notification["phone_number"],
                notification["id"]
            )
            
            if success:
                # تحديث الإشعار لتسجيل أنه تم إرسال تذكير
                notification["reminder_sent"] = True
                notification["reminder_sent_at"] = datetime.now().isoformat()
                sent_count += 1
                logging.info(f"Reminder sent for notification ID: {notification['id']}")
            else:
                logging.error(f"Failed to send reminder for notification ID: {notification['id']} - {result}")
    
    return sent_count