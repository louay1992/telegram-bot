#!/usr/bin/env python3
"""
سكريبت لتشغيل البوت مع التوكن الجديد مباشرة
"""
import os
import sys
import subprocess
import time
import signal
import psutil
import logging

# إعداد التسجيل
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
                    level=logging.INFO)
logger = logging.getLogger(__name__)

# التوكن الجديد 
NEW_TOKEN = "7406580104:AAGG2JQeeNfsmcGVMCm7hxitIK-qm2yekVg"

def kill_existing_bot_processes():
    """إيقاف أي عمليات للبوت قيد التشغيل."""
    print("🛑 إيقاف أي عمليات للبوت قيد التشغيل...")
    
    # البحث عن عمليات البوت
    count = 0
    for process in psutil.process_iter(["pid", "name", "cmdline"]):
        try:
            cmdline = process.info.get("cmdline", [])
            if cmdline and "python" in cmdline[0] and any(cmd == "bot.py" for cmd in cmdline):
                # استثناء العملية الحالية
                if process.pid != os.getpid():
                    print(f"  ❌ إيقاف عملية البوت بـ PID: {process.pid}")
                    try:
                        os.kill(process.pid, signal.SIGTERM)
                        count += 1
                    except Exception as e:
                        print(f"  ⚠️ خطأ في إيقاف العملية {process.pid}: {e}")
        except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
            continue
    
    if count > 0:
        print(f"✅ تم إيقاف {count} عملية للبوت بنجاح.")
        time.sleep(2)  # انتظار قليلاً للتأكد من إغلاق العمليات
    else:
        print("ℹ️ لم يتم العثور على عمليات للبوت قيد التشغيل.")

def run_bot():
    """تشغيل البوت مع التوكن الجديد."""
    print(f"🔄 تشغيل البوت مع التوكن الجديد: {NEW_TOKEN}")
    
    # تعيين التوكن الجديد في متغيرات البيئة
    os.environ["TELEGRAM_BOT_TOKEN"] = NEW_TOKEN
    
    # التحقق من وجود bot.py
    if not os.path.exists("bot.py"):
        print("❌ خطأ: ملف bot.py غير موجود!")
        return False
    
    try:
        # تشغيل البوت
        print("🚀 بدء تشغيل البوت...")
        process = subprocess.Popen(["python", "bot.py"])
        
        # الانتظار قليلاً للتأكد من بدء التشغيل
        time.sleep(5)
        
        # التحقق من حالة العملية
        if process.poll() is None:
            print(f"✅ تم تشغيل البوت بنجاح (PID: {process.pid}).")
            return True
        else:
            print(f"❌ فشل تشغيل البوت. رمز الخروج: {process.returncode}")
            return False
    except Exception as e:
        print(f"❌ خطأ أثناء تشغيل البوت: {e}")
        return False

def main():
    """الوظيفة الرئيسية للسكريبت."""
    print("🤖 أداة تشغيل البوت مع التوكن الجديد 🤖")
    print("=========================================")
    
    # إيقاف أي عمليات للبوت قيد التشغيل
    kill_existing_bot_processes()
    
    # تشغيل البوت مع التوكن الجديد
    if run_bot():
        print("\n✅ تم تشغيل البوت بنجاح مع التوكن الجديد!")
        print("ℹ️ يمكنك الآن استخدام البوت.")
        print("⚠️ ملاحظة: هذا حل مؤقت. يجب تحديث التوكن في Replit Secrets.")
    else:
        print("\n❌ فشل تشغيل البوت. حاول مرة أخرى أو قم بفحص السجلات.")

if __name__ == "__main__":
    main()