#!/usr/bin/env python3
"""
سكريبت مخصص لتشغيل البوت مع التوكن الجديد وتجاوز النظام الحالي
"""
import subprocess
import os
import sys
import time
import logging
import signal
import psutil

# إعداد التسجيل
logging.basicConfig(level=logging.INFO, 
                    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# التوكن القديم والجديد
OLD_TOKEN = "7406580104:AAGG2JQeeNfsmcGVMCm7hxitIK-qm2yekVg"
NEW_TOKEN = "7406580104:AAGG2JQeeNfsmcGVMCm7hxitIK-qm2yekVg"

def stop_existing_bot_processes():
    """إيقاف جميع عمليات البوت الحالية."""
    print("🔍 البحث عن عمليات البوت الحالية وإيقافها...")
    count = 0
    for proc in psutil.process_iter(['pid', 'name', 'cmdline']):
        try:
            # التحقق من العمليات التي تشغل bot.py
            cmdline = proc.info.get('cmdline', [])
            if cmdline and len(cmdline) > 1 and 'python' in cmdline[0] and any('bot.py' in cmd for cmd in cmdline):
                pid = proc.info['pid']
                if pid != os.getpid():  # تجنب إيقاف العملية الحالية
                    print(f"⚠️ إيقاف عملية البوت بـ PID: {pid}")
                    try:
                        os.kill(pid, signal.SIGTERM)
                        count += 1
                    except Exception as e:
                        print(f"❌ خطأ في إيقاف العملية {pid}: {e}")
        except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
            pass
    
    if count > 0:
        print(f"✅ تم إيقاف {count} عملية للبوت.")
        time.sleep(2)  # إعطاء وقت للعمليات لإنهاء عملها
    else:
        print("ℹ️ لم يتم العثور على أي عملية للبوت.")

def inject_token_into_bot():
    """إنشاء نسخة معدلة من bot.py مع التوكن الجديد مدمج فيها."""
    print("🔧 إنشاء نسخة معدلة من Bot.py...")

    # التحقق من وجود bot.py الأصلي
    if not os.path.exists("bot.py"):
        print("❌ خطأ: ملف bot.py غير موجود!")
        return False

    # إنشاء نسخة من bot.py باسم custom_bot.py
    try:
        with open("bot.py", "r", encoding="utf-8") as src_file:
            bot_content = src_file.read()
        
        # استبدال السطر الذي يستخدم التوكن من ملف التكوين
        # بحث عن السطر: application = Application.builder().token(config.TOKEN).build()
        if "application = Application.builder().token(config.TOKEN).build()" in bot_content:
            modified_content = bot_content.replace(
                "application = Application.builder().token(config.TOKEN).build()",
                f'# استخدام التوكن الجديد مباشرةً\n    NEW_TOKEN = "{NEW_TOKEN}"\n    application = Application.builder().token(NEW_TOKEN).build()'
            )
            
            # كتابة المحتوى المعدل إلى custom_bot.py
            with open("custom_bot.py", "w", encoding="utf-8") as dst_file:
                dst_file.write(modified_content)
            
            print("✅ تم إنشاء نسخة معدلة من bot.py باسم custom_bot.py بنجاح!")
            return True
        else:
            print("❌ لم يتم العثور على السطر المطلوب في bot.py!")
            return False
    except Exception as e:
        print(f"❌ خطأ أثناء تعديل bot.py: {e}")
        return False

def run_modified_bot():
    """تشغيل النسخة المعدلة من البوت."""
    print("🚀 جاري تشغيل النسخة المعدلة من البوت...")
    
    try:
        # تشغيل custom_bot.py
        process = subprocess.Popen(["python", "custom_bot.py"])
        
        # انتظار قليلاً للتحقق من بدء التشغيل
        time.sleep(5)
        
        # التحقق من حالة العملية
        if process.poll() is None:
            print(f"✅ تم تشغيل البوت المعدل بنجاح! (PID: {process.pid})")
            print("ℹ️ البوت يعمل الآن مع التوكن الجديد.")
            return True
        else:
            print(f"❌ فشل في بدء تشغيل البوت المعدل. رمز الخروج: {process.returncode}")
            return False
    except Exception as e:
        print(f"❌ خطأ أثناء تشغيل البوت المعدل: {e}")
        return False

def main():
    """الوظيفة الرئيسية للسكريبت."""
    print("🤖 أداة تشغيل البوت مع التوكن الجديد 🤖")
    print("=========================================")
    print(f"التوكن القديم: {OLD_TOKEN}")
    print(f"التوكن الجديد: {NEW_TOKEN}")
    print()
    
    # 1. إيقاف عمليات البوت الحالية
    stop_existing_bot_processes()
    
    # 2. إنشاء نسخة معدلة من bot.py
    if not inject_token_into_bot():
        print("❌ فشل في إنشاء نسخة معدلة من bot.py.")
        return
    
    # 3. تشغيل النسخة المعدلة
    if run_modified_bot():
        print("\n✅ تم تشغيل البوت بنجاح مع التوكن الجديد!")
        print("\nملاحظات هامة:")
        print("1. هذا حل مؤقت. يجب تحديث التوكن في Replit Secrets.")
        print("2. يعمل البوت الآن من خلال custom_bot.py بدلاً من bot.py.")
        print("3. لإيقاف البوت، استخدم: pkill -f 'python custom_bot.py'")
    else:
        print("\n❌ فشل تشغيل البوت المعدل.")

if __name__ == "__main__":
    main()