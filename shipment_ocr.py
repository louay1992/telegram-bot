#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
نظام تحليل صور الشحنات باستخدام OCR
يستخدم هذا النظام مكتبات الذكاء الاصطناعي لتحليل صور الشحنات واستخراج البيانات المهمة منها
"""

import re
import logging
import os
from typing import Dict, Any, Optional
import base64

# استيراد مكتبات للتعامل مع الصور
from PIL import Image

# الإعداد الأساسي للـ logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# تأكد من استخدام مكتبات الذكاء الاصطناعي المناسبة
try:
    from ai_assistant import process_image
except ImportError:
    logger.error("لم يتم العثور على وحدة ai_assistant. التأكد من تثبيتها.")


def extract_shipment_data_from_image(image_path: str) -> Dict[str, Any]:
    """
    استخراج بيانات الشحنة من الصورة باستخدام OCR والتعبيرات المنتظمة
    
    Args:
        image_path: مسار الصورة على القرص
        
    Returns:
        قاموس يحتوي على البيانات المستخرجة من الصورة
    """
    try:
        # التأكد من وجود الصورة
        if not os.path.exists(image_path):
            logger.error(f"الصورة غير موجودة في المسار: {image_path}")
            return {"error": "الصورة غير موجودة"}
        
        # تحليل الصورة باستخدام الذكاء الاصطناعي
        context_info = "استخراج معلومات الشحنة: اسم العميل، رقم الهاتف، التاريخ، الوجهة، قيمة الشحنة"
        extracted_text = process_image(image_path, context_info)
        
        # استخراج البيانات باستخدام التعبيرات المنتظمة
        return extract_data_from_text(extracted_text)
        
    except Exception as e:
        logger.error(f"خطأ في معالجة صورة الشحنة: {e}")
        return {"error": f"حدث خطأ أثناء معالجة الصورة: {str(e)}"}


def extract_data_from_text(text: str) -> Dict[str, Any]:
    """
    استخراج البيانات من النص المستخرج من OCR باستخدام تعبيرات منتظمة متقدمة
    
    Args:
        text: النص المستخرج من الصورة
        
    Returns:
        قاموس يحتوي على البيانات المستخرجة
    """
    data = {}
    
    # استبدال بعض الرموز للتسهيل في البحث
    text = text.replace(":", " : ").replace("-", " - ").replace("،", ", ")
    
    # سجل النص المستخرج للتشخيص
    logger.info(f"النص المستخرج من الصورة: {text}")
    
    # البحث عن وصف الفاتورة
    invoice_type_match = re.search(r"شركة\s+(.+?)\s+للخدمات", text)
    if invoice_type_match:
        data['نوع_الفاتورة'] = invoice_type_match.group(1).strip()
        logger.info(f"تم العثور على نوع الفاتورة: {data['نوع_الفاتورة']}")
    
    # البحث عن رقم الفاتورة
    invoice_number_match = re.search(r"(?:رقم\s+الفاتورة|رقم\s+الشحنة|رقم\s+الدفع)?\s*:?\s*([A-Z0-9]{8,})", text)
    if invoice_number_match:
        data['رقم_الفاتورة'] = invoice_number_match.group(1).strip()
        logger.info(f"تم العثور على رقم الفاتورة: {data['رقم_الفاتورة']}")
    
    # اسم الزبون - استخدام أنماط متعددة للعثور على اسم العميل
    name_patterns = [
        r"(?:المرسل إليه|المرسل اليه|اسم العميل|اسم المستلم|المستلم|العميل|الزبون|اسم الزبون)\s*[:\-–—]?\s*([^\n\d]{3,50}?)(?:\s*[-–]\s*|\n|,|$)",
        r"(?:اسم|name)[:\s]\s*([^\n\d]{3,50}?)(?:\n|,|$)",
        r"(?:الاسم)[:\s]\s*([^\n\d]{3,50}?)(?:\n|,|$)",
        r"(?:مستلم|recipient)[:\s]\s*([^\n\d]{3,50}?)(?:\n|,|$)",
        # أنماط مخصصة للمثال المحدد (ابرار ديبر القزق)
        r"(?:المستلم)[:\s]*\s*([ا-ي\s]{5,50}?)(?:\n|,|$)",
        # نمط خاص بفاتورة الشحن الجديدة
        r"اسم\s+العميل.+?(?::|:).+?([ا-ي\s]{3,50})"
    ]
    
    for pattern in name_patterns:
        name_match = re.search(pattern, text, re.IGNORECASE | re.DOTALL)
        if name_match:
            name = name_match.group(1).strip()
            # تنظيف الاسم من أي كلمات غير مرغوبة
            name = re.sub(r'^\s*[:-]\s*', '', name)  # إزالة الرموز في البداية
            if len(name) >= 3 and len(name) <= 50:  # تحقق إضافي من طول الاسم
                data['اسم_الزبون'] = name
                logger.info(f"تم العثور على اسم الزبون: {name}")
                break
    
    # رقم الهاتف - بحث أكثر شمولاً لأرقام الهواتف السورية والتركية
    phone_patterns = [
        r"(?:رقم|هاتف|جوال|موبايل|تلفون|phone|mobile|tel)[:\s]\s*(\+?(?:90|963)?[\s\-]?[0-9]\d[\s\-]?\d{7,10})",
        r"\+?(?:90|963)[\s\-]?[0-9]\d[\s\-]?\d{7,10}",  # أرقام بالكود الدولي
        r"(?:0)[0-9][\s\-]?\d{8}",  # أرقام محلية سورية وتركية
        r"0\d{9,11}",  # رقم مكون من 10-12 أرقام يبدأ بصفر
        r"\d{4}[\s\-]?\d{7}",  # نمط أرقام إضافي
        # نمط خاص لأرقام الهواتف في الفاتورة الجديدة
        r"هاتف\s*:?\s*0\d{9,11}"
    ]
    
    # البحث في النص كامل عن أرقام الهواتف
    all_phones = []
    for pattern in phone_patterns:
        for phone_match in re.finditer(pattern, text, re.IGNORECASE):
            if ":" in pattern:
                phone = phone_match.group(1)
            else:
                if phone_match.group(0).startswith("هاتف"):
                    # استخراج الرقم من النص الذي يبدأ بكلمة هاتف
                    phone_text = phone_match.group(0)
                    phone = re.search(r"0\d{9,11}", phone_text).group(0)
                else:
                    phone = phone_match.group(0)
            
            phone = re.sub(r'[^\d+]', '', phone)  # تنظيف الرقم من أي حروف غير الأرقام والعلامة +
            
            # تأكد من إضافة كود الدولة إذا لم يكن موجودًا
            if phone.startswith('09'):
                phone = '+963' + phone[1:]
            elif phone.startswith('05'):
                phone = '+90' + phone[1:]
            elif phone.startswith('01'):
                phone = '+963' + phone[1:]
            
            all_phones.append(phone)
    
    # اختيار أول رقم هاتف تم العثور عليه
    if all_phones:
        data['رقم_الهاتف'] = all_phones[0]
        logger.info(f"تم العثور على رقم الهاتف: {data['رقم_الهاتف']}")
        
        # تخزين كافة أرقام الهواتف التي تم العثور عليها
        if len(all_phones) > 1:
            data['أرقام_هواتف_إضافية'] = all_phones[1:]
            logger.info(f"أرقام هواتف إضافية: {data['أرقام_هواتف_إضافية']}")
    
    # التاريخ - بحث عن مجموعة متنوعة من صيغ التاريخ
    date_patterns = [
        r"(?:تاريخ الطباعة|التاريخ|تاريخ الإرسال|تاريخ|date)[:\s]\s*(\d{1,4}[\/\-.]\d{1,2}[\/\-.]\d{1,4})",
        r"(\d{1,2}[\/\-.]\d{1,2}[\/\-.]\d{2,4})",  # نمط تاريخ عام
        r"(\d{4}[\/\-.]\d{1,2}[\/\-.]\d{1,2})",  # نمط تاريخ معكوس (السنة أولاً)
        # نمط مخصص للبحث عن تاريخ مثل المثال (2025-04-22)
        r"(20\d{2}[\-\/]\d{1,2}[\-\/]\d{1,2})",
        # نمط للبحث عن تاريخ مع وقت الطباعة
        r"تاريخ\s+وقت\s+الطباعة\s*:?\s*(20\d{2}-\d{2}-\d{2}\s+\d{2}:\d{2}:\d{2})"
    ]
    
    for pattern in date_patterns:
        date_match = re.search(pattern, text)
        if date_match:
            date_str = date_match.group(1) if ":" in pattern else date_match.group(0)
            data['تاريخ_الشحنة'] = date_str.strip()
            logger.info(f"تم العثور على تاريخ الشحنة: {data['تاريخ_الشحنة']}")
            break
    
    # الوجهة - بحث عن الوجهة أو المدينة
    destination_patterns = [
        r"(?:الوجهة|المدينة|منطقة التسليم|وجهة|مدينة|destination|city)[:\s]\s*([^\n\d]{2,20}?)(?:\n|,|$)",
        r"(?:إلى|الى|to)[:\s]\s*([^\n\d]{2,20}?)(?:\n|,|$)",
        # أنماط إضافية للوجهات السورية المشهورة
        r"\b(دمشق|حلب|حمص|حماة|اللاذقية|طرطوس|الرقة|دير الزور|الحسكة|السويداء|درعا|إدلب|القامشلي)\b",
        # نمط خاص للوجهة في فاتورة الشحن الجديدة
        r"مصدر\s*:?\s*([^\n\d]{2,20})"
    ]
    
    for pattern in destination_patterns:
        destination_match = re.search(pattern, text, re.IGNORECASE)
        if destination_match:
            if ":" in pattern:
                destination = destination_match.group(1).strip()
            else:
                destination = destination_match.group(0).strip()
            destination = re.sub(r'^\s*[:-]\s*', '', destination)  # إزالة الرموز في البداية
            data['الوجهة'] = destination
            logger.info(f"تم العثور على الوجهة: {data['الوجهة']}")
            break
    
    # البحث عن نوع العبوة
    package_type_patterns = [
        r"نوع\s+العبوة\s*:?\s*([^\n\r:]+)",
        r"نوع\s*:?\s*([^\n\r:]+)"
    ]
    
    for pattern in package_type_patterns:
        package_type_match = re.search(pattern, text)
        if package_type_match:
            data['نوع_العبوة'] = package_type_match.group(1).strip()
            logger.info(f"تم العثور على نوع العبوة: {data['نوع_العبوة']}")
            break
    
    # البحث عن أجور الشحن والتوصيل
    shipping_cost_patterns = [
        r"(?:أجور|أجر)\s+(?:الشحن|التنزيل)\s*:?\s*(\d[\d,.]+)",
        r"(?:الشحن|التنزيل)\s*:?\s*(\d[\d,.]+)"
    ]
    
    delivery_cost_patterns = [
        r"(?:أجور|أجر)\s+(?:التوصيل|التحميل)\s*:?\s*(\d[\d,.]+)",
        r"(?:التوصيل|التحميل)\s*:?\s*(\d[\d,.]+)"
    ]
    
    for pattern in shipping_cost_patterns:
        shipping_cost_match = re.search(pattern, text)
        if shipping_cost_match:
            data['أجور_الشحن'] = shipping_cost_match.group(1).strip()
            logger.info(f"تم العثور على أجور الشحن: {data['أجور_الشحن']}")
            break
    
    for pattern in delivery_cost_patterns:
        delivery_cost_match = re.search(pattern, text)
        if delivery_cost_match:
            data['أجور_التوصيل'] = delivery_cost_match.group(1).strip()
            logger.info(f"تم العثور على أجور التوصيل: {data['أجور_التوصيل']}")
            break
    
    # قيمة الشحنة - بحث عن المبلغ أو قيمة الشحنة
    value_patterns = [
        r"(?:المجموع|قيمة البضاعة|المبلغ|السعر|التكلفة|قيمة الشحنة|القيمة|قيمة|amount|value|total|price)[:\s]\s*([\d.,]+)(?:\s*(?:ل\.س|ليرة|دولار|يورو|TL|SYP|USD|EUR|₺|\$|€)?)",
        r"(?:ل\.س|ليرة|دولار|يورو|TL|SYP|USD|EUR|₺|\$|€)\s*([\d.,]+)",  # عملة قبل الرقم
        # أنماط متخصصة لقيم الشحن السورية
        r"(\d{3,6}(?:[.,]\d{3})*)(?:\s*(?:ل\.س|ليرة))?",  # مثل 690,000 أو 690000
        r"(\d{3,6})[,\s](\d{3})(?:\s*(?:ل\.س|ليرة))?",  # مثل 690,000 أو 690 000
        # نمط خاص لقيمة الشحنة في فاتورة الشحن الجديدة
        r"المجموع\s*:?\s*(\d[\d,.]+)"
    ]
    
    for pattern in value_patterns:
        value_match = re.search(pattern, text, re.IGNORECASE)
        if value_match:
            if ',' in pattern and value_match.lastindex == 2:
                # إذا كان النمط يتضمن مجموعتين (الآلاف والوحدات)
                value = value_match.group(1) + value_match.group(2)
            else:
                value = value_match.group(1) if ":" in pattern else value_match.group(0)
            
            # تنظيف القيمة
            value = re.sub(r'[^\d.,]', '', value)  # الاحتفاظ بالأرقام والفواصل فقط
            data['قيمة_الشحنة'] = value
            logger.info(f"تم العثور على قيمة الشحنة: {data['قيمة_الشحنة']}")
            break
    
    # إضافة النص الكامل للمرجعية
    data['النص_الكامل'] = text
    
    return data


def verify_extracted_data(data: Dict[str, Any]) -> Dict[str, Any]:
    """
    التحقق من صحة البيانات المستخرجة وإضافة درجة الثقة
    
    Args:
        data: البيانات المستخرجة من الصورة
        
    Returns:
        البيانات المستخرجة مع إضافة درجات الثقة
    """
    verified_data = {}
    confidence = {}
    
    # التحقق من اسم الزبون
    if 'اسم_الزبون' in data:
        name = data['اسم_الزبون']
        if len(name) < 3:
            confidence['اسم_الزبون'] = 0.3
        elif len(name) > 30:
            confidence['اسم_الزبون'] = 0.5
        else:
            confidence['اسم_الزبون'] = 0.9
        verified_data['اسم_الزبون'] = name
    
    # التحقق من رقم الهاتف
    if 'رقم_الهاتف' in data:
        phone = data['رقم_الهاتف']
        # التحقق من صحة رقم الهاتف
        if re.match(r'^\+?(?:963|90)\d{9}$', phone):
            confidence['رقم_الهاتف'] = 0.95
        else:
            confidence['رقم_الهاتف'] = 0.7
        verified_data['رقم_الهاتف'] = phone
    
    # إضافة باقي البيانات مع نسب ثقة افتراضية
    for key in ['تاريخ_الشحنة', 'الوجهة', 'قيمة_الشحنة']:
        if key in data:
            verified_data[key] = data[key]
            confidence[key] = 0.8
    
    # إضافة النص الكامل
    if 'النص_الكامل' in data:
        verified_data['النص_الكامل'] = data['النص_الكامل']
    
    # إضافة درجات الثقة للبيانات
    verified_data['درجات_الثقة'] = confidence
    
    return verified_data


def get_suggested_notification_data(image_path: str) -> Dict[str, Any]:
    """
    استخراج بيانات الإشعار المقترحة من صورة الشحنة
    
    Args:
        image_path: مسار صورة الشحنة
    
    Returns:
        قاموس يحتوي على البيانات المقترحة للإشعار
    """
    # استخراج البيانات من الصورة
    extracted_data = extract_shipment_data_from_image(image_path)
    
    # التحقق من البيانات المستخرجة
    verified_data = verify_extracted_data(extracted_data)
    
    # تحضير البيانات المقترحة للإشعار
    suggested_data = {
        "customer_name": verified_data.get('اسم_الزبون', ''),
        "phone": verified_data.get('رقم_الهاتف', ''),
        "destination": verified_data.get('الوجهة', ''),
        "value": verified_data.get('قيمة_الشحنة', ''),
        "date": verified_data.get('تاريخ_الشحنة', ''),
        "confidence": {
            "name": verified_data.get('درجات_الثقة', {}).get('اسم_الزبون', 0),
            "phone": verified_data.get('درجات_الثقة', {}).get('رقم_الهاتف', 0),
            "destination": verified_data.get('درجات_الثقة', {}).get('الوجهة', 0),
            "value": verified_data.get('درجات_الثقة', {}).get('قيمة_الشحنة', 0),
            "date": verified_data.get('درجات_الثقة', {}).get('تاريخ_الشحنة', 0)
        },
        "extracted_text": verified_data.get('النص_الكامل', '')
    }
    
    logger.info(f"البيانات المستخرجة من الصورة: {suggested_data}")
    
    return suggested_data