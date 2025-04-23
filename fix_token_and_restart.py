#!/usr/bin/env python3
"""
سكريبت شامل لحل مشكلة توكن التلغرام وإعادة تشغيل البوت
"""
import os
import sys
import time
import subprocess
import logging
import requests
import signal
import psutil
from datetime import datetime

# إعداد التسجيل
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
                    level=logging.INFO)
logger = logging.getLogger(__name__)

# تكوين الألوان لتنسيق المخرجات
GREEN = "\033[92m"
YELLOW = "\033[93m"
RED = "\033[91m"
BLUE = "\033[94m"
RESET = "\033[0m"

def get_input():
    """الحصول على التوكن الجديد من المستخدم والتأكد من صحته."""
    print(f"\n{BLUE}=== 1. التحقق من التوكن الجديد ==={RESET}")
    token = input(f"\n{BLUE}أدخل توكن التلغرام الجديد:{RESET} ").strip()
    
    if not token:
        logger.error("لم يتم إدخال توكن")
        sys.exit(1)
    
    # التحقق من صحة التوكن
    try:
        response = requests.get(f"https://api.telegram.org/bot{token}/getMe")
        data = response.json()
        
        if data.get("ok"):
            bot_info = data.get("result", {})
            bot_name = bot_info.get("username", "غير معروف")
            print(f"{GREEN}✅ تم التحقق من صحة التوكن! اسم البوت: @{bot_name}{RESET}")
            return token
        else:
            print(f"{RED}❌ التوكن غير صالح: {data.get('description', 'خطأ غير معروف')}{RESET}")
            sys.exit(1)
    except Exception as e:
        print(f"{RED}❌ خطأ في التحقق من التوكن: {e}{RESET}")
        sys.exit(1)

def update_environment_variable(token):
    """تحديث متغير البيئة TELEGRAM_BOT_TOKEN."""
    print(f"\n{BLUE}=== 2. تحديث متغير البيئة ==={RESET}")
    
    # الحصول على التوكن القديم
    old_token = os.environ.get("TELEGRAM_BOT_TOKEN", "غير محدد")
    print(f"{YELLOW}التوكن القديم: {old_token}{RESET}")
    
    # تحديث متغير البيئة
    os.environ["TELEGRAM_BOT_TOKEN"] = token
    print(f"{GREEN}✅ تم تعيين متغير البيئة TELEGRAM_BOT_TOKEN إلى: {token}{RESET}")
    
    return old_token

def update_config_file(token):
    """تحديث ملف التكوين config.py."""
    print(f"\n{BLUE}=== 3. تحديث ملف التكوين ==={RESET}")
    
    if not os.path.exists("config.py"):
        print(f"{RED}❌ ملف config.py غير موجود{RESET}")
        return
    
    try:
        with open("config.py", "r") as f:
            content = f.read()
        
        # التحقق من نوع التعريف المستخدم
        if 'TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN")' in content:
            print(f"{GREEN}✅ ملف config.py يستخدم بالفعل طريقة آمنة لقراءة التوكن. لا حاجة للتعديل.{RESET}")
        elif 'TOKEN = os.getenv("TELEGRAM_BOT_TOKEN",' in content:
            # إذا كان التوكن معرفاً بشكل ثابت، قم بتحديثه
            import re
            pattern = r'TOKEN\s*=\s*os\.getenv\("TELEGRAM_BOT_TOKEN",\s*"([^"]*)"\)'
            
            if re.search(pattern, content):
                updated_content = re.sub(
                    pattern,
                    'TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN")',
                    content
                )
                
                with open("config.py", "w") as f:
                    f.write(updated_content)
                
                print(f"{GREEN}✅ تم تحديث ملف config.py لاستخدام os.environ.get بدلاً من قيمة ثابتة{RESET}")
            else:
                print(f"{YELLOW}⚠️ لم يتم العثور على نمط مطابق في config.py{RESET}")
        else:
            print(f"{YELLOW}⚠️ تكوين غير متوقع في config.py، فحص يدوي مطلوب{RESET}")
    except Exception as e:
        print(f"{RED}❌ خطأ في تحديث ملف config.py: {e}{RESET}")

def update_env_file(token, old_token):
    """تحديث ملف .env إذا كان موجوداً."""
    print(f"\n{BLUE}=== 4. تحديث ملف .env ==={RESET}")
    
    if os.path.exists(".env"):
        try:
            with open(".env", "r") as f:
                content = f.read()
            
            if "TELEGRAM_BOT_TOKEN=" in content:
                content = content.replace(f"TELEGRAM_BOT_TOKEN={old_token}", f"TELEGRAM_BOT_TOKEN={token}")
            else:
                content += f"\nTELEGRAM_BOT_TOKEN={token}\n"
            
            with open(".env", "w") as f:
                f.write(content)
            
            print(f"{GREEN}✅ تم تحديث ملف .env{RESET}")
        except Exception as e:
            print(f"{RED}❌ خطأ في تحديث ملف .env: {e}{RESET}")
    else:
        print(f"{YELLOW}⚠️ ملف .env غير موجود{RESET}")

def update_replit_file(token):
    """تحديث ملف .replit إذا كان موجوداً."""
    print(f"\n{BLUE}=== 5. تحديث ملف .replit ==={RESET}")
    
    if os.path.exists(".replit"):
        try:
            with open(".replit", "r") as f:
                content = f.read()
            
            if "[env]" in content:
                lines = content.splitlines()
                in_env_section = False
                updated = False
                new_lines = []
                
                for line in lines:
                    if line.strip() == "[env]":
                        in_env_section = True
                        new_lines.append(line)
                    elif line.startswith("[") and line.endswith("]"):
                        in_env_section = False
                        new_lines.append(line)
                    elif in_env_section and line.strip().startswith("TELEGRAM_BOT_TOKEN"):
                        new_lines.append(f'TELEGRAM_BOT_TOKEN = "{token}"')
                        updated = True
                    else:
                        new_lines.append(line)
                
                if in_env_section and not updated:
                    env_index = lines.index("[env]")
                    new_lines.insert(env_index + 1, f'TELEGRAM_BOT_TOKEN = "{token}"')
                
                with open(".replit", "w") as f:
                    f.write("\n".join(new_lines))
                
                print(f"{GREEN}✅ تم تحديث ملف .replit{RESET}")
            else:
                with open(".replit", "a") as f:
                    f.write(f"\n\n[env]\nTELEGRAM_BOT_TOKEN = \"{token}\"\n")
                
                print(f"{GREEN}✅ تم إضافة قسم [env] إلى ملف .replit{RESET}")
        except Exception as e:
            print(f"{RED}❌ خطأ في تحديث ملف .replit: {e}{RESET}")
    else:
        print(f"{YELLOW}⚠️ ملف .replit غير موجود{RESET}")

def stop_bot_processes():
    """إيقاف جميع عمليات البوت الحالية."""
    print(f"\n{BLUE}=== 6. إيقاف عمليات البوت الحالية ==={RESET}")
    
    count = 0
    for process in psutil.process_iter(["pid", "name", "cmdline"]):
        try:
            cmdline = process.info.get("cmdline", [])
            if cmdline and "python" in cmdline[0] and any("bot.py" in cmd for cmd in cmdline):
                print(f"{YELLOW}إيقاف عملية البوت {process.info['pid']}{RESET}")
                try:
                    # إرسال إشارة SIGTERM للعملية
                    os.kill(process.info["pid"], signal.SIGTERM)
                    count += 1
                except Exception as e:
                    print(f"{RED}❌ خطأ في إيقاف العملية {process.info['pid']}: {e}{RESET}")
        except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
            continue
    
    if count > 0:
        print(f"{GREEN}✅ تم إيقاف {count} عملية للبوت{RESET}")
        time.sleep(2)  # انتظار لضمان إغلاق العمليات
    else:
        print(f"{YELLOW}⚠️ لم يتم العثور على عمليات للبوت قيد التشغيل{RESET}")

def fix_webhook():
    """إصلاح webhook والتأكد من تعطيله."""
    print(f"\n{BLUE}=== 7. إصلاح إعدادات Webhook ==={RESET}")
    
    token = os.environ.get("TELEGRAM_BOT_TOKEN")
    if not token:
        print(f"{RED}❌ لم يتم تعيين TELEGRAM_BOT_TOKEN{RESET}")
        return
    
    try:
        # الحصول على معلومات webhook الحالية
        response = requests.get(f"https://api.telegram.org/bot{token}/getWebhookInfo")
        data = response.json()
        
        if data.get("ok"):
            webhook_info = data.get("result", {})
            webhook_url = webhook_info.get("url", "")
            
            if webhook_url:
                print(f"{YELLOW}Webhook مُعد على: {webhook_url}{RESET}")
                
                # تعطيل webhook
                delete_response = requests.get(f"https://api.telegram.org/bot{token}/deleteWebhook")
                if delete_response.json().get("ok"):
                    print(f"{GREEN}✅ تم حذف Webhook بنجاح{RESET}")
                else:
                    print(f"{RED}❌ فشل في حذف Webhook: {delete_response.json().get('description', 'خطأ غير معروف')}{RESET}")
            else:
                print(f"{GREEN}✅ لا يوجد Webhook مُعد. جاهز لوضع polling.{RESET}")
        else:
            print(f"{RED}❌ خطأ في الحصول على معلومات Webhook: {data.get('description', 'خطأ غير معروف')}{RESET}")
    except Exception as e:
        print(f"{RED}❌ خطأ في إصلاح Webhook: {e}{RESET}")

def restart_workflows():
    """إعادة تشغيل مسارات العمل."""
    print(f"\n{BLUE}=== 8. إعادة تشغيل مسارات العمل ==={RESET}")
    
    print(f"{YELLOW}يرجى استخدام أداة Replit لإعادة تشغيل مسارات العمل يدوياً:{RESET}")
    print(f"  {GREEN}1. انقر على علامة التبويب Shell{RESET}")
    print(f"  {GREEN}2. ثم انقر على مسار العمل 'telegram_bot'{RESET}")
    print(f"  {GREEN}3. انقر على زر إعادة التشغيل ⟳{RESET}")
    print(f"  {GREEN}4. كرر العملية لمسار العمل 'Start application'{RESET}")

def create_confirmation_file(token, old_token):
    """إنشاء ملف تأكيد التحديث."""
    print(f"\n{BLUE}=== 9. إنشاء ملف تأكيد ==={RESET}")
    
    try:
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        with open("token_update_confirmation.txt", "w") as f:
            f.write(f"تم تحديث توكن التلغرام بنجاح في {timestamp}\n")
            f.write(f"من: {old_token}\n")
            f.write(f"إلى: {token}\n")
        
        print(f"{GREEN}✅ تم إنشاء ملف تأكيد التحديث{RESET}")
    except Exception as e:
        print(f"{RED}❌ خطأ في إنشاء ملف التأكيد: {e}{RESET}")

def main():
    """الوظيفة الرئيسية للسكريبت."""
    print(f"\n{BLUE}🔧 أداة إصلاح وتحديث توكن التلغرام 🔧{RESET}")
    print(f"{BLUE}======================================{RESET}")
    
    # 1. الحصول على التوكن الجديد والتحقق منه
    token = get_input()
    
    # 2. تحديث متغير البيئة
    old_token = update_environment_variable(token)
    
    # 3. تحديث ملف التكوين
    update_config_file(token)
    
    # 4. تحديث ملف .env
    update_env_file(token, old_token)
    
    # 5. تحديث ملف .replit
    update_replit_file(token)
    
    # 6. إيقاف عمليات البوت الحالية
    stop_bot_processes()
    
    # 7. إصلاح webhook
    fix_webhook()
    
    # 8. إعادة تشغيل مسارات العمل
    restart_workflows()
    
    # 9. إنشاء ملف تأكيد
    create_confirmation_file(token, old_token)
    
    print(f"\n{GREEN}✅ تم تنفيذ جميع خطوات التحديث!{RESET}")
    print(f"\n{YELLOW}هام: قم بإعادة تشغيل مسارات العمل يدوياً في Replit لتطبيق التغييرات بشكل كامل.{RESET}")

if __name__ == "__main__":
    main()