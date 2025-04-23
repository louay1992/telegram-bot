"""
برنامج لعرض أمثلة لتنسيق أرقام الهواتف
"""
from utils import format_phone_number

def test_phone_examples():
    """
    عرض أمثلة لتنسيق أرقام الهواتف السورية والتركية
    """
    print("=" * 50)
    print("أمثلة لتنسيق أرقام الهواتف السورية والتركية")
    print("=" * 50)
    print("\n--- أرقام هواتف سورية ---")
    
    syrian_numbers = [
        '0947 312 248',     # رقم بصيغة مع مسافات
        '+963947312248',    # رقم مكتمل مع رمز البلد
        '947312248',        # رقم بدون صفر وبدون رمز بلد
        '09 47 31 22 48',   # رقم بمسافات بين كل رقمين
        '0-947-312-248',    # رقم مع شرطات
        'سوريا 0947312248', # رقم مع نص
    ]
    
    for phone in syrian_numbers:
        formatted = format_phone_number(phone)
        print(f"الرقم الأصلي: {phone:<20} | الرقم المنسق: {formatted}")
    
    print("\n--- أرقام هواتف تركية ---")
    
    turkish_numbers = [
        '0535 123 45 67',      # رقم تركي محلي مع مسافات
        '+90 535 123 45 67',   # رقم تركي مع رمز الدولة ومسافات
        '00905351234567',      # رقم تركي بصيغة الاتصال الدولي
        '535 123 45 67',       # رقم تركي بدون الصفر الأول ومسافات
        'تركيا 0535 123 45 67', # رقم تركي مع نص
    ]
    
    for phone in turkish_numbers:
        formatted = format_phone_number(phone)
        print(f"الرقم الأصلي: {phone:<20} | الرقم المنسق: {formatted}")
    
    print("\n--- حالات خاصة ---")
    
    special_cases = [
        '+9639-47312248',     # رقم به خطأ شائع
        '9639-47312248',      # رقم به خطأ شائع بدون +
        '0090 (535) 123 45 67', # رقم تركي مع أقواس
    ]
    
    for phone in special_cases:
        formatted = format_phone_number(phone)
        print(f"الرقم الأصلي: {phone:<20} | الرقم المنسق: {formatted}")

if __name__ == "__main__":
    test_phone_examples()