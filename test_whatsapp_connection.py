import os
import logging
from twilio.rest import Client

# تكوين السجل (logging)
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')

# بيانات الاعتماد Twilio
TWILIO_ACCOUNT_SID = os.environ.get("TWILIO_ACCOUNT_SID")
TWILIO_AUTH_TOKEN = os.environ.get("TWILIO_AUTH_TOKEN")
TWILIO_PHONE_NUMBER = os.environ.get("TWILIO_PHONE_NUMBER")

def check_twilio_whatsapp_channel():
    """
    التحقق من حالة قناة WhatsApp في Twilio وعرض معلومات عن الحساب.
    """
    if not all([TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN, TWILIO_PHONE_NUMBER]):
        logging.error("Twilio configuration missing")
        return "معلومات حساب Twilio غير مكتملة."

    try:
        # إنشاء عميل Twilio
        client = Client(TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN)
        
        # التحقق من معلومات الحساب
        account_info = client.api.accounts(TWILIO_ACCOUNT_SID).fetch()
        logging.info(f"Account Status: {account_info.status}")
        logging.info(f"Account Type: {account_info.type}")
        
        # عرض معلومات الرقم
        try:
            phone_number = client.incoming_phone_numbers.list(phone_number=TWILIO_PHONE_NUMBER)
            if phone_number:
                logging.info(f"Phone Number Found: {phone_number[0].phone_number}")
                logging.info(f"Capabilities: {phone_number[0].capabilities}")
            else:
                logging.warning(f"Phone Number {TWILIO_PHONE_NUMBER} not found in your account")
        except Exception as e:
            logging.error(f"Error fetching phone number details: {e}")
        
        # محاولة الوصول إلى معلومات قناة WhatsApp
        try:
            # تكوين اسم القناة المتوقع لواتساب
            whatsapp_channel_sid = ""
            if TWILIO_PHONE_NUMBER and '+' in TWILIO_PHONE_NUMBER:
                whatsapp_channel_sid = f"whatsapp:{TWILIO_PHONE_NUMBER.replace('+', '')}"
            else:
                whatsapp_channel_sid = f"whatsapp:{TWILIO_PHONE_NUMBER}"
            
            # فحص جميع الرسائل المرسلة من هذا الرقم للتحقق من إمكانية استخدامه مع واتساب
            formatted_from_number = ""
            if TWILIO_PHONE_NUMBER:
                if TWILIO_PHONE_NUMBER.startswith("+"):
                    formatted_from_number = f"whatsapp:{TWILIO_PHONE_NUMBER}"
                else:
                    formatted_from_number = f"whatsapp:+{TWILIO_PHONE_NUMBER}"
                    
            messages = client.messages.list(from_=formatted_from_number)
            
            if messages:
                logging.info(f"Found {len(messages)} messages sent from WhatsApp channel")
                logging.info("WhatsApp channel is working properly")
            else:
                logging.info("No messages found from WhatsApp channel")
                logging.info("This could be normal if you haven't sent any messages yet")
            
            # اختبار ما إذا كان نوع الحساب يدعم WhatsApp Sandbox
            if account_info.type == "Trial":
                logging.info("This is a Trial account. It should support WhatsApp Sandbox.")
                logging.info("Check if you have joined the WhatsApp Sandbox by sending 'join <your-sandbox-code>' to your WhatsApp Sandbox number")
            
            return "تم التحقق من معلومات الحساب، راجع سجل التطبيق للتفاصيل."
            
        except Exception as e:
            logging.error(f"Error accessing WhatsApp channel information: {e}")
            return f"حدث خطأ أثناء التحقق من قناة واتساب: {e}"
        
    except Exception as e:
        logging.error(f"Error connecting to Twilio: {e}")
        return f"حدث خطأ أثناء الاتصال بـ Twilio: {e}"

if __name__ == "__main__":
    result = check_twilio_whatsapp_channel()
    print(result)