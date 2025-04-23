#!/usr/bin/env python3
"""سكريبت للمساعدة في حل تعارض بوت تيليجرام - قم بإيقاف نسخة البوت من main.py بشكل دائم"""

import os
import sys

# طباعة العنوان
print("\033[94m" + "=" * 50 + "\033[0m")
print("\033[94m    مساعد حل تعارض البوت    \033[0m")
print("\033[94m" + "=" * 50 + "\033[0m")

# تمكين أو تعطيل البوت في الخادم
try:
    # تعيين متغير بيئي دائم (سيبقى بعد إعادة تشغيل Replit)
    with open(".replit", "r") as f:
        replit_content = f.read()
    
    if '[env]' not in replit_content:
        # إضافة قسم env جديد
        with open(".replit", "a") as f:
            f.write("\n\n[env]\n")
            f.write('RUN_BOT_FROM_SERVER = "False"\n')
        print("\033[92m✅ تم إضافة متغير RUN_BOT_FROM_SERVER=False إلى ملف .replit\033[0m")
    else:
        # تحديث القسم الموجود
        env_lines = []
        other_lines = []
        in_env_section = False

        for line in replit_content.splitlines():
            if line.strip() == '[env]':
                in_env_section = True
                other_lines.append(line)
            elif line.startswith('[') and line.endswith(']'):
                in_env_section = False
                other_lines.append(line)
            elif in_env_section:
                if line.startswith('RUN_BOT_FROM_SERVER'):
                    env_lines.append('RUN_BOT_FROM_SERVER = "False"')
                else:
                    env_lines.append(line)
            else:
                other_lines.append(line)
        
        # إذا لم يتم العثور على المتغير، أضفه
        if not any(line.startswith('RUN_BOT_FROM_SERVER') for line in env_lines):
            env_lines.append('RUN_BOT_FROM_SERVER = "False"')
        
        # إعادة بناء المحتوى
        new_content = []
        env_added = False
        
        for line in other_lines:
            new_content.append(line)
            if line.strip() == '[env]':
                env_added = True
                new_content.extend(env_lines)
        
        if not env_added:
            new_content.append('[env]')
            new_content.extend(env_lines)
        
        with open(".replit", "w") as f:
            f.write('\n'.join(new_content))
        
        print("\033[92m✅ تم تحديث متغير RUN_BOT_FROM_SERVER=False في ملف .replit\033[0m")
    
    # تعيين متغير بيئي مؤقت للجلسة الحالية
    os.environ["RUN_BOT_FROM_SERVER"] = "False"
    print("\033[92m✅ تم تعيين متغير البيئة RUN_BOT_FROM_SERVER=False للجلسة الحالية\033[0m")
    
    # تسجيل التغييرات في السجل
    with open("bot_conflict_fix.log", "a") as log:
        log.write(f"تم تعطيل تشغيل البوت من الخادم: {os.environ.get('RUN_BOT_FROM_SERVER', 'False')}\n")
    
    print("\033[93m" + "-" * 50 + "\033[0m")
    print("\033[93mالخطوات التالية:\033[0m")
    print("1. \033[93mأعد تشغيل workflow 'Start application' إذا كان متوقفًا\033[0m")
    print("2. \033[93mتأكد أن workflow 'telegram_bot' يعمل\033[0m")
    print("3. \033[93mتحقق من عدم وجود تعارض في السجلات\033[0m")

except Exception as e:
    print(f"\033[91m❌ حدث خطأ: {e}\033[0m")
    sys.exit(1)

print("\033[94m" + "=" * 50 + "\033[0m")
print("\033[92m✓ اكتمل الإصلاح بنجاح!\033[0m")