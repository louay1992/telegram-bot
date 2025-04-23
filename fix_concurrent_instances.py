#!/usr/bin/env python3
"""
أداة لإصلاح مشكلة تشغيل نسخ متعددة من البوت بنفس الوقت
تبحث هذه الأداة عن عمليات البوت الجارية وتوقفها إذا لزم الأمر
"""
import os
import sys
import time
import signal
import logging
import psutil
import subprocess
from typing import List, Dict, Optional, Tuple

# إعداد التسجيل
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    filename='logs/fix_concurrent.log'
)
logger = logging.getLogger("ConcurrentInstancesFixer")

# إضافة معالج لعرض السجلات في وحدة التحكم
console_handler = logging.StreamHandler()
console_handler.setLevel(logging.INFO)
console_formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
console_handler.setFormatter(console_formatter)
logger.addHandler(console_handler)

def find_bot_processes() -> List[Dict]:
    """البحث عن عمليات البوت الجارية"""
    bot_processes = []
    
    # قائمة أنماط أسماء ملفات البوت
    bot_patterns = [
        "bot.py", 
        "custom_bot.py", 
        "enhanced_bot.py", 
        "telegram_bot.py"
    ]
    
    for proc in psutil.process_iter(['pid', 'name', 'cmdline', 'create_time']):
        try:
            # التحقق مما إذا كانت العملية تتطابق مع أحد أنماط البوت
            if proc.info['cmdline'] and any(pattern in ' '.join(proc.info['cmdline']) for pattern in bot_patterns):
                create_time = time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(proc.info['create_time']))
                
                # الحصول على معلومات إضافية عن العملية
                process_info = {
                    'pid': proc.pid,
                    'name': proc.info['name'],
                    'cmdline': ' '.join(proc.info['cmdline']) if proc.info['cmdline'] else "",
                    'create_time': create_time,
                    'running_time': time.time() - proc.info['create_time']
                }
                
                bot_processes.append(process_info)
        except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
            pass
    
    return bot_processes

def find_lock_files() -> List[str]:
    """البحث عن ملفات القفل المتعلقة بالبوت"""
    lock_files = []
    
    # قائمة أنماط أسماء ملفات القفل
    lock_patterns = ["bot.lock", "instance.lock", "telegram_bot.lock"]
    
    for pattern in lock_patterns:
        if os.path.exists(pattern):
            lock_files.append(pattern)
    
    return lock_files

def check_heartbeat_file() -> Tuple[bool, Optional[float]]:
    """التحقق من وجود ملف نبضات القلب وعمره"""
    heartbeat_file = "bot_heartbeat.txt"
    
    if not os.path.exists(heartbeat_file):
        return False, None
    
    try:
        with open(heartbeat_file, 'r') as f:
            timestamp = float(f.read().strip())
        
        heartbeat_age = time.time() - timestamp
        return True, heartbeat_age
    except:
        return True, None

def kill_process(pid: int) -> bool:
    """إيقاف عملية معينة"""
    try:
        os.kill(pid, signal.SIGTERM)
        logger.info(f"تم إرسال إشارة SIGTERM للعملية {pid}")
        
        # الانتظار للتأكد من توقف العملية
        time.sleep(2)
        
        # التحقق مما إذا كانت العملية ما زالت موجودة
        if psutil.pid_exists(pid):
            os.kill(pid, signal.SIGKILL)
            logger.info(f"تم إرسال إشارة SIGKILL للعملية {pid}")
            time.sleep(1)
        
        return not psutil.pid_exists(pid)
    except Exception as e:
        logger.error(f"خطأ في إيقاف العملية {pid}: {e}")
        return False

def remove_lock_files() -> int:
    """إزالة ملفات القفل المتعلقة بالبوت"""
    lock_files = find_lock_files()
    removed_count = 0
    
    for lock_file in lock_files:
        try:
            os.remove(lock_file)
            logger.info(f"تم حذف ملف القفل: {lock_file}")
            removed_count += 1
        except Exception as e:
            logger.error(f"خطأ في حذف ملف القفل {lock_file}: {e}")
    
    return removed_count

def fix_concurrent_instances() -> bool:
    """إصلاح مشكلة تشغيل نسخ متعددة من البوت"""
    logger.info("بدء تشخيص مشكلة تشغيل نسخ متعددة من البوت...")
    
    # البحث عن عمليات البوت الجارية
    bot_processes = find_bot_processes()
    
    if not bot_processes:
        logger.info("لم يتم العثور على أي عمليات للبوت")
        
        # التحقق من ملف نبضات القلب
        has_heartbeat, heartbeat_age = check_heartbeat_file()
        
        if has_heartbeat:
            if heartbeat_age is not None:
                logger.info(f"تم العثور على ملف نبضات القلب، عمره: {heartbeat_age:.2f} ثانية")
            else:
                logger.info("تم العثور على ملف نبضات القلب، لكن لا يمكن قراءة الطابع الزمني")
        else:
            logger.info("لم يتم العثور على ملف نبضات القلب")
        
        # حذف ملفات القفل
        removed_count = remove_lock_files()
        if removed_count > 0:
            logger.info(f"تم حذف {removed_count} ملف قفل")
        
        return True
    
    # عرض معلومات عن عمليات البوت الجارية
    logger.info(f"تم العثور على {len(bot_processes)} عملية للبوت:")
    
    for i, proc in enumerate(bot_processes):
        logger.info(f"[{i+1}] PID: {proc['pid']}, العمر: {proc['running_time']:.2f} ثانية, الأمر: {proc['cmdline']}")
    
    # ترتيب العمليات حسب وقت الإنشاء (الأقدم أولاً)
    bot_processes.sort(key=lambda x: x['create_time'])
    
    # الاحتفاظ بالعملية الأحدث وإيقاف الباقي
    if len(bot_processes) > 1:
        newest_process = bot_processes[-1]
        logger.info(f"الاحتفاظ بالعملية الأحدث: PID {newest_process['pid']}, وقت الإنشاء: {newest_process['create_time']}")
        
        killed_count = 0
        for proc in bot_processes[:-1]:
            logger.info(f"محاولة إيقاف العملية: PID {proc['pid']}, وقت الإنشاء: {proc['create_time']}")
            if kill_process(proc['pid']):
                killed_count += 1
                logger.info(f"تم إيقاف العملية بنجاح: PID {proc['pid']}")
            else:
                logger.warning(f"فشل في إيقاف العملية: PID {proc['pid']}")
        
        if killed_count > 0:
            logger.info(f"تم إيقاف {killed_count} عملية من عمليات البوت القديمة")
    else:
        logger.info("تم العثور على عملية واحدة فقط للبوت، لا حاجة للإيقاف")
    
    # حذف ملفات القفل
    removed_count = remove_lock_files()
    if removed_count > 0:
        logger.info(f"تم حذف {removed_count} ملف قفل")
    
    return True

def start_clean_bot() -> bool:
    """بدء تشغيل البوت بعد التنظيف"""
    logger.info("بدء تشغيل البوت المعزز...")
    
    try:
        # إنشاء المجلدات اللازمة
        os.makedirs("logs", exist_ok=True)
        
        # بدء تشغيل البوت في الخلفية
        subprocess.Popen(["python", "enhanced_bot.py"], 
                         stdout=open("logs/enhanced_bot.log", "a"),
                         stderr=subprocess.STDOUT,
                         start_new_session=True)
        
        logger.info("تم بدء تشغيل البوت المعزز بنجاح")
        return True
    except Exception as e:
        logger.error(f"خطأ في بدء تشغيل البوت: {e}")
        return False

if __name__ == "__main__":
    # إنشاء مجلد السجلات
    os.makedirs("logs", exist_ok=True)
    
    # تحديد وضع التشغيل
    restart_after_fix = "--restart" in sys.argv
    
    # إصلاح مشكلة تشغيل نسخ متعددة من البوت
    fix_successful = fix_concurrent_instances()
    
    if fix_successful and restart_after_fix:
        logger.info("تم إصلاح المشكلة، جارٍ إعادة تشغيل البوت...")
        start_clean_bot()
    elif restart_after_fix:
        logger.warning("فشل في إصلاح المشكلة، لن تتم إعادة تشغيل البوت")
    
    logger.info("اكتمل التنفيذ")