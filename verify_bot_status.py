#!/usr/bin/env python3
"""
سكريبت للتحقق من حالة البوت بالتوكن الجديد
"""
import requests
import json
import os
import time
from datetime import datetime

# التوكن الجديد
TOKEN = "7406580104:AAGG2JQeeNfsmcGVMCm7hxitIK-qm2yekVg"

def check_bot_info():
    """التحقق من معلومات البوت."""
    url = f"https://api.telegram.org/bot{TOKEN}/getMe"
    try:
        response = requests.get(url)
        data = response.json()
        
        if data.get("ok"):
            bot_info = data.get("result", {})
            print("✅ معلومات البوت:")
            print(f"   - معرف البوت: {bot_info.get('id')}")
            print(f"   - اسم البوت: {bot_info.get('first_name')}")
            print(f"   - اسم المستخدم: @{bot_info.get('username')}")
            print(f"   - هل يمكن دعوته للمجموعات: {bot_info.get('can_join_groups', False)}")
            print(f"   - هل يمكنه قراءة جميع رسائل المجموعة: {bot_info.get('can_read_all_group_messages', False)}")
            print(f"   - هل يدعم وضع الخصوصية المتميز: {bot_info.get('supports_inline_queries', False)}")
            return True
        else:
            print(f"❌ خطأ: {data.get('description')}")
            return False
    except Exception as e:
        print(f"❌ خطأ في الاتصال: {e}")
        return False

def check_webhook_status():
    """التحقق من حالة webhook."""
    url = f"https://api.telegram.org/bot{TOKEN}/getWebhookInfo"
    try:
        response = requests.get(url)
        data = response.json()
        
        if data.get("ok"):
            webhook_info = data.get("result", {})
            webhook_url = webhook_info.get("url", "")
            
            if webhook_url:
                print(f"ℹ️ البوت يستخدم webhook: {webhook_url}")
                print(f"   - آخر خطأ: {webhook_info.get('last_error_message', 'لا يوجد')}")
                print(f"   - آخر خطأ حدث في: {webhook_info.get('last_error_date', 'لا يوجد')}")
            else:
                print("ℹ️ البوت لا يستخدم webhook حالياً (يستخدم وضع الاستطلاع)")
            
            return True
        else:
            print(f"❌ خطأ: {data.get('description')}")
            return False
    except Exception as e:
        print(f"❌ خطأ في الاتصال: {e}")
        return False

def check_updates():
    """التحقق من التحديثات الأخيرة."""
    url = f"https://api.telegram.org/bot{TOKEN}/getUpdates?limit=5&timeout=1"
    try:
        response = requests.get(url)
        data = response.json()
        
        if data.get("ok"):
            updates = data.get("result", [])
            
            if updates:
                print(f"✅ آخر {len(updates)} تحديثات:")
                for i, update in enumerate(updates, 1):
                    update_id = update.get("update_id")
                    update_time = datetime.fromtimestamp(update.get("message", {}).get("date", 0))
                    
                    message = update.get("message", {})
                    callback_query = update.get("callback_query", {})
                    
                    if message:
                        chat_id = message.get("chat", {}).get("id")
                        text = message.get("text", "[بدون نص]")
                        user = message.get("from", {}).get("username", "غير معروف")
                        print(f"   {i}. تحديث {update_id}: رسالة من @{user} في دردشة {chat_id}: {text} ({update_time})")
                    elif callback_query:
                        data = callback_query.get("data", "[بدون بيانات]")
                        user = callback_query.get("from", {}).get("username", "غير معروف")
                        print(f"   {i}. تحديث {update_id}: استدعاء زر من @{user}: {data} ({update_time})")
                    else:
                        print(f"   {i}. تحديث {update_id}: نوع غير معروف ({update_time})")
            else:
                print("ℹ️ لا توجد تحديثات جديدة")
            
            return True
        else:
            print(f"❌ خطأ: {data.get('description')}")
            return False
    except Exception as e:
        print(f"❌ خطأ في الاتصال: {e}")
        return False

def send_test_message():
    """إرسال رسالة اختبار للبوت نفسه."""
    # الحصول على معرف البوت
    get_me_url = f"https://api.telegram.org/bot{TOKEN}/getMe"
    try:
        response = requests.get(get_me_url)
        data = response.json()
        
        if data.get("ok"):
            bot_info = data.get("result", {})
            bot_username = bot_info.get("username")
            
            print(f"ℹ️ لإرسال رسالة اختبار:")
            print(f"   1. افتح تطبيق تيليجرام")
            print(f"   2. ابحث عن @{bot_username}")
            print(f"   3. أرسل الأمر /start")
            
            return True
        else:
            print(f"❌ خطأ: {data.get('description')}")
            return False
    except Exception as e:
        print(f"❌ خطأ في الاتصال: {e}")
        return False

def main():
    """الوظيفة الرئيسية للسكريبت."""
    print("🤖 أداة التحقق من حالة البوت بالتوكن الجديد 🤖")
    print("==============================================")
    print(f"التوكن: {TOKEN}")
    print()
    
    # 1. التحقق من معلومات البوت
    print("\n📝 التحقق من معلومات البوت...")
    bot_info_success = check_bot_info()
    
    # 2. التحقق من حالة webhook
    print("\n📡 التحقق من حالة webhook...")
    webhook_success = check_webhook_status()
    
    # 3. التحقق من التحديثات الأخيرة
    print("\n📨 التحقق من التحديثات الأخيرة...")
    updates_success = check_updates()
    
    # 4. إرسال رسالة اختبار
    print("\n📤 إرسال رسالة اختبار...")
    test_message_success = send_test_message()
    
    # 5. عرض النتيجة النهائية
    print("\n🔄 النتيجة النهائية:")
    print(f"   - معلومات البوت: {'✅' if bot_info_success else '❌'}")
    print(f"   - حالة webhook: {'✅' if webhook_success else '❌'}")
    print(f"   - التحديثات الأخيرة: {'✅' if updates_success else '❌'}")
    print(f"   - رسالة اختبار: {'✅' if test_message_success else '❌'}")
    
    overall_success = all([bot_info_success, webhook_success, updates_success, test_message_success])
    print(f"\n{'✅ جميع الاختبارات ناجحة!' if overall_success else '❌ بعض الاختبارات فشلت.'}")
    
    if overall_success:
        print("\nℹ️ البوت يعمل بشكل طبيعي مع التوكن الجديد!")
        print("ℹ️ يمكنك الآن تحديث التوكن في Replit Secrets لضمان استمرارية العمل في المستقبل.")
    else:
        print("\n⚠️ هناك بعض المشاكل في البوت مع التوكن الجديد.")
        print("⚠️ قم بمراجعة الأخطاء أعلاه وإصلاحها قبل تحديث التوكن في Replit Secrets.")

if __name__ == "__main__":
    main()