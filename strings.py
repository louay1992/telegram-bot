# Arabic translations for the bot messages

# Generic messages
WELCOME_MESSAGE = """
مرحبا بك في بوت تتبع الشحنات 📦
- للبحث عن شحنة باسم العميل، أرسل: /search اسم العميل
- للبحث عن شحنة برقم الهاتف، أرسل: /phone رقم الهاتف
- للمساعدة، أرسل: /help
- للعودة للقائمة الرئيسية في أي وقت، أرسل: /menu
"""

MAIN_MENU_BUTTON = "🏠 القائمة الرئيسية"
MAIN_MENU_COMMAND = "menu"
BACK_TO_MENU = "العودة للقائمة الرئيسية"

HELP_MESSAGE = """
أوامر البوت:
- /start - بدء استخدام البوت
- /search اسم العميل - البحث عن شحنة باسم العميل
- /phone رقم الهاتف - البحث عن شحنة برقم الهاتف
- /history - عرض سجل البحث السابق
- /cancel - إلغاء أي أمر حالي
- /help - عرض المساعدة

للمسؤولين فقط:
- /add - إضافة إشعار شحن جديد
- /admin_help - عرض مساعدة المسؤول
- /stats - عرض إحصائيات البوت
- /backup - إدارة النسخ الاحتياطية (للمسؤول الرئيسي فقط)
- /restart - إعادة تشغيل البوت بشكل إجباري
"""

ADMIN_HELP_MESSAGE = """
أوامر المسؤول:
- /add - إضافة إشعار شحن جديد (اتبع التعليمات)
- /list - عرض قائمة بجميع الإشعارات
- /delete معرف الإشعار - حذف إشعار
- /template - إدارة قالب الرسالة النصية
- /confirm_delivery - تأكيد استلام الشحنة من قِبل الزبون
- /delivered - عرض قائمة الشحنات المستلمة
- /stats أو /statistics - عرض إحصائيات البوت
- /restart - إعادة تشغيل البوت بشكل إجباري

أوامر إدارة المسؤولين (للمسؤول الرئيسي فقط):
- /add_admin - إضافة مسؤول جديد
- /remove_admin - إزالة مسؤول
- /list_admins - عرض قائمة المسؤولين
- /manage_admins - فتح قائمة إدارة المسؤولين
- /backup - إدارة النسخ الاحتياطية لقاعدة البيانات
"""

# Admin messages
ADMIN_WELCOME = "مرحبًا بك في واجهة المسؤول!"
NOT_AUTHORIZED = "عذرًا، أنت لست مسؤولاً مصرحًا له. هذا الأمر للمسؤولين فقط."
ADD_NOTIFICATION_NAME = "الرجاء إدخال اسم العميل:"
ADD_NOTIFICATION_PHONE = "الرجاء إدخال رقم هاتف العميل (أرقام فقط):"
ADD_NOTIFICATION_IMAGE = "الرجاء إرسال صورة إشعار الشحن:"
ADD_NOTIFICATION_SUCCESS = "تمت إضافة إشعار الشحن بنجاح! ✅"
ADD_NOTIFICATION_CANCEL = "تم إلغاء إضافة الإشعار الجديد."
DELETE_NOTIFICATION_SUCCESS = "تم حذف الإشعار بنجاح! ✅"
DELETE_NOTIFICATION_ERROR = "حدث خطأ أثناء حذف الإشعار. الرجاء التحقق من المعرف."
LIST_NOTIFICATIONS_EMPTY = "لا توجد إشعارات مخزنة حاليًا."
LIST_NOTIFICATIONS_HEADER = "قائمة الإشعارات الحالية:"
INVALID_NAME = "⚠️ الرجاء إدخال اسم غير فارغ للعميل."
INVALID_PHONE = "⚠️ يجب أن يحتوي رقم الهاتف على أرقام فقط. الرجاء إدخال رقم هاتف صحيح:"

# Edit notification messages
EDIT_NAME_PROMPT = "📝 يرجى إدخال اسم العميل الجديد:"
EDIT_PHONE_PROMPT = "📱 يرجى إدخال رقم الهاتف الجديد:"
EDIT_IMAGE_PROMPT = "🖼️ يرجى إرسال صورة الإشعار الجديدة:"
EDIT_NAME_SUCCESS = "✅ تم تحديث اسم العميل بنجاح إلى: {}"
EDIT_PHONE_SUCCESS = "✅ تم تحديث رقم الهاتف بنجاح إلى: {}"
EDIT_IMAGE_SUCCESS = "✅ تم تحديث صورة الإشعار بنجاح."
EDIT_ERROR = "❌ حدث خطأ أثناء تحديث البيانات."

# Admin management
ADD_ADMIN_PROMPT = "الرجاء توجيه رسالة من المستخدم الذي تريد إضافته كمسؤول، أو إرسال معرف المستخدم."
ADD_ADMIN_SUCCESS = "تمت إضافة المستخدم كمسؤول بنجاح! ✅"
ADD_ADMIN_ALREADY = "هذا المستخدم مسؤول بالفعل!"
ADD_ADMIN_ERROR = "حدث خطأ أثناء إضافة المسؤول. تأكد من إرسال معرف صحيح أو توجيه رسالة من المستخدم."
REMOVE_ADMIN_PROMPT = "الرجاء توجيه رسالة من المسؤول الذي تريد إزالته، أو إرسال معرف المستخدم."
REMOVE_ADMIN_SUCCESS = "تمت إزالة المستخدم من قائمة المسؤولين بنجاح! ✅"
REMOVE_ADMIN_NOT_ADMIN = "هذا المستخدم ليس مسؤولاً!"
REMOVE_ADMIN_ERROR = "حدث خطأ أثناء إزالة المسؤول. تأكد من إرسال معرف صحيح أو توجيه رسالة من المستخدم."
LIST_ADMINS_EMPTY = "لا يوجد مسؤولون مخزنون حاليًا."
LIST_ADMINS_HEADER = "قائمة المسؤولين الحاليين:"
MAIN_ADMIN_ONLY = "هذا الأمر متاح فقط للمسؤول الرئيسي."
RESET_ADMINS_SUCCESS = "تم حذف جميع المسؤولين بنجاح. أول مستخدم يدخل للبوت سيتم تعيينه كمسؤول رئيسي."
RESET_ADMINS_ERROR = "حدث خطأ أثناء حذف المسؤولين. يرجى المحاولة مرة أخرى."

# Search messages
SEARCH_PROMPT = "أدخل اسم العميل للبحث:"
PHONE_SEARCH_PROMPT = "أدخل رقم هاتف العميل للبحث:"
SEARCH_NO_QUERY = "الرجاء إدخال اسم أو رقم هاتف للبحث."
SEARCH_NO_RESULTS = "لم يتم العثور على نتائج للبحث."
SEARCH_RESULTS = "تم العثور على النتائج التالية:"
SEARCH_ERROR = "حدث خطأ أثناء البحث. الرجاء المحاولة مرة أخرى."

# Error messages
GENERAL_ERROR = "حدث خطأ. الرجاء المحاولة مرة أخرى."
IMAGE_ERROR = "حدث خطأ أثناء معالجة الصورة. الرجاء المحاولة مرة أخرى."
INVALID_COMMAND = "أمر غير صالح. أرسل /help للحصول على قائمة الأوامر."

# Reminder messages
REMINDER_HOURS_PROMPT = "بعد كم يوم ترغب في إرسال تذكير للعميل؟ (اكتب رقم بين 1 و 30، أو 0 لعدم إرسال تذكير)"
REMINDER_HOURS_INVALID = "الرجاء إدخال رقم صحيح بين 0 و 30."
REMINDER_SCHEDULED = "تم جدولة تذكير بعد {} يوم من الآن."
REMINDER_DISABLED = "تم تعطيل التذكير التلقائي لهذا الإشعار."
REMINDER_SENT = "تم إرسال التذكير بنجاح إلى العميل {}."
REMINDER_FAILED = "فشل في إرسال التذكير. الخطأ: {}"
WHATSAPP_NOTICE = "✅ سيتم إرسال رسالة واتساب للعميل تحتوي على صورة الإشعار والنص المخصص."

# Message template commands
MESSAGE_TEMPLATE_COMMAND = "template"
VIEW_TEMPLATE = "عرض قالب الرسالة الحالي"
EDIT_TEMPLATE = "تعديل قالب الرسالة"
RESET_TEMPLATE = "إعادة ضبط قالب الرسالة إلى الوضع الافتراضي"
MESSAGE_TEMPLATE_MENU = "إدارة قالب الرسالة النصية"

# Message template messages
CURRENT_TEMPLATE = "📝 *قالب الرسالة الحالي:*\n\n```\n{}\n```\n\nيمكنك استخدام المتغير `{{customer_name}}` والذي سيتم استبداله باسم العميل عند إرسال الرسالة."
EDIT_TEMPLATE_PROMPT = "يرجى إدخال قالب الرسالة الجديد. يمكنك استخدام المتغير {{customer_name}} والذي سيتم استبداله باسم العميل. على سبيل المثال:\n\nمرحباً {{customer_name}}،\n\nهذا تذكير بأن لديك شحنة جاهزة للاستلام.\n\nمع تحيات شركة الشحن."
TEMPLATE_UPDATED = "✅ تم تحديث قالب الرسالة بنجاح!"
TEMPLATE_RESET = "✅ تم إعادة ضبط قالب الرسالة إلى الوضع الافتراضي."
TEMPLATE_ERROR = "❌ حدث خطأ أثناء تحديث قالب الرسالة. الرجاء المحاولة مرة أخرى."

# Welcome message template commands
WELCOME_TEMPLATE_COMMAND = "welcome_template"
VIEW_WELCOME_TEMPLATE = "عرض قالب الرسالة الترحيبية"
EDIT_WELCOME_TEMPLATE = "تعديل قالب الرسالة الترحيبية"
RESET_WELCOME_TEMPLATE = "إعادة ضبط قالب الرسالة الترحيبية"
WELCOME_TEMPLATE_MENU = "إدارة قالب الرسالة الترحيبية الأولية"

# Welcome message template messages
CURRENT_WELCOME_TEMPLATE = "📝 *قالب الرسالة الترحيبية الحالي:*\n\n```\n{}\n```\n\nيمكنك استخدام المتغير `{{customer_name}}` والذي سيتم استبداله باسم العميل عند إرسال الرسالة."
EDIT_WELCOME_TEMPLATE_PROMPT = "يرجى إدخال قالب الرسالة الترحيبية الجديد. يمكنك استخدام المتغير {{customer_name}} والذي سيتم استبداله باسم العميل."
WELCOME_TEMPLATE_UPDATED = "✅ تم تحديث قالب الرسالة الترحيبية بنجاح!"
WELCOME_TEMPLATE_RESET = "✅ تم إعادة ضبط قالب الرسالة الترحيبية إلى الوضع الافتراضي."
WELCOME_TEMPLATE_ERROR = "❌ حدث خطأ أثناء تحديث قالب الرسالة الترحيبية. الرجاء المحاولة مرة أخرى."

# Verification message template commands
VERIFICATION_TEMPLATE_COMMAND = "verification_template"
VIEW_VERIFICATION_TEMPLATE = "عرض قالب رسالة التحقق"
EDIT_VERIFICATION_TEMPLATE = "تعديل قالب رسالة التحقق"
RESET_VERIFICATION_TEMPLATE = "إعادة ضبط قالب رسالة التحقق"
VERIFICATION_TEMPLATE_MENU = "إدارة قالب رسالة التحقق من الاستلام"

# Verification message template messages
CURRENT_VERIFICATION_TEMPLATE = "📝 *قالب رسالة التحقق من الاستلام الحالي:*\n\n```\n{}\n```\n\nيمكنك استخدام المتغير `{{customer_name}}` والذي سيتم استبداله باسم العميل عند إرسال الرسالة."
EDIT_VERIFICATION_TEMPLATE_PROMPT = "يرجى إدخال قالب رسالة التحقق من الاستلام الجديد. يمكنك استخدام المتغير {{customer_name}} والذي سيتم استبداله باسم العميل."
VERIFICATION_TEMPLATE_UPDATED = "✅ تم تحديث قالب رسالة التحقق من الاستلام بنجاح!"
VERIFICATION_TEMPLATE_RESET = "✅ تم إعادة ضبط قالب رسالة التحقق من الاستلام إلى الوضع الافتراضي."
VERIFICATION_TEMPLATE_ERROR = "❌ حدث خطأ أثناء تحديث قالب رسالة التحقق من الاستلام. الرجاء المحاولة مرة أخرى."

# Verification message actions
SEND_VERIFICATION_MESSAGE = "📨 إرسال رسالة تحقق من الاستلام"
VERIFICATION_MESSAGE_SENT = "✅ تم إرسال رسالة التحقق من الاستلام بنجاح إلى العميل عبر واتساب."
VERIFICATION_MESSAGE_FAILED = "⚠️ لم يتم إرسال رسالة التحقق من الاستلام. سبب الخطأ: {}"

# Welcome message template for immediate notification
WELCOME_TEMPLATE_DEFAULT = """مرحباً {{customer_name}}،

تم شحن طلبك بنجاح! الطلب الآن في طريقه إليك.

ستجد صورة إشعار الشحن مرفقة مع هذه الرسالة للاطلاع عليها.

مع تحيات شركة الشحن 🚚
"""

WELCOME_MESSAGE_SENT = "✅ تم إرسال رسالة ترحيبية فورية إلى العميل."
WELCOME_MESSAGE_FAILED = "⚠️ لم يتم إرسال الرسالة الترحيبية الفورية. سبب الخطأ: {}"

# Stats messages
STATS_COMMAND = "statistics"
STATS_MENU_TITLE = "📊 إحصائيات البوت"
STATS_DAILY = "📈 إحصائيات اليوم"
STATS_WEEKLY = "📅 إحصائيات الأسبوع"
STATS_MONTHLY = "📆 إحصائيات الشهر"
STATS_TOTAL = "🔄 الإحصائيات الإجمالية"
STATS_SUCCESS_RATES = "✅ معدلات النجاح"
STATS_PEAK_TIMES = "⏱ أوقات الذروة"
STATS_COMPREHENSIVE = "📋 تقرير شامل"
STATS_BACK = "🔙 رجوع"

STATS_DAILY_TITLE = "📈 إحصائيات اليوم:"
STATS_WEEKLY_TITLE = "📅 إحصائيات الأسبوع الحالي:"
STATS_MONTHLY_TITLE = "📆 إحصائيات الشهر الحالي:"
STATS_TOTAL_TITLE = "🔄 الإحصائيات الإجمالية:"
STATS_SUCCESS_RATES_TITLE = "✅ معدلات نجاح الإرسال:"
STATS_PEAK_TIMES_TITLE = "⏱ أوقات الذروة في الاستخدام:"
STATS_COMPREHENSIVE_TITLE = "📋 تقرير شامل عن أداء البوت:"

# Button texts for delivery confirmation feature
CONFIRM_DELIVERY_BUTTON = "✅ تأكيد استلام زبون"
LIST_DELIVERED_BUTTON = "📋 قائمة الشحنات المستلمة"
SEARCH_BY_NAME = "🧾 بحث باسم العميل"
SEARCH_BY_PHONE = "📱 بحث برقم الهاتف"
CANCEL_BUTTON = "❌ إلغاء"
CONFIRM_BUTTON = "✓ تأكيد"

# Updated NOT_ADMIN constant
NOT_ADMIN = "عذرًا، أنت لست مسؤولاً مصرحًا له. هذا الأمر للمسؤولين فقط."

# Bot restart command messages
RESTART_INITIATED = "🔄 جاري إعادة تشغيل البوت... سيكون البوت متاحاً مرة أخرى خلال لحظات."
RESTART_COMPLETED = "✅ تم إعادة تشغيل البوت بنجاح!"
RESTART_ERROR = "❌ حدث خطأ أثناء محاولة إعادة تشغيل البوت."

# Delivery confirmation messages
DELIVERY_CONFIRMATION_START = """
بدء عملية تأكيد استلام شحنة من قبل الزبون ✅

اختر طريقة البحث عن الشحنة:
"""
ENTER_CUSTOMER_NAME_FOR_DELIVERY = "أدخل اسم العميل المستلم للشحنة:"
ENTER_PHONE_NUMBER_FOR_DELIVERY = "أدخل رقم هاتف العميل المستلم للشحنة:"
NO_NOTIFICATIONS_FOUND = "لم يتم العثور على أي شحنات مرتبطة بـ '{search_term}'."
MULTIPLE_NOTIFICATIONS_FOUND = "تم العثور على {count} شحنات. الرجاء اختيار الشحنة المراد تأكيد استلامها:"
INVALID_SEARCH_METHOD = "خيار غير صالح. الرجاء اختيار إحدى طرق البحث المتاحة."
NOTIFICATION_NOT_FOUND = "لم يتم العثور على بيانات الشحنة المطلوبة."
UNEXPECTED_ERROR = "حدث خطأ غير متوقع. الرجاء المحاولة مرة أخرى."

# Notification details display
NOTIFICATION_DETAILS = """
تفاصيل الشحنة:
- اسم العميل: {customer_name}
- رقم الهاتف: {phone_number}
- تاريخ الإنشاء: {created_at}
{delivery_info}
"""
ALREADY_DELIVERED_INFO = """
⚠️ ملاحظة: هذه الشحنة تم تأكيد استلامها بالفعل بتاريخ {delivered_at}
"""

# Delivery proof and confirmation
UPLOAD_PROOF_IMAGE = "الرجاء إرسال صورة كدليل على استلام الشحنة من العميل (الصورة مطلوبة):"
UPLOAD_PROOF_IMAGE_AGAIN = "الرجاء إرسال صورة صالحة كدليل على استلام الشحنة."
NOT_AN_IMAGE = "الملف المرسل ليس صورة. الرجاء إرسال صورة فقط."
ENTER_DELIVERY_NOTES = "يمكنك إضافة ملاحظات إضافية حول عملية الاستلام (اختياري):"

# Delivery confirmation summary and status
DELIVERY_CONFIRMATION_SUMMARY = """
✅ تأكيد استلام شحنة:
- العميل: {customer_name}
- رقم الهاتف: {phone_number}
- ملاحظات: {notes}

هل تريد تأكيد استلام هذه الشحنة؟
"""
DELIVERY_CONFIRMED_SUCCESS = "✅ تم تأكيد استلام الشحنة بنجاح وتحديث حالتها في قاعدة البيانات!"
ERROR_CONFIRMING_DELIVERY = "❌ حدث خطأ أثناء تأكيد الاستلام. الرجاء المحاولة مرة أخرى لاحقًا."
DELIVERY_CONFIRMATION_CANCELLED = "تم إلغاء عملية تأكيد الاستلام."

# List delivered notifications
NO_DELIVERED_NOTIFICATIONS = "لا توجد شحنات مؤكدة الاستلام حتى الآن."
DELIVERED_NOTIFICATIONS_HEADER = "📋 قائمة الشحنات المؤكدة الاستلام ({count} شحنة):\n\n"
DELIVERED_NOTIFICATION_ITEM = """
{index}. {customer_name} - {phone_number}
   ⏱ تاريخ التأكيد: {delivered_at}
   👤 بواسطة: {confirmed_by}
   -----------------------------
"""

# Errors and administrative messages
IMAGE_NOT_FOUND = "لم يتم العثور على صورة الإشعار."
ERROR_SENDING_IMAGE = "تعذر إرسال صورة الإشعار."
ERROR_SAVING_IMAGE = "حدث خطأ أثناء حفظ الصورة."
TRY_AGAIN_LATER = "الرجاء المحاولة مرة أخرى لاحقًا."
OPERATION_CANCELLED = "تم إلغاء العملية بنجاح."

# Admin notification about delivery confirmation
ADMIN_DELIVERY_NOTIFICATION = """
🔔 *تنبيه: تم تأكيد استلام شحنة*

العميل: {customer_name}
رقم الهاتف: {phone_number}
تم التأكيد بواسطة: {confirming_username}

يمكنك الاطلاع على المزيد من التفاصيل عبر الأمر /delivered
"""

# Filter and categorization system
FILTER_COMMAND = "filter"
FILTER_MENU_TITLE = "🔍 تصفية الإشعارات"
FILTER_BY_DATE = "📅 تصفية حسب التاريخ"
FILTER_BY_STATUS = "📊 تصفية حسب الحالة"
FILTER_BACK = "🔙 رجوع"

# Date filters
FILTER_TODAY = "📆 اليوم"
FILTER_THIS_WEEK = "📆 هذا الأسبوع"
FILTER_THIS_MONTH = "📆 هذا الشهر"
FILTER_ALL_TIME = "📆 كل الوقت"

# Status filters
FILTER_DELIVERED = "✅ تم الاستلام"
FILTER_NOT_DELIVERED = "⏳ قيد الانتظار"
FILTER_REMINDER_SENT = "🔔 تم إرسال التذكير"
FILTER_ALL_STATUS = "📋 كل الحالات"

# Filter results
FILTER_RESULTS_HEADER = "📋 نتائج التصفية ({count} شحنة):\n\n"
FILTER_NO_RESULTS = "لم يتم العثور على نتائج مطابقة للتصفية."
FILTER_APPLIED = "تم تطبيق التصفية: {filter_name}"

# Advanced search system
ADVANCED_SEARCH_COMMAND = "advanced_search"
ADVANCED_SEARCH_WELCOME = "🔍 البحث المتقدم\n\nيمكنك كتابة جزء من اسم العميل أو رقم الهاتف للبحث\nسيتم عرض النتائج المتطابقة على الفور"
ADVANCED_SEARCH_NO_RESULTS = "لم يتم العثور على نتائج للبحث عن: '{query}'"
ADVANCED_SEARCH_RESULTS = "🔍 نتائج البحث عن: '{query}'\nتم العثور على {count} نتيجة:"
SAVE_TO_FAVORITES = "⭐ حفظ بحث"
NEW_SEARCH = "🔍 بحث جديد"
FAVORITES_LIST = "⭐ قائمة البحث المفضلة:"
DELETE_FROM_FAVORITES = "🗑️ حذف من المفضلة"
SELECT_FAVORITE_TO_DELETE = "🗑️ اختر البحث المفضل الذي ترغب في حذفه:"
FAVORITE_DELETED = "✅ تم حذف البحث '{name}' من المفضلة بنجاح!"
FAVORITE_SAVED = "✅ تم حفظ البحث '{name}' في المفضلة بنجاح!"
ENTER_FAVORITE_NAME = "أدخل اسما مختصرا لحفظ هذا البحث في المفضلة:"
NO_FAVORITES = "لا يوجد أي عمليات بحث محفوظة في المفضلة."

# Watchdog messages
RESTART_STATUS_DETAIL = "آخر {count} محاولات إعادة تشغيل:"

# Backup messages
ONLY_MAIN_ADMIN = "هذا الأمر متاح فقط للمسؤول الرئيسي."
BACKUP_COMMAND = "backup"
BACKUP_MENU_TITLE = "📦 إدارة النسخ الاحتياطية"
CREATE_BACKUP = "🔄 إنشاء نسخة احتياطية جديدة"
LIST_BACKUPS = "📋 عرض النسخ الاحتياطية المتوفرة"
RESTORE_BACKUP = "🔙 استعادة نسخة احتياطية"
BACKUP_CREATED_SUCCESS = "✅ تم إنشاء النسخة الاحتياطية بنجاح.\nالمسار: {}"
BACKUP_CREATED_ERROR = "❌ حدث خطأ أثناء إنشاء النسخة الاحتياطية: {}"
NO_BACKUPS_AVAILABLE = "❌ لا توجد نسخ احتياطية متوفرة."
AVAILABLE_BACKUPS = "📋 النسخ الاحتياطية المتوفرة:"
BACKUP_SELECT_TO_RESTORE = "🔍 اختر نسخة احتياطية لاستعادتها:"
CONFIRM_RESTORE_BACKUP = "⚠️ هل أنت متأكد من أنك تريد استعادة هذه النسخة الاحتياطية؟\n\nسيتم استبدال قاعدة البيانات الحالية بالنسخة الاحتياطية المحددة. هذا الإجراء لا يمكن التراجع عنه."
BACKUP_RESTORED_SUCCESS = "✅ تم استعادة النسخة الاحتياطية بنجاح."
BACKUP_RESTORED_ERROR = "❌ حدث خطأ أثناء استعادة النسخة الاحتياطية: {}"
RESTORE_CANCELLED = "🚫 تم إلغاء عملية الاستعادة."
