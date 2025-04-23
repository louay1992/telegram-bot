"""
وحدة الحملات التسويقية لبوت إشعارات الشحن
تمكن المسؤولين من إنشاء وإدارة حملات تسويقية لإرسال عروض وإشعارات ترويجية للعملاء
"""
import os
import json
import uuid
import logging
from datetime import datetime
from typing import List, Dict, Optional, Any, Tuple

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    ContextTypes, ConversationHandler, CommandHandler,
    MessageHandler, CallbackQueryHandler, filters
)

import database as db
import strings as st
import config
import utils
from ultramsg_service import send_whatsapp_message, send_whatsapp_image

# حالات المحادثة
CAMPAIGN_NAME = 1
CAMPAIGN_TYPE = 2
CAMPAIGN_TARGET = 3
CAMPAIGN_MESSAGE = 4
CAMPAIGN_DISCOUNT = 5
CAMPAIGN_MIN_ORDER = 6
CAMPAIGN_MAX_CUSTOMERS = 7
CAMPAIGN_CONFIRMATION = 8
CAMPAIGN_IMAGE = 9

# التحقق من وجود مجلد للحملات
os.makedirs("data/campaigns", exist_ok=True)
CAMPAIGNS_FILE = "data/campaigns.json"

# إنشاء ملف الحملات إذا لم يكن موجوداً
if not os.path.exists(CAMPAIGNS_FILE):
    with open(CAMPAIGNS_FILE, "w", encoding="utf-8") as f:
        json.dump({"campaigns": []}, f, ensure_ascii=False, indent=4)
    logging.info(f"تم إنشاء ملف الحملات: {CAMPAIGNS_FILE}")

# واجهة خدمة الواتساب - تستخدم دوال مباشرة

# الأنواع المدعومة للحملات
CAMPAIGN_TYPES = {
    "discount": "خصم بنسبة مئوية",
    "free_product": "منتج مجاني",
    "special_offer": "عرض خاص",
    "announcement": "إعلان عام"
}

def load_campaigns():
    """تحميل الحملات من الملف."""
    try:
        with open(CAMPAIGNS_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return {"campaigns": []}

def save_campaigns(campaigns_data):
    """حفظ الحملات في الملف."""
    try:
        # تأكد من وجود مجلد البيانات
        os.makedirs(os.path.dirname(CAMPAIGNS_FILE), exist_ok=True)
        
        with open(CAMPAIGNS_FILE, "w", encoding="utf-8") as f:
            json.dump(campaigns_data, f, ensure_ascii=False, indent=4)
        logging.info(f"تم حفظ الحملات في: {CAMPAIGNS_FILE}")
        return True
    except Exception as e:
        logging.error(f"خطأ في حفظ ملف الحملات: {e}")
        import traceback
        logging.error(traceback.format_exc())
        return False

async def marketing_campaigns_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """عرض قائمة الحملات التسويقية وخيارات إدارتها."""
    # تحقق من صلاحية المستخدم
    if not db.is_admin(update.effective_user.id):
        await update.message.reply_text(st.NOT_AUTHORIZED)
        return
    
    # رسالة الترحيب بنظام الحملات التسويقية
    welcome_text = """
🚀 *نظام الحملات التسويقية في NatureCare*

يمكنك من خلال هذا النظام إنشاء وإدارة حملات تسويقية لعملائك، مثل:
• حملات خصومات بنسب مختلفة
• عروض منتجات مجانية عند الشراء
• إعلانات وعروض خاصة
• رسائل تسويقية مخصصة

اختر من الخيارات أدناه:
    """
    
    keyboard = [
        [InlineKeyboardButton("➕ إنشاء حملة جديدة", callback_data="campaign_create")],
        [InlineKeyboardButton("📋 عرض الحملات النشطة", callback_data="campaign_list_active")],
        [InlineKeyboardButton("🗄️ عرض سجل الحملات السابقة", callback_data="campaign_list_past")],
        [InlineKeyboardButton("📊 إحصائيات الحملات", callback_data="campaign_stats")]
    ]
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text(welcome_text, reply_markup=reply_markup, parse_mode="Markdown")

async def handle_campaign_callbacks(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """معالجة استدعاءات الأزرار الخاصة بالحملات التسويقية."""
    query = update.callback_query
    await query.answer()
    callback_data = query.data
    
    if callback_data == "campaign_create":
        await start_campaign_creation(update, context)
    elif callback_data == "campaign_list_active":
        await list_active_campaigns(update, context)
    elif callback_data == "campaign_list_past":
        await list_past_campaigns(update, context)
    elif callback_data == "campaign_stats":
        await show_campaign_stats(update, context)
    elif callback_data.startswith("campaign_view_"):
        campaign_id = callback_data.replace("campaign_view_", "")
        await view_campaign_details(update, context, campaign_id)
    elif callback_data.startswith("campaign_send_"):
        campaign_id = callback_data.replace("campaign_send_", "")
        await send_campaign_messages(update, context, campaign_id)
    elif callback_data.startswith("campaign_delete_"):
        campaign_id = callback_data.replace("campaign_delete_", "")
        await delete_campaign(update, context, campaign_id)
    elif callback_data == "campaign_back_main":
        await update_campaign_main_menu(update, context)
    else:
        await query.edit_message_text("أمر غير معروف. يرجى المحاولة مرة أخرى.")

async def update_campaign_main_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """تحديث القائمة الرئيسية للحملات التسويقية."""
    welcome_text = """
🚀 *نظام الحملات التسويقية في NatureCare*

يمكنك من خلال هذا النظام إنشاء وإدارة حملات تسويقية لعملائك، مثل:
• حملات خصومات بنسب مختلفة
• عروض منتجات مجانية عند الشراء
• إعلانات وعروض خاصة
• رسائل تسويقية مخصصة

اختر من الخيارات أدناه:
    """
    
    keyboard = [
        [InlineKeyboardButton("➕ إنشاء حملة جديدة", callback_data="campaign_create")],
        [InlineKeyboardButton("📋 عرض الحملات النشطة", callback_data="campaign_list_active")],
        [InlineKeyboardButton("🗄️ عرض سجل الحملات السابقة", callback_data="campaign_list_past")],
        [InlineKeyboardButton("📊 إحصائيات الحملات", callback_data="campaign_stats")]
    ]
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.callback_query.edit_message_text(welcome_text, reply_markup=reply_markup, parse_mode="Markdown")

async def start_campaign_creation(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """بدء عملية إنشاء حملة تسويقية جديدة."""
    try:
        # التحقق من صلاحية المستخدم
        if not db.is_admin(update.effective_user.id):
            await update.callback_query.answer("⚠️ هذه الميزة متاحة فقط للمسؤولين")
            return ConversationHandler.END
            
        # التحقق من وجود callback_query
        if not update.callback_query:
            logging.error("No callback_query in update object")
            return ConversationHandler.END
            
        # إنشاء معرف فريد للحملة
        campaign_id = str(uuid.uuid4())
        logging.info(f"Creating new campaign with ID: {campaign_id}")
        
        # التأكد من عدم وجود حملة سابقة في سياق المستخدم
        if 'current_campaign' in context.user_data:
            logging.info(f"Clearing previous campaign data in user context")
            del context.user_data['current_campaign']
        
        # تهيئة قاموس الحملة بكل القيم الافتراضية المطلوبة
        context.user_data['current_campaign'] = {
            'id': campaign_id,
            'name': '',
            'created_at': datetime.now().isoformat(),
            'status': 'draft',
            'sent_count': 0,
            'success_count': 0,
            'created_by': update.effective_user.id,
            'has_image': False,
            'type': 'announcement',  # قيمة افتراضية
            'type_name': CAMPAIGN_TYPES.get('announcement', 'إعلان عام'),
            'target': 'all',  # قيمة افتراضية
            'target_name': 'جميع العملاء',
            'message': '',
            'max_customers': 0,
            'discount': 0,
            'min_order': 0
        }
        
        logging.info(f"Campaign data initialized: {context.user_data['current_campaign']}")
        
        # إرسال رسالة لطلب اسم الحملة
        await update.callback_query.answer()
        await update.callback_query.edit_message_text(
            "🏷️ أدخل اسماً للحملة التسويقية الجديدة:",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("إلغاء", callback_data="campaign_back_main")]
            ])
        )
        return CAMPAIGN_NAME
        
    except Exception as e:
        logging.error(f"Error in start_campaign_creation: {e}")
        import traceback
        logging.error(traceback.format_exc())
        
        try:
            if update.callback_query:
                await update.callback_query.answer("حدث خطأ أثناء بدء إنشاء الحملة")
                await update.callback_query.edit_message_text(
                    "⚠️ حدث خطأ أثناء بدء إنشاء الحملة. يرجى المحاولة مرة أخرى.",
                    reply_markup=InlineKeyboardMarkup([
                        [InlineKeyboardButton("العودة للقائمة الرئيسية", callback_data="campaign_back_main")]
                    ])
                )
            else:
                # إذا لم يكن هناك callback_query، نحاول الرد على الرسالة إذا كانت موجودة
                if update.message:
                    await update.message.reply_text(
                        "⚠️ حدث خطأ أثناء بدء إنشاء الحملة. يرجى المحاولة مرة أخرى.",
                        reply_markup=InlineKeyboardMarkup([
                            [InlineKeyboardButton("العودة للقائمة الرئيسية", callback_data="campaign_back_main")]
                        ])
                    )
        except Exception as inner_e:
            logging.error(f"Error sending error message: {inner_e}")
        
        return ConversationHandler.END

async def received_campaign_name(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """معالجة اسم الحملة المستلم."""
    try:
        campaign_name = update.message.text.strip()
        logging.info(f"Received campaign name: {campaign_name}")
        
        if len(campaign_name) < 3:
            await update.message.reply_text(
                "⚠️ يجب أن يكون اسم الحملة أكثر من 3 أحرف. يرجى المحاولة مرة أخرى:"
            )
            return CAMPAIGN_NAME
        
        # تأكد من وجود قاموس الحملة الحالية
        if 'current_campaign' not in context.user_data:
            logging.warning("Creating missing current_campaign dictionary in user_data during name processing")
            # إنشاء معرف فريد للحملة
            campaign_id = str(uuid.uuid4())
            context.user_data['current_campaign'] = {
                'id': campaign_id,
                'created_at': datetime.now().isoformat(),
                'status': 'draft',
                'sent_count': 0,
                'success_count': 0,
                'created_by': update.effective_user.id,
                'has_image': False,
                'type': '',
                'type_name': '',
                'target': '',
                'target_name': '',
                'message': '',
                'max_customers': 0,
                'discount': 0,
                'min_order': 0
            }
            
        context.user_data['current_campaign']['name'] = campaign_name
        logging.info(f"Saved campaign name to user_data: {campaign_name}")
        
        # اختيار نوع الحملة
        keyboard = []
        for type_key, type_name in CAMPAIGN_TYPES.items():
            keyboard.append([InlineKeyboardButton(f"{type_name}", callback_data=f"campaign_type_{type_key}")])
        
        keyboard.append([InlineKeyboardButton("إلغاء", callback_data="campaign_back_main")])
        
        await update.message.reply_text(
            "📋 اختر نوع الحملة التسويقية:",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
        return CAMPAIGN_TYPE
        
    except Exception as e:
        logging.error(f"Error in received_campaign_name: {e}")
        import traceback
        logging.error(traceback.format_exc())
        
        await update.message.reply_text(
            "⚠️ حدث خطأ أثناء معالجة اسم الحملة. يرجى المحاولة مرة أخرى لاحقاً.",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("العودة للقائمة الرئيسية", callback_data="campaign_back_main")]
            ])
        )
        
        return ConversationHandler.END

async def received_campaign_type(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """معالجة نوع الحملة المختار."""
    try:
        query = update.callback_query
        await query.answer()
        
        type_key = query.data.replace("campaign_type_", "")
        logging.info(f"Received campaign type: {type_key}")
        
        if type_key in CAMPAIGN_TYPES:
            logging.info(f"Setting campaign type to: {type_key}, {CAMPAIGN_TYPES[type_key]}")
            
            # تأكد من وجود قاموس الحملة الحالية
            if 'current_campaign' not in context.user_data:
                context.user_data['current_campaign'] = {}
                logging.warning("Creating missing current_campaign dictionary in user_data")
                
            context.user_data['current_campaign']['type'] = type_key
            context.user_data['current_campaign']['type_name'] = CAMPAIGN_TYPES[type_key]
            
            # إختيار الجمهور المستهدف
            keyboard = [
                [InlineKeyboardButton("جميع العملاء", callback_data="campaign_target_all")],
                [InlineKeyboardButton("العملاء الجدد فقط", callback_data="campaign_target_new")],
                [InlineKeyboardButton("العملاء السابقين فقط", callback_data="campaign_target_returning")],
                [InlineKeyboardButton("إلغاء", callback_data="campaign_back_main")]
            ]
            
            await query.edit_message_text(
                "👥 اختر الجمهور المستهدف للحملة:",
                reply_markup=InlineKeyboardMarkup(keyboard)
            )
            return CAMPAIGN_TARGET
        else:
            logging.warning(f"Invalid campaign type: {type_key}")
            await query.edit_message_text(
                "⚠️ نوع حملة غير صالح. يرجى المحاولة مرة أخرى.",
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("العودة", callback_data="campaign_create")]
                ])
            )
            return ConversationHandler.END
    except Exception as e:
        logging.error(f"Error in received_campaign_type: {e}")
        import traceback
        logging.error(traceback.format_exc())
        
        # محاولة إرسال رسالة للمستخدم
        try:
            if update.callback_query:
                await update.callback_query.answer("حدث خطأ أثناء معالجة نوع الحملة")
                await update.callback_query.edit_message_text(
                    "⚠️ حدث خطأ أثناء معالجة نوع الحملة. يرجى المحاولة مرة أخرى.",
                    reply_markup=InlineKeyboardMarkup([
                        [InlineKeyboardButton("العودة", callback_data="campaign_back_main")]
                    ])
                )
            else:
                await update.message.reply_text(
                    "⚠️ حدث خطأ أثناء معالجة نوع الحملة. يرجى المحاولة مرة أخرى."
                )
        except Exception as inner_e:
            logging.error(f"Error sending error message: {inner_e}")
        
        return ConversationHandler.END

async def received_campaign_target(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """معالجة الجمهور المستهدف المختار."""
    try:
        query = update.callback_query
        await query.answer()
        
        target = query.data.replace("campaign_target_", "")
        logging.info(f"Received campaign target: {target}")
        
        # تأكد من وجود قاموس الحملة الحالية
        if 'current_campaign' not in context.user_data:
            context.user_data['current_campaign'] = {}
            logging.warning("Creating missing current_campaign dictionary in user_data")
            
        context.user_data['current_campaign']['target'] = target
        
        target_name_map = {
            "all": "جميع العملاء",
            "new": "العملاء الجدد فقط", 
            "returning": "العملاء السابقين فقط"
        }
        context.user_data['current_campaign']['target_name'] = target_name_map.get(target, "غير محدد")
        
        # طلب نص الرسالة التسويقية
        await query.edit_message_text(
            "✍️ أدخل نص الرسالة التسويقية، يمكنك استخدام العناصر التالية في الرسالة:\n"
            "• {{customer_name}} - اسم العميل\n"
            "• {{discount}} - قيمة الخصم (إذا كانت الحملة تتضمن خصم)\n\n"
            "نموذج: مرحباً {{customer_name}}! لدينا عرض خاص لك: خصم {{discount}}% على جميع منتجاتنا.",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("إلغاء", callback_data="campaign_back_main")]
            ])
        )
        return CAMPAIGN_MESSAGE
    except Exception as e:
        logging.error(f"Error in received_campaign_target: {e}")
        import traceback
        logging.error(traceback.format_exc())
        
        # محاولة إرسال رسالة للمستخدم
        try:
            if update.callback_query:
                await update.callback_query.answer("حدث خطأ أثناء معالجة الجمهور المستهدف")
                await update.callback_query.edit_message_text(
                    "⚠️ حدث خطأ أثناء معالجة الجمهور المستهدف. يرجى المحاولة مرة أخرى.",
                    reply_markup=InlineKeyboardMarkup([
                        [InlineKeyboardButton("العودة", callback_data="campaign_back_main")]
                    ])
                )
            else:
                await update.message.reply_text(
                    "⚠️ حدث خطأ أثناء معالجة الجمهور المستهدف. يرجى المحاولة مرة أخرى."
                )
        except Exception as inner_e:
            logging.error(f"Error sending error message: {inner_e}")
        
        return ConversationHandler.END

async def received_campaign_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """معالجة نص الرسالة التسويقية."""
    try:
        message_text = update.message.text.strip()
        logging.info(f"Received campaign message text (length: {len(message_text)})")
        
        if len(message_text) < 10:
            await update.message.reply_text(
                "⚠️ يجب أن يكون نص الرسالة أكثر من 10 أحرف. يرجى المحاولة مرة أخرى:"
            )
            return CAMPAIGN_MESSAGE
        
        # تأكد من وجود قاموس الحملة الحالية
        if 'current_campaign' not in context.user_data:
            logging.warning("Creating missing current_campaign dictionary in user_data during message processing")
            # إنشاء معرف فريد للحملة
            campaign_id = str(uuid.uuid4())
            context.user_data['current_campaign'] = {
                'id': campaign_id,
                'created_at': datetime.now().isoformat(),
                'status': 'draft',
                'sent_count': 0,
                'success_count': 0,
                'created_by': update.effective_user.id,
                'has_image': False,
                'type': 'promotion', # قيمة افتراضية
                'type_name': CAMPAIGN_TYPES.get('promotion', 'إعلان عام'),
                'target': 'all',
                'target_name': 'جميع العملاء',
                'max_customers': 0,
                'discount': 0,
                'min_order': 0
            }
            
        context.user_data['current_campaign']['message'] = message_text
        logging.info("Saved campaign message to user_data")
        
        # المرحلة التالية تعتمد على نوع الحملة
        campaign_type = context.user_data['current_campaign'].get('type', '')
        logging.info(f"Current campaign type: {campaign_type}")
        
        if not campaign_type:
            logging.warning("Campaign type is empty, defaulting to promotion")
            campaign_type = 'promotion'
            context.user_data['current_campaign']['type'] = campaign_type
            context.user_data['current_campaign']['type_name'] = CAMPAIGN_TYPES.get(campaign_type, 'إعلان عام')
        
        if campaign_type == "discount":
            await update.message.reply_text(
                "💯 أدخل نسبة الخصم (رقم فقط، مثال: 10 لخصم 10%):"
            )
            return CAMPAIGN_DISCOUNT
        elif campaign_type == "free_product":
            await update.message.reply_text(
                "💰 أدخل الحد الأدنى لقيمة الطلب للحصول على المنتج المجاني (رقم فقط):"
            )
            return CAMPAIGN_MIN_ORDER
        else:
            # بالنسبة للإعلانات والعروض الخاصة، انتقل مباشرة إلى تحديد عدد العملاء
            await update.message.reply_text(
                "👥 أدخل الحد الأقصى لعدد العملاء المستهدفين في هذه الحملة (رقم فقط، 0 للجميع):"
            )
            return CAMPAIGN_MAX_CUSTOMERS
            
    except Exception as e:
        logging.error(f"Error in received_campaign_message: {e}")
        import traceback
        logging.error(traceback.format_exc())
        
        await update.message.reply_text(
            "⚠️ حدث خطأ أثناء معالجة نص الرسالة. يرجى المحاولة مرة أخرى.",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("العودة للقائمة الرئيسية", callback_data="campaign_back_main")]
            ])
        )
        
        return ConversationHandler.END

async def received_campaign_discount(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """معالجة نسبة الخصم المستلمة."""
    try:
        discount = int(update.message.text.strip())
        if discount <= 0 or discount > 100:
            raise ValueError("Discount must be between 1 and 100")
    except ValueError:
        await update.message.reply_text(
            "⚠️ يرجى إدخال رقم صحيح بين 1 و 100 للخصم:"
        )
        return CAMPAIGN_DISCOUNT
    
    context.user_data['current_campaign']['discount'] = discount
    
    # طلب الحد الأقصى لعدد العملاء
    await update.message.reply_text(
        "👥 أدخل الحد الأقصى لعدد العملاء المستهدفين في هذه الحملة (رقم فقط، 0 للجميع):"
    )
    return CAMPAIGN_MAX_CUSTOMERS

async def received_campaign_min_order(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """معالجة الحد الأدنى لقيمة الطلب."""
    try:
        min_order = float(update.message.text.strip())
        if min_order < 0:
            raise ValueError("Min order must be positive")
    except ValueError:
        await update.message.reply_text(
            "⚠️ يرجى إدخال رقم موجب لقيمة الحد الأدنى للطلب:"
        )
        return CAMPAIGN_MIN_ORDER
    
    context.user_data['current_campaign']['min_order'] = min_order
    
    # طلب الحد الأقصى لعدد العملاء
    await update.message.reply_text(
        "👥 أدخل الحد الأقصى لعدد العملاء المستهدفين في هذه الحملة (رقم فقط، 0 للجميع):"
    )
    return CAMPAIGN_MAX_CUSTOMERS

async def received_campaign_max_customers(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """معالجة الحد الأقصى لعدد العملاء."""
    try:
        max_customers = int(update.message.text.strip())
        if max_customers < 0:
            raise ValueError("Max customers must be positive")
    except ValueError:
        await update.message.reply_text(
            "⚠️ يرجى إدخال رقم صحيح موجب لعدد العملاء:"
        )
        return CAMPAIGN_MAX_CUSTOMERS
    
    context.user_data['current_campaign']['max_customers'] = max_customers
    
    # سؤال إذا كان المستخدم يريد إضافة صورة للحملة
    keyboard = [
        [InlineKeyboardButton("نعم، أريد إضافة صورة", callback_data="campaign_add_image")],
        [InlineKeyboardButton("لا، متابعة بدون صورة", callback_data="campaign_no_image")]
    ]
    
    await update.message.reply_text(
        "🖼️ هل تريد إضافة صورة للحملة التسويقية؟",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )
    return CAMPAIGN_IMAGE

async def handle_campaign_image_choice(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """معالجة اختيار إضافة صورة للحملة."""
    query = update.callback_query
    await query.answer()
    
    if query.data == "campaign_add_image":
        await query.edit_message_text(
            "📤 يرجى إرسال الصورة التي تريد استخدامها للحملة التسويقية."
        )
        return CAMPAIGN_IMAGE
    else:  # campaign_no_image
        # المتابعة بدون صورة، الانتقال إلى تأكيد الحملة
        context.user_data['current_campaign']['has_image'] = False
        await show_campaign_confirmation(update, context)
        return CAMPAIGN_CONFIRMATION

async def received_campaign_image(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """معالجة صورة الحملة المستلمة."""
    try:
        # الحصول على أكبر نسخة من الصورة المرفقة
        photo = update.message.photo[-1]
        file = await context.bot.get_file(photo.file_id)
        
        # تحديد مسار الصورة وتنزيلها
        campaign_id = context.user_data['current_campaign']['id']
        campaign_images_dir = "data/campaigns/images"
        os.makedirs(campaign_images_dir, exist_ok=True)
        image_path = f"{campaign_images_dir}/{campaign_id}.jpg"
        logging.info(f"حفظ صورة الحملة في المسار: {image_path}")
        
        # تنزيل الصورة
        await file.download_to_drive(image_path)
        
        # تخزين معلومات الصورة
        context.user_data['current_campaign']['has_image'] = True
        context.user_data['current_campaign']['image_path'] = image_path
        
        await update.message.reply_text("✅ تم استلام الصورة بنجاح!")
        
        # عرض شاشة التأكيد
        await show_campaign_confirmation(update, context)
        return CAMPAIGN_CONFIRMATION
        
    except Exception as e:
        logging.error(f"Error processing campaign image: {e}")
        await update.message.reply_text(
            "⚠️ حدث خطأ أثناء معالجة الصورة. يرجى المحاولة مرة أخرى أو المتابعة بدون صورة.",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("متابعة بدون صورة", callback_data="campaign_no_image")],
                [InlineKeyboardButton("إلغاء", callback_data="campaign_back_main")]
            ])
        )
        return CAMPAIGN_IMAGE

async def show_campaign_confirmation(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """عرض ملخص الحملة للتأكيد."""
    campaign = context.user_data['current_campaign']
    
    summary = f"""
*مراجعة تفاصيل الحملة التسويقية*

📝 *الاسم:* {campaign['name']}
📋 *النوع:* {campaign['type_name']}
👥 *الجمهور المستهدف:* {campaign['target_name']}
"""
    
    if campaign['type'] == "discount":
        summary += f"💯 *نسبة الخصم:* {campaign['discount']}%\n"
    elif campaign['type'] == "free_product":
        summary += f"💰 *الحد الأدنى للطلب:* {campaign['min_order']}\n"
    
    summary += f"""
👥 *الحد الأقصى للعملاء:* {campaign['max_customers'] if campaign['max_customers'] > 0 else 'بلا حدود'}
🖼️ *تتضمن صورة:* {'نعم' if campaign.get('has_image', False) else 'لا'}

📝 *نص الرسالة:*
{campaign['message']}

هل تريد حفظ هذه الحملة؟
"""
    
    keyboard = [
        [InlineKeyboardButton("✅ حفظ الحملة", callback_data="campaign_confirm_save")],
        [InlineKeyboardButton("🖊️ تعديل الرسالة", callback_data="campaign_edit_message")],
        [InlineKeyboardButton("❌ إلغاء", callback_data="campaign_back_main")]
    ]
    
    # تحديد نوع الرسالة بناء على نوع التحديث
    if update.callback_query:
        await update.callback_query.edit_message_text(
            summary, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="Markdown"
        )
    else:
        await update.message.reply_text(
            summary, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="Markdown"
        )
    
    return CAMPAIGN_CONFIRMATION

async def handle_campaign_confirmation(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """معالجة تأكيد الحملة."""
    try:
        query = update.callback_query
        await query.answer()
        
        if query.data == "campaign_confirm_save":
            # التأكد من وجود بيانات الحملة في سياق المستخدم
            if 'current_campaign' not in context.user_data:
                logging.error("Missing current_campaign in user_data during confirmation")
                await query.edit_message_text(
                    "⚠️ حدث خطأ: لم يتم العثور على بيانات الحملة. يرجى المحاولة مرة أخرى.",
                    reply_markup=InlineKeyboardMarkup([
                        [InlineKeyboardButton("العودة للقائمة الرئيسية", callback_data="campaign_back_main")]
                    ])
                )
                return ConversationHandler.END
                
            # حفظ الحملة
            campaign = context.user_data['current_campaign']
            campaign['status'] = 'active'
            campaign['created_at'] = datetime.now().isoformat()
            
            # التأكد من وجود اسم للحملة
            if 'name' not in campaign or not campaign['name']:
                campaign['name'] = f"حملة {datetime.now().strftime('%Y-%m-%d')}"
                logging.warning(f"Missing campaign name, using default: {campaign['name']}")
            
            # تحميل الحملات الحالية وإضافة الحملة الجديدة
            campaigns_data = load_campaigns()
            
            # إنشاء قائمة فارغة إذا لم تكن موجودة
            if 'campaigns' not in campaigns_data:
                campaigns_data['campaigns'] = []
            
            campaigns_data['campaigns'].append(campaign)
            
            # حفظ البيانات وفحص النتيجة
            save_result = save_campaigns(campaigns_data)
            
            if save_result:
                # تأكيد الحفظ للمستخدم
                keyboard = [
                    [InlineKeyboardButton("🚀 إرسال الحملة الآن", callback_data=f"campaign_send_{campaign['id']}")],
                    [InlineKeyboardButton("📋 عرض الحملات", callback_data="campaign_list_active")],
                    [InlineKeyboardButton("🏠 القائمة الرئيسية", callback_data="campaign_back_main")]
                ]
                
                await query.edit_message_text(
                    f"✅ تم حفظ الحملة '{campaign['name']}' بنجاح!\n\n"
                    f"يمكنك إرسالها الآن أو العودة إلى قائمة الحملات.",
                    reply_markup=InlineKeyboardMarkup(keyboard)
                )
                logging.info(f"Campaign saved successfully: {campaign['id']} - {campaign['name']}")
            else:
                await query.edit_message_text(
                    "⚠️ حدث خطأ أثناء حفظ الحملة. يرجى المحاولة مرة أخرى.",
                    reply_markup=InlineKeyboardMarkup([
                        [InlineKeyboardButton("إعادة المحاولة", callback_data="campaign_confirm_save")],
                        [InlineKeyboardButton("العودة للقائمة الرئيسية", callback_data="campaign_back_main")]
                    ])
                )
                logging.error(f"Failed to save campaign: {campaign['id']} - {campaign['name']}")
    except Exception as e:
        logging.error(f"Error in handle_campaign_confirmation: {e}")
        import traceback
        logging.error(traceback.format_exc())
        
        try:
            await update.callback_query.answer("حدث خطأ أثناء تأكيد الحملة")
            await update.callback_query.edit_message_text(
                "⚠️ حدث خطأ أثناء تأكيد الحملة. يرجى المحاولة مرة أخرى.",
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("العودة للقائمة الرئيسية", callback_data="campaign_back_main")]
                ])
            )
        except Exception as inner_e:
            logging.error(f"Error sending error message: {inner_e}")
        
        # مسح بيانات الحملة من context
        if 'current_campaign' in context.user_data:
            del context.user_data['current_campaign']
        
        return ConversationHandler.END
    
    # إذا كان خيار المستخدم هو تعديل النص
    if update.callback_query and update.callback_query.data == "campaign_edit_message":
        # العودة إلى تعديل نص الرسالة
        current_message = context.user_data['current_campaign']['message']
        
        await update.callback_query.edit_message_text(
            f"✍️ أدخل النص الجديد للرسالة التسويقية:\n\n"
            f"النص الحالي:\n{current_message}"
        )
        return CAMPAIGN_MESSAGE
        
    # إلغاء الإنشاء أو العودة للقائمة الرئيسية
    elif update.callback_query and update.callback_query.data == "campaign_back_main":
        # إلغاء إنشاء الحملة
        if 'current_campaign' in context.user_data:
            # إذا كان هناك صورة تم تحميلها، يمكن حذفها
            if context.user_data['current_campaign'].get('has_image', False):
                image_path = context.user_data['current_campaign']['image_path']
                try:
                    if os.path.exists(image_path):
                        os.remove(image_path)
                except Exception as e:
                    logging.error(f"Error removing temporary campaign image: {e}")
            
            # مسح بيانات الحملة
            del context.user_data['current_campaign']
        
        await update_campaign_main_menu(update, context)
        return ConversationHandler.END

async def list_active_campaigns(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """عرض قائمة الحملات النشطة."""
    campaigns_data = load_campaigns()
    active_campaigns = [c for c in campaigns_data['campaigns'] if c['status'] == 'active']
    
    if not active_campaigns:
        await update.callback_query.edit_message_text(
            "📭 لا توجد حملات نشطة حالياً.",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("➕ إنشاء حملة جديدة", callback_data="campaign_create")],
                [InlineKeyboardButton("🏠 العودة", callback_data="campaign_back_main")]
            ])
        )
        return
    
    # تحضير قائمة الحملات
    message = "📋 *الحملات النشطة:*\n\n"
    keyboard = []
    
    for i, campaign in enumerate(active_campaigns, 1):
        created_date = datetime.fromisoformat(campaign['created_at']).strftime("%Y-%m-%d")
        message += f"{i}. *{campaign['name']}* ({campaign['type_name']}) - إنشاء: {created_date}\n"
        
        # أزرار لكل حملة
        keyboard.append([
            InlineKeyboardButton(f"📝 {campaign['name']}", callback_data=f"campaign_view_{campaign['id']}")
        ])
    
    keyboard.append([InlineKeyboardButton("🏠 العودة", callback_data="campaign_back_main")])
    
    await update.callback_query.edit_message_text(
        message,
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode="Markdown"
    )

async def list_past_campaigns(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """عرض قائمة الحملات السابقة (المكتملة)."""
    campaigns_data = load_campaigns()
    past_campaigns = [c for c in campaigns_data['campaigns'] if c['status'] == 'completed']
    
    if not past_campaigns:
        await update.callback_query.edit_message_text(
            "📭 لا توجد حملات سابقة مكتملة.",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("📋 عرض الحملات النشطة", callback_data="campaign_list_active")],
                [InlineKeyboardButton("🏠 العودة", callback_data="campaign_back_main")]
            ])
        )
        return
    
    # تحضير قائمة الحملات
    message = "📋 *الحملات السابقة:*\n\n"
    keyboard = []
    
    for i, campaign in enumerate(past_campaigns, 1):
        created_date = datetime.fromisoformat(campaign['created_at']).strftime("%Y-%m-%d")
        message += f"{i}. *{campaign['name']}* ({campaign['type_name']}) - إنشاء: {created_date}\n"
        message += f"   👤 تم إرسال: {campaign.get('sent_count', 0)} | ✅ ناجح: {campaign.get('success_count', 0)}\n"
        
        # أزرار لكل حملة
        keyboard.append([
            InlineKeyboardButton(f"📝 {campaign['name']}", callback_data=f"campaign_view_{campaign['id']}")
        ])
    
    keyboard.append([InlineKeyboardButton("🏠 العودة", callback_data="campaign_back_main")])
    
    await update.callback_query.edit_message_text(
        message,
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode="Markdown"
    )

async def view_campaign_details(update: Update, context: ContextTypes.DEFAULT_TYPE, campaign_id: str = None):
    """عرض تفاصيل حملة محددة."""
    if not campaign_id and update.callback_query:
        campaign_id = update.callback_query.data.replace("campaign_view_", "")
    
    campaigns_data = load_campaigns()
    campaign = None
    
    for c in campaigns_data['campaigns']:
        if c['id'] == campaign_id:
            campaign = c
            break
    
    if not campaign:
        await update.callback_query.edit_message_text(
            "⚠️ لم يتم العثور على الحملة المطلوبة.",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("🏠 العودة", callback_data="campaign_back_main")]
            ])
        )
        return
    
    # تحضير تفاصيل الحملة
    created_date = datetime.fromisoformat(campaign['created_at']).strftime("%Y-%m-%d %H:%M")
    
    details = f"""
*تفاصيل الحملة: {campaign['name']}*

📅 *تاريخ الإنشاء:* {created_date}
📋 *النوع:* {campaign['type_name']}
👥 *الجمهور المستهدف:* {campaign['target_name']}
📊 *الحالة:* {'نشطة' if campaign['status'] == 'active' else 'مكتملة'}
"""
    
    if campaign['type'] == "discount":
        details += f"💯 *نسبة الخصم:* {campaign['discount']}%\n"
    elif campaign['type'] == "free_product":
        details += f"💰 *الحد الأدنى للطلب:* {campaign['min_order']}\n"
    
    details += f"""
👥 *الحد الأقصى للعملاء:* {campaign['max_customers'] if campaign['max_customers'] > 0 else 'بلا حدود'}
🖼️ *تتضمن صورة:* {'نعم' if campaign.get('has_image', False) else 'لا'}
📨 *الإرسال:* {campaign.get('sent_count', 0)} رسالة | ✅ ناجح: {campaign.get('success_count', 0)}

📝 *نص الرسالة:*
{campaign['message']}
"""
    
    # إعداد أزرار العمليات المتاحة
    keyboard = []
    
    if campaign['status'] == 'active':
        keyboard.append([InlineKeyboardButton("🚀 إرسال الحملة", callback_data=f"campaign_send_{campaign['id']}")])
    
    keyboard.extend([
        [InlineKeyboardButton("❌ حذف الحملة", callback_data=f"campaign_delete_{campaign['id']}")],
        [InlineKeyboardButton("🏠 العودة", callback_data="campaign_back_main")]
    ])
    
    await update.callback_query.edit_message_text(
        details,
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode="Markdown"
    )

async def send_campaign_messages(update: Update, context: ContextTypes.DEFAULT_TYPE, campaign_id: str = None):
    """إرسال رسائل الحملة التسويقية للعملاء المستهدفين."""
    if not campaign_id and update.callback_query:
        campaign_id = update.callback_query.data.replace("campaign_send_", "")
    
    # البحث عن الحملة في البيانات
    campaigns_data = load_campaigns()
    campaign = None
    
    for i, c in enumerate(campaigns_data['campaigns']):
        if c['id'] == campaign_id:
            campaign = c
            campaign_index = i
            break
    
    if not campaign:
        await update.callback_query.edit_message_text(
            "⚠️ لم يتم العثور على الحملة المطلوبة.",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("🏠 العودة", callback_data="campaign_back_main")]
            ])
        )
        return
    
    # تأكيد النية بإرسال الحملة
    await update.callback_query.edit_message_text(
        f"🚀 هل أنت متأكد من رغبتك في إرسال حملة '{campaign['name']}' للعملاء المستهدفين؟\n\n"
        f"👥 الجمهور المستهدف: {campaign['target_name']}\n"
        f"📤 قد يستغرق الإرسال بضع دقائق حسب عدد العملاء.",
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("✅ نعم، بدء الإرسال", callback_data=f"campaign_confirm_send_{campaign_id}")],
            [InlineKeyboardButton("❌ لا، إلغاء", callback_data=f"campaign_view_{campaign_id}")]
        ])
    )

async def confirm_send_campaign(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """تأكيد إرسال الحملة التسويقية ومعالجة الإرسال."""
    campaign_id = update.callback_query.data.replace("campaign_confirm_send_", "")
    await update.callback_query.answer("جاري بدء إرسال الحملة...")
    
    status_message = await update.callback_query.edit_message_text(
        "🔄 جاري تجهيز الحملة وإرسال الرسائل...\n"
        "يرجى الانتظار، قد يستغرق هذا بعض الوقت."
    )
    
    # البحث عن الحملة في البيانات
    campaigns_data = load_campaigns()
    campaign = None
    campaign_index = -1
    
    for i, c in enumerate(campaigns_data['campaigns']):
        if c['id'] == campaign_id:
            campaign = c
            campaign_index = i
            break
    
    if not campaign or campaign_index == -1:
        await status_message.edit_text(
            "⚠️ لم يتم العثور على الحملة المطلوبة.",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("🏠 العودة", callback_data="campaign_back_main")]
            ])
        )
        return
    
    # جلب جميع الإشعارات (العملاء)
    notifications = db.get_all_notifications()
    
    if not notifications:
        await status_message.edit_text(
            "⚠️ لا يوجد عملاء في قاعدة البيانات لإرسال الحملة إليهم.",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("🏠 العودة", callback_data="campaign_back_main")]
            ])
        )
        return
    
    # تصفية العملاء حسب الجمهور المستهدف
    target_customers = []
    current_time = datetime.now()
    
    if campaign['target'] == 'all':
        target_customers = notifications
    elif campaign['target'] == 'new':
        # اعتبار العملاء الجدد خلال الشهر الأخير
        for customer in notifications:
            created_at = customer.get('created_at')
            if created_at:
                try:
                    created_date = datetime.fromisoformat(created_at)
                    days_diff = (current_time - created_date).days
                    if days_diff <= 30:  # عملاء الشهر الأخير
                        target_customers.append(customer)
                except (ValueError, TypeError):
                    pass
    elif campaign['target'] == 'returning':
        # اعتبار العملاء العائدين أقدم من شهر
        for customer in notifications:
            created_at = customer.get('created_at')
            if created_at:
                try:
                    created_date = datetime.fromisoformat(created_at)
                    days_diff = (current_time - created_date).days
                    if days_diff > 30:  # أقدم من شهر
                        target_customers.append(customer)
                except (ValueError, TypeError):
                    pass
    
    # تحديد العدد الأقصى للعملاء إذا تم تعيينه
    if campaign['max_customers'] > 0 and len(target_customers) > campaign['max_customers']:
        target_customers = target_customers[:campaign['max_customers']]
    
    if not target_customers:
        await status_message.edit_text(
            "⚠️ لا يوجد عملاء يطابقون معايير الاستهداف في هذه الحملة.",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("🏠 العودة", callback_data="campaign_back_main")]
            ])
        )
        return
    
    # جلب صورة الحملة إذا كانت موجودة
    image_path = None
    if campaign.get('has_image', False) and os.path.exists(campaign['image_path']):
        image_path = campaign['image_path']
    
    # بدء عملية الإرسال
    sent_count = 0
    success_count = 0
    
    for customer in target_customers:
        customer_name = customer.get('customer_name', 'العميل')
        phone_number = customer.get('phone_number', '')
        
        if not phone_number:
            continue
        
        # تخصيص الرسالة
        message = campaign['message']
        message = message.replace('{{customer_name}}', customer_name)
        
        # إضافة تفاصيل إضافية حسب نوع الحملة
        if campaign['type'] == 'discount':
            message = message.replace('{{discount}}', str(campaign['discount']))
        elif campaign['type'] == 'free_product' and '{{min_order}}' in message:
            message = message.replace('{{min_order}}', str(campaign['min_order']))
        
        # إرسال الرسالة عبر واتساب
        try:
            result = False
            
            if image_path:
                # إرسال رسالة مع صورة
                try:
                    # قراءة ملف الصورة
                    with open(image_path, "rb") as f:
                        image_data = f.read()
                    # إرسال صورة مع رسالة
                    success, result = send_whatsapp_image(phone_number, image_data, message)
                except Exception as img_error:
                    logging.error(f"Error sending image: {img_error}")
                    success, result = send_whatsapp_message(phone_number, message)
            else:
                # إرسال رسالة نصية فقط
                # إرسال رسالة نصية فقط
                success, result = send_whatsapp_message(phone_number, message)
            
            sent_count += 1
            if result:
                success_count += 1
            
            # تحديث الرسالة كل 5 عملاء
            if sent_count % 5 == 0:
                await status_message.edit_text(
                    f"🔄 جاري إرسال الحملة...\n"
                    f"تم إرسال {sent_count} من أصل {len(target_customers)} رسالة.\n"
                    f"✅ ناجح: {success_count}"
                )
        
        except Exception as e:
            logging.error(f"Error sending campaign message to {phone_number}: {e}")
            continue
    
    # تحديث حالة الحملة وإحصائياتها
    campaign['status'] = 'completed'
    campaign['sent_count'] = sent_count
    campaign['success_count'] = success_count
    campaign['completed_at'] = current_time.isoformat()
    
    campaigns_data['campaigns'][campaign_index] = campaign
    save_campaigns(campaigns_data)
    
    # إرسال تقرير الإكمال
    success_rate = 0 if sent_count == 0 else (success_count / sent_count) * 100
    
    await status_message.edit_text(
        f"✅ *تم اكتمال إرسال الحملة*\n\n"
        f"📊 *إحصائيات الإرسال:*\n"
        f"• إجمالي العملاء المستهدفين: {len(target_customers)}\n"
        f"• تم إرسال: {sent_count} رسالة\n"
        f"• ناجح: {success_count} رسالة\n"
        f"• نسبة النجاح: {success_rate:.1f}%\n\n"
        f"الحملة الآن مكتملة ويمكنك مشاهدتها في سجل الحملات السابقة.",
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("📋 عرض الحملات السابقة", callback_data="campaign_list_past")],
            [InlineKeyboardButton("🏠 العودة للقائمة الرئيسية", callback_data="campaign_back_main")]
        ]),
        parse_mode="Markdown"
    )

async def delete_campaign(update: Update, context: ContextTypes.DEFAULT_TYPE, campaign_id: str = None):
    """حذف حملة تسويقية."""
    if not campaign_id and update.callback_query:
        campaign_id = update.callback_query.data.replace("campaign_delete_", "")
    
    # تأكيد نية الحذف
    await update.callback_query.edit_message_text(
        "⚠️ هل أنت متأكد من رغبتك في حذف هذه الحملة؟\n"
        "هذا الإجراء لا يمكن التراجع عنه.",
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("✅ نعم، حذف نهائي", callback_data=f"campaign_confirm_delete_{campaign_id}")],
            [InlineKeyboardButton("❌ لا، إلغاء", callback_data=f"campaign_view_{campaign_id}")]
        ])
    )

async def confirm_delete_campaign(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """تأكيد حذف الحملة ومعالجة الحذف."""
    campaign_id = update.callback_query.data.replace("campaign_confirm_delete_", "")
    await update.callback_query.answer()
    
    # البحث عن الحملة وحذفها
    campaigns_data = load_campaigns()
    
    for i, campaign in enumerate(campaigns_data['campaigns']):
        if campaign['id'] == campaign_id:
            # حذف الصورة إذا كانت موجودة
            if campaign.get('has_image', False) and 'image_path' in campaign:
                try:
                    if os.path.exists(campaign['image_path']):
                        os.remove(campaign['image_path'])
                except Exception as e:
                    logging.error(f"Error removing campaign image: {e}")
            
            # حذف الحملة من القائمة
            del campaigns_data['campaigns'][i]
            save_campaigns(campaigns_data)
            
            await update.callback_query.edit_message_text(
                "✅ تم حذف الحملة بنجاح.",
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("🏠 العودة", callback_data="campaign_back_main")]
                ])
            )
            return
    
    # إذا لم يتم العثور على الحملة
    await update.callback_query.edit_message_text(
        "⚠️ لم يتم العثور على الحملة المطلوبة.",
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("🏠 العودة", callback_data="campaign_back_main")]
        ])
    )

async def show_campaign_stats(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """عرض إحصائيات الحملات التسويقية."""
    campaigns_data = load_campaigns()
    
    if not campaigns_data['campaigns']:
        await update.callback_query.edit_message_text(
            "📊 *إحصائيات الحملات التسويقية*\n\n"
            "لم يتم إنشاء أي حملات بعد.",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("➕ إنشاء أول حملة", callback_data="campaign_create")],
                [InlineKeyboardButton("🏠 العودة", callback_data="campaign_back_main")]
            ]),
            parse_mode="Markdown"
        )
        return
    
    # تحليل وإنشاء إحصائيات
    total_campaigns = len(campaigns_data['campaigns'])
    active_campaigns = len([c for c in campaigns_data['campaigns'] if c['status'] == 'active'])
    completed_campaigns = len([c for c in campaigns_data['campaigns'] if c['status'] == 'completed'])
    
    total_sent = sum(c.get('sent_count', 0) for c in campaigns_data['campaigns'])
    total_success = sum(c.get('success_count', 0) for c in campaigns_data['campaigns'])
    
    success_rate = 0 if total_sent == 0 else (total_success / total_sent) * 100
    
    # تحليل حسب نوع الحملة
    campaign_types = {}
    for c in campaigns_data['campaigns']:
        campaign_type = c.get('type_name', c.get('type', 'غير محدد'))
        if campaign_type not in campaign_types:
            campaign_types[campaign_type] = 0
        campaign_types[campaign_type] += 1
    
    # إنشاء نص الإحصائيات
    stats_text = f"""
📊 *إحصائيات الحملات التسويقية*

📈 *إحصائيات عامة:*
• إجمالي الحملات: {total_campaigns}
• الحملات النشطة: {active_campaigns}
• الحملات المكتملة: {completed_campaigns}

📨 *إحصائيات الإرسال:*
• إجمالي الرسائل المرسلة: {total_sent}
• الرسائل الناجحة: {total_success}
• نسبة النجاح: {success_rate:.1f}%

📋 *الحملات حسب النوع:*
"""
    
    for campaign_type, count in campaign_types.items():
        percentage = (count / total_campaigns) * 100
        stats_text += f"• {campaign_type}: {count} ({percentage:.1f}%)\n"
    
    await update.callback_query.edit_message_text(
        stats_text,
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("📋 عرض الحملات النشطة", callback_data="campaign_list_active")],
            [InlineKeyboardButton("📋 عرض الحملات السابقة", callback_data="campaign_list_past")],
            [InlineKeyboardButton("🏠 العودة", callback_data="campaign_back_main")]
        ]),
        parse_mode="Markdown"
    )

def get_marketing_campaign_handlers():
    """إرجاع معالجات الحملات التسويقية."""
    # معالج المحادثة لإنشاء حملة جديدة
    campaign_creation_handler = ConversationHandler(
        entry_points=[
            CallbackQueryHandler(start_campaign_creation, pattern=r"^campaign_create$")
        ],
        states={
            CAMPAIGN_NAME: [MessageHandler(filters.TEXT & ~filters.COMMAND, received_campaign_name)],
            CAMPAIGN_TYPE: [CallbackQueryHandler(received_campaign_type, pattern=r"^campaign_type_")],
            CAMPAIGN_TARGET: [CallbackQueryHandler(received_campaign_target, pattern=r"^campaign_target_")],
            CAMPAIGN_MESSAGE: [MessageHandler(filters.TEXT & ~filters.COMMAND, received_campaign_message)],
            CAMPAIGN_DISCOUNT: [MessageHandler(filters.TEXT & ~filters.COMMAND, received_campaign_discount)],
            CAMPAIGN_MIN_ORDER: [MessageHandler(filters.TEXT & ~filters.COMMAND, received_campaign_min_order)],
            CAMPAIGN_MAX_CUSTOMERS: [MessageHandler(filters.TEXT & ~filters.COMMAND, received_campaign_max_customers)],
            CAMPAIGN_IMAGE: [
                CallbackQueryHandler(handle_campaign_image_choice, pattern=r"^campaign_(add|no)_image$"),
                MessageHandler(filters.PHOTO, received_campaign_image)
            ],
            CAMPAIGN_CONFIRMATION: [
                CallbackQueryHandler(handle_campaign_confirmation, pattern=r"^campaign_(confirm_save|edit_message|back_main)$")
            ]
        },
        fallbacks=[
            CallbackQueryHandler(update_campaign_main_menu, pattern=r"^campaign_back_main$"),
            CommandHandler("cancel", lambda u, c: ConversationHandler.END)
        ],
        name="marketing_campaign_conversation",
        persistent=False,
        per_message=False,
        per_chat=True,
        allow_reentry=True
    )
    
    # قائمة المعالجات
    handlers = [
        CommandHandler("marketing", marketing_campaigns_command),
        campaign_creation_handler,
        CallbackQueryHandler(confirm_send_campaign, pattern=r"^campaign_confirm_send_"),
        CallbackQueryHandler(confirm_delete_campaign, pattern=r"^campaign_confirm_delete_"),
        CallbackQueryHandler(handle_campaign_callbacks, pattern=r"^campaign_")
    ]
    
    return handlers