#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
نظام التشغيل المتكامل للبوت
--------------------------------------------------------------------
هذا الملف يقوم بتشغيل كافة مكونات النظام المطلوبة لضمان استمرارية البوت 24/7
1. permanent_bot.py - مراقب خارجي لنبضات القلب وإعادة التشغيل التلقائي
2. keep_alive_external.py - خادم خارجي للمراقبة عبر UptimeRobot
3. auto_restart_system.py - نظام مراقبة الموارد وإعادة التشغيل الذكي
4. main.py - تشغيل البوت وخادم Flask بالتزامن
"""

import os
import sys
import time
import signal
import logging
import subprocess
import threading
import atexit

# إنشاء مجلد للسجلات إذا لم يكن موجودًا
os.makedirs('logs', exist_ok=True)

# إعداد نظام السجلات
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler("logs/always_on_system.log", encoding='utf-8')
    ]
)
logger = logging.getLogger("always_on_system")

# متغيرات عامة
processes = {}
stop_all = False


def cleanup():
    """تنظيف الموارد عند إيقاف النظام"""
    global stop_all, processes
    logger.info("تنظيف الموارد قبل الإيقاف")
    
    stop_all = True
    
    # إنهاء جميع العمليات
    for name, process in processes.items():
        try:
            if process and process.poll() is None:
                logger.info(f"إنهاء العملية: {name}")
                process.terminate()
                try:
                    process.wait(timeout=5)
                except:
                    process.kill()
        except Exception as e:
            logger.error(f"خطأ في إنهاء العملية {name}: {e}")


def run_command(command, name):
    """تشغيل أمر كعملية منفصلة مع تسجيل المخرجات"""
    global processes
    
    try:
        logger.info(f"بدء تشغيل: {name} - الأمر: {command}")
        
        # التأكد من عدم وجود مسار Python في الأمر
        if isinstance(command, list) and command[0] == sys.executable:
            # قد يكون الأمر بصيغة [sys.executable, "script.py"]
            log_file = f"logs/{command[1].replace('.py', '')}.log"
        else:
            # قد يكون الأمر بصيغة "python script.py"
            script_name = command.split()[-1] if isinstance(command, str) else command[-1]
            log_file = f"logs/{script_name.replace('.py', '')}.log"
        
        # فتح ملف سجل للمخرجات
        log_handle = open(log_file, "a", encoding="utf-8")
        
        # بدء العملية
        if isinstance(command, list):
            process = subprocess.Popen(
                command,
                stdout=log_handle,
                stderr=subprocess.STDOUT,
                universal_newlines=True
            )
        else:
            process = subprocess.Popen(
                command,
                shell=True,
                stdout=log_handle,
                stderr=subprocess.STDOUT,
                universal_newlines=True
            )
        
        # تخزين العملية ومقبض الملف
        processes[name] = process
        process._log_handle = log_handle
        
        logger.info(f"تم بدء تشغيل {name} بنجاح (PID: {process.pid})")
        
    except Exception as e:
        logger.error(f"فشل في تشغيل {name}: {e}")
        import traceback
        logger.error(traceback.format_exc())


def start_permanent_bot():
    """تشغيل مراقب البوت الدائم"""
    run_command([sys.executable, "permanent_bot.py"], "permanent_bot")


def start_keep_alive():
    """تشغيل نظام المراقبة الخارجية"""
    run_command([sys.executable, "keep_alive_external.py"], "keep_alive")


def start_auto_restart():
    """تشغيل نظام إعادة التشغيل التلقائي"""
    run_command([sys.executable, "auto_restart_system.py"], "auto_restart")


def start_flask_server():
    """تشغيل خادم Flask مع البوت"""
    run_command([sys.executable, "main.py"], "main")


def monitor_processes():
    """مراقبة العمليات وإعادة تشغيل أي منها في حالة توقفها"""
    global stop_all, processes
    
    checked_components = {
        "permanent_bot": start_permanent_bot,
        "keep_alive": start_keep_alive,
        "auto_restart": start_auto_restart,
        "main": start_flask_server
    }
    
    last_check_time = {}
    min_restart_interval = 60  # الحد الأدنى للفاصل الزمني بين عمليات إعادة التشغيل (ثوانية)
    
    logger.info("بدء مراقبة العمليات")
    
    while not stop_all:
        for name, start_func in checked_components.items():
            try:
                # التحقق من وقت آخر فحص
                now = time.time()
                if name in last_check_time and (now - last_check_time[name]) < min_restart_interval:
                    continue
                    
                # التحقق من العملية
                if name not in processes or processes[name].poll() is not None:
                    logger.warning(f"العملية {name} متوقفة، جاري إعادة التشغيل")
                    
                    # إغلاق مقبض السجل إذا كان موجودًا
                    if name in processes and hasattr(processes[name], '_log_handle'):
                        try:
                            processes[name]._log_handle.close()
                        except:
                            pass
                    
                    # إعادة تشغيل العملية
                    start_func()
                    last_check_time[name] = now
                    
            except Exception as e:
                logger.error(f"خطأ في مراقبة العملية {name}: {e}")
                import traceback
                logger.error(traceback.format_exc())
        
        # الانتظار قبل الفحص التالي
        time.sleep(30)


def signal_handler(sig, frame):
    """معالجة إشارات الإيقاف"""
    logger.info(f"تم استلام إشارة الإيقاف: {sig}")
    cleanup()
    sys.exit(0)


def main():
    """النقطة الرئيسية للتشغيل"""
    logger.info("بدء تشغيل نظام التشغيل المتكامل للبوت")
    
    # التأكد من وجود المجلدات الضرورية
    os.makedirs('logs', exist_ok=True)
    os.makedirs('data', exist_ok=True)
    os.makedirs('temp_media', exist_ok=True)
    
    # تسجيل معالجات الإشارات
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    # تسجيل وظيفة التنظيف
    atexit.register(cleanup)
    
    try:
        # بدء تشغيل المكونات بترتيب محدد
        
        # 1. تشغيل خادم Flask مع البوت
        start_flask_server()
        time.sleep(5)  # الانتظار للتأكد من بدء الخادم
        
        # 2. تشغيل نظام المراقبة الخارجية
        start_keep_alive()
        time.sleep(2)
        
        # 3. تشغيل مراقب البوت الدائم
        start_permanent_bot()
        time.sleep(2)
        
        # 4. تشغيل نظام إعادة التشغيل التلقائي
        start_auto_restart()
        time.sleep(2)
        
        logger.info("تم بدء تشغيل جميع المكونات بنجاح")
        
        # بدء مراقبة العمليات في خيط منفصل
        monitor_thread = threading.Thread(target=monitor_processes)
        monitor_thread.daemon = True
        monitor_thread.start()
        
        # الاستمرار في التشغيل
        while True:
            # طباعة حالة جميع العمليات
            logger.info("حالة المكونات:")
            for name, process in processes.items():
                status = "نشط" if process.poll() is None else f"متوقف (رمز الخروج: {process.poll()})"
                logger.info(f"- {name}: {status} (PID: {process.pid})")
            
            # الانتظار قبل التحقق مرة أخرى
            time.sleep(60)
            
    except KeyboardInterrupt:
        logger.info("تم إيقاف النظام بواسطة المستخدم")
    except Exception as e:
        logger.error(f"خطأ عام: {e}")
        import traceback
        logger.error(traceback.format_exc())
    finally:
        cleanup()
    
    return 0


if __name__ == "__main__":
    sys.exit(main())