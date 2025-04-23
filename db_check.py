"""
سكريبت بسيط للتحقق من محتويات قاعدة البيانات
"""
import sqlite3
import os
import sys

def check_database_tables(db_path):
    """التحقق من جداول قاعدة البيانات وعدد السجلات."""
    if not os.path.exists(db_path):
        print(f"خطأ: لا يمكن العثور على قاعدة البيانات في المسار {db_path}")
        return False
    
    try:
        # الاتصال بقاعدة البيانات
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # الحصول على قائمة الجداول
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
        tables = [table[0] for table in cursor.fetchall() if table[0] != 'sqlite_sequence']
        
        print(f"تم العثور على {len(tables)} جدول في قاعدة البيانات:")
        for table in tables:
            cursor.execute(f"SELECT COUNT(*) FROM {table}")
            count = cursor.fetchone()[0]
            print(f"  - {table}: {count} سجل")
            
            # عرض مثال للبيانات إذا كان هناك سجلات
            if count > 0:
                cursor.execute(f"SELECT * FROM {table} LIMIT 3")
                rows = cursor.fetchall()
                
                # الحصول على أسماء الأعمدة
                column_names = [description[0] for description in cursor.description]
                print(f"    أعمدة: {', '.join(column_names)}")
                print(f"    عينة من البيانات:")
                for row in rows:
                    print(f"      {row}")
        
        conn.close()
        return True
    except Exception as e:
        print(f"خطأ أثناء التحقق من قاعدة البيانات: {e}")
        return False

if __name__ == "__main__":
    db_files = ["shipping_bot.db", "bot.db"]
    success = False
    
    for db_file in db_files:
        print(f"\nالتحقق من قاعدة البيانات: {db_file}")
        if os.path.exists(db_file):
            if check_database_tables(db_file):
                success = True
        else:
            print(f"ملف قاعدة البيانات {db_file} غير موجود")
    
    if not success:
        print("\nفشل التحقق من جميع ملفات قاعدة البيانات المحتملة")
        sys.exit(1)