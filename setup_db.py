#!/usr/bin/env python3
"""
إعداد قاعدة بيانات PostgreSQL
"""
import os
import logging
import psycopg2
from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from datetime import datetime
from models import Base, Notification, Admin, SearchHistory, Statistic

# إعداد التسجيل
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
                    level=logging.INFO)
logger = logging.getLogger(__name__)

# الحصول على إعدادات قاعدة البيانات من متغيرات البيئة
DATABASE_URL = os.environ.get('DATABASE_URL')

if not DATABASE_URL:
    logger.error("متغير البيئة DATABASE_URL غير موجود")
    exit(1)

try:
    # إنشاء محرك قاعدة البيانات
    engine = create_engine(DATABASE_URL)
    
    # إنشاء الجداول
    Base.metadata.create_all(engine)
    logger.info("تم إنشاء جداول قاعدة البيانات بنجاح")
    
    # إنشاء جلسة
    Session = sessionmaker(bind=engine)
    session = Session()
    
    # فحص ما إذا كان هناك مسؤول رئيسي
    admin_count = session.query(Admin).filter_by(is_main_admin=True).count()
    if admin_count == 0:
        logger.info("لا يوجد مسؤول رئيسي، سيتم تعيين أول مستخدم يقوم بتشغيل البوت كمسؤول رئيسي")
    else:
        logger.info(f"يوجد {admin_count} مسؤول رئيسي")
        
    # إنشاء سجل إحصائي لليوم الحالي إذا لم يكن موجودًا
    today = datetime.now().date()
    stat = session.query(Statistic).filter_by(date=today).first()
    if not stat:
        stat = Statistic(date=today)
        session.add(stat)
        session.commit()
        logger.info(f"تم إنشاء سجل إحصائي جديد لليوم {today}")
    else:
        logger.info(f"سجل إحصائي لليوم {today} موجود بالفعل")
    
    session.close()
    logger.info("تم إعداد قاعدة البيانات بنجاح")
    
except Exception as e:
    logger.error(f"حدث خطأ أثناء إعداد قاعدة البيانات: {e}")
    exit(1)