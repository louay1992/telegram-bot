#!/usr/bin/env python3
"""
وحدة قفل المثيل
تمنع تشغيل عدة مثيلات من البوت في نفس الوقت
"""
import os
import sys
import time
import fcntl
import logging
import signal
import psutil
from typing import Optional, Tuple, Dict, List

# إعداد التسجيل
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# ملف القفل
LOCK_FILE = "bot_instance.lock"

class InstanceLock:
    """
    فئة لإدارة قفل المثيل
    تضمن عدم تشغيل مثيلات متعددة من البوت في نفس الوقت
    """
    def __init__(self, lock_file=LOCK_FILE, auto_kill=True):
        """
        تهيئة قفل المثيل
        
        المعلمات:
            lock_file: مسار ملف القفل
            auto_kill: ما إذا كان يجب إيقاف المثيلات الأخرى تلقائياً
        """
        self.lock_file = lock_file
        self.auto_kill = auto_kill
        self.lock_handle = None
        
    def acquire(self) -> bool:
        """
        الحصول على قفل المثيل
        
        العوائد:
            True إذا تم الحصول على القفل بنجاح، False خلاف ذلك
        """
        try:
            # التحقق من وجود مثيلات أخرى للبوت
            other_instances = self.find_other_instances()
            
            if other_instances and self.auto_kill:
                logger.warning(f"تم العثور على {len(other_instances)} مثيل آخر للبوت")
                self.kill_other_instances(other_instances)
            
            # إنشاء ملف القفل إذا لم يكن موجوداً
            if not os.path.exists(self.lock_file):
                open(self.lock_file, 'w').close()
            
            # محاولة الحصول على القفل
            self.lock_handle = open(self.lock_file, 'r+')
            
            try:
                fcntl.flock(self.lock_handle.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
                # كتابة معرف العملية في ملف القفل
                self.lock_handle.seek(0)
                self.lock_handle.write(str(os.getpid()))
                self.lock_handle.truncate()
                self.lock_handle.flush()
                logger.info(f"تم الحصول على قفل المثيل (PID: {os.getpid()})")
                return True
            except (IOError, OSError):
                # القفل محجوز بواسطة عملية أخرى
                self.lock_handle.close()
                self.lock_handle = None
                
                # قراءة معرف العملية من ملف القفل
                try:
                    with open(self.lock_file, 'r') as f:
                        pid = f.read().strip()
                    logger.warning(f"فشل في الحصول على قفل المثيل: المثيل نشط بالفعل (PID: {pid})")
                except Exception:
                    logger.warning("فشل في الحصول على قفل المثيل: المثيل نشط بالفعل")
                
                return False
        except Exception as e:
            logger.error(f"خطأ في الحصول على قفل المثيل: {e}")
            if self.lock_handle:
                self.lock_handle.close()
                self.lock_handle = None
            return False
    
    def release(self) -> bool:
        """
        تحرير قفل المثيل
        
        العوائد:
            True إذا تم تحرير القفل بنجاح، False خلاف ذلك
        """
        try:
            if self.lock_handle:
                # تحرير القفل
                fcntl.flock(self.lock_handle.fileno(), fcntl.LOCK_UN)
                self.lock_handle.close()
                self.lock_handle = None
                logger.info("تم تحرير قفل المثيل")
                
                # حذف ملف القفل
                try:
                    os.remove(self.lock_file)
                except OSError:
                    pass
                
                return True
            return False
        except Exception as e:
            logger.error(f"خطأ في تحرير قفل المثيل: {e}")
            return False
    
    def __enter__(self):
        """الدخول إلى سياق الإدارة"""
        if not self.acquire():
            # فشل في الحصول على القفل
            logger.error("فشل في الحصول على قفل المثيل، جاري إنهاء البرنامج")
            sys.exit(1)
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """الخروج من سياق الإدارة"""
        self.release()
    
    def find_other_instances(self) -> List[Dict]:
        """
        البحث عن مثيلات أخرى للبوت
        
        العوائد:
            قائمة بمعلومات المثيلات الأخرى
        """
        current_pid = os.getpid()
        other_instances = []
        
        for proc in psutil.process_iter(['pid', 'name', 'cmdline', 'create_time']):
            try:
                # تجاهل العملية الحالية
                if proc.pid == current_pid:
                    continue
                
                # البحث عن عمليات بوت التيليجرام
                cmdline = ' '.join(proc.info['cmdline']) if proc.info['cmdline'] else ''
                if 'python' in cmdline and ('bot.py' in cmdline or 'enhanced_bot.py' in cmdline or 'custom_bot.py' in cmdline):
                    create_time = time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(proc.info['create_time']))
                    
                    other_instances.append({
                        'pid': proc.pid,
                        'name': proc.info['name'],
                        'cmdline': cmdline,
                        'create_time': create_time,
                        'running_time': time.time() - proc.info['create_time']
                    })
            except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
                pass
        
        return other_instances
    
    def kill_other_instances(self, instances: List[Dict]) -> int:
        """
        إيقاف مثيلات أخرى للبوت
        
        المعلمات:
            instances: قائمة بمعلومات المثيلات الأخرى
            
        العوائد:
            عدد المثيلات التي تم إيقافها
        """
        killed_count = 0
        
        for instance in instances:
            try:
                pid = instance['pid']
                logger.warning(f"محاولة إيقاف المثيل: PID {pid}, الأمر: {instance['cmdline']}")
                
                # محاولة إيقاف العملية بشكل آمن
                os.kill(pid, signal.SIGTERM)
                
                # الانتظار لحظة للتحقق من توقف العملية
                time.sleep(2)
                
                # التحقق من توقف العملية
                if psutil.pid_exists(pid):
                    # استخدام SIGKILL إذا لم تتوقف العملية
                    os.kill(pid, signal.SIGKILL)
                    time.sleep(1)
                
                if not psutil.pid_exists(pid):
                    killed_count += 1
                    logger.info(f"تم إيقاف المثيل {pid} بنجاح")
                else:
                    logger.warning(f"فشل في إيقاف المثيل {pid}")
            except Exception as e:
                logger.error(f"خطأ في إيقاف المثيل {instance['pid']}: {e}")
        
        return killed_count

def check_single_instance(exit_on_fail=True) -> bool:
    """
    التحقق من أن العملية هي المثيل الوحيد للبوت
    
    المعلمات:
        exit_on_fail: ما إذا كان يجب إنهاء البرنامج إذا فشل في الحصول على القفل
        
    العوائد:
        True إذا كانت العملية هي المثيل الوحيد، False خلاف ذلك
    """
    lock = InstanceLock()
    result = lock.acquire()
    
    if not result and exit_on_fail:
        logger.error("فشل في الحصول على قفل المثيل، جاري إنهاء البرنامج")
        sys.exit(1)
    
    return result

if __name__ == "__main__":
    # اختبار وحدة قفل المثيل
    logger.info("اختبار وحدة قفل المثيل")
    
    # البحث عن مثيلات أخرى للبوت
    lock = InstanceLock()
    other_instances = lock.find_other_instances()
    
    if other_instances:
        logger.info(f"تم العثور على {len(other_instances)} مثيل آخر للبوت:")
        for i, instance in enumerate(other_instances):
            logger.info(f"[{i+1}] PID: {instance['pid']}, العمر: {instance['running_time']:.2f} ثانية, الأمر: {instance['cmdline']}")
        
        # سؤال المستخدم إذا كان يريد إيقاف المثيلات الأخرى
        response = input("هل تريد إيقاف هذه المثيلات؟ (y/n): ")
        if response.lower() == 'y':
            killed = lock.kill_other_instances(other_instances)
            logger.info(f"تم إيقاف {killed} مثيل")
    else:
        logger.info("لا توجد مثيلات أخرى للبوت")
    
    # اختبار الحصول على القفل
    logger.info("محاولة الحصول على قفل المثيل...")
    with InstanceLock() as lock:
        logger.info("تم الحصول على قفل المثيل")
        logger.info("جارٍ محاكاة تشغيل البوت...")
        
        # محاكاة تشغيل البوت
        for i in range(5):
            logger.info(f"البوت يعمل ({i+1}/5)...")
            time.sleep(1)
        
        logger.info("انتهى تشغيل البوت، سيتم تحرير القفل تلقائياً")