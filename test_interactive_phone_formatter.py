"""
برنامج تفاعلي بسيط لتجربة وظيفة تنسيق أرقام الهواتف
"""
from utils import format_phone_number

def main():
    """
    برنامج تفاعلي لتجربة وظيفة تنسيق أرقام الهواتف
    """
    print("=" * 50)
    print("مرحباً بك في برنامج تنسيق أرقام الهواتف")
    print("يمكنك إدخال رقم هاتف بأي صيغة وسيقوم البرنامج بتنسيقه")
    print("الأرقام المدعومة: أرقام سورية وتركية")
    print("اكتب 'خروج' للخروج من البرنامج")
    print("=" * 50)
    
    while True:
        phone = input("\nأدخل رقم الهاتف: ")
        
        if phone.lower() in ["خروج", "exit", "quit", "q"]:
            print("شكراً لاستخدامك البرنامج!")
            break
            
        formatted = format_phone_number(phone)
        
        # تحديد نوع الرقم (سوري أو تركي)
        country = "تركي" if formatted.startswith("+90") else "سوري"
        
        print(f"الرقم الأصلي: {phone}")
        print(f"الرقم المنسق: {formatted}")
        print(f"نوع الرقم: {country}")

if __name__ == "__main__":
    main()