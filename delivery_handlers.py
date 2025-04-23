"""
وحدة معالجة تأكيد استلام الطلبات
"""
import logging
import os
from datetime import datetime
from typing import Dict, Any

from telegram import Update, InlineKeyboardMarkup, InlineKeyboardButton, ReplyKeyboardMarkup, ReplyKeyboardRemove
from telegram.ext import (
    ContextTypes, CommandHandler, ConversationHandler, MessageHandler,
    filters, CallbackQueryHandler
)

import db_manager
import strings
import utils
from database import save_image

# حالات المحادثة لتأكيد الاستلام
(
    SEARCH_METHOD, 
    ENTER_CUSTOMER_NAME, 
    ENTER_PHONE_NUMBER, 
    SELECT_NOTIFICATION, 
    UPLOAD_PROOF_IMAGE,
    ENTER_NOTES
) = range(6)

# دالة مساعدة لعرض زر القائمة الرئيسية في حالات الخطأ
async def show_main_menu_on_error(update: Update, context: ContextTypes.DEFAULT_TYPE, error_message: str = None):
    """
    عرض زر القائمة الرئيسية في حالات الخطأ
    
    Args:
        update: تحديث تيليجرام
        context: سياق المحادثة
        error_message: رسالة الخطأ الاختيارية التي سيتم عرضها
    """
    # إنشاء لوحة مفاتيح مع زر القائمة الرئيسية
    keyboard = [
        [strings.MAIN_MENU_BUTTON]
    ]
    reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
    
    # إذا تم توفير رسالة خطأ، نعرضها
    if error_message:
        await context.bot.send_message(
            chat_id=update.effective_chat.id,
            text=error_message,
            reply_markup=reply_markup
        )
    
    # إضافة رسالة حول كيفية العودة إلى القائمة الرئيسية
    await context.bot.send_message(
        chat_id=update.effective_chat.id,
        text="يمكنك العودة إلى القائمة الرئيسية بالضغط على زر القائمة الرئيسية.",
        reply_markup=reply_markup
    )

# معرفات خاصة بأزرار التفاعل
DELIVERY_CALLBACK_PREFIX = "delivery_"
DELIVERY_SELECT_PREFIX = "select_delivery_"
DELIVERY_CONFIRM_PREFIX = "confirm_delivery_"
DELIVERY_CANCEL = "delivery_cancel"
DELIVERY_LIST = "delivery_list"
DELIVERY_BACK = "delivery_back"

async def confirm_delivery_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """بدء عملية تأكيد استلام الشحنة"""
    user_id = update.effective_user.id
    
    # تم إزالة التحقق من صلاحيات المسؤول هنا لأن تأكيد الاستلام متاح للمستخدمين العاديين
    
    # حفظ معلومات المستخدم في السياق
    context.user_data["confirm_delivery"] = {}
    
    # عرض خيارات البحث
    keyboard = [
        [strings.SEARCH_BY_NAME, strings.SEARCH_BY_PHONE],
        [strings.MAIN_MENU_BUTTON]
    ]
    reply_markup = ReplyKeyboardMarkup(keyboard, one_time_keyboard=True, resize_keyboard=True)
    
    await update.message.reply_text(
        strings.DELIVERY_CONFIRMATION_START,
        reply_markup=reply_markup
    )
    
    return SEARCH_METHOD

async def search_method_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """معالجة اختيار طريقة البحث"""
    user_text = update.message.text
    
    if user_text == strings.SEARCH_BY_NAME:
        # تم اختيار البحث بالاسم
        await update.message.reply_text(
            strings.ENTER_CUSTOMER_NAME_FOR_DELIVERY,
            reply_markup=ReplyKeyboardRemove()
        )
        return ENTER_CUSTOMER_NAME
    
    elif user_text == strings.SEARCH_BY_PHONE:
        # تم اختيار البحث برقم الهاتف
        await update.message.reply_text(
            strings.ENTER_PHONE_NUMBER_FOR_DELIVERY,
            reply_markup=ReplyKeyboardRemove()
        )
        return ENTER_PHONE_NUMBER
    
    elif user_text == strings.MAIN_MENU_BUTTON:
        # العودة إلى القائمة الرئيسية
        from bot import main_menu_command
        await main_menu_command(update, context)
        return ConversationHandler.END
    
    else:
        # إدخال غير صالح
        keyboard = [
            [strings.SEARCH_BY_NAME, strings.SEARCH_BY_PHONE],
            [strings.MAIN_MENU_BUTTON]
        ]
        reply_markup = ReplyKeyboardMarkup(keyboard, one_time_keyboard=True, resize_keyboard=True)
        
        await update.message.reply_text(
            strings.INVALID_SEARCH_METHOD,
            reply_markup=reply_markup
        )
        return SEARCH_METHOD

async def customer_name_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """معالجة إدخال اسم العميل"""
    customer_name = update.message.text
    
    # التحقق من زر القائمة الرئيسية
    if customer_name == strings.MAIN_MENU_BUTTON:
        # العودة إلى القائمة الرئيسية
        from bot import main_menu_command
        await main_menu_command(update, context)
        return ConversationHandler.END
    
    # حفظ اسم العميل في السياق
    context.user_data["confirm_delivery"]["customer_name"] = customer_name
    
    # البحث عن الإشعارات بالاسم
    notifications = db_manager.search_notifications_by_name(customer_name)
    
    # معالجة نتائج البحث
    return await handle_search_results(update, context, notifications, customer_name)

async def phone_number_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """معالجة إدخال رقم الهاتف"""
    phone_number = update.message.text
    
    # التحقق من زر القائمة الرئيسية
    if phone_number == strings.MAIN_MENU_BUTTON:
        # العودة إلى القائمة الرئيسية
        from bot import main_menu_command
        await main_menu_command(update, context)
        return ConversationHandler.END
    
    # حفظ رقم الهاتف في السياق
    context.user_data["confirm_delivery"]["phone_number"] = phone_number
    
    # تنسيق رقم الهاتف وإضافة رمز البلد إذا لزم الأمر
    formatted_phone = utils.format_phone_number(phone_number)
    
    # البحث عن الإشعارات برقم الهاتف
    notifications = db_manager.search_notifications_by_phone(formatted_phone)
    
    # معالجة نتائج البحث
    return await handle_search_results(update, context, notifications, formatted_phone)

async def handle_search_results(update: Update, context: ContextTypes.DEFAULT_TYPE, notifications, search_term):
    """معالجة نتائج البحث عن الإشعارات"""
    if not notifications:
        # لم يتم العثور على إشعارات
        await update.message.reply_text(
            strings.NO_NOTIFICATIONS_FOUND.format(search_term=search_term)
        )
        
        # إلغاء المحادثة
        return await cancel_delivery(update, context)
    
    if len(notifications) == 1:
        # تم العثور على إشعار واحد فقط
        notification = notifications[0]
        context.user_data["confirm_delivery"]["notification_id"] = notification["id"]
        
        # عرض تفاصيل الإشعار
        await show_notification_details(update, context, notification)
        
        # إنشاء لوحة المفاتيح مع زر القائمة الرئيسية
        keyboard = [
            [strings.MAIN_MENU_BUTTON]
        ]
        reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
        
        # طلب صورة دليل الاستلام
        await update.message.reply_text(strings.UPLOAD_PROOF_IMAGE, reply_markup=reply_markup)
        return UPLOAD_PROOF_IMAGE
    
    else:
        # تم العثور على عدة إشعارات
        # إنشاء أزرار للاختيار
        keyboard = []
        for notification in notifications:
            # تحقق من حالة التسليم
            delivered_marker = "✅ " if notification.get("is_delivered", False) else ""
            
            customer_name = notification["customer_name"]
            created_date = datetime.fromisoformat(notification["created_at"]).strftime("%Y-%m-%d")
            button_text = f"{delivered_marker}{customer_name} ({created_date})"
            
            keyboard.append([InlineKeyboardButton(
                text=button_text,
                callback_data=f"{DELIVERY_SELECT_PREFIX}{notification['id']}"
            )])
        
        # إضافة زر للإلغاء
        keyboard.append([InlineKeyboardButton(
            text=strings.CANCEL_BUTTON,
            callback_data=DELIVERY_CANCEL
        )])
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await update.message.reply_text(
            strings.MULTIPLE_NOTIFICATIONS_FOUND.format(count=len(notifications)),
            reply_markup=reply_markup
        )
        
        return SELECT_NOTIFICATION

async def show_notification_details(update: Update, context: ContextTypes.DEFAULT_TYPE, notification):
    """عرض تفاصيل الإشعار المحدد"""
    notification_id = notification["id"]
    customer_name = notification["customer_name"]
    phone_number = notification["phone_number"]
    created_at = datetime.fromisoformat(notification["created_at"]).strftime("%Y-%m-%d %H:%M")
    
    # معلومات التسليم إذا كان الإشعار مسلمًا بالفعل
    delivery_info = ""
    if notification.get("is_delivered", False):
        delivered_at = "غير معروف"
        if notification.get("delivery_confirmed_at"):
            delivered_at = datetime.fromisoformat(notification["delivery_confirmed_at"]).strftime("%Y-%m-%d %H:%M")
        
        delivery_info = strings.ALREADY_DELIVERED_INFO.format(
            delivered_at=delivered_at
        )
    
    # إنشاء نص التفاصيل
    details = strings.NOTIFICATION_DETAILS.format(
        customer_name=customer_name,
        phone_number=phone_number,
        created_at=created_at,
        delivery_info=delivery_info
    )
    
    # إرسال صورة الإشعار إذا كانت متوفرة
    if notification.get("has_image", False):
        try:
            # محاولة استرجاع الصورة
            image_path = f"data/images/{notification_id}.jpg"
            if os.path.exists(image_path):
                await update.message.reply_photo(
                    photo=open(image_path, "rb"),
                    caption=details
                )
            else:
                # إرسال النص فقط إذا لم تكن الصورة متوفرة
                await update.message.reply_text(details)
                await update.message.reply_text(strings.IMAGE_NOT_FOUND)
        except Exception as e:
            logging.error(f"خطأ في إرسال صورة الإشعار: {e}")
            await update.message.reply_text(details)
            await update.message.reply_text(strings.ERROR_SENDING_IMAGE)
    else:
        # إرسال النص فقط إذا لم تكن هناك صورة
        await update.message.reply_text(details)

async def notification_selected_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """معالجة اختيار الإشعار من القائمة"""
    query = update.callback_query
    await query.answer()
    
    callback_data = query.data
    
    if callback_data == DELIVERY_CANCEL:
        # تم الضغط على زر الإلغاء
        await query.edit_message_text(strings.OPERATION_CANCELLED)
        return await cancel_delivery(update, context)
    
    # استخراج معرف الإشعار من بيانات رد الاستعلام
    if callback_data.startswith(DELIVERY_SELECT_PREFIX):
        notification_id = callback_data[len(DELIVERY_SELECT_PREFIX):]
        
        # التأكد من أن السياق يحتوي على البيانات اللازمة
        if "confirm_delivery" not in context.user_data:
            context.user_data["confirm_delivery"] = {}
            
        context.user_data["confirm_delivery"]["notification_id"] = notification_id
        
        # البحث عن الإشعار في قاعدة البيانات
        notifications = db_manager.get_all_notifications()
        notification = next((n for n in notifications if n["id"] == notification_id), None)
        
        if notification:
            try:
                # عرض تفاصيل الإشعار
                await show_notification_details(update, context, notification)
                
                # إغلاق المحادثة القديمة وفتح محادثة جديدة
                try:
                    await query.message.edit_text("تم اختيار الإشعار بنجاح.")
                except Exception:
                    pass
                
                # استخدام الدالة المساعدة لعرض زر القائمة الرئيسية
                await show_main_menu_on_error(update, context, strings.UPLOAD_PROOF_IMAGE)
                return UPLOAD_PROOF_IMAGE
            except Exception as e:
                logging.error(f"خطأ عند معالجة الإشعار المحدد: {e}")
                # استخدام الدالة المساعدة لعرض زر القائمة الرئيسية في حالة عدم القدرة على تعديل الرسالة الأصلية
                await show_main_menu_on_error(update, context, strings.UPLOAD_PROOF_IMAGE)
                return UPLOAD_PROOF_IMAGE
        else:
            # لم يتم العثور على الإشعار (غير محتمل، ولكن للتأكد)
            try:
                await query.edit_message_text(strings.NOTIFICATION_NOT_FOUND)
            except Exception:
                await context.bot.send_message(
                    chat_id=update.effective_chat.id,
                    text=strings.NOTIFICATION_NOT_FOUND
                )
            # عرض زر القائمة الرئيسية في حالة الخطأ
            await show_main_menu_on_error(update, context, "يمكنك محاولة البحث مرة أخرى أو العودة للقائمة الرئيسية.")
            return await cancel_delivery(update, context)
    
    # حالة غير متوقعة
    try:
        await query.edit_message_text(strings.UNEXPECTED_ERROR)
    except Exception:
        await context.bot.send_message(
            chat_id=update.effective_chat.id,
            text=strings.UNEXPECTED_ERROR
        )
    return await cancel_delivery(update, context)

async def proof_image_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """معالجة استلام صورة دليل التسليم"""
    notification_id = context.user_data["confirm_delivery"].get("notification_id")
    
    if not notification_id:
        # لا يوجد معرف إشعار في السياق (غير محتمل، ولكن للتأكد)
        await update.message.reply_text(strings.UNEXPECTED_ERROR)
        return await cancel_delivery(update, context)
    
    # التحقق من زر القائمة الرئيسية (يتم إرساله كنص إذا ضغط المستخدم على الزر)
    if update.message.text and update.message.text == strings.MAIN_MENU_BUTTON:
        # العودة إلى القائمة الرئيسية
        from bot import main_menu_command
        await main_menu_command(update, context)
        return ConversationHandler.END
    
    if not update.message.photo:
        # لم يتم إرسال صورة
        keyboard = [
            [strings.MAIN_MENU_BUTTON]
        ]
        reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
        await update.message.reply_text(strings.NOT_AN_IMAGE)
        await update.message.reply_text(strings.UPLOAD_PROOF_IMAGE_AGAIN, reply_markup=reply_markup)
        return UPLOAD_PROOF_IMAGE
    
    # الحصول على أفضل دقة للصورة
    file_id = update.message.photo[-1].file_id
    
    try:
        # تنزيل الصورة وحفظها
        image_obj = await context.bot.get_file(file_id)
        image_bytes = await image_obj.download_as_bytearray()
        
        # حفظ صورة دليل التسليم
        proof_image_id = f"{notification_id}_proof"
        save_image(image_bytes, proof_image_id)
        
        # تحديث قاعدة البيانات
        db_manager.add_delivery_proof_image(notification_id, True)
        
        # حفظ معلومات الصورة في السياق
        context.user_data["confirm_delivery"]["has_proof_image"] = True
        
        # إنشاء زر "بدون ملاحظات" وزر القائمة الرئيسية
        no_notes_keyboard = ReplyKeyboardMarkup([
            ["بدون ملاحظات"],
            [strings.MAIN_MENU_BUTTON]
        ], resize_keyboard=True, one_time_keyboard=True)
        
        # طلب ملاحظات إضافية (اختياري) مع إضافة زر بدون ملاحظات
        await update.message.reply_text(strings.ENTER_DELIVERY_NOTES, reply_markup=no_notes_keyboard)
        return ENTER_NOTES
        
    except Exception as e:
        logging.error(f"خطأ في حفظ صورة دليل التسليم: {e}")
        await update.message.reply_text(strings.ERROR_SAVING_IMAGE)
        await update.message.reply_text(strings.TRY_AGAIN_LATER)
        return await cancel_delivery(update, context)

async def notes_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """معالجة إدخال ملاحظات إضافية"""
    notification_id = context.user_data["confirm_delivery"].get("notification_id")
    notes = update.message.text
    
    if not notification_id:
        # لا يوجد معرف إشعار في السياق (غير محتمل، ولكن للتأكد)
        await update.message.reply_text(strings.UNEXPECTED_ERROR)
        return await cancel_delivery(update, context)
    
    # التحقق من زر القائمة الرئيسية
    if notes == strings.MAIN_MENU_BUTTON:
        # العودة إلى القائمة الرئيسية
        from bot import main_menu_command
        await main_menu_command(update, context)
        return ConversationHandler.END
    
    # التحقق مما إذا كان المستخدم قد اختار "بدون ملاحظات"
    if notes == "بدون ملاحظات":
        notes = ""  # تعيين النص كسلسلة فارغة
    
    # حفظ الملاحظات في السياق
    context.user_data["confirm_delivery"]["notes"] = notes
    
    # عرض ملخص التأكيد للموافقة النهائية
    notification = db_manager.get_all_notifications()
    notification = next((n for n in notification if n["id"] == notification_id), None)
    
    if notification:
        summary = strings.DELIVERY_CONFIRMATION_SUMMARY.format(
            customer_name=notification["customer_name"],
            phone_number=notification["phone_number"],
            notes=notes
        )
        
        # إنشاء أزرار التأكيد
        keyboard = [
            [
                InlineKeyboardButton(
                    text=strings.CONFIRM_BUTTON,
                    callback_data=f"{DELIVERY_CONFIRM_PREFIX}{notification_id}"
                ),
                InlineKeyboardButton(
                    text=strings.CANCEL_BUTTON,
                    callback_data=DELIVERY_CANCEL
                )
            ]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await update.message.reply_text(
            summary,
            reply_markup=reply_markup
        )
        
        return SELECT_NOTIFICATION
    
    else:
        # لم يتم العثور على الإشعار (غير محتمل، ولكن للتأكد)
        await update.message.reply_text(strings.NOTIFICATION_NOT_FOUND)
        return await cancel_delivery(update, context)

async def confirm_delivery_final_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """معالجة التأكيد النهائي لتسليم الشحنة"""
    query = update.callback_query
    await query.answer()
    
    callback_data = query.data
    
    if callback_data == DELIVERY_CANCEL:
        # تم الضغط على زر الإلغاء
        try:
            await query.edit_message_text(strings.OPERATION_CANCELLED)
        except Exception:
            await context.bot.send_message(
                chat_id=update.effective_chat.id,
                text=strings.OPERATION_CANCELLED
            )
        return await cancel_delivery(update, context)
    
    # استخراج معرف الإشعار من بيانات رد الاستعلام
    if callback_data.startswith(DELIVERY_CONFIRM_PREFIX):
        notification_id = callback_data[len(DELIVERY_CONFIRM_PREFIX):]
        user_id = update.effective_user.id
        
        # مسار آمن للحصول على الملاحظات، مع التحقق من وجود context.user_data["confirm_delivery"]
        notes = ""
        if "confirm_delivery" in context.user_data:
            notes = context.user_data["confirm_delivery"].get("notes", "")
        
        # تحديث حالة الإشعار إلى "تم التسليم"
        success = db_manager.mark_as_delivered(notification_id, user_id, notes)
        
        if success:
            # إشعار المستخدم بنجاح العملية
            try:
                await query.edit_message_text(strings.DELIVERY_CONFIRMED_SUCCESS)
            except Exception:
                await context.bot.send_message(
                    chat_id=update.effective_chat.id,
                    text=strings.DELIVERY_CONFIRMED_SUCCESS
                )
            
            # إرسال إشعار للمسؤولين الآخرين
            await notify_admins_about_delivery(context, notification_id, user_id)
            
            # مسح بيانات السياق
            if "confirm_delivery" in context.user_data:
                del context.user_data["confirm_delivery"]
            
            # عرض زر القائمة الرئيسية بعد نجاح العملية
            keyboard = [
                [strings.MAIN_MENU_BUTTON]
            ]
            reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
            
            await context.bot.send_message(
                chat_id=update.effective_chat.id,
                text="يمكنك العودة إلى القائمة الرئيسية للقيام بعمليات أخرى.",
                reply_markup=reply_markup
            )
            
            return ConversationHandler.END
        else:
            # فشل تحديث حالة الإشعار
            try:
                await query.edit_message_text(strings.ERROR_CONFIRMING_DELIVERY)
            except Exception:
                await context.bot.send_message(
                    chat_id=update.effective_chat.id,
                    text=strings.ERROR_CONFIRMING_DELIVERY
                )
                
            # إضافة زر القائمة الرئيسية للحالة الخطأ
            keyboard = [
                [strings.MAIN_MENU_BUTTON]
            ]
            reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
            
            await context.bot.send_message(
                chat_id=update.effective_chat.id,
                text="يمكنك المحاولة مرة أخرى أو العودة إلى القائمة الرئيسية.",
                reply_markup=reply_markup
            )
            
            return await cancel_delivery(update, context)
    
    # حالة غير متوقعة
    try:
        await query.edit_message_text(strings.UNEXPECTED_ERROR)
    except Exception:
        await context.bot.send_message(
            chat_id=update.effective_chat.id,
            text=strings.UNEXPECTED_ERROR
        )
    return await cancel_delivery(update, context)

async def notify_admins_about_delivery(context: ContextTypes.DEFAULT_TYPE, notification_id: str, confirming_user_id: int):
    """إرسال إشعار للمسؤولين الآخرين حول تأكيد التسليم"""
    try:
        # الحصول على معلومات المسؤولين
        admins = db_manager.get_all_admins()
        
        # الحصول على معلومات الإشعار
        notifications = db_manager.get_all_notifications()
        notification = next((n for n in notifications if n["id"] == notification_id), None)
        
        if notification and admins:
            # اسم المستخدم الذي أكد التسليم
            confirming_admin = next((a for a in admins if a["user_id"] == confirming_user_id), None)
            confirming_username = confirming_admin["username"] if confirming_admin else "مستخدم غير معروف"
            
            # بناء نص الإشعار
            notification_text = strings.ADMIN_DELIVERY_NOTIFICATION.format(
                customer_name=notification["customer_name"],
                phone_number=notification["phone_number"],
                confirming_username=confirming_username
            )
            
            # إرسال الإشعار لجميع المسؤولين ما عدا المستخدم الذي أكد التسليم
            for admin in admins:
                if admin["user_id"] != confirming_user_id:
                    try:
                        await context.bot.send_message(
                            chat_id=admin["user_id"],
                            text=notification_text
                        )
                    except Exception as e:
                        logging.error(f"خطأ في إرسال إشعار للمسؤول {admin['user_id']}: {e}")
    
    except Exception as e:
        logging.error(f"خطأ في إشعار المسؤولين عن تأكيد التسليم: {e}")

async def list_delivered_notifications(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """عرض قائمة الشحنات المؤكدة الاستلام"""
    user_id = update.effective_user.id
    is_admin = db_manager.is_admin(user_id)
    
    # التعامل مع الاستدعاء من زر العودة (callback query)
    if update.callback_query:
        query = update.callback_query
        await query.answer()
        message_method = query.message.reply_text
    else:
        message_method = update.message.reply_text
    
    # الحصول على قائمة الإشعارات المسلمة
    delivered = db_manager.get_delivered_notifications()
    
    if not delivered:
        # لا توجد إشعارات مسلمة
        await message_method(strings.NO_DELIVERED_NOTIFICATIONS)
        return
    
    # للمسؤولين: عرض قائمة مرتبة حسب أسماء الزبائن
    if is_admin:
        # فرز الإشعارات حسب أسماء العملاء
        delivered.sort(key=lambda x: x["customer_name"])
        
        # تجميع الإشعارات حسب اسم العميل
        customer_groups = {}
        for notification in delivered:
            customer_name = notification["customer_name"]
            if customer_name not in customer_groups:
                customer_groups[customer_name] = []
            customer_groups[customer_name].append(notification)
        
        # إنشاء قائمة أزرار لكل زبون
        keyboard = []
        for customer_name, notifications in customer_groups.items():
            # إضافة زر لكل زبون مع عدد الشحنات المستلمة له
            button_text = f"📦 {customer_name} ({len(notifications)} شحنة)"
            callback_data = f"delivered_customer:{customer_name}"
            keyboard.append([InlineKeyboardButton(button_text, callback_data=callback_data)])
        
        # إضافة زر لعرض الشحنات المؤرشفة
        keyboard.append([InlineKeyboardButton("🗄️ عرض الشحنات المؤرشفة", callback_data="show_archived_deliveries")])
        
        # إرسال ملخص إجمالي مع أزرار الزبائن
        reply_markup = InlineKeyboardMarkup(keyboard)
        summary_text = "📋 قائمة الزبائن الذين لديهم شحنات مستلمة ({} شحنة):\n\nاضغط على اسم الزبون لعرض تفاصيل وصور إثباتات الاستلام الخاصة به:".format(len(delivered))
        
        await message_method(summary_text, reply_markup=reply_markup)
    
    # للمستخدمين العاديين: عرض القائمة العادية
    else:
        # إنشاء نص القائمة
        list_text = strings.DELIVERED_NOTIFICATIONS_HEADER.format(count=len(delivered))
        
        for i, notification in enumerate(delivered, 1):
            customer_name = notification["customer_name"]
            phone_number = notification["phone_number"]
            
            delivered_at = "غير معروف"
            if notification.get("delivery_confirmed_at"):
                delivered_at = datetime.fromisoformat(notification["delivery_confirmed_at"]).strftime("%Y-%m-%d %H:%M")
            
            confirmed_by = notification.get("confirmed_by_username", "غير معروف")
            
            list_text += strings.DELIVERED_NOTIFICATION_ITEM.format(
                index=i,
                customer_name=customer_name,
                phone_number=phone_number,
                delivered_at=delivered_at,
                confirmed_by=confirmed_by
            )
        
        # إرسال القائمة
        await update.message.reply_text(list_text)

async def handle_delivered_customer(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """التعامل مع اختيار زبون معين من قائمة الزبائن الذين لديهم إشعارات مستلمة"""
    query = update.callback_query
    await query.answer()

    # الحصول على اسم الزبون من callback_data
    customer_name = query.data.split(":")[1]
    
    # الحصول على جميع إشعارات هذا الزبون المستلمة
    delivered = db_manager.get_delivered_notifications()
    
    # فلترة الإشعارات حسب اسم الزبون
    customer_notifications = [n for n in delivered if n["customer_name"] == customer_name]
    
    if not customer_notifications:
        await query.message.reply_text(f"لم يتم العثور على إشعارات مستلمة للزبون {customer_name}.")
        return
    
    # إرسال رسالة تفاصيل المجموعة
    await query.message.reply_text(f"🔹 تفاصيل طلبات {customer_name} المستلمة ({len(customer_notifications)} شحنة):")
    
    # إرسال تفاصيل كل إشعار مع زر الأرشفة
    for i, notification in enumerate(customer_notifications, 1):
        notification_id = notification["id"]
        phone_number = notification["phone_number"]
        delivered_at = "غير معروف"
        if notification.get("delivery_confirmed_at"):
            delivered_at = datetime.fromisoformat(notification["delivery_confirmed_at"]).strftime("%Y-%m-%d %H:%M")
        
        confirmed_by = notification.get("confirmed_by_username", "غير معروف")
        
        detail_text = f"{i}. هاتف: {phone_number}\n"
        detail_text += f"⏱ تاريخ الاستلام: {delivered_at}\n"
        detail_text += f"👤 بواسطة: {confirmed_by}"
        
        # إنشاء زر أرشفة لهذا الإشعار
        archive_button = InlineKeyboardButton(
            "🗄️ أرشفة هذا الإشعار", 
            callback_data=f"archive_notification:{notification_id}"
        )
        reply_markup = InlineKeyboardMarkup([[archive_button]])
        
        # إرسال صورة إثبات الاستلام إذا وجدت
        proof_image_path = f"data/images/{notification_id}_proof.jpg"
        if os.path.exists(proof_image_path):
            try:
                await query.message.reply_photo(
                    photo=open(proof_image_path, "rb"),
                    caption=f"🖼️ صورة إثبات استلام لـ {customer_name}\n{detail_text}",
                    reply_markup=reply_markup
                )
            except Exception as e:
                logging.error(f"خطأ في إرسال صورة إثبات الاستلام: {e}")
                # إرسال النص فقط في حالة فشل إرسال الصورة
                await query.message.reply_text(
                    f"🔹 {customer_name}\n{detail_text}\n(تعذر عرض صورة الإثبات)",
                    reply_markup=reply_markup
                )
        else:
            # لا توجد صورة إثبات
            await query.message.reply_text(
                f"🔹 {customer_name}\n{detail_text}\n(لا توجد صورة إثبات)",
                reply_markup=reply_markup
            )
    
    # إضافة زر العودة إلى القائمة الرئيسية
    back_button = InlineKeyboardButton("🔙 العودة للقائمة الرئيسية", callback_data="back_to_delivered_list")
    await query.message.reply_text(
        "استخدم الأزرار أعلاه لأرشفة الإشعارات بعد التحقق منها.",
        reply_markup=InlineKeyboardMarkup([[back_button]])
    )

async def handle_archive_notification(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """التعامل مع طلب أرشفة إشعار مستلم"""
    query = update.callback_query
    await query.answer()
    
    # الحصول على معرف الإشعار من callback_data
    notification_id = query.data.split(":")[1]
    user_id = update.effective_user.id
    
    # أرشفة الإشعار
    success = db_manager.archive_notification(notification_id, user_id)
    
    if success:
        # تحديث رسالة الزر ليظهر أنه تمت الأرشفة
        await query.edit_message_reply_markup(
            reply_markup=InlineKeyboardMarkup([[
                InlineKeyboardButton("✅ تمت الأرشفة", callback_data=f"notification_archived:{notification_id}")
            ]])
        )
        await query.message.reply_text("✅ تمت أرشفة الإشعار بنجاح.")
    else:
        await query.message.reply_text("❌ حدث خطأ أثناء أرشفة الإشعار. يرجى المحاولة مرة أخرى.")

async def handle_show_archived(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """عرض الإشعارات المؤرشفة"""
    query = update.callback_query
    await query.answer()
    
    # الحصول على الإشعارات المؤرشفة
    archived = db_manager.get_archived_notifications()
    
    if not archived:
        await query.message.reply_text("لا توجد إشعارات مؤرشفة.")
        return
    
    # تجميع الإشعارات حسب اسم العميل
    customer_groups = {}
    for notification in archived:
        customer_name = notification["customer_name"]
        if customer_name not in customer_groups:
            customer_groups[customer_name] = []
        customer_groups[customer_name].append(notification)
    
    # إرسال ملخص إجمالي
    summary_text = f"🗄️ قائمة الشحنات المؤرشفة ({len(archived)} شحنة):\n\n"
    for customer_name, notifications in customer_groups.items():
        summary_text += f"🔹 {customer_name} ({len(notifications)} شحنة)\n"
    
    # إنشاء أزرار للعودة
    back_button = InlineKeyboardButton("🔙 العودة للقائمة الرئيسية", callback_data="back_to_delivered_list")
    
    await query.message.reply_text(
        summary_text,
        reply_markup=InlineKeyboardMarkup([[back_button]])
    )
    
    # إرسال تفاصيل كل مجموعة
    for customer_name, notifications in customer_groups.items():
        # إرسال رسالة تفاصيل المجموعة
        await query.message.reply_text(f"🗄️ تفاصيل طلبات {customer_name} المؤرشفة ({len(notifications)} شحنة):")
        
        for i, notification in enumerate(notifications, 1):
            notification_id = notification["id"]
            phone_number = notification["phone_number"]
            delivered_at = "غير معروف"
            if notification.get("delivery_confirmed_at"):
                delivered_at = datetime.fromisoformat(notification["delivery_confirmed_at"]).strftime("%Y-%m-%d %H:%M")
            
            archived_at = "غير معروف"
            if notification.get("archived_at"):
                archived_at = datetime.fromisoformat(notification["archived_at"]).strftime("%Y-%m-%d %H:%M")
            
            confirmed_by = notification.get("confirmed_by_username", "غير معروف")
            archived_by = notification.get("archived_by_username", "غير معروف")
            
            detail_text = f"{i}. هاتف: {phone_number}\n"
            detail_text += f"⏱ تاريخ الاستلام: {delivered_at}\n"
            detail_text += f"👤 بواسطة: {confirmed_by}\n"
            detail_text += f"📂 تاريخ الأرشفة: {archived_at}\n"
            detail_text += f"👤 تمت الأرشفة بواسطة: {archived_by}"
            
            # إنشاء زر إلغاء الأرشفة
            unarchive_button = InlineKeyboardButton(
                "↩️ إلغاء الأرشفة", 
                callback_data=f"unarchive_notification:{notification_id}"
            )
            reply_markup = InlineKeyboardMarkup([[unarchive_button]])
            
            await query.message.reply_text(
                f"🗄️ {customer_name}\n{detail_text}",
                reply_markup=reply_markup
            )

async def handle_unarchive_notification(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """التعامل مع طلب إلغاء أرشفة إشعار"""
    query = update.callback_query
    await query.answer()
    
    # الحصول على معرف الإشعار من callback_data
    notification_id = query.data.split(":")[1]
    
    # إلغاء أرشفة الإشعار
    success = db_manager.unarchive_notification(notification_id)
    
    if success:
        # تحديث رسالة الزر ليظهر أنه تم إلغاء الأرشفة
        await query.edit_message_reply_markup(
            reply_markup=InlineKeyboardMarkup([[
                InlineKeyboardButton("✅ تم إلغاء الأرشفة", callback_data=f"notification_unarchived:{notification_id}")
            ]])
        )
        await query.message.reply_text("✅ تم إلغاء أرشفة الإشعار بنجاح.")
    else:
        await query.message.reply_text("❌ حدث خطأ أثناء إلغاء أرشفة الإشعار. يرجى المحاولة مرة أخرى.")

async def cancel_delivery(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """إلغاء عملية تأكيد التسليم"""
    # مسح بيانات السياق
    if "confirm_delivery" in context.user_data:
        del context.user_data["confirm_delivery"]
    
    # إرسال رسالة الإلغاء إذا كان update.callback_query هو None
    if not update.callback_query:
        # استخدام الدالة المساعدة لعرض زر القائمة الرئيسية
        await show_main_menu_on_error(update, context, strings.DELIVERY_CONFIRMATION_CANCELLED)
    else:
        # في حالة callback_query، لا يمكننا استخدام الدالة المساعدة مباشرة
        # ولكننا سنضيف زر القائمة الرئيسية في الاستجابة التالية (يتم التعامل معها في المكان الذي تم استدعاء cancel_delivery منه)
        pass
        
    return ConversationHandler.END

def get_delivery_handlers():
    """الحصول على معالجات تأكيد التسليم"""
    delivery_conv_handler = ConversationHandler(
        entry_points=[
            CommandHandler("confirm_delivery", confirm_delivery_command),
            MessageHandler(filters.Regex(f"^{strings.CONFIRM_DELIVERY_BUTTON}$"), confirm_delivery_command)
        ],
        states={
            SEARCH_METHOD: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, search_method_handler)
            ],
            ENTER_CUSTOMER_NAME: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, customer_name_handler)
            ],
            ENTER_PHONE_NUMBER: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, phone_number_handler)
            ],
            SELECT_NOTIFICATION: [
                CallbackQueryHandler(notification_selected_handler, pattern=f"^{DELIVERY_SELECT_PREFIX}"),
                CallbackQueryHandler(confirm_delivery_final_handler, pattern=f"^{DELIVERY_CONFIRM_PREFIX}"),
                CallbackQueryHandler(cancel_delivery, pattern=f"^{DELIVERY_CANCEL}$")
            ],
            UPLOAD_PROOF_IMAGE: [
                MessageHandler(filters.PHOTO, proof_image_handler),
                MessageHandler(filters.TEXT & ~filters.COMMAND, lambda u, c: u.message.reply_text(strings.NOT_AN_IMAGE))
            ],
            ENTER_NOTES: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, notes_handler)
            ]
        },
        fallbacks=[
            CommandHandler("cancel", cancel_delivery),
            MessageHandler(filters.Regex(f"^{strings.CANCEL_BUTTON}$"), cancel_delivery)
        ],
        name="delivery_confirmation",
        persistent=False
    )
    
    return [
        delivery_conv_handler,
        CommandHandler("delivered", list_delivered_notifications),
        MessageHandler(filters.Regex(f"^{strings.LIST_DELIVERED_BUTTON}$"), list_delivered_notifications),
        CallbackQueryHandler(handle_delivered_customer, pattern="^delivered_customer:"),
        CallbackQueryHandler(handle_show_archived, pattern="^show_archived_deliveries$"),
        CallbackQueryHandler(handle_archive_notification, pattern="^archive_notification:"),
        CallbackQueryHandler(handle_unarchive_notification, pattern="^unarchive_notification:"),
        CallbackQueryHandler(list_delivered_notifications, pattern="^back_to_delivered_list$")
    ]