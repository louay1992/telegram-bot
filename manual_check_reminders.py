#!/usr/bin/env python
"""
سكريبت للتحقق اليدوي من التذكيرات المجدولة وإرسالها باستخدام UltraMsg
"""
import os
import sys
import logging
from datetime import datetime, timedelta

# إعداد التسجيل
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)

# استيراد الوحدات اللازمة
import database as db
import ultramsg_service

def main():
    """التحقق اليدوي من التذكيرات وإرسالها."""
    print("🔍 التحقق من الإشعارات المجدولة للتذكير...")
    
    # الحصول على جميع الإشعارات
    notifications = db.get_all_notifications()
    
    if not notifications:
        print("⚠️ لا توجد إشعارات للتحقق منها")
        return 0
    
    print(f"📋 العدد الإجمالي للإشعارات: {len(notifications)}")
    
    # استخدام UltraMsg للتحقق وإرسال التذكيرات
    sent_count = ultramsg_service.check_and_send_scheduled_reminders(notifications)
    
    # حفظ التحديثات في قاعدة البيانات
    db.save_json(db.NOTIFICATIONS_DB, {"notifications": notifications})
    
    if sent_count > 0:
        print(f"✅ تم إرسال {sent_count} تذكير(ات)")
    else:
        print("ℹ️ لم يتم إرسال أي تذكيرات في هذا الوقت")
    
    # طباعة حالة كل إشعار للتشخيص
    print("\n📊 حالة جميع الإشعارات:")
    now = datetime.now()
    for notification in notifications:
        notification_id = notification['id']
        customer_name = notification['customer_name']
        
        # حساب وقت التذكير
        reminder_hours = notification.get('reminder_hours', 0)
        created_at = datetime.fromisoformat(notification['created_at'])
        reminder_time = created_at + timedelta(hours=reminder_hours)
        
        reminder_sent = notification.get('reminder_sent', False)
        time_diff = now - reminder_time
        
        status = "✅ تم إرسال التذكير" if reminder_sent else "❌ لم يتم إرسال التذكير بعد"
        if reminder_hours <= 0:
            status = "⏸️ التذكير معطل"
        elif not reminder_sent and now >= reminder_time:
            status = "⚠️ تأخر إرسال التذكير"
        
        print(f"- {notification_id[:8]}: {customer_name}")
        print(f"  • وقت الإنشاء: {created_at}")
        print(f"  • وقت التذكير: {reminder_time}")
        print(f"  • الوقت الحالي: {now}")
        print(f"  • الحالة: {status}")
        if not reminder_sent and reminder_hours > 0:
            if now >= reminder_time:
                print(f"  • متأخر بـ: {time_diff}")
            else:
                print(f"  • متبقي: {reminder_time - now}")
        print("")
    
    return 0

if __name__ == "__main__":
    sys.exit(main())