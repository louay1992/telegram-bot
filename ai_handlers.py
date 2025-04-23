#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
معالجات الذكاء الاصطناعي للبوت - تدير التفاعل بين المستخدمين ونماذج الذكاء الاصطناعي
"""

import os
import logging
import uuid
from datetime import datetime
import base64

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    ConversationHandler, CommandHandler, MessageHandler,
    CallbackQueryHandler, ContextTypes, filters
)

import database as db
from ai_assistant import (
    get_ai_response, process_image, generate_delivery_prediction
)
from ai_utils import (
    is_admin_async, get_notification_by_id_async, search_notifications_by_phone_async,
    get_user_permission_async, save_ai_chat_history, get_ai_chat_history, reset_ai_chat_history
)

# تكوين السجلات
logger = logging.getLogger(__name__)

# حالات المحادثة
AI_CHAT = 1
AI_IMAGE_ANALYSIS = 2
AI_DELIVERY_PREDICTION = 3
AI_AWAITING_IMAGE = 4
AI_AWAITING_NOTIFICATION_ID = 5

# المفاتيح المستخدمة في الكلاباك
AI_CHAT_CB = "ai_chat"
AI_IMAGE_ANALYSIS_CB = "ai_image_analysis"
AI_DELIVERY_PREDICTION_CB = "ai_delivery_prediction"
AI_RESET_CHAT_CB = "ai_reset_chat"
AI_BACK_CB = "ai_back"
AI_CANCEL_CB = "ai_cancel"
CREATE_NOTIFICATION_CB = "create_notification_from_ai"


async def ai_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """بدء تفاعل الذكاء الاصطناعي وعرض الخيارات المتاحة."""
    user_id = update.effective_user.id
    
    # التحقق مما إذا كان المستخدم مسموحاً له باستخدام ميزات الذكاء الاصطناعي
    is_admin = await is_admin_async(user_id)
    has_permission = await get_user_permission_async(user_id, "ai_features")
    
    if not is_admin and not has_permission:
        await update.message.reply_text(
            "عذراً، هذه الميزة متاحة فقط للمسؤولين والمسوقين المعتمدين."
        )
        return ConversationHandler.END
    
    # إنشاء لوحة أزرار للوظائف المتاحة
    keyboard = [
        [InlineKeyboardButton("💬 محادثة ذكية", callback_data=AI_CHAT_CB)],
        [InlineKeyboardButton("🖼️ تحليل صورة شحنة", callback_data=AI_IMAGE_ANALYSIS_CB)],
        [InlineKeyboardButton("⏱️ التنبؤ بوقت التسليم", callback_data=AI_DELIVERY_PREDICTION_CB)],
        [InlineKeyboardButton("❌ إلغاء", callback_data=AI_CANCEL_CB)]
    ]
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.message.reply_text(
        "🧠 *المساعد الذكي*\n\n"
        "مرحباً! أنا المساعد الذكي لنظام إدارة الشحنات. يمكنني مساعدتك في:\n\n"
        "• الإجابة على استفساراتك عن الشحنات\n"
        "• تحليل صور الشحنات\n"
        "• التنبؤ بأوقات التسليم المتوقعة\n\n"
        "اختر إحدى الوظائف التالية:",
        reply_markup=reply_markup,
        parse_mode='Markdown'
    )
    
    return AI_CHAT


async def handle_ai_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """معالجة ردود استعلام الأزرار في واجهة الذكاء الاصطناعي."""
    query = update.callback_query
    await query.answer()
    
    # الحصول على معرّف المستخدم
    user_id = update.effective_user.id
    
    if query.data == AI_CHAT_CB:
        # بدء محادثة ذكية
        keyboard = [[InlineKeyboardButton("🔄 إعادة تعيين المحادثة", callback_data=AI_RESET_CHAT_CB)],
                   [InlineKeyboardButton("🔙 العودة", callback_data=AI_BACK_CB)]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        # تعيين سياق المستخدم للمحادثة الذكية
        if not 'user_context' in context.bot_data:
            context.bot_data['user_context'] = {}
        context.bot_data['user_context'][user_id] = "smart_chat"
        
        # تخزين سياق المحادثة النشط ليتم استخدامه لاحقاً
        if not 'active_contexts' in context.bot_data:
            context.bot_data['active_contexts'] = {}
        context.bot_data['active_contexts'][user_id] = AI_CHAT
        
        await query.edit_message_text(
            "💬 *المحادثة الذكية*\n\n"
            "يمكنك الآن البدء بالتحدث معي. اسألني أي سؤال عن الشحنات أو الخدمات المتاحة وسأحاول مساعدتك.\n\n"
            "_يمكنك إعادة تعيين المحادثة في أي وقت باستخدام الزر أدناه._",
            reply_markup=reply_markup,
            parse_mode='Markdown'
        )
        
        return AI_CHAT
        
    elif query.data == AI_IMAGE_ANALYSIS_CB:
        # بدء تحليل الصور
        keyboard = [[InlineKeyboardButton("🔙 العودة", callback_data=AI_BACK_CB)]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await query.edit_message_text(
            "🖼️ *تحليل صورة الشحنة*\n\n"
            "أرسل صورة للشحنة وسأقوم بتحليلها وتقديم معلومات عنها.\n\n"
            "يمكنني تحديد:\n"
            "• حالة الشحنة\n"
            "• نوع العبوة\n"
            "• أي علامات أو معلومات مرئية\n"
            "• تقديم ملاحظات حول التعامل مع الشحنة",
            reply_markup=reply_markup,
            parse_mode='Markdown'
        )
        
        return AI_AWAITING_IMAGE
        
    elif query.data == AI_DELIVERY_PREDICTION_CB:
        # بدء التنبؤ بوقت التسليم
        keyboard = [[InlineKeyboardButton("🔙 العودة", callback_data=AI_BACK_CB)]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await query.edit_message_text(
            "⏱️ *التنبؤ بوقت التسليم*\n\n"
            "أرسل لي معرف الإشعار الذي تريد التنبؤ بوقت تسليمه.\n\n"
            "يمكنك الحصول على معرف الإشعار من قائمة الإشعارات باستخدام الأمر /list",
            reply_markup=reply_markup,
            parse_mode='Markdown'
        )
        
        return AI_AWAITING_NOTIFICATION_ID
        
    elif query.data == AI_RESET_CHAT_CB:
        # إعادة تعيين المحادثة
        user_id = update.effective_user.id
        await reset_ai_chat_history(user_id)
        
        keyboard = [[InlineKeyboardButton("🔄 إعادة تعيين المحادثة", callback_data=AI_RESET_CHAT_CB)],
                   [InlineKeyboardButton("🔙 العودة", callback_data=AI_BACK_CB)]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await query.edit_message_text(
            "💬 *المحادثة الذكية*\n\n"
            "تم إعادة تعيين المحادثة. يمكنك بدء محادثة جديدة الآن.",
            reply_markup=reply_markup,
            parse_mode='Markdown'
        )
        
        return AI_CHAT
        
    elif query.data == AI_BACK_CB:
        # العودة إلى القائمة الرئيسية
        keyboard = [
            [InlineKeyboardButton("💬 محادثة ذكية", callback_data=AI_CHAT_CB)],
            [InlineKeyboardButton("🖼️ تحليل صورة شحنة", callback_data=AI_IMAGE_ANALYSIS_CB)],
            [InlineKeyboardButton("⏱️ التنبؤ بوقت التسليم", callback_data=AI_DELIVERY_PREDICTION_CB)],
            [InlineKeyboardButton("❌ إلغاء", callback_data=AI_CANCEL_CB)]
        ]
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await query.edit_message_text(
            "🧠 *المساعد الذكي*\n\n"
            "مرحباً! أنا المساعد الذكي لنظام إدارة الشحنات. يمكنني مساعدتك في:\n\n"
            "• الإجابة على استفساراتك عن الشحنات\n"
            "• تحليل صور الشحنات\n"
            "• التنبؤ بأوقات التسليم المتوقعة\n\n"
            "اختر إحدى الوظائف التالية:",
            reply_markup=reply_markup,
            parse_mode='Markdown'
        )
        
        return AI_CHAT
        
    elif query.data == CREATE_NOTIFICATION_CB:
        # التحقق من وجود معلومات الإشعار المستخرجة
        if 'suggested_notification' not in context.user_data:
            await query.edit_message_text(
                "⚠️ لم يتم العثور على معلومات الإشعار. الرجاء إعادة تحليل الصورة."
            )
            return AI_AWAITING_IMAGE
        
        # الحصول على معلومات الإشعار المستخرجة
        suggested_notification = context.user_data['suggested_notification']
        customer_name = suggested_notification.get('customer_name', '')
        phone = suggested_notification.get('phone', '')
        image_path = suggested_notification.get('image_path', '')
        
        if not customer_name or not phone or not image_path:
            await query.edit_message_text(
                "⚠️ المعلومات المستخرجة غير كاملة. الرجاء التأكد من وجود اسم العميل ورقم الهاتف والصورة."
            )
            return AI_AWAITING_IMAGE
        
        user_id = update.effective_user.id
        
        try:
            # إرسال إشارة إلى أن البوت يعمل
            await query.answer("جاري إنشاء الإشعار...")
            
            # معالجة الهاتف للتأكد من صحة التنسيق
            if not phone.startswith('+'):
                if phone.startswith('09'):
                    phone = '+963' + phone[1:]
                elif phone.startswith('05'):
                    phone = '+90' + phone[1:]
            
            # إنشاء إشعار جديد من البيانات المستخرجة
            from database import add_notification
            
            # قراءة الصورة كبيانات ثنائية
            with open(image_path, 'rb') as image_file:
                image_binary = image_file.read()
            
            # إنشاء معرف فريد للإشعار
            notification_id = str(uuid.uuid4())
            
            # إنشاء الإشعار
            success, result = add_notification(
                customer_name=customer_name,
                phone_number=phone,
                image_data=image_binary,
                reminder_hours=72  # 3 أيام افتراضياً
            )
            
            # التحقق من نجاح إنشاء الإشعار
            if not success:
                raise Exception(f"فشل إنشاء الإشعار: {result}")
                
            # استخدام معرف الإشعار من النتيجة
            created_notification_id = result
                
            # إرسال تأكيد إنشاء الإشعار
            await query.edit_message_text(
                f"✅ *تم إنشاء إشعار جديد بنجاح!*\n\n"
                f"*معرف الإشعار:* `{created_notification_id}`\n"
                f"*اسم العميل:* {customer_name}\n"
                f"*رقم الهاتف:* {phone}\n\n"
                f"تم استخراج هذه البيانات تلقائياً باستخدام الذكاء الاصطناعي وتقنية التعرف على النصوص (OCR) من صورة الشحنة.",
                parse_mode='Markdown'
            )
            
            # إزالة المعلومات المستخرجة من سياق المستخدم
            if 'suggested_notification' in context.user_data:
                del context.user_data['suggested_notification']
            
            logger.info(f"تم إنشاء إشعار جديد بنجاح من البيانات المستخرجة: {notification_id}")
            
            # العودة للقائمة الرئيسية
            return AI_CHAT
            
        except Exception as e:
            logger.error(f"خطأ أثناء إنشاء الإشعار من البيانات المستخرجة: {e}")
            
            await query.edit_message_text(
                f"⚠️ حدث خطأ أثناء إنشاء الإشعار: {str(e)}\n\n"
                f"الرجاء المحاولة مرة أخرى أو إنشاء الإشعار يدوياً."
            )
            
            return AI_AWAITING_IMAGE
    
    elif query.data == AI_CANCEL_CB:
        # إلغاء المحادثة
        user_id = update.effective_user.id
        
        # إزالة سياق المحادثة الذكية
        if hasattr(context, 'bot_data') and 'user_context' in context.bot_data:
            if user_id in context.bot_data['user_context']:
                del context.bot_data['user_context'][user_id]
                logger.info(f"تم إزالة سياق المحادثة الذكية للمستخدم {user_id} عند الضغط على زر الإلغاء")
        
        # إزالة سياق محادثة نشطة إذا كان موجودًا
        if hasattr(context, 'bot_data') and 'active_contexts' in context.bot_data:
            if user_id in context.bot_data['active_contexts']:
                del context.bot_data['active_contexts'][user_id]
                logger.info(f"تم إزالة سياق المحادثة النشطة للمستخدم {user_id} عند الضغط على زر الإلغاء")
                
        await query.edit_message_text(
            "تم إلغاء المساعد الذكي. يمكنك تشغيله مرة أخرى باستخدام الأمر /ai"
        )
        
        return ConversationHandler.END
        
    return AI_CHAT


async def handle_chat_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """معالجة رسائل المحادثة الذكية."""
    user_id = update.effective_user.id
    user_message = update.message.text
    
    # إرسال إشارة كتابة للإشارة إلى أن البوت يعمل
    await context.bot.send_chat_action(
        chat_id=update.effective_chat.id,
        action="typing"
    )
    
    # التحقق من وجود رقم هاتف في الرسالة
    import re
    phone_patterns = [
        r'\+?9\d{2}\d{9}',  # +90xxxxxxxxx أو 90xxxxxxxxx (تركيا)
        r'\+?963\d{9}',     # +963xxxxxxxxx أو 963xxxxxxxxx (سوريا)
        r'09\d{8}',         # 09xxxxxxxx (سوريا)
        r'05\d{9}'          # 05xxxxxxxxx (تركيا)
    ]
    
    found_phone = None
    for pattern in phone_patterns:
        matches = re.findall(pattern, user_message)
        if matches:
            found_phone = matches[0]
            break
    
    if found_phone:
        logger.info(f"تم العثور على رقم هاتف في الرسالة: {found_phone}")
        
        # تنسيق رقم الهاتف للبحث
        if found_phone.startswith('09'):
            # تحويل رقم سوري
            search_phone = '+963' + found_phone[1:]
        elif found_phone.startswith('05'):
            # تحويل رقم تركي
            search_phone = '+90' + found_phone[1:]
        elif not found_phone.startswith('+'):
            # إضافة + للأرقام التي تبدأ بكود الدولة بدون +
            if found_phone.startswith('963') or found_phone.startswith('90'):
                search_phone = '+' + found_phone
            else:
                search_phone = found_phone
        else:
            search_phone = found_phone
        
        # البحث عن الإشعار باستخدام رقم الهاتف
        from ai_utils import search_notifications_by_phone_async
        notifications = await search_notifications_by_phone_async(search_phone)
        
        if notifications and len(notifications) > 0:
            # تم العثور على إشعار، استخدم نوع الرسالة phone_search
            ai_response = get_ai_response(
                user_message=f"البحث عن إشعار برقم الهاتف: {search_phone}",
                message_type="phone_search",
                notification_search=notifications
            )
            
            # حفظ المحادثة في سجل المحادثات
            await save_ai_chat_history(user_id, f"البحث عن إشعار برقم الهاتف: {search_phone}", ai_response, chat_type="phone_search")
            
            # إرسال الرد مع صورة الإشعار إذا وجدت
            notification = notifications[0]
            keyboard = [[InlineKeyboardButton("🔄 إعادة تعيين المحادثة", callback_data=AI_RESET_CHAT_CB)],
                       [InlineKeyboardButton("🔙 العودة", callback_data=AI_BACK_CB)]]
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            # إرسال النص أولاً
            message = await update.message.reply_text(
                ai_response,
                reply_markup=reply_markup
            )
            
            # ثم محاولة إرسال الصورة إذا كانت متوفرة
            try:
                image_path = notification.get('image_path')
                if image_path and os.path.exists(image_path):
                    await context.bot.send_photo(
                        chat_id=update.effective_chat.id,
                        photo=open(image_path, 'rb'),
                        caption=f"📸 صورة الإشعار للعميل: {notification.get('customer_name', 'غير متوفر')}"
                    )
                    logger.info(f"تم إرسال صورة الإشعار: {image_path}")
            except Exception as e:
                logger.error(f"خطأ في إرسال صورة الإشعار: {str(e)}")
            
            return AI_CHAT
    
    # إذا لم يتم العثور على رقم هاتف أو فشل البحث، استخدم المحادثة العادية
    # الحصول على رد من الذكاء الاصطناعي
    ai_response = get_ai_response(user_message, message_type="chat")
    
    # حفظ المحادثة في سجل المحادثات
    await save_ai_chat_history(user_id, user_message, ai_response, chat_type="general")
    
    # إرسال الرد
    keyboard = [[InlineKeyboardButton("🔄 إعادة تعيين المحادثة", callback_data=AI_RESET_CHAT_CB)],
               [InlineKeyboardButton("🔙 العودة", callback_data=AI_BACK_CB)]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.message.reply_text(
        ai_response,
        reply_markup=reply_markup
    )
    
    return AI_CHAT


async def handle_image_upload(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """معالجة تحميل الصور للتحليل."""
    # التأكد من وجود صورة
    if not update.message.photo:
        await update.message.reply_text(
            "لم يتم العثور على صورة. الرجاء إرسال صورة للشحنة أو الفاتورة للتحليل."
        )
        return AI_AWAITING_IMAGE
    
    # إرسال إشارة تحميل للإشارة إلى أن البوت يعمل
    await context.bot.send_chat_action(
        chat_id=update.effective_chat.id,
        action="upload_photo"
    )
    
    # الحصول على الصورة بأعلى دقة
    photo = update.message.photo[-1]
    photo_file = await context.bot.get_file(photo.file_id)
    
    # تنزيل الصورة وحفظها مؤقتاً
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    file_name = f"temp_media/ai_analysis_{timestamp}_{uuid.uuid4().hex}.jpg"
    
    # التأكد من وجود المجلد
    os.makedirs("temp_media", exist_ok=True)
    
    await photo_file.download_to_drive(file_name)
    
    # الحصول على سياق التحليل من نص الرسالة إذا وجد
    caption = update.message.caption or ""
    
    # تحديد سياق التحليل
    context_info = None
    if caption:
        context_info = caption
    elif 'current_ai_context' in context.user_data:
        context_info = context.user_data['current_ai_context']
    
    # تحليل الصورة
    logger.info(f"تحليل الصورة: {file_name} مع السياق: {context_info}")
    
    # إرسال إشارة كتابة مرة أخرى لتدل على أن البوت لا يزال يعمل (لأن تحليل الصورة قد يستغرق وقتاً)
    await context.bot.send_chat_action(
        chat_id=update.effective_chat.id,
        action="typing"
    )
    
    try:
        # محاولة استخدام OCR المحسّن لتحليل صور الشحنات
        from shipment_ocr import get_suggested_notification_data
        suggested_data = get_suggested_notification_data(file_name)
        
        # تحقق من وجود بيانات مستخرجة من OCR
        if suggested_data and suggested_data.get('customer_name') and suggested_data.get('phone'):
            logger.info(f"تم استخراج بيانات من صورة الشحنة: {suggested_data}")
            
            # إضافة معلومات استخراج البيانات إلى نص التحليل
            ocr_info = (
                "🔍 *تحليل صورة الشحنة*\n\n"
                f"يبدو أن هذه الصورة تحتوي على معلومات شحنة للعميل:\n\n"
                f"👤 *اسم العميل*: {suggested_data.get('customer_name', 'غير محدد')}\n"
                f"📱 *رقم الهاتف*: {suggested_data.get('phone', 'غير محدد')}\n"
            )
            
            if suggested_data.get('destination'):
                ocr_info += f"📍 *الوجهة*: {suggested_data.get('destination')}\n"
                
            if suggested_data.get('date'):
                ocr_info += f"📅 *تاريخ الشحنة*: {suggested_data.get('date')}\n"
                
            if suggested_data.get('value'):
                ocr_info += f"💰 *قيمة الشحنة*: {suggested_data.get('value')}\n"
                
            # إضافة درجة الثقة
            name_confidence = suggested_data.get('confidence', {}).get('name', 0)
            phone_confidence = suggested_data.get('confidence', {}).get('phone', 0)
            avg_confidence = (name_confidence + phone_confidence) / 2
            confidence_text = "عالية ✅" if avg_confidence > 0.7 else "متوسطة ⚠️" if avg_confidence > 0.4 else "منخفضة ❌"
            
            ocr_info += f"\n*درجة الثقة*: {confidence_text}\n\n"
            
            # إعطاء خيار إنشاء إشعار بهذه البيانات
            ocr_info += "*هل ترغب في إنشاء إشعار بهذه البيانات؟*\n"
            
            # حفظ بيانات الإشعار المقترحة في بيانات المستخدم لاستخدامها لاحقاً
            context.user_data['suggested_notification'] = {
                'customer_name': suggested_data.get('customer_name', ''),
                'phone': suggested_data.get('phone', ''),
                'destination': suggested_data.get('destination', ''),
                'date': suggested_data.get('date', ''),
                'value': suggested_data.get('value', ''),
                'image_path': file_name
            }
            
            # استكمال التحليل بمزيد من التفاصيل باستخدام نموذج الرؤية
            additional_analysis = process_image(file_name, "تحليل تفصيلي لصورة شحنة. وصف الصورة وطبيعة المنتجات فيها.")
            
            analysis = ocr_info + "\n" + additional_analysis
        else:
            # استخدام نموذج الرؤية العام في حالة عدم القدرة على استخراج بيانات محددة
            analysis = process_image(file_name, context_info)
    except Exception as e:
        logger.error(f"خطأ أثناء تحليل صورة الشحنة باستخدام OCR: {e}")
        # الرجوع إلى نموذج الرؤية العام في حالة الخطأ
        analysis = process_image(file_name, context_info)
    
    # إضافة سجل للتحليل
    user_id = update.effective_user.id
    await save_ai_chat_history(user_id, f"[تحليل صورة] {context_info or 'بدون سياق'}", analysis, chat_type="image_analysis")
    
    # إرسال التحليل مع أزرار للتفاعل
    keyboard = []
    
    # إضافة زر إنشاء إشعار إذا تم استخراج بيانات من الصورة
    if 'suggested_notification' in context.user_data:
        keyboard.append([InlineKeyboardButton("📝 إنشاء إشعار بهذه البيانات", callback_data=CREATE_NOTIFICATION_CB)])
    
    # إضافة زر العودة
    keyboard.append([InlineKeyboardButton("🔙 العودة", callback_data=AI_BACK_CB)])
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    try:
        await update.message.reply_text(
            f"🖼️ *تحليل الصورة*\n\n{analysis}",
            reply_markup=reply_markup,
            parse_mode='Markdown'
        )
    except Exception as e:
        # في حالة فشل إرسال الرد بالتنسيق Markdown، المحاولة بدون تنسيق
        logger.error(f"خطأ في إرسال التحليل بتنسيق Markdown: {e}")
        await update.message.reply_text(
            f"🖼️ تحليل الصورة\n\n{analysis}",
            reply_markup=reply_markup
        )
    
    return AI_AWAITING_IMAGE


async def handle_notification_id(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """معالجة معرّف الإشعار للتنبؤ بوقت التسليم."""
    notification_id = update.message.text.strip()
    
    # إرسال إشارة كتابة للإشارة إلى أن البوت يعمل
    await context.bot.send_chat_action(
        chat_id=update.effective_chat.id,
        action="typing"
    )
    
    # التحقق من معرف الإشعار
    notification = await get_notification_by_id_async(notification_id)
    
    if not notification:
        # محاولة البحث عن الإشعار برقم الهاتف (إذا تم إدخال رقم هاتف)
        if notification_id.startswith('+'):
            notifications = await search_notifications_by_phone_async(notification_id)
            if notifications and len(notifications) > 0:
                notification = notifications[0]
    
    if notification:
        # توليد التنبؤ بوقت التسليم
        prediction = generate_delivery_prediction(notification)
        
        # إنشاء نص الرد
        reply_text = (
            f"⏱️ *التنبؤ بوقت التسليم*\n\n"
            f"*العميل:* {notification.get('customer_name', 'غير معروف')}\n"
            f"*رقم الهاتف:* {notification.get('phone', 'غير معروف')}\n"
            f"*تاريخ الإنشاء:* {notification.get('created_at', datetime.now()).strftime('%Y-%m-%d')}\n\n"
            f"*تاريخ التسليم المتوقع:* {prediction.get('estimated_delivery_date')}\n"
            f"*المدة المتوقعة:* {prediction.get('min_days')} - {prediction.get('max_days')} أيام\n"
            f"*مستوى الثقة:* {prediction.get('confidence')}\n\n"
            f"*تحليل الذكاء الاصطناعي:*\n{prediction.get('ai_explanation')}"
        )
        
        keyboard = [[InlineKeyboardButton("🔙 العودة", callback_data=AI_BACK_CB)]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await update.message.reply_text(
            reply_text,
            reply_markup=reply_markup,
            parse_mode='Markdown'
        )
    else:
        await update.message.reply_text(
            "❌ لم يتم العثور على إشعار بهذا المعرف. الرجاء التأكد من المعرف وإعادة المحاولة."
        )
    
    return AI_AWAITING_NOTIFICATION_ID


async def cancel_ai(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """إلغاء المحادثة الذكية وإزالة سياق المحادثة."""
    user_id = update.effective_user.id
    
    # إزالة سياق المحادثة الذكية
    if hasattr(context, 'bot_data') and 'user_context' in context.bot_data:
        if user_id in context.bot_data['user_context']:
            del context.bot_data['user_context'][user_id]
            logger.info(f"تم إزالة سياق المحادثة الذكية للمستخدم {user_id}")
    
    # إزالة سياق محادثة نشطة إذا كان موجودًا
    if hasattr(context, 'bot_data') and 'active_contexts' in context.bot_data:
        if user_id in context.bot_data['active_contexts']:
            del context.bot_data['active_contexts'][user_id]
            logger.info(f"تم إزالة سياق المحادثة النشطة للمستخدم {user_id}")
    
    await update.message.reply_text(
        "تم إلغاء المساعد الذكي. يمكنك تشغيله مرة أخرى باستخدام الأمر /ai"
    )
    
    return ConversationHandler.END


def get_ai_handlers():
    """الحصول على معالجات الذكاء الاصطناعي لدمجها مع البوت."""
    
    # إنشاء معالج المحادثة للذكاء الاصطناعي
    ai_handler = ConversationHandler(
        entry_points=[CommandHandler("ai", ai_start)],
        states={
            AI_CHAT: [
                CallbackQueryHandler(handle_ai_callback, pattern=f"^{AI_CHAT_CB}$|^{AI_IMAGE_ANALYSIS_CB}$|^{AI_DELIVERY_PREDICTION_CB}$|^{AI_RESET_CHAT_CB}$|^{AI_BACK_CB}$|^{AI_CANCEL_CB}$"),
                MessageHandler(filters.TEXT & ~filters.COMMAND, handle_chat_message)
            ],
            AI_AWAITING_IMAGE: [
                CallbackQueryHandler(handle_ai_callback, pattern=f"^{AI_BACK_CB}$|^{AI_CANCEL_CB}$|^{CREATE_NOTIFICATION_CB}$"),
                MessageHandler(filters.PHOTO, handle_image_upload)
            ],
            AI_AWAITING_NOTIFICATION_ID: [
                CallbackQueryHandler(handle_ai_callback, pattern=f"^{AI_BACK_CB}$|^{AI_CANCEL_CB}$"),
                MessageHandler(filters.TEXT & ~filters.COMMAND, handle_notification_id)
            ],
        },
        fallbacks=[CommandHandler("cancel", cancel_ai)],
        name="ai_conversation",
        persistent=False
    )
    
    return [ai_handler]