#!/usr/bin/env python3
"""
أداة شاملة لحل مشاكل التعارض المختلفة في النظام
"""
import os
import sys
import json
import time
import logging
import argparse
import requests
import socket
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

def get_telegram_token():
    """الحصول على رمز البوت من المتغيرات البيئية."""
    token = os.environ.get("TELEGRAM_BOT_TOKEN")
    if not token:
        logger.error("لم يتم العثور على TELEGRAM_BOT_TOKEN في متغيرات البيئة")
        return None
    return token

def check_ports():
    """التحقق من المنافذ المستخدمة."""
    used_ports = {}
    
    # المنافذ التي نهتم بها
    ports_to_check = [5000, 8080]
    
    for port in ports_to_check:
        try:
            # محاولة إنشاء سوكيت على المنفذ
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            result = sock.connect_ex(('localhost', port))
            sock.close()
            
            if result == 0:
                # المنفذ مفتوح (مستخدم)
                used_ports[port] = True
                logger.info(f"المنفذ {port} مستخدم")
            else:
                # المنفذ مغلق (غير مستخدم)
                used_ports[port] = False
                logger.info(f"المنفذ {port} غير مستخدم")
        except Exception as e:
            logger.error(f"خطأ أثناء فحص المنفذ {port}: {e}")
            used_ports[port] = None
    
    return used_ports

def find_telegram_processes():
    """البحث عن العمليات المتعلقة بالبوت."""
    telegram_processes = []
    
    for proc in psutil.process_iter(['pid', 'name', 'cmdline']):
        try:
            # البحث في سطر الأوامر عن كلمات مفتاحية تشير إلى البوت
            cmdline = ' '.join(proc.info['cmdline']) if proc.info['cmdline'] else ''
            if ('telegram' in cmdline.lower() or 'bot.py' in cmdline.lower()) and 'python' in cmdline.lower():
                telegram_processes.append({
                    'pid': proc.info['pid'],
                    'cmdline': cmdline
                })
        except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
            pass
    
    return telegram_processes

def fix_webhook_conflict(token, force_polling=False):
    """إصلاح تعارض webhook للبوت."""
    logger.info("جاري التحقق من إعدادات webhook...")
    
    try:
        # الحصول على معلومات webhook الحالية
        url = f"https://api.telegram.org/bot{token}/getWebhookInfo"
        response = requests.get(url)
        response.raise_for_status()
        webhook_info = response.json()
        
        has_webhook = bool(webhook_info.get('result', {}).get('url', ''))
        logger.info(f"Webhook مضبوط: {has_webhook}")
        
        if has_webhook or force_polling:
            # إلغاء webhook
            logger.info("جاري إلغاء webhook...")
            url = f"https://api.telegram.org/bot{token}/deleteWebhook"
            response = requests.post(url)
            response.raise_for_status()
            
            if response.json().get('ok'):
                logger.info(f"{GREEN}✅ تم إلغاء webhook بنجاح{RESET}")
            else:
                logger.error(f"{RED}❌ فشل إلغاء webhook: {response.json()}{RESET}")
        
        # اختبار getUpdates للتأكد من عدم وجود تعارض
        logger.info("جاري اختبار getUpdates...")
        url = f"https://api.telegram.org/bot{token}/getUpdates"
        response = requests.post(url)
        
        if response.json().get('ok'):
            logger.info(f"{GREEN}✅ نجح اختبار getUpdates{RESET}")
            return True
        else:
            logger.error(f"{RED}❌ فشل اختبار getUpdates: {response.json()}{RESET}")
            return False
    
    except Exception as e:
        logger.error(f"خطأ أثناء إصلاح تعارض webhook: {e}")
        return False

def update_replit_config(set_run_bot=False):
    """تحديث ملف .replit مع الإعدادات الصحيحة."""
    logger.info("جاري تحديث إعدادات .replit...")
    
    try:
        replit_file = ".replit"
        
        if not os.path.exists(replit_file):
            logger.error(f"ملف {replit_file} غير موجود")
            return False
        
        with open(replit_file, "r") as f:
            content = f.read()
        
        # التحقق من وجود قسم [env]
        if '[env]' not in content:
            # إضافة قسم [env]
            with open(replit_file, "a") as f:
                f.write("\n\n[env]\n")
                f.write(f'RUN_BOT_FROM_SERVER = "{str(set_run_bot).lower()}"\n')
            logger.info(f"{GREEN}✅ تم إضافة إعدادات البيئة إلى {replit_file}{RESET}")
        else:
            # تحديث القسم الموجود
            lines = content.splitlines()
            in_env_section = False
            found_run_bot = False
            new_lines = []
            
            for line in lines:
                if line.strip() == '[env]':
                    in_env_section = True
                    new_lines.append(line)
                elif line.startswith('[') and line.endswith(']'):
                    in_env_section = False
                    new_lines.append(line)
                elif in_env_section and line.startswith('RUN_BOT_FROM_SERVER'):
                    new_lines.append(f'RUN_BOT_FROM_SERVER = "{str(set_run_bot).lower()}"')
                    found_run_bot = True
                else:
                    new_lines.append(line)
            
            # إذا لم يتم العثور على المتغير، أضفه
            if in_env_section and not found_run_bot:
                # البحث عن موقع إدراج المتغير
                env_index = new_lines.index('[env]')
                new_lines.insert(env_index + 1, f'RUN_BOT_FROM_SERVER = "{str(set_run_bot).lower()}"')
            
            # كتابة المحتوى المحدث
            with open(replit_file, "w") as f:
                f.write('\n'.join(new_lines))
            
            logger.info(f"{GREEN}✅ تم تحديث إعدادات البيئة في {replit_file}{RESET}")
        
        # تعيين متغير البيئة للجلسة الحالية
        os.environ["RUN_BOT_FROM_SERVER"] = str(set_run_bot).lower()
        logger.info(f"{GREEN}✅ تم تعيين متغير البيئة RUN_BOT_FROM_SERVER={str(set_run_bot).lower()}{RESET}")
        
        return True
    
    except Exception as e:
        logger.error(f"خطأ أثناء تحديث إعدادات .replit: {e}")
        return False

def restart_workflow(workflow_name):
    """إعادة تشغيل مسار عمل معين."""
    logger.info(f"جاري محاولة إعادة تشغيل مسار العمل '{workflow_name}'...")
    
    try:
        # هذه وظيفة بسيطة تقوم بإنشاء علامة لإعادة تشغيل مسار العمل
        # في بيئة Replit، يجب استخدام واجهة Replit API إذا كانت متاحة
        marker_dir = ".workflow_restart_markers"
        os.makedirs(marker_dir, exist_ok=True)
        
        marker_file = os.path.join(marker_dir, f"{workflow_name.replace(' ', '_')}.restart")
        with open(marker_file, "w") as f:
            f.write(str(datetime.now().timestamp()))
        
        logger.info(f"{GREEN}✅ تم إنشاء علامة إعادة تشغيل لمسار العمل '{workflow_name}'{RESET}")
        logger.info(f"{YELLOW}ملاحظة: قد تحتاج إلى إعادة تشغيل مسار العمل يدويًا من واجهة Replit{RESET}")
        return True
    
    except Exception as e:
        logger.error(f"خطأ أثناء محاولة إعادة تشغيل مسار العمل: {e}")
        return False

def main():
    """الوظيفة الرئيسية."""
    parser = argparse.ArgumentParser(description="أداة شاملة لحل مشاكل التعارض")
    parser.add_argument("--fix-all", action="store_true", help="إصلاح جميع أنواع التعارض")
    parser.add_argument("--fix-bot", action="store_true", help="إصلاح تعارض البوت")
    parser.add_argument("--fix-ports", action="store_true", help="إصلاح تعارض المنافذ")
    parser.add_argument("--fix-replit-config", action="store_true", help="تحديث إعدادات .replit")
    parser.add_argument("--check-only", action="store_true", help="فحص المشاكل دون إصلاحها")
    args = parser.parse_args()
    
    # استخدام --fix-all إذا لم يتم تحديد أي خيار آخر
    if not (args.fix_all or args.fix_bot or args.fix_ports or args.fix_replit_config or args.check_only):
        args.fix_all = True
    
    print(f"\n{BLUE}⭐️ أداة شاملة لحل مشاكل التعارض ⭐️{RESET}")
    print(f"{BLUE}{'=' * 50}{RESET}\n")
    
    # فحص المنافذ المستخدمة
    print(f"{BLUE}جاري فحص المنافذ المستخدمة...{RESET}")
    used_ports = check_ports()
    
    # البحث عن عمليات البوت
    print(f"\n{BLUE}جاري البحث عن عمليات البوت...{RESET}")
    telegram_processes = find_telegram_processes()
    if telegram_processes:
        print(f"تم العثور على {len(telegram_processes)} عملية متعلقة بالبوت:")
        for proc in telegram_processes:
            print(f"  PID: {proc['pid']}")
            print(f"  CMD: {proc['cmdline']}")
            print()
    else:
        print(f"{YELLOW}لم يتم العثور على أي عملية متعلقة بالبوت{RESET}")
    
    # فحص تعارض webhook
    token = get_telegram_token()
    if token:
        print(f"\n{BLUE}جاري التحقق من تعارض webhook...{RESET}")
        try:
            url = f"https://api.telegram.org/bot{token}/getWebhookInfo"
            response = requests.get(url)
            response.raise_for_status()
            webhook_info = response.json().get('result', {})
            
            if webhook_info.get('url'):
                print(f"{YELLOW}تم العثور على webhook مضبوط: {webhook_info.get('url')}{RESET}")
            else:
                print(f"{GREEN}لا يوجد webhook مضبوط{RESET}")
        except Exception as e:
            print(f"{RED}خطأ أثناء التحقق من webhook: {e}{RESET}")
    else:
        print(f"{RED}لم يتم العثور على رمز البوت{RESET}")
    
    # إصلاح المشاكل
    if not args.check_only:
        if args.fix_all or args.fix_bot:
            print(f"\n{BLUE}جاري إصلاح تعارض البوت...{RESET}")
            if token:
                fix_webhook_conflict(token, force_polling=True)
            else:
                print(f"{RED}لا يمكن إصلاح تعارض البوت بدون رمز البوت{RESET}")
        
        if args.fix_all or args.fix_replit_config:
            print(f"\n{BLUE}جاري تحديث إعدادات .replit...{RESET}")
            update_replit_config(set_run_bot=False)
        
        if args.fix_all and used_ports.get(8080, False):
            print(f"\n{BLUE}جاري محاولة إعادة تشغيل مسارات العمل...{RESET}")
            for workflow in ["Start application", "telegram_bot"]:
                restart_workflow(workflow)
    
    print(f"\n{BLUE}{'=' * 50}{RESET}")
    print(f"{GREEN}اكتمل الفحص والإصلاح!{RESET}")
    print(f"\n{YELLOW}ما الذي يجب عليك فعله الآن:{RESET}")
    print(f"{YELLOW}1. تأكد من تشغيل مسار العمل 'telegram_bot' فقط{RESET}")
    print(f"{YELLOW}2. تأكد من إيقاف أي نسخة أخرى من البوت{RESET}")
    print(f"{YELLOW}3. تحقق من سجلات مسار العمل للتأكد من عدم وجود تعارض{RESET}")
    print(f"{BLUE}{'=' * 50}{RESET}\n")

if __name__ == "__main__":
    main()