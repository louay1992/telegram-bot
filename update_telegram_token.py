#!/usr/bin/env python3
"""
سكريبت لتحديث توكن التلغرام
"""
import os
import sys
import logging

# إعداد التسجيل
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
                    level=logging.INFO)
logger = logging.getLogger(__name__)

# الحصول على توكن التلغرام الحالي
current_token = os.environ.get("TELEGRAM_BOT_TOKEN")
if not current_token:
    logger.error("لا يوجد توكن للتلغرام في متغيرات البيئة")
    sys.exit(1)

logger.info(f"توكن التلغرام الحالي: {current_token}")

# طلب التوكن الجديد من المستخدم
print("\nأدخل توكن التلغرام الجديد:")
new_token = input().strip()

if not new_token:
    logger.error("لم يتم إدخال توكن جديد")
    sys.exit(1)

# التأكيد على التحديث
print(f"\nهل أنت متأكد من تحديث توكن التلغرام؟")
print(f"من: {current_token}")
print(f"إلى: {new_token}")
print("\nاكتب 'نعم' للتأكيد:")
confirmation = input().strip()

if confirmation.lower() not in ["نعم", "yes", "y"]:
    logger.error("تم إلغاء التحديث")
    sys.exit(1)

# تحديث متغير البيئة
os.environ["TELEGRAM_BOT_TOKEN"] = new_token
logger.info(f"تم تحديث متغير البيئة TELEGRAM_BOT_TOKEN")

# إذا كنت تستخدم replit.db لتخزين التوكن
try:
    from replit import db
    db["TELEGRAM_BOT_TOKEN"] = new_token
    logger.info("تم تحديث توكن التلغرام في replit.db")
except ImportError:
    logger.info("لا يمكن الوصول إلى replit.db")

# تحديث ملف .env إذا كان موجودًا
if os.path.exists(".env"):
    with open(".env", "r") as f:
        env_content = f.read()
    
    # تحديث أو إضافة التوكن
    if "TELEGRAM_BOT_TOKEN=" in env_content:
        env_content = env_content.replace(f"TELEGRAM_BOT_TOKEN={current_token}", f"TELEGRAM_BOT_TOKEN={new_token}")
    else:
        env_content += f"\nTELEGRAM_BOT_TOKEN={new_token}\n"
    
    with open(".env", "w") as f:
        f.write(env_content)
    
    logger.info("تم تحديث توكن التلغرام في ملف .env")

# تحديث ملف .replit إذا كان موجودًا
if os.path.exists(".replit"):
    with open(".replit", "r") as f:
        replit_content = f.read()
    
    # التحقق من وجود قسم [env]
    if '[env]' not in replit_content:
        # إضافة قسم [env]
        replit_content += "\n\n[env]\n"
        replit_content += f'TELEGRAM_BOT_TOKEN = "{new_token}"\n'
    else:
        # تحديث القسم الموجود
        lines = replit_content.splitlines()
        in_env_section = False
        updated = False
        new_lines = []
        
        for line in lines:
            if line.strip() == '[env]':
                in_env_section = True
                new_lines.append(line)
            elif line.startswith('[') and line.endswith(']'):
                in_env_section = False
                new_lines.append(line)
            elif in_env_section and line.strip().startswith('TELEGRAM_BOT_TOKEN'):
                new_lines.append(f'TELEGRAM_BOT_TOKEN = "{new_token}"')
                updated = True
            else:
                new_lines.append(line)
        
        # إذا لم يتم العثور على التوكن في قسم [env]، أضفه
        if in_env_section and not updated:
            # البحث عن موقع إدراج التوكن
            env_index = lines.index('[env]')
            new_lines.insert(env_index + 1, f'TELEGRAM_BOT_TOKEN = "{new_token}"')
        
        replit_content = '\n'.join(new_lines)
    
    with open(".replit", "w") as f:
        f.write(replit_content)
    
    logger.info("تم تحديث توكن التلغرام في ملف .replit")

# إنشاء ملف تأكيد التحديث
with open("token_updated.txt", "w") as f:
    f.write(f"تم تحديث توكن التلغرام من {current_token} إلى {new_token} في {__import__('datetime').datetime.now()}")

logger.info("تم تحديث توكن التلغرام بنجاح!")
print("\n✅ تم تحديث توكن التلغرام بنجاح!")
print("⚠️ يجب إعادة تشغيل مسارات العمل لتطبيق التغييرات")