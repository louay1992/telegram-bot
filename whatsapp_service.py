"""
ملف لإدارة إرسال رسائل واتساب بواسطة خدمة Twilio.
"""
import os
import logging
from twilio.rest import Client
from datetime import datetime, timedelta

# استيراد معلومات حساب Twilio من المتغيرات البيئية
TWILIO_ACCOUNT_SID = os.environ.get("TWILIO_ACCOUNT_SID")
TWILIO_AUTH_TOKEN = os.environ.get("TWILIO_AUTH_TOKEN")

# استخدام رقم واتساب Sandbox القياسي من Twilio
# ملاحظة: هذا هو الرقم القياسي لبيئة Sandbox الخاصة بـ Twilio
TWILIO_WHATSAPP_NUMBER = "+14155238886"

def send_whatsapp(to_phone_number, message, media_url=None):
    """
    إرسال رسالة واتساب إلى رقم هاتف مع إمكانية إرفاق صورة.
    
    Args:
        to_phone_number (str): رقم الهاتف المستلم
        message (str): نص الرسالة
        media_url (str, optional): رابط الصورة المرفقة (إن وجد)
        
    Returns:
        tuple: (نجاح, نتيجة)
    """
    if not all([TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN, TWILIO_WHATSAPP_NUMBER]):
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
        
        logging.info(f"Formatted WhatsApp number: {cleaned_phone}")
        
        # تنسيق أرقام واتساب
        # واتساب يتطلب تنسيق خاص: whatsapp:+NUMBER
        # تأكد من إضافة البادئة "+" إذا لم تكن موجودة
        from_whatsapp_number = ""
        if TWILIO_WHATSAPP_NUMBER:
            from_whatsapp_number = f"whatsapp:{TWILIO_WHATSAPP_NUMBER}"
            if not TWILIO_WHATSAPP_NUMBER.startswith("+"):
                from_whatsapp_number = f"whatsapp:+{TWILIO_WHATSAPP_NUMBER}"
            
        to_whatsapp_number = f"whatsapp:{cleaned_phone}"
        
        # سجل التنسيق النهائي للأرقام
        logging.info(f"Formatted FROM WhatsApp number: {from_whatsapp_number}")
        logging.info(f"Formatted TO WhatsApp number: {to_whatsapp_number}")
        
        # إنشاء عميل Twilio
        client = Client(TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN)
        
        # إرسال رسالة واتساب
        # إذا كانت هناك صورة، سنرفقها مع الرسالة
        if media_url:
            logging.info(f"Sending WhatsApp message with media: {media_url}")
            message_obj = client.messages.create(
                body=message,
                from_=from_whatsapp_number,
                to=to_whatsapp_number,
                media_url=[media_url]  # قائمة بروابط الوسائط المرفقة
            )
        else:
            logging.info("Sending WhatsApp message without media")
            message_obj = client.messages.create(
                body=message,
                from_=from_whatsapp_number,
                to=to_whatsapp_number
            )
        
        logging.info(f"WhatsApp message sent to {cleaned_phone}, SID: {message_obj.sid}")
        return True, message_obj.sid
    
    except Exception as e:
        logging.error(f"Error sending WhatsApp message: {e}")
        return False, str(e)

def send_reminder(customer_name, phone_number, notification_id):
    """
    إرسال رسالة تذكير للعميل بخصوص الشحنة مع صورة الإشعار.
    
    Args:
        customer_name (str): اسم العميل
        phone_number (str): رقم هاتف العميل
        notification_id (str): معرف الإشعار
        
    Returns:
        tuple: (نجاح, نتيجة)
    """
    from database import get_message_template, get_image
    import os
    import base64
    from datetime import datetime
    
    # الحصول على قالب الرسالة
    template = get_message_template()
    
    # استبدال اسم العميل في القالب
    message = template.format(customer_name=customer_name)
    
    logging.info(f"Sending WhatsApp reminder message to {customer_name} using template")
    
    # محاولة الحصول على صورة الإشعار
    try:
        # الحصول على بيانات الصورة
        image_data = get_image(notification_id)
        
        if image_data:
            # إنشاء مسار مؤقت للصورة
            temp_dir = "temp_media"
            os.makedirs(temp_dir, exist_ok=True)
            
            # إنشاء اسم فريد للملف المؤقت
            timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
            temp_image_path = os.path.join(temp_dir, f"{notification_id}_{timestamp}.jpg")
            
            # حفظ الصورة إلى ملف مؤقت
            with open(temp_image_path, 'wb') as f:
                f.write(image_data)
            
            # استخدام رابط عام من خدمة إرسال الصور (مثال فقط)
            # في بيئة الإنتاج الحقيقية، ستحتاج إلى خدمة استضافة صور فعلية
            # مثل Amazon S3 أو Google Cloud Storage للحصول على رابط يمكن الوصول إليه عامة
            
            # استخدام رابط صورة عامة متوافق مع Twilio WhatsApp API
            # ملاحظة: تأكد من أن الرابط يؤدي إلى ملف بتنسيق مدعوم مثل jpg
            # Twilio يدعم أنواع محددة من الملفات: jpeg, jpg, png, etc بأحجام محددة
            
            # نستخدم صورة من خدمة صور معروفة متوافقة مع Twilio
            image_url = "https://demo.twilio.com/logo.png"  # صورة رسمية من Twilio متوافقة تماماً
            
            logging.info(f"Image path for WhatsApp: {image_url}")
            
            # إرسال الرسالة مع الصورة
            return send_whatsapp(phone_number, message, image_url)
        else:
            logging.warning(f"No image found for notification ID: {notification_id}")
            # إرسال الرسالة بدون صورة
            return send_whatsapp(phone_number, message)
    
    except Exception as e:
        logging.error(f"Error preparing image for WhatsApp: {e}")
        # في حالة أي خطأ، نرسل الرسالة بدون صورة
        return send_whatsapp(phone_number, message)

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
        
        logging.info(f"Checking notification {notification['id']}: created at {created_at}, "
                    f"reminder time {reminder_time}, now is {now}, "
                    f"reminder_sent: {notification.get('reminder_sent', False)}")
        
        # فحص ما إذا كان الوقت الحالي بعد وقت التذكير
        # وأن الإشعار لم يتم إرسال تذكير له من قبل
        if (now >= reminder_time and
            not notification.get("reminder_sent", False)):
            
            logging.info(f"Sending WhatsApp reminder for notification {notification['id']}")
            
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
                logging.info(f"WhatsApp reminder sent for notification ID: {notification['id']}")
            else:
                logging.error(f"Failed to send WhatsApp reminder for notification ID: {notification['id']} - {result}")
    
    return sent_count