"""
وظائف مساعدة للتعامل مع سجلات البحث
"""
import logging
from typing import List, Dict, Any, Optional
from models import SearchHistory, Notification
from db_manager import SessionLocal, increment_statistics

def add_search_record(user_id: int, username: str, search_term: str, search_type: str, 
                     results: List[Dict[str, Any]]) -> bool:
    """
    إضافة سجل بحث جديد
    
    Args:
        user_id: معرف المستخدم
        username: اسم المستخدم
        search_term: مصطلح البحث
        search_type: نوع البحث (اسم أو رقم هاتف)
        results: نتائج البحث
        
    Returns:
        bool: True إذا تم الإضافة بنجاح، False خلاف ذلك
    """
    db = SessionLocal()
    try:
        # طباعة معلومات تشخيصية
        logging.info(f"إضافة سجل بحث جديد: المستخدم {user_id}, البحث: '{search_term}', النوع: {search_type}, عدد النتائج: {len(results)}")
        
        if not results:
            logging.warning(f"محاولة إضافة سجل بحث بدون نتائج: المستخدم {user_id}, البحث: '{search_term}'")
            return False
            
        # طباعة أول نتيجة للتشخيص
        if results:
            first_result = results[0]
            logging.info(f"أول نتيجة: {first_result}")
            if 'id' not in first_result:
                logging.error(f"النتائج لا تحتوي على حقل 'id'. مفاتيح النتيجة الأولى: {first_result.keys()}")
                
        # استخراج معرفات الإشعارات من النتائج مع مزيد من التدقيق
        notification_ids = []
        for i, result in enumerate(results):
            result_id = result.get('id')
            if result_id:
                notification_ids.append(result_id)
            else:
                logging.warning(f"النتيجة رقم {i} لا تحتوي على معرف: {result}")
        
        logging.info(f"تم استخراج {len(notification_ids)} معرف للإشعارات: {notification_ids}")
        
        # التأكد من أن نوع البحث بالتنسيق الصحيح
        if search_type not in ['name', 'phone']:
            original_type = search_type
            if search_type == 'اسم':
                search_type = 'name'
            elif search_type == 'هاتف':
                search_type = 'phone'
            logging.info(f"تم تصحيح نوع البحث من '{original_type}' إلى '{search_type}'")
        
        # إنشاء سجل البحث
        search_record = SearchHistory(
            user_id=user_id,
            username=username,
            search_term=search_term,
            search_type=search_type,
            results_count=len(results),
            notification_ids=notification_ids
        )
        
        # إضافة السجل إلى قاعدة البيانات
        db.add(search_record)
        db.flush()  # للحصول على معرف السجل
        
        # حفظ معرف السجل مؤقتًا قبل الحفظ النهائي
        record_id = search_record.id
        logging.info(f"تم الحصول على معرف السجل قبل الحفظ: {record_id}")
        
        # استدعاء وظيفة زيادة الإحصائيات
        try:
            increment_statistics('search_queries')
        except Exception as stats_error:
            logging.error(f"خطأ في زيادة إحصائيات البحث: {stats_error}")
            # عدم إيقاف العملية في حالة فشل زيادة الإحصائيات
        
        # الحفظ في قاعدة البيانات
        db.commit()
        
        # استخدام المعرف المؤقت بدلاً من الوصول إلى السجل بعد الحفظ
        logging.info(f"تم إضافة سجل بحث جديد للمستخدم {user_id} بنجاح، معرف السجل: {record_id}")
        return True
    except Exception as e:
        # استرجاع قاعدة البيانات في حالة الخطأ
        try:
            db.rollback()
        except:
            pass
        logging.error(f"خطأ أثناء إضافة سجل البحث: {e}")
        import traceback
        logging.error(traceback.format_exc())
        return False
    finally:
        # إغلاق جلسة قاعدة البيانات
        try:
            db.close()
        except:
            pass

def get_user_search_history(user_id: int, limit: int = 10) -> List[Dict[str, Any]]:
    """
    الحصول على سجلات البحث الخاصة بمستخدم معين
    
    Args:
        user_id: معرف المستخدم
        limit: الحد الأقصى لعدد السجلات المسترجعة
        
    Returns:
        List[Dict[str, Any]]: قائمة بسجلات البحث
    """
    db = SessionLocal()
    try:
        logging.info(f"جاري البحث عن سجلات البحث للمستخدم {user_id}...")
        
        # التحقق من وجود سجلات للمستخدم
        count = db.query(SearchHistory).filter(SearchHistory.user_id == user_id).count()
        logging.info(f"عدد سجلات البحث الموجودة للمستخدم {user_id}: {count}")
        
        if count == 0:
            logging.warning(f"لا توجد سجلات بحث للمستخدم {user_id}")
            return []
            
        records = db.query(SearchHistory)\
            .filter(SearchHistory.user_id == user_id)\
            .order_by(SearchHistory.created_at.desc())\
            .limit(limit)\
            .all()
        
        logging.info(f"تم العثور على {len(records)} سجل بحث للمستخدم {user_id}")
            
        results = []
        
        for i, record in enumerate(records):
            result = record.to_dict()
            
            logging.info(f"معالجة سجل البحث #{i+1}: {record.id} - المصطلح: {record.search_term}, "
                         f"النوع: {record.search_type}, معرفات الإشعارات: {record.notification_ids}")
            
            # إضافة معلومات الإشعارات لكل سجل
            if record.notification_ids and len(record.notification_ids) > 0:
                notifications = []
                
                for notif_id in record.notification_ids:
                    try:
                        notification = db.query(Notification).filter(Notification.id == notif_id).first()
                        if notification:
                            notifications.append({
                                'id': notification.id,
                                'customer_name': notification.customer_name,
                                'phone_number': notification.phone_number,
                                'is_delivered': notification.is_delivered,
                                'has_image': notification.has_image
                            })
                        else:
                            logging.warning(f"لم يتم العثور على الإشعار بالمعرف: {notif_id}")
                    except Exception as notif_error:
                        logging.error(f"خطأ في استرجاع الإشعار {notif_id}: {notif_error}")
                
                logging.info(f"تم العثور على {len(notifications)} إشعار مرتبط بسجل البحث {record.id}")
                result['notifications'] = notifications
            else:
                logging.warning(f"سجل البحث {record.id} لا يحتوي على معرفات إشعارات")
                result['notifications'] = []
                
            results.append(result)
            
        return results
    except Exception as e:
        logging.error(f"خطأ أثناء استرجاع سجلات البحث: {e}")
        import traceback
        logging.error(traceback.format_exc())
        return []
    finally:
        db.close()

def get_search_record_by_id(record_id: int) -> Optional[Dict[str, Any]]:
    """
    الحصول على سجل بحث محدد بواسطة معرفه
    
    Args:
        record_id: معرف سجل البحث
        
    Returns:
        Optional[Dict[str, Any]]: بيانات سجل البحث أو None إذا لم يتم العثور عليه
    """
    db = SessionLocal()
    try:
        record = db.query(SearchHistory).filter(SearchHistory.id == record_id).first()
        
        if not record:
            return None
            
        result = record.to_dict()
        
        # إضافة معلومات الإشعارات
        if record.notification_ids:
            notifications = []
            for notif_id in record.notification_ids:
                notification = db.query(Notification).filter(Notification.id == notif_id).first()
                if notification:
                    notifications.append({
                        'id': notification.id,
                        'customer_name': notification.customer_name,
                        'phone_number': notification.phone_number,
                        'is_delivered': notification.is_delivered,
                        'has_image': notification.has_image
                    })
            result['notifications'] = notifications
            
        return result
    except Exception as e:
        logging.error(f"خطأ أثناء استرجاع سجل البحث: {e}")
        return None
    finally:
        db.close()

def delete_search_record(record_id: int, user_id: int) -> bool:
    """
    حذف سجل بحث محدد
    
    Args:
        record_id: معرف سجل البحث
        user_id: معرف المستخدم (للتحقق من الملكية)
        
    Returns:
        bool: True إذا تم الحذف بنجاح، False خلاف ذلك
    """
    db = SessionLocal()
    try:
        record = db.query(SearchHistory)\
            .filter(SearchHistory.id == record_id, SearchHistory.user_id == user_id)\
            .first()
            
        if not record:
            return False
            
        db.delete(record)
        db.commit()
        
        logging.info(f"تم حذف سجل البحث {record_id}")
        return True
    except Exception as e:
        db.rollback()
        logging.error(f"خطأ أثناء حذف سجل البحث: {e}")
        return False
    finally:
        db.close()