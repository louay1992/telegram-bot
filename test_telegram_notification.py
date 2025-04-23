"""
سكريبت اختبار إرسال إشعارات تيليجرام للمشرفين.
استخدم هذا السكريبت لاختبار إعدادات التنبيهات قبل دمجها في نظام المراقبة.
"""

import os
import sys
import json
import requests
from datetime import datetime


def send_telegram_notification(message, alert_type="info"):
    """
    إرسال إشعارات للمشرف عبر Telegram
    
    Args:
        message (str): نص الرسالة
        alert_type (str): نوع التنبيه (error/warning/info/success)
    """
    # التحقق من وجود المتغيرات البيئية المطلوبة
    TELEGRAM_BOT_TOKEN = os.environ.get("ADMIN_BOT_TOKEN", os.environ.get("TELEGRAM_BOT_TOKEN"))
    ADMIN_CHAT_ID = os.environ.get("ADMIN_CHAT_ID")
    
    if not TELEGRAM_BOT_TOKEN or not ADMIN_CHAT_ID:
        print("⚠️ لم يتم تكوين رمز البوت أو معرف الدردشة للإشعارات.")
        print(f"TELEGRAM_BOT_TOKEN: {'✓ متاح' if TELEGRAM_BOT_TOKEN else '✗ غير متاح'}")
        print(f"ADMIN_CHAT_ID: {'✓ متاح' if ADMIN_CHAT_ID else '✗ غير متاح'}")
        return False
    
    # إضافة رموز تعبيرية حسب نوع التنبيه
    icon = {
        "error": "🚨",
        "warning": "⚠️",
        "info": "ℹ️",
        "success": "✅"
    }.get(alert_type, "ℹ️")
    
    # تكوين الرسالة النهائية
    formatted_message = f"{icon} *اختبار نظام الإشعارات* {icon}\n\n{message}\n\n⏰ {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
    
    try:
        url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
        data = {
            "chat_id": ADMIN_CHAT_ID,
            "text": formatted_message,
            "parse_mode": "Markdown"
        }
        
        print(f"🔄 جاري إرسال الرسالة إلى معرف الدردشة: {ADMIN_CHAT_ID}")
        response = requests.post(url, data=data, timeout=10)
        
        if response.status_code == 200:
            result = response.json()
            print(f"✅ تم إرسال الإشعار بنجاح! (معرف الرسالة: {result.get('result', {}).get('message_id', 'غير معروف')})")
            return True
        else:
            print(f"⚠️ فشل في إرسال الإشعار (كود {response.status_code})")
            print(f"الاستجابة: {response.text}")
            return False
    except Exception as e:
        print(f"❌ خطأ أثناء إرسال الإشعار: {e}")
        return False


def setup_environment_variables():
    """
    إعداد متغيرات البيئة للاختبار
    """
    values = {}
    if "ADMIN_BOT_TOKEN" not in os.environ and "TELEGRAM_BOT_TOKEN" not in os.environ:
        values["ADMIN_BOT_TOKEN"] = input("الرجاء إدخال رمز بوت تيليجرام (ADMIN_BOT_TOKEN): ").strip()
    
    if "ADMIN_CHAT_ID" not in os.environ:
        values["ADMIN_CHAT_ID"] = input("الرجاء إدخال معرف الدردشة أو المستخدم (ADMIN_CHAT_ID): ").strip()
    
    for key, value in values.items():
        os.environ[key] = value
    
    return bool(values)


def main():
    """
    الوظيفة الرئيسية
    """
    print("🚀 اختبار نظام إشعارات تيليجرام للمشرفين")
    print("=" * 50)
    
    # التحقق من وجود متغيرات البيئة
    setup_needed = setup_environment_variables()
    
    # إذا تم إعداد متغيرات البيئة، قم بعرض رسالة توضيحية
    if setup_needed:
        print("\n✅ تم إعداد متغيرات البيئة بنجاح!")
        print("ملاحظة: هذه المتغيرات متاحة فقط لهذه الجلسة. لتعيينها بشكل دائم:")
        print("1. أضفها في ملف .env")
        print("2. أو استخدم لوحة تحكم Replit لإضافة الأسرار\n")
    
    # قائمة بأنواع الإشعارات المتاحة للاختبار
    alert_types = ["info", "success", "warning", "error"]
    
    # عرض الخيارات المتاحة
    print("\nأنواع الإشعارات المتاحة للاختبار:")
    for i, alert_type in enumerate(alert_types, 1):
        print(f"{i}. {alert_type}")
    
    try:
        # اختيار نوع الإشعار
        choice = int(input("\nاختر نوع الإشعار (1-4): "))
        if choice < 1 or choice > len(alert_types):
            raise ValueError("اختيار غير صالح")
        
        selected_type = alert_types[choice-1]
        
        # إدخال نص الإشعار
        message = input("\nأدخل نص الإشعار (أو اضغط Enter للنص الافتراضي): ")
        if not message:
            message = f"هذا اختبار لنظام الإشعارات من نوع '{selected_type}'. إذا تلقيت هذه الرسالة، فإن النظام يعمل بشكل صحيح!"
        
        # إرسال الإشعار
        print("\n🔄 جاري إرسال الإشعار...")
        sent = send_telegram_notification(message, selected_type)
        
        if sent:
            print("\n✅ تم إرسال الإشعار بنجاح! تحقق من تطبيق تيليجرام.")
        else:
            print("\n❌ فشل في إرسال الإشعار. راجع الأخطاء أعلاه.")
        
    except ValueError as e:
        print(f"\n❌ خطأ: {e}")
    except KeyboardInterrupt:
        print("\n\n⚠️ تم إلغاء الاختبار.")
    
    print("\n🏁 انتهى اختبار نظام الإشعارات")


if __name__ == "__main__":
    main()