#!/usr/bin/env python
"""
سكريبت اختبار لإرسال رسالة واتساب باستخدام UltraMsg API
"""
import os
import sys
from ultramsg_service import send_whatsapp_message, send_whatsapp_image
from database import get_image

# رقم الهاتف المستلم (الرقم الذي تم توفيره)
PHONE_NUMBER = "+963933000227"

# نص الرسالة
MESSAGE = "هذه رسالة اختبار من بوت الإشعارات 🎉\nتم إرسالها باستخدام UltraMsg API"

def main():
    print(f"🚀 إرسال رسالة اختبار إلى الرقم: {PHONE_NUMBER}")
    
    # اختبار إرسال رسالة نصية
    success, result = send_whatsapp_message(PHONE_NUMBER, MESSAGE)
    
    if success:
        print(f"✅ تم إرسال الرسالة النصية بنجاح!")
        print(f"النتيجة: {result}")
    else:
        print(f"❌ فشل إرسال الرسالة النصية!")
        print(f"الخطأ: {result}")
        return 1
    
    # الحصول على آخر إشعار لإرسال صورته
    notifications = []
    try:
        import json
        import database as db
        notifications_data = db.load_json(db.NOTIFICATIONS_DB, {"notifications": []})
        notifications = notifications_data.get("notifications", [])
    except Exception as e:
        print(f"⚠️ خطأ في قراءة الإشعارات: {e}")
    
    if notifications:
        last_notification = notifications[-1]
        notification_id = last_notification["id"]
        print(f"🖼️ جاري إرسال صورة الإشعار رقم: {notification_id}")
        
        # الحصول على صورة الإشعار
        image_data = get_image(notification_id)
        
        if image_data:
            # اختبار إرسال صورة
            success, result = send_whatsapp_image(
                PHONE_NUMBER, 
                image_data, 
                caption=f"صورة إشعار الشحن للعميل: {last_notification.get('customer_name')}"
            )
            
            if success:
                print(f"✅ تم إرسال الصورة بنجاح!")
                print(f"النتيجة: {result}")
            else:
                print(f"❌ فشل إرسال الصورة!")
                print(f"الخطأ: {result}")
                return 1
        else:
            print("⚠️ لم يتم العثور على صورة للإشعار")
    else:
        print("⚠️ لم يتم العثور على إشعارات")
    
    return 0

if __name__ == "__main__":
    sys.exit(main())