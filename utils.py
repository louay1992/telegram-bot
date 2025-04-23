import logging
import re
import urllib.parse
from datetime import datetime
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
import database as db

async def check_user_is_admin(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    التحقق من أن المستخدم مسؤول.
    
    Args:
        update: تحديث Telegram
        context: سياق المحادثة
        
    Returns:
        bool: True إذا كان المستخدم مسؤولاً، False خلاف ذلك
    """
    user_id = update.effective_user.id
    
    if db.is_admin(user_id):
        return True
    
    await update.message.reply_text("⚠️ هذا الأمر متاح فقط للمسؤولين.")
    return False

def create_back_button(callback_data):
    """
    إنشاء زر الرجوع.
    
    Args:
        callback_data: بيانات الاستجابة لزر الرجوع
        
    Returns:
        InlineKeyboardButton: زر الرجوع
    """
    return InlineKeyboardButton("🔙 رجوع", callback_data=callback_data)

def create_paginated_keyboard(items, page, prefix, items_per_page=5, extra_buttons=None):
    """
    Create a paginated keyboard for navigating through a list of items.
    
    Args:
        items: List of items to paginate
        page: Current page number (1-based)
        prefix: Callback data prefix for the buttons
        items_per_page: Number of items to show per page
        extra_buttons: Optional list of additional buttons to add at the bottom of the keyboard
    
    Returns:
        InlineKeyboardMarkup for the current page
    """
    start_idx = (page - 1) * items_per_page
    end_idx = start_idx + items_per_page
    
    # Get current page items
    current_items = items[start_idx:end_idx]
    
    keyboard = []
    
    # Add item buttons
    for idx, item in enumerate(current_items, start=start_idx + 1):
        item_id = item["id"]
        item_name = item["customer_name"]
        # Truncate long names
        if len(item_name) > 25:
            item_name = item_name[:22] + "..."
        
        keyboard.append([
            InlineKeyboardButton(
                f"{idx}. {item_name}",
                callback_data=f"{prefix}_view_{item_id}"
            )
        ])
    
    # Add navigation buttons
    nav_buttons = []
    
    # Previous page button
    if page > 1:
        nav_buttons.append(
            InlineKeyboardButton("◀️ السابق", callback_data=f"{prefix}_page_{page-1}")
        )
    
    # Page info button
    total_pages = (len(items) + items_per_page - 1) // items_per_page
    nav_buttons.append(
        InlineKeyboardButton(f"{page}/{total_pages}", callback_data="noop")
    )
    
    # Next page button
    if end_idx < len(items):
        nav_buttons.append(
            InlineKeyboardButton("التالي ▶️", callback_data=f"{prefix}_page_{page+1}")
        )
        
    # إضافة تسجيل لتنسيق أزرار التنقل
    logging.debug(f"Navigation buttons created with prefix {prefix}_page_X")
    
    if nav_buttons:
        keyboard.append(nav_buttons)
    
    # Add extra buttons if provided
    if extra_buttons:
        keyboard.extend(extra_buttons)
    
    return InlineKeyboardMarkup(keyboard)

def format_notification_details(notification):
    """Format notification details for display."""
    from datetime import datetime
    
    created_at = notification.get("created_at", "غير معروف")
    
    # Try to format the date nicely if possible
    try:
        dt = datetime.fromisoformat(created_at)
        created_at = dt.strftime("%Y-%m-%d %H:%M")
    except:
        pass  # Keep the original string if parsing fails
    
    # Format reminder information
    reminder_info = ""
    reminder_hours = notification.get("reminder_hours", 0)
    
    if reminder_hours > 0:
        # تحويل الساعات إلى أيام
        reminder_days = reminder_hours / 24.0
        
        # تنسيق النص بناءً على عدد الأيام
        if reminder_days == 1:
            reminder_info = f"⏰ التذكير بعد: يوم واحد"
        else:
            reminder_info = f"⏰ التذكير بعد: {reminder_days:.1f} يوم"
        
        # Add reminder status if applicable
        if notification.get("reminder_sent", False):
            reminder_sent_at = notification.get("reminder_sent_at", "")
            try:
                if reminder_sent_at:
                    dt = datetime.fromisoformat(reminder_sent_at)
                    reminder_sent_at = dt.strftime("%Y-%m-%d %H:%M")
                    reminder_info += f"\n✅ تم إرسال التذكير في: {reminder_sent_at}"
                else:
                    reminder_info += "\n✅ تم إرسال التذكير"
            except:
                reminder_info += "\n✅ تم إرسال التذكير"
    else:
        reminder_info = "⏰ التذكير: معطل"
    
    return (
        f"🆔 معرف الإشعار: {notification['id'][:8]}...\n"
        f"👤 اسم العميل: {notification['customer_name']}\n"
        f"📱 رقم الهاتف: {notification['phone_number']}\n"
        f"📅 تاريخ الإنشاء: {created_at}\n"
        f"{reminder_info}"
    )

def format_phone_number(phone: str) -> str:
    """
    تنسيق رقم الهاتف ليتضمن رمز البلد إذا لزم الأمر
    يتعامل مع جميع صيغ إدخال الرقم بما فيها الأرقام التي تحتوي على مسافات أو فواصل أو رموز أخرى
    يدعم الأرقام السورية والتركية
    
    مثال للأرقام السورية: 
    - "0947 312 248" 
    - "+963 947 312 248"
    - "0947,312,248"
    - "0947/312/248"
    
    مثال للأرقام التركية: 
    - "0535 123 45 67" 
    - "+90 535 123 45 67"
    - "0535-123-45-67"
    
    Args:
        phone: رقم الهاتف المراد تنسيقه
        
    Returns:
        رقم الهاتف المنسق بصيغة موحدة +XXXXXXXXXXXX
    """
    if not phone:
        return ""
        
    # تسجيل المعلومات الأصلية للمساعدة في التشخيص
    original_phone = phone
    logging.info(f"تنسيق رقم الهاتف الأصلي: '{original_phone}'")
    
    # التعامل مع علامة + في بداية الرقم (حذفها مؤقتًا للمعالجة ثم إعادتها لاحقًا)
    has_plus = False
    if phone.startswith('+'):
        has_plus = True
        phone = phone[1:]  # حذف علامة + مؤقتًا
    
    # التعامل مع الحالة الخاصة للأرقام التي تحتوي على فواصل (,)
    # مثل "0947,312,248" أو "0947, 312, 248"
    if ',' in phone:
        logging.info(f"معالجة رقم هاتف يحتوي على فواصل: {phone}")
        # استبدال الفواصل بمسافات للمعالجة اللاحقة
        phone = phone.replace(',', ' ')
    
    # التعامل مع الحالة الخاصة للأرقام التي تحتوي على شرطات (-)
    # مثل "0947-312-248" أو "0535-123-45-67"
    if '-' in phone:
        logging.info(f"معالجة رقم هاتف يحتوي على شرطات: {phone}")
        # استبدال الشرطات بمسافات للمعالجة اللاحقة
        phone = phone.replace('-', ' ')
    
    # التعامل مع الحالة الخاصة للأرقام التي تحتوي على شرطات مائلة (/)
    # مثل "0947/312/248"
    if '/' in phone:
        logging.info(f"معالجة رقم هاتف يحتوي على شرطات مائلة: {phone}")
        # استبدال الشرطات المائلة بمسافات للمعالجة اللاحقة
        phone = phone.replace('/', ' ')
    
    # إزالة جميع المسافات والرموز غير المرغوب بها وإبقاء الأرقام فقط
    cleaned_phone = ''.join(c for c in phone if c.isdigit() or '\u0660' <= c <= '\u0669')
    logging.info(f"الرقم بعد التنظيف: '{cleaned_phone}'")
    
    # تحويل الأرقام العربية إلى أرقام لاتينية إذا وجدت
    arabic_to_latin = {
        '٠': '0', '١': '1', '٢': '2', '٣': '3', '٤': '4',
        '٥': '5', '٦': '6', '٧': '7', '٨': '8', '٩': '9'
    }
    
    for ar, lat in arabic_to_latin.items():
        cleaned_phone = cleaned_phone.replace(ar, lat)
    
    # معالجة الحالات الخاصة - التحقق إذا كان الرقم تركي أو سوري
    is_turkish = False
    
    # فحص وجود رمز الدولة التركي
    if cleaned_phone.startswith('90') or cleaned_phone.startswith('0090'):
        is_turkish = True
        logging.info(f"تم اكتشاف رقم تركي بناءً على رمز البلد 90: {cleaned_phone}")
    # فحص رقم تركي يبدأ بـ 05 (للهواتف المحمولة التركية)
    elif cleaned_phone.startswith('05') and 10 <= len(cleaned_phone) <= 11:
        is_turkish = True
        logging.info(f"تم اكتشاف رقم تركي يبدأ بـ 05: {cleaned_phone}")
    # فحص رقم تركي يبدأ بـ 5 مباشرة (بدون صفر في البداية)
    elif cleaned_phone.startswith('5') and 9 <= len(cleaned_phone) <= 10:
        is_turkish = True
        logging.info(f"تم اكتشاف رقم تركي يبدأ بـ 5: {cleaned_phone}")
    
    # معالجة الرقم بناءً على البلد (تركي أو سوري)
    
    # حالة الرقم التركي
    if is_turkish:
        # حالة: إذا كان الرقم يبدأ بـ 0090
        if cleaned_phone.startswith('0090'):
            formatted_number = '90' + cleaned_phone[4:]  # إزالة 0090 وإضافة 90
            logging.info(f"تنسيق رقم تركي يبدأ بـ 0090: {formatted_number}")
        # حالة: إذا كان الرقم يبدأ بـ 90
        elif cleaned_phone.startswith('90'):
            formatted_number = cleaned_phone
            logging.info(f"الاحتفاظ بالرقم التركي كما هو مع رمز البلد 90: {formatted_number}")
        # حالة: إذا كان الرقم يبدأ بـ 05 (رقم محلي تركي)
        elif cleaned_phone.startswith('05'):
            formatted_number = '90' + cleaned_phone[1:]  # إزالة الصفر وإضافة 90
            logging.info(f"تنسيق رقم تركي محلي يبدأ بـ 05: {formatted_number}")
        # حالة: إذا كان الرقم يبدأ بـ 5 (بدون صفر)
        elif cleaned_phone.startswith('5'):
            formatted_number = '90' + cleaned_phone
            logging.info(f"تنسيق رقم تركي يبدأ بـ 5: {formatted_number}")
        # حالة أخرى للرقم التركي
        else:
            formatted_number = '90' + cleaned_phone
            logging.info(f"تنسيق رقم تركي (حالة أخرى): {formatted_number}")
            
        # التحقق من طول الرقم التركي (90 + 10 أرقام عادة)
        expected_turkish_length = 12  # 2 أرقام لرمز البلد + 10 أرقام للرقم المحلي
        if len(formatted_number) < expected_turkish_length:
            logging.warning(f"رقم هاتف تركي قصير: {formatted_number}, الأصلي: {original_phone}")
    
    # حالة الرقم السوري (أو غيره)
    else:
        # حالة: إذا كان الرقم يبدأ بصفر (مثل 0947312248) - رقم سوري محلي
        if cleaned_phone.startswith('0'):
            formatted_number = '963' + cleaned_phone[1:]  # إزالة الصفر وإضافة 963
            logging.info(f"تنسيق رقم سوري محلي يبدأ بـ 0: {formatted_number}")
        
        # حالة: إذا كان الرقم يبدأ ب 963 (رمز البلد موجود بالفعل)
        elif cleaned_phone.startswith('963'):
            # معالجة خاصة للأرقام التي تحتوي على خطأ شائع مثل 9639xxxxxxx
            if len(cleaned_phone) > 4 and cleaned_phone[3] == '9':
                # فحص إضافي للتأكد من أن هذا ليس جزءًا من رقم طبيعي (مثل 963987654321)
                if len(cleaned_phone) >= 12:
                    # هذا رقم صحيح فيه 9 (رقم محافظة مثلاً)، نتركه كما هو
                    formatted_number = cleaned_phone
                    logging.info(f"الاحتفاظ بالرقم السوري كما هو: {formatted_number}")
                else:
                    # هذا خطأ في الإدخال، نصححه
                    formatted_number = '963' + cleaned_phone[4:]
                    logging.info(f"تصحيح رقم سوري مع خطأ مشترك: {formatted_number}")
            else:
                # الرقم به رمز البلد بالفعل، نتركه كما هو
                formatted_number = cleaned_phone
                logging.info(f"الاحتفاظ بالرقم السوري مع رمز البلد 963: {formatted_number}")
        
        # حالة: إذا كان الرقم يبدأ بـ 9 (ربما رقم سوري بدون رمز البلد الكامل)
        elif cleaned_phone.startswith('9'):
            # نضيف رمز البلد 963
            formatted_number = '963' + cleaned_phone
            logging.info(f"تنسيق رقم سوري يبدأ بـ 9: {formatted_number}")
        
        # حالة: الحالات الأخرى - نفترض أنه رقم محلي ونضيف رمز البلد
        else:
            formatted_number = '963' + cleaned_phone
            logging.info(f"تنسيق رقم سوري (حالة أخرى): {formatted_number}")
        
        # التحقق من طول الرقم السوري
        expected_syrian_length = 12  # 3 أرقام لرمز البلد + 9 أرقام للرقم المحلي
        if len(formatted_number) < expected_syrian_length:
            logging.warning(f"رقم هاتف سوري قصير: {formatted_number}, الأصلي: {original_phone}")
    
    # إرجاع الرقم النهائي مع إضافة علامة +
    final_phone = '+' + formatted_number
    logging.info(f"الرقم النهائي بعد التنسيق: {final_phone}")
    return final_phone

async def send_image_with_caption(update: Update, context: ContextTypes.DEFAULT_TYPE, 
                           photo, caption=None, reply_markup=None):
    """Send an image with caption, handling errors gracefully."""
    try:
        # تسجيل معلومات الرسم البياني للتشخيص
        photo_type = type(photo).__name__
        photo_size = len(photo) if isinstance(photo, bytes) else 'unknown'
        logging.info(f"Sending image: type={photo_type}, size={photo_size}")
        
        # التحقق من حجم الصورة
        if isinstance(photo, bytes) and photo_size < 100:
            logging.warning(f"Image data seems too small: {photo_size} bytes")
            
        # بيانات إضافية للتشخيص
        chat_id = update.effective_chat.id
        caption_len = len(caption) if caption else 0
        logging.info(f"Sending to chat_id={chat_id}, caption length={caption_len}")
        
        # محاولة الإرسال
        message = await context.bot.send_photo(
            chat_id=chat_id,
            photo=photo,
            caption=caption,
            reply_markup=reply_markup
        )
        logging.info(f"Image successfully sent to chat_id={chat_id}")
        return message
    except Exception as e:
        import traceback
        error_tb = traceback.format_exc()
        logging.error(f"Error sending image: {e}")
        logging.error(f"Traceback: {error_tb}")
        
        try:
            # ارسال النص فقط في حالة فشل إرسال الصورة
            await update.effective_message.reply_text(
                f"{caption or ''}\n\n⚠️ حدث خطأ أثناء إرسال الصورة. الرجاء المحاولة مرة أخرى.",
                reply_markup=reply_markup
            )
            logging.info(f"Sent text fallback instead of image to chat_id={chat_id}")
        except Exception as text_error:
            logging.error(f"Error even sending text fallback: {text_error}")
        
        return None
        
def url_encode(text: str) -> str:
    """
    تشفير النص للاستخدام في روابط URL
    
    Args:
        text: النص المراد تشفيره
        
    Returns:
        النص المشفر لاستخدامه في روابط URL
    """
    return urllib.parse.quote(text)

def format_datetime(date_str: str) -> str:
    """
    تنسيق التاريخ والوقت بشكل أكثر قابلية للقراءة.
    
    Args:
        date_str: تاريخ بصيغة ISO (مثل "2025-04-20T10:30:15.123456")
        
    Returns:
        التاريخ المنسق بصيغة "YYYY-MM-DD HH:MM"
    """
    try:
        dt = datetime.fromisoformat(date_str)
        # تنسيق مميز باللغة العربية
        months = {
            1: "يناير", 2: "فبراير", 3: "مارس", 4: "أبريل", 5: "مايو", 6: "يونيو",
            7: "يوليو", 8: "أغسطس", 9: "سبتمبر", 10: "أكتوبر", 11: "نوفمبر", 12: "ديسمبر"
        }
        month_name = months[dt.month]
        return f"{dt.day} {month_name} {dt.year} - {dt.hour:02}:{dt.minute:02}"
    except Exception as e:
        logging.error(f"Error formatting datetime: {e}")
        return date_str
        
def is_admin(user_id: int) -> bool:
    """
    التحقق مما إذا كان المستخدم مسؤولاً أم لا.
    
    Args:
        user_id: معرف المستخدم للتحقق
        
    Returns:
        bool: True إذا كان المستخدم مسؤولاً، False خلاف ذلك
    """
    return db.is_admin(user_id)


def check_admin(func):
    """
    مزخرف لفحص ما إذا كان المستخدم مسؤولاً.
    يستخدم هذا المزخرف لمنع المستخدمين غير المسؤولين من الوصول إلى وظائف معينة.
    
    Args:
        func: الوظيفة المراد تزيينها
        
    Returns:
        wrapper: دالة غلاف تتحقق من صلاحيات المستخدم
    """
    import functools
    
    @functools.wraps(func)
    async def wrapper(update, context, *args, **kwargs):
        if not update.effective_user:
            await update.message.reply_text("⚠️ لم يتم التعرف على المستخدم.")
            return
        
        user_id = update.effective_user.id
        if not db.is_admin(user_id):
            import strings as st
            await update.message.reply_text(st.NOT_AUTHORIZED)
            return
        
        return await func(update, context, *args, **kwargs)
    
    return wrapper
