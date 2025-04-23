import os
import logging
from twilio.rest import Client
from datetime import datetime

# تكوين السجل (logging)
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')

# رقم الهاتف المستهدف
TARGET_PHONE = "+963933000227"

# استخدام رقم واتساب Sandbox القياسي
TWILIO_WHATSAPP_SANDBOX_NUMBER = "+14155238886"

# بيانات اعتماد Twilio
TWILIO_ACCOUNT_SID = os.environ.get("TWILIO_ACCOUNT_SID")
TWILIO_AUTH_TOKEN = os.environ.get("TWILIO_AUTH_TOKEN")

def send_test_whatsapp():
    """
    إرسال رسالة اختبار مباشرة عبر واتساب.
    """
    if not all([TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN]):
        logging.error("Twilio configuration missing")
        return "معلومات حساب Twilio غير مكتملة."

    try:
        # تنسيق أرقام واتساب
        from_whatsapp = f"whatsapp:{TWILIO_WHATSAPP_SANDBOX_NUMBER}"
        to_whatsapp = f"whatsapp:{TARGET_PHONE}"
        
        # طباعة المعلومات للتأكيد
        print(f"إرسال من: {from_whatsapp}")
        print(f"إرسال إلى: {to_whatsapp}")
        
        # إنشاء عميل Twilio
        client = Client(TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN)
        
        # تحضير رسالة اختبار
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        message_text = f"مرحباً! هذه رسالة تذكير اختبارية من بوت إشعارات الشحن.\n\nتم إرسالها في: {now}\n\nشكراً لاستخدامك خدمتنا!"
        
        # إضافة رابط صورة متوافق مع Twilio للاختبار
        # استخدام صورة رسمية من Twilio معروف أنها متوافقة مع WhatsApp API
        image_url = "https://demo.twilio.com/logo.png"
        
        # إرسال الرسالة مع صورة
        message = client.messages.create(
            body=message_text,
            from_=from_whatsapp,
            to=to_whatsapp,
            media_url=[image_url]
        )
        
        print(f"تم إرسال الرسالة بنجاح! معرف الرسالة: {message.sid}")
        return True
    
    except Exception as e:
        print(f"حدث خطأ أثناء الإرسال: {e}")
        return False

if __name__ == "__main__":
    print("=== اختبار إرسال رسالة واتساب ===")
    print(f"رقم الهاتف المستهدف: {TARGET_PHONE}")
    print("\nجارِ إرسال الرسالة...")
    result = send_test_whatsapp()
    
    if result is True:
        print("\n✅ تم إرسال الرسالة بنجاح!")
        print("\nملاحظة هامة:")
        print("إذا لم تصل الرسالة، تأكد من أنك قمت بالانضمام إلى Sandbox عن طريق إرسال")
        print("رسالة 'join <كود-الانضمام>' إلى رقم Twilio WhatsApp Sandbox: +14155238886")
    else:
        print("\n❌ فشل إرسال الرسالة، راجع السجلات للمزيد من المعلومات.")