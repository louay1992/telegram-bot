"""
مدير قاعدة البيانات للبوت
"""
import os
import logging
import json
from datetime import datetime, date, timedelta
from typing import List, Dict, Any, Optional, Union, Tuple
from sqlalchemy import create_engine, func, desc
from sqlalchemy.orm import sessionmaker, scoped_session
from sqlalchemy.sql.expression import extract
from models import Base, Notification, Admin, Statistic, SearchHistory

# استخدام URI قاعدة البيانات من المتغيرات البيئية
DATABASE_URL = os.environ.get('DATABASE_URL')

if not DATABASE_URL:
    logging.warning("DATABASE_URL is not set. Using SQLite as fallback.")
    DATABASE_URL = 'sqlite:///shipping_bot.db'

# إنشاء محرك قاعدة البيانات
engine = create_engine(DATABASE_URL)

# إنشاء جلسة
SessionLocal = scoped_session(sessionmaker(autocommit=False, autoflush=False, bind=engine))

# التأكد من إنشاء جميع الجداول
Base.metadata.create_all(bind=engine)

def migrate_json_to_db():
    """
    نقل البيانات من ملفات JSON إلى قاعدة البيانات SQL
    """
    from database import load_json
    
    # نقل بيانات الإشعارات
    try:
        notifications_data = load_json('data/notifications.json', default={"notifications": []})
        db = SessionLocal()
        
        # التحقق من نوع البيانات المستلمة
        if isinstance(notifications_data, dict) and "notifications" in notifications_data:
            # البيانات بالتنسيق الجديد كقائمة في كائن
            notifications_list = notifications_data["notifications"]
            
            for notification_data in notifications_list:
                notification_id = notification_data.get('id')
                if not notification_id:
                    continue
                    
                # التحقق مما إذا كان الإشعار موجوداً
                existing = db.query(Notification).filter_by(id=notification_id).first()
                if not existing:
                    notification = Notification(
                        id=notification_id,
                        customer_name=notification_data.get('customer_name', ''),
                        phone_number=notification_data.get('phone_number', ''),
                        created_at=datetime.fromisoformat(notification_data.get('created_at')) if notification_data.get('created_at') else datetime.utcnow(),
                        reminder_hours=float(notification_data.get('reminder_hours', 24)),
                        reminder_sent=notification_data.get('reminder_sent', False),
                        has_image=True  # افتراضي لأن جميع الإشعارات القديمة لديها صور
                    )
                    db.add(notification)
        elif isinstance(notifications_data, dict):
            # البيانات بالتنسيق القديم كقاموس
            for notification_id, notification_data in notifications_data.items():
                # تخطي المفاتيح الخاصة
                if notification_id == "notifications":
                    continue
                    
                # التحقق مما إذا كان الإشعار موجوداً
                existing = db.query(Notification).filter_by(id=notification_id).first()
                if not existing:
                    notification = Notification(
                        id=notification_id,
                        customer_name=notification_data.get('customer_name', ''),
                        phone_number=notification_data.get('phone_number', ''),
                        created_at=datetime.fromisoformat(notification_data.get('created_at')) if notification_data.get('created_at') else datetime.utcnow(),
                        reminder_hours=float(notification_data.get('reminder_hours', 24)),
                        reminder_sent=notification_data.get('reminder_sent', False),
                        has_image=True  # افتراضي لأن جميع الإشعارات القديمة لديها صور
                    )
                    db.add(notification)
        
        # استيراد بيانات المسؤولين
        admins_data = load_json('data/admins.json', default={'admins': [], 'main_admin': None})
        
        if isinstance(admins_data, dict) and "admins" in admins_data:
            admin_list = admins_data.get('admins', [])
            main_admin = admins_data.get('main_admin')
            
            for admin_id in admin_list:
                # التحقق مما إذا كان المسؤول موجوداً
                existing = db.query(Admin).filter_by(user_id=admin_id).first()
                if not existing:
                    is_main = admin_id == main_admin
                    admin = Admin(
                        user_id=admin_id,
                        username='',  # لا نملك اسم المستخدم من الملف القديم
                        is_main_admin=is_main
                    )
                    db.add(admin)
        
        db.commit()
        logging.info("نقل البيانات من ملفات JSON إلى قاعدة البيانات SQL بنجاح")
    except Exception as e:
        db.rollback()
        logging.error(f"حدث خطأ أثناء نقل البيانات: {e}")
    finally:
        db.close()

def get_db():
    """
    الحصول على جلسة قاعدة البيانات
    """
    db = SessionLocal()
    try:
        return db
    finally:
        db.close()
        
def mark_as_delivered(notification_id: str, user_id: int, notes: str = None) -> bool:
    """
    تحديث إشعار ليصبح في حالة "تم التسليم"
    
    Args:
        notification_id: معرف الإشعار
        user_id: معرف المستخدم الذي أكد التسليم
        notes: ملاحظات إضافية (اختياري)
        
    Returns:
        bool: True إذا تم التحديث بنجاح، False خلاف ذلك
    """
    db = None
    try:
        db = SessionLocal()
        notification = db.query(Notification).filter(Notification.id == notification_id).first()
        
        if not notification:
            logging.error(f"لم يتم العثور على إشعار بالمعرف {notification_id}")
            return False
            
        notification.is_delivered = True
        notification.delivery_confirmed_at = datetime.now()
        notification.delivery_confirmed_by = user_id
        
        if notes:
            notification.delivery_notes = notes
            
        db.commit()
        
        # زيادة عداد الإحصائيات
        increment_statistics('deliveries_confirmed')
        
        logging.info(f"تم تحديث حالة الإشعار {notification_id} إلى 'تم التسليم'")
        return True
    except Exception as e:
        if db:
            db.rollback()
        logging.error(f"خطأ أثناء تحديث حالة التسليم: {e}")
        return False
    finally:
        if db:
            db.close()
            
def add_delivery_proof_image(notification_id: str, has_image: bool = True) -> bool:
    """
    تحديث إشعار لإضافة صورة دليل تسليم
    
    Args:
        notification_id: معرف الإشعار
        has_image: ما إذا كان هناك صورة دليل
        
    Returns:
        bool: True إذا تم التحديث بنجاح، False خلاف ذلك
    """
    db = None
    try:
        db = SessionLocal()
        notification = db.query(Notification).filter(Notification.id == notification_id).first()
        
        if not notification:
            logging.error(f"لم يتم العثور على إشعار بالمعرف {notification_id}")
            return False
            
        notification.has_proof_image = has_image
        db.commit()
        
        logging.info(f"تم تحديث حالة صورة دليل التسليم للإشعار {notification_id}")
        return True
    except Exception as e:
        if db:
            db.rollback()
        logging.error(f"خطأ أثناء تحديث حالة صورة دليل التسليم: {e}")
        return False
    finally:
        if db:
            db.close()
            
def get_delivered_notifications(include_archived: bool = False) -> List[Dict[str, Any]]:
    """
    الحصول على جميع الإشعارات التي تم تسليمها
    
    Args:
        include_archived: ما إذا كان يجب تضمين الإشعارات المؤرشفة
    
    Returns:
        List[Dict[str, Any]]: قائمة بالإشعارات التي تم تسليمها
    """
    db = None
    try:
        db = SessionLocal()
        query = db.query(Notification).filter(Notification.is_delivered == True)
        
        # استبعاد الإشعارات المؤرشفة إذا لم يتم طلبها
        if not include_archived:
            query = query.filter(Notification.is_archived == False)
            
        notifications = query.all()
        
        result = []
        for notification in notifications:
            notification_dict = notification.to_dict()
            
            # إضافة معلومات المستخدم الذي أكد التسليم إذا كان متاحاً
            if notification.delivery_confirmed_by:
                admin = db.query(Admin).filter(Admin.user_id == notification.delivery_confirmed_by).first()
                if admin:
                    notification_dict['confirmed_by_username'] = admin.username
            
            # إضافة معلومات المستخدم الذي قام بالأرشفة إذا كان متاحاً
            if notification.archived_by:
                admin = db.query(Admin).filter(Admin.user_id == notification.archived_by).first()
                if admin:
                    notification_dict['archived_by_username'] = admin.username
                    
            result.append(notification_dict)
            
        return result
    except Exception as e:
        logging.error(f"خطأ أثناء استرجاع الإشعارات المسلمة: {e}")
        return []
    finally:
        if db:
            db.close()

def add_notification(customer_name: str, phone_number: str, notification_id: str, reminder_hours: float = 24) -> Tuple[bool, str]:
    """
    إضافة إشعار جديد إلى قاعدة البيانات
    """
    db = SessionLocal()
    try:
        # إنشاء الإشعار
        notification = Notification(
            id=notification_id,
            customer_name=customer_name,
            phone_number=phone_number,
            reminder_hours=reminder_hours
        )
        
        db.add(notification)
        
        # تحديث الإحصائيات
        today = date.today()
        stats = db.query(Statistic).filter(Statistic.date == today).first()
        
        if stats:
            stats.notifications_created += 1
        else:
            stats = Statistic(date=today, notifications_created=1)
            db.add(stats)
            
        db.commit()
        return True, notification_id
    except Exception as e:
        db.rollback()
        logging.error(f"Error adding notification to database: {e}")
        return False, str(e)
    finally:
        db.close()

def update_notification(notification_id: str, updates: Dict[str, Any]) -> bool:
    """
    تحديث بيانات إشعار في قاعدة البيانات
    """
    db = SessionLocal()
    try:
        notification = db.query(Notification).filter_by(id=notification_id).first()
        if not notification:
            return False
        
        for key, value in updates.items():
            if hasattr(notification, key):
                setattr(notification, key, value)
        
        db.commit()
        return True
    except Exception as e:
        db.rollback()
        logging.error(f"Error updating notification in database: {e}")
        return False
    finally:
        db.close()

def get_all_notifications() -> List[Dict[str, Any]]:
    """
    الحصول على جميع الإشعارات من قاعدة البيانات
    """
    db = SessionLocal()
    try:
        notifications = db.query(Notification).order_by(desc(Notification.created_at)).all()
        return [n.to_dict() for n in notifications]
    except Exception as e:
        logging.error(f"Error fetching notifications from database: {e}")
        return []
    finally:
        db.close()

def search_notifications_by_name(name: str) -> List[Dict[str, Any]]:
    """
    البحث عن الإشعارات باسم العميل
    """
    db = SessionLocal()
    try:
        name_search = f"%{name}%"
        notifications = db.query(Notification).filter(Notification.customer_name.ilike(name_search)).all()
        return [n.to_dict() for n in notifications]
    except Exception as e:
        logging.error(f"Error searching notifications by name: {e}")
        return []
    finally:
        db.close()

def search_notifications_by_phone(phone: str) -> List[Dict[str, Any]]:
    """
    البحث عن الإشعارات برقم الهاتف
    هذه الوظيفة تسمح بالبحث المرن عن أرقام الهواتف بغض النظر عن تنسيقها
    (مع أو بدون رمز الدولة، مع أو بدون علامة +)
    """
    from sqlalchemy import or_
    import re
    
    # التنظيف والتحضير الأولي للرقم
    # إزالة أي أحرف ليست أرقام
    cleaned_phone = ''.join(c for c in phone if c.isdigit())
    
    # إذا كان الرقم يبدأ بصفر، نقوم بإنشاء نسخة إضافية محتملة مع رمز البلد
    variants = [cleaned_phone]
    
    # إزالة رمز البلد إذا كان موجوداً للبحث عن الرقم بدون رمز البلد أيضاً
    if cleaned_phone.startswith('963'):
        # الرقم بدون رمز البلد (لكن مع الصفر الأول)
        without_country_code = '0' + cleaned_phone[3:]
        variants.append(without_country_code)
    
    # إذا كان الرقم يبدأ بصفر، نقوم بإضافة نسخة مع رمز البلد
    elif cleaned_phone.startswith('0'):
        # الرقم مع رمز البلد (وبدون الصفر الأول)
        with_country_code = '963' + cleaned_phone[1:]
        variants.append(with_country_code)
    
    # إذا لم يبدأ الرقم بـ 963 أو 0، نفترض أنه رقم بدون رمز البلد وبدون 0
    # نضيف نسخًا مع رمز البلد ومع الصفر الأول
    else:
        with_country_code = '963' + cleaned_phone
        with_zero = '0' + cleaned_phone
        variants.append(with_country_code)
        variants.append(with_zero)
    
    logging.info(f"Searching for phone variants: {variants}")
    
    db = SessionLocal()
    try:
        # بناء استعلام بحث مرن يبحث عن أي من المتغيرات الممكنة
        filters = []
        for variant in variants:
            filters.append(Notification.phone_number.ilike(f"%{variant}%"))
        
        # البحث باستخدام OR بين كل المتغيرات
        notifications = db.query(Notification).filter(or_(*filters)).all()
        
        # تسجيل نتائج البحث
        if notifications:
            logging.info(f"Found {len(notifications)} notifications for phone variants")
        else:
            logging.info(f"No notifications found for phone variants")
            
        return [n.to_dict() for n in notifications]
    except Exception as e:
        logging.error(f"Error searching notifications by phone: {e}")
        return []
    finally:
        db.close()

def delete_notification(notification_id: str) -> bool:
    """
    حذف إشعار من قاعدة البيانات
    """
    db = SessionLocal()
    try:
        notification = db.query(Notification).filter_by(id=notification_id).first()
        if notification:
            db.delete(notification)
            db.commit()
            return True
        return False
    except Exception as e:
        db.rollback()
        logging.error(f"Error deleting notification: {e}")
        return False
    finally:
        db.close()

def add_admin(user_id: int, username: str = '', is_main_admin: bool = False) -> bool:
    """
    إضافة مسؤول جديد
    """
    db = SessionLocal()
    try:
        existing = db.query(Admin).filter_by(user_id=user_id).first()
        if existing:
            if existing.is_main_admin != is_main_admin:
                existing.is_main_admin = is_main_admin
                db.commit()
            return True
        
        admin = Admin(
            user_id=user_id,
            username=username,
            is_main_admin=is_main_admin
        )
        db.add(admin)
        db.commit()
        return True
    except Exception as e:
        db.rollback()
        logging.error(f"Error adding admin: {e}")
        return False
    finally:
        db.close()

def remove_admin(user_id: int) -> bool:
    """
    حذف مسؤول
    """
    db = SessionLocal()
    try:
        admin = db.query(Admin).filter_by(user_id=user_id).first()
        if admin:
            db.delete(admin)
            db.commit()
            return True
        return False
    except Exception as e:
        db.rollback()
        logging.error(f"Error removing admin: {e}")
        return False
    finally:
        db.close()

def get_all_admins() -> List[Dict[str, Any]]:
    """
    الحصول على جميع المسؤولين
    """
    db = SessionLocal()
    try:
        admins = db.query(Admin).all()
        result = []
        for admin in admins:
            result.append({
                'user_id': admin.user_id,
                'username': admin.username,
                'is_main_admin': admin.is_main_admin,
                'added_at': admin.added_at.isoformat() if admin.added_at else None
            })
        return result
    except Exception as e:
        logging.error(f"Error getting all admins: {e}")
        return []
    finally:
        db.close()

def is_admin(user_id: int) -> bool:
    """
    التحقق مما إذا كان المستخدم مسؤولاً
    """
    db = SessionLocal()
    try:
        admin = db.query(Admin).filter_by(user_id=user_id).first()
        return admin is not None
    except Exception as e:
        logging.error(f"Error checking admin status: {e}")
        return False
    finally:
        db.close()

def is_main_admin(user_id: int) -> bool:
    """
    التحقق مما إذا كان المستخدم المسؤول الرئيسي
    """
    db = SessionLocal()
    try:
        admin = db.query(Admin).filter_by(user_id=user_id, is_main_admin=True).first()
        return admin is not None
    except Exception as e:
        logging.error(f"Error checking main admin status: {e}")
        return False
    finally:
        db.close()

def set_main_admin_if_none(user_id: int, username: str = '') -> bool:
    """
    تعيين المستخدم كمسؤول رئيسي إذا لم يكن هناك مسؤول رئيسي
    يتم استدعاؤها فقط للمستخدم الأول الذي يصل إلى البوت بعد حذف جميع المسؤولين
    """
    db = SessionLocal()
    try:
        # التحقق مما إذا كان هناك أي مسؤول رئيسي
        main_admin = db.query(Admin).filter_by(is_main_admin=True).first()
        if main_admin:
            return False
        
        # إذا لم يكن هناك أي مسؤول رئيسي، فقم بتعيين هذا المستخدم كمسؤول رئيسي
        existing = db.query(Admin).filter_by(user_id=user_id).first()
        if existing:
            existing.is_main_admin = True
            existing.username = username or existing.username
        else:
            admin = Admin(user_id=user_id, username=username, is_main_admin=True)
            db.add(admin)
        
        db.commit()
        return True
    except Exception as e:
        db.rollback()
        logging.error(f"Error setting main admin: {e}")
        return False
    finally:
        db.close()

def delete_all_admins() -> bool:
    """
    حذف جميع المسؤولين من النظام
    """
    db = SessionLocal()
    try:
        db.query(Admin).delete()
        db.commit()
        return True
    except Exception as e:
        db.rollback()
        logging.error(f"Error deleting all admins: {e}")
        return False
    finally:
        db.close()
        
def archive_notification(notification_id: str, user_id: int) -> bool:
    """
    أرشفة إشعار (وضعه في حالة الأرشفة)
    
    Args:
        notification_id: معرف الإشعار المراد أرشفته
        user_id: معرف المستخدم الذي يقوم بالأرشفة
        
    Returns:
        bool: True إذا تمت العملية بنجاح، False خلاف ذلك
    """
    db = SessionLocal()
    try:
        notification = db.query(Notification).filter_by(id=notification_id).first()
        if not notification:
            logging.warning(f"محاولة أرشفة إشعار غير موجود: {notification_id}")
            return False
        
        # التحقق مما إذا كان الإشعار مؤرشفاً بالفعل
        if notification.is_archived:
            return True  # الإشعار مؤرشف بالفعل
        
        # أرشفة الإشعار
        notification.is_archived = True
        notification.archived_at = datetime.utcnow()
        notification.archived_by = user_id
        
        db.commit()
        logging.info(f"تمت أرشفة الإشعار بنجاح: {notification_id}")
        return True
    except Exception as e:
        db.rollback()
        logging.error(f"خطأ أثناء أرشفة الإشعار: {e}")
        return False
    finally:
        db.close()
        
def unarchive_notification(notification_id: str) -> bool:
    """
    إلغاء أرشفة إشعار
    
    Args:
        notification_id: معرف الإشعار المراد إلغاء أرشفته
        
    Returns:
        bool: True إذا تمت العملية بنجاح، False خلاف ذلك
    """
    db = SessionLocal()
    try:
        notification = db.query(Notification).filter_by(id=notification_id).first()
        if not notification:
            logging.warning(f"محاولة إلغاء أرشفة إشعار غير موجود: {notification_id}")
            return False
        
        # التحقق مما إذا كان الإشعار غير مؤرشف بالفعل
        if not notification.is_archived:
            return True  # الإشعار غير مؤرشف بالفعل
        
        # إلغاء أرشفة الإشعار
        notification.is_archived = False
        notification.archived_at = None
        notification.archived_by = None
        
        db.commit()
        logging.info(f"تم إلغاء أرشفة الإشعار بنجاح: {notification_id}")
        return True
    except Exception as e:
        db.rollback()
        logging.error(f"خطأ أثناء إلغاء أرشفة الإشعار: {e}")
        return False
    finally:
        db.close()
        
def get_archived_notifications() -> List[Dict[str, Any]]:
    """
    الحصول على جميع الإشعارات المؤرشفة
    
    Returns:
        List[Dict[str, Any]]: قائمة بالإشعارات المؤرشفة
    """
    db = None
    try:
        db = SessionLocal()
        notifications = db.query(Notification).filter(
            Notification.is_archived == True,
            Notification.is_delivered == True
        ).all()
        
        result = []
        for notification in notifications:
            notification_dict = notification.to_dict()
            
            # إضافة معلومات المستخدم الذي أكد التسليم إذا كان متاحاً
            if notification.delivery_confirmed_by:
                admin = db.query(Admin).filter(Admin.user_id == notification.delivery_confirmed_by).first()
                if admin:
                    notification_dict['confirmed_by_username'] = admin.username
            
            # إضافة معلومات المستخدم الذي قام بالأرشفة إذا كان متاحاً
            if notification.archived_by:
                admin = db.query(Admin).filter(Admin.user_id == notification.archived_by).first()
                if admin:
                    notification_dict['archived_by_username'] = admin.username
                    
            result.append(notification_dict)
            
        return result
    except Exception as e:
        logging.error(f"خطأ أثناء استرجاع الإشعارات المؤرشفة: {e}")
        return []
    finally:
        if db:
            db.close()

def increment_statistics(stat_type: str, count: int = 1) -> bool:
    """
    زيادة إحصائية معينة
    
    Args:
        stat_type: نوع الإحصائية (notifications_created, notifications_reminded, 
                  messages_sent, images_processed, ocr_success, ocr_failure)
        count: عدد الزيادة (افتراضياً 1)
    """
    db = SessionLocal()
    try:
        today = date.today()
        stats = db.query(Statistic).filter(Statistic.date == today).first()
        
        if not stats:
            stats = Statistic(date=today)
            db.add(stats)
        
        if hasattr(stats, stat_type):
            current_value = getattr(stats, stat_type)
            # التعامل مع حالة القيمة الفارغة (None)
            if current_value is None:
                current_value = 0
            setattr(stats, stat_type, current_value + count)
            
        db.commit()
        return True
    except Exception as e:
        db.rollback()
        logging.error(f"Error incrementing statistics: {e}")
        return False
    finally:
        db.close()

def get_daily_statistics(days: int = 7) -> List[Dict[str, Any]]:
    """
    الحصول على الإحصائيات اليومية لعدد معين من الأيام الماضية
    
    Args:
        days: عدد الأيام
    """
    db = None
    try:
        db = SessionLocal()
        # تأكد من أن days قيمة إيجابية
        days = max(1, days)
        
        # لنحصل على الإحصائيات موجودة بالفعل
        stats = db.query(Statistic).order_by(desc(Statistic.date)).limit(days).all()
        
        # بيانات القاموس
        result = []
        for stat in stats:
            try:
                result.append(stat.to_dict())
            except Exception as dict_error:
                logging.error(f"Error converting statistic to dict: {dict_error}")
                # إضافة قاموس بأقل المعلومات الضرورية
                result.append({
                    'date': stat.date if hasattr(stat, 'date') else datetime.now().date(),
                    'notifications_created': 0,
                    'notifications_reminded': 0,
                    'messages_sent': 0,
                    'images_processed': 0
                })
                
        return result
    except Exception as e:
        logging.error(f"Error getting daily statistics: {e}")
        # إذا كان هناك خطأ، أعد قائمة مع إحصائيات فارغة ليوم واحد
        return [{
            'date': datetime.now().date(),
            'notifications_created': 0,
            'notifications_reminded': 0,
            'messages_sent': 0,
            'images_processed': 0
        }]
    finally:
        if db:
            try:
                db.close()
            except Exception as close_error:
                logging.error(f"Error closing database connection: {close_error}")

def get_monthly_statistics() -> Dict[str, Any]:
    """
    الحصول على إحصائيات الشهر الحالي
    """
    db = SessionLocal()
    try:
        current_month = datetime.now().month
        current_year = datetime.now().year
        
        # استعلام لمجموع إحصائيات الشهر الحالي
        result = db.query(
            func.sum(Statistic.notifications_created).label('notifications_created'),
            func.sum(Statistic.notifications_reminded).label('notifications_reminded'),
            func.sum(Statistic.messages_sent).label('messages_sent'),
            func.sum(Statistic.images_processed).label('images_processed'),
            func.sum(Statistic.ocr_success).label('ocr_success'),
            func.sum(Statistic.ocr_failure).label('ocr_failure')
        ).filter(
            extract('month', Statistic.date) == current_month,
            extract('year', Statistic.date) == current_year
        ).first()
        
        if result:
            return {
                'month': current_month,
                'year': current_year,
                'notifications_created': result.notifications_created or 0,
                'notifications_reminded': result.notifications_reminded or 0,
                'messages_sent': result.messages_sent or 0,
                'images_processed': result.images_processed or 0,
                'ocr_success': result.ocr_success or 0,
                'ocr_failure': result.ocr_failure or 0
            }
        
        return {
            'month': current_month,
            'year': current_year,
            'notifications_created': 0,
            'notifications_reminded': 0,
            'messages_sent': 0,
            'images_processed': 0,
            'ocr_success': 0,
            'ocr_failure': 0
        }
    except Exception as e:
        logging.error(f"Error getting monthly statistics: {e}")
        return {
            'month': datetime.now().month,
            'year': datetime.now().year,
            'error': str(e)
        }
    finally:
        db.close()

def get_total_statistics() -> Dict[str, Any]:
    """
    الحصول على إجمالي الإحصائيات
    """
    db = None
    try:
        db = SessionLocal()
        # استعلام لمجموع جميع الإحصائيات
        result = db.query(
            func.sum(Statistic.notifications_created).label('notifications_created'),
            func.sum(Statistic.notifications_reminded).label('notifications_reminded'),
            func.sum(Statistic.messages_sent).label('messages_sent'),
            func.sum(Statistic.images_processed).label('images_processed'),
            func.sum(Statistic.ocr_success).label('ocr_success'),
            func.sum(Statistic.ocr_failure).label('ocr_failure')
        ).first()
        
        if result:
            return {
                'notifications_created': result.notifications_created or 0,
                'notifications_reminded': result.notifications_reminded or 0,
                'messages_sent': result.messages_sent or 0,
                'images_processed': result.images_processed or 0,
                'ocr_success': result.ocr_success or 0,
                'ocr_failure': result.ocr_failure or 0
            }
        
        return {
            'notifications_created': 0,
            'notifications_reminded': 0,
            'messages_sent': 0,
            'images_processed': 0,
            'ocr_success': 0,
            'ocr_failure': 0
        }
    except Exception as e:
        logging.error(f"Error getting total statistics: {e}")
        # عند حدوث خطأ، نعيد إحصائيات فارغة مع وجود مفتاح خاص للخطأ
        return {
            'notifications_created': 0,
            'notifications_reminded': 0,
            'messages_sent': 0,
            'images_processed': 0,
            'ocr_success': 0,
            'ocr_failure': 0,
            'error': str(e)
        }
    finally:
        if db:
            try:
                db.close()
            except Exception as close_error:
                logging.error(f"Error closing database connection: {close_error}")

def get_weekly_statistics() -> Dict[str, Any]:
    """
    الحصول على إحصائيات الأسبوع الحالي
    """
    db = None
    try:
        db = SessionLocal()
        # الحصول على الأيام السبعة الماضية
        today = date.today()
        week_ago = today - timedelta(days=7)
        
        # استعلام لمجموع إحصائيات الأسبوع الحالي
        result = db.query(
            func.sum(Statistic.notifications_created).label('notifications_created'),
            func.sum(Statistic.notifications_reminded).label('notifications_reminded'),
            func.sum(Statistic.messages_sent).label('messages_sent'),
            func.sum(Statistic.images_processed).label('images_processed'),
            func.sum(Statistic.ocr_success).label('ocr_success'),
            func.sum(Statistic.ocr_failure).label('ocr_failure')
        ).filter(
            Statistic.date >= week_ago,
            Statistic.date <= today
        ).first()
        
        if result:
            return {
                'period': 'weekly',
                'notifications_created': result.notifications_created or 0,
                'notifications_reminded': result.notifications_reminded or 0,
                'messages_sent': result.messages_sent or 0,
                'images_processed': result.images_processed or 0,
                'ocr_success': result.ocr_success or 0,
                'ocr_failure': result.ocr_failure or 0
            }
        
        return {
            'period': 'weekly',
            'notifications_created': 0,
            'notifications_reminded': 0,
            'messages_sent': 0,
            'images_processed': 0,
            'ocr_success': 0,
            'ocr_failure': 0
        }
    except Exception as e:
        logging.error(f"Error getting weekly statistics: {e}")
        # عند حدوث خطأ، نعيد إحصائيات فارغة مع رسالة الخطأ
        return {
            'period': 'weekly',
            'notifications_created': 0,
            'notifications_reminded': 0,
            'messages_sent': 0,
            'images_processed': 0,
            'ocr_success': 0,
            'ocr_failure': 0,
            'error': str(e)
        }
    finally:
        if db:
            try:
                db.close()
            except Exception as close_error:
                logging.error(f"Error closing database connection: {close_error}")

def get_success_rates() -> Dict[str, Any]:
    """
    الحصول على معدلات نجاح إرسال الرسائل والتذكيرات
    """
    db = None
    try:
        db = SessionLocal()
        # اليومي
        today = date.today()
        daily_stats = db.query(Statistic).filter(Statistic.date == today).first()
        
        # الأسبوعي
        week_ago = today - timedelta(days=7)
        weekly_result = db.query(
            func.sum(Statistic.notifications_created).label('notifications_created'),
            func.sum(Statistic.notifications_reminded).label('notifications_reminded'),
            func.sum(Statistic.messages_sent).label('messages_sent')
        ).filter(
            Statistic.date >= week_ago,
            Statistic.date <= today
        ).first()
        
        # الشهري
        current_month = datetime.now().month
        current_year = datetime.now().year
        monthly_result = db.query(
            func.sum(Statistic.notifications_created).label('notifications_created'),
            func.sum(Statistic.notifications_reminded).label('notifications_reminded'),
            func.sum(Statistic.messages_sent).label('messages_sent')
        ).filter(
            extract('month', Statistic.date) == current_month,
            extract('year', Statistic.date) == current_year
        ).first()
        
        # حساب معدلات النجاح
        daily_message_rate = 0
        daily_reminder_rate = 0
        if daily_stats:
            if daily_stats.notifications_created > 0:
                daily_message_rate = (daily_stats.messages_sent / daily_stats.notifications_created) * 100
            if daily_stats.notifications_reminded > 0 and daily_stats.notifications_created > 0:
                daily_reminder_rate = (daily_stats.notifications_reminded / daily_stats.notifications_created) * 100
        
        weekly_message_rate = 0
        weekly_reminder_rate = 0
        if weekly_result and weekly_result.notifications_created:
            if weekly_result.notifications_created > 0:
                weekly_message_rate = (weekly_result.messages_sent / weekly_result.notifications_created) * 100
            if weekly_result.notifications_reminded > 0 and weekly_result.notifications_created > 0:
                weekly_reminder_rate = (weekly_result.notifications_reminded / weekly_result.notifications_created) * 100
        
        monthly_message_rate = 0
        monthly_reminder_rate = 0
        if monthly_result and monthly_result.notifications_created:
            if monthly_result.notifications_created > 0:
                monthly_message_rate = (monthly_result.messages_sent / monthly_result.notifications_created) * 100
            if monthly_result.notifications_reminded > 0 and monthly_result.notifications_created > 0:
                monthly_reminder_rate = (monthly_result.notifications_reminded / monthly_result.notifications_created) * 100
        
        return {
            'daily': {
                'message_success_rate': round(daily_message_rate, 2),
                'reminder_success_rate': round(daily_reminder_rate, 2)
            },
            'weekly': {
                'message_success_rate': round(weekly_message_rate, 2),
                'reminder_success_rate': round(weekly_reminder_rate, 2)
            },
            'monthly': {
                'message_success_rate': round(monthly_message_rate, 2),
                'reminder_success_rate': round(monthly_reminder_rate, 2)
            }
        }
    except Exception as e:
        logging.error(f"Error getting success rates: {e}")
        # عند حدوث خطأ، نعيد قيم افتراضية مع رسالة الخطأ
        return {
            'daily': {'message_success_rate': 0, 'reminder_success_rate': 0},
            'weekly': {'message_success_rate': 0, 'reminder_success_rate': 0},
            'monthly': {'message_success_rate': 0, 'reminder_success_rate': 0},
            'error': str(e)
        }
    finally:
        if db:
            try:
                db.close()
            except Exception as close_error:
                logging.error(f"Error closing database connection: {close_error}")

def get_peak_usage_times() -> Dict[str, Any]:
    """
    الحصول على أوقات الذروة في استخدام البوت
    
    ملاحظة: هذه الدالة محاكاة بسيطة. للتنفيذ الحقيقي، يجب إضافة عمود 'hour' إلى جدول الإحصائيات 
    وحساب الإحصائيات على مستوى الساعة.
    """
    db = None
    try:
        db = SessionLocal()
        # نحتاج إلى استخدام بيانات وقت إنشاء الإشعارات لتحليل أوقات الذروة
        # هذه مجرد شيفرة تمثيلية وتحتاج إلى تحسين في الإنتاج الفعلي
        
        # الحصول على توزيع الإشعارات حسب اليوم
        day_distribution = db.query(
            extract('dow', Notification.created_at).label('day_of_week'),
            func.count().label('count')
        ).group_by('day_of_week').order_by('day_of_week').all()
        
        # تحويل النتائج إلى قاموس
        day_data = {}
        for day in day_distribution:
            day_name = ['الأحد', 'الإثنين', 'الثلاثاء', 'الأربعاء', 'الخميس', 'الجمعة', 'السبت'][int(day.day_of_week)]
            day_data[day_name] = day.count
        
        # الحصول على توزيع الإشعارات حسب الساعة
        hour_distribution = db.query(
            extract('hour', Notification.created_at).label('hour'),
            func.count().label('count')
        ).group_by('hour').order_by('hour').all()
        
        # تحويل النتائج إلى قاموس
        hour_data = {}
        for hour in hour_distribution:
            hour_data[f"{int(hour.hour)}:00"] = hour.count
        
        # تحديد وقت الذروة (الساعة والأيام الأكثر نشاطًا)
        peak_hour = None
        peak_hour_count = 0
        for hour, count in hour_data.items():
            if count > peak_hour_count:
                peak_hour = hour
                peak_hour_count = count
        
        peak_day = None
        peak_day_count = 0
        for day, count in day_data.items():
            if count > peak_day_count:
                peak_day = day
                peak_day_count = count
        
        # في حالة عدم وجود بيانات
        if not peak_hour:
            peak_hour = "غير متوفر"
        if not peak_day:
            peak_day = "غير متوفر"
        
        return {
            'peak_hour': peak_hour,
            'peak_day': peak_day,
            'hourly_distribution': hour_data,
            'daily_distribution': day_data
        }
    except Exception as e:
        logging.error(f"Error getting peak usage times: {e}")
        # عند حدوث خطأ، نعيد قيم افتراضية مع رسالة الخطأ
        return {
            'peak_hour': "غير متوفر",
            'peak_day': "غير متوفر",
            'hourly_distribution': {},
            'daily_distribution': {},
            'error': str(e)
        }
    finally:
        if db:
            try:
                db.close()
            except Exception as close_error:
                logging.error(f"Error closing database connection: {close_error}")

def get_aggregated_statistics() -> Dict[str, Any]:
    """
    الحصول على إحصائيات شاملة تجمع كل المعلومات المفيدة
    """
    try:
        logging.info("جلب الإحصائيات الشاملة...")
        daily_stats = get_daily_statistics(1)
        # التحقق من أن daily_stats هي قائمة غير فارغة قبل الوصول إلى العنصر الأول
        daily = daily_stats[0] if daily_stats and len(daily_stats) > 0 else {}
        
        weekly = get_weekly_statistics()
        monthly = get_monthly_statistics()
        total = get_total_statistics()
        success_rates = get_success_rates()
        peak_times = get_peak_usage_times()
        
        # حساب متوسط الإشعارات اليومية
        weekly_count = weekly.get('notifications_created', 0) or 0
        avg_daily = 0
        if weekly_count:
            try:
                avg_daily = round(weekly_count / 7, 2)
            except Exception as avg_error:
                logging.error(f"خطأ في حساب المتوسط اليومي: {avg_error}")
                avg_daily = 0
        
        # حساب معدل نمو الإشعارات (مقارنة بالأسبوع الماضي)
        # ملاحظة: هذه شيفرة تمثيلية وتحتاج إلى بيانات أكثر دقة في الإنتاج الفعلي
        growth_rate = 0
        daily_created = daily.get('notifications_created', 0) or 0
        if daily_created > 0 and avg_daily > 0:
            try:
                growth_rate = ((daily_created / avg_daily) - 1) * 100
            except Exception as growth_error:
                logging.error(f"خطأ في حساب معدل النمو: {growth_error}")
                growth_rate = 0
        
        result = {
            'summary': {
                'total_notifications': total.get('notifications_created', 0) or 0,
                'total_messages': total.get('messages_sent', 0) or 0,
                'total_reminders': total.get('notifications_reminded', 0) or 0,
                'avg_daily_notifications': avg_daily,
                'growth_rate': round(growth_rate, 2)
            },
            'daily': daily,
            'weekly': weekly,
            'monthly': monthly,
            'success_rates': success_rates,
            'peak_times': peak_times
        }
        
        logging.info("تم جلب الإحصائيات الشاملة بنجاح")
        return result
    except Exception as e:
        logging.error(f"Error getting aggregated statistics: {e}")
        # عند حدوث خطأ، نعيد قاموسًا مع معلومات الخطأ
        return {
            'summary': {
                'total_notifications': 0,
                'total_messages': 0,
                'total_reminders': 0,
                'avg_daily_notifications': 0,
                'growth_rate': 0
            },
            'daily': {},
            'weekly': {},
            'monthly': {},
            'success_rates': {},
            'peak_times': {},
            'error': str(e)
        }

def create_test_statistics():
    """
    إنشاء بيانات إحصائية للاختبار
    """
    db = None
    try:
        db = SessionLocal()
        
        # التحقق من وجود إحصائيات حالية
        existing_stats_count = db.query(func.count(Statistic.id)).scalar()
        if existing_stats_count and existing_stats_count > 0:
            logging.info(f"تم العثور على {existing_stats_count} سجل إحصائي موجود بالفعل")
            return True
        
        # حذف الإحصائيات القديمة (تعليق هذا السطر إذا أردت الحفاظ على الإحصائيات السابقة)
        db.query(Statistic).delete()
        logging.info("تم حذف الإحصائيات السابقة")
        
        # إنشاء بيانات للأيام السبعة الماضية
        today = date.today()
        logging.info("إنشاء بيانات إحصائية تجريبية للأيام السبعة الماضية...")
        
        for i in range(7):
            day = today - timedelta(days=i)
            # قيم متناقصة للأيام السابقة لإنشاء اتجاه نمو
            stats = Statistic(
                date=day,
                notifications_created=10 - i,
                notifications_reminded=5 - (i // 2),
                messages_sent=15 - i,
                images_processed=12 - i,
                ocr_success=8 - (i // 2),
                ocr_failure=4 - (i // 2)
            )
            db.add(stats)
        
        db.commit()
        logging.info("تم إنشاء البيانات الإحصائية التجريبية بنجاح")
        return True
            
    except Exception as e:
        if db:
            try:
                db.rollback()
            except Exception as rollback_error:
                logging.error(f"خطأ أثناء التراجع عن تغييرات قاعدة البيانات: {rollback_error}")
        logging.error(f"خطأ أثناء إنشاء البيانات الإحصائية التجريبية: {e}")
        return False
    finally:
        if db:
            try:
                db.close()
            except Exception as close_error:
                logging.error(f"خطأ أثناء إغلاق اتصال قاعدة البيانات: {close_error}")

# محاولة نقل البيانات من JSON إلى SQL عند استيراد الوحدة
try:
    migrate_json_to_db()
    # كذلك محاولة إنشاء بيانات إحصائية تجريبية إذا لم تكن موجودة
    create_test_statistics()
except Exception as e:
    logging.error(f"Error during migration: {e}")