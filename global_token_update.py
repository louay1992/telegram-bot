#!/usr/bin/env python3
"""
سكريبت لتحديث توكن التلغرام في جميع الملفات الممكنة
"""
import os
import sys
import subprocess
import logging

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

# التوكن القديم والجديد
OLD_TOKEN = "7406580104:AAGG2JQeeNfsmcGVMCm7hxitIK-qm2yekVg"
NEW_TOKEN = "7406580104:AAGG2JQeeNfsmcGVMCm7hxitIK-qm2yekVg"

def find_files_with_token(token, directory="."):
    """البحث عن الملفات التي تحتوي على التوكن."""
    print(f"{BLUE}البحث عن الملفات التي تحتوي على التوكن القديم...{RESET}")
    
    try:
        # استخدام grep للبحث عن الملفات التي تحتوي على التوكن
        cmd = f'grep -r "{token}" {directory} --include="*.py" --include="*.md" --include="*.txt" --include="*.json" --include="*.yml" --include="*.yaml" --include="*.toml" --include="*.ini" --include="*.env" --include="*.sh" --include="*.bat" 2>/dev/null'
        output = subprocess.check_output(cmd, shell=True).decode()
        
        # تحليل النتائج
        files_found = {}
        for line in output.strip().split('\n'):
            if not line:
                continue
            
            parts = line.split(':', 1)
            if len(parts) < 2:
                continue
            
            filename = parts[0]
            
            if filename not in files_found:
                files_found[filename] = []
            
            files_found[filename].append(line)
        
        return files_found
    except subprocess.CalledProcessError:
        print(f"{YELLOW}لم يتم العثور على أي ملفات تحتوي على التوكن.{RESET}")
        return {}
    except Exception as e:
        print(f"{RED}خطأ أثناء البحث عن الملفات: {e}{RESET}")
        return {}

def update_files(files_dict, old_token, new_token):
    """تحديث الملفات لاستبدال التوكن القديم بالجديد."""
    print(f"\n{BLUE}تحديث الملفات...{RESET}")
    updated_files = []
    
    for filename, _ in files_dict.items():
        try:
            # التحقق من وجود الملف
            if not os.path.exists(filename) or not os.path.isfile(filename):
                print(f"{YELLOW}تخطي {filename}: الملف غير موجود.{RESET}")
                continue
            
            # قراءة محتوى الملف
            with open(filename, 'r', errors='ignore') as f:
                content = f.read()
            
            # التحقق من وجود التوكن القديم
            if old_token in content:
                # استبدال التوكن
                updated_content = content.replace(old_token, new_token)
                
                # كتابة المحتوى المحدث
                with open(filename, 'w') as f:
                    f.write(updated_content)
                
                updated_files.append(filename)
                print(f"{GREEN}✅ تم تحديث {filename}{RESET}")
            else:
                print(f"{YELLOW}لم يتم العثور على التوكن في {filename} رغم وجوده في نتائج البحث.{RESET}")
        except Exception as e:
            print(f"{RED}خطأ أثناء تحديث {filename}: {e}{RESET}")
    
    return updated_files

def update_env_variables(old_token, new_token):
    """تحديث متغيرات البيئة."""
    print(f"\n{BLUE}تحديث متغيرات البيئة...{RESET}")
    
    try:
        current_token = os.environ.get("TELEGRAM_BOT_TOKEN", "")
        if current_token == old_token:
            os.environ["TELEGRAM_BOT_TOKEN"] = new_token
            print(f"{GREEN}✅ تم تحديث متغير البيئة TELEGRAM_BOT_TOKEN{RESET}")
            return True
        else:
            print(f"{YELLOW}متغير البيئة TELEGRAM_BOT_TOKEN ليس مساوياً للتوكن القديم. القيمة الحالية: {current_token}{RESET}")
            return False
    except Exception as e:
        print(f"{RED}خطأ أثناء تحديث متغير البيئة: {e}{RESET}")
        return False

def fix_replit_secrets():
    """محاولة تحديث Replit Secrets عبر Replit API (إذا كان مسموحاً)."""
    print(f"\n{BLUE}محاولة تحديث Replit Secrets...{RESET}")
    print(f"{YELLOW}⚠️ يجب تحديث Replit Secrets يدوياً من واجهة Replit.{RESET}")
    print(f"{YELLOW}⚠️ انتقل إلى Secrets في لوحة التحكم وقم بتحديث TELEGRAM_BOT_TOKEN.{RESET}")

def create_helper_script():
    """إنشاء سكريبت مساعد لضبط التوكن في بداية تشغيل البوت."""
    print(f"\n{BLUE}إنشاء سكريبت مساعد لضبط التوكن...{RESET}")
    
    script_content = """#!/usr/bin/env python3
# سكريبت مساعد لضبط توكن التلغرام الصحيح في بداية التشغيل
import os
import sys

# التوكن الجديد
NEW_TOKEN = "7406580104:AAGG2JQeeNfsmcGVMCm7hxitIK-qm2yekVg"

def main():
    # تعيين متغير البيئة
    os.environ["TELEGRAM_BOT_TOKEN"] = NEW_TOKEN
    print(f"✅ تم تعيين TELEGRAM_BOT_TOKEN إلى التوكن الجديد")
    
    # تشغيل bot.py
    if len(sys.argv) > 1:
        args = sys.argv[1:]
        os.execvp("python", ["python"] + args)
    else:
        os.execvp("python", ["python", "bot.py"])

if __name__ == "__main__":
    main()
"""
    
    try:
        with open("start_bot_with_token.py", "w") as f:
            f.write(script_content)
        
        # جعل الملف قابل للتنفيذ
        os.chmod("start_bot_with_token.py", 0o755)
        
        print(f"{GREEN}✅ تم إنشاء سكريبت start_bot_with_token.py{RESET}")
        print(f"{YELLOW}يمكنك الآن تشغيل البوت باستخدام: python start_bot_with_token.py bot.py{RESET}")
    except Exception as e:
        print(f"{RED}خطأ أثناء إنشاء السكريبت المساعد: {e}{RESET}")

def main():
    """الوظيفة الرئيسية للسكريبت."""
    print(f"{BLUE}🔄 أداة تحديث توكن التلغرام العامة 🔄{RESET}")
    print(f"{BLUE}=========================================={RESET}")
    print(f"التوكن القديم: {YELLOW}{OLD_TOKEN}{RESET}")
    print(f"التوكن الجديد: {GREEN}{NEW_TOKEN}{RESET}")
    print()
    
    # 1. البحث عن الملفات التي تحتوي على التوكن القديم
    files_with_token = find_files_with_token(OLD_TOKEN)
    
    if not files_with_token:
        print(f"{YELLOW}لم يتم العثور على أي ملفات تحتوي على التوكن القديم.{RESET}")
    else:
        print(f"\n{GREEN}تم العثور على {len(files_with_token)} ملف يحتوي على التوكن القديم:{RESET}")
        for filename in files_with_token:
            print(f"  {YELLOW}• {filename}{RESET}")
        
        # 2. تحديث الملفات
        updated_files = update_files(files_with_token, OLD_TOKEN, NEW_TOKEN)
        
        print(f"\n{GREEN}تم تحديث {len(updated_files)} ملف:{RESET}")
        for filename in updated_files:
            print(f"  {GREEN}✓ {filename}{RESET}")
    
    # 3. تحديث متغيرات البيئة
    update_env_variables(OLD_TOKEN, NEW_TOKEN)
    
    # 4. إرشادات لتحديث Replit Secrets
    fix_replit_secrets()
    
    # 5. إنشاء سكريبت مساعد
    create_helper_script()
    
    print(f"\n{GREEN}✅ اكتملت عملية تحديث التوكن!{RESET}")
    print(f"\n{YELLOW}ملاحظات هامة:{RESET}")
    print(f"1. يجب تحديث Replit Secrets يدوياً من واجهة Replit.")
    print(f"2. استخدم سكريبت start_bot_with_token.py لتشغيل البوت بالتوكن الجديد.")
    print(f"3. قم بإعادة تشغيل مسارات العمل بعد تحديث Replit Secrets.")

if __name__ == "__main__":
    main()