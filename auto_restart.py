#!/usr/bin/env python3
"""
سكريبت إعادة تشغيل تلقائي للبوت.
يعمل هذا السكريبت على إنشاء علامة إعادة تشغيل دورية للبوت للحفاظ على استقرار النظام.
"""

import os
import time
import datetime
import logging

# إعداد التسجيل
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("auto_restart.log"),
        logging.StreamHandler()
    ]
)

logger = logging.getLogger("AutoRestart")

# معلمات التكوين
RESTART_INTERVAL = 30 * 60  # إعادة تشغيل كل 30 دقيقة (للحفاظ على استقرار البوت) - متزامن مع البوت
SHUTDOWN_MARKER_FILE = "bot_shutdown_marker"  # نفس الملف المستخدم في أمر /restart
SCHEDULED_RESTART_MARKER = "scheduled_restart"  # ملف علامة إعادة التشغيل المجدول

def create_restart_marker():
    """إنشاء ملف علامة إعادة التشغيل."""
    try:
        # إنشاء ملف علامة إعادة التشغيل الرئيسي
        with open(SHUTDOWN_MARKER_FILE, 'w') as f:
            f.write(str(datetime.datetime.now().timestamp()))
            f.flush()
            os.fsync(f.fileno())  # التأكد من كتابة البيانات مباشرة للقرص
        
        # إنشاء ملف إضافي للإشارة إلى أن إعادة التشغيل مجدولة
        with open(SCHEDULED_RESTART_MARKER, 'w') as f:
            restart_time = datetime.datetime.now()
            f.write(f"Scheduled restart initiated at {restart_time.isoformat()}")
            f.flush()
            os.fsync(f.fileno())
        
        logger.info("✅ تم إنشاء علامات إعادة التشغيل التلقائي")
        return True
    except Exception as e:
        logger.error(f"❌ فشل في إنشاء علامة إعادة التشغيل: {e}")
        return False

def main():
    """الوظيفة الرئيسية للسكريبت."""
    logger.info("🚀 بدء تشغيل سكريبت إعادة التشغيل التلقائي")
    logger.info(f"⏰ الفاصل الزمني للإعادة: كل {RESTART_INTERVAL / 60:.0f} دقائق")
    
    last_restart = time.time()
    
    try:
        while True:
            now = time.time()
            elapsed = now - last_restart
            
            if elapsed >= RESTART_INTERVAL:
                logger.info(f"🔄 مر {elapsed/60:.1f} دقيقة منذ آخر إعادة تشغيل، سيتم إعادة تشغيل البوت الآن")
                
                # التحقق من حالة الذاكرة قبل إعادة التشغيل
                try:
                    import psutil
                    process = psutil.Process(os.getpid())
                    memory_info = process.memory_info()
                    memory_usage_mb = memory_info.rss / 1024 / 1024
                    logger.info(f"📊 استخدام الذاكرة قبل إعادة التشغيل: {memory_usage_mb:.2f} ميجابايت")
                except ImportError:
                    logger.warning("📛 وحدة psutil غير متاحة، لن يتم تسجيل استخدام الذاكرة")
                except Exception as e:
                    logger.error(f"⚠️ خطأ في الحصول على معلومات الذاكرة: {e}")
                
                if create_restart_marker():
                    last_restart = now
                    logger.info("⏳ انتظار دقيقة قبل الإعادة التالية...")
                    time.sleep(60)  # انتظار دقيقة للسماح للبوت بإعادة التشغيل
                
            # التحقق كل 1 دقيقة (للاستجابة السريعة للتغييرات)
            time.sleep(60)
            
    except KeyboardInterrupt:
        logger.info("تم إيقاف سكريبت إعادة التشغيل التلقائي")
    except Exception as e:
        logger.error(f"خطأ في سكريبت إعادة التشغيل التلقائي: {e}")
        
if __name__ == "__main__":
    main()