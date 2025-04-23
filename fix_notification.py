#!/usr/bin/env python
"""
سكريبت لإصلاح حالة الإشعار المحدد
"""
import json
import logging
from datetime import datetime

# إعداد التسجيل
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)

# مسار ملف الإشعارات
NOTIFICATIONS_DB = "data/notifications.json"

def fix_notification(notification_id):
    """
    إصلاح حالة إشعار محدد
    """
    try:
        # قراءة ملف الإشعارات
        with open(NOTIFICATIONS_DB, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        found = False
        # البحث عن الإشعار المحدد
        for notification in data['notifications']:
            if notification['id'] == notification_id:
                found = True
                # تحديث حالة الإشعار
                notification['reminder_sent'] = True
                notification['reminder_sent_at'] = datetime.now().isoformat()
                print(f"✅ تم تحديث حالة الإشعار: {notification_id}")
                print(f"معلومات الإشعار:")
                print(f"- اسم العميل: {notification['customer_name']}")
                print(f"- رقم الهاتف: {notification['phone_number']}")
                print(f"- وقت الإنشاء: {notification['created_at']}")
                print(f"- حالة الإرسال: {notification['reminder_sent']}")
                print(f"- وقت الإرسال: {notification['reminder_sent_at']}")
                break
        
        if not found:
            print(f"⚠️ لم يتم العثور على الإشعار: {notification_id}")
            return False
        
        # حفظ التغييرات
        with open(NOTIFICATIONS_DB, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        
        return True
        
    except Exception as e:
        print(f"❌ حدث خطأ: {e}")
        return False

if __name__ == "__main__":
    # معرف الإشعار المطلوب إصلاحه
    notification_id = "310a9855-7e25-462b-8b01-1de17d25acca"
    
    print(f"🔧 جاري إصلاح حالة الإشعار: {notification_id}")
    
    if fix_notification(notification_id):
        print("✅ تم إصلاح حالة الإشعار بنجاح!")
    else:
        print("❌ فشل في إصلاح حالة الإشعار!")