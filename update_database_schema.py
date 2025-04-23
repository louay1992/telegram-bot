"""
تحديث هيكل قاعدة البيانات لإضافة الأعمدة الجديدة
"""
import os
import logging
from sqlalchemy import create_engine, text

# استخدام URI قاعدة البيانات من المتغيرات البيئية
DATABASE_URL = os.environ.get('DATABASE_URL')

if not DATABASE_URL:
    logging.warning("DATABASE_URL is not set. Using SQLite as fallback.")
    DATABASE_URL = 'sqlite:///shipping_bot.db'

# إنشاء محرك قاعدة البيانات
engine = create_engine(DATABASE_URL)

def add_search_queries_column():
    """
    إضافة عمود search_queries إلى جدول statistics
    """
    try:
        with engine.connect() as conn:
            # التحقق مما إذا كان العمود موجودًا بالفعل
            conn.execute(text("ALTER TABLE statistics ADD COLUMN IF NOT EXISTS search_queries INTEGER DEFAULT 0"))
            conn.commit()
            logging.info("تم إضافة عمود search_queries إلى جدول statistics بنجاح")
            return True
    except Exception as e:
        logging.error(f"خطأ أثناء إضافة عمود search_queries: {e}")
        return False

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    add_search_queries_column()