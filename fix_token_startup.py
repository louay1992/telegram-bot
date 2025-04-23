#!/usr/bin/env python3
# تم إنشاء هذا الملف تلقائيًا بواسطة سكريبت تحديث التوكن في 2025-04-22 08:50:51

import os
import sys
import logging

# إعداد التسجيل
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    filename='token_fix.log'
)

# التوكن الصحيح
CORRECT_TOKEN = "7406580104:AAGG2JQeeNfsmcGVMCm7hxitIK-qm2yekVg"

# التحقق من متغير البيئة
env_token = os.environ.get('TELEGRAM_BOT_TOKEN')
if env_token != CORRECT_TOKEN:
    logging.warning(f"تم اكتشاف توكن غير صحيح في متغيرات البيئة: {env_token}")
    logging.info(f"تعيين التوكن الصحيح: {CORRECT_TOKEN}")
    os.environ['TELEGRAM_BOT_TOKEN'] = CORRECT_TOKEN
    logging.info("تم تحديث متغير البيئة TELEGRAM_BOT_TOKEN")

# طباعة معلومات التوكن
print(f"التوكن الحالي: {os.environ.get('TELEGRAM_BOT_TOKEN')}")

# تنفيذ السكريبت الأصلي
if len(sys.argv) > 1:
    script_path = sys.argv[1]
    logging.info(f"تنفيذ السكريبت: {script_path}")
    
    try:
        with open(script_path) as f:
            script_content = f.read()
        
        # تنفيذ السكريبت
        exec(script_content)
    except Exception as e:
        logging.error(f"خطأ في تنفيذ السكريبت {script_path}: {e}")
        sys.exit(1)
else:
    logging.error("لم يتم تحديد سكريبت للتنفيذ")
    print("الاستخدام: python fix_token_startup.py <script_path>")
    sys.exit(1)
