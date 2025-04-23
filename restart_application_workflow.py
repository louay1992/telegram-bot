#!/usr/bin/env python3
"""
أداة لإعادة تشغيل workflow التطبيق
يقوم بإيقاف وإعادة تشغيل تطبيق Flask
"""
import os
import sys
import time
import logging
import json
import subprocess
import psutil
import signal
from datetime import datetime

# إعداد التسجيل
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    filename='logs/workflow_restart.log'
)
logger = logging.getLogger("WorkflowRestart")

# إضافة معالج لعرض السجلات في وحدة التحكم
console_handler = logging.StreamHandler()
console_handler.setLevel(logging.INFO)
console_formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
console_handler.setFormatter(console_formatter)
logger.addHandler(console_handler)

def find_application_processes():
    """البحث عن عمليات تطبيق Flask"""
    processes = []
    
    for proc in psutil.process_iter(['pid', 'name', 'cmdline', 'create_time']):
        try:
            cmdline = proc.info['cmdline']
            if cmdline and any(x in ' '.join(cmdline) for x in ['gunicorn', 'main:app', 'main.py']):
                create_time = time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(proc.info['create_time']))
                
                process_info = {
                    'pid': proc.pid,
                    'name': proc.info['name'],
                    'cmdline': ' '.join(cmdline),
                    'create_time': create_time,
                    'running_time': time.time() - proc.info['create_time']
                }
                
                processes.append(process_info)
        except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
            pass
    
    return processes

def kill_processes(processes):
    """إيقاف عمليات محددة"""
    killed_count = 0
    
    for proc in processes:
        try:
            pid = proc['pid']
            logger.info(f"محاولة إيقاف العملية: PID {pid}, الأمر: {proc['cmdline']}")
            
            os.kill(pid, signal.SIGTERM)
            logger.info(f"تم إرسال إشارة SIGTERM للعملية {pid}")
            
            # انتظار لحظة للتحقق من توقف العملية
            time.sleep(2)
            
            # التحقق من توقف العملية
            if psutil.pid_exists(pid):
                os.kill(pid, signal.SIGKILL)
                logger.info(f"تم إرسال إشارة SIGKILL للعملية {pid}")
                time.sleep(1)
            
            if not psutil.pid_exists(pid):
                killed_count += 1
                logger.info(f"تم إيقاف العملية {pid} بنجاح")
            else:
                logger.warning(f"فشل في إيقاف العملية {pid}")
        except Exception as e:
            logger.error(f"خطأ في إيقاف العملية {proc['pid']}: {e}")
    
    return killed_count

def modify_main_py():
    """تعديل ملف main.py للتأكد من استيراد التطبيق بشكل صحيح"""
    try:
        with open('main.py', 'r') as f:
            content = f.read()

        # نتأكد أن الملف يحتوي على التصدير الصحيح
        if "from server import app" in content and not "# تم تحديث الملف للتوافق" in content:
            logger.info("تحديث ملف main.py للتأكد من التوافق...")
            
            new_content = '"""\nملف التطبيق الرئيسي لتشغيل Flask مع gunicorn\n# تم تحديث الملف للتوافق مع واجهة برمجة التطبيقات المعززة\n"""\n'
            new_content += 'from server import app  # للتوافق مع gunicorn\n\n'
            new_content += "# يتم استيراد التطبيق فقط للاستخدام مع gunicorn\n"
            new_content += "# لا يتم تنفيذ أي كود هنا\n\n"
            new_content += "if __name__ == '__main__':\n"
            new_content += "    # لا يتم استدعاء هذا عادة عند استخدام gunicorn\n"
            new_content += "    # ولكن يمكن تشغيله مباشرة للاختبار\n"
            new_content += "    from server import start_server\n"
            new_content += "    start_server()\n"
            
            # حفظ نسخة احتياطية من الملف الأصلي
            with open('main.py.bak', 'w') as f:
                f.write(content)
                
            # كتابة المحتوى الجديد
            with open('main.py', 'w') as f:
                f.write(new_content)
                
            logger.info("تم تحديث ملف main.py بنجاح")
            return True
        else:
            logger.info("ملف main.py بالفعل محدث أو لا يحتاج إلى تحديث")
            return False
    except Exception as e:
        logger.error(f"خطأ في تحديث ملف main.py: {e}")
        return False
        
def restart_application_workflow():
    """إعادة تشغيل workflow التطبيق"""
    try:
        logger.info("التحقق من حالة تطبيق Flask...")
        
        # البحث عن عمليات تطبيق Flask
        app_processes = find_application_processes()
        
        if app_processes:
            logger.info(f"تم العثور على {len(app_processes)} عملية متعلقة بتطبيق Flask")
            
            for i, proc in enumerate(app_processes):
                logger.info(f"[{i+1}] PID: {proc['pid']}, العمر: {proc['running_time']:.2f} ثانية, الأمر: {proc['cmdline']}")
            
            # إيقاف عمليات تطبيق Flask
            killed_count = kill_processes(app_processes)
            logger.info(f"تم إيقاف {killed_count} عملية من عمليات تطبيق Flask")
        else:
            logger.info("لم يتم العثور على عمليات متعلقة بتطبيق Flask")
        
        # تعديل ملف main.py إذا لزم الأمر
        modify_main_py()
        
        # إعادة تشغيل تطبيق Flask
        logger.info("جارٍ إعادة تشغيل workflow 'Start application'...")
        
        # إعادة تشغيل Workflow
        subprocess.run(["replit", "workflow", "restart", "Start application"], check=False)
        
        logger.info("تم إرسال طلب إعادة تشغيل Workflow بنجاح")
        
        return True
    except Exception as e:
        logger.error(f"خطأ في إعادة تشغيل workflow التطبيق: {e}")
        return False

if __name__ == "__main__":
    # إنشاء مجلد السجلات
    os.makedirs("logs", exist_ok=True)
    
    # إعادة تشغيل workflow التطبيق
    logger.info("بدء عملية إعادة تشغيل workflow التطبيق...")
    success = restart_application_workflow()
    
    if success:
        logger.info("تمت عملية إعادة تشغيل workflow التطبيق بنجاح")
        sys.exit(0)
    else:
        logger.error("فشلت عملية إعادة تشغيل workflow التطبيق")
        sys.exit(1)