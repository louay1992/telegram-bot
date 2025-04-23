"""
معالجات لميزة سجلات البحث السابقة للمستخدم
"""
import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    ContextTypes, ConversationHandler, CommandHandler,
    CallbackQueryHandler, MessageHandler, filters
)
import utils
import db_manager as db
import strings as st
from search_history_functions import (
    add_search_record, get_user_search_history,
    get_search_record_by_id, delete_search_record
)

# حالات المحادثة
VIEWING_HISTORY = 1
CONFIRMING_DELETE = 2
SHARING_OPTIONS = 3

async def view_search_history(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    عرض سجلات البحث السابقة للمستخدم
    """
    user_id = update.effective_user.id
    
    # التحقق من وجود سجلات بحث للمستخدم
    search_records = get_user_search_history(user_id)
    
    if not search_records:
        await update.message.reply_text(
            "ليس لديك أي سجلات بحث سابقة.\n"
            "استخدم وظيفة البحث للعثور على إشعارات وسيتم حفظها تلقائياً هنا."
        )
        return ConversationHandler.END
    
    # تجميع السجلات حسب اسم العميل
    records_by_customer = {}
    for record in search_records:
        if 'notifications' not in record or not record['notifications']:
            continue
            
        for notification in record['notifications']:
            customer_name = notification['customer_name']
            
            if customer_name not in records_by_customer:
                records_by_customer[customer_name] = []
                
            if record not in records_by_customer[customer_name]:
                records_by_customer[customer_name].append(record)
    
    # إنشاء لوحة المفاتيح للزبائن
    keyboard = []
    for customer_name, records in records_by_customer.items():
        # استخدام اسم العميل وعدد السجلات في النص
        button_text = f"{customer_name} ({len(records)})"
        keyboard.append([InlineKeyboardButton(
            button_text, 
            callback_data=f"search_history_customer_{customer_name}"
        )])
    
    # إضافة زر العودة
    keyboard.append([InlineKeyboardButton("🔙 عودة للقائمة الرئيسية", callback_data="search_history_back")])
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.message.reply_text(
        "📋 سجلات البحث السابقة\n"
        "اختر اسم العميل لعرض سجلات البحث المرتبطة به:",
        reply_markup=reply_markup
    )
    
    return VIEWING_HISTORY

async def handle_history_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    معالجة استعلامات الاستجابة لسجلات البحث
    """
    query = update.callback_query
    await query.answer()
    
    user_id = update.effective_user.id
    callback_data = query.data
    
    if callback_data == "search_history_back":
        # العودة للقائمة الرئيسية
        await query.message.reply_text("تم العودة إلى القائمة الرئيسية.")
        return ConversationHandler.END
    
    elif callback_data.startswith("search_history_customer_"):
        # استخراج اسم العميل
        customer_name = callback_data.replace("search_history_customer_", "")
        
        # الحصول على سجلات البحث للمستخدم
        search_records = get_user_search_history(user_id)
        
        # تصفية السجلات حسب اسم العميل
        customer_records = []
        for record in search_records:
            if 'notifications' in record and record['notifications']:
                for notification in record['notifications']:
                    if notification['customer_name'] == customer_name and record not in customer_records:
                        customer_records.append(record)
        
        if not customer_records:
            await query.message.reply_text(f"لا توجد سجلات بحث لـ {customer_name}")
            return VIEWING_HISTORY
        
        # إنشاء لوحة المفاتيح للسجلات
        keyboard = []
        for i, record in enumerate(customer_records):
            search_type = "الاسم" if record['search_type'] == 'name' else "رقم الهاتف"
            record_date = record['created_at'].split('T')[0] if 'created_at' in record else ""
            button_text = f"🔍 {record['search_term']} ({search_type}) - {record_date}"
            
            keyboard.append([InlineKeyboardButton(
                button_text, 
                callback_data=f"search_record_{record['id']}"
            )])
        
        # إضافة زر العودة
        keyboard.append([InlineKeyboardButton("🔙 عودة لقائمة العملاء", callback_data="search_history_back_to_customers")])
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await query.message.reply_text(
            f"📋 سجلات البحث لـ {customer_name}\n"
            "اختر سجل بحث لعرض التفاصيل والخيارات:",
            reply_markup=reply_markup
        )
        
        return VIEWING_HISTORY
    
    elif callback_data == "search_history_back_to_customers":
        # العودة لقائمة العملاء
        return await view_search_history(update, context)
    
    elif callback_data.startswith("search_record_"):
        # استخراج معرف السجل
        record_id = int(callback_data.replace("search_record_", ""))
        
        # الحصول على بيانات السجل
        record = get_search_record_by_id(record_id)
        
        if not record:
            await query.message.reply_text("لم يتم العثور على سجل البحث المطلوب.")
            return VIEWING_HISTORY
        
        # تخزين معرف السجل في بيانات المحادثة
        context.user_data['current_record_id'] = record_id
        
        # إعداد نص الرسالة
        search_type = "الاسم" if record['search_type'] == 'name' else "رقم الهاتف"
        message_text = (
            f"📋 تفاصيل سجل البحث\n"
            f"مصطلح البحث: {record['search_term']}\n"
            f"نوع البحث: {search_type}\n"
            f"عدد النتائج: {record['results_count']}\n"
            f"تاريخ البحث: {record['created_at'].split('T')[0] if 'created_at' in record else 'غير معروف'}\n\n"
            f"الإشعارات المرتبطة:"
        )
        
        # إضافة معلومات الإشعارات
        if 'notifications' in record and record['notifications']:
            for i, notification in enumerate(record['notifications'], 1):
                status = "✅ تم التسليم" if notification['is_delivered'] else "⏳ قيد الانتظار"
                message_text += f"\n{i}. {notification['customer_name']} - {notification['phone_number']} ({status})"
        else:
            message_text += "\nلا توجد إشعارات مرتبطة."
        
        # إنشاء أزرار الخيارات
        keyboard = [
            [
                InlineKeyboardButton("🔄 تأكيد الاستلام", callback_data=f"search_confirm_delivery_{record_id}"),
                InlineKeyboardButton("🔗 مشاركة", callback_data=f"search_share_{record_id}")
            ],
            [
                InlineKeyboardButton("🗑️ حذف السجل", callback_data=f"search_delete_{record_id}"),
                InlineKeyboardButton("🔙 عودة", callback_data="search_history_back_to_records")
            ]
        ]
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await query.message.reply_text(message_text, reply_markup=reply_markup)
        
        return VIEWING_HISTORY
    
    elif callback_data.startswith("search_confirm_delivery_"):
        # استخراج معرف السجل
        record_id = int(callback_data.replace("search_confirm_delivery_", ""))
        
        # الحصول على بيانات السجل
        record = get_search_record_by_id(record_id)
        
        if not record or 'notifications' not in record or not record['notifications']:
            await query.message.reply_text("لا توجد إشعارات مرتبطة بهذا السجل لتأكيد الاستلام.")
            return VIEWING_HISTORY
        
        # إنشاء أزرار للإشعارات
        keyboard = []
        for notification in record['notifications']:
            if not notification['is_delivered']:  # عرض فقط الإشعارات التي لم يتم تسليمها
                status = "⏳ قيد الانتظار"
                button_text = f"{notification['customer_name']} - {status}"
                keyboard.append([InlineKeyboardButton(
                    button_text, 
                    callback_data=f"confirm_delivery_{notification['id']}"
                )])
        
        if not keyboard:
            await query.message.reply_text("جميع الإشعارات في هذا السجل تم تسليمها بالفعل.")
            return VIEWING_HISTORY
        
        # إضافة زر العودة
        keyboard.append([InlineKeyboardButton("🔙 عودة", callback_data=f"search_record_{record_id}")])
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await query.message.reply_text(
            "اختر الإشعار لتأكيد استلامه:",
            reply_markup=reply_markup
        )
        
        return VIEWING_HISTORY
    
    elif callback_data.startswith("search_share_"):
        # استخراج معرف السجل
        record_id = int(callback_data.replace("search_share_", ""))
        context.user_data['current_record_id'] = record_id
        
        # إنشاء أزرار المشاركة
        keyboard = [
            [
                InlineKeyboardButton("📱 واتساب", callback_data="share_whatsapp"),
                InlineKeyboardButton("📲 تلغرام", callback_data="share_telegram")
            ],
            [
                InlineKeyboardButton("🔙 عودة", callback_data=f"search_record_{record_id}")
            ]
        ]
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await query.message.reply_text(
            "اختر طريقة المشاركة:",
            reply_markup=reply_markup
        )
        
        return SHARING_OPTIONS
    
    elif callback_data.startswith("search_delete_"):
        # استخراج معرف السجل
        record_id = int(callback_data.replace("search_delete_", ""))
        context.user_data['record_to_delete'] = record_id
        
        # طلب تأكيد الحذف
        keyboard = [
            [
                InlineKeyboardButton("✅ نعم، حذف", callback_data="confirm_delete"),
                InlineKeyboardButton("❌ لا، إلغاء", callback_data=f"search_record_{record_id}")
            ]
        ]
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await query.message.reply_text(
            "هل أنت متأكد من حذف سجل البحث هذا؟\n"
            "هذا الإجراء لا يمكن التراجع عنه.",
            reply_markup=reply_markup
        )
        
        return CONFIRMING_DELETE
    
    elif callback_data == "search_history_back_to_records":
        # الرجوع إلى قائمة السجلات
        # الحصول على اسم العميل من آخر سجل تم عرضه
        record_id = context.user_data.get('current_record_id')
        if record_id:
            record = get_search_record_by_id(record_id)
            if record and 'notifications' in record and record['notifications']:
                customer_name = record['notifications'][0]['customer_name']
                # إعادة توجيه إلى استعلام عرض سجلات العميل
                update.callback_query.data = f"search_history_customer_{customer_name}"
                return await handle_history_callback(update, context)
        
        # إذا لم تتمكن من تحديد العميل، ارجع إلى قائمة العملاء
        return await view_search_history(update, context)
    
    return VIEWING_HISTORY

async def handle_sharing_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    معالجة استعلامات المشاركة
    """
    query = update.callback_query
    await query.answer()
    
    callback_data = query.data
    record_id = context.user_data.get('current_record_id')
    
    if not record_id:
        await query.message.reply_text("حدث خطأ. يرجى المحاولة مرة أخرى.")
        return ConversationHandler.END
    
    record = get_search_record_by_id(record_id)
    
    if not record:
        await query.message.reply_text("لم يتم العثور على سجل البحث.")
        return ConversationHandler.END
    
    if callback_data == "share_whatsapp":
        # إنشاء رابط مشاركة واتساب
        share_text = f"سجل بحث عن: {record['search_term']}"
        
        if 'notifications' in record and record['notifications']:
            share_text += "\nالإشعارات المرتبطة:\n"
            for i, notification in enumerate(record['notifications'], 1):
                status = "✅ تم التسليم" if notification['is_delivered'] else "⏳ قيد الانتظار"
                share_text += f"{i}. {notification['customer_name']} - {notification['phone_number']} ({status})\n"
        
        whatsapp_link = f"https://wa.me/?text={utils.url_encode(share_text)}"
        
        keyboard = [
            [InlineKeyboardButton("📱 فتح واتساب", url=whatsapp_link)],
            [InlineKeyboardButton("🔙 عودة", callback_data=f"search_record_{record_id}")]
        ]
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await query.message.reply_text(
            "اضغط على الزر أدناه لمشاركة سجل البحث عبر واتساب:",
            reply_markup=reply_markup
        )
        
        return VIEWING_HISTORY
    
    elif callback_data == "share_telegram":
        # إنشاء رسالة للمشاركة عبر تلغرام
        share_text = f"سجل بحث عن: {record['search_term']}\n"
        
        if 'notifications' in record and record['notifications']:
            share_text += "\nالإشعارات المرتبطة:\n"
            for i, notification in enumerate(record['notifications'], 1):
                status = "✅ تم التسليم" if notification['is_delivered'] else "⏳ قيد الانتظار"
                share_text += f"{i}. {notification['customer_name']} - {notification['phone_number']} ({status})\n"
        
        await query.message.reply_text(
            "انسخ النص التالي ومشاركته عبر تلغرام:\n\n" + share_text,
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("🔙 عودة", callback_data=f"search_record_{record_id}")]
            ])
        )
        
        return VIEWING_HISTORY
    
    return VIEWING_HISTORY

async def handle_delete_confirmation(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    معالجة تأكيد حذف سجل البحث
    """
    query = update.callback_query
    await query.answer()
    
    if query.data == "confirm_delete":
        record_id = context.user_data.get('record_to_delete')
        user_id = update.effective_user.id
        
        if not record_id:
            await query.message.reply_text("حدث خطأ. يرجى المحاولة مرة أخرى.")
            return ConversationHandler.END
        
        # حذف السجل
        if delete_search_record(record_id, user_id):
            await query.message.reply_text("تم حذف سجل البحث بنجاح.")
        else:
            await query.message.reply_text("فشل حذف سجل البحث. يرجى المحاولة مرة أخرى.")
        
        # العودة إلى قائمة سجلات البحث
        return await view_search_history(update, context)
    
    # إلغاء الحذف والعودة إلى تفاصيل السجل
    record_id = context.user_data.get('record_to_delete')
    update.callback_query.data = f"search_record_{record_id}"
    
    return await handle_history_callback(update, context)

def get_search_history_handler():
    """
    إنشاء معالج المحادثة لسجلات البحث
    """
    return ConversationHandler(
        entry_points=[
            CommandHandler('search_history', view_search_history),
            MessageHandler(filters.Regex(r'سجلات البحث السابقة'), view_search_history)
        ],
        states={
            VIEWING_HISTORY: [
                CallbackQueryHandler(handle_history_callback, pattern=r'^search_')
            ],
            CONFIRMING_DELETE: [
                CallbackQueryHandler(handle_delete_confirmation, pattern=r'^confirm_delete$'),
                CallbackQueryHandler(handle_history_callback, pattern=r'^search_')
            ],
            SHARING_OPTIONS: [
                CallbackQueryHandler(handle_sharing_callback, pattern=r'^share_'),
                CallbackQueryHandler(handle_history_callback, pattern=r'^search_')
            ]
        },
        fallbacks=[
            CommandHandler('cancel', lambda u, c: ConversationHandler.END),
            MessageHandler(filters.Regex(r'إلغاء|الغاء'), lambda u, c: ConversationHandler.END)
        ],
        name="search_history_conversation",
        persistent=False
    )