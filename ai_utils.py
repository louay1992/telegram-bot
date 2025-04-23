#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
أدوات مساعدة للذكاء الاصطناعي - توفر وظائف مساعدة لمعالجات الذكاء الاصطناعي
"""

import os
import logging
import json
from datetime import datetime

import database as db

# تكوين السجلات
logger = logging.getLogger(__name__)

async def is_admin_async(user_id):
    """
    نسخة غير متزامنة (async) من وظيفة التحقق من المسؤول.
    تستخدم مع معالجات الذكاء الاصطناعي.

    المعلمات:
        user_id (int): معرف المستخدم

    العائد:
        bool: True إذا كان المستخدم مسؤولاً، False خلاف ذلك
    """
    return db.is_admin(user_id)

async def get_notification_by_id_async(notification_id):
    """
    نسخة غير متزامنة (async) من وظيفة الحصول على إشعار بواسطة المعرف.
    تستخدم مع معالجات الذكاء الاصطناعي.

    المعلمات:
        notification_id (str): معرف الإشعار

    العائد:
        dict: بيانات الإشعار إذا وجد، None خلاف ذلك
    """
    try:
        # استخدام الدالة الصحيحة للحصول على الإشعار من قاعدة البيانات
        notification = db.get_notification(notification_id)
        return notification
    except Exception as e:
        logger.error(f"خطأ في الحصول على الإشعار بواسطة المعرف: {str(e)}")
        return None

async def search_notifications_by_phone_async(phone_number):
    """
    نسخة غير متزامنة (async) من وظيفة البحث عن إشعارات بواسطة رقم الهاتف.
    تستخدم مع معالجات الذكاء الاصطناعي.

    المعلمات:
        phone_number (str): رقم الهاتف للبحث

    العائد:
        list: قائمة بالإشعارات المطابقة
    """
    import asyncio
    
    logger.info(f"البحث عن إشعارات باستخدام رقم الهاتف: {phone_number}")
    
    # تحضير نموذج البحث المرن الذي يقبل أشكالاً مختلفة من رقم الهاتف
    search_patterns = [phone_number]
    
    # إضافة أشكال بديلة للبحث
    if phone_number.startswith('+'):
        # إضافة نسخة بدون علامة +
        search_patterns.append(phone_number[1:])
        
        # إذا كان رقم سوري (+963)
        if phone_number.startswith('+963'):
            # إضافة النسخة المحلية (09)
            local_number = '0' + phone_number[4:]
            search_patterns.append(local_number)
        
        # إذا كان رقم تركي (+90)
        elif phone_number.startswith('+90'):
            # إضافة النسخة المحلية (05)
            local_number = '0' + phone_number[3:]
            search_patterns.append(local_number)
    
    # إذا كان الرقم يبدأ بـ 0 (محلي)
    elif phone_number.startswith('0'):
        if phone_number.startswith('09'):  # سوريا
            int_number = '+963' + phone_number[1:]
            search_patterns.append(int_number)
            search_patterns.append('963' + phone_number[1:])
        elif phone_number.startswith('05'):  # تركيا
            int_number = '+90' + phone_number[1:]
            search_patterns.append(int_number)
            search_patterns.append('90' + phone_number[1:])
    
    # إذا كان الرقم يبدأ بكود الدولة بدون +
    elif phone_number.startswith('963'):
        search_patterns.append('+' + phone_number)
        search_patterns.append('0' + phone_number[3:])
    elif phone_number.startswith('90'):
        search_patterns.append('+' + phone_number)
        search_patterns.append('0' + phone_number[2:])
    
    logger.info(f"أنماط البحث المستخدمة: {search_patterns}")
    
    # البحث باستخدام جميع الأنماط
    all_results = []
    
    loop = asyncio.get_event_loop()
    for pattern in search_patterns:
        try:
            results = await loop.run_in_executor(None, db.search_notifications_by_phone, pattern)
            if results:
                all_results.extend(results)
        except Exception as e:
            logger.error(f"خطأ أثناء البحث بنمط {pattern}: {str(e)}")
    
    # إزالة النتائج المكررة بناءً على معرف الإشعار
    unique_results = []
    seen_ids = set()
    
    for notification in all_results:
        if notification['id'] not in seen_ids:
            unique_results.append(notification)
            seen_ids.add(notification['id'])
    
    logger.info(f"تم العثور على {len(unique_results)} إشعار فريد")
    
    return unique_results

async def get_user_permission_async(user_id, permission_type="ai_features"):
    """
    التحقق من صلاحيات المستخدم للوصول إلى ميزات الذكاء الاصطناعي.
    المسؤولين يملكون جميع الصلاحيات تلقائياً.

    المعلمات:
        user_id (int): معرف المستخدم
        permission_type (str): نوع الصلاحية للتحقق، الافتراضي هو "ai_features"

    العائد:
        bool: True إذا كان المستخدم يملك الصلاحية، False خلاف ذلك
    """
    # المسؤولين يملكون جميع الصلاحيات
    if await is_admin_async(user_id):
        return True

    # التحقق من صلاحيات المستخدم العادي
    return db.has_permission(user_id, permission_type)

async def save_ai_chat_history(user_id, message, response, chat_type="general"):
    """
    حفظ سجل محادثة الذكاء الاصطناعي.

    المعلمات:
        user_id (int): معرف المستخدم
        message (str): رسالة المستخدم
        response (str): رد الذكاء الاصطناعي
        chat_type (str): نوع المحادثة (general, image_analysis, delivery_prediction)

    العائد:
        bool: True إذا تم الحفظ بنجاح، False خلاف ذلك
    """
    try:
        # إنشاء مسار حفظ سجلات المحادثات
        chat_history_dir = os.path.join("data", "ai_chat_history")
        os.makedirs(chat_history_dir, exist_ok=True)

        # إنشاء مسار ملف سجل المحادثة للمستخدم
        user_chat_file = os.path.join(chat_history_dir, f"{user_id}.json")

        # تحميل سجل المحادثة الحالي أو إنشاء سجل جديد
        chat_history = []
        if os.path.exists(user_chat_file):
            try:
                with open(user_chat_file, "r", encoding="utf-8") as f:
                    chat_history = json.load(f)
            except json.JSONDecodeError:
                # إذا كان الملف تالفاً، نبدأ بسجل جديد
                chat_history = []

        # إضافة المحادثة الجديدة
        chat_entry = {
            "timestamp": datetime.now().isoformat(),
            "chat_type": chat_type,
            "message": message,
            "response": response
        }
        chat_history.append(chat_entry)

        # حفظ سجل المحادثة المحدث
        with open(user_chat_file, "w", encoding="utf-8") as f:
            json.dump(chat_history, f, ensure_ascii=False, indent=2)

        return True

    except Exception as e:
        logger.error(f"خطأ في حفظ سجل محادثة الذكاء الاصطناعي: {str(e)}")
        return False

async def get_ai_chat_history(user_id, limit=10):
    """
    الحصول على سجل محادثة الذكاء الاصطناعي للمستخدم.

    المعلمات:
        user_id (int): معرف المستخدم
        limit (int): الحد الأقصى لعدد المحادثات المسترجعة

    العائد:
        list: قائمة بسجلات المحادثة السابقة
    """
    try:
        # مسار ملف سجل المحادثة للمستخدم
        user_chat_file = os.path.join("data", "ai_chat_history", f"{user_id}.json")

        # التحقق من وجود السجل
        if not os.path.exists(user_chat_file):
            return []

        # تحميل سجل المحادثة
        with open(user_chat_file, "r", encoding="utf-8") as f:
            chat_history = json.load(f)

        # إرجاع آخر عدد محدد من المحادثات
        return chat_history[-limit:]

    except Exception as e:
        logger.error(f"خطأ في استرجاع سجل محادثة الذكاء الاصطناعي: {str(e)}")
        return []

async def reset_ai_chat_history(user_id):
    """
    إعادة تعيين سجل محادثة الذكاء الاصطناعي للمستخدم.

    المعلمات:
        user_id (int): معرف المستخدم

    العائد:
        bool: True إذا تم إعادة التعيين بنجاح، False خلاف ذلك
    """
    try:
        # مسار ملف سجل المحادثة للمستخدم
        user_chat_file = os.path.join("data", "ai_chat_history", f"{user_id}.json")

        # حذف الملف إذا كان موجوداً
        if os.path.exists(user_chat_file):
            os.remove(user_chat_file)

        return True

    except Exception as e:
        logger.error(f"خطأ في إعادة تعيين سجل محادثة الذكاء الاصطناعي: {str(e)}")
        return False

async def get_ai_stats():
    """
    الحصول على إحصائيات استخدام الذكاء الاصطناعي.

    العائد:
        dict: إحصائيات استخدام الذكاء الاصطناعي
    """
    try:
        # مسار دليل سجلات المحادثات
        chat_history_dir = os.path.join("data", "ai_chat_history")
        
        # التحقق من وجود الدليل
        if not os.path.exists(chat_history_dir):
            return {
                "total_users": 0,
                "total_conversations": 0,
                "total_messages": 0,
                "chat_types": {}
            }
            
        # تجميع الإحصائيات
        stats = {
            "total_users": 0,
            "total_conversations": 0,
            "total_messages": 0,
            "chat_types": {
                "general": 0,
                "image_analysis": 0,
                "delivery_prediction": 0
            }
        }
        
        # قراءة ملفات سجلات المحادثات
        user_files = [f for f in os.listdir(chat_history_dir) if f.endswith('.json')]
        stats["total_users"] = len(user_files)
        
        for user_file in user_files:
            file_path = os.path.join(chat_history_dir, user_file)
            try:
                with open(file_path, "r", encoding="utf-8") as f:
                    chat_history = json.load(f)
                    
                stats["total_conversations"] += 1
                stats["total_messages"] += len(chat_history)
                
                # تجميع الإحصائيات حسب نوع المحادثة
                for entry in chat_history:
                    chat_type = entry.get("chat_type", "general")
                    stats["chat_types"][chat_type] = stats["chat_types"].get(chat_type, 0) + 1
                    
            except Exception as e:
                logger.error(f"خطأ في قراءة ملف سجل المحادثة {user_file}: {str(e)}")
                continue
                
        return stats
        
    except Exception as e:
        logger.error(f"خطأ في الحصول على إحصائيات الذكاء الاصطناعي: {str(e)}")
        return {
            "total_users": 0,
            "total_conversations": 0,
            "total_messages": 0,
            "chat_types": {}
        }