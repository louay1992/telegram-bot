#!/usr/bin/env python
"""
سكريبت اختبار لإرسال رسالة ترحيبية فورية عند إضافة إشعار جديد
"""
import os
import sys
import logging
from datetime import datetime

# إعداد التسجيل
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)

# استيراد الوحدات اللازمة
import ultramsg_service

def main():
    """اختبار إرسال رسالة ترحيبية فورية."""
    # معرف الإشعار الأخير المضاف (استبدله بمعرف حقيقي من قاعدة البيانات)
    notification_id = "310a9855-7e25-462b-8b01-1de17d25acca"
    customer_name = "محمد لؤي"
    phone_number = "0933000227"
    
    print(f"🚀 إرسال رسالة ترحيبية فورية إلى {customer_name} ({phone_number})")
    
    # استدعاء دالة إرسال الرسالة الترحيبية
    success, result = ultramsg_service.send_welcome_message(
        customer_name,
        phone_number,
        notification_id
    )
    
    if success:
        print("✅ تم إرسال الرسالة الترحيبية بنجاح!")
        print(f"النتيجة: {result}")
    else:
        print("❌ فشل في إرسال الرسالة الترحيبية!")
        print(f"سبب الخطأ: {result}")
    
    return 0

if __name__ == "__main__":
    sys.exit(main())