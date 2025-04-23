"""
تطبيق Flask لاستضافة بوت تيليجرام على منصة Render.
يعمل هذا التطبيق كواجهة API للبوت وتلقي التحديثات عبر webhook.
"""

import os
import logging
import threading
import asyncio
from datetime import datetime
import json
from flask import Flask, request, jsonify
import telegram
from telegram.ext import Application, CommandHandler, MessageHandler, filters, CallbackQueryHandler
import database as db
from bot import initialize_bot, start, help_command, handle_photos, handle_keyboard_buttons, admin_help
from admin_handlers import get_admin_handlers, handle_template_callback, handle_welcome_template_callback
from admin_handlers import handle_verification_template_callback, handle_admin_callback
from utils import is_admin

# إعداد التسجيل
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# إنشاء تطبيق Flask
app = Flask(__name__)

# متغير عام لتخزين تطبيق البوت
bot_app = None

# الحصول على توكن البوت من متغيرات البيئة
TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN")
if not TOKEN:
    logger.error("لم يتم العثور على توكن البوت في متغيرات البيئة")
    raise ValueError("يجب تعيين متغير البيئة TELEGRAM_BOT_TOKEN")

# إنشاء رابط webhook من متغيرات البيئة
WEBHOOK_URL = os.environ.get("WEBHOOK_URL")
if not WEBHOOK_URL:
    logger.warning("لم يتم تعيين عنوان webhook في متغيرات البيئة")

async def init_bot():
    """تهيئة البوت وإعداد المعالجات."""
    # إنشاء تطبيق البوت
    application = Application.builder().token(TOKEN).build()
    
    # تسجيل المعالجات الأساسية
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(CommandHandler("admin", admin_help))
    
    # إضافة معالجات المسؤول
    admin_handlers = get_admin_handlers()
    for handler in admin_handlers:
        application.add_handler(handler)

    # تسجيل معالج للصور
    application.add_handler(MessageHandler(filters.PHOTO, handle_photos))
    
    # تسجيل معالج لأزرار لوحة المفاتيح
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_keyboard_buttons))
    
    # تسجيل معالجات الاستدعاءات
    application.add_handler(CallbackQueryHandler(handle_admin_callback, pattern=r"^admin_page_\d+$"))
    application.add_handler(CallbackQueryHandler(handle_template_callback, pattern=r"^(view|edit)_template$"))
    application.add_handler(CallbackQueryHandler(handle_welcome_template_callback, pattern=r"^(view|edit)_welcome_template$"))
    application.add_handler(CallbackQueryHandler(handle_verification_template_callback, pattern=r"^(view|edit)_verification_template$"))
    
    # تهيئة البوت إضافية (ترحيل من initialize_bot في bot.py)
    initialize_bot()
    
    # ضبط webhook إذا كان متاحاً
    if WEBHOOK_URL:
        await application.bot.set_webhook(WEBHOOK_URL)
        logger.info(f"تم تعيين Webhook على: {WEBHOOK_URL}")
    
    return application

def run_async_init():
    """تشغيل تهيئة البوت بشكل غير متزامن."""
    global bot_app
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    bot_app = loop.run_until_complete(init_bot())
    logger.info("تم تهيئة تطبيق البوت بنجاح")

# تهيئة البوت عند بدء التطبيق
init_thread = threading.Thread(target=run_async_init)
init_thread.start()

# مسار التحقق من عمل التطبيق
@app.route('/')
def index():
    """صفحة الترحيب وحالة التطبيق."""
    return jsonify({
        'status': 'online',
        'name': 'Telegram Shipping Bot',
        'environment': os.environ.get('ENVIRONMENT', 'development'),
        'timestamp': datetime.now().isoformat()
    })

# مسار فحص الصحة للمراقبة الخارجية
@app.route('/health')
def health_check():
    """نقطة نهاية فحص الصحة للمراقبة الخارجية."""
    return "OK", 200

# مسار الويب هوك لاستقبال تحديثات التيليجرام
@app.route(f'/webhook', methods=['POST'])
def webhook():
    """استقبال تحديثات webhook من تيليجرام."""
    global bot_app
    
    if not bot_app:
        logger.error("تطبيق البوت غير مهيأ بعد")
        return jsonify({"status": "error", "message": "تطبيق البوت غير مهيأ بعد"}), 503
    
    if request.method == "POST":
        try:
            update = telegram.Update.de_json(request.get_json(force=True), bot_app.bot)
            
            # تسجيل معلومات التحديث للتشخيص
            logger.info(f"تم استلام تحديث: {update.update_id}")
            
            # معالجة التحديث
            asyncio.run(bot_app.process_update(update))
            return jsonify({"status": "success"}), 200
        except Exception as e:
            logger.error(f"خطأ أثناء معالجة التحديث: {e}")
            return jsonify({"status": "error", "message": str(e)}), 500
    else:
        return jsonify({"status": "error", "message": "طريقة غير مدعومة"}), 405

# نقطة نهاية للـ ping للحفاظ على نشاط التطبيق
@app.route('/api/ping')
def api_ping():
    """نقطة نهاية للـ ping للحفاظ على نشاط التطبيق."""
    return jsonify({
        "status": "ok",
        "message": "pong",
        "timestamp": datetime.now().isoformat()
    })

# عرض حالة النظام
@app.route('/api/status')
def api_status():
    """عرض حالة النظام بصيغة JSON."""
    
    # الحصول على إحصائيات من قاعدة البيانات
    try:
        notification_count = db.get_notification_count()
    except Exception:
        notification_count = -1
    
    status_data = {
        "status": "online",
        "service": "Telegram Shipping Bot",
        "version": "2.0.0",
        "timestamp": datetime.now().isoformat(),
        "notifications": notification_count,
        "environment": os.environ.get('ENVIRONMENT', 'development'),
        "webhook_url": WEBHOOK_URL or "Not set"
    }
    
    return jsonify(status_data)

if __name__ == "__main__":
    # عند تشغيل الملف مباشرة على البيئة المحلية
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)