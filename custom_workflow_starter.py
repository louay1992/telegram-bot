#!/usr/bin/env python3
"""
سكريبت لإعداد مسار عمل مخصص للبوت المعدل (custom_bot.py)
"""
import os
import json
import time
import subprocess
import signal
import sys
import logging
from datetime import datetime

# إعداد التسجيل
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    filename='custom_workflow_setup.log'
)

# التوكن الجديد
NEW_TOKEN = "7406580104:AAGG2JQeeNfsmcGVMCm7hxitIK-qm2yekVg"

def stop_existing_telegram_workflows():
    """إيقاف مسارات عمل التلغرام الحالية."""
    print("🔍 البحث عن مسارات عمل التلغرام الحالية وإيقافها...")
    
    try:
        # الحصول على معلومات المسارات
        replit_nix_path = ".replit"
        workflow_name = "telegram_bot"
        
        if os.path.exists(replit_nix_path):
            logging.info(f"تم العثور على ملف تكوين Replit: {replit_nix_path}")
            # في بيئة Replit، إيقاف المسار باستخدام kill -15
            try:
                result = subprocess.run(
                    ["ps", "aux"], 
                    stdout=subprocess.PIPE, 
                    text=True, 
                    check=True
                )
                
                for line in result.stdout.splitlines():
                    if "python bot.py" in line and "grep" not in line:
                        try:
                            pid = int(line.split()[1])
                            print(f"⚠️ إيقاف عملية البوت بـ PID: {pid}")
                            os.kill(pid, signal.SIGTERM)
                            logging.info(f"تم إيقاف مسار العمل {workflow_name} (PID: {pid})")
                            time.sleep(2)  # إعطاء وقت للعملية للإغلاق
                        except Exception as e:
                            logging.error(f"خطأ في إيقاف المسار: {e}")
            except Exception as e:
                logging.error(f"خطأ في البحث عن عمليات البوت: {e}")
        else:
            logging.warning(f"ملف التكوين Replit غير موجود: {replit_nix_path}")
    except Exception as e:
        logging.error(f"خطأ في إيقاف مسارات العمل: {e}")

def create_custom_workflow_script():
    """إنشاء سكريبت لبدء مسار العمل المخصص."""
    script_path = "start_custom_bot.sh"
    script_content = f"""#!/bin/bash
# سكريبت بدء البوت المعدل
# تم إنشاؤه تلقائيًا بواسطة custom_workflow_starter.py في {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

echo "🚀 بدء تشغيل البوت المعدل بالتوكن الجديد..."
echo "📝 التوكن الجديد: {NEW_TOKEN}"

# تعيين متغير البيئة للتوكن
export TELEGRAM_BOT_TOKEN="{NEW_TOKEN}"

# تنفيذ البوت المعدل
python custom_bot.py
"""
    
    try:
        with open(script_path, 'w', encoding='utf-8') as f:
            f.write(script_content)
        
        # جعل السكريبت قابل للتنفيذ
        os.chmod(script_path, 0o755)
        
        logging.info(f"تم إنشاء سكريبت بدء التشغيل: {script_path}")
        print(f"✅ تم إنشاء سكريبت بدء التشغيل: {script_path}")
        return True
    except Exception as e:
        logging.error(f"خطأ في إنشاء سكريبت بدء التشغيل: {e}")
        print(f"❌ خطأ في إنشاء سكريبت بدء التشغيل: {e}")
        return False

def update_replit_workflow():
    """تحديث مسار عمل Replit لاستخدام البوت المعدل."""
    replit_file = ".replit"
    
    try:
        if os.path.exists(replit_file):
            with open(replit_file, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # البحث عن تعريف مسار العمل وتحديثه
            if "name = \"telegram_bot\"" in content and "command = \"python bot.py\"" in content:
                updated_content = content.replace(
                    "command = \"python bot.py\"",
                    "command = \"python custom_bot.py\""
                )
                
                with open(replit_file, 'w', encoding='utf-8') as f:
                    f.write(updated_content)
                
                logging.info(f"تم تحديث ملف تكوين Replit: {replit_file}")
                print(f"✅ تم تحديث ملف تكوين Replit لاستخدام البوت المعدل")
                return True
            else:
                logging.warning("لم يتم العثور على تكوين مسار العمل الصحيح في ملف Replit")
                print("⚠️ لم يتم العثور على تكوين مسار العمل الصحيح في ملف Replit")
        else:
            logging.warning(f"ملف تكوين Replit غير موجود: {replit_file}")
            print(f"⚠️ ملف تكوين Replit غير موجود: {replit_file}")
    except Exception as e:
        logging.error(f"خطأ في تحديث ملف تكوين Replit: {e}")
        print(f"❌ خطأ في تحديث ملف تكوين Replit: {e}")
    
    return False

def update_config_token():
    """تحديث ملف التكوين config.py لاستخدام التوكن الجديد."""
    config_file = "config.py"
    
    try:
        if os.path.exists(config_file):
            with open(config_file, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # البحث عن متغير TOKEN وتحديثه
            if "TOKEN = os.environ.get('TELEGRAM_BOT_TOKEN'" in content:
                # إضافة متغير بديل مباشر
                updated_content = content.replace(
                    "TOKEN = os.environ.get('TELEGRAM_BOT_TOKEN'",
                    f"# التوكن الجديد المضمن مباشرة\nTOKEN = \"{NEW_TOKEN}\"  # التوكن الثابت المضمن\n# في حالة التعليق استخدم: TOKEN = os.environ.get('TELEGRAM_BOT_TOKEN'"
                )
                
                # حفظ نسخة احتياطية من الملف الأصلي
                backup_file = f"{config_file}.bak"
                with open(backup_file, 'w', encoding='utf-8') as f:
                    f.write(content)
                
                # كتابة الملف المحدث
                with open(config_file, 'w', encoding='utf-8') as f:
                    f.write(updated_content)
                
                logging.info(f"تم تحديث ملف التكوين: {config_file}, نسخة احتياطية: {backup_file}")
                print(f"✅ تم تحديث ملف التكوين {config_file} لاستخدام التوكن الجديد")
                print(f"📝 تم حفظ نسخة احتياطية في {backup_file}")
                return True
            else:
                logging.warning(f"لم يتم العثور على متغير TOKEN المطلوب في {config_file}")
                print(f"⚠️ لم يتم العثور على متغير TOKEN المطلوب في {config_file}")
        else:
            logging.warning(f"ملف التكوين غير موجود: {config_file}")
            print(f"⚠️ ملف التكوين غير موجود: {config_file}")
    except Exception as e:
        logging.error(f"خطأ في تحديث ملف التكوين: {e}")
        print(f"❌ خطأ في تحديث ملف التكوين: {e}")
    
    return False

def main():
    """الوظيفة الرئيسية للسكريبت."""
    print("🔧 إعداد مسار عمل مخصص للبوت المعدل")
    print("====================================")
    print(f"التوكن الجديد: {NEW_TOKEN}")
    print()
    
    # 1. إيقاف مسارات عمل التلغرام الحالية
    stop_existing_telegram_workflows()
    
    # 2. إنشاء سكريبت بدء التشغيل المخصص
    script_created = create_custom_workflow_script()
    
    # 3. تحديث ملف تكوين Replit
    replit_updated = update_replit_workflow()
    
    # 4. تحديث ملف التكوين config.py
    config_updated = update_config_token()
    
    # 5. طباعة ملخص وتعليمات للمستخدم
    print()
    print("✅ اكتمل إعداد مسار العمل المخصص!")
    print(f"- إنشاء سكريبت بدء التشغيل: {'✓' if script_created else '✗'}")
    print(f"- تحديث ملف تكوين Replit: {'✓' if replit_updated else '✗'}")
    print(f"- تحديث ملف التكوين config.py: {'✓' if config_updated else '✗'}")
    print()
    print("📋 الخطوات التالية:")
    print("1. قم بإعادة تشغيل مسار العمل telegram_bot من لوحة التحكم")
    print("   أو قم بتنفيذ: python custom_bot.py")
    print()
    print("2. تحديث التوكن في Replit Secrets:")
    print("   - انتقل إلى لوحة تحكم Replit")
    print("   - اختر علامة التبويب 'Secrets'")
    print("   - قم بتحديث قيمة TELEGRAM_BOT_TOKEN إلى:")
    print(f"     {NEW_TOKEN}")
    print()
    print("ملاحظة: تم تسجيل جميع الخطوات في ملف 'custom_workflow_setup.log'")

if __name__ == "__main__":
    main()