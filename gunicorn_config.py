#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
ملف تكوين Gunicorn للنشر على Replit
"""
import os
import multiprocessing

# Server settings
bind = "0.0.0.0:5000"  # This will be forwarded to port 80 externally
workers = 1  # عامل واحد فقط لتقليل استهلاك الموارد
threads = 2
worker_class = "sync"
worker_connections = 1000
timeout = 30  # ضبط وقت الانتظار لمنع المهل الطويلة
keepalive = 5

# Logging settings
accesslog = "-"
errorlog = "-"
loglevel = "info"
logconfig_dict = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "generic": {
            "format": "%(asctime)s [%(process)d] [%(levelname)s] %(message)s",
            "datefmt": "[%Y-%m-%d %H:%M:%S %z]",
            "class": "logging.Formatter"
        }
    },
    "handlers": {
        "console": {
            "class": "logging.StreamHandler",
            "formatter": "generic",
            "level": "INFO"
        }
    },
    "loggers": {
        "gunicorn.error": {
            "level": "INFO",
            "handlers": ["console"],
            "propagate": False
        },
        "gunicorn.access": {
            "level": "INFO",
            "handlers": ["console"],
            "propagate": False
        }
    }
}

# Application settings
reload = True
reload_engine = "auto"
reload_extra_files = [
    "app.py",
    "bot.py",
    "main.py",
    "database.py",
    "models.py",
    "config.py",
    "admin_handlers.py",
    "ai_handlers.py",
    "templates/*",
    "static/*"
]
preload_app = False

# Other settings
proc_name = "telegram_bot_app"
raw_env = [
    f"TELEGRAM_BOT_TOKEN={os.environ.get('TELEGRAM_BOT_TOKEN', '7406580104:AAGG2JQeeNfsmcGVMCm7hxitIK-qm2yekVg')}",
    f"USE_ALWAYS_ON={os.environ.get('USE_ALWAYS_ON', 'True')}",
    f"RUN_BOT_FROM_SERVER={os.environ.get('RUN_BOT_FROM_SERVER', 'False')}"
]

# Graceful shutdown handling
graceful_timeout = 10
max_requests = 1000
max_requests_jitter = 50

# Callback functions
def on_starting(server):
    print("✅ بدء تشغيل خادم Gunicorn...")

def when_ready(server):
    print("✅ خادم Gunicorn جاهز للاستقبال الطلبات!")

def post_fork(server, worker):
    print(f"✅ تم إنشاء عامل جديد: {worker.pid}")

def worker_exit(server, worker):
    print(f"⚠️ خروج العامل: {worker.pid}")

def worker_abort(worker):
    print(f"❌ فشل العامل: {worker.pid}")

def on_exit(server):
    print("⚠️ إيقاف خادم Gunicorn...")