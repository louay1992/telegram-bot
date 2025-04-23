#!/usr/bin/env python3
"""
سكريبت لتحديث توكن التلغرام في جميع الملفات الممكنة
"""
import os
import re
import subprocess
import logging
from datetime import datetime

# إعداد التسجيل
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    filename='token_update.log'
)

# التوكن القديم والجديد
OLD_TOKEN = "7406580104:AAGG2JQeeNfsmcGVMCm7hxitIK-qm2yekVg"
NEW_TOKEN = "7406580104:AAGG2JQeeNfsmcGVMCm7hxitIK-qm2yekVg"

# قائمة الملفات التي يجب تجاهلها
IGNORE_DIRS = [
    ".git", "__pycache__", "venv", "data", "temp", "temp_media",
    "node_modules", "backup", "clienttrackerpro_render", "render_bot", "render_deployment"
]

IGNORE_FILES = [
    "token_update.log", ".env.example", ".replit", "*.log", "*.db",
    "*.pyc", "*.pyo", "*.pyd", "*.json", "*.csv", "*.sql", "*.sqlite",
    "*.gz", "*.zip", "*.tar", "*.png", "*.jpg", "*.jpeg", "*.gif", "*.bmp",
    "custom_bot.py"  # نتجاهل ملف البوت المخصص لأننا قمنا بتحديثه يدويًا
]

def is_ignored(path, ignored_dirs, ignored_files):
    """التحقق ما إذا كان المسار يجب تجاهله."""
    # التحقق من المجلدات المتجاهلة
    for ignored_dir in ignored_dirs:
        if f"/{ignored_dir}/" in f"/{path}/" or path.startswith(f"{ignored_dir}/"):
            return True
    
    # التحقق من أنماط الملفات المتجاهلة
    filename = os.path.basename(path)
    for pattern in ignored_files:
        if "*" in pattern:
            # تحويل نمط glob إلى تعبير منتظم
            regex_pattern = pattern.replace(".", "\\.").replace("*", ".*")
            if re.match(f"^{regex_pattern}$", filename):
                return True
        elif filename == pattern:
            return True
    
    return False

def find_token_in_file(file_path, token):
    """البحث عن التوكن في ملف معين."""
    try:
        with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
            content = f.read()
            return token in content
    except Exception as e:
        logging.error(f"خطأ في قراءة الملف {file_path}: {e}")
        return False

def find_files_with_token(token, directory="."):
    """البحث عن الملفات التي تحتوي على التوكن."""
    matched_files = {}
    
    for root, dirs, files in os.walk(directory):
        # تجاهل المجلدات المحددة
        dirs[:] = [d for d in dirs if d not in IGNORE_DIRS]
        
        for file in files:
            file_path = os.path.join(root, file)
            
            # تجاهل الملفات المحددة
            if is_ignored(file_path, IGNORE_DIRS, IGNORE_FILES):
                continue
            
            # تجاهل الملفات الثنائية والملفات الكبيرة
            try:
                size = os.path.getsize(file_path)
                if size > 1024 * 1024:  # تجاهل الملفات أكبر من 1 ميجابايت
                    logging.info(f"تجاهل الملف الكبير: {file_path} ({size/1024/1024:.2f} MB)")
                    continue
                
                # التحقق من محتوى الملف
                if find_token_in_file(file_path, token):
                    matched_files[file_path] = size
                    logging.info(f"تم العثور على التوكن في: {file_path}")
            except Exception as e:
                logging.error(f"خطأ أثناء معالجة الملف {file_path}: {e}")
    
    return matched_files

def update_file_content(file_path, old_token, new_token):
    """تحديث محتوى ملف لاستبدال التوكن القديم بالجديد."""
    try:
        with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
            content = f.read()
        
        # استبدال التوكن
        updated_content = content.replace(old_token, new_token)
        
        # كتابة المحتوى المحدث
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(updated_content)
        
        return True
    except Exception as e:
        logging.error(f"خطأ في تحديث الملف {file_path}: {e}")
        return False

def update_files(files_dict, old_token, new_token):
    """تحديث الملفات لاستبدال التوكن القديم بالجديد."""
    success_count = 0
    total_count = len(files_dict)
    
    logging.info(f"سيتم تحديث {total_count} ملف:")
    
    for file_path, size in files_dict.items():
        logging.info(f"تحديث الملف: {file_path} ({size/1024:.2f} KB)")
        print(f"تحديث الملف: {file_path}")
        
        if update_file_content(file_path, old_token, new_token):
            success_count += 1
    
    return success_count, total_count

def create_token_startup_script():
    """إنشاء سكريبت بدء التشغيل لضمان استخدام التوكن الصحيح."""
    script_content = f"""#!/usr/bin/env python3
# تم إنشاء هذا الملف تلقائيًا بواسطة سكريبت تحديث التوكن في {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

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
CORRECT_TOKEN = "{NEW_TOKEN}"

# التحقق من متغير البيئة
env_token = os.environ.get('TELEGRAM_BOT_TOKEN')
if env_token != CORRECT_TOKEN:
    logging.warning(f"تم اكتشاف توكن غير صحيح في متغيرات البيئة: {{env_token}}")
    logging.info(f"تعيين التوكن الصحيح: {{CORRECT_TOKEN}}")
    os.environ['TELEGRAM_BOT_TOKEN'] = CORRECT_TOKEN
    logging.info("تم تحديث متغير البيئة TELEGRAM_BOT_TOKEN")

# طباعة معلومات التوكن
print(f"التوكن الحالي: {{os.environ.get('TELEGRAM_BOT_TOKEN')}}")

# تنفيذ السكريبت الأصلي
if len(sys.argv) > 1:
    script_path = sys.argv[1]
    logging.info(f"تنفيذ السكريبت: {{script_path}}")
    
    try:
        with open(script_path) as f:
            script_content = f.read()
        
        # تنفيذ السكريبت
        exec(script_content)
    except Exception as e:
        logging.error(f"خطأ في تنفيذ السكريبت {{script_path}}: {{e}}")
        sys.exit(1)
else:
    logging.error("لم يتم تحديد سكريبت للتنفيذ")
    print("الاستخدام: python fix_token_startup.py <script_path>")
    sys.exit(1)
"""
    
    with open("fix_token_startup.py", 'w', encoding='utf-8') as f:
        f.write(script_content)
    
    os.chmod("fix_token_startup.py", 0o755)  # جعل الملف قابل للتنفيذ
    
    logging.info("تم إنشاء سكريبت بدء التشغيل fix_token_startup.py")
    print("تم إنشاء سكريبت بدء التشغيل fix_token_startup.py")

def update_workflow_file():
    """تحديث ملف مسار العمل لاستخدام البوت المعدل."""
    try:
        replit_content = ""
        replit_path = ".replit"
        
        if os.path.exists(replit_path):
            with open(replit_path, 'r', encoding='utf-8') as f:
                replit_content = f.read()
            
            # البحث عن تكوين مسار العمل telegram_bot
            if "name = \"telegram_bot\"" in replit_content and "command = \"python bot.py\"" in replit_content:
                updated_content = replit_content.replace(
                    "command = \"python bot.py\"",
                    "command = \"python custom_bot.py\""
                )
                
                with open(replit_path, 'w', encoding='utf-8') as f:
                    f.write(updated_content)
                
                logging.info("تم تحديث مسار العمل في ملف .replit")
                print("تم تحديث مسار العمل في ملف .replit")
            else:
                logging.info("لم يتم العثور على تكوين مسار العمل telegram_bot في ملف .replit")
        else:
            logging.warning("ملف .replit غير موجود")
    except Exception as e:
        logging.error(f"خطأ في تحديث ملف مسار العمل: {e}")

def main():
    """الوظيفة الرئيسية للسكريبت."""
    print("🔄 تحديث توكن التلغرام في جميع ملفات المشروع")
    print("============================================")
    print(f"التوكن القديم: {OLD_TOKEN}")
    print(f"التوكن الجديد: {NEW_TOKEN}")
    print()
    
    # 1. البحث عن الملفات التي تحتوي على التوكن القديم
    print("🔍 البحث عن الملفات التي تحتوي على التوكن القديم...")
    matched_files = find_files_with_token(OLD_TOKEN)
    
    if not matched_files:
        print("⚠️ لم يتم العثور على أي ملف يحتوي على التوكن القديم.")
        return
    
    # 2. تحديث الملفات
    print(f"🔄 تحديث {len(matched_files)} ملف...")
    success_count, total_count = update_files(matched_files, OLD_TOKEN, NEW_TOKEN)
    
    # 3. إنشاء سكريبت ضمان التوكن الصحيح
    print("📝 إنشاء سكريبت ضمان التوكن الصحيح...")
    create_token_startup_script()
    
    # 4. تحديث ملف مسار العمل
    print("⚙️ تحديث ملف مسار العمل...")
    update_workflow_file()
    
    # 5. عرض نتائج التحديث
    print()
    print("✅ اكتمل تحديث التوكن!")
    print(f"تم تحديث {success_count} من أصل {total_count} ملف.")
    print()
    print("الخطوات التالية:")
    print("1. تحديث التوكن في Replit Secrets:")
    print("   - انتقل إلى لوحة تحكم Replit")
    print("   - اختر علامة التبويب 'Secrets'")
    print("   - قم بتحديث قيمة TELEGRAM_BOT_TOKEN")
    print()
    print("2. إعادة تشغيل مسار العمل telegram_bot:")
    print("   - قم بإيقاف مسار العمل الحالي إذا كان قيد التشغيل")
    print("   - ابدأ تشغيل مسار العمل باستخدام custom_bot.py")
    print("   - أو استخدم '.replit' المحدث إذا تم تحديثه بنجاح")
    print()
    print("3. اختبار البوت:")
    print("   - تأكد من أن البوت يعمل بشكل صحيح مع التوكن الجديد")
    print()
    print("تم تسجيل جميع العمليات في ملف 'token_update.log'")

if __name__ == "__main__":
    main()