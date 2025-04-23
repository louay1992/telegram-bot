"""
سكريبت لترقية قاعدة البيانات وإضافة الأعمدة الجديدة
"""
import logging
import os
import sys
from sqlalchemy import Column, Boolean, DateTime, String, BigInteger, Integer, create_engine, text
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker

# إعداد تسجيل الأحداث
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# الاتصال بقاعدة البيانات
DATABASE_URL = os.environ.get("DATABASE_URL")
if not DATABASE_URL:
    logger.error("متغير DATABASE_URL البيئي غير موجود")
    sys.exit(1)

# إنشاء محرك قاعدة البيانات
engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
session = SessionLocal()

def add_columns_to_notifications_table():
    """إضافة الأعمدة الجديدة المتعلقة بتأكيد الاستلام إلى جدول الإشعارات"""
    try:
        # فحص ما إذا كانت الأعمدة موجودة بالفعل
        result = session.execute(text("SELECT column_name FROM information_schema.columns WHERE table_name='notifications' AND column_name='is_delivered'"))
        if not result.fetchone():
            logger.info("إضافة أعمدة جديدة لجدول الإشعارات للتسليم...")
            
            session.execute(text("""
                ALTER TABLE notifications 
                ADD COLUMN is_delivered BOOLEAN DEFAULT FALSE,
                ADD COLUMN delivery_confirmed_at TIMESTAMP,
                ADD COLUMN delivery_confirmed_by BIGINT,
                ADD COLUMN has_proof_image BOOLEAN DEFAULT FALSE,
                ADD COLUMN delivery_notes VARCHAR(500)
            """))
            
            session.commit()
            logger.info("تمت إضافة الأعمدة الجديدة لجدول الإشعارات بنجاح")
        else:
            logger.info("أعمدة التسليم موجودة بالفعل في جدول الإشعارات")
            
        # التحقق مما إذا كانت أعمدة الأرشفة موجودة بالفعل
        result = session.execute(text("SELECT column_name FROM information_schema.columns WHERE table_name='notifications' AND column_name='is_archived'"))
        if not result.fetchone():
            logger.info("إضافة أعمدة الأرشفة لجدول الإشعارات...")
            
            session.execute(text("""
                ALTER TABLE notifications 
                ADD COLUMN is_archived BOOLEAN DEFAULT FALSE,
                ADD COLUMN archived_at TIMESTAMP,
                ADD COLUMN archived_by BIGINT
            """))
            
            session.commit()
            logger.info("تمت إضافة أعمدة الأرشفة لجدول الإشعارات بنجاح")
        else:
            logger.info("أعمدة الأرشفة موجودة بالفعل في جدول الإشعارات")
        
        return True
    except Exception as e:
        session.rollback()
        logger.error(f"حدث خطأ أثناء إضافة أعمدة جديدة لجدول الإشعارات: {e}")
        return False

def add_column_to_statistics_table():
    """إضافة عمود deliveries_confirmed إلى جدول الإحصائيات"""
    try:
        # فحص ما إذا كان العمود موجوداً بالفعل
        result = session.execute(text("SELECT column_name FROM information_schema.columns WHERE table_name='statistics' AND column_name='deliveries_confirmed'"))
        if not result.fetchone():
            logger.info("إضافة عمود deliveries_confirmed لجدول الإحصائيات...")
            
            session.execute(text("""
                ALTER TABLE statistics 
                ADD COLUMN deliveries_confirmed INTEGER DEFAULT 0
            """))
            
            session.commit()
            logger.info("تمت إضافة العمود الجديد لجدول الإحصائيات بنجاح")
        else:
            logger.info("العمود موجود بالفعل في جدول الإحصائيات")
        
        return True
    except Exception as e:
        session.rollback()
        logger.error(f"حدث خطأ أثناء إضافة عمود جديد لجدول الإحصائيات: {e}")
        return False

def main():
    """الدالة الرئيسية لترقية قاعدة البيانات"""
    logger.info("بدء عملية ترقية قاعدة البيانات...")
    
    # إضافة الأعمدة الجديدة إلى جدول الإشعارات
    notifications_success = add_columns_to_notifications_table()
    
    # إضافة العمود الجديد إلى جدول الإحصائيات
    statistics_success = add_column_to_statistics_table()
    
    if notifications_success and statistics_success:
        logger.info("تمت ترقية قاعدة البيانات بنجاح!")
    else:
        logger.error("فشلت عملية ترقية قاعدة البيانات!")
        sys.exit(1)

if __name__ == "__main__":
    main()