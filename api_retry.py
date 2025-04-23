#!/usr/bin/env python3
"""
وحدة سياسة إعادة المحاولة الذكية للتعامل مع أخطاء API
"""
import time
import logging
import random
from functools import wraps

# استيراد التكوين الموحد
try:
    from unified_config import get_config
except ImportError:
    # استخدام القيم الافتراضية إذا لم يكن ملف التكوين متاحاً
    def get_config(key=None):
        defaults = {
            "RETRY_MAX_ATTEMPTS": 5,
            "RETRY_INITIAL_DELAY": 1,
            "RETRY_BACKOFF_FACTOR": 2
        }
        if key is None:
            return defaults
        return defaults.get(key)

# قائمة الأخطاء التي يجب إعادة المحاولة عند حدوثها
RETRYABLE_ERRORS = (
    "Connection reset by peer",
    "Read timed out",
    "Connection aborted",
    "Connection refused",
    "Conflict",
    "Bad Gateway",
    "Service Unavailable",
    "Gateway Timeout",
    "Too Many Requests",
    "Network is unreachable"
)

# قائمة رموز الاستجابة التي يجب إعادة المحاولة عند استلامها
RETRYABLE_STATUS_CODES = (408, 425, 429, 500, 502, 503, 504)

def is_retryable_error(exception):
    """تحديد ما إذا كان الخطأ يستدعي إعادة المحاولة"""
    error_str = str(exception).lower()
    
    # التحقق من وجود أي من أنماط الأخطاء القابلة لإعادة المحاولة
    for pattern in RETRYABLE_ERRORS:
        if pattern.lower() in error_str:
            return True
    
    # التحقق من وجود رمز حالة قابل لإعادة المحاولة
    for code in RETRYABLE_STATUS_CODES:
        if f"{code}" in error_str:
            return True
    
    return False

def retry_on_error(max_retries=None, initial_delay=None, backoff_factor=None, retryable_exceptions=None, jitter=True):
    """
    المزخرف (decorator) لإعادة محاولة تنفيذ الدالة عند حدوث أخطاء محددة
    
    المعلمات:
        max_retries: العدد الأقصى لمحاولات إعادة التنفيذ
        initial_delay: التأخير الأولي بين المحاولات (بالثواني)
        backoff_factor: معامل التأخير التصاعدي
        retryable_exceptions: قائمة الاستثناءات التي يجب إعادة المحاولة عند حدوثها
        jitter: إذا كان True، يتم إضافة تأخير عشوائي لمنع تزامن إعادة المحاولات
    
    مثال الاستخدام:
        @retry_on_error(max_retries=3, initial_delay=1, backoff_factor=2)
        def fetch_data_from_api():
            # كود الاتصال بالـ API
    """
    # استخدام قيم التكوين إذا لم يتم تحديد المعلمات
    if max_retries is None:
        max_retries = get_config("RETRY_MAX_ATTEMPTS")
        if not isinstance(max_retries, int):
            max_retries = 3
            
    if initial_delay is None:
        initial_delay = get_config("RETRY_INITIAL_DELAY")
        if not isinstance(initial_delay, (int, float)):
            initial_delay = 1.0
            
    if backoff_factor is None:
        backoff_factor = get_config("RETRY_BACKOFF_FACTOR")
        if not isinstance(backoff_factor, (int, float)):
            backoff_factor = 2.0
    
    # الدالة المغلفة للمزخرف
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            # إنشاء سجل للدالة
            logger = logging.getLogger(func.__module__)
            
            retries = 0
            delay = initial_delay
            
            while True:
                try:
                    return func(*args, **kwargs)
                except Exception as e:
                    retries += 1
                    
                    # التحقق من إذا كان الخطأ قابلاً لإعادة المحاولة
                    if retryable_exceptions:
                        should_retry = any(isinstance(e, ex) for ex in retryable_exceptions)
                    else:
                        should_retry = is_retryable_error(e)
                    
                    # التحقق من عدد المحاولات المتبقية
                    if not should_retry or retries >= max_retries:
                        logger.error(f"فشلت جميع محاولات إعادة التنفيذ ({retries}/{max_retries}) للدالة {func.__name__}: {e}")
                        raise
                    
                    # حساب التأخير قبل المحاولة التالية
                    if jitter:
                        # إضافة تأخير عشوائي (±25%)
                        jitter_amount = delay * 0.25
                        actual_delay = delay + random.uniform(-jitter_amount, jitter_amount)
                        actual_delay = max(0.1, actual_delay)  # تأكد من أن التأخير لا يقل عن 0.1 ثانية
                    else:
                        actual_delay = delay
                    
                    logger.warning(f"محاولة {retries}/{max_retries} فشلت: {e}. إعادة المحاولة بعد {actual_delay:.2f} ثوانٍ...")
                    time.sleep(actual_delay)
                    
                    # زيادة التأخير للمحاولة التالية
                    delay *= backoff_factor
        
        return wrapper
    
    return decorator

class RateLimiter:
    """
    فئة للتحكم في معدل الطلبات لمنع تجاوز حدود API
    
    المعلمات:
        max_calls: الحد الأقصى لعدد الاستدعاءات في الفترة الزمنية المحددة
        period: الفترة الزمنية بالثواني
        
    مثال الاستخدام:
        # إنشاء محدد معدل للسماح بـ 30 طلب في الثانية
        limiter = RateLimiter(max_calls=30, period=1)
        
        def send_api_request():
            limiter()  # انتظر إذا تم تجاوز الحد
            # كود إرسال الطلب
    """
    def __init__(self, max_calls=30, period=1):
        self.max_calls = max_calls
        self.period = period
        self.calls = []
        self.logger = logging.getLogger("RateLimiter")
    
    def __call__(self):
        """
        استدعاء محدد المعدل، سينتظر إذا تم تجاوز الحد
        """
        now = time.time()
        
        # إزالة الطلبات القديمة من السجل
        self.calls = [call for call in self.calls if call > now - self.period]
        
        # إذا تم تجاوز الحد، انتظر حتى يكون من الممكن إرسال طلب جديد
        if len(self.calls) >= self.max_calls:
            sleep_time = self.period - (now - self.calls[0])
            if sleep_time > 0:
                self.logger.debug(f"تجاوز معدل الطلبات ({self.max_calls}/{self.period}s)، الانتظار لمدة {sleep_time:.2f} ثانية")
                time.sleep(sleep_time)
        
        # تسجيل الطلب الحالي
        self.calls.append(time.time())

# إنشاء محدد معدل لاستخدامه مع API تيليجرام
telegram_rate_limiter = RateLimiter(max_calls=25, period=1)

if __name__ == "__main__":
    # إعداد التسجيل
    logging.basicConfig(
        level=logging.DEBUG,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    # اختبار المزخرف retry_on_error
    @retry_on_error(max_retries=3, initial_delay=0.5, backoff_factor=2)
    def test_retry_function(succeed_on_attempt=4):
        attempt = getattr(test_retry_function, "_attempt", 0) + 1
        setattr(test_retry_function, "_attempt", attempt)
        
        print(f"محاولة رقم {attempt}")
        
        if attempt < succeed_on_attempt:
            raise ConnectionError("خطأ في الاتصال (مجرد تجربة)")
        
        return f"نجاح في المحاولة رقم {attempt}"
    
    # اختبار محدد المعدل
    def test_rate_limiter():
        limiter = RateLimiter(max_calls=5, period=2)
        
        print("اختبار محدد المعدل (5 طلبات في 2 ثواني):")
        start_time = time.time()
        
        for i in range(10):
            before_call = time.time()
            limiter()  # قد ينتظر إذا تم تجاوز الحد
            after_call = time.time()
            
            wait_time = after_call - before_call
            elapsed = after_call - start_time
            
            print(f"الطلب {i+1}: انتظر {wait_time:.4f}s, الوقت المنقضي: {elapsed:.4f}s")
    
    # تنفيذ الاختبارات
    try:
        print("=== اختبار إعادة المحاولة الذكية ===")
        result = test_retry_function(succeed_on_attempt=3)
        print(f"النتيجة: {result}")
    except Exception as e:
        print(f"فشل الاختبار مع الخطأ: {e}")
    
    print("\n=== اختبار محدد المعدل ===")
    test_rate_limiter()