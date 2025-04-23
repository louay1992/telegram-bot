#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
نظام الحفاظ على استمرارية تشغيل بوت تيليجرام مع Replit

هذا الملف يمثل نظام المراقبة الخارجي الذي يستخدم مع UptimeRobot لضمان 
استمرارية عمل البوت 24/7 على منصة Replit.

يقوم بتوفير نقاط نهاية HTTP بسيطة يمكن لخدمات المراقبة الخارجية الاتصال بها
للتأكد من أن البوت لا يزال قيد التشغيل، كما يوفر واجهة بسيطة لإعادة تشغيل
البوت في حالة حدوث أي مشكلة.
"""

import os
import time
import logging
import threading
from datetime import datetime
from flask import Flask, jsonify, render_template, redirect

# إعداد السجلات
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler("logs/keep_alive.log")
    ]
)
logger = logging.getLogger("keep_alive")

# إنشاء تطبيق Flask
app = Flask(__name__)

# ملف نبضات القلب للبوت
HEARTBEAT_FILE = "bot_heartbeat.txt"

def update_heartbeat():
    """تحديث ملف نبضات القلب"""
    try:
        with open(HEARTBEAT_FILE, "w") as f:
            f.write(str(time.time()))
    except Exception as e:
        logger.error(f"خطأ في تحديث ملف نبضات القلب: {e}")

def is_bot_running():
    """التحقق من حالة البوت"""
    try:
        if not os.path.exists(HEARTBEAT_FILE):
            return False, "ملف نبضات القلب غير موجود"
            
        with open(HEARTBEAT_FILE, "r") as f:
            timestamp = f.read().strip()
            
        try:
            last_heartbeat = datetime.fromtimestamp(float(timestamp))
            diff = (datetime.now() - last_heartbeat).total_seconds()
            
            # اعتبار البوت نشطًا إذا كان آخر نبضة قلب خلال 3 دقائق
            if diff < 180:
                return True, last_heartbeat.strftime("%Y-%m-%d %H:%M:%S")
            else:
                return False, f"آخر نبضة قلب: {last_heartbeat.strftime('%Y-%m-%d %H:%M:%S')} (منذ {int(diff/60)} دقيقة)"
                
        except (ValueError, TypeError) as e:
            logger.error(f"خطأ في تحليل الطابع الزمني: {e}")
            return False, "خطأ في تنسيق الطابع الزمني"
                
    except Exception as e:
        logger.error(f"خطأ عام في التحقق من حالة البوت: {e}")
        return False, str(e)

@app.route('/')
def home():
    """الصفحة الرئيسية"""
    bot_status, status_message = is_bot_running()
    
    # تحديث ملف نبضات القلب عند زيارة الصفحة
    update_heartbeat()
    
    return f"""
    <html dir="rtl">
    <head>
        <title>حالة البوت</title>
        <meta charset="utf-8">
        <meta http-equiv="refresh" content="30">
        <style>
            body {{ font-family: Arial, sans-serif; margin: 40px; line-height: 1.6; }}
            .container {{ max-width: 800px; margin: 0 auto; }}
            h1 {{ color: #4285f4; }}
            .status {{ padding: 10px; border-radius: 3px; margin: 20px 0; }}
            .running {{ background-color: #d4edda; color: #155724; }}
            .stopped {{ background-color: #f8d7da; color: #721c24; }}
        </style>
    </head>
    <body>
        <div class="container">
            <h1>حالة بوت تيليجرام</h1>
            <div class="status {'running' if bot_status else 'stopped'}">
                <strong>الحالة:</strong> {'يعمل' if bot_status else 'متوقف'}
            </div>
            <div>
                <strong>التفاصيل:</strong> {status_message}
            </div>
            <div>
                <strong>آخر تحديث:</strong> {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}
            </div>
            <div>
                <p>
                    <a href="/ping">فحص الاتصال</a> | 
                    <a href="/health">فحص الصحة</a> | 
                    <a href="/restart">إعادة تشغيل البوت</a>
                </p>
            </div>
        </div>
    </body>
    </html>
    """

@app.route('/ping')
def ping():
    """نقطة نهاية بسيطة لخدمات المراقبة مثل UptimeRobot"""
    # هذه النقطة تستجيب دائمًا بـ "pong" حتى لو كان البوت متوقفًا
    # لأن هدفها هو الحفاظ على خادم Replit نشطًا
    return "pong"

@app.route('/health')
def health():
    """نقطة نهاية للتحقق من صحة البوت"""
    bot_running, status_message = is_bot_running()
    return jsonify({
        'status': 'ok' if bot_running else 'error',
        'running': bot_running,
        'message': status_message,
        'timestamp': datetime.now().isoformat()
    }), 200 if bot_running else 503

@app.route('/restart')
def restart():
    """إعادة تشغيل البوت"""
    try:
        import custom_bot_adapter
        
        # إيقاف البوت الحالي
        custom_bot_adapter.stop_bot_thread()
        
        # انتظار لحظة
        time.sleep(1)
        
        # إعادة تشغيل البوت
        success = custom_bot_adapter.start_bot_thread()
        
        if success:
            return redirect('/?restart=success')
        else:
            return "فشل في إعادة تشغيل البوت", 500
    except Exception as e:
        logger.error(f"خطأ في إعادة تشغيل البوت: {e}")
        return str(e), 500

def run_keep_alive():
    """تشغيل خادم Flask"""
    app.run(host='0.0.0.0', port=5000)

if __name__ == '__main__':
    # تشغيل خادم Flask
    run_keep_alive()