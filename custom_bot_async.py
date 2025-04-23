#!/usr/bin/env python
"""
نسخة خاصة من custom_bot.py للعمل بشكل متكامل مع نظام بدء التشغيل الآمن في Always-On
تم تعديلها لدعم التشغيل الآمن في خيط منفصل مع نظام تزامن متطور
"""

import logging
import os
import asyncio
import time
import psutil
import threading
from datetime import datetime, timedelta
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, ReplyKeyboardMarkup, KeyboardButton
from telegram.ext import (
    Application, CommandHandler, MessageHandler, CallbackQueryHandler,
    ContextTypes, filters
)
from telegram import error as telegram_error

import config
import strings as st
import database as db
import ultramsg_service as sms_service

from admin_handlers import get_admin_handlers, add_notification, list_notifications, admin_help, manage_admins
from admin_handlers import message_template_command, welcome_template_command
from admin_handlers import received_name, received_phone, received_image, NAME, PHONE, IMAGE, REMINDER_HOURS, received_reminder_hours
from search_handlers import get_search_handlers, AWAITING_SEARCH_QUERY, received_search_query
from stats_handlers import get_stats_handlers
from delivery_handlers import get_delivery_handlers
from search_history_handlers import get_search_history_handler
from filter_handlers import get_filter_handlers
from advanced_search_handlers import get_advanced_search_handler
from permissions_handlers import get_permissions_handlers
from theme_handlers import get_theme_handlers
from backup_handlers import get_backup_handlers

# ====== المتغيرات العامة ======
# استخدام متغيرات عامة لتتبع الحالة
_application = None
_shutdown_requested = False
_is_running = False

# استدعاء الوظائف المشتركة من custom_bot.py
from custom_bot import (
    create_admin_keyboard,
    create_user_keyboard,
    update_heartbeat_file,
    heartbeat_updater,
    telegram_self_ping,
    cleanup_marker_files,
    start,
    help_command,
    main_menu_command,
    cancel_command,
    handle_keyboard_buttons
)

async def main_async_compatible():
    """نسخة معدلة من وظيفة main للتوافق مع التشغيل في خيط منفصل مع Always-On"""
    global _application, _shutdown_requested, _is_running
    
    try:
        # تبديل حالة التشغيل
        _is_running = True
        _shutdown_requested = False
        
        # إعداد السجلات بشكل صحيح
        logging.info("🚀 بدء تشغيل النسخة المعدلة من بوت تيليجرام للعمل مع Always-On...")
        
        # تنظيف ملفات العلامات القديمة
        cleanup_marker_files()
        
        # إنشاء المجلدات المطلوبة
        os.makedirs("data", exist_ok=True)
        os.makedirs("data/images", exist_ok=True)
        
        # تحديث ملف نبضات القلب عند البدء
        update_heartbeat_file()
        
        # إنشاء التطبيق وتمرير توكن البوت
        NEW_TOKEN = "7406580104:AAGG2JQeeNfsmcGVMCm7hxitIK-qm2yekVg"
        _application = Application.builder().token(NEW_TOKEN).build()
        
        # استدعاء وظائف المعالجات من ملف custom_bot.py
        from permissions_handlers import handle_permissions_callback, handle_global_permissions_callback
        from theme_handlers import handle_theme_callback, handle_global_theme_callback
        from custom_bot import handle_global_permissions_callback_wrapper
        
        # إضافة معالجات الأوامر
        _application.add_handler(CommandHandler("start", start))
        _application.add_handler(CommandHandler("help", help_command))
        _application.add_handler(CommandHandler("menu", main_menu_command))
        _application.add_handler(CommandHandler("cancel", cancel_command))
        
        # إضافة معالجات المحادثة
        # إضافة معالج إضافة الإشعارات
        _application.add_handler(get_admin_handlers())
        
        # إضافة معالج البحث
        _application.add_handler(get_search_handlers())
        
        # إضافة معالج الإحصائيات
        _application.add_handler(get_stats_handlers())
        
        # إضافة معالج تأكيدات التسليم
        _application.add_handler(get_delivery_handlers())
        
        # إضافة معالج سجل البحث
        _application.add_handler(get_search_history_handler())
        
        # إضافة معالج التصفية
        _application.add_handler(get_filter_handlers())
        
        # إضافة معالج البحث المتقدم
        _application.add_handler(get_advanced_search_handler())
        
        # إضافة معالج إدارة الصلاحيات
        _application.add_handler(get_permissions_handlers())
        
        # إضافة معالج إدارة السمة
        _application.add_handler(get_theme_handlers())
        
        # إضافة معالج إدارة النسخ الاحتياطي
        _application.add_handler(get_backup_handlers())
        
        # إضافة معالج استدعاءات الأزرار العامة
        _application.add_handler(CallbackQueryHandler(handle_global_permissions_callback_wrapper))
        
        # معالج الرسائل النصية (للأزرار)
        _application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_keyboard_buttons))
        
        # معالج الصور (للإشعارات)
        _application.add_handler(MessageHandler(filters.PHOTO, received_image))
        
        # تشغيل مجدول المهام
        job_queue = _application.job_queue
        if job_queue:
            # تقليل فترة نبضات القلب إلى 15 ثانية
            job_queue.run_repeating(heartbeat_updater, interval=15, first=5)
            logging.info("تم جدولة تحديث نبضات القلب كل 15 ثانية")
            
            # تقليل فترة نبضات تيليجرام إلى 10 ثوانٍ للحفاظ على نشاط البوت
            job_queue.run_repeating(telegram_self_ping, interval=10, first=5)
            logging.info("تم جدولة نبضات تيليجرام كل 10 ثوانٍ للحفاظ على نشاط البوت")
            
            # بدء نظام مراقبة البوت مع إشعارات الواتساب
            try:
                import bot_status_monitor
                # تشغيل خيط نظام المراقبة مع فحص كل 3 دقائق
                monitor_thread = bot_status_monitor.start_status_monitor(check_interval=180)
                logging.info("تم بدء نظام مراقبة حالة البوت مع إشعارات واتساب عند التوقف")
            except ImportError:
                logging.warning("لم يتم العثور على وحدة نظام مراقبة البوت")
            except Exception as e:
                logging.error(f"حدث خطأ أثناء تشغيل نظام مراقبة البوت: {e}")
        else:
            logging.warning("JobQueue غير متوفرة - لن يعمل نظام نبضات القلب تلقائيًا")
        
        # تشغيل البوت بوضع طويل الأمد
        logging.info("بدء تشغيل البوت بوضع Always-On...")
        
        # ضبط معالج إشارات للإيقاف الآمن
        async def stop_signal_handler():
            global _shutdown_requested
            logging.info("🛑 تم استلام طلب إيقاف البوت")
            _shutdown_requested = True
            await _application.stop()
            
        # نبدأ التشغيل مع فحص دوري لحالة المتغير shutdown_requested
        update_heartbeat_file()  # تحديث ملف نبضات القلب قبل البدء
        await _application.initialize()
        await _application.start()
        await _application.updater.start_polling()
        
        try:
            # حلقة مستمرة تفحص حالة المتغير shutdown_requested
            while not _shutdown_requested:
                await asyncio.sleep(1)
                
            logging.info("🛑 تم استلام طلب إيقاف البوت من الحلقة الرئيسية")
        finally:
            # الإغلاق الآمن عند الخروج
            logging.info("🛑 إيقاف التطبيق بشكل آمن...")
            await _application.updater.stop()
            await _application.stop()
            await _application.shutdown()
            
            _is_running = False  # تعيين حالة التشغيل إلى متوقف
            logging.info("✅ تم إيقاف البوت بنجاح")
            
    except Exception as e:
        import traceback
        logging.error(f"❌ حدث خطأ أثناء تشغيل البوت: {e}")
        logging.error(traceback.format_exc())
        _is_running = False
        raise

async def stop_bot():
    """إيقاف البوت بشكل آمن"""
    global _shutdown_requested, _application
    
    if not _is_running or _application is None:
        logging.info("البوت غير نشط بالفعل أو لم يتم تهيئته")
        return
    
    try:
        logging.info("🛑 إرسال طلب إيقاف البوت...")
        _shutdown_requested = True
        
        # انتظار حتى يتوقف البوت
        max_wait = 10  # ثواني للانتظار
        while _is_running and max_wait > 0:
            await asyncio.sleep(1)
            max_wait -= 1
            
        if not _is_running:
            logging.info("✅ تم إيقاف البوت بنجاح")
        else:
            logging.warning("⚠️ انتهت مهلة الانتظار، ربما لم يتوقف البوت بشكل صحيح")
    except Exception as e:
        logging.error(f"❌ حدث خطأ أثناء إيقاف البوت: {e}")

def is_bot_running():
    """التحقق مما إذا كان البوت نشطاً"""
    global _is_running
    return _is_running