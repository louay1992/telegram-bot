import os
import logging
from twilio.rest import Client

# تكوين السجل (logging)
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')

# بيانات الاعتماد Twilio
TWILIO_ACCOUNT_SID = os.environ.get("TWILIO_ACCOUNT_SID")
TWILIO_AUTH_TOKEN = os.environ.get("TWILIO_AUTH_TOKEN")

# استخدام رقم واتساب Sandbox القياسي من Twilio
TWILIO_WHATSAPP_SANDBOX_NUMBER = "+14155238886"

def send_whatsapp_test(to_phone_number, message, media_url=None):
    """
    اختبار إرسال رسالة واتساب إلى رقم هاتف محدد باستخدام رقم Sandbox.
    """
    if not all([TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN]):
        logging.error("Twilio configuration missing")
        return "معلومات حساب Twilio غير مكتملة."

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
        from_whatsapp_number = f"whatsapp:{TWILIO_WHATSAPP_SANDBOX_NUMBER}"
        to_whatsapp_number = f"whatsapp:{cleaned_phone}"
        
        # سجل التنسيق النهائي للأرقام
        logging.info(f"Test: Formatted FROM WhatsApp Sandbox number: {from_whatsapp_number}")
        logging.info(f"Test: Formatted TO WhatsApp number: {to_whatsapp_number}")
        
        # إنشاء عميل Twilio
        client = Client(TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN)
        
        # إرسال رسالة واتساب
        if media_url:
            logging.info(f"Test: Sending WhatsApp message with media: {media_url}")
            message_obj = client.messages.create(
                body=message,
                from_=from_whatsapp_number,
                to=to_whatsapp_number,
                media_url=[media_url]
            )
        else:
            logging.info("Test: Sending WhatsApp message without media")
            message_obj = client.messages.create(
                body=message,
                from_=from_whatsapp_number,
                to=to_whatsapp_number
            )
        
        logging.info(f"Test: WhatsApp message sent to {cleaned_phone}, SID: {message_obj.sid}")
        return f"تم إرسال رسالة واتساب بنجاح إلى الرقم {cleaned_phone} بمعرف {message_obj.sid}"
    
    except Exception as e:
        logging.error(f"Test: Error sending WhatsApp message: {e}")
        return f"حدث خطأ أثناء إرسال رسالة واتساب: {e}"

if __name__ == "__main__":
    print("\n=== اختبار باستخدام رقم Sandbox القياسي (+14155238886) ===\n")
    
    # رقم الهاتف المستهدف
    target_phone = "+963933000227"
    
    # رسالة الاختبار
    test_message = "هذه رسالة اختبار من تطبيق إشعارات الشحن باستخدام رقم Sandbox. نشكرك على تعاونك!"
    
    # اختبار إرسال رسالة بدون صورة
    print("\n--- اختبار إرسال رسالة واتساب بدون صورة ---")
    result1 = send_whatsapp_test(target_phone, test_message)
    print(result1)
    
    # اختبار إرسال رسالة مع صورة
    print("\n--- اختبار إرسال رسالة واتساب مع صورة ---")
    # استخدام صورة متوافقة مع Twilio WhatsApp API
    test_image_url = "https://demo.twilio.com/logo.png"
    result2 = send_whatsapp_test(target_phone, test_message, test_image_url)
    print(result2)
    
    print("\n=== ملاحظة هامة ===")
    print("للاستخدام الصحيح لـ WhatsApp Sandbox، يجب أن يكون المستلم قد انضم إلى Sandbox عن طريق إرسال")
    print("رسالة 'join <رمز-الانضمام>' إلى رقم الـ Sandbox على واتساب.")
    print("يمكنك العثور على رمز الانضمام في لوحة تحكم Twilio في قسم WhatsApp Sandbox.")