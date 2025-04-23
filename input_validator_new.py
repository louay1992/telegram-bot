"""
Simplified input validation module
"""
import logging

def is_valid_name(name):
    """
    Extremely simple name validator that only checks if the name is not empty.
    
    Args:
        name (str): The name to validate
    
    Returns:
        bool: True if the name is not empty, False otherwise
    """
    # Basic null check
    if name is None:
        logging.info("Name is None")
        return False
    
    # Check if name is just whitespace or empty
    if name.strip() == "":
        logging.info("Name is empty or just whitespace")
        return False
    
    logging.info(f"Name '{name}' is valid")
    return True


def is_valid_phone(phone):
    """
    يتحقق من صحة رقم الهاتف ويقوم بتنسيقه بشكل موحد.
    يتعامل مع مختلف صيغ الإدخال بما فيها الأرقام مع مسافات مثل "0947 312 248".
    
    Args:
        phone (str): رقم الهاتف المراد التحقق منه
    
    Returns:
        tuple: (is_valid, formatted_phone)
    """
    # التحقق من القيمة الفارغة
    if phone is None:
        logging.info("Phone is None")
        return False, ""
    
    # استخدام دالة تنسيق الهاتف المحسنة من ملف utils.py
    from utils import format_phone_number
    
    # تنسيق رقم الهاتف
    formatted_phone = format_phone_number(phone)
    
    # التحقق من وجود أرقام في النتيجة (بدون علامة +)
    is_valid = len(formatted_phone) > 1  # أكثر من مجرد علامة +
    
    if not is_valid:
        logging.info(f"Phone number contains no valid digits: '{phone}'")
    else:
        logging.info(f"Phone '{phone}' is formatted as '{formatted_phone}'")
    
    return is_valid, formatted_phone