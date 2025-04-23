#!/usr/bin/env python
import logging
import os
import asyncio
import time
import psutil
import threading
import sys
from datetime import datetime, timedelta
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, ReplyKeyboardMarkup, KeyboardButton
from telegram.ext import (
    Application, CommandHandler, MessageHandler, CallbackQueryHandler,
    ContextTypes, filters
)
from telegram import error as telegram_error

# استيراد نظام قفل المثيل
from instance_lock import check_single_instance

import config
import strings as st
import database as db
import ultramsg_service as sms_service  # استخدام خدمة UltraMsg للواتساب
from admin_handlers import get_admin_handlers, add_notification, list_notifications, admin_help, manage_admins, message_template_command, welcome_template_command
from admin_handlers import received_name, received_phone, received_image, NAME, PHONE, IMAGE, REMINDER_HOURS, received_reminder_hours
from search_handlers import get_search_handlers, AWAITING_SEARCH_QUERY, received_search_query
from stats_handlers import get_stats_handlers
from delivery_handlers import get_delivery_handlers
from search_history_handlers import get_search_history_handler
from filter_handlers import get_filter_handler
from advanced_search_handlers import get_advanced_search_handler
from permissions_handlers import get_permissions_handlers
from theme_handlers import get_theme_handlers
from backup_handlers import get_backup_handlers
from personality_handlers import get_personality_handlers
from ai_handlers import get_ai_handlers  # إضافة معالجات الذكاء الاصطناعي

# Function to create admin keyboard
def create_admin_keyboard():
    """Create a keyboard with admin commands."""
    keyboard = [
        [KeyboardButton("➕ إضافة إشعار"), KeyboardButton("📋 قائمة الإشعارات")],
        [KeyboardButton("🔍 تصفية الإشعارات"), KeyboardButton("🔍 البحث المتقدم")],
        [KeyboardButton("📋 قائمة الشحنات المستلمة"), KeyboardButton("📊 الإحصائيات")],
        [KeyboardButton("👥 إدارة المسؤولين"), KeyboardButton("🛡️ إدارة الصلاحيات")],
        [KeyboardButton("✏️ قالب الرسالة"), KeyboardButton("✏️ قالب الترحيب")],
        [KeyboardButton("🎨 إعدادات السمة"), KeyboardButton("🤖 شخصية البوت")],
        [KeyboardButton("🚀 الحملات التسويقية"), KeyboardButton("💾 النسخ الاحتياطي")],
        [KeyboardButton("🧠 المساعد الذكي"), KeyboardButton("❓ مساعدة المسؤول")],
        [KeyboardButton(st.MAIN_MENU_BUTTON)]
    ]
    return ReplyKeyboardMarkup(keyboard, resize_keyboard=True)

# Function to create user keyboard
def create_user_keyboard():
    """Create a keyboard with user commands."""
    keyboard = [
        [KeyboardButton("🔍 بحث باسم العميل"), KeyboardButton("📱 بحث برقم الهاتف")],
        [KeyboardButton("📋 سجلات البحث السابقة"), KeyboardButton("✅ تأكيد استلام زبون")],
        [KeyboardButton("📋 قائمة الشحنات المستلمة"), KeyboardButton("🧠 المساعد الذكي")],
        [KeyboardButton("❓ المساعدة"), KeyboardButton(st.MAIN_MENU_BUTTON)]
    ]
    return ReplyKeyboardMarkup(keyboard, resize_keyboard=True)

# Enable logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)

logger = logging.getLogger(__name__)

# إعدادات نظام نبضات القلب (heartbeat)
HEARTBEAT_FILE = "bot_heartbeat.txt"
HEARTBEAT_INTERVAL = 30  # تحديث ملف نبضات القلب كل 30 ثانية

def update_heartbeat_file():
    """تحديث ملف نبضات القلب بالوقت الحالي"""
    try:
        with open(HEARTBEAT_FILE, 'w') as f:
            f.write(str(datetime.now().timestamp()))
        return True
    except Exception as e:
        logger.error(f"فشل في تحديث ملف نبضات القلب: {e}")
        return False

async def heartbeat_updater(context: ContextTypes.DEFAULT_TYPE):
    """وظيفة تعمل في الخلفية لتحديث ملف نبضات القلب بشكل دوري ومراقبة استخدام الموارد"""
    try:
        # تحديث ملف نبضات القلب
        success = update_heartbeat_file()
        if success:
            logger.debug("تم تحديث ملف نبضات القلب")
        else:
            logger.warning("فشل في تحديث ملف نبضات القلب")
            
        # مراقبة استخدام الذاكرة
        try:
            process = psutil.Process(os.getpid())
            memory_info = process.memory_info()
            memory_usage_mb = memory_info.rss / 1024 / 1024  # تحويل إلى ميجابايت
            
            # إذا تجاوز استخدام الذاكرة 250 ميجابايت، قم بإعادة التشغيل
            if memory_usage_mb > 250:
                logger.warning(f"⚠️ تم تجاوز حد استخدام الذاكرة: {memory_usage_mb:.2f} ميجابايت. جاري التحضير لإعادة التشغيل...")
                
                # إنشاء علامة لإعادة التشغيل الإجباري
                with open("force_restart", "w") as f:
                    f.write(f"تجاوز حد الذاكرة: {memory_usage_mb:.2f} ميجابايت في {datetime.now().isoformat()}")
                    
                # إرسال إشعار واتساب
                try:
                    from bot_status_monitor import send_bot_status_notification
                    send_bot_status_notification(is_down=True)
                    logger.info("تم إرسال إشعار واتساب عن تجاوز حد الذاكرة")
                except Exception as notification_error:
                    logger.error(f"فشل إرسال إشعار واتساب: {notification_error}")
            else:
                logger.debug(f"استخدام الذاكرة الحالي: {memory_usage_mb:.2f} ميجابايت (الحد: 250 ميجابايت)")
        except Exception as memory_error:
            logger.error(f"خطأ في مراقبة الذاكرة: {memory_error}")
            
    except Exception as e:
        # استمر في التشغيل حتى في حالة حدوث خطأ
        logger.error(f"حدث خطأ في تحديث نبضات القلب: {e}")
        
    # تمت معالجة الخطأ وسيتم جدولة المهمة مرة أخرى تلقائيًا من قبل job_queue

async def restart_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """أمر لإعادة تشغيل البوت - متاح للمسؤولين فقط"""
    user_id = update.effective_user.id
    
    # التحقق من أن المستخدم مسؤول
    if not db.is_admin(user_id):
        await update.message.reply_text(st.NOT_ADMIN)
        return
    
    try:
        # إرسال رسالة بدء إعادة التشغيل
        await update.message.reply_text(st.RESTART_INITIATED)
        
        # تسجيل بدء عملية إعادة التشغيل
        logging.info(f"🔄 Restarting bot triggered by admin user {user_id}")
        
        # استخدام subprocess للحصول على معرف العملية الحالية (PID)
        import os
        import signal
        import sys
        import asyncio
        import threading
        
        # تأخير قصير لضمان وصول رسالة بدء إعادة التشغيل
        await asyncio.sleep(2)
        
        # تسجيل خروج آمن من التطبيق
        logging.info("🔄 Stopping the application gracefully...")
        
        # استخدم أسلوب إيقاف أكثر أماناً
        # نحفظ معرف المستخدم ليكون متاحاً لدالة callback
        admin_user_id = user_id
        
        def stop_and_exit():
            """وظيفة تنفذ في خيط منفصل لإيقاف البوت وإنهاء العملية"""
            # أعط البوت وقتاً لإكمال الإرسال الحالي
            time.sleep(2)
            
            try:
                # إنشاء آلية متعددة العلامات للتواصل مع نظام المراقبة
                try:
                    # الخطوة 1: إنشاء ملف ping سريع أولاً لتنبيه المراقب
                    with open("watchdog_ping", "w") as f:
                        f.write(str(time.time()))
                        f.flush()
                        os.fsync(f.fileno())
                    logging.info("🔄 Created watchdog_ping file to alert watchdog")
                    
                    # الخطوة 2: إنشاء علامة الإيقاف الرئيسية
                    with open("bot_shutdown_marker", "w") as f:
                        f.write(str(time.time()))
                        f.flush()
                        os.fsync(f.fileno())  # تأكد من كتابة البيانات مباشرة للقرص
                    
                    # تأكد من أن الملفات تم إنشاؤها بنجاح
                    if os.path.exists("bot_shutdown_marker"):
                        logging.info("🔄 Created shutdown marker file successfully")
                        
                        # الخطوة 3: كتابة رسالة تأكيد إلى سجل النظام
                        with open("restart_requested.log", "w") as f:
                            now = datetime.now()
                            # الحصول على PID الحالي
                            current_pid = os.getpid()
                            f.write(f"Restart requested at {now.isoformat()}\n")
                            f.write(f"PID: {current_pid}\n")
                            f.write(f"User ID: {admin_user_id}\n")
                            f.flush()
                            os.fsync(f.fileno())
                        logging.info("🔄 Created restart confirmation log file")
                        
                        # الخطوة 4: الإنتظار لثانية أو ثانيتين للتأكد من إكتشاف العلامات
                        time.sleep(1)
                    else:
                        logging.error("🔄 Failed to verify shutdown marker creation")
                except Exception as marker_error:
                    logging.error(f"🔄 Error creating shutdown markers: {marker_error}")
                
                # محاولة إيقاف المجدول بشكل آمن مع التحقق إذا كان يعمل
                # نفحص أولاً إذا كان المجدول يعمل قبل محاولة إيقافه
                try:
                    scheduler_running = hasattr(context.application.job_queue, 'scheduler') and hasattr(context.application.job_queue.scheduler, 'running') and context.application.job_queue.scheduler.running
                    if scheduler_running:
                        logging.info("🔄 Shutting down scheduler safely...")
                        context.application.job_queue.scheduler.shutdown(wait=False)
                    else:
                        logging.info("🔄 Scheduler already stopped or not running")
                except Exception as scheduler_error:
                    logging.warning(f"🔄 Error checking scheduler status: {scheduler_error}")
                
                # الحصول على PID الحالي
                pid = os.getpid()
                logging.info(f"🔄 Process will exit with PID: {pid}")
                
                # استخدم SIGTERM للإيقاف الآمن بعد فترة قصيرة
                time.sleep(1)
                logging.info("🔄 Sending SIGTERM signal...")
                os.kill(pid, signal.SIGTERM)
                
            except Exception as e:
                logging.error(f"🔄 Error during shutdown procedure: {e}")
                # في حالة فشل الإغلاق الآمن، استخدم os._exit بدلاً من sys.exit
                # os._exit هو أكثر موثوقية في إنهاء العملية بشكل فوري
                logging.error("🔄 Forcing exit via os._exit...")
                os._exit(0)
        
        # بدء خيط منفصل للإيقاف
        threading.Thread(target=stop_and_exit).start()
        
        # تسجيل أن الأمر تم تنفيذه
        logging.info("🔄 Restart command initiated successfully")
        
    except Exception as e:
        # في حالة حدوث خطأ، نرسل رسالة خطأ للمستخدم
        import traceback
        logging.error(f"⚠️ Error during restart: {e}")
        logging.error(traceback.format_exc())
        await update.message.reply_text(st.RESTART_ERROR)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Send a welcome message when the command /start is issued."""
    # Check if admin system is completely empty (main_admin is None)
    # Only the first user after reset will be set as admin
    admin_data = db.load_json(db.ADMINS_DB, {"admins": [], "main_admin": None})
    if admin_data["main_admin"] is None:
        # This is the first user after admin reset
        logging.info(f"First user after admin reset detected: {update.effective_user.id}")
        if db.set_main_admin_if_none(update.effective_user.id):
            # Create admin keyboard for the main admin
            admin_keyboard = create_admin_keyboard()
            await update.message.reply_text(
                "🌟 تم إعدادك كمسؤول رئيسي للبوت! 🎉\n" + 
                st.ADMIN_WELCOME + "\n\n" + 
                "يمكنك الآن إضافة مسؤولين آخرين.\n\n" + 
                st.WELCOME_MESSAGE,
                reply_markup=admin_keyboard
            )
            return
    
    if db.is_admin(update.effective_user.id):
        # Create admin keyboard for admins
        admin_keyboard = create_admin_keyboard()
        
        # Add special message for main admin
        main_admin_text = ""
        if db.is_main_admin(update.effective_user.id):
            main_admin_text = "\n\n🌟 أنت المسؤول الرئيسي للبوت."
        
        await update.message.reply_text(
            st.ADMIN_WELCOME + main_admin_text + "\n\n" + st.WELCOME_MESSAGE,
            reply_markup=admin_keyboard
        )
    else:
        # Create user keyboard for regular users
        user_keyboard = create_user_keyboard()
        await update.message.reply_text(
            st.WELCOME_MESSAGE,
            reply_markup=user_keyboard
        )

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Send a help message when the command /help is issued."""
    # Check if user is admin to show appropriate keyboard
    if db.is_admin(update.effective_user.id):
        await update.message.reply_text(
            st.HELP_MESSAGE,
            reply_markup=create_admin_keyboard()
        )
    else:
        await update.message.reply_text(
            st.HELP_MESSAGE,
            reply_markup=create_user_keyboard()
        )

async def main_menu_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """عرض القائمة الرئيسية للمستخدم."""
    # مسح بيانات المحادثة الحالية
    context.user_data.clear()
    logging.info("User data cleared for user %s when returning to main menu", update.effective_user.id)
    
    # التحقق مما إذا كان المستخدم مسؤولاً لعرض لوحة المفاتيح المناسبة
    if db.is_admin(update.effective_user.id):
        main_admin_text = ""
        if db.is_main_admin(update.effective_user.id):
            main_admin_text = "\n\n🌟 أنت المسؤول الرئيسي للبوت."
            
        await update.message.reply_text(
            st.BACK_TO_MENU + main_admin_text,
            reply_markup=create_admin_keyboard()
        )
    else:
        await update.message.reply_text(
            st.BACK_TO_MENU,
            reply_markup=create_user_keyboard()
        )

async def cancel_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Cancel any ongoing conversation."""
    # Clear user data
    context.user_data.clear()
    
    # Send confirmation message
    await update.message.reply_text("✅ تم إلغاء العملية الحالية.")
    
    # Show the appropriate keyboard
    if db.is_admin(update.effective_user.id):
        await update.message.reply_text(
            "اختر أحد الخيارات:", 
            reply_markup=create_admin_keyboard()
        )
    else:
        await update.message.reply_text(
            "اختر أحد الخيارات:", 
            reply_markup=create_user_keyboard()
        )

async def handle_keyboard_buttons(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle text messages from keyboard buttons."""
    text = update.message.text
    user_id = update.effective_user.id
    is_admin = db.is_admin(user_id)
    
    # Log the button text for debugging
    logging.info(f"Button pressed: '{text}'")
    
    # التحقق إذا كان المستخدم في سياق محادثة ذكية
    if hasattr(context, 'bot_data') and 'user_context' in context.bot_data:
        user_context = context.bot_data['user_context'].get(user_id)
        if user_context == "smart_chat":
            logging.info(f"User {user_id} is in smart chat context, forwarding to AI handler")
            from ai_handlers import handle_chat_message
            # توجيه الرسالة إلى معالج المحادثة الذكية
            return await handle_chat_message(update, context)
    
    # تحقق من حالة المحادثة في ConversationHandler
    try:
        # التحقق من محادثة السمة - هل المستخدم في انتظار اسم الشركة؟
        # استخدم طرق بديلة للتحقق من حالة المحادثة النشطة
        from theme_handlers import AWAITING_COMPANY_NAME, process_company_name
        
        # التحقق فيما إذا كان المستخدم في محادثة نشطة تنتظر اسم الشركة
        chat_id = update.effective_chat.id
        user_id = update.effective_user.id
        
        # استخدام نهج أكثر أماناً للتحقق من المحادثات النشطة
        # نتحقق مما إذا كان نص الرسالة الأخيرة يتعلق بـ "اسم الشركة"
        last_message = getattr(context, 'last_bot_message', '')
        if last_message and ('اسم الشركة' in last_message or 'شعار الشركة' in last_message):
            logging.info(f"Last message suggests an active theme conversation")
            # سيتم معالجة هذه الحالة في معالجات الرسائل المناسبة
            # لا نقوم بتوجيه الرسالة هنا، بل نسمح للمعالج المناسب بالاستجابة
    except Exception as e:
        logging.error(f"Error checking conversation state for text message: {e}")
        import traceback
        logging.error(traceback.format_exc())
    
    # Handle exact matches for buttons
    if text == "➕ إضافة إشعار":
        logging.info("Add notification button pressed")
        if is_admin:
            return await add_notification(update, context)
        else:
            await update.message.reply_text(st.NOT_AUTHORIZED)
            
    # Handle mode selection for add notification (removed smart mode)
    
    elif text == "📋 قائمة الإشعارات":
        logging.info("List notifications button pressed")
        if is_admin:
            return await list_notifications(update, context)
        else:
            await update.message.reply_text(st.NOT_AUTHORIZED)
    
    elif text == "🔍 تصفية الإشعارات":
        logging.info("Filter notifications button pressed")
        if is_admin:
            from filter_handlers import filter_command
            return await filter_command(update, context)
        else:
            await update.message.reply_text(st.NOT_AUTHORIZED)
    
    elif text == "📅 تصفية حسب التاريخ":
        logging.info("Filter by date button pressed")
        if is_admin:
            from filter_handlers import handle_date_filter_button
            return await handle_date_filter_button(update, context)
        else:
            await update.message.reply_text(st.NOT_AUTHORIZED)
            
    elif text == "📊 تصفية حسب الحالة":
        logging.info("Filter by status button pressed")
        if is_admin:
            from filter_handlers import handle_status_filter_button
            return await handle_status_filter_button(update, context)
        else:
            await update.message.reply_text(st.NOT_AUTHORIZED)
            
    elif text == "🔍 البحث المتقدم":
        logging.info("Advanced search button pressed")
        if is_admin:
            # تعيين حالة البحث المتقدم
            context.user_data['in_advanced_search'] = True
            from advanced_search_handlers import advanced_search_command
            
    elif text == "🧠 المساعد الذكي":
        logging.info("AI assistant button pressed")
        from ai_handlers import ai_start
        return await ai_start(update, context)
            
    elif text == "🔍 البحث المتقدم":
        logging.info("Advanced search button pressed")
        if is_admin:
            # تعيين حالة البحث المتقدم
            context.user_data['in_advanced_search'] = True
            from advanced_search_handlers import advanced_search_command
            return await advanced_search_command(update, context)
        else:
            await update.message.reply_text(st.NOT_AUTHORIZED)
    
    # Delivery confirmation buttons
    elif text == "✅ تأكيد استلام زبون":
        logging.info("Confirm delivery button pressed")
        from delivery_handlers import confirm_delivery_command
        return await confirm_delivery_command(update, context)
            
    elif text == "📋 قائمة الشحنات المستلمة":
        logging.info("List delivered notifications button pressed")
        from delivery_handlers import list_delivered_notifications
        return await list_delivered_notifications(update, context)
    
    elif text == "👥 إدارة المسؤولين":
        logging.info("Manage admins button pressed")
        if is_admin:
            return await manage_admins(update, context)
        else:
            await update.message.reply_text(st.NOT_AUTHORIZED)
            
    elif text == "🛡️ إدارة الصلاحيات":
        logging.info("Permissions management button pressed")
        if is_admin:
            try:
                # بدلاً من استخدام معالج المحادثة مباشرة، سنستخدم الأمر عبر إرسال رسالة جديدة
                sent_message = await update.message.reply_text(
                    "🛡️ *نظام إدارة صلاحيات المستخدمين*\n\n"
                    "يمكنك هنا إدارة صلاحيات المستخدمين غير المسؤولين.\n"
                    "اختر إحدى العمليات التالية:\n\n"
                    "/permissions - لبدء إدارة الصلاحيات\n\n"
                    "يرجى استخدام الأمر المباشر بدلاً من الضغط على الأزرار",
                    parse_mode='Markdown'
                )
            except Exception as e:
                logging.error(f"Error sending permissions menu: {e}")
                await update.message.reply_text("حدث خطأ أثناء فتح إدارة الصلاحيات. الرجاء استخدام الأمر /permissions بشكل مباشر.")
        else:
            await update.message.reply_text(st.NOT_AUTHORIZED)
    
    elif text == "❓ مساعدة المسؤول":
        logging.info("Admin help button pressed")
        if is_admin:
            return await admin_help(update, context)
        else:
            await update.message.reply_text(st.NOT_AUTHORIZED)
            
    elif text == "✏️ قالب الرسالة":
        logging.info("Message template button pressed")
        if is_admin:
            return await message_template_command(update, context)
        else:
            await update.message.reply_text(st.NOT_AUTHORIZED)
            
    elif text == "✏️ قالب الترحيب":
        logging.info("Welcome template button pressed")
        if is_admin:
            return await welcome_template_command(update, context)
        else:
            await update.message.reply_text(st.NOT_AUTHORIZED)
            
    elif text == "🎨 إعدادات السمة":
        logging.info("Theme settings button pressed")
        if is_admin:
            try:
                # بدلاً من استخدام معالج المحادثة مباشرة، سنستخدم الأمر عبر إرسال رسالة جديدة
                sent_message = await update.message.reply_text(
                    "🎨 *إدارة السمة وخيارات العلامة التجارية*\n\n"
                    "هنا يمكنك تخصيص ألوان البوت وتغيير إعدادات العلامة التجارية للشركة.\n\n"
                    "يرجى استخدام الأمر المباشر التالي:\n"
                    "/theme - لبدء إدارة إعدادات السمة\n\n"
                    "يرجى استخدام الأمر المباشر بدلاً من الضغط على الأزرار",
                    parse_mode='Markdown'
                )
            except Exception as e:
                logging.error(f"Error sending theme settings menu: {e}")
                await update.message.reply_text("حدث خطأ أثناء فتح إعدادات السمة. الرجاء استخدام الأمر /theme بشكل مباشر.")
        else:
            await update.message.reply_text(st.NOT_AUTHORIZED)
            
    elif text == "🤖 شخصية البوت":
        logging.info("Bot personality button pressed")
        if is_admin:
            try:
                # إرسال رسالة توضيحية ثم الأمر المباشر
                sent_message = await update.message.reply_text(
                    "🤖 *إعدادات شخصية البوت*\n\n"
                    "يمكنك تعديل طريقة تفاعل البوت مع المستخدمين من خلال ضبط شخصية البوت.\n\n"
                    "يرجى استخدام الأمر المباشر التالي:\n"
                    "/personality - لبدء إدارة إعدادات شخصية البوت\n\n"
                    "يمكنك تعديل مستوى الرسمية والحماس واستخدام الرموز التعبيرية وغيرها من العوامل.",
                    parse_mode='Markdown'
                )
                # تنفيذ الأمر تلقائياً بعد إرسال الرسالة التوضيحية
                await context.bot.send_message(update.effective_chat.id, "/personality")
            except Exception as e:
                logging.error(f"Error sending personality settings menu: {e}")
                await update.message.reply_text("حدث خطأ أثناء فتح إعدادات شخصية البوت. الرجاء استخدام الأمر /personality بشكل مباشر.")
        else:
            await update.message.reply_text(st.NOT_AUTHORIZED)
            
    elif text == "🚀 الحملات التسويقية":
        logging.info("Marketing campaigns button pressed")
        if is_admin:
            try:
                # استدعاء أمر الحملات التسويقية مباشرة
                from marketing_campaign_handlers import marketing_campaigns_command
                
                # استدعاء الأمر مباشرة
                return await marketing_campaigns_command(update, context)
            except Exception as e:
                logging.error(f"Error in marketing campaigns command: {e}")
                await update.message.reply_text("حدث خطأ أثناء فتح نظام الحملات التسويقية. الرجاء المحاولة مجدداً.")
        else:
            await update.message.reply_text(st.NOT_AUTHORIZED)
            
    elif text == "💾 النسخ الاحتياطي":
        logging.info("Backup button pressed")
        if is_admin:
            try:
                # استدعاء أمر النسخ الاحتياطي مباشرة
                from backup_handlers import backup_command
                
                # استدعاء الأمر مباشرة
                return await backup_command(update, context)
            except Exception as e:
                logging.error(f"Error in backup command: {e}")
                await update.message.reply_text("حدث خطأ أثناء فتح نظام النسخ الاحتياطي. الرجاء المحاولة مجدداً.")
        else:
            await update.message.reply_text(st.NOT_AUTHORIZED)
            
    elif text == "📊 الإحصائيات":
        logging.info("Statistics button pressed")
        if is_admin:
            try:
                # استدعاء أمر الإحصائيات مباشرة
                from stats_handlers import stats_command
                
                # تعيين الوسائط اللازمة بدون تغيير النص
                context.args = []
                
                # استدعاء الأمر مباشرة
                return await stats_command(update, context)
            except Exception as e:
                logging.error(f"Error in statistics command: {e}")
                await update.message.reply_text("حدث خطأ أثناء عرض الإحصائيات. الرجاء المحاولة مجدداً.")
        else:
            await update.message.reply_text(st.NOT_AUTHORIZED)
    
    # User buttons
    elif text == "🔍 بحث باسم العميل":
        logging.info("Search by name button pressed")
        # التحقق مما إذا كان المستخدم مسؤولاً للسماح بالبحث باسم العميل
        if is_admin:
            await update.message.reply_text(st.SEARCH_PROMPT)
            context.user_data['search_type'] = 'اسم'
            return AWAITING_SEARCH_QUERY
        else:
            # منع المستخدمين العاديين من البحث بالاسم لأسباب أمنية
            await update.message.reply_text("⚠️ البحث بالاسم متاح فقط للمسؤولين لأسباب أمنية. الرجاء استخدام البحث برقم الهاتف.")
    
    elif text == "📱 بحث برقم الهاتف":
        logging.info("Search by phone button pressed")
        await update.message.reply_text(st.PHONE_SEARCH_PROMPT)
        context.user_data['search_type'] = 'هاتف'
        return AWAITING_SEARCH_QUERY
        
    elif text == "📋 سجلات البحث السابقة":
        logging.info("Search history button pressed")
        from search_history_handlers import view_search_history
        return await view_search_history(update, context)
    
    elif text == "❓ المساعدة":
        logging.info("Help button pressed")
        await help_command(update, context)
    
    elif text == "❌ إلغاء العملية الحالية" or "إلغاء العملية" in text:
        logging.info("Cancel button pressed")
        # If we're in a conversation from admin_handlers, use its cancel function
        if 'conversation_state' in context.user_data:
            from admin_handlers import cancel_add
            await cancel_add(update, context)
        else:
            await cancel_command(update, context)
    
    elif text == st.MAIN_MENU_BUTTON:
        logging.info("Main menu button pressed")
        await main_menu_command(update, context)
    
    else:
        # Check if we are in the middle of any conversation
        if 'in_advanced_search' in context.user_data and context.user_data['in_advanced_search']:
            # معالجة مدخلات البحث المتقدم
            logging.info(f"Handling advanced search input: '{text}'")
            from advanced_search_handlers import process_search_input
            await process_search_input(update, context)
        elif 'search_type' in context.user_data:
            logging.info(f"Handling search query: '{text}'")
            await received_search_query(update, context)
        elif 'conversation_state' in context.user_data:
            state = context.user_data['conversation_state']
            logging.info(f"In conversation state: {state}")
            
            # Handle add notification conversation states
            if state == NAME:
                # التعامل مع إدخال الاسم
                logging.info(f"Processing name input: '{text}'")
                await received_name(update, context)
            elif state == PHONE:
                # التعامل مع إدخال رقم الهاتف
                logging.info(f"Processing phone input: '{text}'")
                await received_phone(update, context)
            elif state == REMINDER_HOURS:
                # التعامل مع إدخال وقت التذكير
                logging.info(f"Processing reminder hours input: '{text}'")
                await received_reminder_hours(update, context)
            # Smart mode states have been removed
            else:
                logging.info(f"Unknown command in conversation: '{text}'")
                await update.message.reply_text(st.INVALID_COMMAND)
        else:
            logging.info(f"Unknown command: '{text}'")
            await update.message.reply_text(st.INVALID_COMMAND)

async def handle_unknown_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle unknown commands."""
    await update.message.reply_text(st.INVALID_COMMAND)

async def error_handler(update: object, context: ContextTypes.DEFAULT_TYPE):
    """Log errors caused by updates."""
    logger.error(f"Update {update} caused error: {context.error}")

async def telegram_self_ping(context: ContextTypes.DEFAULT_TYPE):
    """
    يرسل طلبًا إلى API تيليجرام للحفاظ على نشاط البوت.
    هذه الدالة تعمل كنبضة قلب تيليجرام للحفاظ على اتصال البوت وتجنب وضع السكون.
    مع معالجة متقدمة للاستثناءات لضمان استمرارية الدالة حتى في حالة الأخطاء المؤقتة.
    تستخدم الآن ثلاثة أساليب متتالية: getMe، sendChatAction، وgetUpdates لضمان أقصى استقرار.
    """
    max_retry_attempts = 5  # زيادة عدد المحاولات
    retry_count = 0
    success = False
    
    # الطريقة 1: استخدام getMe (أسلوب أساسي)
    while retry_count < max_retry_attempts and not success:
        try:
            # نرسل أمر getMe إلى API تيليجرام
            bot_info = await context.bot.get_me()
            logging.debug(f"✓ نبضة تيليجرام ناجحة (معرف البوت: {bot_info.id})")
            success = True
            # حتى مع النجاح، نكمل بالطرق الأخرى للتأكيد
            break
        except telegram_error.NetworkError as e:
            # خطأ في الشبكة، يمكن أن يكون مؤقتًا
            retry_count += 1
            logging.warning(f"⚠️ خطأ شبكة في نبضة تيليجرام (محاولة {retry_count}/{max_retry_attempts}): {e}")
            if retry_count < max_retry_attempts:
                # ننتظر قبل إعادة المحاولة مع زيادة وقت الانتظار تدريجياً
                await asyncio.sleep(0.5 * retry_count)
        except telegram_error.TimedOut as e:
            # انتهاء وقت الاتصال، يمكن أن يكون مؤقتًا
            retry_count += 1
            logging.warning(f"⚠️ انتهاء وقت اتصال نبضة تيليجرام (محاولة {retry_count}/{max_retry_attempts}): {e}")
            if retry_count < max_retry_attempts:
                # ننتظر قبل إعادة المحاولة مع زيادة وقت الانتظار تدريجياً
                await asyncio.sleep(1 * retry_count)
        except Exception as e:
            # خطأ عام، نسجله ونستمر
            retry_count += 1
            logging.error(f"❌ فشل في إرسال نبضة تيليجرام: {str(e)}")
            import traceback
            logging.debug(traceback.format_exc())
            if retry_count < max_retry_attempts:
                await asyncio.sleep(1)  # انتظار قبل المحاولة التالية
            
    # الطريقة 2: إرسال إشارة نشاط للمسؤول الرئيسي (فعالة لإبقاء البوت نشطًا)
    if not success or True:  # نستخدم هذه الطريقة حتى إذا نجحت الطريقة الأولى
        retry_count = 0  # إعادة تعيين العداد للطريقة الثانية
        
        while retry_count < max_retry_attempts and not success:
            try:
                # الحصول على معرف المسؤول الرئيسي من قاعدة البيانات
                admin_id = db.get_main_admin_id()
                
                if admin_id:
                    # تنويع نوع النشاط لتجنب القيود
                    actions = ["typing", "upload_photo", "record_voice", "upload_document", "find_location"]
                    action = actions[retry_count % len(actions)]
                    
                    # إرسال إشارة نشاط بدون إشعار فعلي
                    await context.bot.send_chat_action(
                        chat_id=admin_id,
                        action=action
                    )
                    logging.debug(f"✓ تم إرسال إشارة نشاط '{action}' إلى المسؤول الرئيسي")
                    success = True
                    break
                else:
                    logging.warning("⚠️ لم يتم العثور على معرف المسؤول الرئيسي لإرسال إشارة نشاط")
                    retry_count += 1
            except Exception as action_error:
                retry_count += 1
                if retry_count < max_retry_attempts:
                    await asyncio.sleep(0.5)  # انتظار قصير قبل المحاولة التالية
                logging.warning(f"⚠️ محاولة {retry_count}: فشل إرسال إشارة نشاط للمسؤول: {action_error}")
    
    # الطريقة 3: استخدام getUpdates كاحتياط نهائي (يحافظ على الاتصال مع API)
    if not success:
        try:
            # استخدام getUpdates مع الحد 0 (لن يجلب أي تحديثات فعلية)
            await context.bot.get_updates(limit=1, timeout=1, offset=-1)
            logging.debug("✓ تم إرسال نبضة تيليجرام باستخدام getUpdates")
            success = True
        except Exception as updates_error:
            logging.error(f"❌ فشل في إرسال نبضة تيليجرام باستخدام getUpdates: {updates_error}")
    
    # تحديث ملف نبضات القلب يدوياً لضمان تجديده حتى في حالة فشل جميع الطرق
    try:
        update_heartbeat_file()
        if not success:
            logging.info("✓ تم تحديث ملف نبضات القلب يدوياً على الرغم من فشل نبضات تيليجرام")
    except Exception as hb_error:
        logging.error(f"❌ فشل في تحديث ملف نبضات القلب: {hb_error}")
    
    # تسجيل النتيجة النهائية
    if not success:
        logging.error(f"❌ فشلت جميع محاولات نبضة تيليجرام ({max_retry_attempts} محاولات × 3 طرق)")
    return success

def cleanup_marker_files():
    """تنظيف ملفات العلامات القديمة عند بدء تشغيل البوت"""
    markers = [
        "bot_shutdown_marker",
        "watchdog_ping",
        "bot_restart_marker",
        "restart_requested.log"
    ]
    
    for marker in markers:
        if os.path.exists(marker):
            try:
                os.remove(marker)
                logging.info(f"✓ تم حذف ملف العلامة القديم: {marker}")
            except Exception as e:
                logging.error(f"❌ خطأ في حذف ملف العلامة: {marker}: {e}")
    
    # التحقق من علامة البدء النظيف
    if os.path.exists("bot_start_clean"):
        try:
            os.remove("bot_start_clean")
            logging.info("تم بدء تشغيل البوت بواسطة نظام التشغيل الموحد")
        except Exception as e:
            logging.error(f"خطأ في قراءة علامة البدء النظيف: {e}")

def main():
    """Start the bot."""
    # التحقق من أن هذا هو المثيل الوحيد للبوت باستخدام نظام قفل المثيل
    if not check_single_instance():
        logging.error("❌ هناك مثيل آخر من البوت قيد التشغيل بالفعل. جاري الخروج...")
        sys.exit(1)
    
    # تنظيف ملفات العلامات القديمة
    cleanup_marker_files()
    
    # Create the required directories
    os.makedirs("data", exist_ok=True)
    os.makedirs("data/images", exist_ok=True)
    
    # تشغيل خدمة Keep-Alive لمنع توقف البوت بسبب عدم النشاط
    try:
        import keep_alive
        logging.info("بدء تشغيل خدمة Keep-Alive للحفاظ على استمرارية البوت...")
        keep_alive_threads = keep_alive.start_keep_alive_service()
        logging.info("✅ تم تشغيل خدمة Keep-Alive بنجاح!")
    except ImportError:
        logging.warning("⚠️ لم يتم العثور على وحدة keep_alive. سيتم تجاهل خدمة الحفاظ على النشاط.")
    except Exception as e:
        logging.error(f"❌ خطأ أثناء تشغيل خدمة Keep-Alive: {e}")
    
    # Create the Application and pass it the bot's token
    # محاولة الحصول على التوكن من التكوين الموحد إذا كان متاحاً
    try:
        from unified_config import get_bot_token
        token = get_bot_token()
        logging.info("✅ تم الحصول على توكن البوت من نظام التكوين الموحد")
        application = Application.builder().token(token).build()
    except ImportError:
        logging.info("استخدام توكن البوت من ملف config.py")
        application = Application.builder().token(config.TOKEN).build()
    
    # إضافة معالجات الاستدعاء العامة مباشرة في بداية القائمة لضمان أولويتها
    # هذه المعالجات ستلتقط جميع الاستدعاءات قبل معالجات المحادثة
    from permissions_handlers import handle_permissions_callback, handle_global_permissions_callback
    from theme_handlers import handle_theme_callback, handle_global_theme_callback
    
    # وظائف مساعدة للمعالجات العامة
    async def handle_global_permissions_callback_wrapper(update: Update, context: ContextTypes.DEFAULT_TYPE):
        """معالج عام لاستدعاءات إدارة الصلاحيات لضمان استجابتها."""
        logging.info("🔧 Global permissions callback handler activated")
        try:
            # التحقق من أن الاستدعاء متعلق بنظام الصلاحيات
            callback_data = update.callback_query.data
            logging.info(f"Received callback_data in handle_permissions_callback: {callback_data}")
            
            # إذا كان الاستدعاء يبدأ بـ campaign_، قم بتمريره إلى معالج الحملات التسويقية
            if callback_data.startswith("campaign_"):
                logging.info(f"Redirecting campaign callback to campaign handler: {callback_data}")
                from marketing_campaign_handlers import handle_campaign_callbacks
                return await handle_campaign_callbacks(update, context)
                
            # إذا كان الاستدعاء يبدأ بـ theme_، قم بتمريره إلى معالج السمة
            if callback_data.startswith("theme_"):
                logging.info(f"Redirecting theme callback to theme handler: {callback_data}")
                return await handle_theme_callback(update, context)
                
            # إذا كان الاستدعاء يبدأ بـ ai_، قم بتمريره إلى معالج الذكاء الاصطناعي
            if callback_data.startswith("ai_"):
                logging.info(f"Redirecting AI callback to AI handler: {callback_data}")
                from ai_handlers import handle_ai_callback
                return await handle_ai_callback(update, context)
                
            # إذا كان الاستدعاء متعلق بالصلاحيات، قم بتمريره
            if callback_data.startswith("perm_") or callback_data.startswith("permissions_"):
                return await handle_permissions_callback(update, context)
                
            # معالجة استدعاءات قالب الرسائل النصية
            if callback_data.startswith("template_") or callback_data == "view_template" or callback_data == "edit_template":
                logging.info(f"Redirecting template callback to template handler: {callback_data}")
                from admin_handlers import handle_template_callback
                return await handle_template_callback(update, context)
                
            # معالجة استدعاءات قالب الرسائل الترحيبية
            if callback_data.startswith("welcome_template_") or callback_data == "view_welcome_template" or callback_data == "edit_welcome_template":
                logging.info(f"Redirecting welcome template callback to welcome template handler: {callback_data}")
                from admin_handlers import handle_welcome_template_callback
                return await handle_welcome_template_callback(update, context)
                
            # معالجة استدعاءات قالب رسائل التحقق
            if callback_data.startswith("verification_template_") or callback_data == "view_verification_template" or callback_data == "edit_verification_template":
                logging.info(f"Redirecting verification template callback to verification template handler: {callback_data}")
                from admin_handlers import handle_verification_template_callback
                return await handle_verification_template_callback(update, context)
                
            # إذا لم يتم التعرف على نوع الاستدعاء
            logging.warning(f"Unhandled callback_data: {callback_data}")
            await update.callback_query.answer("إجراء غير معروف")
            return None
        except Exception as e:
            logging.error(f"🚨 Error in global permissions callback: {e}")
            import traceback
            logging.error(traceback.format_exc())
            # عرض إشعار للمستخدم
            await update.callback_query.answer("حدث خطأ أثناء معالجة الطلب.")
            return None
    
    async def handle_global_theme_callback_wrapper(update: Update, context: ContextTypes.DEFAULT_TYPE):
        """معالج عام لاستدعاءات إدارة السمة لضمان استجابتها."""
        callback_data = update.callback_query.data
        
        # تحقق فقط من callback data التي تبدأ بـ theme_ أو logo_mode_
        if callback_data.startswith("theme_") or callback_data.startswith("logo_mode_"):
            logging.info("🎨 Global theme callback handler activated")
            try:
                logging.info(f"Processing theme callback: {callback_data}")
                return await handle_theme_callback(update, context)
            except Exception as e:
                logging.error(f"🚨 Error in global theme callback: {e}")
                import traceback
                logging.error(traceback.format_exc())
                # عرض إشعار للمستخدم
                await update.callback_query.answer("حدث خطأ أثناء معالجة إعدادات السمة.")
                return None
        
        # لا تقوم المعالج العام بمعالجة callbacks غير الخاصة بالسمة
        return None
        
    async def handle_global_campaign_callback_wrapper(update: Update, context: ContextTypes.DEFAULT_TYPE):
        """معالج عام لاستدعاءات نظام الحملات التسويقية لضمان استجابتها."""
        callback_data = update.callback_query.data
        
        # تحقق فقط من callback data التي تبدأ بـ campaign_
        if callback_data.startswith("campaign_"):
            logging.info("🚀 Global marketing campaign callback handler activated")
            try:
                # التحقق من أن الاستدعاء متعلق بنظام الحملات التسويقية
                logging.info(f"Processing campaign callback: {callback_data}")
                from marketing_campaign_handlers import handle_campaign_callbacks
                return await handle_campaign_callbacks(update, context)
            except Exception as e:
                logging.error(f"🚨 Error in global campaign callback: {e}")
                import traceback
                logging.error(traceback.format_exc())
                # عرض إشعار للمستخدم
                await update.callback_query.answer("حدث خطأ أثناء معالجة الطلب.")
                return None
        
        # لا تقوم المعالج العام بمعالجة callbacks غير الخاصة بالحملات
        return None
    
    # إضافة معالج مخصص للتعامل مع استدعاءات عرض الإشعارات وإرسال رسائل التحقق وتصفية الإشعارات بأولوية عالية
    from admin_handlers import handle_admin_callback, send_verification_message_command
    from filter_handlers import handle_filter_callback, handle_date_filter_callback, handle_status_filter_callback
    
    # معالج مخصص لاستدعاءات عرض الإشعارات بأولوية قصوى
    async def direct_view_notification_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
        """معالج خاص لاستدعاءات عرض الإشعارات فقط"""
        query = update.callback_query
        
        # تسجيل الاستدعاء للتشخيص
        logging.info(f"⭐ Received callback in direct handler: {query.data}")
        
        # التعامل فقط مع استدعاءات عرض الإشعارات
        if query.data.startswith("admin_view_"):
            try:
                logging.info(f"⭐ Processing admin_view callback directly: {query.data}")
                # إرسال إشعار بأننا نعالج الطلب
                await query.answer("جاري التحميل...")
                return await handle_admin_callback(update, context)
            except Exception as e:
                import traceback
                logging.error(f"⚠️ Error in direct view handler: {e}")
                logging.error(traceback.format_exc())
                await query.answer("حدث خطأ أثناء معالجة الطلب")
                
        # تمرير الاستدعاءات الأخرى
        return False
    
    # معالج مخصص لاستدعاءات إرسال رسائل التحقق
    async def direct_verification_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
        """معالج خاص لاستدعاءات إرسال رسائل التحقق"""
        query = update.callback_query
        
        # تسجيل الاستدعاء للتشخيص
        logging.info(f"🔔 Received verification callback: {query.data}")
        
        # التعامل فقط مع استدعاءات إرسال رسائل التحقق
        if query.data.startswith("send_verification_"):
            try:
                logging.info(f"🔔 Processing verification callback directly: {query.data}")
                # إرسال إشعار بأننا نعالج الطلب
                await query.answer("جاري إرسال رسالة التحقق...")
                return await send_verification_message_command(update, context)
            except Exception as e:
                import traceback
                logging.error(f"⚠️ Error in verification handler: {e}")
                logging.error(traceback.format_exc())
                await query.answer("حدث خطأ أثناء إرسال رسالة التحقق")
                
        # تمرير الاستدعاءات الأخرى
        return False
    
    # معالج مخصص لاستدعاءات تصفية الإشعارات
    async def direct_filter_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
        """معالج خاص لاستدعاءات تصفية الإشعارات"""
        query = update.callback_query
        
        # تسجيل الاستدعاء للتشخيص
        logging.info(f"🔍 Received filter callback: {query.data}")
        
        # التعامل مع استدعاءات تصفية الإشعارات
        try:
            if query.data.startswith("filter_"):
                logging.info(f"🔍 Processing filter callback directly: {query.data}")
                await query.answer("جاري تنفيذ التصفية...")
                return await handle_filter_callback(update, context)
            elif query.data.startswith("date_"):
                logging.info(f"📅 Processing date filter callback directly: {query.data}")
                await query.answer("جاري تصفية التاريخ...")
                return await handle_date_filter_callback(update, context)
            elif query.data.startswith("status_"):
                logging.info(f"📊 Processing status filter callback directly: {query.data}")
                await query.answer("جاري تصفية الحالة...")
                return await handle_status_filter_callback(update, context)
        except Exception as e:
            import traceback
            logging.error(f"⚠️ Error in filter handler: {e}")
            logging.error(traceback.format_exc())
            await query.answer("حدث خطأ أثناء تصفية الإشعارات")
            
        # تمرير الاستدعاءات الأخرى
        return False
        
    # معالج مخصص لاستدعاءات الإحصائيات
    async def direct_stats_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
        """معالج خاص لاستدعاءات الإحصائيات"""
        query = update.callback_query
        
        # تسجيل الاستدعاء للتشخيص
        logging.info(f"📊 Received stats callback: {query.data}")
        
        # التعامل مع استدعاءات الإحصائيات
        try:
            if query.data.startswith("stats_"):
                logging.info(f"📊 Processing stats callback directly: {query.data}")
                await query.answer("جاري تحميل الإحصائيات...")
                
                # استدعاء المعالج المناسب حسب نوع الاستدعاء
                from stats_handlers import handle_stats_callback, handle_stats_type_callback
                
                # إذا كان استدعاء عودة أو إلغاء، نستخدم handle_stats_type_callback
                if query.data in ["stats_back", "stats_cancel"]:
                    logging.info(f"📊 Processing stats type callback: {query.data}")
                    return await handle_stats_type_callback(update, context)
                else:
                    # الاستدعاءات الرئيسية للإحصائيات
                    logging.info(f"📊 Processing main stats callback: {query.data}")
                    return await handle_stats_callback(update, context)
        except Exception as e:
            import traceback
            logging.error(f"⚠️ Error in stats handler: {e}")
            logging.error(traceback.format_exc())
            await query.answer("حدث خطأ أثناء معالجة الإحصائيات")
            
        # تمرير الاستدعاءات الأخرى
        return False
        
    # معالج مخصص لاستدعاءات الصلاحيات
    async def direct_permissions_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
        """معالج خاص لاستدعاءات الصلاحيات"""
        query = update.callback_query
        
        # تسجيل الاستدعاء للتشخيص
        logging.info(f"🔑 Received permissions callback: {query.data}")
        
        # التعامل مع استدعاءات الصلاحيات
        try:
            if query.data.startswith("perm_") or query.data.startswith("permissions_"):
                logging.info(f"🔑 Processing permissions callback directly: {query.data}")
                await query.answer("جاري معالجة الصلاحيات...")
                
                # استدعاء معالج الصلاحيات
                from permissions_handlers import handle_permissions_callback
                return await handle_permissions_callback(update, context)
        except Exception as e:
            import traceback
            logging.error(f"⚠️ Error in permissions handler: {e}")
            logging.error(traceback.format_exc())
            await query.answer("حدث خطأ أثناء معالجة الصلاحيات")
            
        # تمرير الاستدعاءات الأخرى
        return False
    
    # معالج مخصص لأزرار واجهة المراقبة Watchdog في مجموعة -5 (أعلى أولوية)
    async def direct_watchdog_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
        """معالج خاص لاستدعاءات أزرار واجهة المراقبة"""
        query = update.callback_query
        
        # تسجيل الاستدعاء للتشخيص
        logging.info(f"🔍 Received watchdog callback: {query.data}")
        
        # التعامل فقط مع استدعاءات أزرار المراقبة
        watchdog_patterns = [
            "admin_restart_bot",
            "admin_clean_markers",
            "admin_view_logs",
            "admin_return_watchdog"
        ]
        
        for pattern in watchdog_patterns:
            if query.data == pattern:
                logging.info(f"🔍 Processing watchdog callback directly: {query.data}")
                await query.answer("جاري المعالجة...")
                
                # استدعاء معالج أزرار المراقبة
                from admin_handlers import handle_watchdog_callback
                return await handle_watchdog_callback(update, context)
                
        # تمرير الاستدعاءات الأخرى
        return False
    
    # إضافة معالجات الاستدعاء بترتيب الأولوية الصحيح
    # صفر: معالج مخصص لأزرار واجهة المراقبة في مجموعة -5 (أعلى أولوية)
    application.add_handler(
        CallbackQueryHandler(
            direct_watchdog_handler,
            pattern=r'^admin_(restart_bot|clean_markers|view_logs|return_watchdog)$'
        ),
        group=-5
    )
    
    # أولاً: معالج مخصص لعرض الإشعارات في مجموعة -2 (أولوية عالية)
    application.add_handler(
        CallbackQueryHandler(direct_view_notification_handler, pattern=r'^admin_view_'), 
        group=-2
    )
    
    # ثانياً: معالج مخصص لإرسال رسائل التحقق في مجموعة -1 (أولوية عالية)
    application.add_handler(
        CallbackQueryHandler(direct_verification_handler, pattern=r'^send_verification_'),
        group=-1
    )
    
    # ثالثاً: معالج مخصص لتصفية الإشعارات في مجموعة 0 (أولوية عالية)
    application.add_handler(
        CallbackQueryHandler(direct_filter_handler, pattern=r'^filter_|^date_|^status_'),
        group=0
    )
    
    # رابعاً: معالج مخصص للإحصائيات في مجموعة 0 (أولوية عالية)
    application.add_handler(
        CallbackQueryHandler(direct_stats_handler, pattern=r'^stats_'),
        group=0
    )
    
    # خامساً: معالج مخصص للصلاحيات في مجموعة 0 (أولوية عالية)
    application.add_handler(
        CallbackQueryHandler(direct_permissions_handler, pattern=r'^perm_|^permissions_'),
        group=0
    )
    
    # معالج مخصص للذكاء الاصطناعي في مجموعة 0 (أولوية عالية)
    async def direct_ai_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
        """معالج خاص لاستدعاءات الذكاء الاصطناعي"""
        query = update.callback_query
        
        # تسجيل الاستدعاء للتشخيص
        logging.info(f"🧠 Received AI callback: {query.data}")
        
        # التعامل مع استدعاءات الذكاء الاصطناعي
        try:
            if query.data.startswith("ai_"):
                logging.info(f"🧠 Processing AI callback directly: {query.data}")
                await query.answer("جاري معالجة الطلب...")
                
                # استدعاء معالج الذكاء الاصطناعي
                from ai_handlers import handle_ai_callback
                return await handle_ai_callback(update, context)
        except Exception as e:
            import traceback
            logging.error(f"⚠️ Error in AI handler: {e}")
            logging.error(traceback.format_exc())
            await query.answer("حدث خطأ أثناء معالجة طلب الذكاء الاصطناعي")
            
        # تمرير الاستدعاءات الأخرى
        return False
        
    application.add_handler(
        CallbackQueryHandler(direct_ai_handler, pattern=r'^ai_'),
        group=0
    )
    
    # سادساً: معالج مخصص لإدارة المسؤولين في مجموعة 0 (أولوية عالية)
    async def direct_admin_manage_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
        """معالج خاص لاستدعاءات إدارة المسؤولين"""
        query = update.callback_query
        
        # تسجيل الاستدعاء للتشخيص
        logging.info(f"👥 Received admin manage callback: {query.data}")
        
        # التعامل مع استدعاءات إدارة المسؤولين
        try:
            if query.data.startswith("admin_manage_"):
                logging.info(f"👥 Processing admin manage callback directly: {query.data}")
                await query.answer("جاري معالجة إدارة المسؤولين...")
                
                # استدعاء معالج إدارة المسؤولين
                from admin_handlers import handle_admin_manage_callback
                return await handle_admin_manage_callback(update, context)
        except Exception as e:
            import traceback
            logging.error(f"⚠️ Error in admin manage handler: {e}")
            logging.error(traceback.format_exc())
            await query.answer("حدث خطأ أثناء معالجة إدارة المسؤولين")
            
        # تمرير الاستدعاءات الأخرى
        return False
    
    application.add_handler(
        CallbackQueryHandler(direct_admin_manage_handler, pattern=r'^admin_manage_'),
        group=0
    )
    
    # سابعاً: معالج مخصص لتعديل وحذف الإشعارات في مجموعة 0 (أولوية عالية)
    async def direct_notification_edit_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
        """معالج خاص لاستدعاءات تعديل وحذف الإشعارات"""
        query = update.callback_query
        
        # تسجيل الاستدعاء للتشخيص
        logging.info(f"✏️ Received notification edit callback: {query.data}")
        
        try:
            # التعامل مع استدعاءات تعديل وحذف الإشعارات
            if (query.data.startswith("admin_edit_") or 
                query.data.startswith("admin_delete_") or 
                (query.data.startswith("admin_confirm_delete_")) or 
                (query.data == "admin_cancel_delete")):
                
                logging.info(f"✏️ Processing notification edit/delete callback directly: {query.data}")
                await query.answer("جاري المعالجة...")
                
                # استدعاء معالج تعديل وحذف الإشعارات
                from admin_handlers import handle_admin_callback
                return await handle_admin_callback(update, context)
            
        except Exception as e:
            import traceback
            logging.error(f"⚠️ Error in notification edit handler: {e}")
            logging.error(traceback.format_exc())
            await query.answer("حدث خطأ أثناء معالجة تعديل/حذف الإشعار")
            
        # تمرير الاستدعاءات الأخرى
        return False
    
    application.add_handler(
        CallbackQueryHandler(direct_notification_edit_handler, 
                           pattern=r'^admin_edit_|^admin_delete_|^admin_confirm_delete_|^admin_cancel_delete$'),
        group=0
    )
    
    # معالج خاص لأزرار التنقل بين صفحات الإشعارات في مجموعة -2 (أعلى أولوية)
    async def pagination_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
        """معالج خاص لأزرار التنقل بين صفحات الإشعارات"""
        query = update.callback_query
        
        # تسجيل الاستدعاء للتشخيص
        logging.info(f"📄 Received pagination callback: {query.data}")
        
        try:
            # التعامل مع استدعاءات التنقل بين الصفحات
            if query.data.startswith("admin_page_"):
                logging.info(f"📄 Processing pagination callback directly: {query.data}")
                await query.answer("جاري الانتقال للصفحة...")
                
                # استدعاء معالج التنقل بين الصفحات
                from admin_handlers import handle_admin_callback
                return await handle_admin_callback(update, context)
            
        except Exception as e:
            import traceback
            logging.error(f"⚠️ Error in pagination handler: {e}")
            logging.error(traceback.format_exc())
            await query.answer("حدث خطأ أثناء تحميل الصفحة")
            
        # تمرير الاستدعاءات الأخرى
        return False
    
    application.add_handler(
        CallbackQueryHandler(pagination_handler, pattern=r'^admin_page_'),
        group=-2  # أعلى أولوية لضمان استجابة أزرار التنقل
    )
    
    # ثامناً: معالج مخصص لأزرار البحث في مجموعة 0 (أولوية عالية)
    async def direct_search_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
        """معالج خاص لاستدعاءات البحث في قائمة الإشعارات"""
        query = update.callback_query
        
        # تسجيل الاستدعاء للتشخيص
        logging.info(f"🔍 Received search callback: {query.data}")
        
        try:
            # التعامل مع استدعاءات البحث
            if query.data.startswith("search_"):
                logging.info(f"🔍 Processing search callback directly: {query.data}")
                await query.answer("جاري معالجة البحث...")
                
                # استدعاء معالج البحث
                from search_handlers import handle_search_callback
                return await handle_search_callback(update, context)
            
        except Exception as e:
            import traceback
            logging.error(f"⚠️ Error in search handler: {e}")
            logging.error(traceback.format_exc())
            await query.answer("حدث خطأ أثناء معالجة عملية البحث")
            
        # تمرير الاستدعاءات الأخرى
        return False
    
    # معالج خاص لأزرار البحث بالاسم والرقم في أسفل قائمة الإشعارات
    async def notifications_list_search_buttons_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
        """معالج خاص لأزرار البحث في قائمة الإشعارات"""
        query = update.callback_query
        
        # تسجيل الاستدعاء للتشخيص
        logging.info(f"🔍 Received list search button callback: {query.data}")
        
        try:
            # معالجة زر البحث حسب الاسم
            if query.data == "search_by_name":
                logging.info("Processing search by name button")
                # استخدام answer_callback_query بدلاً من answer لإظهار الرسالة
                await context.bot.answer_callback_query(callback_query_id=query.id, text="جاري فتح البحث بالاسم...", show_alert=False)
                
                # التحقق من صلاحيات المستخدم
                user_id = update.effective_user.id
                import config
                if not db.is_admin(user_id) and not db.has_permission(user_id, config.PERMISSION_SEARCH_BY_NAME):
                    await query.message.reply_text("⚠️ البحث بالاسم متاح فقط للمسؤولين والمستخدمين المخولين. الرجاء استخدام البحث برقم الهاتف.")
                    return
                
                # بدء عملية البحث بالاسم
                keyboard = [
                    [st.MAIN_MENU_BUTTON]
                ]
                reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
                await query.message.reply_text("🔍 أدخل اسم العميل للبحث:", reply_markup=reply_markup)
                
                # تحديد نوع البحث في بيانات المستخدم
                context.user_data['search_type'] = 'اسم'
                from admin_handlers import AWAITING_SEARCH_NAME
                return AWAITING_SEARCH_NAME
            
            # معالجة زر البحث حسب الرقم
            elif query.data == "search_by_phone":
                logging.info("Processing search by phone button")
                # استخدام answer_callback_query بدلاً من answer لإظهار الرسالة
                await context.bot.answer_callback_query(callback_query_id=query.id, text="جاري فتح البحث بالرقم...", show_alert=False)
                
                # بدء عملية البحث بالرقم
                keyboard = [
                    [st.MAIN_MENU_BUTTON]
                ]
                reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
                await query.message.reply_text("🔍 أدخل رقم هاتف العميل للبحث:", reply_markup=reply_markup)
                
                # تحديد نوع البحث في بيانات المستخدم
                context.user_data['search_type'] = 'هاتف'
                from admin_handlers import AWAITING_SEARCH_PHONE
                return AWAITING_SEARCH_PHONE
            
        except Exception as e:
            import traceback
            logging.error(f"⚠️ Error in list search buttons handler: {e}")
            logging.error(traceback.format_exc())
            await query.answer("حدث خطأ أثناء معالجة زر البحث")
            
        # تمرير الاستدعاءات الأخرى
        return False
    
    application.add_handler(
        CallbackQueryHandler(direct_search_handler, pattern=r'^search_'),
        group=0
    )
    
    # إضافة معالج أزرار البحث في قائمة الإشعارات
    application.add_handler(
        CallbackQueryHandler(notifications_list_search_buttons_handler, pattern=r'^search_by_'),
        group=-1  # مجموعة أعلى أولوية من المعالج العام
    )
    
    # إضافة معالجات عالية الأولوية لأزرار تعديل وحذف الإشعارات
    from admin_handlers import handle_admin_callback
    
    # إضافة معالجات الذكاء الاصطناعي
    from ai_handlers import get_ai_handlers
    for handler in get_ai_handlers():
        application.add_handler(handler)
    
    # معالجات تعديل وحذف الإشعارات بأولوية عالية
    application.add_handler(CallbackQueryHandler(handle_admin_callback, pattern=r'^admin_edit_name_'), group=-5)
    application.add_handler(CallbackQueryHandler(handle_admin_callback, pattern=r'^admin_edit_phone_'), group=-5)
    application.add_handler(CallbackQueryHandler(handle_admin_callback, pattern=r'^admin_edit_image_'), group=-5)
    application.add_handler(CallbackQueryHandler(handle_admin_callback, pattern=r'^admin_delete_'), group=-5)
    application.add_handler(CallbackQueryHandler(handle_admin_callback, pattern=r'^admin_confirm_delete_'), group=-5)
    application.add_handler(CallbackQueryHandler(handle_admin_callback, pattern=r'^admin_cancel_delete'), group=-5)
    application.add_handler(CallbackQueryHandler(handle_admin_callback, pattern=r'^admin_page_'), group=-5)
    
    # ثم معالجات عامة أخرى في مجموعة 0
    application.add_handler(CallbackQueryHandler(handle_global_campaign_callback_wrapper), group=0)
    application.add_handler(CallbackQueryHandler(handle_global_theme_callback_wrapper), group=0)
    application.add_handler(CallbackQueryHandler(handle_global_permissions_callback_wrapper), group=0)
    
    # Basic command handlers
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(CommandHandler("cancel", cancel_command))
    application.add_handler(CommandHandler("restart", restart_command))
    application.add_handler(CommandHandler(st.MAIN_MENU_COMMAND, main_menu_command))
    
    # Add explicit permissions, theme and marketing command handlers
    from permissions_handlers import manage_permissions
    from theme_handlers import theme_command
    from marketing_campaign_handlers import marketing_campaigns_command
    application.add_handler(CommandHandler("permissions", manage_permissions))
    application.add_handler(CommandHandler("theme", theme_command))
    application.add_handler(CommandHandler("marketing", marketing_campaigns_command))
    
    # Add admin handlers
    for handler in get_admin_handlers():
        application.add_handler(handler)
    
    # Add search handlers
    for handler in get_search_handlers():
        application.add_handler(handler)
        
    # Add statistics handlers
    for handler in get_stats_handlers():
        application.add_handler(handler)
        
    # Add delivery confirmation handlers
    for handler in get_delivery_handlers():
        application.add_handler(handler)
        
    # Add search history handler
    application.add_handler(get_search_history_handler())
    
    # Add filter handlers
    for handler in get_filter_handlers():
        application.add_handler(handler)
        
    # Add advanced search handler
    application.add_handler(get_advanced_search_handler())
    
    # Add permissions handlers
    for handler in get_permissions_handlers():
        application.add_handler(handler)
        
    # Add theme handlers
    for handler in get_theme_handlers():
        application.add_handler(handler)
        
    # Add personality handlers
    try:
        for handler in get_personality_handlers():
            application.add_handler(handler)
        logging.info("Personality handlers loaded successfully")
    except Exception as e:
        logging.error(f"Error loading personality handlers: {e}")
    
    # Add backup handlers
    try:
        for handler in get_backup_handlers():
            application.add_handler(handler)
        logging.info("Backup handlers loaded successfully")
    except Exception as e:
        logging.error(f"Error loading backup handlers: {e}")
        
    # Add marketing campaign handlers
    try:
        from marketing_campaign_handlers import get_marketing_campaign_handlers
        for handler in get_marketing_campaign_handlers():
            # المهم هو تسجيل معالج المحادثة للحملات التسويقية في مجموعة منخفضة (3-) 
            # لضمان أنه يتم تنفيذه قبل المعالج العام للرسائل النصية
            application.add_handler(handler, group=-3)
        logging.info("Marketing campaign handlers loaded successfully")
    except Exception as e:
        logging.error(f"Error loading marketing campaign handlers: {e}")
    
    # Add our own implementation of photo handler for image conversation state
    async def handle_photos(update, context):
        logging.info("Handling photo message...")
        
        # تحقق من context.chat_data للوصول إلى حالة المحادثة في نظام ConversationHandler 
        chat_id = update.effective_chat.id
        user_id = update.effective_user.id
        logging.info(f"Photo from user_id: {user_id}, chat_id: {chat_id}")
        
        # تحقق من حالة محادثة نظام السمة - يجب تنفيذه أولاً
        from theme_handlers import AWAITING_COMPANY_LOGO
        
        # استخدام process_company_logo مباشرة لمعالجة صور شعار الشركة
        try:
            import theme_handlers as th
            
            # نتحقق إذا كانت حالة المحادثة تشير إلى انتظار شعار الشركة
            chat_id = update.effective_chat.id
            
            # استخدام طريقة أكثر أماناً للتحقق من حالة المحادثة
            try:
                # محاولة تشغيل معالج شعار الشركة مباشرة إذا كانت آخر رسالة تطلب شعار الشركة
                last_message = context.bot_data.get('last_sent_messages', {}).get(chat_id, '')
                if 'شعار الشركة' in last_message:
                    logging.info(f"Found request for company logo in last message")
                    logging.info("Processing photo as company logo")
                    return await th.process_company_logo(update, context)
            except Exception as e:
                logging.error(f"Error checking chat history: {e}")
                
            # نحاول أيضًا التحقق ما إذا كان المستخدم قد تلقى رسالة طلب شعار مؤخرًا
            last_bot_message = getattr(context, 'last_bot_message', None)
            if last_bot_message and 'شعار الشركة' in last_bot_message:
                logging.info("Last bot message requested company logo, processing image as logo")
                return await th.process_company_logo(update, context)
                
            logging.info("Photo is not for theme conversation based on chat_data state")
        except Exception as e:
            logging.error(f"Error checking theme conversation state: {e}")
            import traceback
            logging.error(traceback.format_exc())
        
        # التحقق من حالة المحادثة في context.user_data (نظام إضافة الإشعارات)
        if 'conversation_state' in context.user_data:
            state = context.user_data['conversation_state']
            logging.info(f"Found conversation_state in user_data: {state}")
            
            # Handle standard image upload state
            if state == IMAGE:
                logging.info(f"Processing image in conversation state IMAGE")
                
                # Implement image handling directly instead of using received_image
                try:
                    # Enhanced logging for image processing
                    logging.info(f"Starting image processing")
                    
                    # Verify we have the required data in context.user_data
                    if "customer_name" not in context.user_data or "phone_number" not in context.user_data:
                        logging.error("Missing customer_name or phone_number in user_data")
                        logging.info(f"Available user_data keys: {list(context.user_data.keys())}")
                        await update.message.reply_text("⚠️ حدث خطأ: بيانات العميل غير مكتملة. يرجى إعادة المحاولة.")
                        return
                    
                    # Log customer info for debugging
                    logging.info(f"Processing image for customer: {context.user_data.get('customer_name', 'MISSING')} | Phone: {context.user_data.get('phone_number', 'MISSING')}")
                    
                    # Get the largest available photo
                    photo = update.message.photo[-1]
                    logging.info(f"Received photo with file_id: {photo.file_id}")
                    
                    # Download the photo
                    file = await context.bot.get_file(photo.file_id)
                    image_bytes = await file.download_as_bytearray()
                    logging.info(f"Downloaded image, size: {len(image_bytes)} bytes")
                    
                    # Store the image data in context
                    context.user_data["image_bytes"] = image_bytes
                    
                    # Update conversation state to ask for reminder hours
                    context.user_data['conversation_state'] = REMINDER_HOURS
                    logging.info(f"Updated conversation state to REMINDER_HOURS: {REMINDER_HOURS}")
                    
                    # Ask for reminder hours
                    await update.message.reply_text(st.REMINDER_HOURS_PROMPT)
                    
                except Exception as e:
                    logging.error(f"Error processing image: {e}")
                    import traceback
                    logging.error(traceback.format_exc())
                    await update.message.reply_text(st.IMAGE_ERROR)
            
            # تعامل مع الصورة في مراحل مختلفة
            elif state == NAME:
                # استلام الصورة في مرحلة طلب الاسم - سنحاول استخراج المعلومات من الصورة
                logging.info(f"Processing image in NAME state - will try to extract information")
                import admin_handlers as ah
                await ah.received_image(update, context)
            elif state == PHONE:
                # استلام الصورة في مرحلة طلب رقم الهاتف - سنتقدم إلى مرحلة الصورة
                logging.info(f"Received photo in PHONE state - will process it as IMAGE state")
                context.user_data['conversation_state'] = IMAGE
                import admin_handlers as ah
                await ah.received_image(update, context)
            # معالجة صورة شعار الشركة حسب الحاجة (هذه احتياطية)
            elif state == AWAITING_COMPANY_LOGO:
                logging.info(f"Processing company logo image from conversation_state")
                try:
                    import theme_handlers as th
                    await th.process_company_logo(update, context)
                except Exception as e:
                    logging.error(f"Error processing company logo: {e}")
                    import traceback
                    logging.error(traceback.format_exc())
                    await update.message.reply_text("⚠️ حدث خطأ أثناء معالجة صورة شعار الشركة. يرجى المحاولة مرة أخرى.")
            # حالات أخرى
            else:
                logging.info(f"Received photo in unhandled conversation state: {state}")
                await update.message.reply_text("لست متأكدًا مما تحاول فعله بهذه الصورة في هذه المرحلة.")
                
        else:
            logging.info(f"Received photo outside of any conversation state")
            # نتحقق إذا كان المستخدم في محادثة نشطة عن طريق فحص context.chat_data
            try:
                chat_id = update.effective_chat.id
                active_conversations = False
                
                # نبحث عن مفاتيح الحالة في chat_data
                for key in context._chat_data.keys():
                    if key.startswith('CONVERSATION_'):
                        logging.info(f"Found active conversation in chat_data: {key}")
                        active_conversations = True
                
                if active_conversations:
                    logging.info("User has active conversations, letting other handlers process the message")
                    return
            except Exception as e:
                logging.error(f"Error checking active conversations: {e}")
            
            # لا توجد محادثة نشطة، نحلل الصورة باستخدام معالج الذكاء الاصطناعي
            logging.info("تحويل الصورة إلى محلل الصور الذكي")
            try:
                from ai_handlers import handle_image_upload
                # توجيه الصورة إلى معالج تحليل الصور في وحدة الذكاء الاصطناعي
                await handle_image_upload(update, context)
            except Exception as e:
                logging.error(f"خطأ أثناء تحليل الصورة تلقائياً: {e}")
                await update.message.reply_text("حدث خطأ أثناء تحليل الصورة. يرجى تجربة المساعد الذكي عبر الضغط على زر 'المساعد الذكي'")
    
    application.add_handler(MessageHandler(filters.PHOTO, handle_photos))
    
    # Add keyboard buttons handler (before unknown command handler)
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_keyboard_buttons))
    
    # Unknown command handler
    application.add_handler(MessageHandler(filters.COMMAND, handle_unknown_command))
    
    # Error handler
    application.add_error_handler(error_handler)
    
    # Scheduled reminder check function
    async def check_for_reminders(context: ContextTypes.DEFAULT_TYPE):
        """Check for notifications that need reminders sent."""
        logging.info("Checking for scheduled reminders...")
        
        # Get all notifications
        notifications = db.get_all_notifications()
        
        if not notifications:
            logging.info("No notifications found to check for reminders")
            return
        
        # Check and send reminders using the sms_service
        sent_count = sms_service.check_and_send_scheduled_reminders(notifications)
        
        # Force an update to the notifications database to ensure changes are saved
        db.save_json(db.NOTIFICATIONS_DB, {"notifications": notifications})
        
        if sent_count > 0:
            logging.info(f"Sent {sent_count} reminder(s)")
            
            # Update notifications in database to mark reminders as sent
            # (this is handled inside check_and_send_scheduled_reminders)
        else:
            logging.info("No reminders needed to be sent at this time")
    
    # Schedule the reminder check to run every 1 minute
    job_queue = application.job_queue
    if job_queue:
        job_queue.run_repeating(check_for_reminders, interval=60, first=10)
        logging.info("Scheduled reminder check job every minute")
    else:
        logging.warning("JobQueue not available - reminder checks will not run automatically")
        logging.warning("You need to install python-telegram-bot with [job-queue] extra, e.g., pip install 'python-telegram-bot[job-queue]'")
        
        # Add a manual way to check reminders for testing
        application.add_handler(CommandHandler("check_reminders", lambda u, c: check_for_reminders(c)))
    
    # تحديث ملف نبضات القلب عند البدء
    logging.info("بدء تشغيل نظام نبضات القلب...")
    update_heartbeat_file()  # تحديث ملف نبضات القلب عند البدء
    
    # جدولة وظيفة تحديث ملف نبضات القلب كل 15 ثانية
    job_queue = application.job_queue
    if job_queue:
        # تقليل فترة نبضات القلب إلى 15 ثانية
        job_queue.run_repeating(heartbeat_updater, interval=15, first=5)
        logging.info("تم جدولة تحديث نبضات القلب كل 15 ثانية")
        
        # تقليل فترة نبضات تيليجرام إلى 10 ثوانٍ للحفاظ على نشاط البوت
        job_queue.run_repeating(telegram_self_ping, interval=10, first=5)
        logging.info("تم جدولة نبضات تيليجرام كل 10 ثوانٍ للحفاظ على نشاط البوت")
        
        # إيقاف تشغيل وظيفة أمر /start التلقائي لأننا نستخدم sendChatAction الآن
        # جدولة تنفيذ أمر /start تلقائياً تم تعطيلها لأن نبضات تيليجرام المُحسنة (sendChatAction) أكثر كفاءة
        logging.info("🔕 تم تعطيل جدولة تنفيذ أمر /start التلقائي واستبداله بنبضات تيليجرام المُحسنة (sendChatAction)")
        
        # تعطيل إعادة التشغيل الدورية بناءً على طلب المستخدم
        from datetime import datetime, timedelta
        
        # تم تعطيل وظيفة إعادة التشغيل الدورية
        async def force_periodic_restart(context: ContextTypes.DEFAULT_TYPE):
            """وظيفة لإعادة تشغيل البوت بشكل دوري للحفاظ على الاستقرار (معطلة)"""
            # هذه الوظيفة معطلة تماماً بناءً على طلب المستخدم
            logging.info("⚠️ تم تعطيل إعادة التشغيل الدورية بناءً على طلب المستخدم")
            pass
            
        # تم تعطيل جدولة إعادة التشغيل الدوري نهائياً
        # job_queue.run_repeating(force_periodic_restart, interval=30*60, first=30*60)
        logging.info("⚠️ تم تعطيل جدولة إعادة تشغيل البوت الدورية بشكل نهائي بناءً على طلب المستخدم")
        
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
    
    # Start the Bot
    logging.info("بدء تشغيل البوت...")
 # … (كل الكود الأصلي لديك من التعاريف، handlers، جدولة الـ jobs، heartbeat، إلخ) …

def build_application() -> Application:
    """
    تجهيز الـ Application بكل التحضيرات (handlers, jobs, heartbeat_updater، إلخ)
    دون تشغيله، فقط إرجاعه جاهزًا للتشغيل.
    """
    application = Application.builder().token(TOKEN).build()
    
    # أضف هنا كل التحضيرات:
    # application.add_handler(...), job_queue، الخ
    
    return application


def main():
    """نقطة الدخول عند تشغيل bot.py مباشرةً."""
    app = build_application()
    logging.info("بدء تشغيل البوت…")
    app.run_polling()


 if __name__ == '__main__':
    main()

