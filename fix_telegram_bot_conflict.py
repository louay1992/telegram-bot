#!/usr/bin/env python
"""
أداة مساعدة لإصلاح تعارض Telegram Bot.

تقوم هذه الأداة بإلغاء تسجيل webhook وتأكيد أن البوت جاهز للعمل
بوضع polling (أو إعداد webhook).

استخدم هذه الأداة عندما ترى خطأ:
"Conflict: terminated by other getUpdates request; make sure that only one bot instance is running"
"""

import os
import sys
import time
import json
import argparse
import requests
from datetime import datetime

# تكوين الألوان لتنسيق المخرجات
GREEN = "\033[92m"
YELLOW = "\033[93m"
RED = "\033[91m"
BLUE = "\033[94m"
RESET = "\033[0m"

def get_token():
    """الحصول على رمز البوت من المتغيرات البيئية أو من المستخدم."""
    token = os.environ.get("TELEGRAM_BOT_TOKEN")
    
    if not token:
        print(f"{YELLOW}لم يتم العثور على رمز البوت في متغيرات البيئة{RESET}")
        token = input(f"{BLUE}أدخل رمز البوت (TELEGRAM_BOT_TOKEN): {RESET}").strip()
    
    return token

def get_webhook_info(token):
    """الحصول على معلومات webhook الحالية."""
    try:
        url = f"https://api.telegram.org/bot{token}/getWebhookInfo"
        response = requests.get(url)
        response.raise_for_status()
        return response.json()
    except Exception as e:
        print(f"{RED}خطأ في الحصول على معلومات webhook: {e}{RESET}")
        return None

def delete_webhook(token):
    """إلغاء تسجيل webhook."""
    try:
        url = f"https://api.telegram.org/bot{token}/deleteWebhook"
        response = requests.post(url)
        response.raise_for_status()
        return response.json()
    except Exception as e:
        print(f"{RED}خطأ في حذف webhook: {e}{RESET}")
        return None

def set_webhook(token, webhook_url):
    """تعيين webhook جديد."""
    try:
        url = f"https://api.telegram.org/bot{token}/setWebhook"
        data = {"url": webhook_url}
        response = requests.post(url, data=data)
        response.raise_for_status()
        return response.json()
    except Exception as e:
        print(f"{RED}خطأ في تعيين webhook: {e}{RESET}")
        return None

def test_getUpdates(token):
    """اختبار دالة getUpdates للتأكد من عدم وجود تعارض."""
    try:
        url = f"https://api.telegram.org/bot{token}/getUpdates"
        response = requests.post(url)
        response.raise_for_status()
        return response.json()
    except Exception as e:
        print(f"{RED}خطأ في استدعاء getUpdates: {e}{RESET}")
        return None

def test_getMe(token):
    """التحقق من صحة رمز البوت."""
    try:
        url = f"https://api.telegram.org/bot{token}/getMe"
        response = requests.get(url)
        response.raise_for_status()
        return response.json()
    except Exception as e:
        print(f"{RED}خطأ في استدعاء getMe: {e}{RESET}")
        return None

def main():
    # إنشاء محلل الأوامر
    parser = argparse.ArgumentParser(description="أداة إصلاح تعارض Telegram Bot")
    group = parser.add_mutually_exclusive_group()
    group.add_argument(
        "--webhook", 
        help="تعيين webhook جديد (مثال: https://example.com/webhook)"
    )
    group.add_argument(
        "--polling", 
        action="store_true", 
        help="إلغاء webhook والإعداد لوضع polling"
    )
    args = parser.parse_args()
    
    print(f"{BLUE}⭐️ أداة إصلاح تعارض Telegram Bot ⭐️{RESET}")
    print(f"{BLUE}{'=' * 50}{RESET}")
    
    # الحصول على رمز البوت
    token = get_token()
    if not token:
        print(f"{RED}لم يتم توفير رمز البوت. الخروج.{RESET}")
        sys.exit(1)
    
    # التحقق من صحة رمز البوت
    me_info = test_getMe(token)
    if not me_info or not me_info.get("ok"):
        print(f"{RED}⚠️ رمز البوت غير صالح أو البوت غير متاح!{RESET}")
        print(f"{RED}الاستجابة: {json.dumps(me_info, indent=2) if me_info else 'لا توجد استجابة'}{RESET}")
        sys.exit(1)
    
    bot_username = me_info.get("result", {}).get("username", "غير معروف")
    print(f"{GREEN}✅ تم التحقق من صحة رمز البوت! اسم البوت: @{bot_username}{RESET}")
    
    # الحصول على معلومات webhook الحالية
    webhook_info = get_webhook_info(token)
    if not webhook_info or not webhook_info.get("ok"):
        print(f"{RED}⚠️ لا يمكن الحصول على معلومات webhook! {webhook_info}{RESET}")
        sys.exit(1)
    
    current_webhook = webhook_info.get("result", {}).get("url", "لا يوجد")
    print(f"{BLUE}معلومات Webhook الحالية:{RESET}")
    print(f"URL: {current_webhook}")
    print(f"عدد التحديثات المعلقة: {webhook_info.get('result', {}).get('pending_update_count', 0)}")
    has_webhook = bool(current_webhook)
    
    # تطبيق الخيار المحدد
    if args.webhook:
        if args.webhook == current_webhook:
            print(f"{YELLOW}⚠️ Webhook الجديد مطابق للقيمة الحالية! لا حاجة للتغيير.{RESET}")
        else:
            # إلغاء webhook الحالي أولاً
            print(f"{BLUE}جاري إزالة webhook الحالي...{RESET}")
            delete_result = delete_webhook(token)
            if delete_result and delete_result.get("ok"):
                print(f"{GREEN}✅ تم حذف webhook الحالي بنجاح!{RESET}")
            else:
                print(f"{RED}⚠️ حدث خطأ أثناء حذف webhook: {delete_result}{RESET}")
            
            # تعيين webhook الجديد
            print(f"{BLUE}جاري تعيين webhook جديد: {args.webhook}{RESET}")
            set_result = set_webhook(token, args.webhook)
            if set_result and set_result.get("ok"):
                print(f"{GREEN}✅ تم تعيين webhook الجديد بنجاح!{RESET}")
            else:
                print(f"{RED}⚠️ حدث خطأ أثناء تعيين webhook: {set_result}{RESET}")
    elif args.polling or has_webhook:
        if has_webhook:
            # إلغاء webhook
            print(f"{BLUE}جاري إلغاء webhook للسماح بوضع polling...{RESET}")
            delete_result = delete_webhook(token)
            if delete_result and delete_result.get("ok"):
                print(f"{GREEN}✅ تم إلغاء webhook بنجاح!{RESET}")
            else:
                print(f"{RED}⚠️ حدث خطأ أثناء إلغاء webhook: {delete_result}{RESET}")
        
        # اختبار getUpdates
        print(f"{BLUE}اختبار getUpdates للتأكد من عدم وجود تعارض...{RESET}")
        updates_result = test_getUpdates(token)
        if updates_result and updates_result.get("ok"):
            print(f"{GREEN}✅ تم اختبار getUpdates بنجاح! البوت جاهز لوضع polling.{RESET}")
        else:
            print(f"{RED}⚠️ لا يزال هناك تعارض مع getUpdates: {updates_result}{RESET}")
            
            # محاولة عدة مرات
            for attempt in range(3):
                print(f"{YELLOW}محاولة إضافية {attempt+1}/3 بعد 5 ثوانٍ من الانتظار...{RESET}")
                time.sleep(5)
                
                updates_result = test_getUpdates(token)
                if updates_result and updates_result.get("ok"):
                    print(f"{GREEN}✅ تم اختبار getUpdates بنجاح! البوت جاهز الآن لوضع polling.{RESET}")
                    break
            else:
                print(f"{RED}⚠️ لا يزال التعارض موجوداً بعد عدة محاولات.{RESET}")
                print(f"{YELLOW}نصائح للإصلاح:{RESET}")
                print(f"{YELLOW}1. تأكد من أن جميع نسخ البوت الأخرى متوقفة تماماً{RESET}")
                print(f"{YELLOW}2. قد تحتاج للانتظار بضع دقائق حتى يتم تحرير الاتصال من جانب Telegram{RESET}")
                print(f"{YELLOW}3. إذا كان لديك خادم ويب، تأكد من أنه لا يتلقى تحديثات webhook من Telegram{RESET}")
    else:
        print(f"{BLUE}الحالة الحالية:{RESET}")
        print(f"{GREEN}✅ لا يوجد webhook مسجّل حالياً.{RESET}")
        print(f"{GREEN}✅ البوت جاهز لوضع polling.{RESET}")
    
    # عرض تعليمات إضافية
    print(f"\n{BLUE}ما الذي يجب عليك فعله الآن:{RESET}")
    if args.webhook:
        print(f"{GREEN}1. تأكد من أن الخادم الخاص بك جاهز لاستقبال تحديثات webhook{RESET}")
        print(f"{GREEN}2. استخدم وضع webhook في تطبيقك بدلاً من polling{RESET}")
        print(f"{GREEN}3. يمكنك استخدام app.py الذي يستقبل التحديثات عبر webhook{RESET}")
    else:
        print(f"{GREEN}1. تأكد من تعطيل جميع مثيلات سيرفر التطبيق (app.py){RESET}")
        print(f"{GREEN}2. استخدم وضع polling في تطبيقك بدلاً من webhook{RESET}")
        print(f"{GREEN}3. يمكنك تشغيل bot.py فقط للعمل بوضع polling{RESET}")
    
    print(f"\n{BLUE}ملاحظة مهمة:{RESET}")
    print(f"{YELLOW}يجب استخدام طريقة واحدة فقط للاتصال: إما polling أو webhook، وليس كليهما معاً!{RESET}")

if __name__ == "__main__":
    main()