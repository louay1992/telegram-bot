"""
نظام إدارة صلاحيات المستخدمين.
هذا الملف يحتوي على معالجات لإضافة وإزالة وعرض صلاحيات المستخدمين.
"""

import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ConversationHandler, ContextTypes, CommandHandler, CallbackQueryHandler, MessageHandler, filters

import database
import config
from utils import create_back_button, check_user_is_admin

# حالات المحادثة لإدارة الصلاحيات
AWAITING_USER_ID = 1
AWAITING_PERMISSION_SELECTION = 2

# أنواع الإشعارات لمعالج استجابة الأزرار
SHOW_USERS = "perm_show_users"
ADD_PERMISSION = "perm_add"
REMOVE_PERMISSION = "perm_remove"
LIST_PERMISSIONS = "perm_list"
SELECT_USER = "perm_sel_user"
SELECT_PERMISSION = "perm_sel_perm"
CONFIRM_ADD = "perm_confirm_add"
CONFIRM_REMOVE = "perm_confirm_remove"
BACK_TO_PERMISSIONS = "perm_back_main"
PAGE_USERS = "perm_page_users"

# نص الأزرار
BTN_ADD_PERMISSION = "🟢 إضافة صلاحية"
BTN_REMOVE_PERMISSION = "🔴 إزالة صلاحية"
BTN_LIST_PERMISSIONS = "📋 عرض المستخدمين وصلاحياتهم"
BTN_MAIN_MENU = "🏠 القائمة الرئيسية"
BTN_BACK = "🔙 رجوع"

# القائمة الرئيسية لإدارة الصلاحيات
async def manage_permissions(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """إدارة صلاحيات المستخدمين."""
    # التحقق من أن المستخدم مسؤول
    if not await check_user_is_admin(update, context):
        return ConversationHandler.END
    
    # إنشاء لوحة المفاتيح
    keyboard = [
        [InlineKeyboardButton(BTN_ADD_PERMISSION, callback_data=ADD_PERMISSION)],
        [InlineKeyboardButton(BTN_REMOVE_PERMISSION, callback_data=REMOVE_PERMISSION)],
        [InlineKeyboardButton(BTN_LIST_PERMISSIONS, callback_data=LIST_PERMISSIONS)],
        [InlineKeyboardButton(BTN_MAIN_MENU, callback_data="main_menu")]
    ]
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    # إرسال رسالة الترحيب
    await update.message.reply_text(
        "🛡️ *نظام إدارة صلاحيات المستخدمين*\n\n"
        "يمكنك هنا إدارة صلاحيات المستخدمين غير المسؤولين.\n"
        "اختر إحدى العمليات التالية:",
        reply_markup=reply_markup,
        parse_mode='Markdown'
    )
    
    return AWAITING_PERMISSION_SELECTION

# عرض قائمة المستخدمين مع صلاحياتهم
async def show_users_with_permissions(update: Update, context: ContextTypes.DEFAULT_TYPE, page=0):
    """عرض قائمة المستخدمين الذين يملكون صلاحيات مع تفاصيل صلاحياتهم."""
    query = update.callback_query
    
    if query:
        await query.answer()
    
    # الحصول على قائمة المستخدمين مع صلاحياتهم
    users = database.get_all_users_with_permissions()
    
    if not users:
        # إذا لم يكن هناك مستخدمين
        keyboard = [[create_back_button(BACK_TO_PERMISSIONS)]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        if query:
            await query.edit_message_text(
                "🔍 لا يوجد مستخدمين لديهم صلاحيات خاصة حالياً.",
                reply_markup=reply_markup
            )
        else:
            await update.message.reply_text(
                "🔍 لا يوجد مستخدمين لديهم صلاحيات خاصة حالياً.",
                reply_markup=reply_markup
            )
        
        return AWAITING_PERMISSION_SELECTION
    
    # تقسيم المستخدمين إلى صفحات
    items_per_page = 5
    total_pages = (len(users) - 1) // items_per_page + 1
    
    # التأكد من أن رقم الصفحة صالح
    page = max(0, min(page, total_pages - 1))
    
    # تحديد المستخدمين للصفحة الحالية
    start_idx = page * items_per_page
    end_idx = min(start_idx + items_per_page, len(users))
    page_users = users[start_idx:end_idx]
    
    # إنشاء النص
    message_text = "👥 *المستخدمين وصلاحياتهم:*\n\n"
    
    for user in page_users:
        # ترجمة أسماء الصلاحيات
        permissions_text = ""
        for permission in user['permissions']:
            if permission == config.PERMISSION_SEARCH_BY_NAME:
                permissions_text += "• البحث بالاسم\n"
            else:
                permissions_text += f"• {permission}\n"
        
        # إضافة معلومات المستخدم
        username = user['username'] if user['username'] != "غير معروف" else user['first_name']
        message_text += f"👤 *{username}* (ID: `{user['id']}`)\n"
        message_text += f"الصلاحيات:\n{permissions_text}\n"
    
    # إضافة معلومات الصفحة
    message_text += f"\nالصفحة {page + 1} من {total_pages}"
    
    # إنشاء أزرار التنقل
    keyboard = []
    
    # أزرار الصفحات
    pagination_buttons = []
    if page > 0:
        pagination_buttons.append(InlineKeyboardButton("◀️", callback_data=f"{PAGE_USERS}:{page-1}"))
    
    if page < total_pages - 1:
        pagination_buttons.append(InlineKeyboardButton("▶️", callback_data=f"{PAGE_USERS}:{page+1}"))
    
    if pagination_buttons:
        keyboard.append(pagination_buttons)
    
    # زر الرجوع
    keyboard.append([create_back_button(BACK_TO_PERMISSIONS)])
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    # تحديث الرسالة أو إرسال رسالة جديدة
    if query:
        await query.edit_message_text(
            message_text,
            reply_markup=reply_markup,
            parse_mode='Markdown'
        )
    else:
        await update.message.reply_text(
            message_text,
            reply_markup=reply_markup,
            parse_mode='Markdown'
        )
    
    return AWAITING_PERMISSION_SELECTION

# بدء عملية إضافة صلاحية
async def start_add_permission(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """بدء عملية إضافة صلاحية لمستخدم."""
    query = update.callback_query
    await query.answer()
    
    # إنشاء لوحة المفاتيح
    keyboard = [[create_back_button(BACK_TO_PERMISSIONS)]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await query.edit_message_text(
        "🟢 *إضافة صلاحية جديدة*\n\n"
        "يرجى إرسال معرف المستخدم (User ID) الذي ترغب بإضافة صلاحية له.\n\n"
        "ملاحظة: يمكن للمستخدم معرفة معرف الخاص به عبر الضغط على /id",
        reply_markup=reply_markup,
        parse_mode='Markdown'
    )
    
    return AWAITING_USER_ID

# معالجة معرف المستخدم المستلم لإضافة صلاحية
async def process_user_id_for_permission(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """معالجة معرف المستخدم الذي تم استلامه لإضافة صلاحية."""
    # التحقق من أن الإدخال رقم صحيح
    user_id_text = update.message.text.strip()
    
    try:
        user_id = int(user_id_text)
        
        # التحقق من أن المستخدم ليس مسؤولاً بالفعل
        if database.is_admin(user_id):
            await update.message.reply_text(
                "⚠️ هذا المستخدم مسؤول بالفعل ويملك جميع الصلاحيات.\n"
                "يرجى إدخال معرف مستخدم آخر غير مسؤول."
            )
            return AWAITING_USER_ID
        
        # حفظ معرف المستخدم في سياق المحادثة
        context.user_data['permission_user_id'] = user_id
        context.user_data['username'] = "مستخدم"  # قيمة افتراضية
        context.user_data['first_name'] = "مستخدم"  # قيمة افتراضية
        
        # محاولة تحديث معلومات المستخدم إذا كان مستخدماً حالياً
        try:
            user = await context.bot.get_chat(user_id)
            context.user_data['username'] = user.username or "مستخدم"
            context.user_data['first_name'] = user.first_name or "مستخدم"
        except Exception as e:
            logging.warning(f"Could not get user info: {e}")
        
        # عرض خيارات الصلاحيات
        keyboard = []
        
        # إضافة خيارات الصلاحيات
        keyboard.append([InlineKeyboardButton("🔍 البحث بالاسم", callback_data=f"{SELECT_PERMISSION}:{config.PERMISSION_SEARCH_BY_NAME}")])
        
        # إضافة زر الرجوع
        keyboard.append([create_back_button(BACK_TO_PERMISSIONS)])
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await update.message.reply_text(
            f"👤 *إضافة صلاحية للمستخدم:* `{user_id}`\n\n"
            "يرجى اختيار الصلاحية التي ترغب بإضافتها:",
            reply_markup=reply_markup,
            parse_mode='Markdown'
        )
        
        return AWAITING_PERMISSION_SELECTION
        
    except ValueError:
        # إذا لم يكن الإدخال رقم صحيح
        await update.message.reply_text(
            "⚠️ يرجى إدخال معرف المستخدم كرقم صحيح فقط.\n"
            "حاول مرة أخرى:"
        )
        return AWAITING_USER_ID

# تأكيد إضافة صلاحية
async def confirm_add_permission(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """تأكيد إضافة الصلاحية المحددة للمستخدم."""
    query = update.callback_query
    await query.answer()
    
    # استخراج نوع الصلاحية من بيانات الاستجابة
    permission_type = query.data.split(':')[1]
    
    # استرجاع معرف المستخدم من سياق المحادثة
    user_id = context.user_data.get('permission_user_id')
    username = context.user_data.get('username', "مستخدم")
    first_name = context.user_data.get('first_name', "مستخدم")
    
    if not user_id:
        # إذا لم يتم العثور على معرف المستخدم
        await query.edit_message_text(
            "⚠️ حدث خطأ. يرجى المحاولة مرة أخرى."
        )
        return AWAITING_PERMISSION_SELECTION
    
    # ترجمة نوع الصلاحية
    permission_name = "غير معروف"
    if permission_type == config.PERMISSION_SEARCH_BY_NAME:
        permission_name = "البحث بالاسم"
    
    # إضافة الصلاحية
    success = database.add_permission_to_user(user_id, username, first_name, permission_type)
    
    # إنشاء لوحة المفاتيح
    keyboard = [[create_back_button(BACK_TO_PERMISSIONS)]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    if success:
        await query.edit_message_text(
            f"✅ تمت إضافة صلاحية *{permission_name}* للمستخدم بنجاح.\n\n"
            f"معرف المستخدم: `{user_id}`",
            reply_markup=reply_markup,
            parse_mode='Markdown'
        )
    else:
        await query.edit_message_text(
            f"❌ فشل في إضافة الصلاحية. يرجى المحاولة مرة أخرى.",
            reply_markup=reply_markup,
            parse_mode='Markdown'
        )
    
    return AWAITING_PERMISSION_SELECTION

# بدء عملية إزالة صلاحية
async def start_remove_permission(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """بدء عملية إزالة صلاحية من مستخدم."""
    query = update.callback_query
    await query.answer()
    
    # الحصول على قائمة المستخدمين مع صلاحياتهم
    users = database.get_all_users_with_permissions()
    
    if not users:
        # إذا لم يكن هناك مستخدمين
        keyboard = [[create_back_button(BACK_TO_PERMISSIONS)]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await query.edit_message_text(
            "🔍 لا يوجد مستخدمين لديهم صلاحيات خاصة حالياً.",
            reply_markup=reply_markup
        )
        
        return AWAITING_PERMISSION_SELECTION
    
    # إنشاء قائمة بالمستخدمين
    keyboard = []
    
    for user in users:
        username = user['username'] if user['username'] != "غير معروف" else user['first_name']
        user_text = f"{username} (ID: {user['id']})"
        keyboard.append([InlineKeyboardButton(user_text, callback_data=f"{SELECT_USER}:{user['id']}")])
    
    # إضافة زر الرجوع
    keyboard.append([create_back_button(BACK_TO_PERMISSIONS)])
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await query.edit_message_text(
        "🔴 *إزالة صلاحية*\n\n"
        "اختر المستخدم الذي ترغب بإزالة صلاحية منه:",
        reply_markup=reply_markup,
        parse_mode='Markdown'
    )
    
    return AWAITING_PERMISSION_SELECTION

# عرض صلاحيات المستخدم للإزالة
async def show_user_permissions_for_removal(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """عرض صلاحيات المستخدم المحدد للإزالة."""
    query = update.callback_query
    await query.answer()
    
    # استخراج معرف المستخدم من بيانات الاستجابة
    user_id = int(query.data.split(':')[1])
    
    # حفظ معرف المستخدم في سياق المحادثة
    context.user_data['permission_user_id'] = user_id
    
    # الحصول على صلاحيات المستخدم
    permissions = database.get_user_permissions(user_id)
    
    if not permissions:
        # إذا لم يكن هناك صلاحيات
        keyboard = [[create_back_button(BACK_TO_PERMISSIONS)]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await query.edit_message_text(
            f"⚠️ المستخدم ليس لديه أي صلاحيات حالياً.",
            reply_markup=reply_markup
        )
        
        return AWAITING_PERMISSION_SELECTION
    
    # إنشاء قائمة بالصلاحيات
    keyboard = []
    
    for permission in permissions:
        permission_name = "غير معروف"
        if permission == config.PERMISSION_SEARCH_BY_NAME:
            permission_name = "البحث بالاسم"
        
        keyboard.append([InlineKeyboardButton(f"🗑️ {permission_name}", callback_data=f"{CONFIRM_REMOVE}:{permission}")])
    
    # إضافة زر الرجوع
    keyboard.append([create_back_button(BACK_TO_PERMISSIONS)])
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    # محاولة الحصول على اسم المستخدم
    try:
        user = await context.bot.get_chat(user_id)
        username = user.username or user.first_name or f"المستخدم (ID: {user_id})"
    except:
        username = f"المستخدم (ID: {user_id})"
    
    await query.edit_message_text(
        f"🔴 *إزالة صلاحية من {username}*\n\n"
        "اختر الصلاحية التي ترغب بإزالتها:",
        reply_markup=reply_markup,
        parse_mode='Markdown'
    )
    
    return AWAITING_PERMISSION_SELECTION

# تأكيد إزالة صلاحية
async def confirm_remove_permission(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """تأكيد إزالة الصلاحية المحددة من المستخدم."""
    query = update.callback_query
    await query.answer()
    
    # استخراج نوع الصلاحية من بيانات الاستجابة
    permission_type = query.data.split(':')[1]
    
    # استرجاع معرف المستخدم من سياق المحادثة
    user_id = context.user_data.get('permission_user_id')
    
    if not user_id:
        # إذا لم يتم العثور على معرف المستخدم
        await query.edit_message_text(
            "⚠️ حدث خطأ. يرجى المحاولة مرة أخرى."
        )
        return AWAITING_PERMISSION_SELECTION
    
    # ترجمة نوع الصلاحية
    permission_name = "غير معروف"
    if permission_type == config.PERMISSION_SEARCH_BY_NAME:
        permission_name = "البحث بالاسم"
    
    # إزالة الصلاحية
    success = database.remove_permission_from_user(user_id, permission_type)
    
    # إنشاء لوحة المفاتيح
    keyboard = [[create_back_button(BACK_TO_PERMISSIONS)]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    if success:
        await query.edit_message_text(
            f"✅ تمت إزالة صلاحية *{permission_name}* من المستخدم بنجاح.\n\n"
            f"معرف المستخدم: `{user_id}`",
            reply_markup=reply_markup,
            parse_mode='Markdown'
        )
    else:
        await query.edit_message_text(
            f"❌ فشل في إزالة الصلاحية. يرجى المحاولة مرة أخرى.",
            reply_markup=reply_markup,
            parse_mode='Markdown'
        )
    
    return AWAITING_PERMISSION_SELECTION

# معالجة ردود الاستعلام لإدارة الصلاحيات
async def handle_permissions_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """معالجة ردود الاستعلام لإدارة الصلاحيات."""
    query = update.callback_query
    callback_data = query.data
    
    # تسجيل بيانات الاستجابة للتصحيح
    logging.info(f"Received callback_data in handle_permissions_callback: {callback_data}")
    
    try:
        # التعامل مع زر الرجوع الرئيسي
        if callback_data == BACK_TO_PERMISSIONS:
            await query.answer()
            await manage_permissions_callback(update, context)
            return AWAITING_PERMISSION_SELECTION
        
        # التعامل مع أزرار تصفح المستخدمين
        if callback_data.startswith(f"{PAGE_USERS}:"):
            await query.answer()
            page = int(callback_data.split(':')[1])
            await show_users_with_permissions(update, context, page)
            return AWAITING_PERMISSION_SELECTION
        
        # معالجة الإجراءات الرئيسية
        if callback_data == ADD_PERMISSION:
            await query.answer()
            return await start_add_permission(update, context)
        elif callback_data == REMOVE_PERMISSION:
            await query.answer()
            return await start_remove_permission(update, context)
        elif callback_data == LIST_PERMISSIONS:
            await query.answer()
            return await show_users_with_permissions(update, context)
        
        # معالجة تحديد المستخدم
        if callback_data.startswith(f"{SELECT_USER}:"):
            await query.answer()
            return await show_user_permissions_for_removal(update, context)
        
        # معالجة تحديد الصلاحية
        if callback_data.startswith(f"{SELECT_PERMISSION}:"):
            await query.answer()
            return await confirm_add_permission(update, context)
        
        # معالجة تأكيد إزالة الصلاحية
        if callback_data.startswith(f"{CONFIRM_REMOVE}:"):
            await query.answer()
            return await confirm_remove_permission(update, context)
        
        # إرجاع استجابة افتراضية
        logging.warning(f"Unhandled callback_data: {callback_data}")
        await query.answer("عملية غير معروفة")
        return AWAITING_PERMISSION_SELECTION
    except Exception as e:
        logging.error(f"Error in handle_permissions_callback: {e}")
        await query.answer("حدث خطأ في معالجة الطلب")
        return AWAITING_PERMISSION_SELECTION

# معالجة استجابة القائمة الرئيسية
async def manage_permissions_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """معالجة استجابة القائمة الرئيسية لإدارة الصلاحيات."""
    query = update.callback_query
    
    # إنشاء لوحة المفاتيح
    keyboard = [
        [InlineKeyboardButton(BTN_ADD_PERMISSION, callback_data=ADD_PERMISSION)],
        [InlineKeyboardButton(BTN_REMOVE_PERMISSION, callback_data=REMOVE_PERMISSION)],
        [InlineKeyboardButton(BTN_LIST_PERMISSIONS, callback_data=LIST_PERMISSIONS)],
        [InlineKeyboardButton(BTN_MAIN_MENU, callback_data="main_menu")]
    ]
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await query.edit_message_text(
        "🛡️ *نظام إدارة صلاحيات المستخدمين*\n\n"
        "يمكنك هنا إدارة صلاحيات المستخدمين غير المسؤولين.\n"
        "اختر إحدى العمليات التالية:",
        reply_markup=reply_markup,
        parse_mode='Markdown'
    )
    
    return AWAITING_PERMISSION_SELECTION

# إلغاء عملية إدارة الصلاحيات
async def cancel_permissions(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """إلغاء عملية إدارة الصلاحيات."""
    # مسح بيانات المستخدم
    if 'permission_user_id' in context.user_data:
        del context.user_data['permission_user_id']
    
    # إرسال رسالة الإلغاء
    await update.message.reply_text(
        "❌ تم إلغاء عملية إدارة الصلاحيات."
    )
    
    return ConversationHandler.END

# الحصول على معالج محادثة إدارة الصلاحيات
def get_permissions_management_handler():
    """إرجاع معالج المحادثة لإدارة الصلاحيات."""
    return ConversationHandler(
        entry_points=[CommandHandler("permissions", manage_permissions)],
        states={
            AWAITING_PERMISSION_SELECTION: [
                # استخدام معالج استدعاءات عام بدون قيود تعبيرات نمطية
                CallbackQueryHandler(handle_permissions_callback),
                CallbackQueryHandler(lambda u, c: ConversationHandler.END, pattern="^main_menu$")
            ],
            AWAITING_USER_ID: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, process_user_id_for_permission),
                # إضافة إمكانية إلغاء العملية في جميع الحالات
                CommandHandler("cancel", cancel_permissions)
            ]
        },
        fallbacks=[
            CommandHandler("cancel", cancel_permissions),
            CommandHandler("start", lambda u, c: ConversationHandler.END),
            # إضافة معالج عام للاستدعاءات كاحتياطي
            CallbackQueryHandler(handle_permissions_callback)
        ],
        name="permissions_conversation",
        # تفعيل الخيارات المتقدمة لتتبع الاستدعاءات
        per_message=True,
        per_chat=True,
        per_user=True,
        persistent=False
    )

# معالج للتحقق من معرف المستخدم - للتسهيل على المستخدمين
async def user_id_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """عرض معرف المستخدم."""
    user_id = update.effective_user.id
    first_name = update.effective_user.first_name
    
    await update.message.reply_text(
        f"👤 مرحباً {first_name}،\n\n"
        f"معرف المستخدم الخاص بك هو: `{user_id}`\n\n"
        "يمكنك مشاركة هذا المعرف مع المسؤول لإضافة صلاحيات خاصة لحسابك.",
        parse_mode='Markdown'
    )

# معالج عام للاستدعاءات خارج نظام المحادثة
async def handle_global_permissions_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """معالج عام لاستدعاءات إدارة الصلاحيات خارج نظام المحادثة."""
    logging.info("🔧 Handle global permissions callback activated")
    query = update.callback_query
    
    if not query:
        return
    
    callback_data = query.data
    
    # تسجيل بيانات الاستدعاء للتشخيص
    logging.info(f"Global permissions callback data: {callback_data}")
    
    # استدعاء معالج الصلاحيات الرئيسي لمعالجة البيانات
    try:
        await handle_permissions_callback(update, context)
    except Exception as e:
        logging.error(f"Error in global permissions callback: {e}")
        import traceback
        logging.error(traceback.format_exc())
        await query.answer("حدث خطأ أثناء معالجة طلب إدارة الصلاحيات. الرجاء المحاولة مجدداً.")
    
    return ConversationHandler.END

# الحصول على جميع معالجات الصلاحيات
def get_permissions_handlers():
    """إرجاع معالجات متعلقة بوظائف الصلاحيات."""
    
    # إضافة معالج عام للاستدعاءات خارج معالج المحادثة
    # هذا سيلتقط أي استدعاءات لم يتم التقاطها بواسطة معالج المحادثة
    general_permissions_callback_handler = CallbackQueryHandler(handle_global_permissions_callback)
    
    return [
        get_permissions_management_handler(),
        CommandHandler("id", user_id_command),
        general_permissions_callback_handler
    ]