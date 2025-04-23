import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, ReplyKeyboardMarkup, ReplyKeyboardRemove
from telegram.ext import (
    CommandHandler, MessageHandler, CallbackQueryHandler,
    ContextTypes, filters, ConversationHandler
)

import database as db
import strings as st
import utils
import input_validator as validator

# Search conversation states
AWAITING_SEARCH_QUERY = 0

async def search_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /search command to find notifications by customer name."""
    # تحقق مما إذا كان المستخدم مسؤولاً أو لديه صلاحية البحث بالاسم
    import database as db
    import config
    user_id = update.effective_user.id
    
    if not db.is_admin(user_id) and not db.has_permission(user_id, config.PERMISSION_SEARCH_BY_NAME):
        await update.message.reply_text("⚠️ البحث بالاسم متاح فقط للمسؤولين والمستخدمين المخولين. الرجاء استخدام البحث برقم الهاتف.")
        return ConversationHandler.END
    
    # تعيين نوع البحث في بيانات المستخدم
    context.user_data['search_type'] = 'اسم'
    
    # If there's a query after the command, process it immediately
    if context.args:
        query = ' '.join(context.args)
        await process_name_search(update, context, query)
        return ConversationHandler.END
    
    # Otherwise, prompt for search query
    keyboard = [
        [st.MAIN_MENU_BUTTON]
    ]
    reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
    await update.message.reply_text(st.SEARCH_PROMPT, reply_markup=reply_markup)
    return AWAITING_SEARCH_QUERY

async def phone_search_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /phone command to find notifications by phone number."""
    # تعيين نوع البحث في بيانات المستخدم
    context.user_data['search_type'] = 'هاتف'
    
    # If there's a query after the command, process it immediately
    if context.args:
        query = ' '.join(context.args)
        await process_phone_search(update, context, query)
        return ConversationHandler.END
    
    # Otherwise, prompt for phone number
    keyboard = [
        [st.MAIN_MENU_BUTTON]
    ]
    reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
    await update.message.reply_text(st.PHONE_SEARCH_PROMPT, reply_markup=reply_markup)
    return AWAITING_SEARCH_QUERY

async def received_search_query(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Process the received search query."""
    query = update.message.text
    
    logging.info(f"Consulta de búsqueda recibida: '{query}' - longitud: {len(query)}")
    
    # التحقق من زر القائمة الرئيسية
    if query == st.MAIN_MENU_BUTTON:
        # العودة إلى القائمة الرئيسية
        from bot import main_menu_command
        await main_menu_command(update, context)
        return ConversationHandler.END
    
    if not query or query.strip() == "":
        await update.message.reply_text(st.SEARCH_NO_QUERY)
        return ConversationHandler.END
    
    # تحديد نوع البحث استنادًا إلى المعالج الذي بدأ المحادثة
    search_type = context.user_data.get('search_type', 'اسم')
    logging.info(f"نوع البحث: {search_type}")
    
    if search_type == 'اسم':
        # تحقق مما إذا كان المستخدم مسؤولاً أو لديه صلاحية البحث بالاسم
        import database as db
        import config
        user_id = update.effective_user.id
        
        if not db.is_admin(user_id) and not db.has_permission(user_id, config.PERMISSION_SEARCH_BY_NAME):
            await update.message.reply_text("⚠️ البحث بالاسم متاح فقط للمسؤولين والمستخدمين المخولين. الرجاء استخدام البحث برقم الهاتف.")
            return ConversationHandler.END
            
        # Simple validation - only check if empty
        if not query.strip():
            await update.message.reply_text(st.INVALID_NAME)
            # Stay in the conversation to allow user to correct input
            return AWAITING_SEARCH_QUERY
        
        logging.info(f"Valid query, processing name search: '{query}'")
        await process_name_search(update, context, query)
    else:  # phone
        # تسجيل معلومات رقم الهاتف الأصلي للمساعدة في التشخيص
        logging.info(f"Original phone input for search: '{query}'")
        
        # استخدام مدقق أرقام الهواتف مع تنسيق محسن
        is_valid, formatted_phone = validator.is_valid_phone(query)
        logging.info(f"Phone formatted for search: '{formatted_phone}'")
        
        if not is_valid:
            await update.message.reply_text(st.INVALID_PHONE)
            # Stay in the conversation to allow user to correct input
            return AWAITING_SEARCH_QUERY
        
        logging.info(f"Valid phone number, processing search: '{formatted_phone}'")
        await process_phone_search(update, context, formatted_phone)
    
    return ConversationHandler.END

async def process_name_search(update: Update, context: ContextTypes.DEFAULT_TYPE, query):
    """Process a search by customer name."""
    if not query or not query.strip():
        await update.message.reply_text(st.SEARCH_NO_QUERY)
        return
    
    # No additional validation needed - accept any non-empty string
    try:
        results = db.search_notifications_by_name(query)
        await display_search_results(update, context, results, query)
    except Exception as e:
        logging.error(f"Error in name search: {e}")
        await update.message.reply_text(st.SEARCH_ERROR)

async def process_phone_search(update: Update, context: ContextTypes.DEFAULT_TYPE, query):
    """Process a search by phone number."""
    if not query:
        await update.message.reply_text(st.SEARCH_NO_QUERY)
        return
    
    # تسجيل معلومات رقم الهاتف الأصلي للمساعدة في التشخيص
    logging.info(f"Processing phone search with query: '{query}'")
    
    # Use our improved phone validator with better formatting
    is_valid, formatted_phone = validator.is_valid_phone(query)
    logging.info(f"Formatted phone for database search: '{formatted_phone}'")
    
    if not is_valid:
        # This will only happen if the phone has no digits at all
        await update.message.reply_text(st.INVALID_PHONE)
        return
    
    try:
        # استخدام رقم الهاتف المنسق (مع رمز البلد) للبحث في قاعدة البيانات
        results = db.search_notifications_by_phone(formatted_phone)
        await display_search_results(update, context, results, formatted_phone)
    except Exception as e:
        logging.error(f"Error in phone search: {e}")
        await update.message.reply_text(st.SEARCH_ERROR)

async def display_search_results(update: Update, context: ContextTypes.DEFAULT_TYPE, results, query):
    """Display search results to the user."""
    if not results:
        await update.message.reply_text(f"{st.SEARCH_NO_RESULTS} '{query}'")
        return
    
    # Set up pagination
    page = 1
    keyboard = utils.create_paginated_keyboard(results, page, "search")
    
    # حفظ سجل البحث
    try:
        user_id = update.effective_user.id
        username = update.effective_user.username or update.effective_user.first_name or "مستخدم"
        
        # تحديد نوع البحث (اسم أو هاتف) بشكل صحيح
        search_type = context.user_data.get('search_type', 'phone')
        
        if search_type == 'اسم':
            search_type = 'name'
        elif search_type == 'هاتف':
            search_type = 'phone'
            
        logging.info(f"حفظ سجل بحث جديد - المستخدم: {user_id}, المصطلح: '{query}', النوع: {search_type}, عدد النتائج: {len(results)}")
        
        # التحقق من وجود معرفات في النتائج
        has_ids = all('id' in r for r in results) if results else False
        if not has_ids and results:
            logging.warning(f"نتائج البحث تفتقد لمعرفات الإشعارات! البحث: '{query}'")
            
        # طباعة مفاتيح النتيجة الأولى للمساعدة في التشخيص
        if results:
            first_keys = list(results[0].keys())
            logging.info(f"مفاتيح أول نتيجة بحث: {first_keys}")
            
        from search_history_functions import add_search_record
        logging.info(f"⚠️ قبل إضافة سجل البحث - المستخدم: {user_id}, المصطلح: '{query}', النوع: {search_type}, النتائج: {len(results)}")
        
        try:
            # طباعة مفاتيح النتيجة الأولى بشكل مفصل للتشخيص
            if results and len(results) > 0:
                first_result = results[0]
                all_keys = list(first_result.keys())
                logging.info(f"🔑 مفاتيح أول نتيجة: {all_keys}")
                for key in all_keys:
                    logging.info(f"   - {key}: {first_result.get(key)}")
            
            # محاولة إضافة سجل البحث
            success = add_search_record(user_id, username, query, search_type, results)
            
            if success:
                logging.info(f"✅ تم حفظ سجل البحث بنجاح للمستخدم {user_id} - المصطلح: '{query}'")
            else:
                logging.error(f"❌ فشل في حفظ سجل البحث للمستخدم {user_id} - المصطلح: '{query}'")
        except Exception as search_record_error:
            logging.error(f"🔴 استثناء عند محاولة إضافة سجل البحث: {search_record_error}")
            import traceback
            logging.error(traceback.format_exc())
    except Exception as e:
        logging.error(f"خطأ في حفظ سجل البحث: {e}")
        import traceback
        logging.error(traceback.format_exc())
    
    await update.message.reply_text(
        f"{st.SEARCH_RESULTS} '{query}'\n"
        f"تم العثور على {len(results)} نتيجة:",
        reply_markup=keyboard
    )

async def handle_search_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle callback queries for search pagination and viewing results."""
    query = update.callback_query
    await query.answer()
    
    data = query.data.split("_")
    
    if data[0] != "search":
        return
    
    if data[1] == "page":
        # Handle pagination
        page = int(data[2])
        
        # We need to recreate the search results
        # This is a bit inefficient but simplifies implementation
        original_text = query.message.text
        search_query = original_text.split("'")[1] if "'" in original_text else ""
        
        # تحقق من نوع البحث ومن صلاحيات المستخدم
        is_name_search = "اسم" in original_text.lower()
        
        # تحقق مما إذا كان المستخدم مسؤولاً أو لديه صلاحية البحث بالاسم
        import config
        user_id = update.effective_user.id
        if is_name_search and not db.is_admin(user_id) and not db.has_permission(user_id, config.PERMISSION_SEARCH_BY_NAME):
            await query.message.reply_text("⚠️ البحث بالاسم متاح فقط للمسؤولين والمستخدمين المخولين لأسباب أمنية.")
            return
            
        if is_name_search:
            results = db.search_notifications_by_name(search_query)
        else:
            results = db.search_notifications_by_phone(search_query)
        
        keyboard = utils.create_paginated_keyboard(results, page, "search")
        
        await query.edit_message_text(
            query.message.text,
            reply_markup=keyboard
        )
    
    elif data[1] == "view":
        # View notification details
        notification_id = data[2]
        
        # الحصول على كل الإشعارات ثم البحث عن الإشعار بالمعرف مباشرة
        all_notifications = db.get_all_notifications()
        notification = next((n for n in all_notifications if n["id"] == notification_id), None)
        
        if not notification:
            logging.error(f"لم يتم العثور على الإشعار بالمعرف {notification_id}")
            await query.message.reply_text("⚠️ لم يتم العثور على الإشعار!")
            return
        
        # Display notification details
        details = utils.format_notification_details(notification)
        
        # Get the image
        image_data = db.get_image(notification_id)
        
        if image_data:
            await utils.send_image_with_caption(update, context, photo=image_data, caption=details)
        else:
            await query.message.reply_text(details + "\n\n⚠️ الصورة غير متوفرة!")

def get_search_handlers():
    """Return handlers related to search functionality."""
    name_search_handler = ConversationHandler(
        entry_points=[CommandHandler('search', search_command)],
        states={
            AWAITING_SEARCH_QUERY: [MessageHandler(filters.TEXT & ~filters.COMMAND, received_search_query)]
        },
        fallbacks=[CommandHandler('cancel', lambda u, c: ConversationHandler.END)],
        name="name_search",
        persistent=False
    )
    
    phone_search_handler = ConversationHandler(
        entry_points=[CommandHandler('phone', phone_search_command)],
        states={
            AWAITING_SEARCH_QUERY: [MessageHandler(filters.TEXT & ~filters.COMMAND, received_search_query)]
        },
        fallbacks=[CommandHandler('cancel', lambda u, c: ConversationHandler.END)],
        name="phone_search",
        persistent=False
    )
    
    return [
        name_search_handler,
        phone_search_handler,
        CallbackQueryHandler(handle_search_callback, pattern=r'^search_')
    ]
