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
NAME, PHONE, IMAGE = range(1, 4)
AWAITING_ADMIN_ID, AWAITING_ADMIN_ACTION = range(5, 7)

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
        
        # Verify we have the required data in context.user_data
        if "customer_name" not in context.user_data or "phone_number" not in context.user_data:
            logging.error("Missing customer_name or phone_number in user_data")
            logging.info(f"Available user_data keys: {list(context.user_data.keys())}")
            await update.message.reply_text("⚠️ حدث خطأ: بيانات العميل غير مكتملة. يرجى إعادة المحاولة.")
            return ConversationHandler.END
        
        # Log customer info for debugging
        logging.info(f"Processing image for customer: {context.user_data.get('customer_name', 'MISSING')} | Phone: {context.user_data.get('phone_number', 'MISSING')}")
        
        # Get the largest available photo
        photo = update.message.photo[-1]
        logging.info(f"Received photo with file_id: {photo.file_id}")
        
        # Download the photo
        file = await context.bot.get_file(photo.file_id)
        image_bytes = await file.download_as_bytearray()
        logging.info(f"Downloaded image, size: {len(image_bytes)} bytes")
        
        # Add the notification to the database
        success, result = db.add_notification(
            context.user_data["customer_name"],
            context.user_data["phone_number"],
            image_bytes
        )
        
        logging.info(f"Database add result: success={success}, result={result}")
        
        if success:
            # Clear conversation state
            context.user_data.clear()
            await update.message.reply_text(st.ADD_NOTIFICATION_SUCCESS)
        else:
            await update.message.reply_text(f"⚠️ حدث خطأ: {result}")
        
        # Return to conversation end
        return ConversationHandler.END
    except Exception as e:
        logging.error(f"Error processing image: {e}")
        import traceback
        logging.error(traceback.format_exc())
        await update.message.reply_text(st.IMAGE_ERROR)
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
    
    # Set up pagination
    page = 1
    keyboard = utils.create_paginated_keyboard(notifications, page, "admin")
    
    await update.message.reply_text(
        f"{st.LIST_NOTIFICATIONS_HEADER}\n"
        f"إجمالي الإشعارات: {len(notifications)}",
        reply_markup=keyboard
    )

async def handle_admin_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle callback queries for admin pagination."""
    query = update.callback_query
    await query.answer()
    
    # Check if user is admin
    if not db.is_admin(update.effective_user.id):
        await query.message.reply_text(st.NOT_AUTHORIZED)
        return
    
    data = query.data.split("_")
    
    if data[0] != "admin":
        return
    
    if data[1] == "page":
        # Handle pagination
        page = int(data[2])
        notifications = db.get_all_notifications()
        keyboard = utils.create_paginated_keyboard(notifications, page, "admin")
        
        await query.edit_message_text(
            f"{st.LIST_NOTIFICATIONS_HEADER}\n"
            f"إجمالي الإشعارات: {len(notifications)}",
            reply_markup=keyboard
        )
    
    elif data[1] == "view":
        # View notification details
        notification_id = data[2]
        notifications = db.get_all_notifications()
        
        # Find the notification
        notification = next((n for n in notifications if n["id"] == notification_id), None)
        
        if not notification:
            await query.message.reply_text("⚠️ لم يتم العثور على الإشعار!")
            return
        
        # Create keyboard for actions
        keyboard = [
            [InlineKeyboardButton("🗑️ حذف الإشعار", callback_data=f"admin_delete_{notification_id}")]
        ]
        
        # Display notification details
        details = utils.format_notification_details(notification)
        
        # Get the image
        image_data = db.get_image(notification_id)
        
        if image_data:
            await utils.send_image_with_caption(
                update, context, 
                photo=image_data, 
                caption=details,
                reply_markup=InlineKeyboardMarkup(keyboard)
            )
        else:
            await query.message.reply_text(
                details + "\n\n⚠️ الصورة غير متوفرة!",
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
        
        await query.edit_message_text(
            "هل أنت متأكد من حذف هذا الإشعار؟",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
    
    elif data[1] == "confirm" and data[2] == "delete":
        # Confirm deletion
        notification_id = data[3]
        
        if db.delete_notification(notification_id):
            await query.edit_message_text(st.DELETE_NOTIFICATION_SUCCESS)
        else:
            await query.edit_message_text(st.DELETE_NOTIFICATION_ERROR)
    
    elif data[1] == "cancel" and data[2] == "delete":
        # Cancel deletion
        await query.edit_message_text("تم إلغاء عملية الحذف.")

async def admin_help(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Display admin help message."""
    # Check if user is admin
    if not db.is_admin(update.effective_user.id):
        await update.message.reply_text(st.NOT_AUTHORIZED)
        return
    
    await update.message.reply_text(st.ADMIN_HELP)

async def manage_admins(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show admin management options."""
    # Check if user is admin
    if not db.is_admin(update.effective_user.id):
        await update.message.reply_text(st.NOT_AUTHORIZED)
        return
    
    keyboard = [
        [InlineKeyboardButton("👥 عرض المسؤولين", callback_data="admin_manage_list")],
        [InlineKeyboardButton("➕ إضافة مسؤول", callback_data="admin_manage_add")],
        [InlineKeyboardButton("➖ إزالة مسؤول", callback_data="admin_manage_remove")]
    ]
    
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

async def process_admin_id(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Process the received admin ID."""
    admin_action = context.user_data.get('admin_action')
    
    if not admin_action:
        await update.message.reply_text("⚠️ حدث خطأ: نوع العملية غير محدد.")
        return ConversationHandler.END
    
    user_id = None
    
    # Check if it's a forwarded message
    if update.message.forward_from:
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
            IMAGE: [MessageHandler(filters.PHOTO, received_image)]
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

def get_admin_handlers():
    """Return handlers related to admin functionality."""
    add_notification_handler = get_add_notification_handler()
    admin_management_handler = get_admin_management_handler()
    
    return [
        add_notification_handler,
        CommandHandler('list', list_notifications),
        CommandHandler('admin_help', admin_help),
        CommandHandler('list_admins', list_admins),
        CommandHandler('manage_admins', manage_admins),
        admin_management_handler,
        CallbackQueryHandler(handle_admin_callback, pattern=r'^admin_')
    ]