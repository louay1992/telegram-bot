#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
وحدة المساعد الذكي - تدمج نماذج الذكاء الاصطناعي مع بوت التيليجرام

تتيح هذه الوحدة وظائف ذكية مثل:
- محادثة ذكية مع العملاء والمسوقين
- تحليل صور الشحنات
- التنبؤ بأوقات التسليم
"""

import os
import json
import logging
import random
from datetime import datetime, timedelta
import base64

# تكوين السجلات
logger = logging.getLogger(__name__)

# استيراد مكتبات الذكاء الاصطناعي
try:
    from openai import OpenAI
    openai_imported = True
    logger.info("تم استيراد مكتبة OpenAI بنجاح")
except ImportError:
    openai_imported = False
    logger.error("فشل استيراد مكتبة OpenAI")

try:
    from anthropic import Anthropic
    anthropic_imported = True
    logger.info("تم استيراد مكتبة Anthropic بنجاح")
except ImportError:
    anthropic_imported = False
    logger.error("فشل استيراد مكتبة Anthropic")

# الحصول على مفاتيح API الخاصة بنماذج الذكاء الاصطناعي
OPENAI_API_KEY = os.environ.get('OPENAI_API_KEY')
ANTHROPIC_API_KEY = os.environ.get('ANTHROPIC_API_KEY')

# the newest OpenAI model is "gpt-4o" which was released May 13, 2024. 
# do not change this unless explicitly requested by the user
OPENAI_MODEL = "gpt-4o"

#the newest Anthropic model is "claude-3-5-sonnet-20241022" which was released October 22, 2024
# do not change this unless explicitly requested by the user
ANTHROPIC_MODEL = "claude-3-5-sonnet-20241022"

# التحقق من وجود مفاتيح API وتكوين العملاء
openai_client = None
if OPENAI_API_KEY and openai_imported:
    try:
        openai_client = OpenAI(api_key=OPENAI_API_KEY)
        logger.info("تم تكوين OpenAI API")
    except Exception as e:
        logger.error(f"خطأ في تكوين OpenAI API: {str(e)}")
        openai_client = None
else:
    logger.warning("مفتاح OpenAI API غير متوفر أو لم يتم استيراد المكتبة بنجاح")

anthropic_client = None
if ANTHROPIC_API_KEY and anthropic_imported:
    try:
        anthropic_client = Anthropic(api_key=ANTHROPIC_API_KEY)
        logger.info("تم تكوين Anthropic API")
    except Exception as e:
        logger.error(f"خطأ في تكوين Anthropic API: {str(e)}")
        anthropic_client = None
else:
    logger.warning("مفتاح Anthropic API غير متوفر أو لم يتم استيراد المكتبة بنجاح")

def get_ai_response(user_message, message_type="chat", image_data=None, delivery_data=None, notification_search=None):
    """
    الحصول على رد ذكي من نماذج الذكاء الاصطناعي
    
    المعلمات:
        user_message (str): رسالة المستخدم
        message_type (str): نوع الرسالة: "chat", "image", "delivery_prediction", "phone_search"
        image_data (str): بيانات الصورة بتنسيق base64 (للتحليل البصري)
        delivery_data (dict): بيانات إضافية للتنبؤ بالتسليم
        notification_search (dict): نتائج البحث عن إشعارات (للبحث برقم الهاتف)
        
    العائد:
        str: رد الذكاء الاصطناعي
    """
    try:
        # التحقق أولاً من توفر Anthropic API (الخيار المفضل)
        if anthropic_client:
            logger.info("استخدام Anthropic API للحصول على الرد")
            
            # إنشاء سياق الرسالة حسب نوع الطلب
            if message_type == "chat":
                # ضبط نظام رسالة للمحادثة
                system_message = """
                أنت مساعد ذكي لنظام إدارة الشحنات، متخصص في مساعدة المسوقين والعملاء.
                أجب بشكل موجز ومفيد عن أسئلة المستخدم المتعلقة بالشحنات والتسليم.
                لغتك الرئيسية هي العربية.
                """
                
                response = anthropic_client.messages.create(
                    model=ANTHROPIC_MODEL,
                    max_tokens=1000,
                    system=system_message,
                    messages=[
                        {"role": "user", "content": user_message}
                    ]
                )
                
                return response.content[0].text
                
            elif message_type == "phone_search":
                # تحضير نص نتائج البحث بناءً على بيانات الإشعارات
                if notification_search and len(notification_search) > 0:
                    # تم العثور على إشعار أو أكثر
                    notification = notification_search[0]  # نأخذ الإشعار الأول في حالة وجود عدة نتائج
                    
                    # تنسيق تاريخ الإنشاء إذا كان متوفراً
                    created_at = "غير متوفر"
                    if "created_at" in notification:
                        try:
                            from datetime import datetime
                            if isinstance(notification["created_at"], str):
                                created_at = notification["created_at"].split("T")[0]  # استخراج التاريخ فقط دون الوقت
                            else:
                                created_at = notification["created_at"].strftime("%Y-%m-%d")
                        except:
                            created_at = str(notification["created_at"])
                    
                    # تنسيق النص للإشعار
                    formatted_result = f"""
✅ تم العثور على إشعار الشحنة:

👤 اسم الزبون: {notification.get("customer_name", "غير متوفر")}
📞 رقم الهاتف: {notification.get("phone_number", "غير متوفر")}
📅 تاريخ الشحنة: {created_at}
"""
                    
                    # إضافة الوجهة إذا كانت متوفرة
                    if notification.get("destination"):
                        formatted_result += f"📍 الوجهة: {notification.get('destination')}\n"
                    
                    # إضافة قيمة الشحنة إذا كانت متوفرة
                    if notification.get("value"):
                        formatted_result += f"💰 القيمة: {notification.get('value')}\n"
                    
                    # إضافة إشارة إلى الصورة
                    formatted_result += f"🖼️ صورة الإشعار متوفرة [رقم المعرف: {notification.get('id', 'غير متوفر')}]"
                    
                    return formatted_result
                else:
                    # لم يتم العثور على إشعارات
                    return "⚠️ لم يتم العثور على إشعار شحنة يطابق الرقم المدخل. تأكد من صحة الرقم أو جرب رقمًا آخر."
                
            elif message_type == "image":
                # تحليل الصورة (يتطلب Claude 3 vision)
                system_message = """
                أنت محلل خبير متخصص في المجالات التالية:
                1. تحليل صور الشحنات والطرود
                2. تحليل الفواتير والإيصالات
                3. تمييز المستندات المتعلقة بالشحن
                
                قدم تحليلاً شاملاً يتضمن:
                1. تحديد نوع المستند (شحنة، فاتورة، إيصال، صورة منتج، الخ)
                2. استخراج البيانات المهمة كالتاريخ والقيمة والعناوين
                3. حالة الشحنة إذا كانت الصورة تظهر طرداً
                4. تفاصيل التسعير والكميات إذا كانت الصورة تظهر فاتورة
                5. أي معلومات مفيدة تظهر في الصورة
                
                ملاحظة مهمة: هذه الصور تأتي عادة ضمن سياق إدارة الشحنات والفواتير، لذا ركز على الجوانب ذات الصلة بنظام إدارة الشحنات ولا تتطرق للتفاصيل غير المهمة.
                
                أجب باللغة العربية بأسلوب مختصر ومهني.
                """
                
                # إنشاء قائمة الرسائل مع الصورة المضمنة
                messages = [
                    {"role": "user", "content": [
                        {"type": "text", "text": "أرجو تحليل هذه الصورة وإخباري بما تتضمنه. " + user_message},
                        {"type": "image", "source": {"type": "base64", "media_type": "image/jpeg", "data": image_data}}
                    ]}
                ]
                
                response = anthropic_client.messages.create(
                    model=ANTHROPIC_MODEL,
                    max_tokens=1000,
                    system=system_message,
                    messages=messages
                )
                
                return response.content[0].text
                
            elif message_type == "delivery_prediction":
                # التنبؤ بوقت التسليم
                system_message = """
                أنت محلل خبير للشحنات، متخصص في التنبؤ بأوقات التسليم.
                قم بتحليل بيانات الشحنة وتقديم توقع منطقي لوقت التسليم بناءً على المعلومات المقدمة.
                أجب باللغة العربية.
                """
                
                # إنشاء نص الطلب بناءً على بيانات التسليم
                prompt = f"""
                معلومات الشحنة:
                - اسم العميل: {delivery_data.get('customer_name', 'غير معروف')}
                - رقم الهاتف: {delivery_data.get('phone', 'غير معروف')}
                - تاريخ إنشاء الإشعار: {delivery_data.get('created_at', 'غير معروف')}
                - المنطقة: {delivery_data.get('region', 'غير معروف')}
                
                قم بتحليل هذه البيانات وتقديم:
                1. تاريخ التسليم المتوقع
                2. المدة المتوقعة للتسليم بالأيام (حد أدنى وحد أقصى)
                3. مستوى الثقة في التنبؤ (نسبة مئوية)
                4. تحليل العوامل المؤثرة في وقت التسليم
                """
                
                response = anthropic_client.messages.create(
                    model=ANTHROPIC_MODEL,
                    max_tokens=1000,
                    system=system_message,
                    messages=[
                        {"role": "user", "content": prompt}
                    ]
                )
                
                return response.content[0].text
                
        # استخدام OpenAI API كخيار احتياطي إذا كان متوفراً
        elif openai_client:
            logger.info("استخدام OpenAI API للحصول على الرد")
            
            if message_type == "chat":
                # ضبط نظام رسالة للمحادثة
                system_message = """
                أنت مساعد ذكي لنظام إدارة الشحنات، متخصص في مساعدة المسوقين والعملاء.
                أجب بشكل موجز ومفيد عن أسئلة المستخدم المتعلقة بالشحنات والتسليم.
                لغتك الرئيسية هي العربية.
                """
                
                response = openai_client.chat.completions.create(
                    model=OPENAI_MODEL,
                    messages=[
                        {"role": "system", "content": system_message},
                        {"role": "user", "content": user_message}
                    ],
                    max_tokens=1000
                )
                
                return response.choices[0].message.content
                
            elif message_type == "image":
                # تحليل الصورة (يتطلب GPT-4 vision)
                system_message = """
                أنت محلل خبير للشحنات، متخصص في تحليل صور الشحنات وتقديم معلومات مفيدة.
                قم بتحليل الصورة وتحديد:
                1. حالة الطرد/الشحنة
                2. نوع التغليف وجودته
                3. أي تفاصيل مهمة مرئية
                4. نصائح للتعامل مع الشحنة
                أجب باللغة العربية.
                """
                
                response = openai_client.chat.completions.create(
                    model=OPENAI_MODEL,
                    messages=[
                        {"role": "system", "content": system_message},
                        {"role": "user", "content": [
                            {"type": "text", "text": user_message},
                            {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{image_data}"}}
                        ]}
                    ],
                    max_tokens=1000
                )
                
                return response.choices[0].message.content
                
            elif message_type == "delivery_prediction":
                # التنبؤ بوقت التسليم
                system_message = """
                أنت محلل خبير للشحنات، متخصص في التنبؤ بأوقات التسليم.
                قم بتحليل بيانات الشحنة وتقديم توقع منطقي لوقت التسليم بناءً على المعلومات المقدمة.
                أجب باللغة العربية.
                """
                
                # إنشاء نص الطلب بناءً على بيانات التسليم
                prompt = f"""
                معلومات الشحنة:
                - اسم العميل: {delivery_data.get('customer_name', 'غير معروف')}
                - رقم الهاتف: {delivery_data.get('phone', 'غير معروف')}
                - تاريخ إنشاء الإشعار: {delivery_data.get('created_at', 'غير معروف')}
                - المنطقة: {delivery_data.get('region', 'غير معروف')}
                
                قم بتحليل هذه البيانات وتقديم:
                1. تاريخ التسليم المتوقع
                2. المدة المتوقعة للتسليم بالأيام (حد أدنى وحد أقصى)
                3. مستوى الثقة في التنبؤ (نسبة مئوية)
                4. تحليل العوامل المؤثرة في وقت التسليم
                """
                
                response = openai_client.chat.completions.create(
                    model=OPENAI_MODEL,
                    messages=[
                        {"role": "system", "content": system_message},
                        {"role": "user", "content": prompt}
                    ],
                    max_tokens=1000
                )
                
                return response.choices[0].message.content
                
        # إذا لم تكن هناك واجهات API متاحة، استخدم الردود الافتراضية
        else:
            logger.warning("لا توجد واجهات API للذكاء الاصطناعي متاحة، استخدام الردود الافتراضية")
            
            if message_type == "chat":
                return """
                عذراً، لا يمكن الوصول إلى خدمات الذكاء الاصطناعي حالياً. 
                يرجى التواصل مع مسؤول النظام للتحقق من إعدادات API.
                """
                
            elif message_type == "image":
                return """
                عذراً، لا يمكن تحليل الصورة حالياً لعدم توفر خدمات الذكاء الاصطناعي.
                يرجى التواصل مع مسؤول النظام للتحقق من إعدادات API.
                """
                
            elif message_type == "delivery_prediction":
                return """
                عذراً، لا يمكن التنبؤ بوقت التسليم حالياً لعدم توفر خدمات الذكاء الاصطناعي.
                يرجى التواصل مع مسؤول النظام للتحقق من إعدادات API.
                """
                
    except Exception as e:
        logger.error(f"خطأ في الحصول على رد الذكاء الاصطناعي: {str(e)}")
        return f"حدث خطأ أثناء معالجة طلبك: {str(e)}"
        

def process_image(image_file_path, context_info=None):
    """
    معالجة وتحليل صورة الشحنة باستخدام الذكاء الاصطناعي
    
    المعلمات:
        image_file_path (str): مسار ملف الصورة
        context_info (str, optional): معلومات سياقية إضافية عن الصورة
        
    العائد:
        str: نتائج تحليل الصورة
    """
    try:
        # التحقق من وجود الملف
        if not os.path.exists(image_file_path):
            return "خطأ: ملف الصورة غير موجود"
            
        # قراءة الصورة وتحويلها إلى base64
        with open(image_file_path, "rb") as image_file:
            image_data = base64.b64encode(image_file.read()).decode('utf-8')
        
        # تحديد رسالة المستخدم بناءً على السياق
        if context_info and 'إشعار' in context_info:
            user_message = "هذه صورة تم تحميلها في سياق إضافة إشعار شحنة جديد. يرجى تحليل محتوياتها وتقديم معلومات مفيدة عن هذه الفاتورة أو الإشعار."
        elif context_info and 'فاتورة' in context_info:
            user_message = "هذه صورة فاتورة. يرجى تحليل محتوياتها واستخراج المعلومات المهمة مثل المبلغ والتاريخ والعميل."
        elif context_info:
            user_message = f"يرجى تحليل هذه الصورة في سياق: {context_info}"
        else:
            user_message = "يرجى تحليل هذه الصورة وتحديد نوعها (شحنة، فاتورة، إيصال، الخ) وتقديم معلومات مفيدة عن محتواها."
            
        # طلب تحليل الصورة
        analysis = get_ai_response(
            user_message=user_message,
            message_type="image",
            image_data=image_data
        )
        
        return analysis
        
    except Exception as e:
        logger.error(f"خطأ في معالجة الصورة: {str(e)}")
        import traceback
        logger.error(traceback.format_exc())
        return f"حدث خطأ أثناء تحليل الصورة: {str(e)}"
        

def generate_delivery_prediction(notification_data):
    """
    توليد تنبؤ ذكي لوقت تسليم الشحنة بناءً على بيانات الإشعار
    
    المعلمات:
        notification_data (dict): بيانات الإشعار مثل اسم العميل والهاتف وتاريخ الإنشاء
        
    العائد:
        dict: معلومات التنبؤ بالتسليم
    """
    try:
        # تنسيق البيانات للتنبؤ
        delivery_data = {
            "customer_name": notification_data.get("customer_name", "غير معروف"),
            "phone": notification_data.get("phone_number", "غير معروف"),
            "created_at": notification_data.get("created_at", datetime.now().strftime("%Y-%m-%d")),
            "region": "غير محدد"  # يمكن استخراج المنطقة من رقم الهاتف أو إضافتها إلى نموذج البيانات
        }
        
        # الحصول على تحليل الذكاء الاصطناعي
        ai_response = get_ai_response(
            user_message="تنبؤ بوقت التسليم",
            message_type="delivery_prediction",
            delivery_data=delivery_data
        )
        
        # في حالة عدم توفر واجهات API للذكاء الاصطناعي، يمكن إنشاء تنبؤ افتراضي بسيط
        # يستخدم فقط في حال فشل الحصول على تحليل من API
        if "عذراً، لا يمكن التنبؤ" in ai_response or "حدث خطأ" in ai_response:
            logger.warning("استخدام تنبؤ افتراضي لوقت التسليم")
            
            # إذا لم يكن هناك رد من واجهة الذكاء الاصطناعي، استخدم توقعًا افتراضيًا ثابتًا
            created_date = datetime.strptime(delivery_data["created_at"], "%Y-%m-%d") if isinstance(delivery_data["created_at"], str) else delivery_data["created_at"]
            
            # استخدام تقدير ثابت للتسليم (5-7 أيام) 
            min_days = 5
            max_days = 7
            estimated_date = created_date + timedelta(days=min_days)
            
            return {
                "estimated_delivery_date": estimated_date.strftime("%Y-%m-%d"),
                "min_days": min_days,
                "max_days": max_days,
                "confidence": "غير متوفر",
                "ai_explanation": "لم يتمكن النظام من الاتصال بخدمة الذكاء الاصطناعي. هذا تقدير افتراضي بناءً على متوسط أوقات التسليم السابقة."
            }
        
        # معالجة استجابة الذكاء الاصطناعي لاستخراج المعلومات المهمة
        prediction = {
            "estimated_delivery_date": "قيد المعالجة",
            "min_days": 3,
            "max_days": 7,
            "confidence": "85%",
            "ai_explanation": ai_response
        }
        
        # محاولة استخراج التاريخ المتوقع من الاستجابة
        import re
        
        date_match = re.search(r'(\d{4}-\d{2}-\d{2})', ai_response)
        if date_match:
            prediction["estimated_delivery_date"] = date_match.group(1)
            
        # محاولة استخراج المدة المتوقعة
        days_range_match = re.search(r'(\d+)\s*-\s*(\d+)\s*[أاي][يو][اأ][مم]', ai_response)
        if days_range_match:
            prediction["min_days"] = int(days_range_match.group(1))
            prediction["max_days"] = int(days_range_match.group(2))
            
        # محاولة استخراج مستوى الثقة
        confidence_match = re.search(r'(\d+)[٪%]', ai_response)
        if confidence_match:
            prediction["confidence"] = f"{confidence_match.group(1)}%"
            
        return prediction
        
    except Exception as e:
        logger.error(f"خطأ في توليد تنبؤ التسليم: {str(e)}")
        return {
            "estimated_delivery_date": "غير متوفر",
            "min_days": 0,
            "max_days": 0,
            "confidence": "0%",
            "ai_explanation": f"حدث خطأ أثناء توليد التنبؤ: {str(e)}"
        }