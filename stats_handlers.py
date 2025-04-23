"""
وحدة لإدارة وعرض إحصائيات البوت
"""
import logging
from typing import Dict, List, Any
from telegram import Update, InlineKeyboardMarkup, InlineKeyboardButton
from telegram.ext import ContextTypes, CommandHandler, CallbackQueryHandler, ConversationHandler

import db_manager
import strings

# حالات المحادثة
(SELECTING_STATS_PERIOD, SELECTING_STATS_TYPE) = range(2)

async def stats_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    عرض قائمة خيارات الإحصائيات للمشرفين
    """
    if not db_manager.is_admin(update.effective_user.id):
        await update.message.reply_text("عذرًا، أنت لست مسؤولاً مصرحًا له. هذا الأمر للمسؤولين فقط.")
        return

    keyboard = [
        [
            InlineKeyboardButton("📊 إحصائيات اليوم", callback_data="stats_day"),
            InlineKeyboardButton("📈 إحصائيات الأسبوع", callback_data="stats_week")
        ],
        [
            InlineKeyboardButton("📉 إحصائيات الشهر", callback_data="stats_month"),
            InlineKeyboardButton("📋 إحصائيات إجمالية", callback_data="stats_total")
        ],
        [
            InlineKeyboardButton("📱 معدلات نجاح الإرسال", callback_data="stats_success"),
            InlineKeyboardButton("⏰ أوقات الذروة", callback_data="stats_peak")
        ],
        [
            InlineKeyboardButton("📑 تقرير شامل", callback_data="stats_report"),
            InlineKeyboardButton("❌ إلغاء", callback_data="stats_cancel")
        ]
    ]

    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text(
        "📊 *إحصائيات البوت*\n\n"
        "اختر نوع الإحصائيات التي تريد عرضها:",
        reply_markup=reply_markup,
        parse_mode='Markdown'
    )
    return SELECTING_STATS_PERIOD


async def handle_stats_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    معالجة استعلامات زر الإحصائيات
    """
    try:
        query = update.callback_query
        await query.answer()
        data = query.data

        if data == "stats_cancel":
            await query.edit_message_text("تم إلغاء عرض الإحصائيات.")
            return ConversationHandler.END
            
        # التعامل مع زر العودة
        if data == "stats_back":
            keyboard = [
                [
                    InlineKeyboardButton("📊 إحصائيات اليوم", callback_data="stats_day"),
                    InlineKeyboardButton("📈 إحصائيات الأسبوع", callback_data="stats_week")
                ],
                [
                    InlineKeyboardButton("📉 إحصائيات الشهر", callback_data="stats_month"),
                    InlineKeyboardButton("📋 إحصائيات إجمالية", callback_data="stats_total")
                ],
                [
                    InlineKeyboardButton("📱 معدلات نجاح الإرسال", callback_data="stats_success"),
                    InlineKeyboardButton("⏰ أوقات الذروة", callback_data="stats_peak")
                ],
                [
                    InlineKeyboardButton("📑 تقرير شامل", callback_data="stats_report"),
                    InlineKeyboardButton("❌ إلغاء", callback_data="stats_cancel")
                ]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            await query.edit_message_text(
                "📊 *إحصائيات البوت*\n\n"
                "اختر نوع الإحصائيات التي تريد عرضها:",
                reply_markup=reply_markup,
                parse_mode='Markdown'
            )
            return SELECTING_STATS_PERIOD

        # جلب البيانات المناسبة بناءً على الخيار المحدد
        stats_text = ""

        try:
            if data == "stats_day":
                stats_text = await get_daily_stats_text()

            elif data == "stats_week":
                stats_text = await get_weekly_stats_text()

            elif data == "stats_month":
                stats_text = await get_monthly_stats_text()

            elif data == "stats_total":
                stats_text = await get_total_stats_text()

            elif data == "stats_success":
                stats_text = await get_success_rates_text()

            elif data == "stats_peak":
                stats_text = await get_peak_times_text()

            elif data == "stats_report":
                stats_text = await get_comprehensive_report_text()
            
            # إضافة زر العودة
            keyboard = [[InlineKeyboardButton("🔙 العودة للإحصائيات", callback_data="stats_back"),
                        InlineKeyboardButton("❌ إغلاق", callback_data="stats_cancel")]]
            
            reply_markup = InlineKeyboardMarkup(keyboard)
            await query.edit_message_text(stats_text, reply_markup=reply_markup, parse_mode='Markdown')
            
            return SELECTING_STATS_TYPE
            
        except Exception as e:
            logging.error(f"Error showing statistics: {e}")
            # يمكننا محاولة إرسال رسالة جديدة بدلاً من تحرير الرسالة الحالية إذا فشلت
            try:
                await query.edit_message_text(f"حدث خطأ أثناء جلب الإحصائيات. الرجاء المحاولة مرة أخرى.")
            except:
                await update.effective_chat.send_message("حدث خطأ أثناء عرض الإحصائيات. الرجاء المحاولة مرة أخرى.")
            return ConversationHandler.END
            
    except Exception as e:
        logging.error(f"Error in handle_stats_callback: {e}")
        try:
            await update.effective_chat.send_message("حدث خطأ أثناء معالجة الإحصائيات. الرجاء المحاولة مرة أخرى.")
        except:
            pass
        return ConversationHandler.END


async def handle_stats_type_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    معالجة استعلامات الأزرار في شاشة تفاصيل الإحصائيات
    """
    query = update.callback_query
    await query.answer()
    data = query.data

    if data == "stats_cancel":
        await query.edit_message_text("تم إغلاق عرض الإحصائيات.")
        return ConversationHandler.END

    if data == "stats_back":
        # العودة إلى القائمة الرئيسية
        keyboard = [
            [
                InlineKeyboardButton("📊 إحصائيات اليوم", callback_data="stats_day"),
                InlineKeyboardButton("📈 إحصائيات الأسبوع", callback_data="stats_week")
            ],
            [
                InlineKeyboardButton("📉 إحصائيات الشهر", callback_data="stats_month"),
                InlineKeyboardButton("📋 إحصائيات إجمالية", callback_data="stats_total")
            ],
            [
                InlineKeyboardButton("📱 معدلات نجاح الإرسال", callback_data="stats_success"),
                InlineKeyboardButton("⏰ أوقات الذروة", callback_data="stats_peak")
            ],
            [
                InlineKeyboardButton("📑 تقرير شامل", callback_data="stats_report"),
                InlineKeyboardButton("❌ إلغاء", callback_data="stats_cancel")
            ]
        ]

        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.edit_message_text(
            "📊 *إحصائيات البوت*\n\n"
            "اختر نوع الإحصائيات التي تريد عرضها:",
            reply_markup=reply_markup,
            parse_mode='Markdown'
        )
        return SELECTING_STATS_PERIOD

    return SELECTING_STATS_TYPE


async def get_daily_stats_text() -> str:
    """
    جلب نص إحصائيات اليوم
    """
    try:
        logging.info("جلب إحصائيات اليوم...")
        daily_stats = db_manager.get_daily_statistics(1)
        logging.info(f"تم استلام {len(daily_stats)} من الإحصائيات اليومية: {daily_stats}")
        
        if not daily_stats or len(daily_stats) == 0:
            logging.warning("لم يتم العثور على إحصائيات لليوم الحالي")
            return "📊 *إحصائيات اليوم*\n\nلا توجد إحصائيات متاحة لليوم الحالي."
        
        stats = daily_stats[0]
        logging.info(f"إحصائيات اليوم: {stats}")
        
        # تأكد من أن القيم موجودة، وإذا كانت غير موجودة، استخدم 0
        notifications_created = stats.get('notifications_created', 0) or 0
        notifications_reminded = stats.get('notifications_reminded', 0) or 0
        messages_sent = stats.get('messages_sent', 0) or 0
        images_processed = stats.get('images_processed', 0) or 0
        ocr_success = stats.get('ocr_success', 0) or 0
        ocr_failure = stats.get('ocr_failure', 0) or 0
        
        # حساب معدل OCR بشكل آمن
        ocr_rate = 0
        if images_processed > 0:
            ocr_rate = (ocr_success / images_processed) * 100
        
        return (
            "📊 *إحصائيات اليوم*\n\n"
            f"📅 التاريخ: {stats.get('date')}\n"
            f"📨 الإشعارات المنشأة: {notifications_created}\n"
            f"⏰ التذكيرات المرسلة: {notifications_reminded}\n"
            f"💬 الرسائل المرسلة: {messages_sent}\n"
            f"🖼 الصور المعالجة: {images_processed}\n"
            f"✅ تحليل OCR ناجح: {ocr_success}\n"
            f"❌ تحليل OCR فاشل: {ocr_failure}\n\n"
            f"معدل نجاح OCR: {ocr_rate:.1f}%"
        )
    except Exception as e:
        logging.error(f"خطأ أثناء جلب إحصائيات اليوم: {e}")
        return "📊 *إحصائيات اليوم*\n\nحدث خطأ أثناء جلب الإحصائيات: {e}"


async def get_weekly_stats_text() -> str:
    """
    جلب نص إحصائيات الأسبوع
    """
    try:
        logging.info("جلب إحصائيات الأسبوع...")
        weekly_stats = db_manager.get_weekly_statistics()
        logging.info(f"تم استلام إحصائيات الأسبوع: {weekly_stats}")
        
        # تأكد من أن القيم موجودة، وإذا كانت غير موجودة، استخدم 0
        notifications_created = weekly_stats.get('notifications_created', 0) or 0 
        notifications_reminded = weekly_stats.get('notifications_reminded', 0) or 0
        messages_sent = weekly_stats.get('messages_sent', 0) or 0
        images_processed = weekly_stats.get('images_processed', 0) or 0
        ocr_success = weekly_stats.get('ocr_success', 0) or 0
        ocr_failure = weekly_stats.get('ocr_failure', 0) or 0
        
        # حساب متوسط الإشعارات اليومية بأمان
        avg_daily = notifications_created / 7 if notifications_created else 0
        
        # حساب معدل OCR بشكل آمن
        ocr_rate = 0
        if images_processed > 0:
            ocr_rate = (ocr_success / images_processed) * 100
            
        return (
            "📈 *إحصائيات الأسبوع*\n\n"
            f"📨 الإشعارات المنشأة: {notifications_created}\n"
            f"📊 متوسط الإشعارات اليومية: {avg_daily:.1f}\n"
            f"⏰ التذكيرات المرسلة: {notifications_reminded}\n"
            f"💬 الرسائل المرسلة: {messages_sent}\n"
            f"🖼 الصور المعالجة: {images_processed}\n"
            f"✅ تحليل OCR ناجح: {ocr_success}\n"
            f"❌ تحليل OCR فاشل: {ocr_failure}\n\n"
            f"معدل نجاح OCR: {ocr_rate:.1f}%"
        )
    except Exception as e:
        logging.error(f"خطأ أثناء جلب إحصائيات الأسبوع: {e}")
        return "📈 *إحصائيات الأسبوع*\n\nحدث خطأ أثناء جلب الإحصائيات: {e}"


async def get_monthly_stats_text() -> str:
    """
    جلب نص إحصائيات الشهر
    """
    try:
        logging.info("جلب إحصائيات الشهر...")
        monthly_stats = db_manager.get_monthly_statistics()
        logging.info(f"تم استلام إحصائيات الشهر: {monthly_stats}")
        
        # أسماء الأشهر بالعربية
        month_names = [
            "يناير", "فبراير", "مارس", "إبريل", "مايو", "يونيو",
            "يوليو", "أغسطس", "سبتمبر", "أكتوبر", "نوفمبر", "ديسمبر"
        ]
        
        month = int(monthly_stats.get('month', 1))
        # التأكد من أن الشهر ضمن النطاق
        if month < 1 or month > 12:
            month = 1
        month_name = month_names[month - 1]
        year = monthly_stats.get('year', 2025)
        
        # تأكد من أن القيم موجودة، وإذا كانت غير موجودة، استخدم 0
        notifications_created = monthly_stats.get('notifications_created', 0) or 0 
        notifications_reminded = monthly_stats.get('notifications_reminded', 0) or 0
        messages_sent = monthly_stats.get('messages_sent', 0) or 0
        images_processed = monthly_stats.get('images_processed', 0) or 0
        ocr_success = monthly_stats.get('ocr_success', 0) or 0
        ocr_failure = monthly_stats.get('ocr_failure', 0) or 0
        
        # حساب معدل OCR بشكل آمن
        ocr_rate = 0
        if images_processed > 0:
            ocr_rate = (ocr_success / images_processed) * 100
            
        return (
            f"📉 *إحصائيات شهر {month_name} {year}*\n\n"
            f"📨 الإشعارات المنشأة: {notifications_created}\n"
            f"⏰ التذكيرات المرسلة: {notifications_reminded}\n"
            f"💬 الرسائل المرسلة: {messages_sent}\n"
            f"🖼 الصور المعالجة: {images_processed}\n"
            f"✅ تحليل OCR ناجح: {ocr_success}\n"
            f"❌ تحليل OCR فاشل: {ocr_failure}\n\n"
            f"معدل نجاح OCR: {ocr_rate:.1f}%"
        )
    except Exception as e:
        logging.error(f"خطأ أثناء جلب إحصائيات الشهر: {e}")
        return f"📉 *إحصائيات الشهر*\n\nحدث خطأ أثناء جلب الإحصائيات: {e}"


async def get_total_stats_text() -> str:
    """
    جلب نص الإحصائيات الإجمالية
    """
    try:
        logging.info("جلب الإحصائيات الإجمالية...")
        total_stats = db_manager.get_total_statistics()
        logging.info(f"تم استلام الإحصائيات الإجمالية: {total_stats}")
        
        # حساب عدد الإشعارات النشطة (غير المرسل لها تذكير بعد)
        all_notifications = db_manager.get_all_notifications()
        active_notifications = len([n for n in all_notifications if not n.get('reminder_sent', False) and n.get('reminder_hours', 0) > 0])
        
        # تأكد من أن القيم موجودة، وإذا كانت غير موجودة، استخدم 0
        notifications_created = total_stats.get('notifications_created', 0) or 0 
        notifications_reminded = total_stats.get('notifications_reminded', 0) or 0
        messages_sent = total_stats.get('messages_sent', 0) or 0
        images_processed = total_stats.get('images_processed', 0) or 0
        ocr_success = total_stats.get('ocr_success', 0) or 0
        ocr_failure = total_stats.get('ocr_failure', 0) or 0
        
        # حساب معدل OCR بشكل آمن
        ocr_rate = 0
        if images_processed > 0:
            ocr_rate = (ocr_success / images_processed) * 100
            
        return (
            "📋 *الإحصائيات الإجمالية*\n\n"
            f"📨 إجمالي الإشعارات: {notifications_created}\n"
            f"📬 الإشعارات النشطة: {active_notifications}\n"
            f"⏰ التذكيرات المرسلة: {notifications_reminded}\n"
            f"💬 الرسائل المرسلة: {messages_sent}\n"
            f"🖼 الصور المعالجة: {images_processed}\n"
            f"✅ تحليل OCR ناجح: {ocr_success}\n"
            f"❌ تحليل OCR فاشل: {ocr_failure}\n\n"
            f"معدل نجاح OCR: {ocr_rate:.1f}%"
        )
    except Exception as e:
        logging.error(f"خطأ أثناء جلب الإحصائيات الإجمالية: {e}")
        return "📋 *الإحصائيات الإجمالية*\n\nحدث خطأ أثناء جلب الإحصائيات: {e}"


async def get_success_rates_text() -> str:
    """
    جلب نص معدلات نجاح الإرسال
    """
    try:
        logging.info("جلب معدلات نجاح الإرسال...")
        success_rates = db_manager.get_success_rates()
        logging.info(f"تم استلام معدلات نجاح الإرسال: {success_rates}")
        
        daily = success_rates.get('daily', {})
        weekly = success_rates.get('weekly', {})
        monthly = success_rates.get('monthly', {})
        
        # تأكد من أن القيم موجودة وآمنة
        daily_message_rate = daily.get('message_success_rate', 0) or 0
        daily_reminder_rate = daily.get('reminder_success_rate', 0) or 0
        weekly_message_rate = weekly.get('message_success_rate', 0) or 0
        weekly_reminder_rate = weekly.get('reminder_success_rate', 0) or 0
        monthly_message_rate = monthly.get('message_success_rate', 0) or 0
        monthly_reminder_rate = monthly.get('reminder_success_rate', 0) or 0
        
        return (
            "📱 *معدلات نجاح الإرسال*\n\n"
            "*اليومي:*\n"
            f"💬 معدل نجاح إرسال الرسائل: {daily_message_rate}%\n"
            f"⏰ معدل نجاح إرسال التذكيرات: {daily_reminder_rate}%\n\n"
            
            "*الأسبوعي:*\n"
            f"💬 معدل نجاح إرسال الرسائل: {weekly_message_rate}%\n"
            f"⏰ معدل نجاح إرسال التذكيرات: {weekly_reminder_rate}%\n\n"
            
            "*الشهري:*\n"
            f"💬 معدل نجاح إرسال الرسائل: {monthly_message_rate}%\n"
            f"⏰ معدل نجاح إرسال التذكيرات: {monthly_reminder_rate}%"
        )
    except Exception as e:
        logging.error(f"خطأ أثناء جلب معدلات نجاح الإرسال: {e}")
        return "📱 *معدلات نجاح الإرسال*\n\nحدث خطأ أثناء جلب الإحصائيات: {e}"


async def get_peak_times_text() -> str:
    """
    جلب نص أوقات الذروة
    """
    peak_times = db_manager.get_peak_usage_times()
    
    peak_hour = peak_times.get('peak_hour', 'غير متوفر')
    peak_day = peak_times.get('peak_day', 'غير متوفر')
    
    hourly_distribution = peak_times.get('hourly_distribution', {})
    daily_distribution = peak_times.get('daily_distribution', {})
    
    # تنسيق بيانات التوزيع الساعي
    hour_stats = ""
    sorted_hours = sorted(hourly_distribution.items(), key=lambda x: int(x[0].split(':')[0]))
    top_hours = sorted(hourly_distribution.items(), key=lambda x: x[1], reverse=True)[:3]
    
    top_hours_text = "\n".join([f"• {hour}: {count} إشعار" for hour, count in top_hours if count > 0])
    
    # تنسيق بيانات التوزيع اليومي
    day_stats = ""
    for day, count in daily_distribution.items():
        if count > 0:
            day_stats += f"• {day}: {count} إشعار\n"
    
    return (
        "⏰ *أوقات الذروة في استخدام البوت*\n\n"
        f"🕒 وقت الذروة: {peak_hour}\n"
        f"📅 يوم الذروة: {peak_day}\n\n"
        
        "*أكثر 3 أوقات نشاطًا:*\n"
        f"{top_hours_text}\n\n"
        
        "*التوزيع اليومي:*\n"
        f"{day_stats}"
    )


async def get_comprehensive_report_text() -> str:
    """
    جلب نص التقرير الشامل
    """
    stats = db_manager.get_aggregated_statistics()
    
    if 'error' in stats:
        return f"حدث خطأ أثناء جلب التقرير الشامل: {stats['error']}"
    
    summary = stats.get('summary', {})
    daily = stats.get('daily', {})
    success_rates = stats.get('success_rates', {})
    peak_times = stats.get('peak_times', {})
    
    return (
        "📑 *التقرير الإحصائي الشامل*\n\n"
        "*ملخص الأداء:*\n"
        f"📨 إجمالي الإشعارات: {summary.get('total_notifications', 0)}\n"
        f"💬 إجمالي الرسائل: {summary.get('total_messages', 0)}\n"
        f"⏰ إجمالي التذكيرات: {summary.get('total_reminders', 0)}\n"
        f"📊 متوسط الإشعارات اليومية: {summary.get('avg_daily_notifications', 0)}\n"
        f"📈 معدل النمو: {summary.get('growth_rate', 0)}%\n\n"
        
        "*اليوم الحالي:*\n"
        f"📨 الإشعارات: {daily.get('notifications_created', 0)}\n"
        f"💬 الرسائل: {daily.get('messages_sent', 0)}\n"
        f"⏰ التذكيرات: {daily.get('notifications_reminded', 0)}\n\n"
        
        "*معدلات النجاح (هذا الشهر):*\n"
        f"💬 معدل نجاح إرسال الرسائل: {success_rates.get('monthly', {}).get('message_success_rate', 0)}%\n"
        f"⏰ معدل نجاح إرسال التذكيرات: {success_rates.get('monthly', {}).get('reminder_success_rate', 0)}%\n\n"
        
        "*أوقات الذروة:*\n"
        f"🕒 وقت الذروة: {peak_times.get('peak_hour', 'غير متوفر')}\n"
        f"📅 يوم الذروة: {peak_times.get('peak_day', 'غير متوفر')}"
    )


def get_stats_handlers():
    """
    العودة بمعالجات الإحصائيات
    """
    # معالج الاستعلامات للإحصائيات (أزرار الإحصائيات)
    stats_callback_handler = CallbackQueryHandler(handle_stats_callback, pattern='^stats_')
    
    # معالج محادثة الإحصائيات
    stats_conv_handler = ConversationHandler(
        entry_points=[
            CommandHandler('stats', stats_command),
            CommandHandler('statistics', stats_command),
        ],
        states={
            SELECTING_STATS_PERIOD: [
                CallbackQueryHandler(handle_stats_callback, pattern='^stats_')
            ],
            SELECTING_STATS_TYPE: [
                CallbackQueryHandler(handle_stats_type_callback, pattern='^stats_')
            ],
        },
        fallbacks=[CommandHandler('cancel', lambda update, context: ConversationHandler.END)],
        allow_reentry=True,
        per_message=False
    )
    
    # استجابة لأمر الإحصائيات المكتوب نصاً
    return [
        stats_conv_handler,
        CommandHandler('stats', stats_command),
        CommandHandler('statistics', stats_command),
        stats_callback_handler  # معالج استعلامات الأزرار منفصل
    ]