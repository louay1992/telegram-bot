import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, ReplyKeyboardMarkup, KeyboardButton
from telegram.ext import (
    ConversationHandler, CommandHandler, MessageHandler, CallbackQueryHandler,
    ContextTypes, filters
)

import database as db
import strings as st
import utils
import input_validator as validator

# Conversation states
NAME, PHONE, IMAGE, REMINDER_HOURS = range(1, 5)
AWAITING_ADMIN_ID, AWAITING_ADMIN_ACTION = range(6, 8)
AWAITING_TEMPLATE_TEXT = 1
# States for editing notifications
AWAITING_EDIT_NAME, AWAITING_EDIT_PHONE, AWAITING_EDIT_IMAGE = range(10, 13)
# States for searching notifications
AWAITING_SEARCH_NAME, AWAITING_SEARCH_PHONE = range(20, 22)
# State for welcome message template editing
AWAITING_WELCOME_TEMPLATE_TEXT = 30
# State for verification message template editing
AWAITING_VERIFICATION_TEMPLATE_TEXT = 31

async def add_notification(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Start the process of adding a new notification."""
    # Check if user is admin
    if not db.is_admin(update.effective_user.id):
        await update.message.reply_text(st.NOT_AUTHORIZED)
        return ConversationHandler.END

    # Clear any existing conversation data
    context.user_data.clear()
    
    # Set the conversation state explicitly in user_data
    context.user_data['conversation_state'] = NAME
    logging.info(f"Starting add notification conversation, name state: {NAME}")

    # Ask for customer name directly
    await update.message.reply_text(st.ADD_NOTIFICATION_NAME)
    return NAME

async def received_name(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle received customer name."""
    name = update.message.text
    user = update.effective_user
    
    # Check if this is a cancel request
    if "إلغاء العملية" in name:
        logging.info(f"Cancel command detected during name input: '{name}'")
        context.user_data.clear()
        await update.message.reply_text(st.ADD_NOTIFICATION_CANCEL)
        return ConversationHandler.END
    
    # Enhanced logging for debugging name issues
    logging.info(f"Name received from user {user.id} ({user.username or 'No username'})")
    logging.info(f"Name content: '{name}'")
    logging.info(f"Name length: {len(name)}")
    
    # Use the validator function
    if not validator.is_valid_name(name):
        logging.info(f"Name validation failed using validator function")
        await update.message.reply_text(st.INVALID_NAME)
        return NAME
    
    # Log and store the name
    logging.info(f"Name validation passed using validator function, storing name: '{name}'")
    context.user_data["customer_name"] = name
    
    # Update conversation state
    context.user_data['conversation_state'] = PHONE
    logging.info(f"Updated conversation state to PHONE: {PHONE}")
    
    # Ask for phone number
    await update.message.reply_text(st.ADD_NOTIFICATION_PHONE)
    return PHONE

async def received_phone(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle received phone number."""
    phone = update.message.text
    
    # Check if this is a cancel request
    if "إلغاء العملية" in phone:
        logging.info(f"Cancel command detected during phone input: '{phone}'")
        context.user_data.clear()
        await update.message.reply_text(st.ADD_NOTIFICATION_CANCEL)
        return ConversationHandler.END
    
    # تسجيل معلومات رقم الهاتف الأصلي للمساعدة في التشخيص
    logging.info(f"Original phone input: '{phone}'")
    
    # Use our phone validator with improved formatting
    is_valid, formatted_phone = validator.is_valid_phone(phone)
    logging.info(f"Received phone: '{phone}', formatted: '{formatted_phone}', valid: {is_valid}")
    
    if not is_valid:
        # This only happens if there are no digits at all
        await update.message.reply_text(st.INVALID_PHONE)
        return PHONE
    
    # Store the formatted phone number with country code
    context.user_data["phone_number"] = formatted_phone
    logging.info(f"Phone stored: '{formatted_phone}'")
    
    # إعلام المستخدم بالرقم بعد تنسيقه
    await update.message.reply_text(f"✅ تم حفظ رقم الهاتف: {formatted_phone}")
    
    # Update conversation state
    context.user_data['conversation_state'] = IMAGE
    logging.info(f"Updated conversation state to IMAGE: {IMAGE}")

    # Ask for the image
    await update.message.reply_text(st.ADD_NOTIFICATION_IMAGE)
    return IMAGE

async def received_image(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle received notification image."""
    try:
        # Enhanced logging for image processing
        logging.info(f"Starting image processing")
        
        # Get the largest available photo
        photo = update.message.photo[-1]
        logging.info(f"Received photo with file_id: {photo.file_id}")
        
        # Download the photo
        file = await context.bot.get_file(photo.file_id)
        image_bytes = await file.download_as_bytearray()
        logging.info(f"Downloaded image, size: {len(image_bytes)} bytes")
        
        # Store the image data in context
        context.user_data["image_bytes"] = image_bytes
        
        # التحقق إذا كانت البيانات المطلوبة متوفرة
        if "customer_name" not in context.user_data or "phone_number" not in context.user_data:
            logging.error("Missing customer_name or phone_number in user_data")
            logging.info(f"Available user_data keys: {list(context.user_data.keys())}")
            
            # في حالة عدم وجود اسم العميل، اطلب من المستخدم إدخاله
            if "customer_name" not in context.user_data:
                await update.message.reply_text("⚠️ يرجى إدخال اسم العميل أولاً.\n" + st.ADD_NOTIFICATION_NAME)
                context.user_data['conversation_state'] = NAME
                return NAME
            
            # في حالة عدم وجود رقم الهاتف، اطلب من المستخدم إدخاله
            if "phone_number" not in context.user_data:
                await update.message.reply_text("⚠️ يرجى إدخال رقم هاتف العميل.\n" + st.ADD_NOTIFICATION_PHONE)
                context.user_data['conversation_state'] = PHONE
                return PHONE
                
            await update.message.reply_text("⚠️ حدث خطأ: بيانات العميل غير مكتملة. يرجى إعادة المحاولة.")
            return ConversationHandler.END
        
        # تم استلام الصورة وجميع البيانات المطلوبة متوفرة
        # Log customer info for debugging
        logging.info(f"Processing image for customer: {context.user_data.get('customer_name', 'MISSING')} | Phone: {context.user_data.get('phone_number', 'MISSING')}")
        
        # عرض ملخص المعلومات
        message = "✅ تم استلام الصورة بنجاح!\n\n"
        message += f"اسم العميل: {context.user_data['customer_name']}\n"
        message += f"رقم الهاتف: {context.user_data['phone_number']}\n"
        
        await update.message.reply_text(message)
        
        # Update conversation state
        context.user_data['conversation_state'] = REMINDER_HOURS
        logging.info(f"Updated conversation state to REMINDER_HOURS: {REMINDER_HOURS}")
        
        # Ask for reminder hours
        await update.message.reply_text(st.REMINDER_HOURS_PROMPT)
        return REMINDER_HOURS
    except Exception as e:
        logging.error(f"Error processing image: {e}")
        import traceback
        logging.error(traceback.format_exc())
        await update.message.reply_text(st.IMAGE_ERROR)
        return ConversationHandler.END

async def received_reminder_hours(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle received reminder hours (now in minutes for testing)."""
    try:
        reminder_text = update.message.text
        
        # Check if this is a cancel request
        if "إلغاء العملية" in reminder_text:
            logging.info(f"Cancel command detected during reminder input: '{reminder_text}'")
            context.user_data.clear()
            await update.message.reply_text(st.ADD_NOTIFICATION_CANCEL)
            return ConversationHandler.END
        
        # Try to parse the reminder days
        try:
            reminder_days = int(reminder_text.strip())
            
            # حد للقيمة: 0-30 يوم
            if reminder_days < 0 or reminder_days > 30:
                await update.message.reply_text(st.REMINDER_HOURS_INVALID)
                return REMINDER_HOURS
                
            # تحويل الأيام إلى ساعات لقاعدة البيانات
            reminder_hours = reminder_days * 24.0  # كل يوم 24 ساعة
            
        except ValueError:
            await update.message.reply_text(st.REMINDER_HOURS_INVALID)
            return REMINDER_HOURS
        
        # Add the notification to the database with reminder setting
        success, result = db.add_notification(
            context.user_data["customer_name"],
            context.user_data["phone_number"],
            context.user_data["image_bytes"],
            reminder_hours  # تمرير القيمة كساعات لكن قمنا بتحويلها من أيام
        )
        
        logging.info(f"Database add result: success={success}, result={result}")
        
        if success:
            # إرسال رسالة ترحيبية فورية للعميل
            notification_id = result
            customer_name = context.user_data["customer_name"]
            phone_number = context.user_data["phone_number"]
            
            # استدعاء دالة إرسال الرسالة الترحيبية الفورية
            import ultramsg_service
            welcome_success, welcome_result = ultramsg_service.send_welcome_message(
                customer_name, 
                phone_number, 
                notification_id
            )
            
            # Provide feedback about the reminder
            reminder_message = ""
            if reminder_days > 0:
                reminder_message = st.REMINDER_SCHEDULED.format(reminder_days)
                logging.info(f"Reminder scheduled for {reminder_days} days (stored as {reminder_hours} hours)")
            else:
                reminder_message = st.REMINDER_DISABLED
            
            # إعداد رسالة تأكيد إرسال الترحيب
            welcome_message = ""
            if welcome_success:
                welcome_message = st.WELCOME_MESSAGE_SENT
                logging.info(f"Welcome message sent successfully to {customer_name} ({phone_number})")
            else:
                welcome_message = st.WELCOME_MESSAGE_FAILED.format(str(welcome_result))
                logging.error(f"Failed to send welcome message to {customer_name}: {welcome_result}")
                
            # Clear conversation state
            context.user_data.clear()
            await update.message.reply_text(f"{st.ADD_NOTIFICATION_SUCCESS}\n\n{welcome_message}\n\n{reminder_message}\n\n{st.WHATSAPP_NOTICE}")
        else:
            await update.message.reply_text(f"⚠️ حدث خطأ: {result}")
        
        # Return to conversation end
        return ConversationHandler.END
    except Exception as e:
        logging.error(f"Error processing reminder hours: {e}")
        import traceback
        logging.error(traceback.format_exc())
        await update.message.reply_text(st.GENERAL_ERROR)
        return ConversationHandler.END

async def cancel_add(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Cancel the conversation."""
    context.user_data.clear()
    await update.message.reply_text(st.ADD_NOTIFICATION_CANCEL)
    return ConversationHandler.END

async def list_notifications(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """List all notifications."""
    # Check if user is admin
    if not db.is_admin(update.effective_user.id):
        await update.message.reply_text(st.NOT_AUTHORIZED)
        return

    notifications = db.get_all_notifications()
    
    if not notifications:
        await update.message.reply_text(st.LIST_NOTIFICATIONS_EMPTY)
        return
    
    # إضافة أزرار البحث
    search_buttons = [
        [
            InlineKeyboardButton("🔍 بحث حسب الاسم", callback_data="search_by_name"),
            InlineKeyboardButton("🔍 بحث حسب الرقم", callback_data="search_by_phone")
        ]
    ]
    
    # Set up pagination
    page = 1
    keyboard = utils.create_paginated_keyboard(notifications, page, "admin", extra_buttons=search_buttons)
    
    await update.message.reply_text(
        f"{st.LIST_NOTIFICATIONS_HEADER}\n"
        f"إجمالي الإشعارات: {len(notifications)}",
        reply_markup=keyboard
    )

async def handle_admin_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle callback queries for admin pagination."""
    query = update.callback_query
    
    # تسجيل تفصيلي للتمكن من تتبع المشاكل
    logging.info(f"🔴 Admin callback received: {query.data}")
    
    # محاولة معالجة الاستدعاء الواردة
    try:
        await query.answer("جاري المعالجة...")
    except Exception as e:
        logging.error(f"Error answering query: {e}")
        
    # تسجيل معلومات إضافية للتشخيص
    user_id = update.effective_user.id
    chat_id = update.effective_chat.id
    logging.info(f"Callback from user_id={user_id}, chat_id={chat_id}, data={query.data}")
    
    # Handle reset admins confirmation
    if query.data == "confirm_reset_admins":
        # Check if user is main admin (double check)
        if not db.is_main_admin(update.effective_user.id):
            await query.message.reply_text(st.MAIN_ADMIN_ONLY)
            return
        
        # Delete all admins
        if db.delete_all_admins():
            await query.edit_message_text(st.RESET_ADMINS_SUCCESS)
        else:
            await query.edit_message_text(st.RESET_ADMINS_ERROR)
        return
    
    # Handle cancel reset admins
    if query.data == "cancel_reset_admins":
        await query.edit_message_text("تم إلغاء عملية حذف المسؤولين.")
        return
    
    # Check if user is admin for other admin operations
    if not db.is_admin(update.effective_user.id):
        await query.message.reply_text(st.NOT_AUTHORIZED)
        return
    
    # بدء عمليات البحث - تم تغيير الأسماء لتتوافق مع الأزرار الجديدة
    if query.data == "search_by_name":
        await query.message.reply_text("🔍 أدخل اسم العميل للبحث:")
        context.user_data['search_type'] = 'اسم'
        return AWAITING_SEARCH_NAME
        
    if query.data == "search_by_phone":
        await query.message.reply_text("🔍 أدخل رقم هاتف العميل للبحث:")
        context.user_data['search_type'] = 'هاتف'
        return AWAITING_SEARCH_PHONE
        
    if query.data == "admin_search_history":
        from search_history_handlers import view_search_history
        return await view_search_history(update, context)
    
    data = query.data.split("_")
    
    if data[0] != "admin":
        logging.info(f"Ignoring non-admin callback: {query.data}")
        return
    
    if data[1] == "page":
        # Handle pagination
        page = int(data[2])
        notifications = db.get_all_notifications()
        
        # إضافة أزرار البحث
        search_buttons = [
            [
                InlineKeyboardButton("🔍 بحث حسب الاسم", callback_data="search_by_name"),
                InlineKeyboardButton("🔍 بحث حسب الرقم", callback_data="search_by_phone")
            ],
            [
                InlineKeyboardButton("📋 سجلات البحث السابقة", callback_data="admin_search_history")
            ]
        ]
        
        keyboard = utils.create_paginated_keyboard(notifications, page, "admin", extra_buttons=search_buttons)
        
        await query.edit_message_text(
            f"{st.LIST_NOTIFICATIONS_HEADER}\n"
            f"إجمالي الإشعارات: {len(notifications)}",
            reply_markup=keyboard
        )
    
    elif data[1] == "view":
        # View notification details
        notification_id = data[2]
        logging.info(f"Viewing notification with ID: {notification_id}")
        
        # تحميل قائمة الإشعارات
        notifications = db.get_all_notifications()
        logging.info(f"Found {len(notifications)} notifications in database")
        
        # البحث عن الإشعار بالمعرف
        notification = next((n for n in notifications if n["id"] == notification_id), None)
        
        if not notification:
            logging.warning(f"⚠️ Notification not found with ID: {notification_id}")
            await query.message.reply_text("⚠️ لم يتم العثور على الإشعار!")
            return
        
        # تسجيل بيانات الإشعار المطلوب
        logging.info(f"Found notification: {notification['customer_name']} - {notification['phone_number']}")
        
        # Create keyboard for actions
        keyboard = [
            [
                InlineKeyboardButton("✏️ تعديل الاسم", callback_data=f"admin_edit_name_{notification_id}"),
                InlineKeyboardButton("📱 تعديل الرقم", callback_data=f"admin_edit_phone_{notification_id}")
            ],
            [
                InlineKeyboardButton("🖼️ تعديل الصورة", callback_data=f"admin_edit_image_{notification_id}"),
                InlineKeyboardButton("🗑️ حذف الإشعار", callback_data=f"admin_delete_{notification_id}")
            ],
            [
                InlineKeyboardButton(st.SEND_VERIFICATION_MESSAGE, callback_data=f"send_verification_{notification_id}")
            ]
        ]
        
        # Display notification details
        details = utils.format_notification_details(notification)
        logging.info(f"Formatted notification details: {details}")
        
        # Get the image
        try:
            image_data = db.get_image(notification_id)
            if image_data:
                logging.info(f"Image found for notification {notification_id}, size: {len(image_data)} bytes")
                await utils.send_image_with_caption(
                    update, context, 
                    photo=image_data, 
                    caption=details,
                    reply_markup=InlineKeyboardMarkup(keyboard)
                )
            else:
                logging.warning(f"No image found for notification {notification_id}")
                await query.message.reply_text(
                    details + "\n\n⚠️ الصورة غير متوفرة!",
                    reply_markup=InlineKeyboardMarkup(keyboard)
                )
        except Exception as e:
            # تسجيل أي خطأ قد يحدث أثناء استرجاع الصورة
            logging.error(f"Error fetching image for notification {notification_id}: {e}")
            import traceback
            logging.error(traceback.format_exc())
            
            # إرسال رسالة لإعلام المستخدم بوجود خطأ
            await query.message.reply_text(
                details + "\n\n⚠️ حدث خطأ أثناء استرجاع الصورة!",
                reply_markup=InlineKeyboardMarkup(keyboard)
            )
    
    elif data[1] == "delete":
        # Delete notification
        notification_id = data[2]
        
        # Create confirmation keyboard
        keyboard = [
            [
                InlineKeyboardButton("✅ تأكيد", callback_data=f"admin_confirm_delete_{notification_id}"),
                InlineKeyboardButton("❌ إلغاء", callback_data="admin_cancel_delete")
            ]
        ]
        
        # نستخدم reply_text بدلاً من edit_message_text
        # لأن الرسالة قد تكون صورة فقط بدون نص
        await query.message.reply_text(
            "هل أنت متأكد من حذف هذا الإشعار؟",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
        # إغلاق الاستعلام لتجنب أيقونة التحميل
        await query.answer()
    
    elif data[1] == "confirm" and data[2] == "delete":
        # Confirm deletion
        notification_id = data[3]
        
        if db.delete_notification(notification_id):
            await query.message.reply_text(st.DELETE_NOTIFICATION_SUCCESS)
            await query.answer("تم الحذف بنجاح")
        else:
            await query.message.reply_text(st.DELETE_NOTIFICATION_ERROR)
            await query.answer("حدث خطأ أثناء الحذف")
    
    elif data[1] == "cancel" and data[2] == "delete":
        # Cancel deletion
        await query.message.reply_text("تم إلغاء عملية الحذف.")
        await query.answer("تم الإلغاء")
        
    # معالجة طلبات تعديل الإشعارات - تعديل للدعم الكامل للأنماط الجديدة
    elif (data[1] == "edit" and len(data) >= 4) or data[1] in ["edit_name", "edit_phone", "edit_image"]:
        # دعم كل من النمط القديم (admin_edit_الاسم_المعرف) والنمط الجديد (admin_edit_name_المعرف)
        if data[1] == "edit":
            # النمط القديم
            edit_type = data[2]  # نوع التعديل (الاسم، الرقم، الصورة)
            notification_id = data[3]  # معرف الإشعار
        else:
            # النمط الجديد (admin_edit_name_id)
            edit_type = data[1].replace("edit_", "")  # استخراج نوع التعديل من الاستدعاء (name, phone, image)
            notification_id = data[2]  # معرف الإشعار
        
        logging.info(f"Processing edit request: type={edit_type}, notification_id={notification_id}")
        
        # حفظ معرف الإشعار في البيانات المؤقتة للمستخدم
        context.user_data['edit_notification_id'] = notification_id
        
        # نستخدم reply_text بدلاً من edit_message_text
        # لأن الرسالة قد تكون صورة فقط بدون نص
        if edit_type == "name":
            # بدء عملية تعديل الاسم
            await query.message.reply_text(st.EDIT_NAME_PROMPT)
            # إغلاق الاستعلام لتجنب أيقونة التحميل
            await query.answer()
            return AWAITING_EDIT_NAME
            
        elif edit_type == "phone":
            # بدء عملية تعديل رقم الهاتف
            await query.message.reply_text(st.EDIT_PHONE_PROMPT)
            # إغلاق الاستعلام لتجنب أيقونة التحميل
            await query.answer()
            return AWAITING_EDIT_PHONE
            
        elif edit_type == "image":
            # بدء عملية تعديل الصورة
            await query.message.reply_text(st.EDIT_IMAGE_PROMPT)
            # إغلاق الاستعلام لتجنب أيقونة التحميل
            await query.answer()
            return AWAITING_EDIT_IMAGE

async def admin_help(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Display admin help message."""
    # Check if user is admin
    if not db.is_admin(update.effective_user.id):
        await update.message.reply_text(st.NOT_AUTHORIZED)
        return
    
    await update.message.reply_text(st.ADMIN_HELP_MESSAGE)

async def manage_admins(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show admin management options."""
    # Check if user is admin
    if not db.is_admin(update.effective_user.id):
        await update.message.reply_text(st.NOT_AUTHORIZED)
        return
    
    # Special option for main admin only
    is_main_admin = db.is_main_admin(update.effective_user.id)
    
    keyboard = [
        [InlineKeyboardButton("👥 عرض المسؤولين", callback_data="admin_manage_list")],
        [InlineKeyboardButton("➕ إضافة مسؤول", callback_data="admin_manage_add")],
        [InlineKeyboardButton("➖ إزالة مسؤول", callback_data="admin_manage_remove")]
    ]
    
    # Add reset admins button only for main admin
    if is_main_admin:
        keyboard.append([InlineKeyboardButton("🔄 إعادة تعيين المسؤولين", callback_data="admin_manage_reset")])
    
    await update.message.reply_text(
        "إدارة المسؤولين:",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

async def add_admin_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Start the process of adding a new admin."""
    # Check if user is main admin
    if not db.is_main_admin(update.effective_user.id):
        await update.message.reply_text("⚠️ هذا الأمر متاح فقط للمسؤول الرئيسي.")
        return ConversationHandler.END
    
    context.user_data['admin_action'] = 'add'
    
    await update.message.reply_text(
        "لإضافة مسؤول جديد، يرجى توجيه رسالة من المستخدم أو إدخال معرف المستخدم مباشرة."
    )
    
    return AWAITING_ADMIN_ID

async def remove_admin_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Start the process of removing an admin."""
    # Check if user is main admin
    if not db.is_main_admin(update.effective_user.id):
        await update.message.reply_text("⚠️ هذا الأمر متاح فقط للمسؤول الرئيسي.")
        return ConversationHandler.END
    
    context.user_data['admin_action'] = 'remove'
    
    await update.message.reply_text(
        "لإزالة مسؤول، يرجى توجيه رسالة من المستخدم أو إدخال معرف المستخدم مباشرة."
    )
    
    return AWAITING_ADMIN_ID

async def list_admins(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """List all admins."""
    # Check if user is admin
    if not db.is_admin(update.effective_user.id):
        await update.message.reply_text(st.NOT_AUTHORIZED)
        return
    
    admins = db.get_all_admins()
    
    if not admins:
        await update.message.reply_text("⚠️ لا يوجد مسؤولين في النظام!")
        return
    
    # Format admin list
    text = "👥 قائمة المسؤولين:\n\n"
    
    for i, admin in enumerate(admins, 1):
        status = "👑 مسؤول رئيسي" if admin.get("is_main", False) else "👤 مسؤول"
        text += f"{i}. {status}: {admin['id']}\n"
    
    await update.message.reply_text(text)

async def reset_admins(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Reset all admins - remove all admins from the system."""
    user_id = update.effective_user.id
    
    # Only the main admin can reset all admins
    if not db.is_main_admin(user_id):
        await update.message.reply_text(st.MAIN_ADMIN_ONLY)
        return
    
    # Ask for confirmation
    keyboard = [
        [
            InlineKeyboardButton("✅ نعم، حذف جميع المسؤولين", callback_data="confirm_reset_admins"),
            InlineKeyboardButton("❌ لا، إلغاء العملية", callback_data="cancel_reset_admins")
        ]
    ]
    
    await update.message.reply_text(
        "⚠️ هل أنت متأكد من حذف جميع المسؤولين؟\n" +
        "هذا سيحذف جميع المسؤولين بما فيهم المسؤول الرئيسي،\n" +
        "وسيتم تعيين أول مستخدم يدخل للبوت كمسؤول رئيسي جديد.",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

async def process_admin_id(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Process the received admin ID."""
    admin_action = context.user_data.get('admin_action')
    
    if not admin_action:
        await update.message.reply_text("⚠️ حدث خطأ: نوع العملية غير محدد.")
        return ConversationHandler.END
    
    user_id = None
    
    # Check if it's a forwarded message
    if hasattr(update.message, 'forward_from') and update.message.forward_from:
        user_id = update.message.forward_from.id
    else:
        # Try to parse user ID from text
        try:
            user_id = int(update.message.text.strip())
        except ValueError:
            await update.message.reply_text("⚠️ معرف المستخدم غير صالح. الرجاء توجيه رسالة من المستخدم أو إدخال معرف المستخدم.")
            return AWAITING_ADMIN_ID
    
    if not user_id:
        await update.message.reply_text("⚠️ لم يتم العثور على معرف المستخدم. الرجاء توجيه رسالة من المستخدم أو إدخال معرف المستخدم.")
        return AWAITING_ADMIN_ID
    
    if admin_action == 'add':
        # Check if user is already an admin
        if db.is_admin(user_id):
            await update.message.reply_text(st.ADD_ADMIN_ALREADY)
        else:
            # Add user as admin
            if db.add_admin(user_id):
                await update.message.reply_text(f"{st.ADD_ADMIN_SUCCESS}\nمعرف المستخدم: {user_id}")
            else:
                await update.message.reply_text(st.ADD_ADMIN_ERROR)
    
    elif admin_action == 'remove':
        # Check if user is an admin
        if not db.is_admin(user_id):
            await update.message.reply_text(st.REMOVE_ADMIN_NOT_ADMIN)
        # Check if user is the main admin (cannot be removed)
        elif db.is_main_admin(user_id):
            await update.message.reply_text("⚠️ لا يمكن إزالة المسؤول الرئيسي.")
        else:
            # Remove user from admins
            if db.remove_admin(user_id):
                await update.message.reply_text(f"{st.REMOVE_ADMIN_SUCCESS}\nمعرف المستخدم: {user_id}")
            else:
                await update.message.reply_text(st.REMOVE_ADMIN_ERROR)
    
    return ConversationHandler.END

async def handle_admin_manage_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle callback queries for admin management."""
    query = update.callback_query
    await query.answer()
    
    # Check if user is admin
    if not db.is_admin(update.effective_user.id):
        await query.message.reply_text(st.NOT_AUTHORIZED)
        return
    
    data = query.data.split("_")
    
    if len(data) < 3 or data[0] != "admin" or data[1] != "manage":
        return
    
    action = data[2]
    
    if action == "list":
        # List admins
        admins = db.get_all_admins()
        
        if not admins:
            await query.edit_message_text("⚠️ لا يوجد مسؤولين في النظام!")
            return
        
        # Format admin list
        text = "👥 قائمة المسؤولين:\n\n"
        
        for i, admin in enumerate(admins, 1):
            status = "👑 مسؤول رئيسي" if admin.get("is_main", False) else "👤 مسؤول"
            text += f"{i}. {status}: {admin['id']}\n"
        
        await query.edit_message_text(text)
    
    elif action == "add":
        # Check if user is main admin
        if not db.is_main_admin(update.effective_user.id):
            await query.edit_message_text("⚠️ هذا الإجراء متاح فقط للمسؤول الرئيسي.")
            return
        
        # Start admin add process
        context.user_data['admin_action'] = 'add'
        
        await query.edit_message_text(
            "لإضافة مسؤول جديد، يرجى توجيه رسالة من المستخدم أو إدخال معرف المستخدم مباشرة."
        )
        
        return AWAITING_ADMIN_ID
    
    elif action == "remove":
        # Check if user is main admin
        if not db.is_main_admin(update.effective_user.id):
            await query.edit_message_text("⚠️ هذا الإجراء متاح فقط للمسؤول الرئيسي.")
            return
        
        # Start admin remove process
        context.user_data['admin_action'] = 'remove'
        
        await query.edit_message_text(
            "لإزالة مسؤول، يرجى توجيه رسالة من المستخدم أو إدخال معرف المستخدم مباشرة."
        )
        
        return AWAITING_ADMIN_ID
        
    elif action == "reset":
        # Check if user is main admin
        if not db.is_main_admin(update.effective_user.id):
            await query.edit_message_text("⚠️ هذا الإجراء متاح فقط للمسؤول الرئيسي.")
            return
        
        # Ask for confirmation
        keyboard = [
            [
                InlineKeyboardButton("✅ نعم، حذف جميع المسؤولين", callback_data="confirm_reset_admins"),
                InlineKeyboardButton("❌ لا، إلغاء العملية", callback_data="cancel_reset_admins")
            ]
        ]
        
        await query.edit_message_text(
            "⚠️ هل أنت متأكد من حذف جميع المسؤولين؟\n" +
            "هذا سيحذف جميع المسؤولين بما فيهم المسؤول الرئيسي،\n" +
            "وسيتم تعيين أول مستخدم يدخل للبوت كمسؤول رئيسي جديد.",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )

def get_add_notification_handler():
    """Return the conversation handler for adding notifications."""
    return ConversationHandler(
        entry_points=[
            CommandHandler('add', add_notification),
            MessageHandler(filters.Regex(r'.*إضافة إشعار.*'), add_notification)
        ],
        states={
            NAME: [MessageHandler(filters.TEXT & ~filters.COMMAND, received_name)],
            PHONE: [MessageHandler(filters.TEXT & ~filters.COMMAND, received_phone)],
            IMAGE: [MessageHandler(filters.PHOTO, received_image)],
            REMINDER_HOURS: [MessageHandler(filters.TEXT & ~filters.COMMAND, received_reminder_hours)]
        },
        fallbacks=[
            CommandHandler('cancel', cancel_add),
            MessageHandler(filters.Regex(r'.*إلغاء العملية.*'), cancel_add)
        ],
        name="add_notification"
    )

def get_admin_management_handler():
    """Return the conversation handler for admin management."""
    return ConversationHandler(
        entry_points=[
            CommandHandler('add_admin', add_admin_command),
            CommandHandler('remove_admin', remove_admin_command),
            CallbackQueryHandler(handle_admin_manage_callback, pattern=r'^admin_manage_')
        ],
        states={
            AWAITING_ADMIN_ID: [MessageHandler(filters.TEXT | filters.FORWARDED, process_admin_id)]
        },
        fallbacks=[CommandHandler('cancel', lambda u, c: ConversationHandler.END)],
        name="admin_management"
    )

# دوال معالجة تعديل الإشعارات
async def process_edit_name(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """معالجة تعديل اسم العميل في الإشعار."""
    # التحقق من أن المستخدم مسؤول
    if not db.is_admin(update.effective_user.id):
        await update.message.reply_text(st.NOT_AUTHORIZED)
        return ConversationHandler.END
    
    # الحصول على الاسم الجديد
    new_name = update.message.text.strip()
    
    # التحقق من صحة الاسم
    if not validator.is_valid_name(new_name):
        await update.message.reply_text(st.INVALID_NAME)
        return AWAITING_EDIT_NAME
    
    # الحصول على معرف الإشعار من البيانات المؤقتة
    notification_id = context.user_data.get('edit_notification_id')
    if not notification_id:
        await update.message.reply_text("⚠️ حدث خطأ: لم يتم العثور على معرف الإشعار.")
        return ConversationHandler.END
    
    # تحديث الاسم في قاعدة البيانات
    updates = {"customer_name": new_name}
    if db.update_notification(notification_id, updates):
        await update.message.reply_text(st.EDIT_NAME_SUCCESS.format(new_name))
    else:
        await update.message.reply_text(st.EDIT_ERROR)
    
    return ConversationHandler.END

async def process_edit_phone(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """معالجة تعديل رقم الهاتف في الإشعار."""
    # التحقق من أن المستخدم مسؤول
    if not db.is_admin(update.effective_user.id):
        await update.message.reply_text(st.NOT_AUTHORIZED)
        return ConversationHandler.END
    
    # الحصول على رقم الهاتف الجديد
    phone = update.message.text.strip()
    
    # التحقق من صحة رقم الهاتف
    is_valid, cleaned_phone = validator.is_valid_phone(phone)
    if not is_valid:
        await update.message.reply_text(st.INVALID_PHONE)
        return AWAITING_EDIT_PHONE
    
    # الحصول على معرف الإشعار من البيانات المؤقتة
    notification_id = context.user_data.get('edit_notification_id')
    if not notification_id:
        await update.message.reply_text("⚠️ حدث خطأ: لم يتم العثور على معرف الإشعار.")
        return ConversationHandler.END
    
    # تحديث رقم الهاتف في قاعدة البيانات
    updates = {"phone_number": cleaned_phone}
    if db.update_notification(notification_id, updates):
        await update.message.reply_text(st.EDIT_PHONE_SUCCESS.format(cleaned_phone))
    else:
        await update.message.reply_text(st.EDIT_ERROR)
    
    return ConversationHandler.END

async def process_edit_image(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """معالجة تعديل صورة الإشعار."""
    # التحقق من أن المستخدم مسؤول
    if not db.is_admin(update.effective_user.id):
        await update.message.reply_text(st.NOT_AUTHORIZED)
        return ConversationHandler.END
    
    # التحقق من وجود صورة
    if not update.message.photo:
        await update.message.reply_text("⚠️ يرجى إرسال صورة.")
        return AWAITING_EDIT_IMAGE
    
    try:
        # الحصول على أكبر نسخة متاحة من الصورة
        photo = update.message.photo[-1]
        
        # تنزيل الصورة
        file = await context.bot.get_file(photo.file_id)
        image_bytes = await file.download_as_bytearray()
        
        # الحصول على معرف الإشعار من البيانات المؤقتة
        notification_id = context.user_data.get('edit_notification_id')
        if not notification_id:
            await update.message.reply_text("⚠️ حدث خطأ: لم يتم العثور على معرف الإشعار.")
            return ConversationHandler.END
        
        # حفظ الصورة الجديدة
        db.save_image(image_bytes, notification_id)
        
        await update.message.reply_text(st.EDIT_IMAGE_SUCCESS)
    except Exception as e:
        logging.error(f"Error updating notification image: {e}")
        await update.message.reply_text(st.EDIT_ERROR)
    
    return ConversationHandler.END

async def message_template_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """إدارة قالب الرسالة النصية"""
    # التحقق مما إذا كان المستخدم مسؤولًا
    if not db.is_admin(update.effective_user.id):
        await update.message.reply_text(st.NOT_AUTHORIZED)
        return
    
    # إنشاء لوحة مفاتيح لإدارة قالب الرسالة
    keyboard = [
        [InlineKeyboardButton(st.VIEW_TEMPLATE, callback_data="template_view")],
        [InlineKeyboardButton(st.EDIT_TEMPLATE, callback_data="template_edit")],
        [InlineKeyboardButton(st.RESET_TEMPLATE, callback_data="template_reset")]
    ]
    
    await update.message.reply_text(
        st.MESSAGE_TEMPLATE_MENU,
        reply_markup=InlineKeyboardMarkup(keyboard)
    )
    
async def welcome_template_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """إدارة قالب الرسالة الترحيبية الفورية"""
    # التحقق مما إذا كان المستخدم مسؤولًا
    if not db.is_admin(update.effective_user.id):
        await update.message.reply_text(st.NOT_AUTHORIZED)
        return
    
    # إنشاء لوحة مفاتيح لإدارة قالب الرسالة الترحيبية
    keyboard = [
        [InlineKeyboardButton(st.VIEW_WELCOME_TEMPLATE, callback_data="welcome_template_view")],
        [InlineKeyboardButton(st.EDIT_WELCOME_TEMPLATE, callback_data="welcome_template_edit")],
        [InlineKeyboardButton(st.RESET_WELCOME_TEMPLATE, callback_data="welcome_template_reset")]
    ]
    
    await update.message.reply_text(
        st.WELCOME_TEMPLATE_MENU,
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

async def handle_template_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """معالجة ردود الاستعلام لإدارة قالب الرسالة"""
    query = update.callback_query
    await query.answer()
    
    # التحقق مما إذا كان المستخدم مسؤولًا
    if not db.is_admin(update.effective_user.id):
        await query.message.reply_text(st.NOT_AUTHORIZED)
        return
    
    action = query.data.split("_")[1]
    
    if action == "view":
        # عرض القالب الحالي
        template = db.get_message_template()
        await query.message.reply_text(
            st.CURRENT_TEMPLATE.format(template),
            parse_mode="Markdown"
        )
    
    elif action == "edit":
        # بدء عملية تحرير القالب
        context.user_data['template_action'] = 'edit'
        await query.message.reply_text(st.EDIT_TEMPLATE_PROMPT)
        return AWAITING_TEMPLATE_TEXT
    
    elif action == "reset":
        # إعادة ضبط القالب إلى الوضع الافتراضي
        if db.reset_message_template():
            template = db.get_message_template()
            await query.message.reply_text(
                f"{st.TEMPLATE_RESET}\n\n"
                f"القالب الجديد:\n```\n{template}\n```",
                parse_mode="Markdown"
            )
        else:
            await query.message.reply_text(st.TEMPLATE_ERROR)
            
async def handle_welcome_template_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """معالجة ردود الاستعلام لإدارة قالب الرسالة الترحيبية"""
    query = update.callback_query
    await query.answer()
    
    # التحقق مما إذا كان المستخدم مسؤولًا
    if not db.is_admin(update.effective_user.id):
        await query.message.reply_text(st.NOT_AUTHORIZED)
        return
    
    action = query.data.split("_")[2]  # welcome_template_view -> view
    
    if action == "view":
        # عرض القالب الحالي
        template = db.get_welcome_message_template()
        await query.message.reply_text(
            st.CURRENT_WELCOME_TEMPLATE.format(template),
            parse_mode="Markdown"
        )
    
    elif action == "edit":
        # بدء عملية تحرير القالب
        context.user_data['welcome_template_action'] = 'edit'
        await query.message.reply_text(st.EDIT_WELCOME_TEMPLATE_PROMPT)
        return AWAITING_WELCOME_TEMPLATE_TEXT
    
    elif action == "reset":
        # إعادة ضبط القالب إلى الوضع الافتراضي
        try:
            import config
            if db.update_welcome_message_template(config.DEFAULT_WELCOME_TEMPLATE):
                template = db.get_welcome_message_template()
                await query.message.reply_text(
                    f"{st.WELCOME_TEMPLATE_RESET}\n\n"
                    f"القالب الجديد:\n```\n{template}\n```",
                    parse_mode="Markdown"
                )
            else:
                await query.message.reply_text(st.WELCOME_TEMPLATE_ERROR)
        except Exception as e:
            logging.error(f"Error resetting welcome template: {e}")
            await query.message.reply_text(st.WELCOME_TEMPLATE_ERROR)

async def process_template_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """معالجة نص القالب المستلم."""
    template_text = update.message.text
    
    # التحقق مما إذا كان هذا طلب إلغاء
    if "إلغاء العملية" in template_text:
        context.user_data.clear()
        await update.message.reply_text("تم إلغاء تعديل القالب.")
        return ConversationHandler.END
    
    # التحقق من وجود المتغير المطلوب {customer_name}
    if "{customer_name}" not in template_text:
        await update.message.reply_text(
            "⚠️ القالب يجب أن يحتوي على المتغير {customer_name}. الرجاء إعادة المحاولة."
        )
        return AWAITING_TEMPLATE_TEXT
    
    # تحديث القالب
    if db.update_message_template(template_text):
        await update.message.reply_text(
            f"{st.TEMPLATE_UPDATED}\n\n"
            f"القالب الجديد:\n```\n{template_text}\n```",
            parse_mode="Markdown"
        )
    else:
        await update.message.reply_text(st.TEMPLATE_ERROR)
    
    # تنظيف بيانات المحادثة
    context.user_data.clear()
    return ConversationHandler.END
    
async def process_welcome_template_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """معالجة نص قالب الرسالة الترحيبية المستلم."""
    template_text = update.message.text
    
    # التحقق مما إذا كان هذا طلب إلغاء
    if "إلغاء العملية" in template_text:
        context.user_data.clear()
        await update.message.reply_text("تم إلغاء تعديل قالب الرسالة الترحيبية.")
        return ConversationHandler.END
    
    # التحقق من وجود المتغير المطلوب {customer_name}
    if "{customer_name}" not in template_text:
        await update.message.reply_text(
            "⚠️ القالب يجب أن يحتوي على المتغير {customer_name}. الرجاء إعادة المحاولة."
        )
        return AWAITING_WELCOME_TEMPLATE_TEXT
    
    # تحديث القالب
    if db.update_welcome_message_template(template_text):
        await update.message.reply_text(
            f"{st.WELCOME_TEMPLATE_UPDATED}\n\n"
            f"القالب الجديد:\n```\n{template_text}\n```",
            parse_mode="Markdown"
        )
    else:
        await update.message.reply_text(st.WELCOME_TEMPLATE_ERROR)
    
    # تنظيف بيانات المحادثة
    context.user_data.clear()
    return ConversationHandler.END

async def process_search_by_name(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """معالجة البحث بواسطة اسم العميل."""
    # التحقق مما إذا كان المستخدم مسؤولاً
    if not db.is_admin(update.effective_user.id):
        await update.message.reply_text(st.NOT_AUTHORIZED)
        return ConversationHandler.END
    
    search_term = update.message.text.strip()
    
    # فحص ما إذا كان طلب إلغاء
    if "إلغاء العملية" in search_term or len(search_term) < 2:
        await update.message.reply_text("تم إلغاء عملية البحث أو البحث قصير جدًا.")
        return ConversationHandler.END
    
    # البحث عن الإشعارات بواسطة الاسم
    results = db.search_notifications_by_name(search_term)
    
    # حفظ سجل البحث
    user = update.effective_user
    from search_history_functions import add_search_record
    add_search_record(
        user_id=user.id,
        username=user.username or user.first_name,
        search_term=search_term,
        search_type='name',
        results=results
    )
    
    if not results:
        await update.message.reply_text(f"⚠️ لم يتم العثور على نتائج للبحث عن: {search_term}")
        return ConversationHandler.END
    
    # إنشاء لوحة مفاتيح للنتائج مع أزرار البحث
    search_buttons = [
        [
            InlineKeyboardButton("🔍 بحث جديد بالاسم", callback_data="admin_search_by_name"),
            InlineKeyboardButton("🔍 بحث جديد بالرقم", callback_data="admin_search_by_phone")
        ],
        [
            InlineKeyboardButton("📋 سجلات البحث السابقة", callback_data="admin_search_history")
        ]
    ]
    
    page = 1
    keyboard = utils.create_paginated_keyboard(results, page, "admin", extra_buttons=search_buttons)
    
    await update.message.reply_text(
        f"🔍 نتائج البحث عن: {search_term}\n"
        f"عدد النتائج: {len(results)}",
        reply_markup=keyboard
    )
    
    return ConversationHandler.END

async def process_search_by_phone(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """معالجة البحث بواسطة رقم الهاتف."""
    # التحقق مما إذا كان المستخدم مسؤولاً
    if not db.is_admin(update.effective_user.id):
        await update.message.reply_text(st.NOT_AUTHORIZED)
        return ConversationHandler.END
    
    search_term = update.message.text.strip()
    
    # فحص ما إذا كان طلب إلغاء
    if "إلغاء العملية" in search_term:
        await update.message.reply_text("تم إلغاء عملية البحث.")
        return ConversationHandler.END
    
    # تنسيق رقم الهاتف
    formatted_phone = utils.format_phone_number(search_term)
    
    # البحث عن الإشعارات بواسطة الرقم
    results = db.search_notifications_by_phone(formatted_phone)
    
    # حفظ سجل البحث
    user = update.effective_user
    from search_history_functions import add_search_record
    add_search_record(
        user_id=user.id,
        username=user.username or user.first_name,
        search_term=formatted_phone,
        search_type='phone',
        results=results
    )
    
    if not results:
        await update.message.reply_text(f"⚠️ لم يتم العثور على نتائج للبحث عن الرقم: {formatted_phone}")
        return ConversationHandler.END
    
    # إنشاء لوحة مفاتيح للنتائج مع أزرار البحث
    search_buttons = [
        [
            InlineKeyboardButton("🔍 بحث جديد بالاسم", callback_data="admin_search_by_name"),
            InlineKeyboardButton("🔍 بحث جديد بالرقم", callback_data="admin_search_by_phone")
        ],
        [
            InlineKeyboardButton("📋 سجلات البحث السابقة", callback_data="admin_search_history")
        ]
    ]
    
    page = 1
    keyboard = utils.create_paginated_keyboard(results, page, "admin", extra_buttons=search_buttons)
    
    await update.message.reply_text(
        f"🔍 نتائج البحث عن الرقم: {formatted_phone}\n"
        f"عدد النتائج: {len(results)}",
        reply_markup=keyboard
    )
    
    return ConversationHandler.END

def get_template_management_handler():
    """إرجاع معالج المحادثة لإدارة قالب الرسالة."""
    return ConversationHandler(
        entry_points=[
            CommandHandler(st.MESSAGE_TEMPLATE_COMMAND, message_template_command),
            CallbackQueryHandler(handle_template_callback, pattern=r'^template_edit$')
        ],
        states={
            AWAITING_TEMPLATE_TEXT: [MessageHandler(filters.TEXT & ~filters.COMMAND, process_template_text)]
        },
        fallbacks=[
            CommandHandler('cancel', lambda u, c: ConversationHandler.END),
            MessageHandler(filters.Regex(r'.*إلغاء العملية.*'), lambda u, c: ConversationHandler.END)
        ],
        name="template_management"
    )
    
def get_welcome_template_management_handler():
    """إرجاع معالج المحادثة لإدارة قالب الرسالة الترحيبية."""
    return ConversationHandler(
        entry_points=[
            CommandHandler(st.WELCOME_TEMPLATE_COMMAND, welcome_template_command),
            CallbackQueryHandler(handle_welcome_template_callback, pattern=r'^welcome_template_edit$')
        ],
        states={
            AWAITING_WELCOME_TEMPLATE_TEXT: [MessageHandler(filters.TEXT & ~filters.COMMAND, process_welcome_template_text)]
        },
        fallbacks=[
            CommandHandler('cancel', lambda u, c: ConversationHandler.END),
            MessageHandler(filters.Regex(r'.*إلغاء العملية.*'), lambda u, c: ConversationHandler.END)
        ],
        name="welcome_template_management"
    )
    
async def verification_template_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """إدارة قالب رسالة التحقق من الاستلام"""
    # Check if user is admin
    if not db.is_admin(update.effective_user.id):
        await update.message.reply_text(st.NOT_AUTHORIZED)
        return ConversationHandler.END
    
    # Get the current template
    template = db.get_verification_message_template()
    
    # Create keyboard
    keyboard = [
        [InlineKeyboardButton(st.VIEW_VERIFICATION_TEMPLATE, callback_data="verification_template_view")],
        [InlineKeyboardButton(st.EDIT_VERIFICATION_TEMPLATE, callback_data="verification_template_edit")],
        [InlineKeyboardButton(st.RESET_VERIFICATION_TEMPLATE, callback_data="verification_template_reset")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.message.reply_text(
        st.VERIFICATION_TEMPLATE_MENU,
        reply_markup=reply_markup
    )
    
    return ConversationHandler.END

async def handle_verification_template_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """معالجة ردود الاستعلام لإدارة قالب رسالة التحقق"""
    query = update.callback_query
    await query.answer()
    
    if not db.is_admin(update.effective_user.id):
        await query.edit_message_text(st.NOT_AUTHORIZED)
        return ConversationHandler.END
    
    if query.data == "verification_template_view":
        # Show current template
        template = db.get_verification_message_template()
        await query.edit_message_text(
            st.CURRENT_VERIFICATION_TEMPLATE.format(template),
            parse_mode='Markdown',
            reply_markup=InlineKeyboardMarkup([[
                InlineKeyboardButton(st.EDIT_VERIFICATION_TEMPLATE, callback_data="verification_template_edit")
            ]])
        )
        return ConversationHandler.END
        
    elif query.data == "verification_template_edit":
        # Start editing the template
        await query.edit_message_text(st.EDIT_VERIFICATION_TEMPLATE_PROMPT)
        return AWAITING_VERIFICATION_TEMPLATE_TEXT
        
    elif query.data == "verification_template_reset":
        # Reset to default template
        import config
        db.update_verification_message_template(config.DEFAULT_VERIFICATION_TEMPLATE)
        
        await query.edit_message_text(st.VERIFICATION_TEMPLATE_RESET)
        return ConversationHandler.END
    
    return ConversationHandler.END

async def process_verification_template_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """معالجة نص قالب رسالة التحقق المستلم."""
    new_template = update.message.text
    
    # Update the template
    success = db.update_verification_message_template(new_template)
    
    if success:
        await update.message.reply_text(st.VERIFICATION_TEMPLATE_UPDATED)
    else:
        await update.message.reply_text(st.VERIFICATION_TEMPLATE_ERROR)
    
    return ConversationHandler.END
    
def get_verification_template_management_handler():
    """إرجاع معالج المحادثة لإدارة قالب رسالة التحقق."""
    return ConversationHandler(
        entry_points=[
            CommandHandler(st.VERIFICATION_TEMPLATE_COMMAND, verification_template_command),
            CallbackQueryHandler(handle_verification_template_callback, pattern=r'^verification_template_edit$')
        ],
        states={
            AWAITING_VERIFICATION_TEMPLATE_TEXT: [MessageHandler(filters.TEXT & ~filters.COMMAND, process_verification_template_text)]
        },
        fallbacks=[
            CommandHandler('cancel', lambda u, c: ConversationHandler.END),
            MessageHandler(filters.Regex(r'.*إلغاء العملية.*'), lambda u, c: ConversationHandler.END)
        ],
        name="verification_template_management"
    )

def get_edit_notification_handler():
    """إرجاع معالج المحادثة لتعديل الإشعارات."""
    return ConversationHandler(
        entry_points=[
            CallbackQueryHandler(handle_admin_callback, pattern=r'^admin_edit_name_'),
            CallbackQueryHandler(handle_admin_callback, pattern=r'^admin_edit_phone_'),
            CallbackQueryHandler(handle_admin_callback, pattern=r'^admin_edit_image_')
        ],
        states={
            AWAITING_EDIT_NAME: [MessageHandler(filters.TEXT & ~filters.COMMAND, process_edit_name)],
            AWAITING_EDIT_PHONE: [MessageHandler(filters.TEXT & ~filters.COMMAND, process_edit_phone)],
            AWAITING_EDIT_IMAGE: [MessageHandler(filters.PHOTO, process_edit_image)]
        },
        fallbacks=[
            CommandHandler('cancel', lambda u, c: ConversationHandler.END),
            MessageHandler(filters.Regex(r'.*إلغاء العملية.*'), lambda u, c: ConversationHandler.END)
        ],
        name="edit_notification"
    )

def get_search_handler():
    """إرجاع معالج البحث في الإشعارات."""
    return ConversationHandler(
        entry_points=[
            CallbackQueryHandler(handle_admin_callback, pattern=r'^admin_search_')
        ],
        states={
            AWAITING_SEARCH_NAME: [MessageHandler(filters.TEXT & ~filters.COMMAND, process_search_by_name)],
            AWAITING_SEARCH_PHONE: [MessageHandler(filters.TEXT & ~filters.COMMAND, process_search_by_phone)]
        },
        fallbacks=[
            CommandHandler('cancel', lambda u, c: ConversationHandler.END),
            MessageHandler(filters.Regex(r'.*إلغاء العملية.*'), lambda u, c: ConversationHandler.END)
        ],
        name="admin_search_conversation",
        persistent=False
    )

async def handle_watchdog_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """معالجة استجابات أزرار لوحة التحكم في المراقبة."""
    import logging
    
    # سجل تشخيصي للتحقق من استدعاء المعالج
    logging.info(f"🔍 تم استدعاء handle_watchdog_callback مع البيانات: {update.callback_query.data}")
    
    query = update.callback_query
    await query.answer("جاري معالجة طلبك...")
    
    # التحقق من صلاحيات المستخدم
    if not db.is_admin(update.effective_user.id):
        await query.edit_message_text(st.NOT_AUTHORIZED)
        return
    
    try:
        # استيراد المكتبات اللازمة في بداية الدالة لتكون متاحة لكل الأكواد
        import os
        import time
        import sys
        import signal
        import subprocess
        import json
        from threading import Thread
        from datetime import datetime
        
        # معالجة الاستجابات المختلفة
        if query.data == "admin_restart_bot":
            await query.edit_message_text("🔄 جاري إعادة تشغيل البوت... سيتم إخطارك عند الانتهاء.")
            
            try:
                # إنشاء علامة طلب إعادة التشغيل
                with open("restart_requested.log", "w") as f:
                    f.write(f"{time.time()}")
                
                # إرسال إشارة إعادة التشغيل للبوت
                logging.info("🔄 تم طلب إعادة التشغيل من واجهة المراقبة")
                
                # إنشاء عملية منفصلة لإعادة التشغيل
                def stop_and_restart():
                    time.sleep(1)  # انتظار لحظة قبل إعادة التشغيل
                    try:
                        if os.path.exists("start_all_systems.py"):
                            # استخدام نظام التشغيل الموحد إذا كان موجوداً
                            subprocess.Popen([sys.executable, 'start_all_systems.py'])
                        else:
                            # استخدام طريقة إعادة التشغيل التقليدية
                            os.execl(sys.executable, sys.executable, *sys.argv)
                    except Exception as e:
                        logging.error(f"❌ خطأ في إعادة تشغيل البوت: {e}")
                
                restart_thread = Thread(target=stop_and_restart)
                restart_thread.daemon = True
                restart_thread.start()
                
                # انتظار لحظة ثم إيقاف البوت
                time.sleep(2)
                os._exit(0)
            except Exception as e:
                logging.error(f"❌ خطأ في إعادة تشغيل البوت: {e}")
                await context.bot.send_message(
                    chat_id=query.message.chat_id,
                    text=f"⚠️ حدث خطأ أثناء محاولة إعادة التشغيل: {str(e)}"
                )
                
        elif query.data == "admin_clean_markers":
            try:
                # تنظيف ملفات العلامات
                cleaned_files = []
                markers = [
                    "bot_shutdown_marker",
                    "watchdog_ping",
                    "bot_restart_marker",
                    "restart_requested.log"
                ]
                
                for marker in markers:
                    if os.path.exists(marker):
                        os.remove(marker)
                        cleaned_files.append(marker)
                
                if cleaned_files:
                    await query.edit_message_text(f"✅ تم تنظيف ملفات العلامات التالية:\n{', '.join(cleaned_files)}")
                else:
                    await query.edit_message_text("ℹ️ لا توجد ملفات علامات للتنظيف.")
            except Exception as e:
                logging.error(f"❌ خطأ في تنظيف ملفات العلامات: {e}")
                await query.edit_message_text(f"⚠️ حدث خطأ أثناء تنظيف ملفات العلامات: {str(e)}")
                
        elif query.data == "admin_view_logs":
            try:
                # عرض آخر سجلات النظام
                logs = []
                
                # قراءة سجل المراقب
                if os.path.exists("supervisor.log"):
                    logs.append("*📋 سجل المراقب (آخر 5 سطور):*")
                    result = subprocess.run(['tail', '-n', '5', "supervisor.log"], capture_output=True, text=True)
                    if result.stdout.strip():
                        logs.append(f"```\n{result.stdout.strip()}\n```")
                    else:
                        logs.append("_لا توجد سجلات_")
                
                # قراءة سجل البوت
                if os.path.exists("bot.log"):
                    logs.append("\n*📋 سجل البوت (آخر 5 سطور):*")
                    result = subprocess.run(['tail', '-n', '5', "bot.log"], capture_output=True, text=True)
                    if result.stdout.strip():
                        logs.append(f"```\n{result.stdout.strip()}\n```")
                    else:
                        logs.append("_لا توجد سجلات_")
                
                # قراءة سجل نبضات تيليجرام
                telegram_alive_status = None
                if os.path.exists("telegram_alive_status.json"):
                    with open("telegram_alive_status.json", 'r') as f:
                        data = json.load(f)
                        telegram_alive_status = f"\n*📡 حالة نبضات تيليجرام:*\n```\n{json.dumps(data, indent=2, ensure_ascii=False)}\n```"
                
                # تجميع الرسالة
                log_message = "\n".join(logs)
                if telegram_alive_status:
                    log_message += telegram_alive_status
                
                if not log_message:
                    log_message = "⚠️ لا توجد سجلات متاحة للعرض."
                    
                # إضافة زر للعودة
                keyboard = [[InlineKeyboardButton("🔙 العودة للمراقبة", callback_data="admin_return_watchdog")]]
                reply_markup = InlineKeyboardMarkup(keyboard)
                    
                await query.edit_message_text(
                    f"🔍 *سجلات النظام*\n\n{log_message}",
                    parse_mode='Markdown',
                    reply_markup=reply_markup
                )
            except Exception as e:
                logging.error(f"❌ خطأ في عرض السجلات: {e}")
                await query.edit_message_text(f"⚠️ حدث خطأ أثناء عرض السجلات: {str(e)}")
                
        elif query.data == "admin_return_watchdog":
            # العودة إلى أمر المراقبة
            await watchdog_command(update, context)
    except Exception as e:
        logging.error(f"❌ خطأ عام في معالجة استجابة المراقبة: {e}")
        try:
            await query.edit_message_text(f"⚠️ حدث خطأ غير متوقع: {str(e)}")
        except:
            await context.bot.send_message(
                chat_id=query.message.chat_id,
                text=f"⚠️ حدث خطأ غير متوقع: {str(e)}"
            )

async def watchdog_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """عرض معلومات حول نظام مراقبة البوت."""
    # استيراد المكتبات اللازمة في بداية الدالة
    import os
    import time
    import subprocess
    import json
    import traceback
    from datetime import datetime, timedelta
    
    # التحقق من صلاحيات المستخدم
    if not db.is_admin(update.effective_user.id):
        await update.message.reply_text(st.NOT_AUTHORIZED)
        return

    # جمع معلومات حول حالة نبضات القلب
    heartbeat_file = "bot_heartbeat.txt"
    heartbeat_status = "❓ غير معروف"
    heartbeat_time = "غير متوفر"
    
    try:
        if os.path.exists(heartbeat_file):
            with open(heartbeat_file, 'r') as f:
                try:
                    last_heartbeat = float(f.read().strip())
                    now = datetime.now().timestamp()
                    time_diff = now - last_heartbeat
                    
                    # تحويل الطابع الزمني إلى تاريخ قابل للقراءة
                    heartbeat_time = datetime.fromtimestamp(last_heartbeat).strftime('%Y-%m-%d %H:%M:%S')
                    
                    # تحديد حالة نبضات القلب بناءً على الوقت المنقضي
                    if time_diff < 60:  # أقل من دقيقة
                        heartbeat_status = "✅ نشط (آخر تحديث منذ %d ثانية)" % time_diff
                    elif time_diff < 300:  # أقل من 5 دقائق
                        heartbeat_status = "⚠️ متأخر (آخر تحديث منذ %d دقيقة)" % (time_diff // 60)
                    else:
                        heartbeat_status = "❌ قديم (آخر تحديث منذ %d دقيقة)" % (time_diff // 60)
                except:
                    heartbeat_status = "❌ خطأ في قراءة ملف نبضات القلب"
        else:
            heartbeat_status = "❌ ملف نبضات القلب غير موجود"
    except Exception as e:
        logging.error(f"Error checking heartbeat: {e}")
        logging.error(traceback.format_exc())
        heartbeat_status = f"❌ خطأ في التحقق من نبضات القلب: {str(e)}"

    # التحقق من حالة نظام نبضات تيليجرام
    telegram_alive_status = "غير متوفر"
    telegram_alive_time = None
    try:
        telegram_alive_file = "telegram_alive_status.json"
        if os.path.exists(telegram_alive_file):
            with open(telegram_alive_file, 'r') as f:
                try:
                    data = json.load(f)
                    telegram_alive_status = data.get("status", "غير معروف")
                    if "last_check" in data:
                        last_check_time = datetime.fromisoformat(data["last_check"])
                        now = datetime.now()
                        check_diff = (now - last_check_time).total_seconds()
                        
                        telegram_alive_time = last_check_time.strftime("%Y-%m-%d %H:%M:%S")
                        
                        if check_diff < 60:
                            telegram_alive_status = f"✅ {telegram_alive_status} (منذ {int(check_diff)} ثانية)"
                        elif check_diff < 300:
                            telegram_alive_status = f"⚠️ {telegram_alive_status} (منذ {int(check_diff // 60)} دقيقة)"
                        else:
                            telegram_alive_status = f"❌ {telegram_alive_status} (منذ {int(check_diff // 60)} دقيقة)"
                except Exception as e:
                    telegram_alive_status = f"❌ خطأ في قراءة ملف حالة نبضات تيليجرام: {str(e)}"
        else:
            telegram_alive_status = "❌ ملف حالة نبضات تيليجرام غير موجود"
    except Exception as e:
        telegram_alive_status = f"❌ خطأ في التحقق من حالة نبضات تيليجرام: {str(e)}"

    # فحص حالة ملف المراقبة
    watchdog_log = "bot_watchdog.log"
    watchdog_status = "غير مفعّل"
    try:
        if os.path.exists(watchdog_log):
            # قراءة آخر 5 سطور من ملف سجل المراقبة
            result = subprocess.run(['tail', '-n', '5', watchdog_log], capture_output=True, text=True)
            last_logs = result.stdout.strip()
            
            if last_logs:
                watchdog_status = "✅ نشط (آخر تحديث: يرجى التحقق من السجل)"
            else:
                watchdog_status = "⚠️ موجود ولكن فارغ"
        else:
            watchdog_status = "❌ غير مفعّل (ملف السجل غير موجود)"
    except Exception as e:
        watchdog_status = f"❌ خطأ في التحقق من سجل المراقبة: {str(e)}"

    # فحص سجل إعادة التشغيل الأساسي
    restart_log_file = "restart_log.json"
    restart_log_info = "📋 سجل إعادة التشغيل غير متوفر"
    
    try:
        if os.path.exists(restart_log_file):
            with open(restart_log_file, 'r', encoding="utf-8") as f:
                try:
                    import json
                    restart_logs = json.load(f)
                    
                    if restart_logs and len(restart_logs) > 0:
                        # أخذ آخر 3 محاولات إعادة تشغيل
                        last_logs = restart_logs[-3:]
                        
                        restart_log_info = "📋 آخر عمليات إعادة تشغيل (نظام قديم):\n"
                        for log in last_logs:
                            timestamp = log.get("timestamp", "غير متوفر")
                            attempt = log.get("attempt", "غير متوفر")
                            reason = log.get("reason", "غير متوفر")
                            success = "✅" if log.get("success", False) else "❌"
                            
                            # تنسيق الوقت بشكل أفضل
                            try:
                                dt = datetime.fromisoformat(timestamp)
                                formatted_time = dt.strftime("%Y-%m-%d %H:%M:%S")
                            except:
                                formatted_time = timestamp
                                
                            restart_log_info += f"{success} {formatted_time} (#{attempt}): {reason}\n"
                except Exception as e:
                    restart_log_info = f"❌ خطأ في قراءة سجل إعادة التشغيل: {str(e)}"
    except Exception as e:
        restart_log_info = f"❌ خطأ في الوصول لسجل إعادة التشغيل: {str(e)}"
    
    # فحص سجل إعادة التشغيل الجديد
    supervisor_log_file = "restart_supervisor.log"
    supervisor_log_info = ""
    
    try:
        if os.path.exists(supervisor_log_file):
            # قراءة آخر 5 سطور من ملف سجل المراقب الجديد
            result = subprocess.run(['tail', '-n', '5', supervisor_log_file], capture_output=True, text=True)
            last_logs = result.stdout.strip()
            
            if last_logs:
                supervisor_log_info = "📋 آخر عمليات إعادة تشغيل (نظام جديد):\n"
                for line in last_logs.split('\n'):
                    if line.strip():
                        supervisor_log_info += f"{line.strip()}\n"
            else:
                supervisor_log_info = "📋 سجل المراقب الجديد موجود ولكن فارغ\n"
        else:
            supervisor_log_info = "📋 سجل المراقب الجديد غير موجود\n"
    except Exception as e:
        supervisor_log_info = f"❌ خطأ في قراءة سجل المراقب الجديد: {str(e)}\n"
    
    # التحقق من معرفات العمليات
    running_processes = {}
    try:
        if os.path.exists("system_pids.log"):
            with open("system_pids.log", 'r') as f:
                for line in f.readlines():
                    if ":" in line:
                        name, pid = line.strip().split(":", 1)
                        pid = pid.strip()
                        running_processes[name] = pid
    except Exception as e:
        logging.error(f"خطأ في قراءة ملف معرفات العمليات: {e}")
    
    processes_info = ""
    if running_processes:
        processes_info = "⚙️ العمليات النشطة:\n"
        for name, pid in running_processes.items():
            # التحقق مما إذا كانت العملية لا تزال قيد التشغيل
            try:
                if subprocess.run(['ps', '-p', pid], stdout=subprocess.PIPE, stderr=subprocess.PIPE).returncode == 0:
                    status = "✅ نشط"
                else:
                    status = "❌ متوقف"
            except:
                status = "❓ غير معروف"
            
            processes_info += f"• {name}: {pid} ({status})\n"
    
    # استجابة لأمر المراقبة مع معلومات محدثة
    watchdog_info = (
        "🛡️ *نظام المراقبة متعدد الطبقات*\n\n"
        "*📊 حالة أنظمة المراقبة*\n"
        f"• نبضات القلب: {heartbeat_status}\n"
        f"• نبضات تيليجرام: {telegram_alive_status}\n"
        f"• نظام المراقبة القديم: {watchdog_status}\n\n"
    )
    
    if processes_info:
        watchdog_info += f"{processes_info}\n"
    
    watchdog_info += (
        "*📋 سجل إعادة التشغيل*\n"
        f"{supervisor_log_info}\n"
        f"{restart_log_info}\n\n"
        "*⚙️ معلومات النظام*\n"
        "• نبضات تيليجرام ذاتية: كل 20 ثانية\n"
        "• نبضات تيليجرام خارجية: كل 15 ثانية\n"
        "• تحديث ملف نبضات القلب: كل 30 ثانية\n"
        "• فحص المراقب: كل 60 ثانية\n"
        "• حد استخدام الذاكرة: 300 ميجابايت\n\n"
        "*🔄 تشغيل النظام الموحد*\n"
        "لتشغيل النظام المتكامل بالكامل، استخدم:\n"
        "`python start_all_systems.py`\n\n"
        "⚠️ لمزيد من المعلومات حول نظام المراقبة متعدد الطبقات، راجع:\n"
        "`README_KEEPALIVE.md`"
    )
    
    # إنشاء لوحة المفاتيح للتحكم
    keyboard = [
        [InlineKeyboardButton("🔄 إعادة تشغيل البوت", callback_data="admin_restart_bot")],
        [InlineKeyboardButton("🧹 تنظيف ملفات العلامات", callback_data="admin_clean_markers")],
        [InlineKeyboardButton("📋 عرض السجلات", callback_data="admin_view_logs")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    await update.message.reply_text(watchdog_info, parse_mode='Markdown', reply_markup=reply_markup)

async def send_verification_message_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """إرسال رسالة تحقق من الاستلام لإشعار محدد."""
    import logging
    
    # تسجيل مفصل للتشخيص
    logging.info("🚀 تم استدعاء send_verification_message_command")
    
    query = update.callback_query
    # أضف محاولة/إلا للتأكد من أن query.answer() لا تسبب مشاكل
    try:
        await query.answer("جاري معالجة طلبك...")
    except Exception as e:
        logging.error(f"❌ خطأ في query.answer(): {e}")
    
    # تسجيل البيانات المهمة للتشخيص
    logging.info(f"🔍 معرف المستخدم: {update.effective_user.id}, بيانات الاستدعاء: {query.data}")
    
    # Check if user is admin
    if not db.is_admin(update.effective_user.id):
        logging.warning(f"⚠️ محاولة غير مصرح بها من المستخدم: {update.effective_user.id}")
        await query.edit_message_text(st.NOT_AUTHORIZED)
        return
    
    # Get notification ID from callback data
    notification_id = query.data.split('_')[-1]
    logging.info(f"✅ معرف الإشعار المستخرج: {notification_id}")
    
    # Get notification details
    notifications = db.get_all_notifications()
    notification = None
    for notif in notifications:
        if notif.get('id') == notification_id:
            notification = notif
            break
    
    if not notification:
        await query.edit_message_text("⚠️ لم يتم العثور على الإشعار المطلوب.")
        return
    
    # Get customer info
    customer_name = notification.get('customer_name', 'العميل')
    phone_number = notification.get('phone_number', '')
    
    # Send verification message
    import ultramsg_service
    success, result = ultramsg_service.send_verification_message(
        customer_name,
        phone_number,
        notification_id
    )
    
    if success:
        # تعديل الرسالة الحالية أولاً
        try:
            await query.edit_message_text(st.VERIFICATION_MESSAGE_SENT)
        except Exception as e:
            logging.error(f"Error updating message: {e}")
            # إرسال رسالة جديدة كبديل
            await query.message.reply_text(st.VERIFICATION_MESSAGE_SENT)
    else:
        error_message = st.VERIFICATION_MESSAGE_FAILED.format(str(result))
        try:
            await query.edit_message_text(error_message)
        except Exception as e:
            logging.error(f"Error updating message: {e}")
            # إرسال رسالة خطأ جديدة
            await query.message.reply_text(error_message)


def get_admin_handlers():
    """Return handlers related to admin functionality."""
    add_notification_handler = get_add_notification_handler()
    admin_management_handler = get_admin_management_handler()
    template_management_handler = get_template_management_handler()
    welcome_template_management_handler = get_welcome_template_management_handler()
    verification_template_management_handler = get_verification_template_management_handler()
    edit_notification_handler = get_edit_notification_handler()
    search_handler = get_search_handler()
    
    # معالجات عادية للمكونات العامة
    regular_handlers = [
        add_notification_handler,
        CommandHandler('list', list_notifications),
        CommandHandler('admin_help', admin_help),
        CommandHandler('list_admins', list_admins),
        CommandHandler('manage_admins', manage_admins),
        CommandHandler('reset_admins', reset_admins),
        CommandHandler('watchdog', watchdog_command),
        CommandHandler(st.MESSAGE_TEMPLATE_COMMAND, message_template_command),
        CommandHandler(st.WELCOME_TEMPLATE_COMMAND, welcome_template_command),
        CommandHandler(st.VERIFICATION_TEMPLATE_COMMAND, verification_template_command),
        admin_management_handler,
        template_management_handler,
        welcome_template_management_handler,
        verification_template_management_handler,
        edit_notification_handler,
        search_handler,
        # معالجات أزرار محددة - ترتيب المعالجات هنا مهم جداً
        # معالج أزرار واجهة المراقبة يجب أن يكون قبل المعالج العام لأنماط المسؤول
        CallbackQueryHandler(handle_watchdog_callback, pattern=r'^admin_(restart_bot|clean_markers|view_logs|return_watchdog)$'),
        CallbackQueryHandler(handle_template_callback, pattern=r'^template_'),
        CallbackQueryHandler(handle_welcome_template_callback, pattern=r'^welcome_template_'),
        CallbackQueryHandler(handle_verification_template_callback, pattern=r'^verification_template_'),
        CallbackQueryHandler(handle_admin_callback, pattern=r'^confirm_reset_admins$'),
        CallbackQueryHandler(handle_admin_callback, pattern=r'^cancel_reset_admins$'),
        CallbackQueryHandler(send_verification_message_command, pattern=r'^send_verification_')
    ]
    
    # معالجات ذات أولوية عالية لأزرار التعديل والحذف
    # تسجيل أنواع الاستدعاءات التي نريد معالجتها بأولوية عالية
    critical_patterns = [
        # أنماط تعديل الإشعارات
        r'^admin_edit_name_',
        r'^admin_edit_phone_',
        r'^admin_edit_image_',
        r'^admin_delete_',
        r'^admin_confirm_delete_',
        r'^admin_cancel_delete',
        r'^admin_page_'  # للتنقل بين الصفحات
    ]
    
    # إضافة معالج عام للاستدعاءات الأخرى - يجب أن يكون بعد كل المعالجات المحددة
    # للتأكد من أن المعالجات المحددة تعمل أولاً
    regular_handlers.append(CallbackQueryHandler(handle_admin_callback, pattern=r'^admin_'))
    
    return regular_handlers