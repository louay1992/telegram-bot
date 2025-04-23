import os
import logging
from twilio.rest import Client

# تكوين السجل (logging)
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')

# بيانات الاعتماد Twilio
TWILIO_ACCOUNT_SID = os.environ.get("TWILIO_ACCOUNT_SID")
TWILIO_AUTH_TOKEN = os.environ.get("TWILIO_AUTH_TOKEN")
TWILIO_PHONE_NUMBER = os.environ.get("TWILIO_PHONE_NUMBER")

def check_twilio_whatsapp_sandbox():
    """
    التحقق من إعدادات Sandbox لواتساب في Twilio.
    """
    if not all([TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN]):
        print("معلومات حساب Twilio غير مكتملة.")
        return

    try:
        # إنشاء عميل Twilio
        client = Client(TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN)
        
        # التحقق من معلومات الحساب
        account = client.api.accounts(TWILIO_ACCOUNT_SID).fetch()
        print(f"حالة الحساب: {account.status}")
        print(f"نوع الحساب: {account.type}")
        
        # عرض الرقم المخزن في المتغير البيئي
        print(f"\nرقم الهاتف المخزن في المتغير البيئي: {TWILIO_PHONE_NUMBER}")
        
        # الحصول على قائمة أرقام الهاتف الواردة
        incoming_numbers = client.incoming_phone_numbers.list()
        print(f"\nأرقام الهاتف المرتبطة بالحساب ({len(incoming_numbers)}):")
        for number in incoming_numbers:
            print(f"- {number.phone_number} (SID: {number.sid})")
        
        # البحث عن معلومات قناة واتساب
        print("\nجاري البحث عن معلومات قناة واتساب...")
        
        # محاولة استرداد معلومات واتساب من مكالمات REST متعددة
        # التحقق من خدمات الرسائل
        try:
            # الحصول على الخدمات المخصصة لرسائل واتساب
            services = client.messaging.services.list()
            print(f"\nخدمات الرسائل المكونة ({len(services)}):")
            for service in services:
                print(f"- {service.friendly_name} (SID: {service.sid})")
                
            # الحصول على قنوات واتساب المخصصة
            print("\nمحاولة الحصول على معلومات قنوات واتساب...")
            # لاحظ: هذا قد لا يعمل مباشرة في API العام، ولكن يمكن أن يساعد في فهم المشكلة
            
            # طريقة أخرى - البحث في الرسائل المرسلة مسبقاً
            print("\nآخر الرسائل المرسلة:")
            messages = client.messages.list(limit=5)
            for msg in messages:
                print(f"- من: {msg.from_} إلى: {msg.to} (الحالة: {msg.status})")
            
            # البحث عن معلومات خاصة بـ Sandbox
            print("\nنصائح لاستخدام WhatsApp Sandbox:")
            print("1. تأكد من أن الرقم المستخدم في المتغير البيئي هو نفس رقم واتساب Sandbox.")
            print("2. قم بزيارة لوحة تحكم Twilio والانتقال إلى قسم واتساب للاطلاع على رقم Sandbox الخاص بك.")
            print("3. استخدم تنسيق الرقم بالشكل الصحيح: whatsapp:+1XXXXXXXXXX")
            
            # مثال على الشكل الصحيح لرقم واتساب Sandbox
            whatsapp_number = f"whatsapp:{TWILIO_PHONE_NUMBER}"
            if not TWILIO_PHONE_NUMBER.startswith("+"):
                whatsapp_number = f"whatsapp:+{TWILIO_PHONE_NUMBER}"
                
            print(f"\nتنسيق الرقم المستخدم حالياً في الكود: {whatsapp_number}")
            print("تأكد من أن هذا يطابق رقم واتساب Sandbox في لوحة تحكم Twilio.")
            
        except Exception as e:
            print(f"حدث خطأ أثناء البحث عن معلومات واتساب: {e}")
    
    except Exception as e:
        print(f"حدث خطأ أثناء الاتصال بـ Twilio: {e}")

if __name__ == "__main__":
    print("التحقق من إعدادات Twilio WhatsApp Sandbox...")
    check_twilio_whatsapp_sandbox()