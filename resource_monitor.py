#!/usr/bin/env python3
"""
وحدة مراقبة الموارد - تراقب استخدام الذاكرة والمعالج وتنظف الموارد عند الحاجة
"""
import os
import sys
import time
import logging
import gc
import datetime
import json
import threading
import psutil
from logging.handlers import RotatingFileHandler

# استيراد التكوين الموحد
try:
    from unified_config import get_config
except ImportError:
    # استخدام القيم الافتراضية إذا لم يكن ملف التكوين متاحاً
    def get_config(key=None):
        defaults = {
            "LOGS_DIR": "logs",
            "MEMORY_THRESHOLD": 200,  # ميغابايت
            "MEMORY_CHECK_INTERVAL": 3600,  # ثانية (ساعة)
            "LOG_MAX_SIZE": 10 * 1024 * 1024,
            "LOG_BACKUP_COUNT": 5
        }
        if key is None:
            return defaults
        return defaults.get(key)

# إعداد التسجيل
log_dir = get_config("LOGS_DIR")
os.makedirs(log_dir, exist_ok=True)
log_file = os.path.join(log_dir, "resource_monitor.log")

logger = logging.getLogger("ResourceMonitor")
logger.setLevel(logging.INFO)

# معالج الملف
file_handler = RotatingFileHandler(
    log_file,
    maxBytes=get_config("LOG_MAX_SIZE"),
    backupCount=get_config("LOG_BACKUP_COUNT")
)
file_handler.setFormatter(logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s'))
logger.addHandler(file_handler)

# معالج وحدة التحكم
console_handler = logging.StreamHandler()
console_handler.setFormatter(logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s'))
logger.addHandler(console_handler)

class ResourceMonitor:
    """
    فئة لمراقبة موارد النظام والتنظيف عند الحاجة
    """
    def __init__(self, check_interval=None, memory_threshold=None):
        """
        تهيئة مراقب الموارد
        
        المعلمات:
            check_interval: الفاصل الزمني بين عمليات الفحص (بالثواني)
            memory_threshold: عتبة استخدام الذاكرة (بالميغابايت) التي تستدعي تنظيف الذاكرة
        """
        self.check_interval = check_interval or get_config("MEMORY_CHECK_INTERVAL")
        self.memory_threshold = memory_threshold or get_config("MEMORY_THRESHOLD")
        self.metrics_file = os.path.join(get_config("LOGS_DIR"), "resource_metrics.json")
        self.keep_running = False
        self.monitoring_thread = None
        self.metrics = []
        self.load_metrics()
    
    def load_metrics(self):
        """تحميل سجل القياسات السابقة"""
        try:
            if os.path.exists(self.metrics_file):
                with open(self.metrics_file, 'r') as f:
                    self.metrics = json.load(f)
                logger.info(f"تم تحميل {len(self.metrics)} قياس سابق")
        except Exception as e:
            logger.error(f"خطأ في تحميل القياسات: {e}")
            self.metrics = []
    
    def save_metrics(self):
        """حفظ سجل القياسات"""
        try:
            # الاحتفاظ بآخر 1000 قياس فقط
            if len(self.metrics) > 1000:
                self.metrics = self.metrics[-1000:]
            
            with open(self.metrics_file, 'w') as f:
                json.dump(self.metrics, f)
            logger.debug(f"تم حفظ {len(self.metrics)} قياس")
        except Exception as e:
            logger.error(f"خطأ في حفظ القياسات: {e}")
    
    def get_process_info(self):
        """الحصول على معلومات العملية الحالية"""
        process = psutil.Process(os.getpid())
        
        # استخدام الذاكرة
        memory_info = process.memory_info()
        memory_usage_mb = memory_info.rss / 1024 / 1024
        
        # استخدام المعالج
        cpu_percent = process.cpu_percent(interval=0.5)
        
        # عدد الخيوط
        num_threads = process.num_threads()
        
        # الوقت المنقضي
        create_time = datetime.datetime.fromtimestamp(process.create_time())
        elapsed_time = (datetime.datetime.now() - create_time).total_seconds()
        
        # معلومات النظام
        system_memory = psutil.virtual_memory()
        system_memory_usage_percent = system_memory.percent
        
        return {
            "timestamp": datetime.datetime.now().isoformat(),
            "memory_usage_mb": round(memory_usage_mb, 2),
            "cpu_percent": round(cpu_percent, 2),
            "num_threads": num_threads,
            "elapsed_time_sec": round(elapsed_time, 2),
            "system_memory_percent": round(system_memory_usage_percent, 2)
        }
    
    def clean_memory(self, force=False):
        """
        تنظيف الذاكرة عندما يتجاوز استخدامها العتبة المحددة
        
        المعلمات:
            force: إذا كان True، يتم تنظيف الذاكرة بغض النظر عن استخدامها
        """
        try:
            process = psutil.Process(os.getpid())
            memory_usage_mb = process.memory_info().rss / 1024 / 1024
            
            if force or memory_usage_mb > self.memory_threshold:
                logger.warning(f"بدء تنظيف الذاكرة. الاستخدام الحالي: {memory_usage_mb:.2f} ميغابايت")
                
                # جمع الكائنات غير المستخدمة
                collected = gc.collect()
                
                # قياس استخدام الذاكرة بعد التنظيف
                memory_usage_after = process.memory_info().rss / 1024 / 1024
                memory_saved = memory_usage_mb - memory_usage_after
                
                logger.info(f"اكتمل تنظيف الذاكرة. تم تحرير {collected} كائن، توفير {memory_saved:.2f} ميغابايت")
                return True
            
            return False
        except Exception as e:
            logger.error(f"خطأ في تنظيف الذاكرة: {e}")
            return False
    
    def monitor_thread(self):
        """خيط مراقبة الموارد"""
        logger.info(f"بدء مراقبة الموارد (الفاصل الزمني: {self.check_interval}ث، عتبة الذاكرة: {self.memory_threshold} ميغابايت)")
        
        while self.keep_running:
            try:
                # جمع معلومات الموارد
                process_info = self.get_process_info()
                self.metrics.append(process_info)
                
                # تسجيل المعلومات
                logger.info(f"استخدام الموارد: ذاكرة={process_info['memory_usage_mb']:.2f}MB, معالج={process_info['cpu_percent']}%, خيوط={process_info['num_threads']}")
                
                # تنظيف الذاكرة إذا تجاوزت العتبة
                if process_info['memory_usage_mb'] > self.memory_threshold:
                    self.clean_memory()
                
                # حفظ القياسات كل 10 مرات
                if len(self.metrics) % 10 == 0:
                    self.save_metrics()
                
                # انتظار الفحص التالي
                for _ in range(self.check_interval):
                    if not self.keep_running:
                        break
                    time.sleep(1)
                
            except Exception as e:
                logger.error(f"خطأ في مراقبة الموارد: {e}")
                time.sleep(60)  # انتظار قبل المحاولة مرة أخرى في حالة حدوث خطأ
    
    def start(self):
        """بدء مراقبة الموارد"""
        if self.monitoring_thread is not None and self.monitoring_thread.is_alive():
            logger.warning("مراقبة الموارد قيد التشغيل بالفعل")
            return False
        
        self.keep_running = True
        self.monitoring_thread = threading.Thread(target=self.monitor_thread)
        self.monitoring_thread.daemon = True
        self.monitoring_thread.start()
        
        return True
    
    def stop(self):
        """إيقاف مراقبة الموارد"""
        self.keep_running = False
        
        if self.monitoring_thread is not None:
            self.monitoring_thread.join(timeout=10)
            
        # حفظ القياسات عند الإيقاف
        self.save_metrics()
        
        logger.info("تم إيقاف مراقبة الموارد")
        return True
    
    def get_resource_summary(self):
        """الحصول على ملخص استخدام الموارد"""
        if not self.metrics:
            return "لا توجد بيانات متاحة"
        
        # حساب متوسط وأقصى استخدام
        memory_values = [m['memory_usage_mb'] for m in self.metrics]
        cpu_values = [m['cpu_percent'] for m in self.metrics]
        
        avg_memory = sum(memory_values) / len(memory_values) if memory_values else 0
        max_memory = max(memory_values) if memory_values else 0
        avg_cpu = sum(cpu_values) / len(cpu_values) if cpu_values else 0
        max_cpu = max(cpu_values) if cpu_values else 0
        
        # الحصول على آخر قياس
        latest = self.metrics[-1] if self.metrics else {}
        
        return {
            "current": {
                "memory_mb": latest.get('memory_usage_mb', 0),
                "cpu_percent": latest.get('cpu_percent', 0),
                "threads": latest.get('num_threads', 0),
                "system_memory_percent": latest.get('system_memory_percent', 0)
            },
            "average": {
                "memory_mb": round(avg_memory, 2),
                "cpu_percent": round(avg_cpu, 2)
            },
            "maximum": {
                "memory_mb": round(max_memory, 2),
                "cpu_percent": round(max_cpu, 2)
            },
            "measurements_count": len(self.metrics),
            "last_measurement": latest.get('timestamp', '')
        }

# إنشاء نسخة عامة من مراقب الموارد
monitor = ResourceMonitor()

def start_monitoring():
    """بدء مراقبة الموارد"""
    return monitor.start()

def stop_monitoring():
    """إيقاف مراقبة الموارد"""
    return monitor.stop()

def get_resource_summary():
    """الحصول على ملخص استخدام الموارد"""
    return monitor.get_resource_summary()

def clean_memory(force=False):
    """تنظيف الذاكرة"""
    return monitor.clean_memory(force)

if __name__ == "__main__":
    # اختبار وحدة مراقبة الموارد
    print("=== اختبار مراقبة الموارد ===")
    
    # جمع معلومات الموارد الحالية
    process = psutil.Process(os.getpid())
    memory_before = process.memory_info().rss / 1024 / 1024
    
    print(f"استخدام الذاكرة الحالي: {memory_before:.2f} ميغابايت")
    
    # إنشاء بعض البيانات لزيادة استخدام الذاكرة
    data = [bytearray(1024 * 1024) for _ in range(10)]  # إنشاء حوالي 10 ميغابايت من البيانات
    
    # قياس استخدام الذاكرة بعد إنشاء البيانات
    memory_after = process.memory_info().rss / 1024 / 1024
    print(f"استخدام الذاكرة بعد إنشاء البيانات: {memory_after:.2f} ميغابايت")
    print(f"زيادة الذاكرة: {memory_after - memory_before:.2f} ميغابايت")
    
    # تنظيف الذاكرة
    print("تنظيف الذاكرة...")
    gc.collect()
    del data
    gc.collect()
    
    # قياس استخدام الذاكرة بعد التنظيف
    memory_after_cleanup = process.memory_info().rss / 1024 / 1024
    print(f"استخدام الذاكرة بعد التنظيف: {memory_after_cleanup:.2f} ميغابايت")
    print(f"الذاكرة المحررة: {memory_after - memory_after_cleanup:.2f} ميغابايت")
    
    # اختبار مراقب الموارد
    test_monitor = ResourceMonitor(check_interval=5, memory_threshold=10)
    test_monitor.start()
    
    print("\nمراقبة الموارد لمدة 10 ثوانٍ...")
    time.sleep(10)
    
    print("\nالحصول على ملخص الموارد:")
    summary = test_monitor.get_resource_summary()
    
    if isinstance(summary, dict):
        print(f"القياسات: {summary['measurements_count']}")
        print(f"الذاكرة الحالية: {summary['current']['memory_mb']} ميغابايت")
        print(f"استخدام المعالج: {summary['current']['cpu_percent']}%")
    else:
        print(summary)
    
    test_monitor.stop()
    print("تم إيقاف مراقبة الموارد")