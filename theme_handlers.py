"""
نظام إدارة السمات وخيارات العلامة التجارية للشركة
"""

import logging
import re
from telegram import Update, InlineKeyboardMarkup, InlineKeyboardButton, ReplyKeyboardMarkup, KeyboardButton
from telegram.ext import (
    ContextTypes, ConversationHandler, CommandHandler, CallbackQueryHandler,
    MessageHandler, filters
)

import database as db
import strings as st
from utils import check_admin

# حالات المحادثة
AWAITING_THEME_ACTION = 1
AWAITING_COLOR_NAME = 2
AWAITING_COLOR_VALUE = 3
AWAITING_COMPANY_NAME = 4
AWAITING_COMPANY_LOGO = 5
AWAITING_LOGO_MODE = 6

# حالات الاستجابة للأزرار
PRIMARY_COLOR = "primary"
SECONDARY_COLOR = "secondary"
ACCENT_COLOR = "accent"
SUCCESS_COLOR = "success"
WARNING_COLOR = "warning"
ERROR_COLOR = "error"
COMPANY_NAME = "company_name"
COMPANY_LOGO = "company_logo"
LOGO_MODE = "logo_mode"
RESET_THEME = "reset_theme"
MAIN_MENU = "main_menu"


@check_admin
async def theme_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """بدء عملية إدارة السمات."""
    logging.info(f"User {update.effective_user.id} started theme management")
    
    # الحصول على إعدادات السمة الحالية
    theme_settings = db.get_theme_settings()
    
    # إنشاء معاينة للإعدادات الحالية
    preview_text = create_theme_preview(theme_settings)
    
    # إنشاء لوحة المفاتيح
    keyboard = [
        [InlineKeyboardButton("🎨 اللون الرئيسي", callback_data=f"theme_{PRIMARY_COLOR}")],
        [InlineKeyboardButton("🎨 اللون الثانوي", callback_data=f"theme_{SECONDARY_COLOR}")],
        [InlineKeyboardButton("🎨 لون التمييز", callback_data=f"theme_{ACCENT_COLOR}")],
        [InlineKeyboardButton("✅ لون النجاح", callback_data=f"theme_{SUCCESS_COLOR}")],
        [InlineKeyboardButton("⚠️ لون التحذير", callback_data=f"theme_{WARNING_COLOR}")],
        [InlineKeyboardButton("❌ لون الخطأ", callback_data=f"theme_{ERROR_COLOR}")],
        [InlineKeyboardButton("🏢 اسم الشركة", callback_data=f"theme_{COMPANY_NAME}")],
        [InlineKeyboardButton("🖼️ شعار الشركة", callback_data=f"theme_{COMPANY_LOGO}")],
        [InlineKeyboardButton("🔄 وضع الشعار", callback_data=f"theme_{LOGO_MODE}")],
        [InlineKeyboardButton("↩️ إعادة ضبط السمة", callback_data=f"theme_{RESET_THEME}")],
        [InlineKeyboardButton("🏠 القائمة الرئيسية", callback_data=f"theme_{MAIN_MENU}")]
    ]
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.message.reply_text(
        f"🎨 *إدارة السمة وخيارات العلامة التجارية*\n\n"
        f"هنا يمكنك تخصيص ألوان البوت وتغيير إعدادات العلامة التجارية للشركة.\n\n"
        f"*إعدادات السمة الحالية:*\n"
        f"{preview_text}\n\n"
        f"اختر إعداداً لتغييره:",
        reply_markup=reply_markup,
        parse_mode="Markdown"
    )
    
    return AWAITING_THEME_ACTION


# معالج عام للاستدعاءات خارج نظام المحادثة
async def handle_global_theme_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """معالج عام لاستدعاءات إدارة السمة خارج نظام المحادثة."""
    logging.info("🌟 Handle global theme callback activated")
    query = update.callback_query
    
    if not query:
        return
    
    callback_data = query.data
    
    # تسجيل بيانات الاستدعاء للتشخيص
    logging.info(f"Global theme callback data: {callback_data}")
    
    # استدعاء معالج السمة الرئيسي لمعالجة البيانات
    try:
        return await handle_theme_callback(update, context)
    except Exception as e:
        logging.error(f"Error in global theme callback: {e}")
        import traceback
        logging.error(traceback.format_exc())
        
        # عرض إشعار للمستخدم
        try:
            await query.answer("حدث خطأ أثناء معالجة طلب تغيير السمة. الرجاء المحاولة مجدداً.")
        except Exception:
            pass
            
    return ConversationHandler.END


async def handle_theme_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """معالجة استجابات أزرار إدارة السمة."""
    query = update.callback_query
    
    try:
        # تسجيل بيانات المعاودة للتصحيح
        callback_data = query.data
        logging.info(f"Received theme callback data: {callback_data}")
        
        # تحقق من أن البيانات تبدأ بـ "theme_"
        if not callback_data.startswith("theme_"):
            logging.info(f"Handling general callback data: {callback_data}")
            # إذا كان اسم الاستدعاء يبدأ بـ "logo_mode_"، قم بإعادة توجيهه إلى المعالج المناسب
            if callback_data.startswith("logo_mode_"):
                return await handle_logo_mode_callback(update, context)
            await query.answer("إجراء غير معروف")
            return AWAITING_THEME_ACTION
        
        await query.answer()
        
        # الحصول على نوع الإجراء المطلوب - تعديل طريقة الاستخراج للتعامل مع أسماء متعددة الكلمات
        parts = callback_data.split('_')
        if len(parts) > 2 and parts[1] == "company" and parts[2] == "name":
            action = "company_name"
        elif len(parts) > 2 and parts[1] == "company" and parts[2] == "logo":
            action = "company_logo"
        elif len(parts) > 2 and parts[1] == "logo" and parts[2] == "mode":
            action = "logo_mode"
        else:
            action = parts[1]
        logging.info(f"Theme callback action: {action}")
        
        # الحصول على إعدادات السمة الحالية
        theme_settings = db.get_theme_settings()
        
        if action == MAIN_MENU:
            await query.message.reply_text("تم الخروج من إعدادات السمة.")
            return ConversationHandler.END
        
        elif action == RESET_THEME:
            # إعادة ضبط السمة إلى الإعدادات الافتراضية
            import config
            if db.reset_theme_settings():
                await query.message.reply_text("✅ تم إعادة ضبط السمة إلى الإعدادات الافتراضية.")
            else:
                await query.message.reply_text("❌ حدث خطأ أثناء إعادة ضبط السمة.")
            
            # عرض قائمة إدارة السمة مجدداً
            await theme_command(update, context)
            return AWAITING_THEME_ACTION
        
        elif action in [PRIMARY_COLOR, SECONDARY_COLOR, ACCENT_COLOR, SUCCESS_COLOR, WARNING_COLOR, ERROR_COLOR]:
            # حفظ نوع اللون المراد تغييره
            context.user_data['color_type'] = action
            
            # الحصول على اسم اللون بالعربية
            color_name = get_color_name_arabic(action)
            current_color = theme_settings.get(f"{action}_color", "#000000")
            
            await query.message.reply_text(
                f"🎨 تغيير {color_name}\n\n"
                f"اللون الحالي: `{current_color}`\n\n"
                f"يرجى إدخال اللون الجديد بتنسيق HEX (مثل #FF5733):",
                parse_mode="Markdown"
            )
            return AWAITING_COLOR_VALUE
        
        elif action == COMPANY_NAME:
            logging.info(f"Processing company name action")
            current_name = theme_settings.get("company_name", "شركة الشحن")
            
            await query.message.reply_text(
                f"🏢 تغيير اسم الشركة\n\n"
                f"الاسم الحالي: *{current_name}*\n\n"
                f"يرجى إدخال اسم الشركة الجديد:",
                parse_mode="Markdown"
            )
            return AWAITING_COMPANY_NAME
        
        elif action == LOGO_MODE:
            current_mode = theme_settings.get("logo_mode", "text")
            mode_text = get_logo_mode_arabic(current_mode)
            
            keyboard = [
                [InlineKeyboardButton("نص فقط", callback_data="logo_mode_text")],
                [InlineKeyboardButton("صورة فقط", callback_data="logo_mode_image")],
                [InlineKeyboardButton("نص وصورة", callback_data="logo_mode_both")],
                [InlineKeyboardButton("العودة", callback_data="logo_mode_back")]
            ]
            
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            await query.message.reply_text(
                f"🔄 تغيير وضع عرض الشعار\n\n"
                f"الوضع الحالي: *{mode_text}*\n\n"
                f"اختر الوضع الجديد:",
                reply_markup=reply_markup,
                parse_mode="Markdown"
            )
            return AWAITING_LOGO_MODE
        
        elif action == COMPANY_LOGO:
            logging.info(f"Processing company logo action")
            await query.message.reply_text(
                f"🖼️ تغيير شعار الشركة\n\n"
                f"يرجى إرسال صورة الشعار الجديدة:"
            )
            return AWAITING_COMPANY_LOGO
        
        else:
            logging.warning(f"Unknown theme action: {action}")
            await query.message.reply_text("❌ خيار غير معروف.")
            return AWAITING_THEME_ACTION
            
    except Exception as e:
        logging.error(f"Error in handle_theme_callback: {e}")
        import traceback
        logging.error(traceback.format_exc())
        try:
            await query.answer("حدث خطأ في معالجة الطلب")
        except:
            pass
        return AWAITING_THEME_ACTION


async def handle_logo_mode_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """معالجة استجابات أزرار وضع الشعار."""
    query = update.callback_query
    callback_data = query.data
    
    try:
        logging.info(f"Received logo mode callback data: {callback_data}")
        
        # التحقق من صحة بيانات المعاودة
        if not callback_data.startswith("logo_mode_"):
            # إذا كان الاستدعاء ليس لوضع الشعار، نقوم بإرجاعه للمعالج المناسب
            logging.info(f"Non-logo_mode callback detected: {callback_data}")
            if callback_data.startswith("theme_"):
                await query.answer()
                return await handle_theme_callback(update, context)
            await query.answer("إجراء غير معروف")
            return AWAITING_THEME_ACTION
        
        await query.answer()
        
        # الحصول على الوضع المختار
        parts = callback_data.split('_')
        if len(parts) >= 3:
            mode = parts[2]
            logging.info(f"Logo mode callback: {mode}")
            
            if mode == "back":
                # العودة إلى قائمة إدارة السمة
                await theme_command(update, context)
                return AWAITING_THEME_ACTION
            
            # تحديث وضع الشعار
            if mode in ["text", "image", "both"]:
                if db.update_theme_settings({"logo_mode": mode}):
                    mode_text = get_logo_mode_arabic(mode)
                    await query.message.reply_text(f"✅ تم تغيير وضع الشعار إلى: {mode_text}")
                else:
                    await query.message.reply_text("❌ حدث خطأ أثناء تحديث وضع الشعار.")
            else:
                logging.warning(f"Unknown logo mode: {mode}")
                await query.message.reply_text("❌ وضع شعار غير معروف.")
                
            # العودة إلى قائمة إدارة السمة
            await theme_command(update, context)
            return AWAITING_THEME_ACTION
        else:
            logging.warning(f"Invalid logo_mode data format: {callback_data}")
            await query.message.reply_text("❌ تنسيق بيانات غير صالح.")
            return AWAITING_THEME_ACTION
            
    except Exception as e:
        logging.error(f"Error in handle_logo_mode_callback: {e}")
        import traceback
        logging.error(traceback.format_exc())
        try:
            await query.answer("حدث خطأ في معالجة الطلب")
        except:
            pass
        return AWAITING_THEME_ACTION


async def process_color_value(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """معالجة قيمة اللون المستلمة."""
    color_value = update.message.text.strip()
    
    # التحقق من صحة تنسيق اللون
    if not is_valid_hex_color(color_value):
        await update.message.reply_text(
            "❌ تنسيق اللون غير صحيح. يرجى إدخال اللون بتنسيق HEX (مثل #FF5733):"
        )
        return AWAITING_COLOR_VALUE
    
    # الحصول على نوع اللون المراد تغييره
    color_type = context.user_data.get('color_type')
    if not color_type:
        await update.message.reply_text("❌ حدث خطأ: نوع اللون غير محدد.")
        return ConversationHandler.END
    
    # تحديث اللون في إعدادات السمة
    update_key = f"{color_type}_color"
    if db.update_theme_settings({update_key: color_value}):
        color_name = get_color_name_arabic(color_type)
        await update.message.reply_text(f"✅ تم تغيير {color_name} إلى: `{color_value}`", parse_mode="Markdown")
    else:
        await update.message.reply_text("❌ حدث خطأ أثناء تحديث اللون.")
    
    # إزالة بيانات المحادثة المؤقتة
    if 'color_type' in context.user_data:
        del context.user_data['color_type']
    
    # العودة إلى قائمة إدارة السمة
    await theme_command(update, context)
    return AWAITING_THEME_ACTION


async def process_company_name(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """معالجة اسم الشركة المستلم."""
    logging.info(f"Processing company name: received text message")
    
    company_name = update.message.text.strip()
    logging.info(f"Company name text: '{company_name}'")
    
    # التحقق من صحة الاسم
    if not company_name or len(company_name) > 50:
        await update.message.reply_text(
            "❌ اسم الشركة غير صالح. يجب أن يكون بين 1 و 50 حرفاً. يرجى المحاولة مجدداً:"
        )
        return AWAITING_COMPANY_NAME
    
    try:
        # تحديث اسم الشركة في إعدادات السمة
        logging.info(f"Updating company name to: {company_name}")
        if db.update_theme_settings({"company_name": company_name}):
            await update.message.reply_text(f"✅ تم تغيير اسم الشركة إلى: *{company_name}*", parse_mode="Markdown")
        else:
            await update.message.reply_text("❌ حدث خطأ أثناء تحديث اسم الشركة.")
        
        # العودة إلى قائمة إدارة السمة
        await theme_command(update, context)
        return AWAITING_THEME_ACTION
    except Exception as e:
        logging.error(f"Error in process_company_name: {e}")
        import traceback
        logging.error(traceback.format_exc())
        await update.message.reply_text("❌ حدث خطأ أثناء معالجة اسم الشركة. يرجى المحاولة مرة أخرى.")
        return AWAITING_COMPANY_NAME


async def process_company_logo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """معالجة شعار الشركة المستلم."""
    logging.info(f"Processing company logo image")
    
    # التحقق من وجود صورة
    if not update.message.photo:
        logging.warning("No photo received in process_company_logo")
        await update.message.reply_text(
            "❌ لم يتم استلام أي صورة. يرجى إرسال صورة الشعار:"
        )
        return AWAITING_COMPANY_LOGO
    
    try:
        # الحصول على أكبر نسخة من الصورة
        photo = update.message.photo[-1]
        logging.info(f"Received photo with file_id: {photo.file_id}")
        
        # تنزيل الصورة
        file = await context.bot.get_file(photo.file_id)
        image_bytes = await file.download_as_bytearray()
        logging.info(f"Downloaded image, size: {len(image_bytes)} bytes")
        
        # وضع حالة المحادثة في سياق المستخدم ليتمكن معالج الصور في bot.py من التعرف عليها
        context.user_data['conversation_state'] = AWAITING_COMPANY_LOGO
        
        # تحديث شعار الشركة
        success, logo_id = db.update_company_logo(image_bytes)
        logging.info(f"Logo update result: success={success}, logo_id={logo_id}")
        
        if success:
            await update.message.reply_text("✅ تم تحديث شعار الشركة بنجاح.")
        else:
            await update.message.reply_text("❌ حدث خطأ أثناء تحديث شعار الشركة.")
    
    except Exception as e:
        logging.error(f"Error processing company logo: {e}")
        import traceback
        logging.error(traceback.format_exc())
        await update.message.reply_text("❌ حدث خطأ أثناء معالجة الصورة. يرجى المحاولة مجدداً.")
        return AWAITING_COMPANY_LOGO
    
    # العودة إلى قائمة إدارة السمة
    await theme_command(update, context)
    return AWAITING_THEME_ACTION


async def cancel_theme(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """إلغاء عملية إدارة السمة."""
    await update.message.reply_text("تم إلغاء عملية إدارة السمة.")
    return ConversationHandler.END


# وظائف مساعدة

def is_valid_hex_color(color):
    """التحقق من صحة تنسيق لون HEX."""
    pattern = r'^#([A-Fa-f0-9]{6}|[A-Fa-f0-9]{3})$'
    return bool(re.match(pattern, color))


def get_color_name_arabic(color_type):
    """الحصول على اسم اللون بالعربية."""
    color_names = {
        PRIMARY_COLOR: "اللون الرئيسي",
        SECONDARY_COLOR: "اللون الثانوي",
        ACCENT_COLOR: "لون التمييز",
        SUCCESS_COLOR: "لون النجاح",
        WARNING_COLOR: "لون التحذير",
        ERROR_COLOR: "لون الخطأ"
    }
    return color_names.get(color_type, "لون غير معروف")


def get_logo_mode_arabic(mode):
    """الحصول على وصف وضع الشعار بالعربية."""
    mode_names = {
        "text": "نص فقط",
        "image": "صورة فقط",
        "both": "نص وصورة"
    }
    return mode_names.get(mode, "وضع غير معروف")


def create_theme_preview(theme_settings):
    """إنشاء نص معاينة لإعدادات السمة الحالية."""
    preview = ""
    preview += f"🎨 اللون الرئيسي: `{theme_settings.get('primary_color', '#1e88e5')}`\n"
    preview += f"🎨 اللون الثانوي: `{theme_settings.get('secondary_color', '#26a69a')}`\n"
    preview += f"🎨 لون التمييز: `{theme_settings.get('accent_color', '#ff5722')}`\n"
    preview += f"✅ لون النجاح: `{theme_settings.get('success_color', '#4caf50')}`\n"
    preview += f"⚠️ لون التحذير: `{theme_settings.get('warning_color', '#ffc107')}`\n"
    preview += f"❌ لون الخطأ: `{theme_settings.get('error_color', '#e53935')}`\n"
    preview += f"🏢 اسم الشركة: *{theme_settings.get('company_name', 'شركة الشحن')}*\n"
    
    logo_mode = theme_settings.get('logo_mode', 'text')
    preview += f"🔄 وضع الشعار: *{get_logo_mode_arabic(logo_mode)}*\n"
    
    has_logo = theme_settings.get('company_logo') is not None
    preview += f"🖼️ شعار الشركة: {'✅ موجود' if has_logo else '❌ غير موجود'}"
    
    return preview


def get_theme_handlers():
    """إرجاع معالجات إدارة السمة."""
    
    # إضافة معالج عام للاستدعاءات لكل استدعاءات السمة
    general_callback_handler = CallbackQueryHandler(handle_global_theme_callback)
    
    # تعديل معالج المحادثة مع إضافة المزيد من الخيارات للتعامل مع الاستدعاءات
    theme_conv_handler = ConversationHandler(
        entry_points=[CommandHandler("theme", theme_command)],
        states={
            AWAITING_THEME_ACTION: [
                # استخدام معالج استدعاءات عام لتلقي كل الاستدعاءات
                CallbackQueryHandler(handle_theme_callback),
            ],
            AWAITING_COLOR_VALUE: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, process_color_value),
                CommandHandler("cancel", cancel_theme),
            ],
            AWAITING_COMPANY_NAME: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, process_company_name),
                CommandHandler("cancel", cancel_theme),
            ],
            AWAITING_LOGO_MODE: [
                CallbackQueryHandler(handle_logo_mode_callback),
                # إضافة معالج عام للاستدعاءات في كل الحالات
                CallbackQueryHandler(handle_theme_callback),
            ],
            AWAITING_COMPANY_LOGO: [
                MessageHandler(filters.PHOTO, process_company_logo),
                CommandHandler("cancel", cancel_theme),
            ],
        },
        fallbacks=[
            CommandHandler("cancel", cancel_theme),
            # إضافة معالج الاستدعاءات العام كواجهة احتياطية 
            CallbackQueryHandler(handle_theme_callback)
        ],
        name="theme_conversation",
        persistent=False
    )
    
    # إرجاع جميع المعالجات بما في ذلك المعالج العام للاستدعاءات خارج المحادثة
    return [theme_conv_handler, general_callback_handler]