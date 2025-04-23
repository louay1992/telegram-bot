#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
نظام البوت الدائم - محسّن خصيصًا لـ Replit Always-On

هذا الملف مصمم للعمل مباشرة في بيئة Replit Always-On حيث يضمن استمرارية
تشغيل البوت حتى بعد إغلاق متصفح المستخدم من خلال تشغيل البوت كعملية رئيسية.
"""

import os
import sys
import time
import atexit
import logging
import psutil
import signal
import traceback
from datetime import datetime

# إعداد السجلات
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler("logs/always_on_bot.log")
    ]
)
logger = logging.getLogger("always_on_bot")

# التأكد من وجود المجلدات اللازمة
os.makedirs("logs", exist_ok=True)
os.makedirs("data", exist_ok=True)
os.makedirs("temp_media", exist_ok=True)

# ملف نبضات القلب
HEARTBEAT_FILE = "bot_heartbeat.txt"
PID_FILE = "bot_process.pid"

def create_pid_file():
    """إنشاء ملف PID لتتبع عملية البوت"""
    pid = os.getpid()
    with open(PID_FILE, "w") as f:
        f.write(str(pid))
    logger.info(f"تم إنشاء ملف PID: {pid}")

def update_heartbeat():
    """تحديث ملف نبضات القلب"""
    try:
        with open(HEARTBEAT_FILE, "w") as f:
            f.write(str(time.time()))
    except Exception as e:
        logger.error(f"خطأ في تحديث ملف نبضات القلب: {e}")

def cleanup():
    """تنظيف الموارد عند الخروج"""
    logger.info("تنظيف الموارد قبل الخروج...")
    try:
        if os.path.exists(PID_FILE):
            os.remove(PID_FILE)
    except Exception as e:
        logger.error(f"خطأ في تنظيف الموارد: {e}")

def signal_handler(sig, frame):
    """معالج الإشارات لضمان تنظيف الموارد عند الإيقاف"""
    logger.info(f"تم استلام إشارة: {sig}")
    cleanup()
    sys.exit(0)

def setup_signal_handlers():
    """إعداد معالجات الإشارات"""
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)

def start_bot_directly():
    """بدء تشغيل البوت بدون خيوط"""
    logger.info("بدء تشغيل البوت كعملية رئيسية...")
    
    try:
        # استيراد وحدة البوت
        import bot
        
        # بدء تشغيل البوت مباشرة (دون خيوط)
        bot.main()
    except KeyboardInterrupt:
        logger.info("تم إيقاف البوت بواسطة المستخدم")
    except Exception as e:
        logger.error(f"خطأ غير متوقع عند تشغيل البوت: {e}")
        logger.error(traceback.format_exc())

def main():
    """الوظيفة الرئيسية"""
    logger.info("----- بدء تشغيل نظام البوت الدائم -----")
    
    # إعداد وظيفة التنظيف عند الخروج
    atexit.register(cleanup)
    
    # إعداد معالجات الإشارات
    setup_signal_handlers()
    
    # إنشاء ملف PID
    create_pid_file()
    
    # تحديث ملف نبضات القلب
    update_heartbeat()
    
    # بدء تشغيل البوت مباشرة (دون خيوط)
    start_bot_directly()

if __name__ == "__main__":
    main()