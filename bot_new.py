"""
Telegram bot for shipping notifications
"""
import logging
import os
from telegram import Update, KeyboardButton, ReplyKeyboardMarkup
from telegram.ext import (
    Application, CommandHandler, MessageHandler, CallbackQueryHandler,
    ContextTypes, filters
)

import database as db
import strings as st
import search_handlers as search
import admin_handlers_new as admin

# Configure logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)

def create_admin_keyboard():
    """Create a keyboard with admin commands."""
    keyboard = [
        [KeyboardButton("➕ إضافة إشعار"), KeyboardButton("📋 قائمة الإشعارات")],
        [KeyboardButton("👥 إدارة المسؤولين"), KeyboardButton("❓ مساعدة المسؤول")]
    ]
    return ReplyKeyboardMarkup(keyboard, resize_keyboard=True)

def create_user_keyboard():
    """Create a keyboard with user commands."""
    keyboard = [
        [KeyboardButton("🔍 بحث باسم العميل"), KeyboardButton("📞 بحث برقم الهاتف")],
        [KeyboardButton("❓ مساعدة")]
    ]
    return ReplyKeyboardMarkup(keyboard, resize_keyboard=True)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Send a welcome message when the command /start is issued."""
    user_id = update.effective_user.id
    username = update.effective_user.username or "Unknown"
    logging.info(f"User {username} (ID: {user_id}) started the bot")
    
    # Set the user as main admin if there is none
    db.set_main_admin_if_none(user_id)
    
    # Send appropriate keyboard based on user role
    if db.is_admin(user_id):
        await update.message.reply_text(
            f"{st.ADMIN_WELCOME}\n\n{st.WELCOME_MESSAGE}",
            reply_markup=create_admin_keyboard()
        )
    else:
        await update.message.reply_text(
            st.WELCOME_MESSAGE,
            reply_markup=create_user_keyboard()
        )

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Send a help message when the command /help is issued."""
    if db.is_admin(update.effective_user.id):
        await update.message.reply_text(st.ADMIN_HELP_MESSAGE)
    else:
        await update.message.reply_text(st.HELP_MESSAGE)

async def handle_keyboard_buttons(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle text messages from keyboard buttons."""
    text = update.message.text
    
    # Admin commands
    if text == "➕ إضافة إشعار":
        return await admin.add_notification(update, context)
    elif text == "📋 قائمة الإشعارات":
        return await admin.list_notifications(update, context)
    elif text == "👥 إدارة المسؤولين":
        return await admin.manage_admins(update, context)
    elif text == "❓ مساعدة المسؤول":
        return await admin.admin_help(update, context)
    
    # User commands
    elif text == "🔍 بحث باسم العميل":
        context.user_data['search_type'] = 'name'
        return await search.search_command(update, context)
    elif text == "📞 بحث برقم الهاتف":
        context.user_data['search_type'] = 'phone'
        return await search.phone_search_command(update, context)
    elif text == "❓ مساعدة":
        return await help_command(update, context)
    
    # Unknown command
    else:
        await update.message.reply_text(st.INVALID_COMMAND)

async def handle_unknown_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle unknown commands."""
    await update.message.reply_text(st.INVALID_COMMAND)

async def error_handler(update: object, context: ContextTypes.DEFAULT_TYPE):
    """Log errors caused by updates."""
    logging.error(f"Exception while handling an update: {context.error}")

def main():
    """Start the bot."""
    # Get the token from environment variable
    token = os.environ.get("TELEGRAM_TOKEN", "7406580104:AAHdONTM_KBWT5Yuup3rr_gLSovoaD7QxVI")
    
    # Create the application
    application = Application.builder().token(token).build()
    
    # Add handlers
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("help", help_command))
    
    # Add the new admin handler for adding notifications
    application.add_handler(admin.get_add_notification_handler())
    
    # Add other handlers (reusing from original files)
    for handler in search.get_search_handlers():
        application.add_handler(handler)
    
    # Add handlers for keyboard buttons
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_keyboard_buttons))
    
    # Add handler for unknown commands
    application.add_handler(MessageHandler(filters.COMMAND, handle_unknown_command))
    
    # Register error handler
    application.add_error_handler(error_handler)
    
    # Start the bot
    application.run_polling()

if __name__ == "__main__":
    main()