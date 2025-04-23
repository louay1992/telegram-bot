"""
وحدة معالجة تصفية وتصنيف الإشعارات
"""
import logging
from datetime import datetime, timedelta
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    ContextTypes, CommandHandler, ConversationHandler,
    CallbackQueryHandler, MessageHandler, filters
)

import database as db
import strings as st
import utils

# تعريف حالات المحادثة
SHOW_FILTER_MENU, SHOW_DATE_FILTERS, SHOW_STATUS_FILTERS, SHOW_RESULTS = range(4)

async def filter_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """بدء عملية تصفية الإشعارات."""
    # التحقق من صلاحيات المستخدم
    if not db.is_admin(update.effective_user.id):
        await update.message.reply_text(st.NOT_ADMIN)
        return ConversationHandler.END
    
    # عرض قائمة خيارات التصفية
    await show_filter_menu(update, context)
    return SHOW_FILTER_MENU

async def show_filter_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """عرض قائمة خيارات التصفية."""
    keyboard = [
        [InlineKeyboardButton(st.FILTER_BY_DATE, callback_data="filter_date")],
        [InlineKeyboardButton(st.FILTER_BY_STATUS, callback_data="filter_status")],
        [InlineKeyboardButton(st.CANCEL_BUTTON, callback_data="filter_cancel")]
    ]
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    # إذا كان هناك استعلام، فقم بتحرير الرسالة
    if update.callback_query:
        await update.callback_query.edit_message_text(
            text=st.FILTER_MENU_TITLE,
            reply_markup=reply_markup
        )
    else:
        # وإلا قم بإرسال رسالة جديدة
        await update.message.reply_text(
            text=st.FILTER_MENU_TITLE,
            reply_markup=reply_markup
        )
    
    return SHOW_FILTER_MENU

async def handle_filter_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """معالجة ردود الاستعلام لقائمة التصفية."""
    query = update.callback_query
    await query.answer()
    
    callback_data = query.data
    
    if callback_data == "filter_date":
        await show_date_filters(update, context)
        return SHOW_DATE_FILTERS
    
    elif callback_data == "filter_status":
        await show_status_filters(update, context)
        return SHOW_STATUS_FILTERS
    
    elif callback_data == "filter_cancel":
        await query.edit_message_text(st.OPERATION_CANCELLED)
        return ConversationHandler.END
    
    # إذا كان الاستعلام غير معروف، عد إلى القائمة الرئيسية
    await show_filter_menu(update, context)
    return SHOW_FILTER_MENU

async def show_date_filters(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """عرض خيارات التصفية حسب التاريخ."""
    keyboard = [
        [InlineKeyboardButton(st.FILTER_TODAY, callback_data="date_today")],
        [InlineKeyboardButton(st.FILTER_THIS_WEEK, callback_data="date_week")],
        [InlineKeyboardButton(st.FILTER_THIS_MONTH, callback_data="date_month")],
        [InlineKeyboardButton(st.FILTER_ALL_TIME, callback_data="date_all")],
        [InlineKeyboardButton(st.FILTER_BACK, callback_data="filter_back")]
    ]
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    # التحقق إذا كان الاستدعاء من callback_query أو رسالة نصية
    if update.callback_query:
        await update.callback_query.edit_message_text(
            text=st.FILTER_BY_DATE,
            reply_markup=reply_markup
        )
    else:
        await update.message.reply_text(
            text=st.FILTER_BY_DATE,
            reply_markup=reply_markup
        )
    
    return SHOW_DATE_FILTERS

async def show_status_filters(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """عرض خيارات التصفية حسب الحالة."""
    keyboard = [
        [InlineKeyboardButton(st.FILTER_DELIVERED, callback_data="status_delivered")],
        [InlineKeyboardButton(st.FILTER_NOT_DELIVERED, callback_data="status_pending")],
        [InlineKeyboardButton(st.FILTER_REMINDER_SENT, callback_data="status_reminder")],
        [InlineKeyboardButton(st.FILTER_ALL_STATUS, callback_data="status_all")],
        [InlineKeyboardButton(st.FILTER_BACK, callback_data="filter_back")]
    ]
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    # التحقق إذا كان الاستدعاء من callback_query أو رسالة نصية
    if update.callback_query:
        await update.callback_query.edit_message_text(
            text=st.FILTER_BY_STATUS,
            reply_markup=reply_markup
        )
    else:
        await update.message.reply_text(
            text=st.FILTER_BY_STATUS,
            reply_markup=reply_markup
        )
    
    return SHOW_STATUS_FILTERS

async def handle_date_filter_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """معالجة ردود الاستعلام لتصفية التاريخ."""
    query = update.callback_query
    await query.answer()
    
    callback_data = query.data
    
    # الحصول على جميع الإشعارات
    all_notifications = db.get_all_notifications()
    
    # تصفية الإشعارات بناءً على التاريخ المحدد
    today = datetime.now()
    filtered_notifications = []
    filter_name = ""
    
    if callback_data == "date_today":
        # الإشعارات التي تم إنشاؤها اليوم
        today_start = today.replace(hour=0, minute=0, second=0, microsecond=0)
        
        filtered_notifications = [
            n for n in all_notifications 
            if datetime.fromisoformat(n['created_at']) >= today_start
        ]
        filter_name = st.FILTER_TODAY
        
    elif callback_data == "date_week":
        # الإشعارات التي تم إنشاؤها هذا الأسبوع
        week_start = today - timedelta(days=today.weekday())
        week_start = week_start.replace(hour=0, minute=0, second=0, microsecond=0)
        
        filtered_notifications = [
            n for n in all_notifications 
            if datetime.fromisoformat(n['created_at']) >= week_start
        ]
        filter_name = st.FILTER_THIS_WEEK
        
    elif callback_data == "date_month":
        # الإشعارات التي تم إنشاؤها هذا الشهر
        month_start = today.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        
        filtered_notifications = [
            n for n in all_notifications 
            if datetime.fromisoformat(n['created_at']) >= month_start
        ]
        filter_name = st.FILTER_THIS_MONTH
        
    elif callback_data == "date_all":
        # كل الإشعارات
        filtered_notifications = all_notifications
        filter_name = st.FILTER_ALL_TIME
        
    elif callback_data == "filter_back":
        # العودة إلى قائمة التصفية
        await show_filter_menu(update, context)
        return SHOW_FILTER_MENU
    
    # عرض نتائج التصفية
    await show_filter_results(update, context, filtered_notifications, filter_name)
    return SHOW_RESULTS

async def handle_status_filter_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """معالجة ردود الاستعلام لتصفية الحالة."""
    query = update.callback_query
    await query.answer()
    
    callback_data = query.data
    
    # الحصول على جميع الإشعارات
    all_notifications = db.get_all_notifications()
    
    # تصفية الإشعارات بناءً على الحالة المحددة
    filtered_notifications = []
    filter_name = ""
    
    if callback_data == "status_delivered":
        # الإشعارات التي تم تسليمها
        filtered_notifications = [
            n for n in all_notifications 
            if n.get('delivered', False)
        ]
        filter_name = st.FILTER_DELIVERED
        
    elif callback_data == "status_pending":
        # الإشعارات التي لم يتم تسليمها بعد
        filtered_notifications = [
            n for n in all_notifications 
            if not n.get('delivered', False)
        ]
        filter_name = st.FILTER_NOT_DELIVERED
        
    elif callback_data == "status_reminder":
        # الإشعارات التي تم إرسال تذكير لها
        filtered_notifications = [
            n for n in all_notifications 
            if n.get('reminder_sent', False)
        ]
        filter_name = st.FILTER_REMINDER_SENT
        
    elif callback_data == "status_all":
        # كل الإشعارات
        filtered_notifications = all_notifications
        filter_name = st.FILTER_ALL_STATUS
        
    elif callback_data == "filter_back":
        # العودة إلى قائمة التصفية
        await show_filter_menu(update, context)
        return SHOW_FILTER_MENU
    
    # عرض نتائج التصفية
    await show_filter_results(update, context, filtered_notifications, filter_name)
    return SHOW_RESULTS

async def show_filter_results(update: Update, context: ContextTypes.DEFAULT_TYPE, filtered_notifications, filter_name):
    """عرض نتائج التصفية."""
    
    if not filtered_notifications:
        # التحقق إذا كان الاستدعاء من callback_query أو رسالة نصية
        if update.callback_query:
            await update.callback_query.edit_message_text(
                text=st.FILTER_NO_RESULTS,
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton(st.FILTER_BACK, callback_data="results_back")]
                ])
            )
        else:
            await update.message.reply_text(
                text=st.FILTER_NO_RESULTS,
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton(st.FILTER_BACK, callback_data="results_back")]
                ])
            )
        return
    
    # ترتيب الإشعارات حسب تاريخ الإنشاء (الأحدث أولاً)
    filtered_notifications.sort(
        key=lambda x: datetime.fromisoformat(x['created_at']), 
        reverse=True
    )
    
    # تخزين النتائج في سياق المستخدم لاستخدامها في التنقل
    context.user_data['filtered_notifications'] = filtered_notifications
    context.user_data['current_page'] = 0
    context.user_data['filter_name'] = filter_name
    
    # عرض الصفحة الأولى من النتائج
    await display_notifications_page(update, context)

async def display_notifications_page(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """عرض صفحة من الإشعارات المصفاة."""
    
    # استعادة البيانات من سياق المستخدم
    filtered_notifications = context.user_data.get('filtered_notifications', [])
    current_page = context.user_data.get('current_page', 0)
    filter_name = context.user_data.get('filter_name', "")
    
    # التأكد من أن current_page ضمن النطاق الصحيح
    if current_page < 0:
        current_page = 0
    
    # حساب العدد الإجمالي للصفحات (5 إشعارات في الصفحة)
    page_size = 5
    total_pages = (len(filtered_notifications) + page_size - 1) // page_size
    
    if current_page >= total_pages:
        current_page = total_pages - 1
    
    # تحديث الصفحة الحالية في سياق المستخدم
    context.user_data['current_page'] = current_page
    
    # استخراج الإشعارات للصفحة الحالية
    start_idx = current_page * page_size
    end_idx = min(start_idx + page_size, len(filtered_notifications))
    page_notifications = filtered_notifications[start_idx:end_idx]
    
    # بناء نص الرسالة
    header = st.FILTER_RESULTS_HEADER.format(count=len(filtered_notifications))
    header += st.FILTER_APPLIED.format(filter_name=filter_name) + "\n\n"
    
    notifications_text = ""
    for i, notification in enumerate(page_notifications, start=start_idx + 1):
        # توليد نص ملخص للإشعار
        customer_name = notification.get('customer_name', 'غير معروف')
        phone_number = notification.get('phone_number', 'غير معروف')
        created_at = utils.format_datetime(notification.get('created_at', ''))
        
        status = "✅ تم الاستلام" if notification.get('delivered', False) else "⏳ قيد الانتظار"
        reminder = "🔔 تم إرسال تذكير" if notification.get('reminder_sent', False) else ""
        
        notifications_text += f"{i}. *{customer_name}* - {phone_number}\n"
        notifications_text += f"   📅 {created_at}\n"
        notifications_text += f"   {status} {reminder}\n"
        notifications_text += "   --------------------------\n"
    
    # إضافة معلومات الصفحة
    page_info = f"📄 الصفحة {current_page + 1}/{total_pages}"
    
    # بناء لوحة المفاتيح
    keyboard = []
    
    # أزرار التنقل بين الصفحات
    navigation_buttons = []
    
    if current_page > 0:
        navigation_buttons.append(
            InlineKeyboardButton("◀️ السابق", callback_data="results_prev")
        )
    
    if current_page < total_pages - 1:
        navigation_buttons.append(
            InlineKeyboardButton("▶️ التالي", callback_data="results_next")
        )
    
    if navigation_buttons:
        keyboard.append(navigation_buttons)
    
    # أزرار الإجراءات
    keyboard.append([
        InlineKeyboardButton("🔄 تصفية أخرى", callback_data="results_new_filter")
    ])
    
    keyboard.append([
        InlineKeyboardButton(st.FILTER_BACK, callback_data="results_back")
    ])
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    # إرسال أو تحديث الرسالة
    message_text = header + notifications_text + "\n" + page_info
    
    try:
        # التحقق إذا كان الاستدعاء من callback_query أو رسالة نصية
        if update.callback_query:
            await update.callback_query.edit_message_text(
                text=message_text,
                reply_markup=reply_markup,
                parse_mode='Markdown'
            )
        else:
            await update.message.reply_text(
                text=message_text,
                reply_markup=reply_markup,
                parse_mode='Markdown'
            )
    except Exception as e:
        logging.error(f"Error displaying notifications page: {e}")
        # في حالة حدوث خطأ (مثل رسالة كبيرة جدًا)، جرب بدون parse_mode
        try:
            if update.callback_query:
                await update.callback_query.edit_message_text(
                    text=header + notifications_text + "\n" + page_info,
                    reply_markup=reply_markup
                )
            else:
                await update.message.reply_text(
                    text=header + notifications_text + "\n" + page_info,
                    reply_markup=reply_markup
                )
        except Exception as e2:
            logging.error(f"Error displaying notifications page (without parse_mode): {e2}")
            error_message = "⚠️ حدث خطأ أثناء عرض النتائج. الرجاء المحاولة مرة أخرى."
            error_markup = InlineKeyboardMarkup([
                [InlineKeyboardButton(st.FILTER_BACK, callback_data="results_back")]
            ])
            
            if update.callback_query:
                await update.callback_query.edit_message_text(
                    text=error_message,
                    reply_markup=error_markup
                )
            else:
                await update.message.reply_text(
                    text=error_message,
                    reply_markup=error_markup
                )

async def handle_results_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """معالجة ردود الاستعلام لنتائج التصفية."""
    query = update.callback_query
    await query.answer()
    
    callback_data = query.data
    
    if callback_data == "results_next":
        # الانتقال إلى الصفحة التالية
        context.user_data['current_page'] += 1
        await display_notifications_page(update, context)
        return SHOW_RESULTS
    
    elif callback_data == "results_prev":
        # الانتقال إلى الصفحة السابقة
        context.user_data['current_page'] -= 1
        await display_notifications_page(update, context)
        return SHOW_RESULTS
    
    elif callback_data == "results_new_filter":
        # بدء تصفية جديدة
        await show_filter_menu(update, context)
        return SHOW_FILTER_MENU
    
    elif callback_data == "results_back":
        # العودة إلى قائمة التصفية
        await show_filter_menu(update, context)
        return SHOW_FILTER_MENU
    
    # إذا كان الاستعلام غير معروف، ابق في نفس الحالة
    return SHOW_RESULTS

async def handle_date_filter_button(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """معالجة زر تصفية التاريخ من لوحة المفاتيح الرئيسية."""
    # تعيين معلومات callback_query بشكل اصطناعي
    context.user_data['temp_callback'] = {'data': 'filter_date'}
    await filter_command(update, context)
    await show_date_filters(update, context)
    return SHOW_DATE_FILTERS

async def handle_status_filter_button(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """معالجة زر تصفية الحالة من لوحة المفاتيح الرئيسية."""
    # تعيين معلومات callback_query بشكل اصطناعي
    context.user_data['temp_callback'] = {'data': 'filter_status'}
    await filter_command(update, context)
    await show_status_filters(update, context)
    return SHOW_STATUS_FILTERS

def get_filter_handler():
    """إرجاع معالج المحادثة لتصفية الإشعارات."""
    filter_conv_handler = ConversationHandler(
        entry_points=[
            CommandHandler(st.FILTER_COMMAND, filter_command),
            # إضافة معالج رسائل لاستقبال النص من أزرار لوحة المفاتيح
            MessageHandler(filters.TEXT & filters.Regex(f"^🔍 تصفية الإشعارات$"), filter_command),
            MessageHandler(filters.TEXT & filters.Regex(f"^{st.FILTER_BY_DATE}$"), handle_date_filter_button),
            MessageHandler(filters.TEXT & filters.Regex(f"^{st.FILTER_BY_STATUS}$"), handle_status_filter_button)
        ],
        states={
            SHOW_FILTER_MENU: [
                CallbackQueryHandler(handle_filter_callback, pattern=r'^filter_')
            ],
            SHOW_DATE_FILTERS: [
                CallbackQueryHandler(handle_date_filter_callback, pattern=r'^date_|^filter_back$')
            ],
            SHOW_STATUS_FILTERS: [
                CallbackQueryHandler(handle_status_filter_callback, pattern=r'^status_|^filter_back$')
            ],
            SHOW_RESULTS: [
                CallbackQueryHandler(handle_results_callback, pattern=r'^results_')
            ]
        },
        fallbacks=[CommandHandler('cancel', filter_command)]
    )
    
    return filter_conv_handler

def get_filter_handlers():
    """إرجاع المعالجات المتعلقة بوظائف التصفية."""
    filter_handler = get_filter_handler()
    
    return [
        filter_handler
    ]