"""
Django settings for tapstar_project.
Configured via environment variables — see .env.example.
"""

from pathlib import Path
import os
import dj_database_url
from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent.parent

load_dotenv(BASE_DIR / ".env")


def env_bool(key: str, default: bool = False) -> bool:
    val = os.getenv(key)
    if val is None:
        return default
    return val.strip().lower() in ("1", "true", "yes", "on")


SECRET_KEY = os.getenv("SECRET_KEY", "django-insecure-dev-only-change-me")
DEBUG = env_bool("DEBUG", True)

ALLOWED_HOSTS = [h.strip() for h in os.getenv("ALLOWED_HOSTS", "localhost,127.0.0.1").split(",") if h.strip()]
CSRF_TRUSTED_ORIGINS = [o.strip() for o in os.getenv("CSRF_TRUSTED_ORIGINS", "").split(",") if o.strip()]


INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    # third-party
    "rest_framework",
    "django_htmx",
    # local apps
    "accounts",
    "businesses",
    "reviews",
    "feedback",
    "analytics",
    "settings_mgr",
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "whitenoise.middleware.WhiteNoiseMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
    "django_htmx.middleware.HtmxMiddleware",
]

ROOT_URLCONF = "tapstar_project.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [BASE_DIR / "templates"],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
                "feedback.context_processors.unread_feedback",
            ],
        },
    },
]

WSGI_APPLICATION = "tapstar_project.wsgi.application"


DATABASE_URL = os.getenv("DATABASE_URL", f"sqlite:///{BASE_DIR / 'db.sqlite3'}")
DATABASES = {
    "default": dj_database_url.parse(DATABASE_URL, conn_max_age=600),
}


AUTH_USER_MODEL = "accounts.User"

AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator"},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]

LANGUAGE_CODE = "en-in"
TIME_ZONE = "Asia/Kolkata"
USE_I18N = True
USE_TZ = True


STATIC_URL = "static/"
STATIC_ROOT = BASE_DIR / "staticfiles"
STORAGES = {
    "default": {"BACKEND": "django.core.files.storage.FileSystemStorage"},
    "staticfiles": {
        "BACKEND": (
            "whitenoise.storage.CompressedManifestStaticFilesStorage"
            if not DEBUG
            else "django.contrib.staticfiles.storage.StaticFilesStorage"
        )
    },
}

MEDIA_URL = "media/"
MEDIA_ROOT = Path(os.getenv("MEDIA_ROOT", BASE_DIR / "media"))


DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"


# ----------------------------------------------------------------------
# Security — all defaults are safe for dev; the production flags only
# activate when DEBUG=False and you explicitly enable them via .env.
# ----------------------------------------------------------------------

# Honour the X-Forwarded-Proto header from nginx so Django knows the
# request arrived over HTTPS. Without this, SECURE_SSL_REDIRECT loops.
SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")

# Redirect plain HTTP → HTTPS at the Django layer. Keep off in dev.
# Production: set SECURE_SSL_REDIRECT=True in .env once TLS is live.
SECURE_SSL_REDIRECT = env_bool("SECURE_SSL_REDIRECT", False)

# Secure cookie flags — only send cookies over HTTPS in prod.
SESSION_COOKIE_SECURE = env_bool("SESSION_COOKIE_SECURE", not DEBUG)
CSRF_COOKIE_SECURE = env_bool("CSRF_COOKIE_SECURE", not DEBUG)

# HSTS — tell browsers to only visit over HTTPS for the next N seconds.
# Start small (e.g. 3600) while testing, then raise to 31536000 (1 year).
SECURE_HSTS_SECONDS = int(os.getenv("SECURE_HSTS_SECONDS", "0"))
SECURE_HSTS_INCLUDE_SUBDOMAINS = env_bool("SECURE_HSTS_INCLUDE_SUBDOMAINS", False)
SECURE_HSTS_PRELOAD = env_bool("SECURE_HSTS_PRELOAD", False)

# Prevent the site from being framed (clickjacking).
X_FRAME_OPTIONS = "DENY"
SECURE_CONTENT_TYPE_NOSNIFF = True
SECURE_REFERRER_POLICY = "same-origin"


# ----------------------------------------------------------------------
# Logging — structured to stdout/stderr in prod so systemd/journald can
# collect. A rotating file is also written to LOG_DIR if provided.
# ----------------------------------------------------------------------
LOG_LEVEL = os.getenv("LOG_LEVEL", "DEBUG" if DEBUG else "INFO").upper()
LOG_DIR = os.getenv("LOG_DIR")  # e.g. /var/log/tapstar — optional

_log_handlers = {
    "console": {
        "class": "logging.StreamHandler",
        "formatter": "verbose",
    },
}
if LOG_DIR:
    try:
        Path(LOG_DIR).mkdir(parents=True, exist_ok=True)
        _log_handlers["file"] = {
            "class": "logging.handlers.RotatingFileHandler",
            "filename": str(Path(LOG_DIR) / "tapstar.log"),
            "maxBytes": 10 * 1024 * 1024,
            "backupCount": 5,
            "formatter": "verbose",
        }
    except OSError:
        # Directory not writable — fall back to console-only rather than crash.
        pass

_active_handlers = list(_log_handlers.keys())

LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "verbose": {
            "format": "{asctime} [{levelname}] {name}: {message}",
            "style": "{",
        },
    },
    "handlers": _log_handlers,
    "root": {"handlers": _active_handlers, "level": LOG_LEVEL},
    "loggers": {
        "django": {"handlers": _active_handlers, "level": LOG_LEVEL, "propagate": False},
        "django.request": {"handlers": _active_handlers, "level": "WARNING", "propagate": False},
        "tapstar": {"handlers": _active_handlers, "level": LOG_LEVEL, "propagate": False},
    },
}


# Auth redirects
LOGIN_URL = "/auth/login/"
LOGIN_REDIRECT_URL = "/dashboard/"
LOGOUT_REDIRECT_URL = "/"


# Celery / Redis
REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")
CELERY_BROKER_URL = REDIS_URL
CELERY_RESULT_BACKEND = REDIS_URL
CELERY_TASK_ALWAYS_EAGER = env_bool("CELERY_TASK_ALWAYS_EAGER", DEBUG)
CELERY_TIMEZONE = TIME_ZONE


# Anthropic
ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY", "")
ANTHROPIC_MODEL = os.getenv("ANTHROPIC_MODEL", "claude-sonnet-4-20250514")

# Google Places (optional — enables primary photo fallback on the customer page
# when a business only has a Place ID and no uploaded logo). Without this key,
# the customer page falls back to a branded gradient initial.
GOOGLE_PLACES_API_KEY = os.getenv("GOOGLE_PLACES_API_KEY", "")


# Easebuzz (Indian payment gateway — UPI + cards + net banking, INR)
EASEBUZZ_KEY = os.getenv("EASEBUZZ_KEY", "")
EASEBUZZ_SALT = os.getenv("EASEBUZZ_SALT", "")
EASEBUZZ_ENV = os.getenv("EASEBUZZ_ENV", "test")  # "test" | "prod"


# Email
EMAIL_BACKEND = os.getenv(
    "EMAIL_BACKEND",
    "django.core.mail.backends.console.EmailBackend" if DEBUG else "django.core.mail.backends.smtp.EmailBackend",
)
EMAIL_HOST = os.getenv("EMAIL_HOST", "smtp.gmail.com")
EMAIL_PORT = int(os.getenv("EMAIL_PORT", "587"))
EMAIL_HOST_USER = os.getenv("EMAIL_HOST_USER", "")
EMAIL_HOST_PASSWORD = os.getenv("EMAIL_HOST_PASSWORD", "")
EMAIL_USE_TLS = env_bool("EMAIL_USE_TLS", True)
DEFAULT_FROM_EMAIL = os.getenv("DEFAULT_FROM_EMAIL", "Tapstar <noreply@tapstar.in>")


SITE_URL = os.getenv("SITE_URL", "http://localhost:8000")

# Subscription plan codes
PLAN_STARTER = "starter"
PLAN_GROWTH = "growth"
PLAN_BUSINESS = "business"

# Prices in paise (1 INR = 100 paise). Easebuzz expects rupees as a
# decimal string but we store paise internally to keep integer math clean.
#   Starter  — free forever
#   Growth   — billed monthly
#   Business — billed yearly (cheaper per-month than Growth by design)
PLAN_PRICES_PAISE = {
    PLAN_STARTER: 0,
    PLAN_GROWTH: 5000,     # Rs.50 / month
    PLAN_BUSINESS: 49900,  # Rs.499 / year
}

# How long a successful payment extends the subscription for each plan.
PLAN_BILLING_PERIOD_DAYS = {
    PLAN_STARTER: 0,       # free — not extended by payments
    PLAN_GROWTH: 30,
    PLAN_BUSINESS: 365,
}

# How to describe each plan's price in UI ("forever" / "/ month" / "/ year").
PLAN_PERIOD_LABELS = {
    PLAN_STARTER: "forever",
    PLAN_GROWTH: "/ month",
    PLAN_BUSINESS: "/ year",
}

# None = unlimited
PLAN_REVIEW_LIMITS = {
    PLAN_STARTER: 5,
    PLAN_GROWTH: None,
    PLAN_BUSINESS: None,
}

PLAN_LOCATION_LIMITS = {
    PLAN_STARTER: 1,
    PLAN_GROWTH: 1,
    PLAN_BUSINESS: 5,
}
