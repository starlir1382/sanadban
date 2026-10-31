"""
Django settings for SanadBan (DeedFlow) project.
National Housing Dossier & Archival Workflow System
"""

import os
from pathlib import Path

# Build paths inside the project like this: BASE_DIR / 'subdir'.
BASE_DIR = Path(__file__).resolve().parent.parent

# Auto-load .env file if present
_env_file = BASE_DIR / '.env'
if _env_file.exists():
    try:
        with open(_env_file, 'r', encoding='utf-8') as _f:
            for _line in _f:
                _line = _line.strip()
                if _line and not _line.startswith('#') and '=' in _line:
                    _k, _v = _line.split('=', 1)
                    os.environ.setdefault(_k.strip(), _v.strip().strip("'").strip('"'))
    except Exception:
        pass


def _env_bool(name, default=False):
    return os.environ.get(name, str(default)).strip().lower() in ('1', 'true', 'yes', 'on')


def _env_list(name, default=''):
    return [v.strip() for v in os.environ.get(name, default).split(',') if v.strip()]


# ---------------------------------------------------------------------------
# Core security settings (all driven by .env)
# ---------------------------------------------------------------------------
DEBUG = _env_bool('DJANGO_DEBUG', True)

SECRET_KEY = os.environ.get('DJANGO_SECRET_KEY')
if not SECRET_KEY:
    if DEBUG:
        SECRET_KEY = 'django-insecure-dev-only-key-change-me'
    else:
        raise RuntimeError('DJANGO_SECRET_KEY is missing. Set it in .env when DEBUG is off.')

ALLOWED_HOSTS = _env_list('DJANGO_ALLOWED_HOSTS', '127.0.0.1,localhost,*')

# Needed when the site is opened through IIS under a real domain/HTTPS
CSRF_TRUSTED_ORIGINS = _env_list('DJANGO_CSRF_TRUSTED_ORIGINS')

SESSION_COOKIE_SECURE = _env_bool('DJANGO_HTTPS', False)
CSRF_COOKIE_SECURE = _env_bool('DJANGO_HTTPS', False)
if not _env_bool('DJANGO_HTTPS', False):
    SECURE_CROSS_ORIGIN_OPENER_POLICY = None

# Application definition
INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',

    # SanadBan Workflow App
    'workflow.apps.WorkflowConfig',
    'django.contrib.humanize',
]

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    # Serves /static/ files when running under Waitress (no runserver)
    'whitenoise.middleware.WhiteNoiseMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'workflow.middleware.FirstLoginSecurityMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

ROOT_URLCONF = 'config.urls'

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
                'workflow.context_processors.jalali_date_context',
            ],
        },
    },
]

WSGI_APPLICATION = 'config.wsgi.application'

# Database Configuration
# Supports both PostgreSQL (production) and SQLite (fallback / dev)
# Set DB_ENGINE=postgresql in .env or environment to activate PostgreSQL
DB_ENGINE = os.environ.get('DB_ENGINE', 'sqlite').lower()

if DB_ENGINE in ('postgres', 'postgresql', 'pg'):
    DATABASES = {
        'default': {
            'ENGINE': 'django.db.backends.postgresql',
            'NAME': os.environ.get('DB_NAME', 'ztkmaskan'),
            'USER': os.environ.get('DB_USER', 'sanadban_user'),
            'PASSWORD': os.environ.get('DB_PASSWORD', 'Maskan2026ztk'),
            'HOST': os.environ.get('DB_HOST', '127.0.0.1'),
            'PORT': os.environ.get('DB_PORT', '5432'),
            'CONN_MAX_AGE': 600,
        }
    }
else:
    DATABASES = {
        'default': {
            'ENGINE': 'django.db.backends.sqlite3',
            'NAME': BASE_DIR / 'db.sqlite3',
            'OPTIONS': {
                'timeout': 60,
                'init_command': 'PRAGMA journal_mode=WAL; PRAGMA synchronous=NORMAL; PRAGMA cache_size=10000; PRAGMA temp_store=MEMORY;',
            },
        }
    }

AUTH_PASSWORD_VALIDATORS = [
    {
        'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator',
    },
]

# Internationalization & Persian Localization
LANGUAGE_CODE = 'fa-ir'
TIME_ZONE = 'Asia/Tehran'
USE_I18N = True
USE_TZ = True

# Static files (CSS, JavaScript, Images)
STATIC_URL = '/static/'
STATICFILES_DIRS = [
    BASE_DIR / 'static',
]
STATIC_ROOT = Path(os.environ.get('SANADBAN_STATIC_ROOT', str(BASE_DIR / 'staticfiles')))

# Media files (Scanned attachments, signatures, checks)
MEDIA_URL = '/uploads/'
MEDIA_ROOT = Path(os.environ.get('SANADBAN_MEDIA_ROOT', str(BASE_DIR / 'uploads')))

LOGIN_URL = 'login'
LOGIN_REDIRECT_URL = 'dossier_list'
LOGOUT_REDIRECT_URL = 'login'

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

# Upload & Request Limits (Support large Excel sheets and scan attachments)
DATA_UPLOAD_MAX_MEMORY_SIZE = 104857600  # 100 MB
FILE_UPLOAD_MAX_MEMORY_SIZE = 104857600  # 100 MB
DATA_UPLOAD_MAX_NUMBER_FIELDS = 50000

# Logging
LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'simple': {'format': '%(asctime)s %(levelname)s %(name)s: %(message)s'},
    },
    'handlers': {
        'console': {'class': 'logging.StreamHandler', 'formatter': 'simple'},
    },
    'root': {'handlers': ['console'], 'level': 'WARNING'},
}
