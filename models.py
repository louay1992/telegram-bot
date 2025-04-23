"""
نماذج قاعدة البيانات للبوت
"""
from datetime import datetime
from sqlalchemy import Column, String, Boolean, DateTime, Integer, Float, Date, ForeignKey, BigInteger, JSON, Text
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship

Base = declarative_base()

class Notification(Base):
    """
    نموذج بيانات إشعار الشحن
    """
    __tablename__ = 'notifications'
    
    id = Column(String(40), primary_key=True)
    customer_name = Column(String(100), nullable=False)
    phone_number = Column(String(20), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    reminder_hours = Column(Float, default=24)
    reminder_sent = Column(Boolean, default=False)
    has_image = Column(Boolean, default=True)
    # حقول جديدة لميزة تأكيد الاستلام
    is_delivered = Column(Boolean, default=False)
    delivery_confirmed_at = Column(DateTime, nullable=True)
    delivery_confirmed_by = Column(BigInteger, nullable=True)  # معرف المستخدم الذي أكد الاستلام
    has_proof_image = Column(Boolean, default=False)  # هل يوجد صورة دليل استلام؟
    delivery_notes = Column(String(500), nullable=True)  # ملاحظات إضافية حول الاستلام
    is_archived = Column(Boolean, default=False)  # هل تم أرشفة الإشعار؟
    archived_at = Column(DateTime, nullable=True)  # تاريخ الأرشفة
    archived_by = Column(BigInteger, nullable=True)  # معرف المستخدم الذي قام بالأرشفة
    
    def __repr__(self):
        return f"<Notification(id={self.id}, customer={self.customer_name}, phone={self.phone_number}, delivered={self.is_delivered})>"
    
    def to_dict(self):
        """
        تحويل النموذج إلى قاموس
        """
        return {
            'id': self.id,
            'customer_name': self.customer_name,
            'phone_number': self.phone_number,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'reminder_hours': self.reminder_hours,
            'reminder_sent': self.reminder_sent,
            'has_image': self.has_image,
            'is_delivered': self.is_delivered,
            'delivery_confirmed_at': self.delivery_confirmed_at.isoformat() if self.delivery_confirmed_at else None,
            'delivery_confirmed_by': self.delivery_confirmed_by,
            'has_proof_image': self.has_proof_image,
            'delivery_notes': self.delivery_notes,
            'is_archived': self.is_archived,
            'archived_at': self.archived_at.isoformat() if self.archived_at else None,
            'archived_by': self.archived_by
        }


class Admin(Base):
    """
    نموذج بيانات المسؤول
    """
    __tablename__ = 'admins'
    
    user_id = Column(BigInteger, primary_key=True)
    username = Column(String(100))
    is_main_admin = Column(Boolean, default=False)
    added_at = Column(DateTime, default=datetime.utcnow)
    
    def __repr__(self):
        return f"<Admin(user_id={self.user_id}, username={self.username}, is_main_admin={self.is_main_admin})>"


class SearchHistory(Base):
    """
    نموذج بيانات سجل البحث
    """
    __tablename__ = 'search_history'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(BigInteger, nullable=False, index=True)  # معرف المستخدم الذي قام بالبحث
    username = Column(String(100), nullable=True)  # اسم المستخدم (إن وجد)
    search_term = Column(String(100), nullable=False)  # مصطلح البحث
    search_type = Column(String(20), nullable=False)  # نوع البحث (اسم أو رقم هاتف)
    results_count = Column(Integer, default=0)  # عدد النتائج
    notification_ids = Column(JSON, nullable=True)  # معرفات الإشعارات التي تم العثور عليها
    created_at = Column(DateTime, default=datetime.utcnow)  # وقت البحث
    
    def __repr__(self):
        return f"<SearchHistory(id={self.id}, user_id={self.user_id}, term={self.search_term}, count={self.results_count})>"
    
    def to_dict(self):
        """
        تحويل النموذج إلى قاموس
        """
        return {
            'id': self.id,
            'user_id': self.user_id,
            'username': self.username,
            'search_term': self.search_term,
            'search_type': self.search_type,
            'results_count': self.results_count,
            'notification_ids': self.notification_ids,
            'created_at': self.created_at.isoformat() if self.created_at else None
        }


class Statistic(Base):
    """
    نموذج بيانات الإحصائيات
    """
    __tablename__ = 'statistics'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    date = Column(Date, default=func.current_date())
    notifications_created = Column(Integer, default=0)
    notifications_reminded = Column(Integer, default=0)
    messages_sent = Column(Integer, default=0)
    images_processed = Column(Integer, default=0)
    ocr_success = Column(Integer, default=0)
    ocr_failure = Column(Integer, default=0)
    # حقل جديد لتتبع تأكيدات التسليم
    deliveries_confirmed = Column(Integer, default=0)
    # حقل جديد لتتبع عمليات البحث
    search_queries = Column(Integer, default=0)
    
    def __repr__(self):
        return f"<Statistic(date={self.date}, notifications_created={self.notifications_created})>"
        
    def to_dict(self):
        """
        تحويل النموذج إلى قاموس بطريقة آمنة
        """
        try:
            return {
                'id': self.id if hasattr(self, 'id') else 0,
                'date': self.date.isoformat() if hasattr(self, 'date') and self.date else datetime.now().date().isoformat(),
                'notifications_created': self.notifications_created if hasattr(self, 'notifications_created') else 0,
                'notifications_reminded': self.notifications_reminded if hasattr(self, 'notifications_reminded') else 0,
                'messages_sent': self.messages_sent if hasattr(self, 'messages_sent') else 0,
                'images_processed': self.images_processed if hasattr(self, 'images_processed') else 0,
                'ocr_success': self.ocr_success if hasattr(self, 'ocr_success') else 0,
                'ocr_failure': self.ocr_failure if hasattr(self, 'ocr_failure') else 0,
                'deliveries_confirmed': self.deliveries_confirmed if hasattr(self, 'deliveries_confirmed') else 0,
                'search_queries': self.search_queries if hasattr(self, 'search_queries') else 0
            }
        except Exception as e:
            import logging
            logging.error(f"Error in Statistic.to_dict(): {e}")
            # إعادة قاموس بقيم افتراضية في حالة حدوث خطأ
            return {
                'date': datetime.now().date().isoformat(),
                'notifications_created': 0,
                'notifications_reminded': 0,
                'messages_sent': 0,
                'images_processed': 0,
                'ocr_success': 0,
                'ocr_failure': 0,
                'deliveries_confirmed': 0,
                'search_queries': 0
            }


class BotPersonality(Base):
    """
    نموذج بيانات شخصية البوت
    يخزن إعدادات شخصية البوت ومزاجه وطريقة تفاعله مع المستخدمين
    """
    __tablename__ = 'bot_personalities'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    mood_type = Column(String(50), nullable=False)  # رسمي، ودود، احترافي، إلخ
    settings = Column(Text, nullable=False)  # إعدادات الشخصية بتنسيق JSON
    greeting = Column(Text, nullable=False)  # رسالة الترحيب
    farewell = Column(Text, nullable=False)  # رسالة الوداع
    is_active = Column(Boolean, default=False)  # هل هذه الشخصية نشطة حالياً؟
    created_at = Column(DateTime, default=datetime.utcnow)
    created_by = Column(BigInteger, nullable=True)  # معرف المستخدم الذي أنشأ الشخصية
    
    def __repr__(self):
        return f"<BotPersonality(id={self.id}, mood_type={self.mood_type}, is_active={self.is_active})>"
    
    def to_dict(self):
        """
        تحويل النموذج إلى قاموس
        """
        import json
        try:
            settings_dict = json.loads(self.settings)
        except:
            settings_dict = {}
            
        return {
            'id': self.id,
            'mood_type': self.mood_type,
            'settings': settings_dict,
            'greeting': self.greeting,
            'farewell': self.farewell,
            'is_active': self.is_active,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'created_by': self.created_by
        }