"""
وحدة لوحة المعلومات الإحصائية لبوت إشعارات الشحن
"""
import os
import json
from datetime import datetime, timedelta
import logging
from typing import Dict, List, Any
from flask import Flask, render_template, jsonify

import db_manager

# استخدام تطبيق Flask منفصل للوحة المعلومات
dashboard_app = Flask(__name__)
dashboard_app.secret_key = os.environ.get("FLASK_SECRET_KEY", "shipping_notification_dashboard_secret")


def format_date(date_obj):
    """
    تنسيق كائن التاريخ إلى نص
    """
    if not date_obj:
        return ""
    
    if isinstance(date_obj, str):
        try:
            date_obj = datetime.strptime(date_obj, "%Y-%m-%d").date()
        except ValueError:
            return date_obj
            
    return date_obj.strftime("%Y-%m-%d")


@dashboard_app.route('/')
def index():
    """
    عرض صفحة لوحة المعلومات الرئيسية
    """
    # الإحصائيات الإجمالية
    total_stats = db_manager.get_total_statistics()
    
    # معدل نجاح تحليل الصور
    ocr_success_rate = 0
    if total_stats.get('images_processed', 0) > 0:
        ocr_success_rate = round((total_stats.get('ocr_success', 0) / total_stats.get('images_processed', 1)) * 100)
    
    # الإحصائيات اليومية للأيام السبعة الماضية
    daily_stats = db_manager.get_daily_statistics(7)
    
    # التعامل مع الحالة التي تكون فيها الإحصائيات فارغة
    if not daily_stats:
        daily_stats = []
        daily_dates = []
        daily_notifications = []
        daily_messages = []
        daily_reminders = []
    else:
        daily_stats.reverse()  # عكس الترتيب ليكون من الأقدم إلى الأحدث
        
        # إعداد البيانات للمخططات البيانية
        daily_dates = [format_date(stat.get('date')) for stat in daily_stats]
        daily_notifications = [stat.get('notifications_created', 0) for stat in daily_stats]
        daily_messages = [stat.get('messages_sent', 0) for stat in daily_stats]
        daily_reminders = [stat.get('notifications_reminded', 0) for stat in daily_stats]
    
    # الحصول على أحدث الإشعارات
    notifications = db_manager.get_all_notifications()
    recent_notifications = notifications[:10] if notifications else []  # أحدث 10 إشعارات
    
    # الحصول على المسؤولين
    admins = db_manager.get_all_admins()
    
    # تنسيق التاريخ الحالي
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
    return render_template(
        'index.html',
        total_stats=total_stats,
        ocr_success_rate=ocr_success_rate,
        daily_stats=daily_stats,
        daily_dates=json.dumps(daily_dates),
        daily_notifications=json.dumps(daily_notifications),
        daily_messages=json.dumps(daily_messages),
        daily_reminders=json.dumps(daily_reminders),
        recent_notifications=recent_notifications,
        admins=admins,
        last_update=now
    )


@dashboard_app.route('/api/stats')
def get_stats():
    """
    توفير بيانات الإحصائيات كـ JSON لتحديث لوحة المعلومات ديناميكيًا
    """
    try:
        logging.info("Receiving stats API request")
        
        # الإحصائيات الإجمالية
        total_stats = db_manager.get_total_statistics()
        logging.info(f"Total stats retrieved: {str(total_stats)[:100]}...")
        
        # التأكد من أن total_stats ليس None
        if total_stats is None:
            total_stats = {
                'notifications_created': 0,
                'messages_sent': 0,
                'notifications_reminded': 0,
                'images_processed': 0,
                'ocr_success': 0,
                'ocr_failure': 0
            }
        
        # معدل نجاح تحليل الصور
        ocr_success_rate = 0
        if total_stats.get('images_processed', 0) > 0:
            ocr_success_rate = round((total_stats.get('ocr_success', 0) / total_stats.get('images_processed', 1)) * 100)
        
        # الإحصائيات اليومية للأيام السبعة الماضية
        daily_stats = db_manager.get_daily_statistics(7)
        logging.info(f"Daily stats retrieved, count: {len(daily_stats) if daily_stats else 0}")
        
        # التعامل مع الحالة التي تكون فيها الإحصائيات فارغة
        if not daily_stats:
            daily_stats = []
            daily_dates = []
            daily_notifications = []
            daily_messages = []
            daily_reminders = []
        else:
            daily_stats.reverse()  # عكس الترتيب ليكون من الأقدم إلى الأحدث
            
            # إعداد البيانات للمخططات البيانية بشكل آمن
            daily_dates = []
            daily_notifications = []
            daily_messages = []
            daily_reminders = []
            
            for stat in daily_stats:
                date_str = format_date(stat.get('date')) if stat.get('date') else 'Unknown'
                daily_dates.append(date_str)
                daily_notifications.append(stat.get('notifications_created', 0))
                daily_messages.append(stat.get('messages_sent', 0))
                daily_reminders.append(stat.get('notifications_reminded', 0))
        
        response_data = {
            'total_stats': total_stats,
            'ocr_success_rate': ocr_success_rate,
            'daily_stats': daily_stats,
            'daily_dates': daily_dates,
            'daily_notifications': daily_notifications,
            'daily_messages': daily_messages,
            'daily_reminders': daily_reminders,
            'timestamp': datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        }
        
        logging.info("Stats data prepared successfully")
        return jsonify(response_data)
    except Exception as e:
        logging.error(f"Error retrieving statistics API data: {e}")
        import traceback
        logging.error(traceback.format_exc())
        
        # إرجاع بيانات فارغة آمنة في حالة حدوث خطأ
        return jsonify({
            'total_stats': {
                'notifications_created': 0,
                'messages_sent': 0,
                'notifications_reminded': 0,
                'images_processed': 0,
                'ocr_success': 0,
                'ocr_failure': 0
            },
            'ocr_success_rate': 0,
            'daily_stats': [],
            'daily_dates': [],
            'daily_notifications': [],
            'daily_messages': [],
            'daily_reminders': [],
            'timestamp': datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            'error': str(e)
        })


@dashboard_app.route('/migrate')
def migrate():
    """
    تشغيل عملية نقل البيانات من JSON إلى قاعدة البيانات
    """
    try:
        db_manager.migrate_json_to_db()
        return jsonify({
            'success': True,
            'message': 'تم نقل البيانات بنجاح من ملفات JSON إلى قاعدة البيانات SQL.'
        })
    except Exception as e:
        logging.error(f"Error during migration: {e}")
        return jsonify({
            'success': False,
            'message': f'حدث خطأ أثناء نقل البيانات: {e}'
        })


@dashboard_app.route('/test')
def test():
    """
    صفحة اختبار للتحقق من عمل الخادم
    """
    return jsonify({
        'status': 'ok',
        'message': 'خادم لوحة المعلومات يعمل بشكل صحيح',
        'timestamp': datetime.now().isoformat()
    })


def populate_sample_data():
    """
    إنشاء بيانات عينة للاختبار في قاعدة البيانات إذا كانت فارغة
    """
    try:
        db = db_manager.SessionLocal()
        stats_count = db.query(db_manager.Statistic).count()
        
        if stats_count == 0:
            logging.info("Populating sample statistics data...")
            
            # إضافة إحصائيات للأيام السبعة الماضية
            today = datetime.now().date()
            for i in range(7):
                day = today - timedelta(days=i)
                stat = db_manager.Statistic(
                    date=day,
                    notifications_created=10 - i,
                    notifications_reminded=5 - (i // 2),
                    messages_sent=15 - i,
                    images_processed=12 - i,
                    ocr_success=8 - (i // 2),
                    ocr_failure=4 - (i // 2)
                )
                db.add(stat)
            
            db.commit()
            logging.info("Sample statistics data created successfully.")
    except Exception as e:
        logging.error(f"Error populating sample data: {e}")
    finally:
        db.close()


if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO)
    logging.info("Starting dashboard server...")
    
    # التحقق من توفر بيانات إحصائية أولية
    populate_sample_data()
    
    # تشغيل الخادم
    port = int(os.environ.get("PORT", 5000))
    dashboard_app.run(host='0.0.0.0', port=port, debug=True)