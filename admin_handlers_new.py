"""
Simplified admin handlers module
"""
import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    ConversationHandler, CommandHandler, MessageHandler, CallbackQueryHandler,
    ContextTypes, filters
)

import database as db
import strings as st
import utils
import input_validator_new as validator

# Conversation states
NAME, PHONE, IMAGE = range(3)
AWAITING_ADMIN_ID, AWAITING_ADMIN_ACTION = range(3, 5)

async def add_notification(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Start the process of adding a new notification."""
    # Check if user is admin
    if not db.is_admin(update.effective_user.id):
        await update.message.reply_text(st.NOT_AUTHORIZED)
        return ConversationHandler.END

    # Clear any existing conversation data
    context.user_data.clear()
    
    # Log who started the conversation
    user_id = update.effective_user.id
    username = update.effective_user.username or "Unknown"
    logging.info(f"User {username} (ID: {user_id}) started adding a notification")

    # Ask for customer name
    await update.message.reply_text(st.ADD_NOTIFICATION_NAME)
    return NAME

async def received_name(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle received customer name."""
    # Get the name entered by the user
    name = update.message.text
    
    # Log the received name
    user_id = update.effective_user.id
    username = update.effective_user.username or "Unknown"
    logging.info(f"User {username} (ID: {user_id}) entered name: '{name}'")
    
    # Validate the name
    if not validator.is_valid_name(name):
        await update.message.reply_text(st.INVALID_NAME)
        return NAME
    
    # Store the name
    context.user_data["customer_name"] = name
    logging.info(f"Name '{name}' stored successfully")

    # Ask for phone number
    await update.message.reply_text(st.ADD_NOTIFICATION_PHONE)
    return PHONE

async def received_phone(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle received phone number."""
    # Get the phone entered by the user
    phone = update.message.text
    
    # Log the received phone
    user_id = update.effective_user.id
    username = update.effective_user.username or "Unknown"
    logging.info(f"User {username} (ID: {user_id}) entered phone: '{phone}'")
    
    # تسجيل معلومات رقم الهاتف الأصلي للمساعدة في التشخيص
    logging.info(f"Original phone input: '{phone}'")
    
    # Validate the phone
    is_valid, formatted_phone = validator.is_valid_phone(phone)
    logging.info(f"Received phone: '{phone}', formatted: '{formatted_phone}', valid: {is_valid}")
    
    if not is_valid:
        await update.message.reply_text(st.INVALID_PHONE)
        return PHONE
    
    # Store the formatted phone number with country code
    context.user_data["phone_number"] = formatted_phone
    logging.info(f"Phone '{formatted_phone}' stored successfully")
    
    # إعلام المستخدم بالرقم بعد تنسيقه
    await update.message.reply_text(f"✅ تم حفظ رقم الهاتف: {formatted_phone}")

    # Ask for the image
    await update.message.reply_text(st.ADD_NOTIFICATION_IMAGE)
    return IMAGE

async def received_image(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle received notification image."""
    try:
        # Check if a photo was sent
        if not update.message.photo:
            await update.message.reply_text("الرجاء إرسال صورة وليس نصاً أو ملفاً آخر.")
            return IMAGE
        
        # Get the largest available photo
        photo = update.message.photo[-1]
        
        # Download the photo
        file = await context.bot.get_file(photo.file_id)
        image_bytes = await file.download_as_bytearray()
        
        # Get the stored customer information
        customer_name = context.user_data.get("customer_name")
        phone_number = context.user_data.get("phone_number")
        
        if not customer_name or not phone_number:
            logging.error("Missing customer data in conversation context")
            await update.message.reply_text(st.GENERAL_ERROR)
            return ConversationHandler.END
        
        # Add the notification to the database
        logging.info(f"Adding notification: Name: '{customer_name}', Phone: '{phone_number}'")
        success, result = db.add_notification(customer_name, phone_number, image_bytes)
        
        if success:
            await update.message.reply_text(st.ADD_NOTIFICATION_SUCCESS)
        else:
            await update.message.reply_text(f"⚠️ حدث خطأ: {result}")
        
        return ConversationHandler.END
    except Exception as e:
        logging.error(f"Error processing image: {e}")
        await update.message.reply_text(st.IMAGE_ERROR)
        return ConversationHandler.END

async def cancel_add(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Cancel the conversation."""
    await update.message.reply_text(st.ADD_NOTIFICATION_CANCEL)
    return ConversationHandler.END

def get_add_notification_handler():
    """Return the conversation handler for adding notifications."""
    return ConversationHandler(
        entry_points=[CommandHandler('add', add_notification)],
        states={
            NAME: [MessageHandler(filters.TEXT & ~filters.COMMAND, received_name)],
            PHONE: [MessageHandler(filters.TEXT & ~filters.COMMAND, received_phone)],
            IMAGE: [MessageHandler(filters.PHOTO, received_image)]
        },
        fallbacks=[CommandHandler('cancel', cancel_add)],
        name="add_notification",
        persistent=False
    )