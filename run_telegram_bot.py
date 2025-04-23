#!/usr/bin/env python3
"""
سكريبت لتشغيل بوت التيليجرام
هذا الملف يتم استدعاؤه من قبل Replit Workflow
"""
import os
import subprocess
import sys

def main():
    """
    الدالة الرئيسية لتشغيل البوت
    """
    # الحصول على المسار الحالي
    current_dir = os.path.dirname(os.path.abspath(__file__))
    
    # تشغيل سكريبت البوت
    script_path = os.path.join(current_dir, "start_telegram_bot.sh")
    
    try:
        # التأكد من أن السكريبت قابل للتنفيذ
        os.chmod(script_path, 0o755)
        
        # تشغيل السكريبت
        result = subprocess.run([script_path], 
                                stdout=subprocess.PIPE, 
                                stderr=subprocess.PIPE,
                                text=True,
                                check=True)
        
        print(result.stdout)
        if result.stderr:
            print(f"Error: {result.stderr}", file=sys.stderr)
            
    except subprocess.CalledProcessError as e:
        print(f"Error running start_telegram_bot.sh: {e}", file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        print(f"Unexpected error: {e}", file=sys.stderr)
        sys.exit(1)

if __name__ == "__main__":
    main()