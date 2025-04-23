#!/usr/bin/env python
"""
سكريبت بدء تشغيل كافة أنظمة البوت - Startup All Bot Systems

يقوم هذا السكريبت ببدء تشغيل كافة أنظمة البوت والمراقبة لضمان استمرارية العمل:
1. بدء تشغيل نظام Keep Alive لـ Replit
2. بدء تشغيل نظام نبضات تيليجرام
3. بدء تشغيل البوت الرئيسي
4. بدء تشغيل نظام المراقبة والإشراف
"""

import logging
import os
import subprocess
import sys
import threading
import time

# إعداد التسجيل
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO,
    filename='startup.log'
)
logger = logging.getLogger("StartupSystem")

# تنظيف ملفات العلامات والعمليات القديمة
def cleanup_marker_files():
    """تنظيف ملفات العلامات القديمة"""
    markers = [
        "bot_shutdown_marker",
        "watchdog_ping",
        "bot_restart_marker",
        "restart_requested.log",
        "bot_process.pid"
    ]
    
    for marker in markers:
        if os.path.exists(marker):
            try:
                os.remove(marker)
                logger.info(f"✓ تم حذف ملف العلامة القديم: {marker}")
            except Exception as e:
                logger.error(f"❌ خطأ في حذف ملف العلامة: {marker}: {e}")

# بدء تشغيل خدمة Keep Alive
def start_keep_alive():
    """بدء تشغيل خدمة Keep Alive لـ Replit"""
    try:
        logger.info("🚀 جاري بدء تشغيل خدمة Keep Alive...")
        process = subprocess.Popen(
            [sys.executable, 'keep_alive.py'],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE
        )
        logger.info(f"✅ تم بدء تشغيل خدمة Keep Alive بنجاح (PID: {process.pid})")
        return process.pid
    except Exception as e:
        logger.error(f"❌ خطأ في بدء تشغيل خدمة Keep Alive: {e}")
        return None

# بدء تشغيل نظام نبضات تيليجرام
def start_telegram_alive():
    """بدء تشغيل نظام نبضات تيليجرام"""
    try:
        logger.info("🚀 جاري بدء تشغيل نظام نبضات تيليجرام...")
        process = subprocess.Popen(
            [sys.executable, 'keep_telegram_alive.py'],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE
        )
        logger.info(f"✅ تم بدء تشغيل نظام نبضات تيليجرام بنجاح (PID: {process.pid})")
        return process.pid
    except Exception as e:
        logger.error(f"❌ خطأ في بدء تشغيل نظام نبضات تيليجرام: {e}")
        return None

# بدء تشغيل البوت الرئيسي
def start_bot():
    """بدء تشغيل البوت الرئيسي"""
    try:
        logger.info("🚀 جاري بدء تشغيل البوت الرئيسي...")
        
        # تعيين علامة لاستخدامها في الوظيفة المدمجة في البوت
        with open("bot_start_clean", "w") as f:
            f.write("1")
        
        process = subprocess.Popen(
            [sys.executable, 'bot.py'],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE
        )
        
        # حفظ معرف العملية
        with open("bot_process.pid", "w") as f:
            f.write(str(process.pid))
        
        logger.info(f"✅ تم بدء تشغيل البوت الرئيسي بنجاح (PID: {process.pid})")
        return process.pid
    except Exception as e:
        logger.error(f"❌ خطأ في بدء تشغيل البوت الرئيسي: {e}")
        return None

# بدء تشغيل نظام المراقبة والإشراف
def start_supervisor():
    """بدء تشغيل نظام المراقبة والإشراف"""
    try:
        logger.info("🚀 جاري بدء تشغيل نظام المراقبة والإشراف...")
        process = subprocess.Popen(
            [sys.executable, 'telegram_supervisor.py'],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE
        )
        logger.info(f"✅ تم بدء تشغيل نظام المراقبة والإشراف بنجاح (PID: {process.pid})")
        return process.pid
    except Exception as e:
        logger.error(f"❌ خطأ في بدء تشغيل نظام المراقبة والإشراف: {e}")
        return None

def start_all_systems():
    """بدء تشغيل كافة الأنظمة"""
    try:
        logger.info("🔄 جاري تنظيف ملفات العلامات القديمة...")
        cleanup_marker_files()
        
        logger.info("🔄 جاري بدء تشغيل كافة الأنظمة...")
        
        # 1. بدء تشغيل خدمة Keep Alive
        keep_alive_pid = start_keep_alive()
        
        # إضافة تأخير قصير قبل بدء العملية التالية
        time.sleep(2)
        
        # 2. بدء تشغيل البوت الرئيسي
        bot_pid = start_bot()
        
        # إضافة تأخير قصير قبل بدء العملية التالية
        time.sleep(5)
        
        # 3. بدء تشغيل نظام نبضات تيليجرام
        telegram_alive_pid = start_telegram_alive()
        
        # إضافة تأخير قصير قبل بدء العملية التالية
        time.sleep(2)
        
        # 4. بدء تشغيل نظام المراقبة والإشراف
        supervisor_pid = start_supervisor()
        
        # التحقق من بدء تشغيل كافة الأنظمة بنجاح
        all_started = all([keep_alive_pid, bot_pid, telegram_alive_pid, supervisor_pid])
        
        if all_started:
            logger.info("✅ تم بدء تشغيل كافة الأنظمة بنجاح!")
            
            # كتابة سجل بمعرفات العمليات
            with open("system_pids.log", "w") as f:
                f.write(f"Keep Alive PID: {keep_alive_pid}\n")
                f.write(f"Bot PID: {bot_pid}\n")
                f.write(f"Telegram Alive PID: {telegram_alive_pid}\n")
                f.write(f"Supervisor PID: {supervisor_pid}\n")
            
            return True
        else:
            logger.error("❌ فشل في بدء تشغيل بعض الأنظمة!")
            return False
    except Exception as e:
        logger.error(f"❌ خطأ غير متوقع: {e}")
        return False

if __name__ == "__main__":
    logger.info("🚀 بدء تشغيل سكريبت بدء كافة الأنظمة...")
    
    try:
        # بدء تشغيل كافة الأنظمة في خيط رئيسي
        success = start_all_systems()
        
        if success:
            logger.info("✅ تم تشغيل كافة الأنظمة بنجاح. البوت جاهز للعمل!")
            print("✅ تم تشغيل كافة الأنظمة بنجاح. البوت جاهز للعمل!")
        else:
            logger.error("❌ فشل في بدء تشغيل بعض الأنظمة. راجع السجلات للتفاصيل.")
            print("❌ فشل في بدء تشغيل بعض الأنظمة. راجع السجلات للتفاصيل.")
        
        # نظل في الحلقة الرئيسية للحفاظ على عمل البرنامج
        try:
            while True:
                time.sleep(60)
        except KeyboardInterrupt:
            logger.info("👋 تم إيقاف سكريبت التشغيل بواسطة المستخدم")
    except Exception as e:
        logger.error(f"❌ خطأ في الدالة الرئيسية: {e}")
        print(f"❌ خطأ في الدالة الرئيسية: {e}")