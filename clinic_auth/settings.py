import os
from pathlib import Path
from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent.parent

load_dotenv(BASE_DIR / '.env')


def env_bool(name, default=False):
    return os.environ.get(name, '1' if default else '').strip().lower() in ('1', 'true', 'yes', 'on')


# SECURITY WARNING: keep the secret key secret in production.
SECRET_KEY = os.environ.get('DJANGO_SECRET_KEY', 'django-insecure-clinic-auth-module-key-change-in-production')

# SECURITY WARNING: don't run with debug turned on in production!
# DEBUG defaults to True for local dev (no DATABASE_URL), False for production (has DATABASE_URL)
DEBUG = env_bool('DJANGO_DEBUG', not bool(os.environ.get('DATABASE_URL')))

ALLOWED_HOSTS = [h.strip() for h in os.environ.get('DJANGO_ALLOWED_HOSTS', '*').split(',') if h.strip()] + ['healthcheck.railway.app']

INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sites',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'accounts',
    'allauth',
    'allauth.account',
    'allauth.socialaccount',
    'allauth.socialaccount.providers.google',
]

SITE_ID = 1

AUTHENTICATION_BACKENDS = [
    'django.contrib.auth.backends.ModelBackend',
    'allauth.account.auth_backends.AuthenticationBackend',
]

# ---- Google OAuth (django-allauth) ----
SOCIALACCOUNT_PROVIDERS = {
    'google': {
        'SCOPE': ['profile', 'email'],
        'AUTH_PARAMS': {'access_type': 'online'},
    }
}
SOCIALACCOUNT_LOGIN_ON_GET = True
SOCIALACCOUNT_EMAIL_REQUIRED = True
SOCIALACCOUNT_EMAIL_VERIFICATION = 'none'
ACCOUNT_EMAIL_VERIFICATION = 'none'
ACCOUNT_ADAPTER = 'accounts.adapters.AccountAdapter'
SOCIALACCOUNT_ADAPTER = 'accounts.adapters.SocialAccountAdapter'
LOGIN_REDIRECT_URL = '/'

# Google OAuth - configurable for production
ACCOUNT_DEFAULT_HTTP_PROTOCOL = os.environ.get('ACCOUNT_DEFAULT_HTTP_PROTOCOL', 'https' if not DEBUG else 'http')

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'whitenoise.middleware.WhiteNoiseMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.sites.middleware.CurrentSiteMiddleware',
    'allauth.account.middleware.AccountMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
    'clinic_auth.middleware.CharsetMiddleware',
]

ROOT_URLCONF = 'clinic_auth.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [BASE_DIR / 'templates'],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
                'clinic_auth.context_processors.google_oauth',
            ],
        },
    },
]

WSGI_APPLICATION = 'clinic_auth.wsgi.application'

# PostgreSQL in production (DATABASE_URL), SQLite for local development.
if os.environ.get('DATABASE_URL'):
    import dj_database_url
    _dj_url = os.environ.get('DATABASE_URL', '')
    try:
        _db_config = dj_database_url.parse(_dj_url)
        if not _db_config.get('NAME'):
            # Railway's default database is named 'railway'; tolerate a URL
            # that omits the trailing '/railway' path segment.
            if '+postgres' in _dj_url or _dj_url.startswith('postgres'):
                _db_config['NAME'] = 'railway'
        DATABASES = {'default': _db_config}
    except Exception:
        import warnings
        warnings.warn('DATABASE_URL could not be parsed; falling back to SQLite.')
        DATABASES = {
            'default': {
                'ENGINE': 'django.db.backends.sqlite3',
                'NAME': BASE_DIR / 'db.sqlite3',
            }
        }
else:
    DATABASES = {
        'default': {
            'ENGINE': 'django.db.backends.sqlite3',
            'NAME': BASE_DIR / 'db.sqlite3',
        }
    }

AUTH_PASSWORD_VALIDATORS = []

LANGUAGE_CODE = 'en-us'
TIME_ZONE = 'UTC'
USE_I18N = True

# Clinic local timezone used for scheduling reminder emails (e.g. Asia/Tehran)
CLINIC_TIME_ZONE = os.environ.get('CLINIC_TIME_ZONE', 'Asia/Tehran')

DEFAULT_CHARSET = 'utf-8'
USE_TZ = True

STATIC_URL = '/static/'
STATIC_ROOT = BASE_DIR / 'staticfiles'
STATICFILES_DIRS = [BASE_DIR / 'static']

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

LOGIN_URL = '/login/'

MEDIA_URL = '/media/'
MEDIA_ROOT = BASE_DIR / 'media'

AUTH_USER_MODEL = 'accounts.User'

CSRF_TRUSTED_ORIGINS = [o.strip() for o in os.environ.get('CSRF_TRUSTED_ORIGINS', 'http://127.0.0.1:8000,http://localhost:8000').split(',') if o.strip()]

# Email Configuration
# If SMTP credentials are present, default to real SMTP; otherwise fall back to console (dev).
if os.environ.get('EMAIL_BACKEND'):
    EMAIL_BACKEND = os.environ.get('EMAIL_BACKEND')
elif os.environ.get('EMAIL_HOST_USER'):
    EMAIL_BACKEND = 'django.core.mail.backends.smtp.EmailBackend'
else:
    EMAIL_BACKEND = 'django.core.mail.backends.console.EmailBackend'
EMAIL_HOST = os.environ.get('EMAIL_HOST', 'smtp.gmail.com' if os.environ.get('EMAIL_HOST_USER') else 'localhost')
EMAIL_PORT = int(os.environ.get('EMAIL_PORT', '587'))
EMAIL_HOST_USER = os.environ.get('EMAIL_HOST_USER', '')
EMAIL_HOST_PASSWORD = os.environ.get('EMAIL_HOST_PASSWORD', '')
EMAIL_USE_TLS = env_bool('EMAIL_USE_TLS', True)
EMAIL_USE_SSL = env_bool('EMAIL_USE_SSL', False)
EMAIL_TIMEOUT = int(os.environ.get('EMAIL_TIMEOUT', '20'))
MAILEROO_API_KEY = os.environ.get('MAILEROO_API_KEY', '')
MAILEROO_FROM_EMAIL = os.environ.get('MAILEROO_FROM_EMAIL', '')
DEFAULT_FROM_EMAIL = os.environ.get('DEFAULT_FROM_EMAIL', 'ClinicOS <noreply@clinic.local>')

# ---------------------------------------------------------------------------
# SMS / push notification channels (worldwide-ready).
# Reminders are always sent by email; the app ALSO supports SMS so patients and
# doctors with only a phone number can be reached. Set SMS_PROVIDER + the
# provider's credentials (below) in Railway to enable. Until then the system
# safely reports "SMS not configured" without breaking anything.
#
#   SMS_PROVIDER        = 'twilio' | 'kavenegar' | 'smsir' | '' (disabled)
#   DEFAULT_PHONE_CC    = international country code used for local-format numbers
#                         (e.g. '98' = Iran, '44' = UK, '1' = USA). Patients may
#                         also enter their numbers with '+' in full E.164 form.
#   PHONE_REGISTRATION  = 'e164' (world format) | 'local' (Iranian 09...) to control
#                         the format expected at registration. Default: e164.
# ---------------------------------------------------------------------------
SMS_PROVIDER = os.environ.get('SMS_PROVIDER', '').strip().lower()
DEFAULT_PHONE_CC = os.environ.get('DEFAULT_PHONE_CC', '98')
PHONE_REGISTRATION = os.environ.get('PHONE_REGISTRATION', 'e164').strip().lower()

# Twilio (global - US/UK/roaming, best worldwide coverage)
TWILIO_ACCOUNT_SID = os.environ.get('TWILIO_ACCOUNT_SID', '')
TWILIO_AUTH_TOKEN = os.environ.get('TWILIO_AUTH_TOKEN', '')
TWILIO_FROM_NUMBER = os.environ.get('TWILIO_FROM_NUMBER', '')

# Kavenegar (Iran - iranian SMS panel)
KAVENEGAR_API_KEY = os.environ.get('KAVENEGAR_API_KEY', '')
KAVENEGAR_SENDER = os.environ.get('KAVENEGAR_SENDER', '')

# sms.ir (Iran - iranian SMS panel)
SMSIR_API_KEY = os.environ.get('SMSIR_API_KEY', '')
SMSIR_SENDER = os.environ.get('SMSIR_SENDER', '')

# ---------------------------------------------------------------------------
# Telegram bot (free worldwide text channel).
# Create the bot via @BotFather (https://t.me/BotFather), then set in Railway:
#   TELEGRAM_BOT_TOKEN     = the token BotFather gives you (123456:ABC...)
#   TELEGRAM_BOT_USERNAME  = bot username without '@' (e.g. ClinicOSBot)
# The bot delivers the same reminders as email: patients get medication +
# appointment reminders, doctors get their patient list at 10 PM.
# ---------------------------------------------------------------------------
TELEGRAM_BOT_TOKEN = os.environ.get('TELEGRAM_BOT_TOKEN', '')
TELEGRAM_BOT_USERNAME = os.environ.get('TELEGRAM_BOT_USERNAME', '')
TELEGRAM_WEBHOOK_SECRET = os.environ.get('TELEGRAM_WEBHOOK_SECRET', '').strip() or 'clinicostelegramwebhook'
TELEGRAM_BOT_NAME = os.environ.get('TELEGRAM_BOT_NAME', 'ClinicOS')
TELEGRAM_BOT_LOGO_URL = os.environ.get('TELEGRAM_BOT_LOGO_URL', '')
# Optional base URL for the Telegram webhook (e.g. https://web-production-38b5b9.up.railway.app).
# Falls back to RAILWAY_PUBLIC_DOMAIN, then ALLOWED_HOSTS[0].
TELEGRAM_WEBHOOK_BASE = os.environ.get('TELEGRAM_WEBHOOK_BASE', '')
# Secret for test endpoints (e.g. /test/doctor-list-now/?token=...)
TEST_TRIGGER_SECRET = os.environ.get('TEST_TRIGGER_SECRET', 'test-secret-change-me')

# Security headers for production HTTPS.
SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')
SESSION_COOKIE_SECURE = env_bool('DJANGO_SESSION_COOKIE_SECURE', not DEBUG)
CSRF_COOKIE_SECURE = env_bool('DJANGO_CSRF_COOKIE_SECURE', not DEBUG)
SESSION_COOKIE_SAMESITE = 'Lax'

_cookie_domain = os.environ.get('DJANGO_SESSION_COOKIE_DOMAIN', '')
SESSION_COOKIE_DOMAIN = _cookie_domain or None

LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'handlers': {
        'console': {
            'class': 'logging.StreamHandler',
        },
    },
    'root': {
        'handlers': ['console'],
        'level': 'WARNING',
    },
    'loggers': {
        'accounts': {
            'handlers': ['console'],
            'level': 'ERROR',
            'propagate': False,
        },
        'clinic_auth': {
            'handlers': ['console'],
            'level': 'ERROR',
            'propagate': False,
        },
    },
}
