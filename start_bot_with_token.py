#!/usr/bin/env python3
# سكريبت مساعد لضبط توكن التلغرام الصحيح في بداية التشغيل
import os
import sys

# التوكن الجديد
NEW_TOKEN = "7406580104:AAGG2JQeeNfsmcGVMCm7hxitIK-qm2yekVg"

def main():
    # تعيين متغير البيئة
    os.environ["TELEGRAM_BOT_TOKEN"] = NEW_TOKEN
    print(f"✅ تم تعيين TELEGRAM_BOT_TOKEN إلى التوكن الجديد")
    
    # تشغيل bot.py
    if len(sys.argv) > 1:
        args = sys.argv[1:]
        os.execvp("python", ["python"] + args)
    else:
        os.execvp("python", ["python", "bot.py"])

if __name__ == "__main__":
    main()
