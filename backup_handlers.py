"""
وظائف إدارة النسخ الاحتياطي للبوت
"""
import logging
import os
from datetime import datetime
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    CommandHandler, CallbackQueryHandler, ConversationHandler,
    ContextTypes
)

import database as db
import strings as st
import auto_backup

# معرف المحادثة للنسخ الاحتياطي
AWAITING_RESTORE_CONFIRMATION = 1


async def backup_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """أمر لإدارة النسخ الاحتياطية"""
    # التحقق من صلاحيات المستخدم
    if not db.is_main_admin(update.effective_user.id):
        await update.message.reply_text(st.ONLY_MAIN_ADMIN)
        return
    
    # إنشاء لوحة مفاتيح لإدارة النسخ الاحتياطية
    keyboard = [
        [InlineKeyboardButton("🔄 إنشاء نسخة احتياطية جديدة", callback_data="create_backup")],
        [InlineKeyboardButton("📋 عرض النسخ الاحتياطية المتاحة", callback_data="list_backups")],
        [InlineKeyboardButton("🔙 رجوع", callback_data="admin_menu_main")]
    ]
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text(st.BACKUP_MENU_TITLE, reply_markup=reply_markup)


async def backup_menu_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """معالجة استدعاءات قائمة النسخ الاحتياطية"""
    query = update.callback_query
    await query.answer()
    
    # التحقق من صلاحيات المستخدم
    if not db.is_main_admin(query.from_user.id):
        await query.edit_message_text(st.ONLY_MAIN_ADMIN)
        return
    
    # عرض القائمة الرئيسية للنسخ الاحتياطية
    keyboard = [
        [InlineKeyboardButton("🔄 إنشاء نسخة احتياطية جديدة", callback_data="create_backup")],
        [InlineKeyboardButton("📋 عرض النسخ الاحتياطية المتاحة", callback_data="list_backups")],
        [InlineKeyboardButton("🔙 رجوع", callback_data="admin_menu_main")]
    ]
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    await query.edit_message_text(st.BACKUP_MENU_TITLE, reply_markup=reply_markup)


async def create_backup_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """إنشاء نسخة احتياطية جديدة"""
    query = update.callback_query
    await query.answer()
    
    # التحقق من صلاحيات المستخدم
    if not db.is_main_admin(query.from_user.id):
        await query.edit_message_text(st.ONLY_MAIN_ADMIN)
        return
    
    # إعلام المستخدم بأن إنشاء النسخة الاحتياطية قيد التقدم
    await query.edit_message_text("⏳ جاري إنشاء نسخة احتياطية جديدة...")
    
    # إنشاء نسخة احتياطية
    success, result = db.backup_database()
    
    if success:
        # النجاح، عرض معلومات النسخة الاحتياطية
        keyboard = [
            [InlineKeyboardButton("🔙 رجوع إلى قائمة النسخ الاحتياطية", callback_data="backup_menu_main")]
        ]
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.edit_message_text(
            f"✅ تم إنشاء النسخة الاحتياطية بنجاح!\n\n"
            f"📂 المسار: {result}",
            reply_markup=reply_markup
        )
    else:
        # فشل، عرض رسالة الخطأ
        keyboard = [
            [InlineKeyboardButton("🔄 إعادة المحاولة", callback_data="create_backup")],
            [InlineKeyboardButton("🔙 رجوع", callback_data="backup_menu_main")]
        ]
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.edit_message_text(
            f"❌ فشل إنشاء النسخة الاحتياطية\n\n"
            f"⚠️ الخطأ: {result}",
            reply_markup=reply_markup
        )


async def list_backups_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """عرض قائمة النسخ الاحتياطية المتاحة"""
    query = update.callback_query
    await query.answer()
    
    # التحقق من صلاحيات المستخدم
    if not db.is_main_admin(query.from_user.id):
        await query.edit_message_text(st.ONLY_MAIN_ADMIN)
        return
    
    # الحصول على قائمة النسخ الاحتياطية
    backups = db.get_backup_list()
    
    if not backups:
        # لا توجد نسخ احتياطية
        keyboard = [
            [InlineKeyboardButton("🔄 إنشاء نسخة احتياطية جديدة", callback_data="create_backup")],
            [InlineKeyboardButton("🔙 رجوع", callback_data="backup_menu_main")]
        ]
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.edit_message_text(
            st.NO_BACKUPS_AVAILABLE,
            reply_markup=reply_markup
        )
        return
    
    # عرض النسخ الاحتياطية (أحدث 5 نسخ فقط)
    latest_backups = backups[:5]
    
    message_text = st.AVAILABLE_BACKUPS + "\n\n"
    keyboard = []
    
    for i, backup in enumerate(latest_backups):
        # تنسيق تاريخ النسخة الاحتياطية
        backup_date = backup.get("date_formatted", "غير معروف")
        backup_size = backup.get("size_formatted", "غير معروف")
        backup_name = backup.get("filename", "غير معروف")
        
        message_text += f"{i+1}. <b>{backup_name}</b>\n"
        message_text += f"   📅 التاريخ: {backup_date}\n"
        message_text += f"   📊 الحجم: {backup_size}\n\n"
        
        # إضافة زر لاستعادة النسخة الاحتياطية
        keyboard.append([InlineKeyboardButton(
            f"🔄 استعادة النسخة {i+1}",
            callback_data=f"restore_backup_{backup_name}"
        )])
    
    # إضافة أزرار التنقل
    keyboard.append([InlineKeyboardButton("🔄 إنشاء نسخة احتياطية جديدة", callback_data="create_backup")])
    keyboard.append([InlineKeyboardButton("🔙 رجوع", callback_data="backup_menu_main")])
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    await query.edit_message_text(
        message_text,
        reply_markup=reply_markup,
        parse_mode="HTML"
    )


async def restore_backup_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """معالجة طلب استعادة نسخة احتياطية"""
    query = update.callback_query
    await query.answer()
    
    # التحقق من صلاحيات المستخدم
    if not db.is_main_admin(query.from_user.id):
        await query.edit_message_text(st.ONLY_MAIN_ADMIN)
        return
    
    # الحصول على اسم النسخة الاحتياطية من بيانات الاستدعاء
    backup_name = query.data.split('_', 2)[2]
    
    # تخزين اسم النسخة الاحتياطية في سياق المحادثة
    context.user_data['backup_to_restore'] = backup_name
    
    # عرض رسالة تأكيد
    keyboard = [
        [InlineKeyboardButton("✅ نعم، استعادة النسخة الاحتياطية", callback_data=f"confirm_restore_{backup_name}")],
        [InlineKeyboardButton("❌ لا، إلغاء الاستعادة", callback_data="cancel_restore")]
    ]
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    await query.edit_message_text(
        st.CONFIRM_RESTORE_BACKUP,
        reply_markup=reply_markup,
        parse_mode="HTML"
    )
    
    return AWAITING_RESTORE_CONFIRMATION


async def confirm_restore_backup_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """تأكيد استعادة النسخة الاحتياطية"""
    query = update.callback_query
    await query.answer()
    
    # التحقق من صلاحيات المستخدم
    if not db.is_main_admin(query.from_user.id):
        await query.edit_message_text(st.ONLY_MAIN_ADMIN)
        return ConversationHandler.END
    
    # الحصول على اسم النسخة الاحتياطية
    backup_name = query.data.split('_', 2)[2]
    
    # إعلام المستخدم بأن استعادة النسخة الاحتياطية قيد التقدم
    await query.edit_message_text("⏳ جاري استعادة النسخة الاحتياطية...")
    
    # استعادة النسخة الاحتياطية
    success, result = db.restore_backup(backup_name)
    
    if success:
        # النجاح، عرض رسالة نجاح
        keyboard = [
            [InlineKeyboardButton("🔙 رجوع إلى قائمة النسخ الاحتياطية", callback_data="backup_menu_main")]
        ]
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.edit_message_text(
            st.BACKUP_RESTORED_SUCCESS + "\n\n🔄 يرجى إعادة تشغيل البوت باستخدام الأمر /restart لتطبيق التغييرات.",
            reply_markup=reply_markup
        )
    else:
        # فشل، عرض رسالة الخطأ
        keyboard = [
            [InlineKeyboardButton("🔙 رجوع إلى قائمة النسخ الاحتياطية", callback_data="list_backups")]
        ]
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.edit_message_text(
            st.BACKUP_RESTORED_ERROR.format(result),
            reply_markup=reply_markup
        )
    
    # تنظيف سياق المحادثة
    if 'backup_to_restore' in context.user_data:
        del context.user_data['backup_to_restore']
    
    return ConversationHandler.END


async def cancel_restore_backup_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """إلغاء استعادة النسخة الاحتياطية"""
    query = update.callback_query
    await query.answer()
    
    # العودة إلى قائمة النسخ الاحتياطية
    keyboard = [
        [InlineKeyboardButton("🔄 إنشاء نسخة احتياطية جديدة", callback_data="create_backup")],
        [InlineKeyboardButton("📋 عرض النسخ الاحتياطية المتاحة", callback_data="list_backups")],
        [InlineKeyboardButton("🔙 رجوع", callback_data="admin_menu_main")]
    ]
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    await query.edit_message_text(st.RESTORE_CANCELLED, reply_markup=reply_markup)
    
    # تنظيف سياق المحادثة
    if 'backup_to_restore' in context.user_data:
        del context.user_data['backup_to_restore']
    
    return ConversationHandler.END


def get_backup_handlers():
    """الحصول على معالجات النسخ الاحتياطي"""
    restore_handler = ConversationHandler(
        entry_points=[
            CallbackQueryHandler(restore_backup_callback, pattern=r'^restore_backup_')
        ],
        states={
            AWAITING_RESTORE_CONFIRMATION: [
                CallbackQueryHandler(confirm_restore_backup_callback, pattern=r'^confirm_restore_'),
                CallbackQueryHandler(cancel_restore_backup_callback, pattern=r'^cancel_restore')
            ]
        },
        fallbacks=[],
        name="restore_backup_conversation",
        persistent=False
    )
    
    return [
        CommandHandler('backup', backup_command),
        CallbackQueryHandler(backup_menu_callback, pattern=r'^backup_menu'),
        CallbackQueryHandler(create_backup_callback, pattern=r'^create_backup'),
        CallbackQueryHandler(list_backups_callback, pattern=r'^list_backups'),
        restore_handler
    ]


def register_backup_handlers(application):
    """تسجيل معالجات النسخ الاحتياطي"""
    for handler in get_backup_handlers():
        application.add_handler(handler)
    logging.info("Backup handlers loaded successfully")