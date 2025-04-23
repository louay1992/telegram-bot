"""
نظام البحث المتقدم للمسؤولين
"""
import logging
import re
from typing import List, Dict, Any, Optional

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, ReplyKeyboardMarkup, ReplyKeyboardRemove
from telegram.ext import (
    CommandHandler, MessageHandler, CallbackQueryHandler,
    ContextTypes, filters, ConversationHandler
)

import database as db
import strings as st
import utils
import input_validator as validator
from search_history_functions import add_search_record, get_user_search_history

# حالات المحادثة
AWAITING_SEARCH_INPUT = 0
DISPLAYING_RESULTS = 1
SAVING_FAVORITE = 2
DELETING_FAVORITE = 3

# معرف خاص لنتائج البحث الفوري
LIVE_SEARCH_RESULTS = "live_search_results"

async def advanced_search_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """بدء عملية البحث المتقدم للمسؤولين."""
    # التحقق من أن المستخدم هو مسؤول
    if not utils.is_admin(update.effective_user.id):
        await update.message.reply_text(st.NOT_AUTHORIZED)
        return ConversationHandler.END
    
    # تعيين حالة البحث المتقدم
    context.user_data['in_advanced_search'] = True
    logging.info("Advanced search mode enabled for user %s", update.effective_user.id)
    
    # الحصول على سجلات البحث الأخيرة للمستخدم
    user_id = update.effective_user.id
    recent_searches = get_user_search_history(user_id, limit=5)
    
    # إنشاء أزرار اقتراحات البحث السابقة
    keyboard = []
    
    if recent_searches:
        # إضافة الاقتراحات من سجلات البحث
        for search in recent_searches:
            keyboard.append([
                f"🔍 {search['search_term']} ({search['results_count']} نتيجة)"
            ])
    
    # إضافة أزرار العودة والإلغاء
    keyboard.append([st.CANCEL_BUTTON, st.MAIN_MENU_BUTTON])
    
    reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
    await update.message.reply_text(
        "🔍 *البحث المتقدم*\n\n"
        "يمكنك كتابة جزء من اسم العميل أو رقم الهاتف للبحث\n"
        "سيتم عرض النتائج المتطابقة على الفور\n\n"
        "• للبحث عن اسم، اكتب مباشرة (مثلاً: محمد، أحمد)\n"
        "• للبحث عن رقم هاتف، اكتب # ثم الرقم (مثلاً: #0991)\n\n"
        "يمكنك اختيار أحد عمليات البحث السابقة أو كتابة نص البحث:",
        reply_markup=reply_markup,
        parse_mode='Markdown'
    )
    
    # إعادة تعيين البيانات المؤقتة للبحث
    context.user_data[LIVE_SEARCH_RESULTS] = []
    
    return AWAITING_SEARCH_INPUT

async def process_search_input(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """معالجة مدخلات البحث المتقدم في الوقت الفعلي."""
    query = update.message.text
    
    # التحقق من أزرار الإلغاء والقائمة الرئيسية
    if query == st.CANCEL_BUTTON:
        # إزالة حالة البحث المتقدم
        if 'in_advanced_search' in context.user_data:
            del context.user_data['in_advanced_search']
            logging.info("Advanced search mode disabled for user %s after cancel", update.effective_user.id)
        
        await update.message.reply_text("تم إلغاء البحث المتقدم.", reply_markup=ReplyKeyboardRemove())
        return ConversationHandler.END
    
    elif query == st.MAIN_MENU_BUTTON:
        # إزالة حالة البحث المتقدم (لن تكون ضرورية لأن main_menu_command سيمسح كل البيانات)
        if 'in_advanced_search' in context.user_data:
            del context.user_data['in_advanced_search']
            logging.info("Advanced search mode disabled for user %s before main menu", update.effective_user.id)
        
        from bot import main_menu_command
        await main_menu_command(update, context)
        return ConversationHandler.END
    
    # التحقق من السجلات السابقة
    if query.startswith("🔍 "):
        # استخراج استعلام البحث من السجل السابق
        search_term = re.search(r"🔍 (.*) \(\d+ نتيجة\)", query)
        if search_term:
            query = search_term.group(1)
    
    # تحديد نوع البحث (اسم أو رقم هاتف)
    if query.startswith("#"):
        # البحث برقم الهاتف
        phone_query = query[1:]  # إزالة علامة #
        is_valid, cleaned_phone = validator.is_valid_phone(phone_query)
        
        if not is_valid:
            await update.message.reply_text("رقم هاتف غير صالح. يرجى إدخال أرقام فقط.")
            return AWAITING_SEARCH_INPUT
        
        search_type = "هاتف"
        search_results = db.search_notifications_by_phone(cleaned_phone)
    else:
        # البحث بالاسم
        search_type = "اسم"
        search_results = db.search_notifications_by_name(query)
    
    # حفظ النتائج في بيانات المستخدم
    context.user_data[LIVE_SEARCH_RESULTS] = search_results
    context.user_data['search_term'] = query
    context.user_data['search_type'] = search_type
    
    # عرض ملخص النتائج
    if not search_results:
        await update.message.reply_text(f"لم يتم العثور على نتائج للبحث عن: '{query}'")
        return AWAITING_SEARCH_INPUT
    
    # إضافة السجل لسجلات البحث
    try:
        user_id = update.effective_user.id
        username = update.effective_user.username or update.effective_user.first_name or "مستخدم"
        add_search_record(user_id, username, query, search_type, search_results)
        
        logging.info(f"تم حفظ سجل البحث للمستخدم {user_id} - المصطلح: {query}")
    except Exception as e:
        logging.error(f"خطأ في حفظ سجل البحث: {e}")
    
    # إنشاء لوحة مفاتيح للنتائج
    keyboard = []
    
    # تجهيز النتائج (أقصى 5 نتائج في الصفحة الواحدة)
    max_results = min(5, len(search_results))
    for i in range(max_results):
        notification = search_results[i]
        customer_name = notification.get('customer_name', 'غير معروف')
        phone_number = notification.get('phone_number', 'غير معروف')
        
        # إنشاء زر لكل نتيجة
        keyboard.append([
            InlineKeyboardButton(
                f"{i+1}. {customer_name} - {phone_number}",
                callback_data=f"advsearch_view_{notification['id']}"
            )
        ])
    
    # إضافة أزرار الإجراءات
    actions_row = []
    
    # زر لحفظ البحث في المفضلة
    actions_row.append(InlineKeyboardButton("⭐ حفظ بحث", callback_data="advsearch_save"))
    
    # زر للعودة للبحث
    actions_row.append(InlineKeyboardButton("🔍 بحث جديد", callback_data="advsearch_new"))
    
    # إضافة صف الإجراءات
    keyboard.append(actions_row)
    
    # إضافة زر القائمة الرئيسية
    keyboard.append([InlineKeyboardButton("🏠 القائمة الرئيسية", callback_data="advsearch_menu")])
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    # عرض النتائج
    await update.message.reply_text(
        f"🔍 نتائج البحث عن: '{query}'\n"
        f"تم العثور على {len(search_results)} نتيجة:",
        reply_markup=reply_markup
    )
    
    return DISPLAYING_RESULTS

async def handle_live_search_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """معالجة استجابة أزرار البحث المتقدم."""
    query = update.callback_query
    await query.answer()
    
    action = query.data.split("_")[1]
    
    if action == "view":
        # عرض تفاصيل الإشعار
        notification_id = query.data.split("_")[2]
        
        # الحصول على كل الإشعارات ثم البحث عن الإشعار بالمعرف مباشرة
        all_notifications = db.get_all_notifications()
        notification = next((n for n in all_notifications if n["id"] == notification_id), None)
        
        if not notification:
            logging.error(f"لم يتم العثور على الإشعار بالمعرف {notification_id}")
            await query.message.reply_text("⚠️ لم يتم العثور على الإشعار!")
            return DISPLAYING_RESULTS
        
        # عرض تفاصيل الإشعار
        details = utils.format_notification_details(notification)
        
        # إضافة أزرار الإجراءات
        keyboard = [
            [InlineKeyboardButton("🔙 عودة للنتائج", callback_data="advsearch_back")],
            [InlineKeyboardButton("🏠 القائمة الرئيسية", callback_data="advsearch_menu")]
        ]
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        # الحصول على الصورة
        image_data = db.get_image(notification_id)
        
        if image_data:
            await utils.send_image_with_caption(update, context, photo=image_data, caption=details)
            await query.message.reply_text("الإجراءات المتاحة:", reply_markup=reply_markup)
        else:
            await query.message.reply_text(details + "\n\n⚠️ الصورة غير متوفرة!", reply_markup=reply_markup)
        
        return DISPLAYING_RESULTS
    
    elif action == "save":
        # حفظ البحث في المفضلة
        await query.message.reply_text(
            "أدخل اسما مختصرا لحفظ هذا البحث في المفضلة:",
            reply_markup=ReplyKeyboardMarkup([[st.CANCEL_BUTTON]], resize_keyboard=True)
        )
        return SAVING_FAVORITE
    
    elif action == "new":
        # بدء بحث جديد
        # استخدام send_message بدلاً من advanced_search_command مباشرة
        user_id = update.effective_user.id
        
        # تعيين حالة البحث المتقدم
        context.user_data['in_advanced_search'] = True
        logging.info("Advanced search mode enabled for user %s", user_id)
        
        # الحصول على سجلات البحث الأخيرة للمستخدم
        recent_searches = get_user_search_history(user_id, limit=5)
        
        # إنشاء أزرار اقتراحات البحث السابقة
        keyboard = []
        
        if recent_searches:
            # إضافة الاقتراحات من سجلات البحث
            for search in recent_searches:
                keyboard.append([
                    f"🔍 {search['search_term']} ({search['results_count']} نتيجة)"
                ])
        
        # إضافة أزرار العودة والإلغاء
        keyboard.append([st.CANCEL_BUTTON, st.MAIN_MENU_BUTTON])
        
        reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
        await query.message.reply_text(
            "🔍 *البحث المتقدم*\n\n"
            "يمكنك كتابة جزء من اسم العميل أو رقم الهاتف للبحث\n"
            "سيتم عرض النتائج المتطابقة على الفور\n\n"
            "• للبحث عن اسم، اكتب مباشرة (مثلاً: محمد، أحمد)\n"
            "• للبحث عن رقم هاتف، اكتب # ثم الرقم (مثلاً: #0991)\n\n"
            "يمكنك اختيار أحد عمليات البحث السابقة أو كتابة نص البحث:",
            reply_markup=reply_markup,
            parse_mode='Markdown'
        )
        
        # إعادة تعيين البيانات المؤقتة للبحث
        context.user_data[LIVE_SEARCH_RESULTS] = []
        
        return AWAITING_SEARCH_INPUT
    
    elif action == "back":
        # العودة لنتائج البحث
        search_results = context.user_data.get(LIVE_SEARCH_RESULTS, [])
        search_term = context.user_data.get('search_term', '')
        
        # إنشاء لوحة مفاتيح للنتائج
        keyboard = []
        
        # تجهيز النتائج
        max_results = min(5, len(search_results))
        for i in range(max_results):
            notification = search_results[i]
            customer_name = notification.get('customer_name', 'غير معروف')
            phone_number = notification.get('phone_number', 'غير معروف')
            
            # إنشاء زر لكل نتيجة
            keyboard.append([
                InlineKeyboardButton(
                    f"{i+1}. {customer_name} - {phone_number}",
                    callback_data=f"advsearch_view_{notification['id']}"
                )
            ])
        
        # إضافة أزرار الإجراءات
        actions_row = []
        
        # زر لحفظ البحث في المفضلة
        actions_row.append(InlineKeyboardButton("⭐ حفظ بحث", callback_data="advsearch_save"))
        
        # زر للعودة للبحث
        actions_row.append(InlineKeyboardButton("🔍 بحث جديد", callback_data="advsearch_new"))
        
        # إضافة صف الإجراءات
        keyboard.append(actions_row)
        
        # إضافة زر القائمة الرئيسية
        keyboard.append([InlineKeyboardButton("🏠 القائمة الرئيسية", callback_data="advsearch_menu")])
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        # عرض النتائج
        await query.message.edit_text(
            f"🔍 نتائج البحث عن: '{search_term}'\n"
            f"تم العثور على {len(search_results)} نتيجة:",
            reply_markup=reply_markup
        )
        
        return DISPLAYING_RESULTS
    
    elif action == "menu":
        # العودة للقائمة الرئيسية
        # إزالة حالة البحث المتقدم
        if 'in_advanced_search' in context.user_data:
            del context.user_data['in_advanced_search']
            logging.info("Advanced search mode disabled for user %s", update.effective_user.id)
        
        # استدعاء القائمة الرئيسية بالرد مباشرة
        user_id = update.effective_user.id
        is_admin = db.is_admin(user_id)
        
        # مسح بيانات المحادثة الحالية
        context.user_data.clear()
        logging.info("User data cleared for user %s when returning to main menu from callback", user_id)
        
        # عرض القائمة المناسبة للمستخدم (مسؤول أو مستخدم عادي)
        from bot import create_admin_keyboard, create_user_keyboard
        
        if is_admin:
            main_admin_text = ""
            if db.is_main_admin(user_id):
                main_admin_text = "\n\n🌟 أنت المسؤول الرئيسي للبوت."
                
            await query.message.reply_text(
                st.BACK_TO_MENU + main_admin_text,
                reply_markup=create_admin_keyboard()
            )
        else:
            await query.message.reply_text(
                st.BACK_TO_MENU,
                reply_markup=create_user_keyboard()
            )
            
        return ConversationHandler.END
    
    return DISPLAYING_RESULTS

async def save_favorite_search(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """حفظ البحث في المفضلة."""
    favorite_name = update.message.text
    
    if favorite_name == st.CANCEL_BUTTON:
        # إلغاء عملية الحفظ
        await update.message.reply_text("تم إلغاء حفظ البحث في المفضلة.", reply_markup=ReplyKeyboardRemove())
        
        # العودة لنتائج البحث
        search_results = context.user_data.get(LIVE_SEARCH_RESULTS, [])
        search_term = context.user_data.get('search_term', '')
        
        # إنشاء لوحة مفاتيح للنتائج
        keyboard = []
        
        # تجهيز النتائج
        max_results = min(5, len(search_results))
        for i in range(max_results):
            notification = search_results[i]
            customer_name = notification.get('customer_name', 'غير معروف')
            phone_number = notification.get('phone_number', 'غير معروف')
            
            # إنشاء زر لكل نتيجة
            keyboard.append([
                InlineKeyboardButton(
                    f"{i+1}. {customer_name} - {phone_number}",
                    callback_data=f"advsearch_view_{notification['id']}"
                )
            ])
        
        # إضافة أزرار الإجراءات
        actions_row = []
        
        # زر لحفظ البحث في المفضلة
        actions_row.append(InlineKeyboardButton("⭐ حفظ بحث", callback_data="advsearch_save"))
        
        # زر للعودة للبحث
        actions_row.append(InlineKeyboardButton("🔍 بحث جديد", callback_data="advsearch_new"))
        
        # إضافة صف الإجراءات
        keyboard.append(actions_row)
        
        # إضافة زر القائمة الرئيسية
        keyboard.append([InlineKeyboardButton("🏠 القائمة الرئيسية", callback_data="advsearch_menu")])
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        # عرض النتائج
        await update.message.reply_text(
            f"🔍 نتائج البحث عن: '{search_term}'\n"
            f"تم العثور على {len(search_results)} نتيجة:",
            reply_markup=reply_markup
        )
        
        return DISPLAYING_RESULTS
    
    # الحصول على بيانات البحث
    search_term = context.user_data.get('search_term', '')
    search_type = context.user_data.get('search_type', '')
    search_results = context.user_data.get(LIVE_SEARCH_RESULTS, [])
    
    # حفظ البحث في المفضلة
    user_id = update.effective_user.id
    
    # تحقق من وجود قائمة المفضلة للمستخدم
    if 'favorite_searches' not in context.user_data:
        context.user_data['favorite_searches'] = []
    
    # إضافة البحث للمفضلة
    context.user_data['favorite_searches'].append({
        'name': favorite_name,
        'term': search_term,
        'type': search_type,
        'count': len(search_results)
    })
    
    await update.message.reply_text(
        f"✅ تم حفظ البحث '{favorite_name}' في المفضلة بنجاح!",
        reply_markup=ReplyKeyboardRemove()
    )
    
    # عرض قائمة البحث المفضلة
    await display_favorite_searches(update, context)
    
    return DISPLAYING_RESULTS

async def display_favorite_searches(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """عرض قائمة البحث المفضلة."""
    # الحصول على قائمة المفضلة
    favorite_searches = context.user_data.get('favorite_searches', [])
    
    if not favorite_searches:
        await update.message.reply_text("لا يوجد أي عمليات بحث محفوظة في المفضلة.")
        return
    
    # إنشاء لوحة مفاتيح للمفضلة
    keyboard = []
    
    for i, search in enumerate(favorite_searches):
        keyboard.append([
            InlineKeyboardButton(
                f"{i+1}. {search['name']} ({search['count']} نتيجة)",
                callback_data=f"favorite_use_{i}"
            )
        ])
    
    # إضافة أزرار الإجراءات
    keyboard.append([
        InlineKeyboardButton("🗑️ حذف من المفضلة", callback_data="favorite_delete"),
        InlineKeyboardButton("🔍 بحث جديد", callback_data="advsearch_new")
    ])
    
    # إضافة زر القائمة الرئيسية
    keyboard.append([InlineKeyboardButton("🏠 القائمة الرئيسية", callback_data="advsearch_menu")])
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    # عرض المفضلة
    await update.message.reply_text(
        "⭐ قائمة البحث المفضلة:",
        reply_markup=reply_markup
    )

async def handle_favorite_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """معالجة استجابة أزرار المفضلة."""
    query = update.callback_query
    await query.answer()
    
    # تحليل البيانات من زر الاستجابة
    parts = query.data.split("_")
    prefix = parts[0]  # favorite أو advsearch
    
    # إذا كان البادئة هي advsearch، فتحويل المعالجة إلى معالج البحث المتقدم
    if prefix == "advsearch":
        return await handle_live_search_callback(update, context)
    
    action = parts[1]
    
    if action == "use":
        # استخدام بحث من المفضلة
        index = int(query.data.split("_")[2])
        favorite_searches = context.user_data.get('favorite_searches', [])
        
        if index >= len(favorite_searches):
            await query.message.reply_text("⚠️ لم يتم العثور على البحث المطلوب.")
            return DISPLAYING_RESULTS
        
        # الحصول على بيانات البحث
        search = favorite_searches[index]
        
        # تنفيذ البحث
        if search['type'] == 'هاتف':
            # البحث برقم الهاتف
            is_valid, cleaned_phone = validator.is_valid_phone(search['term'])
            search_results = db.search_notifications_by_phone(cleaned_phone)
        else:
            # البحث بالاسم
            search_results = db.search_notifications_by_name(search['term'])
        
        # حفظ النتائج في بيانات المستخدم
        context.user_data[LIVE_SEARCH_RESULTS] = search_results
        context.user_data['search_term'] = search['term']
        context.user_data['search_type'] = search['type']
        
        # إنشاء لوحة مفاتيح للنتائج
        keyboard = []
        
        # تجهيز النتائج
        max_results = min(5, len(search_results))
        for i in range(max_results):
            notification = search_results[i]
            customer_name = notification.get('customer_name', 'غير معروف')
            phone_number = notification.get('phone_number', 'غير معروف')
            
            # إنشاء زر لكل نتيجة
            keyboard.append([
                InlineKeyboardButton(
                    f"{i+1}. {customer_name} - {phone_number}",
                    callback_data=f"advsearch_view_{notification['id']}"
                )
            ])
        
        # إضافة أزرار الإجراءات
        actions_row = []
        
        # زر للعودة للمفضلة
        actions_row.append(InlineKeyboardButton("⭐ المفضلة", callback_data="favorite_show"))
        
        # زر للعودة للبحث
        actions_row.append(InlineKeyboardButton("🔍 بحث جديد", callback_data="advsearch_new"))
        
        # إضافة صف الإجراءات
        keyboard.append(actions_row)
        
        # إضافة زر القائمة الرئيسية
        keyboard.append([InlineKeyboardButton("🏠 القائمة الرئيسية", callback_data="advsearch_menu")])
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        # عرض النتائج
        await query.message.edit_text(
            f"🔍 نتائج البحث المفضل: '{search['name']}'\n"
            f"تم العثور على {len(search_results)} نتيجة:",
            reply_markup=reply_markup
        )
        
        return DISPLAYING_RESULTS
    
    elif action == "delete":
        # حذف بحث من المفضلة
        favorite_searches = context.user_data.get('favorite_searches', [])
        
        if not favorite_searches:
            await query.message.reply_text("لا يوجد أي عمليات بحث محفوظة في المفضلة.")
            return DISPLAYING_RESULTS
        
        # إنشاء لوحة مفاتيح للحذف
        keyboard = []
        
        for i, search in enumerate(favorite_searches):
            keyboard.append([
                InlineKeyboardButton(
                    f"{i+1}. {search['name']} ({search['count']} نتيجة)",
                    callback_data=f"favorite_remove_{i}"
                )
            ])
        
        # إضافة زر إلغاء
        keyboard.append([InlineKeyboardButton("🔙 إلغاء", callback_data="favorite_cancel")])
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        # عرض قائمة الحذف
        await query.message.edit_text(
            "🗑️ اختر البحث المفضل الذي ترغب في حذفه:",
            reply_markup=reply_markup
        )
        
        return DELETING_FAVORITE
    
    elif action == "remove":
        # حذف بحث محدد من المفضلة
        index = int(query.data.split("_")[2])
        favorite_searches = context.user_data.get('favorite_searches', [])
        
        if index >= len(favorite_searches):
            await query.message.reply_text("⚠️ لم يتم العثور على البحث المطلوب.")
            return DISPLAYING_RESULTS
        
        # حفظ اسم البحث قبل الحذف
        search_name = favorite_searches[index]['name']
        
        # حذف البحث من المفضلة
        favorite_searches.pop(index)
        context.user_data['favorite_searches'] = favorite_searches
        
        await query.message.edit_text(f"✅ تم حذف البحث '{search_name}' من المفضلة بنجاح!")
        
        # عرض قائمة المفضلة المحدثة
        await handle_favorite_callback(update, context)
        
        return DISPLAYING_RESULTS
    
    elif action == "show":
        # عرض قائمة المفضلة
        favorite_searches = context.user_data.get('favorite_searches', [])
        
        if not favorite_searches:
            await query.message.edit_text("لا يوجد أي عمليات بحث محفوظة في المفضلة.")
            return DISPLAYING_RESULTS
        
        # إنشاء لوحة مفاتيح للمفضلة
        keyboard = []
        
        for i, search in enumerate(favorite_searches):
            keyboard.append([
                InlineKeyboardButton(
                    f"{i+1}. {search['name']} ({search['count']} نتيجة)",
                    callback_data=f"favorite_use_{i}"
                )
            ])
        
        # إضافة أزرار الإجراءات
        keyboard.append([
            InlineKeyboardButton("🗑️ حذف من المفضلة", callback_data="favorite_delete"),
            InlineKeyboardButton("🔍 بحث جديد", callback_data="advsearch_new")
        ])
        
        # إضافة زر القائمة الرئيسية
        keyboard.append([InlineKeyboardButton("🏠 القائمة الرئيسية", callback_data="advsearch_menu")])
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        # عرض المفضلة
        await query.message.edit_text(
            "⭐ قائمة البحث المفضلة:",
            reply_markup=reply_markup
        )
        
        return DISPLAYING_RESULTS
    
    elif action == "cancel":
        # إلغاء عملية الحذف
        await handle_favorite_callback(update, context)
        return DISPLAYING_RESULTS
    
    return DISPLAYING_RESULTS

def get_advanced_search_handler():
    """إرجاع معالج البحث المتقدم للمسؤولين."""
    advanced_search_handler = ConversationHandler(
        entry_points=[
            CommandHandler('advanced_search', advanced_search_command),
            # إضافة نقطة دخول لزر البحث المتقدم
            MessageHandler(filters.Regex('^🔍 البحث المتقدم$'), advanced_search_command)
        ],
        states={
            AWAITING_SEARCH_INPUT: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, process_search_input)
            ],
            DISPLAYING_RESULTS: [
                CallbackQueryHandler(handle_live_search_callback, pattern=r'^advsearch_'),
                CallbackQueryHandler(handle_favorite_callback, pattern=r'^favorite_')
            ],
            SAVING_FAVORITE: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, save_favorite_search)
            ],
            DELETING_FAVORITE: [
                CallbackQueryHandler(handle_favorite_callback, pattern=r'^favorite_')
            ]
        },
        fallbacks=[
            # عند الإلغاء بواسطة الأوامر، إزالة حالة البحث المتقدم
            CommandHandler('cancel', lambda u, c: (
                'in_advanced_search' in c.user_data and c.user_data.pop('in_advanced_search'),
                logging.info("Advanced search mode disabled for user %s via cancel command", u.effective_user.id),
                ConversationHandler.END
            )[-1]),
            MessageHandler(filters.Regex(r'.*إلغاء العملية.*'), lambda u, c: (
                'in_advanced_search' in c.user_data and c.user_data.pop('in_advanced_search'),
                logging.info("Advanced search mode disabled for user %s via cancel message", u.effective_user.id),
                ConversationHandler.END
            )[-1])
        ],
        name="advanced_search"
    )
    
    return advanced_search_handler