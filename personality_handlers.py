#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
وحدة معالجات شخصية البوت المتغيرة
تسمح للمسؤولين بتعديل شخصية وطريقة تفاعل البوت مع المستخدمين
"""

import logging
import json
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    ContextTypes,
    CommandHandler,
    CallbackQueryHandler,
    ConversationHandler,
    filters,
    MessageHandler,
)
import database as db

from models import BotPersonality
from database import get_db_session, is_admin, get_bot_personality, update_bot_personality, create_bot_personality

# حالات المحادثة
SELECTING_MOOD, ADJUSTING_SLIDER, PREVIEW_PERSONALITY, SAVE_PERSONALITY = range(4)

# أنواع المزاج المختلفة للبوت
MOOD_TYPES = {
    "formal": "رسمي",
    "friendly": "ودود",
    "professional": "احترافي",
    "humorous": "مرح",
    "motivational": "تحفيزي",
}

# عوامل شخصية البوت
PERSONALITY_FACTORS = {
    "enthusiasm": {
        "name": "الحماس",
        "min_desc": "هادئ",
        "max_desc": "متحمس جداً",
        "emojis": ["😐", "🙂", "😊", "😃", "😄"]
    },
    "formality": {
        "name": "الرسمية",
        "min_desc": "غير رسمي",
        "max_desc": "رسمي جداً",
        "emojis": ["🤙", "👋", "👔", "🤵", "👨‍💼"]
    },
    "verbosity": {
        "name": "الإسهاب",
        "min_desc": "مختصر",
        "max_desc": "مفصّل",
        "emojis": ["📝", "📄", "📑", "📚", "📜"]
    },
    "emoji_usage": {
        "name": "استخدام الرموز التعبيرية",
        "min_desc": "بدون رموز",
        "max_desc": "الكثير من الرموز",
        "emojis": ["🚫", "☺️", "😊", "😄", "🎉"]
    },
    "response_speed": {
        "name": "سرعة الاستجابة",
        "min_desc": "متأني",
        "max_desc": "سريع جداً",
        "emojis": ["🐌", "🚶", "🏃", "🚀", "⚡"]
    }
}

# النصوص الافتراضية لأنماط الشخصية
DEFAULT_PERSONALITY_TEMPLATES = {
    "formal": {
        "enthusiasm": 3,
        "formality": 5,
        "verbosity": 4,
        "emoji_usage": 2,
        "response_speed": 3,
        "greeting": "مرحباً بكم في نظام تتبع الشحنات. كيف يمكنني مساعدتكم اليوم؟",
        "farewell": "شكراً لاستخدامكم خدماتنا. نتطلع لخدمتكم مرة أخرى."
    },
    "friendly": {
        "enthusiasm": 4,
        "formality": 2,
        "verbosity": 3,
        "emoji_usage": 4,
        "response_speed": 4,
        "greeting": "أهلاً وسهلاً! 😊 سعيد بوجودك هنا. كيف يمكنني مساعدتك اليوم؟",
        "farewell": "أتمنى لك يوماً رائعاً! 👋 لا تتردد في العودة متى احتجت للمساعدة!"
    },
    "professional": {
        "enthusiasm": 3,
        "formality": 4,
        "verbosity": 4,
        "emoji_usage": 1,
        "response_speed": 5,
        "greeting": "مرحباً بكم في النظام المتخصص لتتبع الشحنات. نحن جاهزون لتقديم الخدمة بأعلى مستويات الجودة.",
        "farewell": "نشكركم على ثقتكم بخدماتنا. فريقنا المتخصص جاهز دوماً لمساعدتكم."
    },
    "humorous": {
        "enthusiasm": 5,
        "formality": 1,
        "verbosity": 3,
        "emoji_usage": 5,
        "response_speed": 4,
        "greeting": "أهلاً بك! 😄 وصلت للتو إلى أكثر بوت شحنات مرحاً على الإطلاق! 🎉 ماذا تريد أن نفعل اليوم؟",
        "farewell": "وداعاً صديقي! 👋 لا تنسَ أن تحضر معك بعض الحلوى في المرة القادمة! 🍭"
    },
    "motivational": {
        "enthusiasm": 5,
        "formality": 3,
        "verbosity": 4,
        "emoji_usage": 3,
        "response_speed": 4,
        "greeting": "أهلاً بك! 🌟 يومك مليء بالإمكانيات والفرص! نحن هنا لنساعدك في تحقيق أهدافك!",
        "farewell": "تذكر أن كل شحنة تمثل فرصة جديدة! 💪 استمر في التقدم ونحن معك في كل خطوة!"
    }
}

async def get_current_personality():
    """الحصول على إعدادات الشخصية الحالية من قاعدة البيانات أو من الإعدادات الافتراضية"""
    # استخدام الوظيفة المعرفة في ملف database.py
    personality_data = get_bot_personality()
    
    # تحويل الشخصية إلى التنسيق المطلوب
    if isinstance(personality_data, dict):
        # استخدام الشخصية المسترجعة من قاعدة البيانات
        return {
            "mood_type": personality_data.get("mood_type", "friendly"),
            "settings": personality_data.get("settings", {}),
            "greeting": personality_data.get("greeting", "مرحباً! كيف يمكنني مساعدتك؟"),
            "farewell": personality_data.get("farewell", "شكراً لاستخدامك البوت!")
        }
    else:
        # في حالة وجود مشكلة، استخدام القيم الافتراضية
        default_mood = "friendly"
        default_settings = DEFAULT_PERSONALITY_TEMPLATES[default_mood]
        
        # إنشاء شخصية افتراضية وحفظها
        success, personality_id = create_bot_personality(
            mood_type=default_mood,
            settings=default_settings,
            greeting=default_settings["greeting"],
            farewell=default_settings["farewell"],
            created_by=1,  # المسؤول الأول
            is_active=True
        )
        
        return {
            "mood_type": default_mood,
            "settings": default_settings,
            "greeting": default_settings["greeting"],
            "farewell": default_settings["farewell"]
        }

def get_personality_message(mood_type, settings, preview=False):
    """إنشاء رسالة تعرض إعدادات الشخصية"""
    message = "🤖 *شخصية البوت*\n\n"
    
    if preview:
        message += "✨ *معاينة الشخصية* ✨\n\n"
    
    message += f"🎭 *المزاج الحالي:* {MOOD_TYPES.get(mood_type, 'غير معروف')}\n\n"
    
    # إضافة شرائح لكل عامل
    for factor, value in settings.items():
        if factor in PERSONALITY_FACTORS:
            factor_info = PERSONALITY_FACTORS[factor]
            if isinstance(value, (int, float)) and 1 <= value <= 5:
                emoji_index = min(int(value) - 1, len(factor_info["emojis"]) - 1)
                emoji = factor_info["emojis"][emoji_index]
                
                slider = "▫️" * (value - 1) + "🔘" + "▫️" * (5 - value)
                message += f"{emoji} *{factor_info['name']}:* {slider}\n"
                message += f"  {factor_info['min_desc']} {' ' * (10 - len(factor_info['min_desc']))} {factor_info['max_desc']}\n\n"
    
    if "greeting" in settings:
        message += f"👋 *رسالة الترحيب:*\n_{settings['greeting']}_\n\n"
        
    if "farewell" in settings:
        message += f"👋 *رسالة الوداع:*\n_{settings['farewell']}_\n\n"
    
    if preview:
        message += "\n⚠️ هذه معاينة فقط، التغييرات لم يتم حفظها بعد."
    
    return message

def get_mood_selection_keyboard():
    """إنشاء لوحة مفاتيح لاختيار نوع المزاج"""
    keyboard = []
    
    # إضافة زر لكل نوع مزاج
    for mood_key, mood_name in MOOD_TYPES.items():
        keyboard.append([InlineKeyboardButton(mood_name, callback_data=f"mood_{mood_key}")])
    
    # إضافة زر العودة
    keyboard.append([InlineKeyboardButton("🔙 العودة", callback_data="personality_back")])
    
    return InlineKeyboardMarkup(keyboard)

def get_factors_keyboard(current_settings, selected_factor=None):
    """إنشاء لوحة مفاتيح لاختيار أو تعديل عوامل الشخصية"""
    keyboard = []
    
    # إضافة زر لكل عامل
    for factor_key, factor_info in PERSONALITY_FACTORS.items():
        value = current_settings.get(factor_key, 3)
        emoji_index = min(int(value) - 1, len(factor_info["emojis"]) - 1)
        emoji = factor_info["emojis"][emoji_index]
        
        # إذا كان هذا هو العامل المحدد، أظهر شريط التمرير
        if selected_factor == factor_key:
            button_text = f"✏️ {factor_info['name']}: {value}/5"
        else:
            button_text = f"{emoji} {factor_info['name']}: {value}/5"
        
        keyboard.append([InlineKeyboardButton(button_text, callback_data=f"factor_{factor_key}")])
    
    # أزرار تعديل رسائل الترحيب والوداع
    keyboard.append([InlineKeyboardButton("✏️ تعديل رسالة الترحيب", callback_data="edit_greeting")])
    keyboard.append([InlineKeyboardButton("✏️ تعديل رسالة الوداع", callback_data="edit_farewell")])
    
    # أزرار إضافية
    actions_row = []
    actions_row.append(InlineKeyboardButton("👁 معاينة", callback_data="preview_personality"))
    actions_row.append(InlineKeyboardButton("💾 حفظ", callback_data="save_personality"))
    keyboard.append(actions_row)
    
    # زر العودة
    keyboard.append([InlineKeyboardButton("🔙 العودة للقائمة الرئيسية", callback_data="personality_back_main")])
    
    return InlineKeyboardMarkup(keyboard)

def get_slider_keyboard(factor_key, current_value):
    """إنشاء لوحة مفاتيح لشريط التمرير"""
    factor_info = PERSONALITY_FACTORS[factor_key]
    
    keyboard = []
    
    # شريط القيم
    values_row = []
    for i in range(1, 6):
        if i == current_value:
            # القيمة المحددة حالياً
            values_row.append(InlineKeyboardButton(f"[{i}]", callback_data=f"slider_{factor_key}_{i}"))
        else:
            values_row.append(InlineKeyboardButton(f"{i}", callback_data=f"slider_{factor_key}_{i}"))
    
    keyboard.append(values_row)
    
    # وصف القيم
    keyboard.append([
        InlineKeyboardButton(f"{factor_info['min_desc']} ⟵", callback_data="slider_desc_min"),
        InlineKeyboardButton(f"⟶ {factor_info['max_desc']}", callback_data="slider_desc_max")
    ])
    
    # زر العودة
    keyboard.append([InlineKeyboardButton("🔙 العودة", callback_data="slider_back")])
    
    return InlineKeyboardMarkup(keyboard)

async def personality_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """بدء عملية تغيير شخصية البوت"""
    user_id = update.effective_user.id
    
    # التحقق إذا كان المستخدم مسؤولاً
    if not db.is_admin(user_id):
        await update.message.reply_text("⛔️ هذا الأمر متاح للمسؤولين فقط.")
        return ConversationHandler.END
    
    # الحصول على الشخصية الحالية
    current_personality = await get_current_personality()
    
    # حفظ البيانات في سياق المحادثة
    context.user_data["personality_edit"] = {
        "mood_type": current_personality["mood_type"],
        "settings": current_personality["settings"].copy(),
        "greeting": current_personality.get("greeting", ""),
        "farewell": current_personality.get("farewell", "")
    }
    
    # عرض القائمة الرئيسية
    message = "🤖 *إعدادات شخصية البوت*\n\n"
    message += "يمكنك تعديل طريقة تفاعل البوت مع المستخدمين من خلال ضبط شخصية البوت.\n\n"
    message += "اختر أحد الإجراءات:"
    
    keyboard = [
        [InlineKeyboardButton("🎭 اختيار مزاج جاهز", callback_data="select_mood")],
        [InlineKeyboardButton("⚙️ تعديل الإعدادات", callback_data="edit_factors")],
        [InlineKeyboardButton("👁 عرض الشخصية الحالية", callback_data="view_current")],
        [InlineKeyboardButton("❌ إلغاء", callback_data="cancel_personality")]
    ]
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.message.reply_text(message, reply_markup=reply_markup, parse_mode="Markdown")
    return SELECTING_MOOD

async def personality_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """معالجة استجابات أزرار شخصية البوت"""
    query = update.callback_query
    await query.answer()
    
    user_id = update.effective_user.id
    
    # التحقق إذا كان المستخدم مسؤولاً
    if not db.is_admin(user_id):
        await query.edit_message_text("⛔️ هذا الأمر متاح للمسؤولين فقط.")
        return ConversationHandler.END
    
    # التأكد من وجود بيانات الشخصية في سياق المحادثة
    if "personality_edit" not in context.user_data:
        current_personality = await get_current_personality()
        context.user_data["personality_edit"] = {
            "mood_type": current_personality["mood_type"],
            "settings": current_personality["settings"].copy(),
            "greeting": current_personality.get("greeting", ""),
            "farewell": current_personality.get("farewell", "")
        }
    
    personality_data = context.user_data["personality_edit"]
    
    # معالجة مختلف الاستجابات
    if query.data == "select_mood":
        # عرض قائمة اختيار المزاج
        await query.edit_message_text(
            "🎭 *اختر المزاج الذي يناسب بوتك:*\n\n"
            "سيتم تطبيق إعدادات مسبقة لشخصية البوت وفقاً للمزاج المختار.",
            reply_markup=get_mood_selection_keyboard(),
            parse_mode="Markdown"
        )
        return SELECTING_MOOD
        
    elif query.data.startswith("mood_"):
        # تم اختيار مزاج معين
        mood_type = query.data.split("_")[1]
        
        if mood_type in DEFAULT_PERSONALITY_TEMPLATES:
            # تطبيق قالب المزاج المختار
            personality_data["mood_type"] = mood_type
            personality_data["settings"] = DEFAULT_PERSONALITY_TEMPLATES[mood_type].copy()
            personality_data["greeting"] = DEFAULT_PERSONALITY_TEMPLATES[mood_type]["greeting"]
            personality_data["farewell"] = DEFAULT_PERSONALITY_TEMPLATES[mood_type]["farewell"]
            
            # عرض الإعدادات المطبقة
            message = f"✅ تم اختيار المزاج: *{MOOD_TYPES[mood_type]}*\n\n"
            message += get_personality_message(mood_type, personality_data["settings"])
            
            await query.edit_message_text(
                message,
                reply_markup=get_factors_keyboard(personality_data["settings"]),
                parse_mode="Markdown"
            )
            return ADJUSTING_SLIDER
        
    elif query.data == "edit_factors":
        # تعديل عوامل الشخصية
        await query.edit_message_text(
            "⚙️ *تعديل إعدادات الشخصية*\n\n"
            "اختر العامل الذي تريد تعديله:",
            reply_markup=get_factors_keyboard(personality_data["settings"]),
            parse_mode="Markdown"
        )
        return ADJUSTING_SLIDER
        
    elif query.data.startswith("factor_"):
        # تم اختيار عامل للتعديل
        factor_key = query.data.split("_")[1]
        current_value = personality_data["settings"].get(factor_key, 3)
        
        factor_info = PERSONALITY_FACTORS.get(factor_key)
        if factor_info:
            await query.edit_message_text(
                f"🎚 *تعديل {factor_info['name']}*\n\n"
                f"حدد مستوى {factor_info['name']} المناسب:\n"
                f"الحد الأدنى: *{factor_info['min_desc']}*\n"
                f"الحد الأقصى: *{factor_info['max_desc']}*\n\n"
                f"القيمة الحالية: *{current_value}/5*",
                reply_markup=get_slider_keyboard(factor_key, current_value),
                parse_mode="Markdown"
            )
            return ADJUSTING_SLIDER
            
    elif query.data.startswith("slider_"):
        # تعديل قيمة العامل
        parts = query.data.split("_")
        if len(parts) >= 3 and parts[1] in PERSONALITY_FACTORS:
            factor_key = parts[1]
            new_value = int(parts[2])
            
            # تحديث القيمة
            personality_data["settings"][factor_key] = new_value
            
            # العودة إلى قائمة العوامل
            await query.edit_message_text(
                "⚙️ *تعديل إعدادات الشخصية*\n\n"
                f"✅ تم تحديث {PERSONALITY_FACTORS[factor_key]['name']} إلى {new_value}/5\n\n"
                "اختر عامل آخر للتعديل:",
                reply_markup=get_factors_keyboard(personality_data["settings"]),
                parse_mode="Markdown"
            )
            return ADJUSTING_SLIDER
            
    elif query.data == "slider_back":
        # العودة من شريط التمرير إلى قائمة العوامل
        await query.edit_message_text(
            "⚙️ *تعديل إعدادات الشخصية*\n\n"
            "اختر العامل الذي تريد تعديله:",
            reply_markup=get_factors_keyboard(personality_data["settings"]),
            parse_mode="Markdown"
        )
        return ADJUSTING_SLIDER
        
    elif query.data == "edit_greeting":
        # تعديل رسالة الترحيب
        await query.edit_message_text(
            "✏️ *تعديل رسالة الترحيب*\n\n"
            "أرسل الرسالة الجديدة التي سيستخدمها البوت للترحيب بالمستخدمين.\n\n"
            "الرسالة الحالية:\n"
            f"_{personality_data['greeting']}_",
            parse_mode="Markdown"
        )
        context.user_data["editing_message_type"] = "greeting"
        return ADJUSTING_SLIDER
        
    elif query.data == "edit_farewell":
        # تعديل رسالة الوداع
        await query.edit_message_text(
            "✏️ *تعديل رسالة الوداع*\n\n"
            "أرسل الرسالة الجديدة التي سيستخدمها البوت عند إنهاء المحادثة.\n\n"
            "الرسالة الحالية:\n"
            f"_{personality_data['farewell']}_",
            parse_mode="Markdown"
        )
        context.user_data["editing_message_type"] = "farewell"
        return ADJUSTING_SLIDER
        
    elif query.data == "preview_personality":
        # معاينة الشخصية
        mood_type = personality_data["mood_type"]
        settings = personality_data["settings"]
        
        # عرض معاينة الشخصية
        message = get_personality_message(mood_type, settings, preview=True)
        
        # إضافة أمثلة على التفاعل
        message += "\n\n*أمثلة على التفاعل:*\n\n"
        
        # مثال ترحيب
        message += f"👤 *مستخدم جديد يدخل للبوت*\n🤖 _{personality_data['greeting']}_\n\n"
        
        # مثال استجابة لطلب
        enthusiasm_level = settings.get("enthusiasm", 3)
        formality_level = settings.get("formality", 3)
        emoji_usage = settings.get("emoji_usage", 3)
        
        response_example = ""
        if formality_level >= 4:
            response_example = "تم العثور على الشحنة المطلوبة. الشحنة جاهزة للاستلام."
        elif formality_level <= 2:
            response_example = "وجدت شحنتك! يمكنك استلامها الآن"
        else:
            response_example = "تم إيجاد الشحنة. يمكنك استلامها قريباً."
            
        if enthusiasm_level >= 4:
            response_example = "رائع! " + response_example + " نحن متحمسون لخدمتك!"
        
        if emoji_usage >= 3:
            emojis = ["📦", "✅", "🚚", "🎁"]
            import random
            for _ in range(min(emoji_usage, 3)):
                response_example += f" {random.choice(emojis)}"
                
        message += f"👤 *طلب معلومات عن شحنة*\n🤖 _{response_example}_\n\n"
        
        # مثال وداع
        message += f"👤 *مستخدم ينهي المحادثة*\n🤖 _{personality_data['farewell']}_\n"
        
        back_button = InlineKeyboardMarkup([[InlineKeyboardButton("🔙 العودة", callback_data="preview_back")]])
        
        await query.edit_message_text(message, reply_markup=back_button, parse_mode="Markdown")
        return PREVIEW_PERSONALITY
        
    elif query.data == "preview_back":
        # العودة من المعاينة
        await query.edit_message_text(
            "⚙️ *تعديل إعدادات الشخصية*\n\n"
            "اختر العامل الذي تريد تعديله:",
            reply_markup=get_factors_keyboard(personality_data["settings"]),
            parse_mode="Markdown"
        )
        return ADJUSTING_SLIDER
        
    elif query.data == "save_personality":
        # حفظ الشخصية
        mood_type = personality_data["mood_type"]
        settings = personality_data["settings"]
        greeting = personality_data["greeting"]
        farewell = personality_data["farewell"]
        
        # حفظ في قاعدة البيانات باستخدام وظيفة create_bot_personality
        success, personality_id = create_bot_personality(
            mood_type=mood_type,
            settings=settings,
            greeting=greeting,
            farewell=farewell,
            created_by=user_id,
            is_active=True
        )
        
        if success:
            await query.edit_message_text(
                "✅ *تم حفظ شخصية البوت بنجاح!*\n\n"
                "تم تطبيق الإعدادات الجديدة على البوت. ستظهر التغييرات في جميع تفاعلات البوت الجديدة.",
                parse_mode="Markdown"
            )
            
            # مسح بيانات تعديل الشخصية من سياق المحادثة
            if "personality_edit" in context.user_data:
                del context.user_data["personality_edit"]
                
            return ConversationHandler.END
        else:
            logging.error(f"Error saving personality: {personality_id}")  # personality_id يحتوي على رسالة الخطأ
            
            await query.edit_message_text(
                "❌ *حدث خطأ أثناء حفظ الشخصية*\n\n"
                "يرجى المحاولة مرة أخرى لاحقاً أو التواصل مع مطور البوت.",
                parse_mode="Markdown"
            )
            return ConversationHandler.END
            
    elif query.data == "preview_personality":
        # معاينة الشخصية المعدلة قبل حفظها
        mood_type = personality_data["mood_type"]
        settings = personality_data["settings"]
        
        message = get_personality_message(mood_type, settings, preview=True)
        back_button = InlineKeyboardMarkup([[InlineKeyboardButton("🔙 العودة", callback_data="preview_back")]])
        
        await query.edit_message_text(message, reply_markup=back_button, parse_mode="Markdown")
        return PREVIEW_PERSONALITY
        
    elif query.data == "preview_back":
        # العودة من المعاينة إلى تحرير الإعدادات
        await query.edit_message_text(
            "⚙️ *تعديل إعدادات الشخصية*\n\n"
            "اختر العامل الذي تريد تعديله:",
            reply_markup=get_factors_keyboard(personality_data["settings"]),
            parse_mode="Markdown"
        )
        return ADJUSTING_SLIDER
        
    elif query.data == "view_current":
        # عرض الشخصية الحالية
        current_personality = await get_current_personality()
        
        message = "🤖 *الشخصية الحالية للبوت*\n\n"
        message += get_personality_message(
            current_personality["mood_type"], 
            current_personality["settings"]
        )
        
        back_button = InlineKeyboardMarkup([[InlineKeyboardButton("🔙 العودة", callback_data="view_back")]])
        
        await query.edit_message_text(message, reply_markup=back_button, parse_mode="Markdown")
        return SELECTING_MOOD
        
    elif query.data == "view_back" or query.data == "personality_back":
        # العودة من عرض الشخصية الحالية
        message = "🤖 *إعدادات شخصية البوت*\n\n"
        message += "يمكنك تعديل طريقة تفاعل البوت مع المستخدمين من خلال ضبط شخصية البوت.\n\n"
        message += "اختر أحد الإجراءات:"
        
        keyboard = [
            [InlineKeyboardButton("🎭 اختيار مزاج جاهز", callback_data="select_mood")],
            [InlineKeyboardButton("⚙️ تعديل الإعدادات", callback_data="edit_factors")],
            [InlineKeyboardButton("👁 عرض الشخصية الحالية", callback_data="view_current")],
            [InlineKeyboardButton("❌ إلغاء", callback_data="cancel_personality")]
        ]
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await query.edit_message_text(message, reply_markup=reply_markup, parse_mode="Markdown")
        return SELECTING_MOOD
        
    elif query.data == "personality_back_main":
        # العودة إلى القائمة الرئيسية
        message = "🤖 *إعدادات شخصية البوت*\n\n"
        message += "يمكنك تعديل طريقة تفاعل البوت مع المستخدمين من خلال ضبط شخصية البوت.\n\n"
        message += "اختر أحد الإجراءات:"
        
        keyboard = [
            [InlineKeyboardButton("🎭 اختيار مزاج جاهز", callback_data="select_mood")],
            [InlineKeyboardButton("⚙️ تعديل الإعدادات", callback_data="edit_factors")],
            [InlineKeyboardButton("👁 عرض الشخصية الحالية", callback_data="view_current")],
            [InlineKeyboardButton("❌ إلغاء", callback_data="cancel_personality")]
        ]
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await query.edit_message_text(message, reply_markup=reply_markup, parse_mode="Markdown")
        return SELECTING_MOOD
        
    elif query.data == "cancel_personality":
        # إلغاء عملية تعديل الشخصية
        if "personality_edit" in context.user_data:
            del context.user_data["personality_edit"]
            
        await query.edit_message_text("❌ تم إلغاء عملية تعديل شخصية البوت.")
        return ConversationHandler.END
    
    # إذا وصلنا إلى هنا، فهذا يعني أن callback_data غير معروف
    return SELECTING_MOOD

async def process_message_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """معالجة النص المستلم لتعديل رسائل الترحيب أو الوداع"""
    if "editing_message_type" not in context.user_data or "personality_edit" not in context.user_data:
        await update.message.reply_text("⚠️ حدث خطأ. يرجى بدء عملية تعديل الشخصية من جديد باستخدام /personality")
        return ConversationHandler.END
    
    message_type = context.user_data["editing_message_type"]
    new_text = update.message.text
    
    # تحديث النص المناسب
    if message_type == "greeting":
        context.user_data["personality_edit"]["greeting"] = new_text
        message = "✅ *تم تحديث رسالة الترحيب بنجاح!*\n\n"
    elif message_type == "farewell":
        context.user_data["personality_edit"]["farewell"] = new_text
        message = "✅ *تم تحديث رسالة الوداع بنجاح!*\n\n"
    else:
        message = "⚠️ *حدث خطأ أثناء تحديث الرسالة*\n\n"
    
    message += "اختر الإجراء التالي:"
    
    # العودة إلى قائمة تعديل العوامل
    personality_data = context.user_data["personality_edit"]
    
    await update.message.reply_text(
        message,
        reply_markup=get_factors_keyboard(personality_data["settings"]),
        parse_mode="Markdown"
    )
    
    # حذف معلومات التعديل الحالية
    if "editing_message_type" in context.user_data:
        del context.user_data["editing_message_type"]
    
    return ADJUSTING_SLIDER

async def cancel_personality(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """إلغاء عملية تعديل الشخصية"""
    if "personality_edit" in context.user_data:
        del context.user_data["personality_edit"]
    
    await update.message.reply_text("❌ تم إلغاء عملية تعديل شخصية البوت.")
    return ConversationHandler.END

def get_personality_handlers():
    """الحصول على معالجات شخصية البوت"""
    personality_conv_handler = ConversationHandler(
        entry_points=[CommandHandler("personality", personality_command)],
        states={
            SELECTING_MOOD: [
                CallbackQueryHandler(personality_callback, pattern="^(select_mood|mood_|view_current|view_back|personality_back|cancel_personality)"),
            ],
            ADJUSTING_SLIDER: [
                CallbackQueryHandler(personality_callback, pattern="^(edit_factors|factor_|slider_|edit_greeting|edit_farewell|preview_personality|save_personality|personality_back_main)"),
                MessageHandler(filters.TEXT & ~filters.COMMAND, process_message_text),
            ],
            PREVIEW_PERSONALITY: [
                CallbackQueryHandler(personality_callback, pattern="^preview_back$"),
            ],
            SAVE_PERSONALITY: [
                CallbackQueryHandler(personality_callback, pattern="^(save_personality|cancel_personality)$"),
            ],
        },
        fallbacks=[CommandHandler("cancel", cancel_personality)],
    )
    
    return [personality_conv_handler]

# وظائف مساعدة للوصول إلى شخصية البوت من خارج هذه الوحدة

async def get_bot_personality_settings():
    """الحصول على إعدادات شخصية البوت الحالية للاستخدام في أجزاء أخرى من البوت"""
    return await get_current_personality()

def apply_personality_to_message(message, personality_settings=None):
    """تطبيق شخصية البوت على رسالة نصية
    
    Args:
        message (str): الرسالة الأصلية
        personality_settings (dict, optional): إعدادات الشخصية. سيتم الحصول عليها تلقائيًا إذا لم يتم تحديدها.
        
    Returns:
        str: الرسالة بعد تطبيق شخصية البوت
    """
    if not personality_settings:
        # استخدام القيم الافتراضية إذا لم يتم تحديد إعدادات الشخصية
        personality_settings = {
            "settings": {
                "enthusiasm": 3,
                "formality": 3,
                "verbosity": 3,
                "emoji_usage": 3,
                "response_speed": 3
            }
        }
    
    settings = personality_settings.get("settings", {})
    
    # تطبيق مستوى الرسمية
    formality_level = settings.get("formality", 3)
    if formality_level >= 4:
        # أكثر رسمية
        message = message.replace("أنت", "سيادتك").replace("لك", "لسيادتك")
    elif formality_level <= 2:
        # أقل رسمية
        message = message.replace("يمكنك", "يمكنك ببساطة").replace("يرجى", "")
    
    # تطبيق استخدام الرموز التعبيرية
    emoji_usage = settings.get("emoji_usage", 3)
    if emoji_usage > 0:
        common_emojis = ["✅", "👍", "🌟", "💼", "📦", "📊", "🚚", "🔍", "📱", "⏰", "✨", "🎯"]
        import random
        
        # تحديد عدد الرموز التعبيرية المراد إضافتها
        emoji_count = max(1, min(emoji_usage, 4))
        
        # إضافة رموز تعبيرية في نهاية الرسالة
        for _ in range(emoji_count - 1):
            if random.random() < 0.7:  # احتمال 70% لإضافة رمز تعبيري
                message += f" {random.choice(common_emojis)}"
    
    # تطبيق مستوى الحماس
    enthusiasm_level = settings.get("enthusiasm", 3)
    if enthusiasm_level >= 4:
        # أكثر حماساً
        message = message.replace("تم", "تم بنجاح").replace("جاهزة", "جاهزة تماماً")
        if "!" not in message:
            message = message.rstrip(".") + "!"
    
    # تطبيق مستوى الإسهاب
    verbosity_level = settings.get("verbosity", 3)
    if verbosity_level <= 2:
        # أكثر اختصاراً
        sentences = message.split(".")
        if len(sentences) > 1:
            message = ".".join(sentences[:2]) + ("." if not message.endswith(".") else "")
    elif verbosity_level >= 4:
        # أكثر إسهاباً
        if "شكراً" not in message and "شكرا" not in message:
            message += " شكراً لتعاملك معنا."
    
    return message

def format_greeting(user_name, personality_settings=None):
    """تنسيق رسالة الترحيب وفقاً لشخصية البوت"""
    if not personality_settings:
        # استخدام القيم الافتراضية إذا لم يتم تحديد إعدادات الشخصية
        greeting = "مرحباً {user_name}! كيف يمكنني مساعدتك اليوم؟"
    else:
        greeting = personality_settings.get("greeting", "مرحباً {user_name}! كيف يمكنني مساعدتك اليوم؟")
    
    # استبدال متغير اسم المستخدم
    greeting = greeting.replace("{user_name}", user_name)
    
    return greeting