import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent

# =========================
# Security / Environment
# =========================
SECRET_KEY = os.environ.get("DJANGO_SECRET_KEY", "CHANGE_ME_IN_PRODUCTION")

DEBUG = os.environ.get("DJANGO_DEBUG", "1") == "1"

ALLOWED_HOSTS = os.environ.get(
    "DJANGO_ALLOWED_HOSTS",
    "127.0.0.1,localhost"
).split(",")

# =========================
# Applications
# =========================
INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',

    'captcha',
    'import_export',
    
    'root',
    'applications',
    'documents',
    'tracking',
    'dashboard',
    'notifications',
    'locations',
    'authentification',
]

# =========================
# Middleware
# =========================
MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',

    # 'django.middleware.locale.LocaleMiddleware',

    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

ROOT_URLCONF = 'main.urls'

# =========================
# Templates
# =========================
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
            ],
        },
    },
]

WSGI_APPLICATION = 'main.wsgi.application'

# =========================
# captcha
# =========================

CAPTCHA_LENGTH = 5
CAPTCHA_TIMEOUT = 5 * 60  # 5 minutes
CAPTCHA_CHALLENGE_FUNCT = 'captcha.helpers.random_char_challenge'
CAPTCHA_FONT_SIZE = 24
CAPTCHA_IMAGE_SIZE = (200,40)
CAPTCHA_BACKGROUND_COLOR = '#f8f9fa'   
CAPTCHA_FOREGROUND_COLOR = '#2c3e50'  

CAPTCHA_NOISE_FUNCTIONS = (
    'captcha.helpers.noise_dots',
    'captcha.helpers.noise_arcs',
)
CAPTCHA_CHALLENGE_FUNCT = 'captcha.helpers.random_char_challenge'
CAPTCHA_ALLOWED_CHARS = 'ABCDEFGHJKLMNPQRSTUVWXYZ23456789'
# =========================
# Database
# =========================
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql',
        'NAME': os.environ.get('DB_NAME', 'career_portal_db'),
        'USER': os.environ.get('DB_USER', 'postgres'),
        'PASSWORD': os.environ.get('DB_PASSWORD', '7895123'), 
        'HOST': os.environ.get('DB_HOST', 'localhost'),
        'PORT': os.environ.get('DB_PORT', '5432'),
        'CONN_MAX_AGE': 60,
    }
}

# =========================
# Auth
# =========================
LOGIN_URL = '/auth/login/'
LOGIN_REDIRECT_URL = '/dashboard/'
LOGOUT_REDIRECT_URL = '/auth/login/'
# OR
# LOGIN_URL = 'authentification:admin_login'
# LOGIN_REDIRECT_URL = 'dashboard:dashboard_home'
# LOGOUT_REDIRECT_URL = 'authentification:admin_login'

# =========================
# Password validation
# =========================
AUTH_PASSWORD_VALIDATORS = [
    {'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator'},
    {'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator'},
    {'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator'},
    {'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator'},
]

# =========================
# Language / Timezone
# =========================
LANGUAGE_CODE = 'fr'
TIME_ZONE = 'Africa/Algiers'

USE_I18N = False
USE_L10N = True
USE_TZ = True

# =========================
# Static / Media
# =========================
STATIC_URL = '/static/'
STATIC_ROOT = BASE_DIR / 'staticfiles'

STATICFILES_DIRS = [
    BASE_DIR / 'static', 
]

MEDIA_URL = '/media/'
MEDIA_ROOT = BASE_DIR / 'media'

# Django 3.2+
DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

# =========================
# Email
# =========================

EMAIL_BACKEND = 'django.core.mail.backends.smtp.EmailBackend'
EMAIL_HOST = os.environ.get('EMAIL_HOST', 'mail.mkesm.gov.dz')
EMAIL_PORT = int(os.environ.get('EMAIL_PORT', '587'))
EMAIL_USE_TLS = bool(int(os.environ.get('EMAIL_USE_TLS', '1')))
EMAIL_USE_SSL = bool(int(os.environ.get('EMAIL_USE_SSL', '0')))
EMAIL_HOST_USER = os.environ.get('EMAIL_HOST_USER', 'no-reply@mkesm.gov.dz')
EMAIL_HOST_PASSWORD = os.environ.get('EMAIL_HOST_PASSWORD', 'ze{9Yd5JSf')
DEFAULT_FROM_EMAIL = os.environ.get('DEFAULT_FROM_EMAIL', 'no-reply@mkesm.gov.dz')
DEFAULT_ADMIN_EMAIL = os.environ.get('DEFAULT_ADMIN_EMAIL', 'no-reply@mkesm.gov.dz')
EMAIL_TIMEOUT = 10

# =========================
# captcha
# =========================

CAPTCHA_LENGTH = 5
CAPTCHA_TIMEOUT = 5 * 60  # 5 minutes
CAPTCHA_CHALLENGE_FUNCT = 'captcha.helpers.random_char_challenge'

CAPTCHA_FONT_SIZE = 32
CAPTCHA_IMAGE_SIZE = (260, 70)

CAPTCHA_BACKGROUND_COLOR = '#f8f9fa'
CAPTCHA_FOREGROUND_COLOR = '#2c3e50'

CAPTCHA_NOISE_FUNCTIONS = (
    'captcha.helpers.noise_dots',
    'captcha.helpers.noise_arcs',
)

CAPTCHA_ALLOWED_CHARS = 'ABCDEFGHJKLMNPQRSTUVWXYZ23456789'

# =========================
# Production Security
# =========================
if not DEBUG:
    SECURE_SSL_REDIRECT = True
    SESSION_COOKIE_SECURE = True
    CSRF_COOKIE_SECURE = True
    SECURE_HSTS_SECONDS = 31536000
    SECURE_HSTS_INCLUDE_SUBDOMAINS = True
    SECURE_HSTS_PRELOAD = True
    X_FRAME_OPTIONS = 'DENY'

# =========================
# Celery
# =========================

CELERY_BROKER_URL = os.environ.get("CELERY_BROKER_URL", "redis://127.0.0.1:6379/0")
CELERY_RESULT_BACKEND = os.environ.get("CELERY_RESULT_BACKEND", "redis://127.0.0.1:6379/1")

CELERY_TASK_ALWAYS_EAGER = DEBUG
CELERY_TASK_EAGER_PROPAGATES = DEBUG

CELERY_TASK_TIME_LIMIT = 30 * 60
CELERY_TASK_SOFT_TIME_LIMIT = 25 * 60
CELERY_TASK_TRACK_STARTED = True
CELERY_TASK_IGNORE_RESULT = True
# =========================
# Logging
# =========================
LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'handlers': {'console': {'class': 'logging.StreamHandler'}},
    'root': {'handlers': ['console'], 'level': 'DEBUG' if DEBUG else 'INFO'},
}

# Fix mimetypes for .js
if DEBUG:
    import mimetypes
    mimetypes.add_type("application/javascript", ".js", True)
