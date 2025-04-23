#!/usr/bin/env python3
"""
مراقب البوت - يقوم بالتحقق من أن البوت يعمل وإعادة تشغيله إذا توقف.
"""

import os
import sys
import time
import subprocess
import logging
import signal
import datetime

# إعداد التسجيل
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("bot_watchdog.log"),
        logging.StreamHandler()
    ]
)

logger = logging.getLogger("BotWatchdog")

# إعدادات المراقبة محسنة
BOT_SCRIPT = "bot.py"  # اسم سكريبت البوت
CHECK_INTERVAL = 2  # الفاصل الزمني للتحقق (بالثواني) - مخفض لزيادة استجابة النظام للحد الأقصى
MAX_RESTART_ATTEMPTS = 50  # زيادة الحد الأقصى لمحاولات إعادة التشغيل
RESTART_COOLDOWN = 5  # تقليل فترة الانتظار بين محاولات إعادة التشغيل للاستجابة السريعة
HEARTBEAT_FILE = "bot_heartbeat.txt"  # ملف لتسجيل نبضات القلب (heartbeat)
HEARTBEAT_TIMEOUT = 15  # تقليل المدة قبل اعتبار البوت غير مستجيب (بالثواني)
FORCE_RESTART_INTERVAL = 0  # تعطيل إعادة التشغيل الدورية (متزامن مع البوت) - تم التعطيل بناءً على طلب المستخدم
MEMORY_THRESHOLD = 250 * 1024 * 1024  # 250 ميجابايت - الحد الأقصى لاستخدام الذاكرة (متزامن مع البوت)
API_HEALTH_CHECK_INTERVAL = 60  # التحقق من API كل دقيقة
BOT_ACTIVITY_CHECK_INTERVAL = 15  # فحص نشاط البوت كل 15 ثانية
LOG_ROTATION_INTERVAL = 24 * 60 * 60  # تدوير ملفات السجل كل 24 ساعة
AUTO_RECOVERY_TIMEOUT = 30  # وقت الانتظار للاستعادة التلقائية بعد الفشل (بالثواني)
NETWORK_ERROR_RETRY_DELAY = 3  # تأخير إعادة المحاولة عند حدوث أخطاء الشبكة (بالثواني)
LOG_VERBOSE = True  # تسجيل مفصل للمراقبة والأخطاء لتسهيل التشخيص
REDUNDANT_HEARTBEAT = True  # استخدم نظام نبضات قلب احتياطي إضافي لضمان استمرارية الكشف

# متغيرات للتتبع
bot_process = None
restart_count = 0
last_restart_time = None
consecutive_failures = 0  # عدد مرات الفشل المتتالية
bot_start_time = None  # وقت بدء تشغيل البوت الأخير (لإعادة التشغيل الدورية)
restart_log = []  # سجل إعادة التشغيل (للتشخيص)
max_restart_log_entries = 100  # عدد أقصى من سجلات إعادة التشغيل للاحتفاظ بها

# إنشاء ملف نبضات القلب أو تحديثه إذا كان موجودًا
def update_heartbeat_file():
    """تحديث ملف نبضات القلب بالوقت الحالي"""
    try:
        with open(HEARTBEAT_FILE, 'w') as f:
            f.write(str(datetime.datetime.now().timestamp()))
        return True
    except Exception as e:
        logger.error(f"فشل في تحديث ملف نبضات القلب: {e}")
        return False

# التحقق من وجود ملف علامة الإيقاف عمداً (مستخدم في أمر /restart)
def check_shutdown_marker():
    """تحقق من وجود ملف علامة إيقاف"""
    shutdown_marker = "bot_shutdown_marker"
    watchdog_ping = "watchdog_ping"
    restart_in_progress = "restart_in_progress"
    
    # التحقق من وجود ملف "ping" من البوت
    if os.path.exists(watchdog_ping):
        try:
            logger.info("🔄 تم العثور على ملف ping من البوت، سيتم حذفه")
            os.remove(watchdog_ping)
        except Exception as e:
            logger.error(f"خطأ في حذف ملف ping: {e}")
    
    # التحقق من ملف علامة الإيقاف الرئيسي
    if os.path.exists(shutdown_marker):
        try:
            # الحصول على وقت إنشاء الملف
            with open(shutdown_marker, 'r') as f:
                try:
                    marker_time = float(f.read().strip())
                except ValueError:
                    logger.error("قيمة غير صالحة في ملف علامة الإيقاف")
                    marker_time = 0
            
            # حساب الوقت منذ إنشاء الملف
            now = datetime.datetime.now().timestamp()
            time_diff = now - marker_time
            
            # زيادة الفترة الزمنية لاكتشاف علامة الإيقاف إلى 300 ثانية (5 دقائق) للتأكد من اكتشافها
            if time_diff < 300:
                logger.info(f"🔄 تم العثور على ملف علامة إيقاف حديث (منذ {time_diff:.1f} ثانية)")
                
                # إنشاء ملف مؤقت لتتبع عملية إعادة التشغيل
                try:
                    with open(restart_in_progress, "w") as f:
                        f.write(str(now))
                    logger.info("🔄 تم إنشاء ملف 'restart_in_progress' لتتبع عملية إعادة التشغيل")
                except Exception as restart_error:
                    logger.error(f"🔄 خطأ في إنشاء ملف تتبع إعادة التشغيل: {restart_error}")
                
                # تأخير بسيط قبل حذف الملف للتأكد من اكتمال القراءة
                time.sleep(0.5)
                
                # حذف ملف علامة الإيقاف بعد معالجته
                try:
                    os.remove(shutdown_marker)
                    logger.info("🔄 تم حذف ملف علامة الإيقاف بنجاح")
                except Exception as remove_error:
                    logger.error(f"🔄 خطأ في حذف ملف علامة الإيقاف: {remove_error}")
                
                return True
            else:
                # ملف قديم، حذفه والمتابعة
                logger.info(f"تم العثور على ملف علامة إيقاف قديم (منذ {time_diff:.1f} ثانية)، سيتم حذفه")
                os.remove(shutdown_marker)
        except Exception as e:
            logger.error(f"خطأ في معالجة ملف علامة الإيقاف: {e}")
            # حذف الملف الخاطئ
            try:
                os.remove(shutdown_marker)
            except:
                pass
    
    # التحقق من ملف عملية إعادة التشغيل الجارية
    if os.path.exists(restart_in_progress):
        try:
            # الحصول على وقت بدء عملية إعادة التشغيل
            with open(restart_in_progress, 'r') as f:
                try:
                    restart_time = float(f.read().strip())
                except ValueError:
                    logger.error("قيمة غير صالحة في ملف تتبع إعادة التشغيل")
                    restart_time = 0
            
            # حساب الوقت منذ بدء عملية إعادة التشغيل
            now = datetime.datetime.now().timestamp()
            restart_diff = now - restart_time
            
            # إذا كانت عملية إعادة التشغيل بدأت خلال آخر 120 ثانية (دقيقتين)
            if restart_diff < 120:
                logger.info(f"🔄 عملية إعادة التشغيل جارية منذ {restart_diff:.1f} ثانية")
                return True
            else:
                # مر وقت طويل، يبدو أن هناك مشكلة في إعادة التشغيل
                logger.warning(f"⚠️ استمرت عملية إعادة التشغيل لفترة طويلة ({restart_diff:.1f} ثانية)، سيتم إلغاؤها")
                os.remove(restart_in_progress)
        except Exception as restart_error:
            logger.error(f"خطأ في معالجة ملف تتبع إعادة التشغيل: {restart_error}")
            # حذف الملف الخاطئ
            try:
                os.remove(restart_in_progress)
            except:
                pass
    
    return False

# التحقق من نبضات القلب
def check_heartbeat():
    """التحقق مما إذا كان البوت يستجيب من خلال ملف نبضات القلب"""
    try:
        if not os.path.exists(HEARTBEAT_FILE):
            logger.warning("ملف نبضات القلب غير موجود، البوت قد يكون غير نشط")
            return False
            
        with open(HEARTBEAT_FILE, 'r') as f:
            try:
                last_heartbeat = float(f.read().strip())
                now = datetime.datetime.now().timestamp()
                time_diff = now - last_heartbeat
                
                if time_diff > HEARTBEAT_TIMEOUT:
                    logger.warning(f"آخر نبضة قلب كانت منذ {time_diff:.1f} ثانية، وهو أكثر من الحد المسموح به ({HEARTBEAT_TIMEOUT} ثانية)")
                    return False
                    
                return True
            except ValueError:
                logger.error("تنسيق ملف نبضات القلب غير صالح")
                return False
    except Exception as e:
        logger.error(f"فشل في التحقق من ملف نبضات القلب: {e}")
        return False


def is_process_running(process):
    """التحقق مما إذا كانت العملية لا تزال قيد التشغيل."""
    if process is None:
        return False
    
    return process.poll() is None


def notify_admin_about_restart_failure(reason, attempt, error=None):
    """
    إرسال إشعار للمسؤول عند فشل إعادة تشغيل البوت بشكل متكرر.
    
    Args:
        reason (str): سبب إعادة التشغيل
        attempt (int): رقم محاولة إعادة التشغيل
        error (str): رسالة الخطأ إن وجدت
    """
    try:
        # تسجيل محاولة إرسال الإشعار
        logger.info(f"محاولة إرسال إشعار للمسؤول عن فشل إعادة التشغيل (محاولة {attempt})")
        
        # الحصول على قائمة المسؤولين من قاعدة البيانات
        try:
            # استخدام sqlite3 مباشرة بدلاً من مدير قاعدة البيانات (لتجنب الاعتماد على وحدات البوت)
            import sqlite3
            import os
            
            db_file = "shipping_bot.db"
            if not os.path.exists(db_file):
                logger.warning(f"قاعدة البيانات غير موجودة: {db_file}")
                return
                
            # الاتصال بقاعدة البيانات
            conn = sqlite3.connect(db_file)
            cursor = conn.cursor()
            
            # الحصول على معرف المسؤول الرئيسي
            cursor.execute("SELECT user_id FROM admins LIMIT 1")
            admin_result = cursor.fetchone()
            
            if not admin_result:
                logger.warning("لا يوجد مسؤولين في قاعدة البيانات")
                conn.close()
                return
                
            admin_id = admin_result[0]
            
            # محاولة إرسال إشعار عبر WhatsApp (إذا أمكن)
            # هذا سيعمل فقط إذا كانت خدمة UltraMsg مفعلة
            try:
                # الحصول على رقم هاتف المسؤول (إذا كان متاحاً)
                try:
                    from ultramsg_service import send_admin_alert
                    
                    # تجهيز رسالة الإشعار
                    message = f"⚠️ *تنبيه هام: فشل إعادة تشغيل البوت*\n\n"
                    message += f"• محاولة رقم: {attempt}\n"
                    message += f"• السبب: {reason}\n"
                    
                    if error:
                        message += f"• الخطأ: {error}\n"
                        
                    message += f"• الوقت: {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n"
                    message += "يرجى التحقق من حالة البوت ومعالجة المشكلة يدوياً."
                    
                    # إرسال الإشعار
                    send_admin_alert(message)
                    logger.info("تم إرسال إشعار للمسؤول عبر WhatsApp")
                    
                except ImportError:
                    logger.warning("وحدة ultramsg_service غير متاحة، لم يتم إرسال إشعار")
                except Exception as msg_error:
                    logger.error(f"خطأ في إرسال إشعار WhatsApp: {msg_error}")
            
            finally:
                # إغلاق الاتصال بقاعدة البيانات
                conn.close()
                
        except Exception as db_error:
            logger.error(f"خطأ في الوصول لقاعدة البيانات: {db_error}")
            
    except Exception as e:
        logger.error(f"خطأ في إرسال إشعار للمسؤول: {e}")


def log_restart_attempt(reason, success=False, error=None):
    """
    تسجيل محاولة إعادة تشغيل البوت في سجل المحاولات.
    
    Args:
        reason (str): سبب إعادة التشغيل
        success (bool): هل نجحت محاولة إعادة التشغيل
        error (str): رسالة الخطأ إن وجدت
    """
    global restart_log, max_restart_log_entries, restart_count, consecutive_failures
    
    # إنشاء سجل محاولة إعادة التشغيل
    restart_entry = {
        "timestamp": datetime.datetime.now().isoformat(),
        "attempt": restart_count,
        "reason": reason,
        "success": success,
        "error": str(error) if error else None
    }
    
    # إضافة السجل إلى القائمة
    restart_log.append(restart_entry)
    
    # التأكد من أن عدد السجلات لا يتجاوز الحد الأقصى
    if len(restart_log) > max_restart_log_entries:
        restart_log = restart_log[-max_restart_log_entries:]
    
    # حفظ سجل إعادة التشغيل في ملف
    try:
        with open("restart_log.json", "w", encoding="utf-8") as f:
            import json
            json.dump(restart_log, f, ensure_ascii=False, indent=2)
    except Exception as e:
        logger.error(f"خطأ في حفظ سجل إعادة التشغيل: {e}")
    
    # إرسال إشعار للمسؤول في حالة فشل إعادة التشغيل لعدة مرات متتالية
    if not success:
        consecutive_failures += 1
        
        # بعد عدة محاولات فاشلة متتالية، أرسل إشعاراً للمسؤول
        if consecutive_failures >= 5:
            logger.warning(f"تنبيه: فشل متتالي في إعادة التشغيل ({consecutive_failures} محاولات)")
            # إرسال إشعار للمسؤول
            notify_admin_about_restart_failure(reason, restart_count, error)
    else:
        # إعادة تعيين عداد الفشل المتتالي في حالة النجاح
        consecutive_failures = 0


def start_bot():
    """بدء تشغيل البوت وإرجاع معرف العملية."""
    global restart_count, last_restart_time, bot_start_time
    
    # تحديث وقت إعادة التشغيل
    now = datetime.datetime.now()
    
    # التحقق من فترة الراحة بين إعادة التشغيل المتكرر
    if last_restart_time is not None:
        elapsed = (now - last_restart_time).total_seconds()
        if elapsed < RESTART_COOLDOWN:
            logger.info(f"نظام المراقبة في فترة الراحة. مر {elapsed:.0f} ثانية منذ آخر إعادة تشغيل.")
            log_restart_attempt("فترة راحة", success=False, error="محاولة متكررة خلال فترة الراحة")
            return None
    
    last_restart_time = now
    bot_start_time = now  # تحديث وقت بدء تشغيل البوت للتحقق من الإعادة الدورية
    restart_count += 1
    
    try:
        logger.info(f"🔁 بدء تشغيل البوت (محاولة رقم {restart_count})...")
        process = subprocess.Popen([sys.executable, BOT_SCRIPT],
                                  stdout=subprocess.PIPE,
                                  stderr=subprocess.PIPE,
                                  text=True)
        pid = process.pid
        logger.info(f"✅ تم بدء تشغيل البوت بنجاح، معرف العملية: {pid}")
        
        # تسجيل محاولة إعادة التشغيل الناجحة
        log_restart_attempt("طلب إعادة تشغيل عادي", success=True)
        
        return process
    except Exception as e:
        error_msg = str(e)
        logger.error(f"❌ فشل في بدء تشغيل البوت: {error_msg}")
        
        # تسجيل محاولة إعادة التشغيل الفاشلة
        log_restart_attempt("طلب إعادة تشغيل عادي", success=False, error=error_msg)
        
        return None


def stop_bot(process):
    """إيقاف البوت بأمان."""
    if process is None:
        return
    
    logger.info(f"إيقاف البوت (معرف العملية: {process.pid})...")
    
    try:
        # محاولة إيقاف العملية بأمان
        process.terminate()
        
        # الانتظار حتى 5 ثواني للإنهاء
        for _ in range(5):
            if process.poll() is not None:
                break
            time.sleep(1)
            
        # إذا كانت العملية لا تزال قيد التشغيل، أوقفها بالقوة
        if process.poll() is None:
            logger.warning("البوت لم يستجب للإيقاف العادي، جاري إيقافه بالقوة...")
            process.kill()
            
        logger.info("تم إيقاف البوت بنجاح")
    except Exception as e:
        logger.error(f"حدث خطأ أثناء محاولة إيقاف البوت: {e}")


def handle_exit(signum, frame):
    """معالج الإشارات للخروج الآمن."""
    logger.info("تم استلام إشارة للخروج، جاري إيقاف البوت...")
    if bot_process is not None:
        stop_bot(bot_process)
    sys.exit(0)


def check_memory_usage(process):
    """
    مراقبة استخدام الذاكرة للعملية المعطاة.
    
    Args:
        process: عملية البوت.
        
    Returns:
        (bool): True إذا كان استخدام الذاكرة ضمن الحدود المسموح بها، False خلاف ذلك.
    """
    if process is None:
        return True  # لا يمكن فحص الذاكرة لعملية غير موجودة
    
    try:
        import psutil
        p = psutil.Process(process.pid)
        memory_usage = p.memory_info().rss
        
        logger.debug(f"استخدام الذاكرة للبوت: {memory_usage / (1024 * 1024):.2f} MB")
        
        if memory_usage > MEMORY_THRESHOLD:
            logger.warning(f"تجاوز استخدام الذاكرة الحد المسموح به! ({memory_usage / (1024 * 1024):.2f} MB > {MEMORY_THRESHOLD / (1024 * 1024):.2f} MB)")
            return False
        
        return True
    except ImportError:
        logger.warning("لم يتم العثور على وحدة psutil. لن يتم فحص استخدام الذاكرة.")
        return True
    except Exception as e:
        logger.error(f"خطأ أثناء فحص استخدام الذاكرة: {e}")
        return True  # نفترض أن استخدام الذاكرة جيد في حالة حدوث خطأ


def check_network_connection():
    """
    التحقق من اتصال الشبكة بخادم تيليجرام.
    
    Returns:
        (bool): True إذا كان الاتصال جيدًا، False خلاف ذلك.
    """
    try:
        import socket
        socket.create_connection(("api.telegram.org", 443), timeout=10)
        return True
    except Exception as e:
        logger.error(f"فشل في الاتصال بـ api.telegram.org: {e}")
        return False


def check_api_health():
    """
    التحقق من صحة API تيليجرام.
    
    Returns:
        (bool): True إذا كان API يعمل بشكل جيد، False خلاف ذلك.
    """
    try:
        import requests
        response = requests.get("https://api.telegram.org", timeout=10)
        return response.status_code == 200
    except Exception as e:
        logger.error(f"فشل في التحقق من صحة API تيليجرام: {e}")
        return False


def check_bot_restart_signals():
    """التحقق من إشارات إعادة تشغيل البوت."""
    global bot_process, restart_count, consecutive_failures, bot_start_time
    
    # التحقق من وجود ملف watchdog_ping (يتم إنشاؤه من قبل البوت عند إرسال أمر /restart)
    if os.path.exists("watchdog_ping"):
        try:
            logger.info("🔄 تم العثور على ملف ping سريع من البوت، سيتم حذفه والتحقق من علامات إعادة التشغيل")
            os.remove("watchdog_ping")
            # تأكد من فحص علامة الإيقاف فوراً
            force_check_shutdown = True
        except Exception as e:
            logger.error(f"خطأ في معالجة ملف ping: {e}")
            force_check_shutdown = False
    else:
        force_check_shutdown = False
    
    # التحقق مما إذا كان البوت قد تم إيقافه عمداً (من خلال أمر /restart)
    restart_initiated = check_shutdown_marker()
    
    # إذا وجدنا ملف Ping، نفرض إعادة تشغيل حتى لو لم نجد علامة الإيقاف
    if force_check_shutdown and not restart_initiated:
        logger.info("🔄 تم فرض إعادة التشغيل من ملف Ping حتى بدون علامة إيقاف")
        restart_initiated = True
        
    if restart_initiated:
        logger.info("🔄 تم اكتشاف أن البوت يحتاج إلى إعادة تشغيل (بواسطة أمر /restart أو ping).")
        
        # تسجيل عملية إعادة التشغيل
        restart_reason = "أمر /restart يدوي"
        
        # إيقاف العملية الحالية إذا كانت نشطة
        if bot_process is not None and is_process_running(bot_process):
            logger.info(f"🔄 البوت ما زال يعمل (PID: {bot_process.pid})، سيتم إيقافه...")
            stop_bot(bot_process)
        else:
            logger.info("🔄 لم يتم العثور على عملية بوت نشطة")
            # إعادة تعيين متغير bot_process
            bot_process = None
        
        # إعادة تعيين متغيرات التتبع
        restart_count = max(0, restart_count - 1)  # تقليل عداد إعادة التشغيل
        consecutive_failures = max(0, consecutive_failures - 1)  # تقليل عداد الفشل المتتالي
        
        # تأخير قصير قبل إعادة التشغيل (للتأكد من تحرر الموارد)
        time.sleep(2)
        
        # إعادة تشغيل البوت
        logger.info("🔄 إعادة تشغيل البوت بعد أمر /restart...")
        bot_process = start_bot()
        
        if bot_process is None:
            logger.error("❌ فشل في إعادة تشغيل البوت بعد أمر /restart!")
            log_restart_attempt(restart_reason, success=False, error="فشل بدء عملية البوت")
        else:
            logger.info(f"✅ تم إعادة تشغيل البوت بنجاح! (PID الجديد: {bot_process.pid})")
            # تحديث ملف نبضات القلب يدوياً
            update_heartbeat_file()
            log_restart_attempt(restart_reason, success=True)
            
            # تنظيف جميع ملفات علامات الإيقاف وإعادة التشغيل بعد النجاح
            cleanup_restart_markers()
            
def cleanup_restart_markers():
    """
    تنظيف جميع ملفات علامات الإيقاف وإعادة التشغيل.
    يتم استدعاء هذه الوظيفة بعد إعادة تشغيل البوت بنجاح.
    """
    marker_files = [
        "bot_shutdown_marker", 
        "watchdog_ping", 
        "restart_in_progress", 
        "restart_requested.log"
    ]
    
    for marker_file in marker_files:
        if os.path.exists(marker_file):
            try:
                os.remove(marker_file)
                logger.info(f"🧹 تم حذف ملف العلامة: {marker_file}")
            except Exception as e:
                logger.error(f"❌ خطأ في حذف ملف العلامة {marker_file}: {e}")


def check_bot_health():
    """التحقق من صحة البوت وإعادة تشغيله إذا لزم الأمر."""
    global bot_process, restart_count, consecutive_failures, bot_start_time
    
    # التحقق من عملية البوت
    process_alive = is_process_running(bot_process)
    
    # الطريقة 2: التحقق من ملف نبضات القلب
    heartbeat_alive = check_heartbeat()
    
    # الطريقة 3: التحقق من استخدام الذاكرة
    memory_ok = check_memory_usage(bot_process) if process_alive else True
    
    # الطريقة 4: التحقق من اتصال الشبكة (مرة كل 10 عمليات تحقق)
    network_check = (restart_count % 10 == 0)
    network_ok = check_network_connection() if network_check else True
    
    # تسجيل الحالة للتشخيص
    logger.debug(f"حالة البوت: Process={process_alive}, Heartbeat={heartbeat_alive}, Memory={memory_ok}, Network={network_ok}")
    
    # التحقق من الحاجة إلى إعادة تشغيل دورية
    force_restart = False
    now = datetime.datetime.now()
    if bot_start_time is not None:
        uptime = (now - bot_start_time).total_seconds()
        # إذا مر وقت أطول من الفترة المحددة، قم بإعادة تشغيل البوت بغض النظر عن حالته
        if uptime > FORCE_RESTART_INTERVAL:
            logger.info(f"البوت يعمل منذ {uptime/3600:.1f} ساعة، سيتم إعادة تشغيله دوريًا للحفاظ على الاستقرار.")
            force_restart = True
            # إذا كانت العملية تعمل، قم بإيقافها أولاً
            if process_alive:
                stop_bot(bot_process)
    
    # إذا كان البوت لا يعمل أو لم يستجب أو نحتاج إلى إعادة تشغيل دورية، قم بإعادة تشغيله
    if not process_alive or not heartbeat_alive or not memory_ok or not network_ok or force_restart:
        restart_reason = "تم اكتشاف مشكلة: "
        if not process_alive:
            restart_reason += "العملية متوقفة. "
        if not heartbeat_alive:
            restart_reason += "نبضات القلب متوقفة. "
        if not memory_ok:
            restart_reason += "استخدام الذاكرة مرتفع جداً. "
        if not network_ok:
            restart_reason += "مشكلة في اتصال الشبكة. "
        if force_restart:
            restart_reason += "إعادة تشغيل دورية مجدولة. "
        
        logger.warning(restart_reason)
        
        if not force_restart:  # لا داعي لزيادة عداد الأخطاء المتتالية في حالة إعادة التشغيل الدورية
            consecutive_failures += 1
            logger.warning(f"محاولة إعادة التشغيل رقم {consecutive_failures}")
        
        # تنظيف وإعادة تشغيل
        if process_alive:
            stop_bot(bot_process)
        
        # إعادة تعيين ملف نبضات القلب
        update_heartbeat_file()
        
        # تعزيز الاتصال إذا كانت هناك مشكلة في الشبكة
        if not network_ok:
            logger.info("جاري محاولة إعادة الاتصال بالشبكة...")
            try:
                import socket
                socket.getaddrinfo('api.telegram.org', 443)
            except Exception as e:
                logger.error(f"فشل في إعادة حل مشكلة DNS: {e}")
        
        # التحقق من عدد محاولات إعادة التشغيل (لا ينطبق على إعادة التشغيل الدورية)
        if not force_restart and restart_count >= MAX_RESTART_ATTEMPTS:
            logger.error(f"تم الوصول إلى الحد الأقصى لمحاولات إعادة التشغيل ({MAX_RESTART_ATTEMPTS}).")
            logger.info(f"سيتم الانتظار لمدة {RESTART_COOLDOWN} ثانية قبل المحاولة مرة أخرى.")
            time.sleep(RESTART_COOLDOWN)
            restart_count = 0
        
        # جدولة إعادة تشغيل ثانية إذا فشلت المحاولة السابقة عدة مرات
        retry_count = 0
        max_retry = 3
        
        # إعادة التشغيل مع المحاولات المتعددة
        while retry_count < max_retry:
            # إعادة التشغيل    
            bot_process = start_bot()
            
            if bot_process is None:
                error_msg = f"فشل في إعادة تشغيل البوت! (محاولة {retry_count + 1}/{max_retry})"
                logger.error(error_msg)
                log_restart_attempt(restart_reason, success=False, error=error_msg)
                retry_count += 1
                time.sleep(5)  # انتظر 5 ثوانٍ قبل المحاولة مرة أخرى
            else:
                # تم النجاح
                if force_restart:
                    logger.info("✅ تم إعادة تشغيل البوت دوريًا بنجاح!")
                    log_restart_attempt("إعادة تشغيل دورية مجدولة", success=True)
                else:
                    logger.info(f"✅ تم إعادة تشغيل البوت بنجاح! (محاولة {retry_count + 1}/{max_retry})")
                    log_restart_attempt(restart_reason, success=True)
                # تحديث ملف نبضات القلب بعد إعادة التشغيل
                update_heartbeat_file()
                break
        
        # التحقق من نجاح جميع المحاولات
        if retry_count == max_retry:
            logger.critical("‼️ فشل في إعادة تشغيل البوت بعد محاولات متعددة! سيتم محاولة إعادة الاتصال بالشبكة...")
            # محاولة إعادة الاتصال بالشبكة
            try:
                import requests
                requests.get("https://api.telegram.org", timeout=5)
                logger.info("✅ تم إعادة الاتصال بالشبكة بنجاح، سيتم المحاولة مرة أخرى في الدورة التالية.")
            except Exception as e:
                logger.error(f"❌ فشل في إعادة الاتصال بالشبكة: {e}")
                
            # إعادة تعيين عداد المحاولات المتتالية
            restart_count = 0
    else:
        # إذا كان البوت يعمل ويستجيب، أعد تعيين العدادات
        if consecutive_failures > 0:
            logger.info(f"✅ البوت يعمل بشكل جيد الآن بعد {consecutive_failures} محاولة فاشلة.")
            consecutive_failures = 0
            
        if restart_count > 0 and last_restart_time is not None:
            time_diff = (now - last_restart_time).total_seconds()
            if time_diff > RESTART_COOLDOWN:
                restart_count = 0
                logger.info("🟢 تم إعادة تعيين عداد إعادة التشغيل، البوت مستقر.")


def rotate_log_files():
    """
    تدوير ملفات السجلات لمنع نموها بشكل كبير جداً.
    """
    try:
        log_file = "bot_watchdog.log"
        
        # التحقق من وجود الملف
        if not os.path.exists(log_file):
            return
            
        # التحقق من حجم الملف (1 ميجابايت)
        max_size = 1 * 1024 * 1024
        current_size = os.path.getsize(log_file)
        
        if current_size < max_size:
            return
            
        # إنشاء ملف احتياطي
        backup_file = f"bot_watchdog_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}.log"
        
        # نسخ الملف القديم وإنشاء ملف جديد
        try:
            with open(log_file, 'r') as src, open(backup_file, 'w') as dst:
                dst.write(src.read())
                
            # مسح محتوى الملف الأصلي
            with open(log_file, 'w') as f:
                f.write(f"-- بدء سجل جديد: {datetime.datetime.now()} --\n")
                
            # الاحتفاظ بآخر 5 ملفات سجل فقط
            backup_files = [f for f in os.listdir('.') if f.startswith('bot_watchdog_') and f.endswith('.log')]
            backup_files.sort(reverse=True)
            
            # حذف الملفات القديمة
            for old_file in backup_files[5:]:
                try:
                    os.remove(old_file)
                except Exception as e:
                    logger.error(f"خطأ في حذف ملف السجل القديم {old_file}: {e}")
                    
            logger.info(f"تم تدوير ملف السجل بنجاح، تم إنشاء نسخة احتياطية: {backup_file}")
        except Exception as e:
            logger.error(f"خطأ في تدوير ملف السجل: {e}")
    except Exception as e:
        logger.error(f"خطأ في وظيفة تدوير ملف السجل: {e}")


def install_required_packages():
    """
    تثبيت الحزم المطلوبة إذا لم تكن موجودة.
    """
    try:
        missing_packages = []
        
        # التحقق من وجود psutil
        try:
            import psutil
        except ImportError:
            missing_packages.append("psutil")
            
        # التحقق من وجود requests
        try:
            import requests
        except ImportError:
            missing_packages.append("requests")
            
        # تثبيت الحزم المفقودة
        if missing_packages:
            logger.info(f"جاري تثبيت الحزم المطلوبة: {', '.join(missing_packages)}")
            
            try:
                # استخدام subprocess لتثبيت الحزم بدلاً من استخدام pip مباشرة
                import subprocess
                for package in missing_packages:
                    try:
                        logger.info(f"جاري تثبيت {package}...")
                        subprocess.check_call([sys.executable, "-m", "pip", "install", package])
                        logger.info(f"تم تثبيت {package} بنجاح")
                    except Exception as e:
                        logger.error(f"خطأ في تثبيت {package}: {e}")
            except Exception as pip_error:
                logger.error(f"خطأ في استخدام pip: {pip_error}")
        else:
            logger.debug("جميع الحزم المطلوبة مثبتة بالفعل")
    except Exception as e:
        logger.error(f"خطأ في تثبيت الحزم المطلوبة: {e}")


def create_watchdog_service_file():
    """
    إنشاء ملف خدمة لتشغيل watchdog تلقائياً عند إعادة تشغيل النظام.
    """
    try:
        # مسار ملف الخدمة
        service_file = "bot_watchdog.service"
        
        # التحقق من نوع النظام (هذه الوظيفة تعمل فقط على نظام لينكس مع systemd)
        if not os.path.exists("/bin/systemctl"):
            logger.info("نظام systemd غير موجود، لن يتم إنشاء ملف خدمة.")
            return
            
        # محتوى ملف الخدمة
        current_dir = os.getcwd()
        service_content = f"""[Unit]
Description=Telegram Bot Watchdog Service
After=network.target

[Service]
Type=simple
User={os.getenv('USER', 'root')}
WorkingDirectory={current_dir}
ExecStart={sys.executable} {os.path.join(current_dir, 'watchdog.py')}
Restart=on-failure
RestartSec=10
StandardOutput=syslog
StandardError=syslog
SyslogIdentifier=bot_watchdog

[Install]
WantedBy=multi-user.target
"""
        
        # كتابة ملف الخدمة
        with open(service_file, 'w') as f:
            f.write(service_content)
            
        logger.info(f"تم إنشاء ملف خدمة الـ watchdog: {service_file}")
        logger.info("لاستخدام هذه الخدمة، قم بنسخ الملف إلى مجلد الخدمات وتفعيله:")
        logger.info(f"  sudo cp {service_file} /etc/systemd/system/")
        logger.info("  sudo systemctl daemon-reload")
        logger.info("  sudo systemctl enable bot_watchdog.service")
        logger.info("  sudo systemctl start bot_watchdog.service")
    except Exception as e:
        logger.error(f"خطأ في إنشاء ملف خدمة الـ watchdog: {e}")


def start_keep_alive_service():
    """
    تشغيل خدمة Keep-Alive لمنع Replit من تعليق البوت
    """
    try:
        logger.info("جاري بدء تشغيل خدمة Keep-Alive...")
        
        try:
            # محاولة استيراد وحدة keep_alive
            import keep_alive
            # بدء تشغيل الخدمة
            keep_alive_threads = keep_alive.start_keep_alive_service()
            logger.info("✅ تم بدء تشغيل خدمة Keep-Alive بنجاح!")
            return keep_alive_threads
        except ImportError:
            logger.warning("⚠️ لم يتم العثور على وحدة keep_alive. سيتم تجاهل خدمة Keep-Alive.")
        except Exception as e:
            logger.error(f"❌ خطأ أثناء بدء تشغيل خدمة Keep-Alive: {e}")
            import traceback
            logger.error(traceback.format_exc())
    except Exception as outer_e:
        logger.error(f"❌ خطأ خارجي أثناء إعداد خدمة Keep-Alive: {outer_e}")
    
    return None


def clean_restart_markers():
    """
    تنظيف ملفات علامات إعادة التشغيل العالقة.
    هذه الوظيفة تقوم بحذف جميع علامات الإيقاف وإعادة التشغيل المتبقية من تشغيلات سابقة.
    """
    marker_files = [
        "bot_shutdown_marker", 
        "watchdog_ping", 
        "restart_in_progress", 
        "restart_requested.log"
    ]
    
    for marker_file in marker_files:
        if os.path.exists(marker_file):
            try:
                os.remove(marker_file)
                logger.info(f"🧹 تم حذف ملف علامة عالق: {marker_file}")
            except Exception as e:
                logger.error(f"❌ خطأ في حذف ملف العلامة {marker_file}: {e}")


def main():
    """الوظيفة الرئيسية - معززة."""
    global bot_process
    
    # استيراد المكتبات المطلوبة
    import traceback
    
    # تنظيف ملفات علامات إعادة التشغيل العالقة
    logger.info("🧹 تنظيف ملفات علامات إعادة التشغيل العالقة...")
    clean_restart_markers()
    
    # تثبيت الحزم المطلوبة
    install_required_packages()
    
    # تسجيل معالجي الإشارات
    signal.signal(signal.SIGINT, handle_exit)
    signal.signal(signal.SIGTERM, handle_exit)
    
    # تدوير ملفات السجل
    rotate_log_files()
    
    # إنشاء ملف خدمة (لا يؤثر على تشغيل البرنامج الحالي)
    create_watchdog_service_file()
    
    # بدء تشغيل خدمة Keep-Alive لمنع Replit من تعليق البوت
    keep_alive_threads = start_keep_alive_service()
    
    logger.info("🚀 بدء تشغيل نظام مراقبة البوت المعزز...")
    logger.info(f"⚙️ معلمات التكوين: فحص كل {CHECK_INTERVAL} ثانية، إعادة تشغيل دورية كل {FORCE_RESTART_INTERVAL/3600} ساعة")
    
    # محاولة التحقق من الاتصال بالإنترنت قبل البدء
    connected = check_network_connection()
    if not connected:
        logger.warning("⚠️ لا يوجد اتصال بالإنترنت! سيتم المحاولة مع ذلك...")
    
    # بدء تشغيل البوت للمرة الأولى
    max_initial_attempts = 5
    for attempt in range(max_initial_attempts):
        logger.info(f"🔄 محاولة بدء تشغيل البوت الأولية {attempt+1}/{max_initial_attempts}...")
        bot_process = start_bot()
        
        if bot_process is None:
            logger.error(f"❌ فشل في بدء تشغيل البوت (محاولة {attempt+1}/{max_initial_attempts})!")
            time.sleep(5)  # انتظار قبل المحاولة التالية
        else:
            logger.info(f"✅ تم بدء تشغيل البوت بنجاح، معرف العملية: {bot_process.pid}")
            break
    
    if bot_process is None:
        logger.critical("‼️ فشل في بدء تشغيل البوت بعد عدة محاولات! سيتم إعادة المحاولة في الحلقة الرئيسية.")
    
    # تحديث ملف نبضات القلب في البداية
    update_heartbeat_file()
    
    # متغيرات للتتبع
    last_log_rotation = datetime.datetime.now()
    
    # حلقة المراقبة الرئيسية المعززة
    try:
        while True:
            try:
                # تنفيذ مهام دورية
                current_time = datetime.datetime.now()
                
                # تدوير ملفات السجل (مرة كل يوم)
                if (current_time - last_log_rotation).total_seconds() > LOG_ROTATION_INTERVAL:
                    rotate_log_files()
                    last_log_rotation = current_time
                
                # تحديث ملف نبضات القلب في كل دورة تفقدية
                update_heartbeat_file()
                
                # التحقق من حالة البوت
                check_bot_status()
                
                # الانتظار قبل الدورة التالية
                time.sleep(CHECK_INTERVAL)
            except Exception as loop_error:
                logger.error(f"❌ خطأ في دورة المراقبة: {loop_error}")
                time.sleep(CHECK_INTERVAL)  # الانتظار ثم المتابعة
    except KeyboardInterrupt:
        logger.info("⛔ تم استلام إشارة إيقاف من المستخدم. جاري إيقاف المراقبة...")
        stop_bot(bot_process)
    except Exception as e:
        logger.error(f"‼️ حدث خطأ في نظام المراقبة: {e}")
        logger.error(f"سجل التتبع: {traceback.format_exc()}")
        stop_bot(bot_process)


if __name__ == "__main__":
    main()