"""
Ultra-simple input validation module that accepts almost anything
"""
import logging

def is_valid_name(name):
    """
    Most basic name validator - only rejects empty strings.
    Accepts any name with at least one non-whitespace character.
    
    Args:
        name (str): The name to validate
    
    Returns:
        bool: Always returns True unless name is empty/None
    """
    # Handle None case explicitly
    if name is None:
        logging.info("Name validation failed: received None")
        return False
        
    # Trim whitespace and check if anything remains
    trimmed = name.strip()
    
    # Log validation result
    if trimmed:
        logging.info(f"Name validation passed: '{name}'")
        return True
    else:
        logging.info(f"Name validation failed: empty or whitespace only")
        return False

def is_valid_phone(phone):
    """
    موّسع للتحقق من صحة رقم الهاتف - يقبل رقم هاتف بأي تنسيق
    يتعامل مع أرقام الهواتف بمختلف الصيغ بما فيها الأرقام التي تحتوي على مسافات
    مثل "0947 312 248" أو "+963 947 312 248"
    
    Args:
        phone (str): رقم الهاتف المراد التحقق منه
    
    Returns:
        tuple: (is_valid, cleaned_phone)
    """
    # Handle None case explicitly
    if phone is None:
        logging.info("Phone validation failed: received None")
        return False, ""
    
    # استخدام دالة تنسيق الهاتف المحسنة
    from utils import format_phone_number
    
    # تنسيق رقم الهاتف
    formatted_phone = format_phone_number(phone)
    
    # التحقق من وجود أرقام في النتيجة (بدون علامة +)
    is_valid = len(formatted_phone) > 1  # أكثر من مجرد علامة +
    
    # تسجيل نتيجة التحقق
    if is_valid:
        logging.info(f"Phone validation passed: '{phone}' -> '{formatted_phone}'")
    else:
        logging.info(f"Phone validation failed: no valid digits in '{phone}'")
    
    return is_valid, formatted_phone