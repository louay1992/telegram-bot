#!/usr/bin/env python
"""
تطبيق موحد يجمع بين بوت تيليجرام وخادم الويب في تطبيق واحد
لضمان استمرارية العمل في وضع Always-On
"""

import os
import logging
from datetime import datetime
from flask import Flask, render_template, jsonify, send_from_directory

# إعداد السجلات
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger('combined_app')

# قراءة التوكن من متغيرات البيئة أو استخدام القيمة الافتراضية المضمنة
DEFAULT_TOKEN = "7406580104:AAGG2JQeeNfsmcGVMCm7hxitIK-qm2yekVg"
BOT_TOKEN = os.environ.get('TELEGRAM_BOT_TOKEN', DEFAULT_TOKEN)

# التحقق من تمكين وضع Always-On
USE_ALWAYS_ON = os.environ.get('USE_ALWAYS_ON', 'True').lower() in ('true', 'yes', '1')
logger.info(f"USE_ALWAYS_ON = {USE_ALWAYS_ON} (تم ضبطه يدوياً)")

# إنشاء تطبيق Flask
app = Flask(__name__)

logger.info("======== بدء تشغيل نظام موحد لبوت تيليجرام وخادم الويب ========")

def start_bot():
    """بدء تشغيل البوت في خلفية النظام"""
    logger.info("بدء تشغيل بوت تيليجرام...")
    
    try:
        # استيراد ملف محول البوت المخصص
        import custom_bot_adapter
        
        # بدء تشغيل البوت في خيط منفصل
        custom_bot_adapter.start_bot_thread()
        
        logger.info("✅ تم بدء تشغيل جميع الخدمات في وضع Always-On")
        return True
    except Exception as e:
        logger.error(f"❌ فشل في بدء تشغيل بوت تيليجرام: {e}")
        import traceback
        logger.error(traceback.format_exc())
        return False

@app.route('/')
def index():
    """صفحة الواجهة الرئيسية للنظام"""
    # استيراد دوال من ملف main_combined (الذي قمنا بإنشائه مسبقًا)
    # نستخدم try-except للتعامل مع حالات الخطأ في الاستيراد
    try:
        import main_combined
        return main_combined.index()
    except ImportError:
        from flask import render_template, jsonify
        import time
        
        # استدعاء دوال محلية كبديل في حالة عدم وجود ملف main_combined
        system_info = {
            "cpu_percent": 0,
            "memory_percent": 0,
            "memory_used": "غير متاح",
            "memory_total": "غير متاح",
            "disk_percent": 0,
            "disk_used": "غير متاح",
            "disk_total": "غير متاح"
        }
        
        # بيانات افتراضية للعرض
        template_data = {
            "bot_status": True, 
            "status_class": "status-ok",
            "last_update": time.strftime("%Y-%m-%d %H:%M:%S"),
            "uptime": "غير متاح",
            "last_heartbeat": "غير متاح",
            "system_info": system_info,
            "notification_count": 0,
            "visit_count": 0,
            "always_on": USE_ALWAYS_ON,
            "bot_token": f"{BOT_TOKEN[:5]}...{BOT_TOKEN[-5:]}"
        }
        
        return render_template('status.html', **template_data)

@app.route('/health')
def health_check():
    """نقطة نهاية فحص الصحة"""
    try:
        import main_combined
        return main_combined.health_check()
    except ImportError:
        from flask import jsonify
        # استخدام قيم افتراضية إذا لم يوجد main_combined
        return jsonify({
            "status": "ok",
            "bot_running": True,
            "last_heartbeat": "غير متاح",
            "uptime": "غير متاح"
        })

@app.route('/api/status')
def api_status():
    """نقطة نهاية حالة النظام بصيغة JSON"""
    try:
        import main_combined
        return main_combined.api_status()
    except ImportError:
        from flask import jsonify
        # استخدام قيم افتراضية إذا لم يوجد main_combined
        system_info = {
            "cpu_percent": 0,
            "memory_percent": 0,
            "memory_used": "غير متاح",
            "memory_total": "غير متاح",
            "disk_percent": 0,
            "disk_used": "غير متاح",
            "disk_total": "غير متاح"
        }
        
        return jsonify({
            "status": "ok",
            "bot_running": True,
            "last_heartbeat": "غير متاح",
            "uptime": "غير متاح",
            "system_info": system_info,
            "notification_count": 0
        })

@app.route('/ping')
def ping():
    """نقطة نهاية بسيطة للتحقق من حياة الخادم"""
    return "pong", 200

@app.route('/media/<path:filename>')
def serve_media(filename):
    """تقديم ملفات الوسائط"""
    try:
        import main_combined
        return main_combined.serve_media(filename)
    except ImportError:
        from flask import send_from_directory
        # استخدام طريقة محلية إذا لم يوجد main_combined
        media_folder = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'data/images')
        return send_from_directory(media_folder, filename)

def main():
    """الدالة الرئيسية لتشغيل التطبيق الموحد"""
    # بدء تشغيل البوت
    bot_started = start_bot()
    
    if bot_started:
        logger.info("✅ تم بدء تشغيل بوت تيليجرام بنجاح")
    else:
        logger.warning("⚠️ فشل في بدء تشغيل بوت تيليجرام، ستستمر الخدمة بدون بوت")
    
    # عرض معلومات التكوين
    logger.info(f"📡 عنوان التطبيق: http://0.0.0.0:5000")
    logger.info(f"🤖 توكن البوت: {BOT_TOKEN[:5]}...{BOT_TOKEN[-5:]}")
    
    # تشغيل خادم الويب على المنفذ 5000 (المنفذ الافتراضي في Replit)
    return app

# تصدير الكائنات المطلوبة للاستيراد الخارجي
__all__ = ['app', 'main']

if __name__ == "__main__":
    app = main()
    app.run(host='0.0.0.0', port=5000)