#!/usr/bin/env python3
"""
هذا السكريبت يشغل auto_restart.py كعملية منفصلة لضمان استمرارية البوت.
"""

import subprocess
import sys
import logging
import time

# إعداد التسجيل
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("auto_restart_launcher.log"),
        logging.StreamHandler()
    ]
)

logger = logging.getLogger("AutoRestartLauncher")

def main():
    logger.info("🚀 تشغيل برنامج إعادة التشغيل التلقائي...")
    
    try:
        process = subprocess.Popen(
            [sys.executable, "auto_restart.py"],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )
        
        logger.info(f"✅ تم بدء تشغيل auto_restart.py بنجاح، معرف العملية: {process.pid}")
        
        # مراقبة العملية
        try:
            while True:
                # التحقق من استمرار تشغيل العملية
                if process.poll() is not None:
                    exit_code = process.poll()
                    logger.warning(f"⚠️ توقفت عملية إعادة التشغيل التلقائي (رمز الخروج: {exit_code})، جاري إعادة التشغيل...")
                    
                    # إعادة تشغيل العملية
                    process = subprocess.Popen(
                        [sys.executable, "auto_restart.py"],
                        stdout=subprocess.PIPE,
                        stderr=subprocess.PIPE,
                        text=True
                    )
                    logger.info(f"✅ تمت إعادة تشغيل auto_restart.py، معرف العملية الجديدة: {process.pid}")
                
                # انتظار قبل الفحص التالي
                time.sleep(60)
                
        except KeyboardInterrupt:
            logger.info("⛔ تم استلام إشارة إيقاف من المستخدم. جاري إيقاف برنامج إعادة التشغيل التلقائي...")
            if process.poll() is None:
                process.terminate()
                logger.info("✅ تم إيقاف برنامج إعادة التشغيل التلقائي بنجاح")
            
    except Exception as e:
        logger.error(f"❌ حدث خطأ: {e}")

if __name__ == "__main__":
    main()