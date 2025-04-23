"""
اختبار تنسيق أرقام الهواتف بصيغ مختلفة
"""

import logging
import input_validator
import input_validator_new
import utils

# إعداد التسجيل
logging.basicConfig(level=logging.INFO, 
                   format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')

# أمثلة على أرقام هواتف بصيغ مختلفة
test_phones = [
    # أرقام سورية بصيغ مختلفة
    "0947312248",           # رقم سوري محلي
    "0947 312 248",         # رقم سوري محلي مع مسافات
    "0947,312,248",         # رقم سوري محلي مع فواصل
    "0947-312-248",         # رقم سوري محلي مع شرطات
    "947312248",            # رقم سوري بدون صفر البداية
    "+963947312248",        # رقم سوري مع رمز البلد
    "+963 947 312 248",     # رقم سوري مع رمز البلد ومسافات
    "963947312248",         # رقم سوري مع رمز البلد بدون +
    "00963947312248",       # رقم سوري مع رمز البلد بصيغة دولية
    "9639473122480",        # رقم سوري مع خطأ شائع (9639 بداية الرقم)
    
    # أرقام تركية بصيغ مختلفة
    "05311234567",          # رقم تركي محلي
    "0531 123 45 67",       # رقم تركي محلي مع مسافات
    "0531-123-45-67",       # رقم تركي محلي مع شرطات 
    "5311234567",           # رقم تركي بدون صفر البداية
    "+905311234567",        # رقم تركي مع رمز البلد
    "+90 531 123 45 67",    # رقم تركي مع رمز البلد ومسافات
    "905311234567",         # رقم تركي مع رمز البلد بدون +
    "00905311234567"        # رقم تركي مع رمز البلد بصيغة دولية
]

def print_header(title):
    """طباعة عنوان بشكل منسق"""
    print("\n" + "=" * 50)
    print(f"  {title}")
    print("=" * 50)

def main():
    print_header("اختبار تنسيق أرقام الهواتف")
    
    # اختبار input_validator.py القديم
    print_header("النتائج باستخدام input_validator.py")
    for original in test_phones:
        print(f"الرقم الأصلي: {original}")
        is_valid, result = input_validator.is_valid_phone(original)
        print(f"النتيجة: {'✓' if is_valid else '✗'} => {result}\n")
    
    # اختبار input_validator_new.py (إذا كان موجوداً)
    try:
        print_header("النتائج باستخدام input_validator_new.py")
        for original in test_phones:
            print(f"الرقم الأصلي: {original}")
            is_valid, result = input_validator_new.is_valid_phone(original)
            print(f"النتيجة: {'✓' if is_valid else '✗'} => {result}\n")
    except:
        print("ملف input_validator_new.py غير موجود أو لا يحتوي على دالة is_valid_phone")
        
    # اختبار دالة format_phone_number مباشرة
    print_header("النتائج باستخدام utils.format_phone_number مباشرة")
    for original in test_phones:
        print(f"الرقم الأصلي: {original}")
        result = utils.format_phone_number(original)
        print(f"النتيجة: {result}\n")

if __name__ == "__main__":
    main()