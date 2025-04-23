#!/usr/bin/env python3
"""
نظام بسيط للحفاظ على استمرارية تشغيل البوت

هذا السكريبت يقوم بتحديث ملف نبضات القلب بشكل دوري، مما يسمح
لنظام المراقبة بمعرفة أن البوت لا يزال يعمل.
"""
import os
import sys
import time
import logging
import datetime
import threading
import json
import signal

# إعداد التسجيل
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    filename='logs/simple_keepalive.log'
)

# المتغيرات العامة
HEARTBEAT_FILE = "bot_heartbeat.txt"
HEARTBEAT_INTERVAL = 10  # ثوانٍ
keep_running = True

def update_heartbeat():
    """تحديث ملف نبضات القلب بالوقت الحالي"""
    try:
        with open(HEARTBEAT_FILE, 'w') as f:
            f.write(datetime.datetime.now().isoformat())
        return True
    except Exception as e:
        logging.error(f"فشل في تحديث ملف نبضات القلب: {e}")
        return False

def heartbeat_thread():
    """خيط تحديث نبضات القلب"""
    while keep_running:
        try:
            update_heartbeat()
            logging.debug(f"تم تحديث ملف نبضات القلب: {datetime.datetime.now().isoformat()}")
        except Exception as e:
            logging.error(f"خطأ في تحديث ملف نبضات القلب: {e}")
        
        time.sleep(HEARTBEAT_INTERVAL)

def signal_handler(sig, frame):
    """معالج إشارات النظام"""
    global keep_running
    logging.info("تم استلام إشارة إيقاف")
    keep_running = False
    print("\nتم استلام طلب إيقاف، جارٍ الإيقاف...")

def main():
    """الوظيفة الرئيسية"""
    global keep_running
    
    # تسجيل معالجات الإشارات
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    # تهيئة نظام السجلات
    os.makedirs("logs", exist_ok=True)
    
    # تهيئة ملف نبضات القلب الأولي
    update_heartbeat()
    
    # بدء خيط تحديث نبضات القلب
    heartbeat = threading.Thread(target=heartbeat_thread)
    heartbeat.daemon = True
    heartbeat.start()
    
    print("🤖 نظام الحفاظ على استمرارية البوت البسيط 🤖")
    print("===========================================")
    print(f"✅ بدء التشغيل في: {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"✅ فترة تحديث نبضات القلب: كل {HEARTBEAT_INTERVAL} ثوانٍ")
    print(f"✅ ملف نبضات القلب: {HEARTBEAT_FILE}")
    print(f"✅ ملف السجلات: logs/simple_keepalive.log")
    print("\nجارٍ تحديث ملف نبضات القلب، اضغط Ctrl+C للإيقاف...")
    
    # الانتظار حتى يتم إيقاف البرنامج
    try:
        while keep_running:
            time.sleep(1)
    except KeyboardInterrupt:
        keep_running = False
    finally:
        print("\n👋 تم إيقاف نظام الحفاظ على استمرارية البوت. مع السلامة!")

if __name__ == "__main__":
    main()