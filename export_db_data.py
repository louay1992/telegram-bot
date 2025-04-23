"""
سكريبت تصدير بيانات قاعدة البيانات إلى ملف JSON

يستخدم هذا السكريبت لتصدير بيانات قاعدة البيانات الحالية إلى ملف JSON 
لاستيرادها لاحقاً في قاعدة بيانات PostgreSQL على Render
"""

import json
import os
import sys
import sqlite3
from datetime import datetime

# تكوين المسارات
DB_PATH = 'shipping_bot.db'
if not os.path.exists(DB_PATH):
    DB_PATH = 'bot.db'  # اسم بديل محتمل لقاعدة البيانات
OUTPUT_FOLDER = 'render_deployment/db_backup'
OUTPUT_FILE = f'db_export_{datetime.now().strftime("%Y%m%d_%H%M%S")}.json'

def create_output_folder():
    """إنشاء مجلد الإخراج إذا لم يكن موجوداً."""
    os.makedirs(OUTPUT_FOLDER, exist_ok=True)

def export_table_to_json(conn, table_name):
    """تصدير جدول إلى كائن JSON."""
    cursor = conn.cursor()
    cursor.execute(f"SELECT * FROM {table_name}")
    
    # الحصول على أسماء الأعمدة
    columns = [description[0] for description in cursor.description]
    
    # جمع البيانات
    rows = []
    for row in cursor.fetchall():
        row_dict = {}
        for i, column in enumerate(columns):
            row_dict[column] = row[i]
        rows.append(row_dict)
    
    return rows

def get_all_tables(conn):
    """الحصول على قائمة بجميع الجداول في قاعدة البيانات."""
    cursor = conn.cursor()
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
    return [table[0] for table in cursor.fetchall() if table[0] != 'sqlite_sequence']

def export_database():
    """تصدير كامل قاعدة البيانات إلى ملف JSON."""
    if not os.path.exists(DB_PATH):
        print(f"خطأ: لا يمكن العثور على قاعدة البيانات في المسار {DB_PATH}")
        sys.exit(1)
    
    # إنشاء مجلد الإخراج
    create_output_folder()
    
    # الاتصال بقاعدة البيانات
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    
    # الحصول على قائمة الجداول
    tables = get_all_tables(conn)
    print(f"تم العثور على {len(tables)} جدول في قاعدة البيانات:")
    for table in tables:
        print(f"  - {table}")
    
    # تصدير كل جدول
    export_data = {}
    for table in tables:
        export_data[table] = export_table_to_json(conn, table)
        print(f"تم تصدير جدول {table} مع {len(export_data[table])} سجل")
    
    # إغلاق الاتصال
    conn.close()
    
    # كتابة البيانات إلى ملف JSON
    output_path = os.path.join(OUTPUT_FOLDER, OUTPUT_FILE)
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(export_data, f, ensure_ascii=False, indent=2)
    
    print(f"\nتم تصدير البيانات بنجاح إلى {output_path}")
    return output_path

if __name__ == "__main__":
    print("بدء تصدير بيانات قاعدة البيانات...")
    export_database()
    print("تم الانتهاء من تصدير البيانات.")