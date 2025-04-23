import logging
import os
from telegram import Update, KeyboardButton, ReplyKeyboardMarkup
from telegram.ext import (
    Application, CommandHandler, MessageHandler, 
    filters, CallbackContext, ContextTypes
)

import database as db
import strings as st
import admin_handlers_simplified as admin_handlers
import search_handlers
import config

# Set up logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

def create_admin_keyboard():
    """Create a keyboard with admin commands."""
    keyboard = [
        [KeyboardButton("➕ إضافة إشعار"), KeyboardButton("📋 قائمة الإشعارات")],
        [KeyboardButton("👥 إدارة المسؤولين"), KeyboardButton("❓ مساعدة المسؤول")],
        [KeyboardButton("🔍 البحث عن إشعار"), KeyboardButton("📱 البحث برقم الهاتف")],
        [KeyboardButton("❌ إلغاء العملية الحالية")]
    ]
    return ReplyKeyboardMarkup(keyboard, resize_keyboard=True)

def create_user_keyboard():
    """Create a keyboard with user commands."""
    keyboard = [
        [KeyboardButton("🔍 البحث عن إشعار"), KeyboardButton("📱 البحث برقم الهاتف")],
        [KeyboardButton("❓ مساعدة")]
    ]
    return ReplyKeyboardMarkup(keyboard, resize_keyboard=True)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Send a welcome message when the command /start is issued."""
    user = update.effective_user
    
    # Check if the user is the first to start the bot
    db.set_main_admin_if_none(user.id)
    
    # Check if the user is an admin
    is_admin = db.is_admin(user.id)
    
    welcome_message = st.WELCOME_MESSAGE.format(name=user.first_name)
    
    # Add the appropriate keyboard based on user role
    if is_admin:
        await update.message.reply_text(
            welcome_message + "\n\n" + st.ADMIN_WELCOME,
            reply_markup=create_admin_keyboard()
        )
    else:
        await update.message.reply_text(
            welcome_message + "\n\n" + st.USER_WELCOME,
            reply_markup=create_user_keyboard()
        )

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Send a help message when the command /help is issued."""
    user = update.effective_user
    is_admin = db.is_admin(user.id)
    
    if is_admin:
        await update.message.reply_text(
            st.ADMIN_HELP,
            reply_markup=create_admin_keyboard()
        )
    else:
        await update.message.reply_text(
            st.USER_HELP,
            reply_markup=create_user_keyboard()
        )

async def cancel_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Cancel any ongoing conversation."""
    # Clear any user data
    context.user_data.clear()
    
    # Send confirmation message
    await update.message.reply_text(st.CANCEL_COMMAND)
    
    # Provide appropriate keyboard
    user = update.effective_user
    is_admin = db.is_admin(user.id)
    
    if is_admin:
        await update.message.reply_text(
            "تم إلغاء العملية الحالية.",
            reply_markup=create_admin_keyboard()
        )
    else:
        await update.message.reply_text(
            "تم إلغاء العملية الحالية.",
            reply_markup=create_user_keyboard()
        )

async def handle_keyboard_buttons(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle text messages from keyboard buttons."""
    text = update.message.text
    user_id = update.effective_user.id
    
    # Log the button press
    logger.info(f"Button pressed: '{text}'")
    
    if "إضافة إشعار" in text:
        # Only admins can add notifications
        if db.is_admin(user_id):
            logger.info("Add notification button pressed")
            return await admin_handlers.add_notification(update, context)
        else:
            await update.message.reply_text(st.NOT_AUTHORIZED)
    
    elif "قائمة الإشعارات" in text:
        # Only admins can list all notifications
        if db.is_admin(user_id):
            return await admin_handlers.list_notifications(update, context)
        else:
            await update.message.reply_text(st.NOT_AUTHORIZED)
    
    elif "إدارة المسؤولين" in text:
        # Only admins can manage admins
        if db.is_admin(user_id):
            return await admin_handlers.manage_admins(update, context)
        else:
            await update.message.reply_text(st.NOT_AUTHORIZED)
    
    elif "مساعدة المسؤول" in text:
        # Only admins can see admin help
        if db.is_admin(user_id):
            return await admin_handlers.admin_help(update, context)
        else:
            await update.message.reply_text(st.NOT_AUTHORIZED)
    
    elif "البحث عن إشعار" in text:
        # Both users and admins can search
        return await search_handlers.search_command(update, context)
    
    elif "البحث برقم الهاتف" in text:
        # Both users and admins can search by phone
        return await search_handlers.phone_search_command(update, context)
    
    elif "إلغاء العملية الحالية" in text:
        # Cancel any ongoing conversation
        return await cancel_command(update, context)
    
    elif "مساعدة" in text:
        # Show help message
        return await help_command(update, context)
    
    else:
        # Unknown button
        logger.info(f"Unknown command: '{text}'")
        await update.message.reply_text(st.UNKNOWN_COMMAND)

async def handle_unknown_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle unknown commands."""
    await update.message.reply_text(st.UNKNOWN_COMMAND)

async def error_handler(update: object, context: ContextTypes.DEFAULT_TYPE):
    """Log errors caused by updates."""
    if update:
        logger.error(f"Update {update} caused error: {context.error}")
    else:
        logger.error(f"Error without update: {context.error}")

def main():
    """Start the bot."""
    # Create the Application
    application = Application.builder().token(config.TOKEN).build()

    # Add conversation handlers
    admin_handlers_list = admin_handlers.get_admin_handlers()
    for handler in admin_handlers_list:
        application.add_handler(handler)
    
    # Add search handlers
    search_handlers_list = search_handlers.get_search_handlers()
    for handler in search_handlers_list:
        application.add_handler(handler)
    
    # Basic command handlers
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(CommandHandler("cancel", cancel_command))

    # Handle regular messages
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_keyboard_buttons))
    
    # Handle unknown commands
    application.add_handler(MessageHandler(filters.COMMAND, handle_unknown_command))
    
    # Log all errors
    application.add_error_handler(error_handler)
    
    # Run the bot until the user presses Ctrl-C
    application.run_polling()

if __name__ == "__main__":
    main()