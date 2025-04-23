#!/usr/bin/env python3
"""
سكريبت مراقبة البوت
يراقب ملف نبضات القلب ويعيد تشغيل البوت إذا توقف
"""
import os
import sys
import time
import logging
import datetime
import subprocess
import signal
import json

# إعداد التسجيل
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    filename='logs/bot_monitor.log'
)

# المتغيرات العامة
HEARTBEAT_FILE = "bot_heartbeat.txt"
CHECK_INTERVAL = 60  # ثوانٍ
MAX_HEARTBEAT_AGE = 120  # ثوانٍ
keep_running = True

def get_heartbeat_age():
    """الحصول على عمر آخر نبضة قلب بالثواني"""
    try:
        if not os.path.exists(HEARTBEAT_FILE):
            return float('inf')  # قيمة لا نهائية إذا لم يكن الملف موجودًا
        
        mtime = os.path.getmtime(HEARTBEAT_FILE)
        age_seconds = time.time() - mtime
        return age_seconds
    except Exception as e:
        logging.error(f"خطأ في قراءة ملف نبضات القلب: {e}")
        return float('inf')

def start_bot():
    """بدء تشغيل البوت"""
    try:
        logging.info("بدء تشغيل البوت...")
        
        # إنشاء علامة البدء النظيف
        with open("bot_start_clean", "w") as f:
            f.write(datetime.datetime.now().isoformat())
        
        # تشغيل مسار العمل telegram_bot
        if os.path.exists("start_all_on_reboot.sh"):
            subprocess.Popen(["bash", "start_all_on_reboot.sh"])
            logging.info("تم تشغيل البوت باستخدام start_all_on_reboot.sh")
        else:
            subprocess.Popen(["python", "custom_bot.py"])
            logging.info("تم تشغيل البوت باستخدام custom_bot.py")
        
        return True
    except Exception as e:
        logging.error(f"خطأ في بدء تشغيل البوت: {e}")
        return False

def signal_handler(sig, frame):
    """معالج إشارات النظام"""
    global keep_running
    logging.info("تم استلام إشارة إيقاف")
    keep_running = False
    print("\nتم استلام طلب إيقاف، جارٍ الإيقاف...")

def notify_admin(message):
    """إرسال إشعار للمسؤول"""
    logging.info(f"إشعار للمسؤول: {message}")
    # يمكن إضافة رمز لإرسال إشعارات للمسؤول هنا
    
    # سجل الإشعار في ملف
    try:
        with open("monitor_alerts.json", "a") as f:
            f.write(json.dumps({
                "timestamp": datetime.datetime.now().isoformat(),
                "message": message
            }) + "\n")
    except Exception as e:
        logging.error(f"خطأ في تسجيل الإشعار: {e}")

def main():
    """الوظيفة الرئيسية"""
    global keep_running
    
    # تسجيل معالجات الإشارات
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    # تهيئة نظام السجلات
    os.makedirs("logs", exist_ok=True)
    
    print("🤖 نظام مراقبة البوت 🤖")
    print("========================")
    print(f"✅ بدء التشغيل في: {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"✅ فترة فحص نبضات القلب: كل {CHECK_INTERVAL} ثانية")
    print(f"✅ الحد الأقصى لعمر نبضات القلب: {MAX_HEARTBEAT_AGE} ثانية")
    print(f"✅ ملف نبضات القلب: {HEARTBEAT_FILE}")
    print(f"✅ ملف السجلات: logs/bot_monitor.log")
    print("\nجارٍ مراقبة حالة البوت، اضغط Ctrl+C للإيقاف...")
    
    restart_count = 0
    last_restart = None
    
    # حلقة المراقبة الرئيسية
    while keep_running:
        try:
            # الحصول على عمر آخر نبضة قلب
            heartbeat_age = get_heartbeat_age()
            
            if heartbeat_age > MAX_HEARTBEAT_AGE:
                logging.warning(f"⚠️ البوت متوقف! آخر نبضة قلب: {heartbeat_age:.1f} ثانية مضت")
                
                # تحديد إذا كان يجب إعادة التشغيل
                should_restart = True
                
                # التحقق من عدد مرات إعادة التشغيل في الساعة الأخيرة
                if last_restart and (datetime.datetime.now() - last_restart).total_seconds() < 3600:
                    restart_count += 1
                    if restart_count > 5:
                        logging.error(f"❌ تم الوصول للحد الأقصى من محاولات إعادة التشغيل ({restart_count}) في الساعة الأخيرة")
                        notify_admin(f"⚠️ تم الوصول للحد الأقصى من محاولات إعادة التشغيل ({restart_count}) في الساعة الأخيرة")
                        should_restart = False
                else:
                    # إعادة تعيين العداد بعد ساعة
                    restart_count = 1
                
                if should_restart:
                    logging.info(f"🔄 إعادة تشغيل البوت (المحاولة #{restart_count})...")
                    if start_bot():
                        last_restart = datetime.datetime.now()
                        logging.info(f"✅ تم إعادة تشغيل البوت بنجاح في {last_restart}")
                        notify_admin(f"✅ تم إعادة تشغيل البوت بنجاح (المحاولة #{restart_count})")
                    else:
                        logging.error("❌ فشل في إعادة تشغيل البوت!")
                        notify_admin("❌ فشل في إعادة تشغيل البوت!")
            else:
                logging.debug(f"✅ البوت يعمل بشكل طبيعي. آخر نبضة قلب: {heartbeat_age:.1f} ثانية مضت")
        except Exception as e:
            logging.error(f"خطأ في مراقبة البوت: {e}")
        
        # الانتظار قبل الفحص التالي
        for _ in range(CHECK_INTERVAL):
            if not keep_running:
                break
            time.sleep(1)
    
    print("\n👋 تم إيقاف نظام مراقبة البوت. مع السلامة!")

if __name__ == "__main__":
    main()