# Django REST Framework: Production Project Setup

This guide provides a comprehensive, production-ready project setup for Django REST Framework.

## Table of Contents

1. [Project Structure](#project-structure)
2. [Environment Setup](#environment-setup)
3. [Settings Configuration](#settings-configuration)
4. [Database Configuration](#database-configuration)
5. [Authentication Setup](#authentication-setup)
6. [CORS Configuration](#cors-configuration)
7. [Static and Media Files](#static-and-media-files)
8. [Logging Setup](#logging-setup)
9. [Security Checklist](#security-checklist)
10. [Deployment Preparation](#deployment-preparation)

---

## Project Structure

### Recommended Directory Layout

```
myproject/
├── config/                      # Project configuration
│   ├── __init__.py
│   ├── settings/
│   │   ├── __init__.py
│   │   ├── base.py             # Base settings
│   │   ├── development.py      # Dev overrides
│   │   ├── staging.py          # Staging overrides
│   │   └── production.py       # Production overrides
│   ├── urls.py
│   ├── wsgi.py
│   └── asgi.py
├── apps/                        # All Django apps
│   ├── api/                     # Core API app
│   │   ├── __init__.py
│   │   ├── models.py
│   │   ├── serializers.py
│   │   ├── views.py
│   │   ├── permissions.py
│   │   ├── pagination.py
│   │   └── urls.py
│   ├── users/                   # Custom user app
│   └── ...
├── requirements/
│   ├── base.txt                 # Base requirements
│   ├── development.txt          # Dev dependencies
│   └── production.txt           # Production dependencies
├── static/
├── media/
├── logs/
├── .env.example                 # Example environment variables
├── .env                         # Actual env vars (gitignored)
├── .gitignore
├── manage.py
└── README.md
```

### Create the Structure

```bash
# Create project
mkdir myproject && cd myproject

# Start Django project
django-admin startproject config .

# Create settings directory
mkdir -p config/settings
touch config/settings/{__init__.py,base.py,development.py,production.py}

# Create apps directory
mkdir apps
touch apps/__init__.py

# Create requirements directory
mkdir requirements
touch requirements/{base.txt,development.txt,production.txt}

# Create other directories
mkdir -p {static,media,logs}

# Create environment file
touch .env.example .env
```

---

## Environment Setup

### 1. Virtual Environment

```bash
# Create virtual environment
python3 -m venv venv

# Activate
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Upgrade pip
pip install --upgrade pip
```

### 2. Requirements Files

**requirements/base.txt:**
```txt
Django>=4.2,<5.0
djangorestframework>=3.14
django-environ>=0.10  # For environment variables
psycopg2-binary>=2.9  # PostgreSQL adapter
gunicorn>=21.0        # Production server
```

**requirements/development.txt:**
```txt
-r base.txt
django-debug-toolbar>=4.0
django-extensions>=3.2
ipython>=8.0
```

**requirements/production.txt:**
```txt
-r base.txt
django-cors-headers>=4.0
whitenoise>=6.5       # Static file serving
sentry-sdk>=1.30      # Error tracking
```

### 3. Install Dependencies

```bash
# For development
pip install -r requirements/development.txt

# For production
pip install -r requirements/production.txt
```

---

## Settings Configuration

### config/settings/base.py

```python
"""
Base settings shared across all environments.
"""
import os
from pathlib import Path
import environ

# Build paths
BASE_DIR = Path(__file__).resolve().parent.parent.parent

# Initialize environment variables
env = environ.Env(
    DEBUG=(bool, False),
    SECRET_KEY=(str, 'changeme'),
    ALLOWED_HOSTS=(list, []),
)

# Read .env file
environ.Env.read_env(os.path.join(BASE_DIR, '.env'))

# SECURITY WARNING: keep the secret key used in production secret!
SECRET_KEY = env('SECRET_KEY')

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = env('DEBUG')

ALLOWED_HOSTS = env.list('ALLOWED_HOSTS')


# Application definition
INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',

    # Third party apps
    'rest_framework',
    'rest_framework.authtoken',

    # Local apps
    'apps.api',
]

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
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
            ],
        },
    },
]

WSGI_APPLICATION = 'config.wsgi.application'


# Database
# https://docs.djangoproject.com/en/4.2/ref/settings/#databases
DATABASES = {
    'default': env.db('DATABASE_URL', default='sqlite:///db.sqlite3'),
}


# Password validation
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


# Internationalization
LANGUAGE_CODE = 'en-us'
TIME_ZONE = 'UTC'
USE_I18N = True
USE_TZ = True


# Static files (CSS, JavaScript, Images)
STATIC_URL = 'static/'
STATIC_ROOT = BASE_DIR / 'staticfiles'
STATICFILES_DIRS = [BASE_DIR / 'static']

# Media files
MEDIA_URL = 'media/'
MEDIA_ROOT = BASE_DIR / 'media'


# Default primary key field type
DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'


# REST Framework settings
REST_FRAMEWORK = {
    # Authentication
    'DEFAULT_AUTHENTICATION_CLASSES': [
        'rest_framework.authentication.TokenAuthentication',
        'rest_framework.authentication.SessionAuthentication',
    ],

    # Permissions
    'DEFAULT_PERMISSION_CLASSES': [
        'rest_framework.permissions.IsAuthenticated',
    ],

    # Pagination
    'DEFAULT_PAGINATION_CLASS': 'rest_framework.pagination.PageNumberPagination',
    'PAGE_SIZE': 20,

    # Filtering
    'DEFAULT_FILTER_BACKENDS': [
        'rest_framework.filters.SearchFilter',
        'rest_framework.filters.OrderingFilter',
    ],

    # Rendering
    'DEFAULT_RENDERER_CLASSES': [
        'rest_framework.renderers.JSONRenderer',
        'rest_framework.renderers.BrowsableAPIRenderer',
    ],

    # Throttling
    'DEFAULT_THROTTLE_CLASSES': [
        'rest_framework.throttling.AnonRateThrottle',
        'rest_framework.throttling.UserRateThrottle',
    ],
    'DEFAULT_THROTTLE_RATES': {
        'anon': '100/day',
        'user': '1000/day',
    },

    # Date/Time format
    'DATETIME_FORMAT': '%Y-%m-%d %H:%M:%S',
}
```

### config/settings/development.py

```python
from .base import *

DEBUG = True

ALLOWED_HOSTS = ['localhost', '127.0.0.1']

# Development-specific apps
INSTALLED_APPS += [
    'django_extensions',
    'debug_toolbar',
]

# Debug toolbar middleware
MIDDLEWARE += [
    'debug_toolbar.middleware.DebugToolbarMiddleware',
]

# Debug toolbar configuration
INTERNAL_IPS = [
    '127.0.0.1',
]

# Disable throttling in development
REST_FRAMEWORK['DEFAULT_THROTTLE_CLASSES'] = []
REST_FRAMEWORK['DEFAULT_THROTTLE_RATES'] = {}

# Use console email backend
EMAIL_BACKEND = 'django.core.mail.backends.console.EmailBackend'
```

### config/settings/production.py

```python
from .base import *
import sentry_sdk
from sentry_sdk.integrations.django import DjangoIntegration

DEBUG = False

# Security settings
SECURE_SSL_REDIRECT = True
SESSION_COOKIE_SECURE = True
CSRF_COOKIE_SECURE = True
SECURE_HSTS_SECONDS = 31536000
SECURE_HSTS_INCLUDE_SUBDOMAINS = True
SECURE_HSTS_PRELOAD = True
SECURE_BROWSER_XSS_FILTER = True
SECURE_CONTENT_TYPE_NOSNIFF = True

# CORS (if needed)
INSTALLED_APPS += ['corsheaders']
MIDDLEWARE.insert(0, 'corsheaders.middleware.CorsMiddleware')

CORS_ALLOWED_ORIGINS = env.list('CORS_ALLOWED_ORIGINS', default=[])

# Static files with WhiteNoise
MIDDLEWARE.insert(1, 'whitenoise.middleware.WhiteNoiseMiddleware')
STATICFILES_STORAGE = 'whitenoise.storage.CompressedManifestStaticFilesStorage'

# Remove browsable API in production
REST_FRAMEWORK['DEFAULT_RENDERER_CLASSES'] = [
    'rest_framework.renderers.JSONRenderer',
]

# Sentry error tracking
if env('SENTRY_DSN', default=None):
    sentry_sdk.init(
        dsn=env('SENTRY_DSN'),
        integrations=[DjangoIntegration()],
        traces_sample_rate=1.0,
        send_default_pii=True,
    )

# Email configuration
EMAIL_BACKEND = 'django.core.mail.backends.smtp.EmailBackend'
EMAIL_HOST = env('EMAIL_HOST')
EMAIL_PORT = env.int('EMAIL_PORT', 587)
EMAIL_USE_TLS = True
EMAIL_HOST_USER = env('EMAIL_HOST_USER')
EMAIL_HOST_PASSWORD = env('EMAIL_HOST_PASSWORD')
```

### .env.example

```bash
# Django settings
DEBUG=True
SECRET_KEY=your-secret-key-here
ALLOWED_HOSTS=localhost,127.0.0.1

# Database
DATABASE_URL=postgresql://user:password@localhost:5432/dbname

# Email
EMAIL_HOST=smtp.gmail.com
EMAIL_PORT=587
EMAIL_HOST_USER=your-email@gmail.com
EMAIL_HOST_PASSWORD=your-password

# Sentry (optional)
SENTRY_DSN=

# CORS (optional)
CORS_ALLOWED_ORIGINS=http://localhost:3000,http://localhost:8080
```

---

## Database Configuration

### PostgreSQL Setup

```bash
# Install PostgreSQL
# On Ubuntu/Debian
sudo apt-get install postgresql postgresql-contrib

# On macOS
brew install postgresql

# Create database and user
sudo -u postgres psql

CREATE DATABASE myproject;
CREATE USER myprojectuser WITH PASSWORD 'password';
ALTER ROLE myprojectuser SET client_encoding TO 'utf8';
ALTER ROLE myprojectuser SET default_transaction_isolation TO 'read committed';
ALTER ROLE myprojectuser SET timezone TO 'UTC';
GRANT ALL PRIVILEGES ON DATABASE myproject TO myprojectuser;
\q
```

### Update .env

```bash
DATABASE_URL=postgresql://myprojectuser:password@localhost:5432/myproject
```

### Apply Migrations

```bash
python manage.py migrate
```

---

## Authentication Setup

### Token Authentication

Token authentication is already configured in base settings. Create tokens for users:

```python
# In Django shell
from django.contrib.auth.models import User
from rest_framework.authtoken.models import Token

user = User.objects.get(username='admin')
token = Token.objects.create(user=user)
print(token.key)
```

### JWT Authentication (Alternative)

For JWT, install `djangorestframework-simplejwt`:

```bash
pip install djangorestframework-simplejwt
```

**Update settings:**

```python
REST_FRAMEWORK = {
    'DEFAULT_AUTHENTICATION_CLASSES': [
        'rest_framework_simplejwt.authentication.JWTAuthentication',
    ],
}

from datetime import timedelta

SIMPLE_JWT = {
    'ACCESS_TOKEN_LIFETIME': timedelta(minutes=60),
    'REFRESH_TOKEN_LIFETIME': timedelta(days=1),
    'ROTATE_REFRESH_TOKENS': True,
}
```

**URLs:**

```python
from rest_framework_simplejwt.views import (
    TokenObtainPairView,
    TokenRefreshView,
)

urlpatterns = [
    path('api/token/', TokenObtainPairView.as_view(), name='token_obtain_pair'),
    path('api/token/refresh/', TokenRefreshView.as_view(), name='token_refresh'),
]
```

---

## CORS Configuration

For APIs consumed by frontend apps on different domains:

```bash
pip install django-cors-headers
```

**Update settings:**

```python
INSTALLED_APPS += ['corsheaders']

MIDDLEWARE = [
    'corsheaders.middleware.CorsMiddleware',
    'django.middleware.common.CommonMiddleware',
    # ... other middleware
]

# Development: Allow all origins
CORS_ALLOW_ALL_ORIGINS = True

# Production: Specify allowed origins
CORS_ALLOWED_ORIGINS = [
    "https://example.com",
    "https://sub.example.com",
]

# Allow credentials (cookies, auth headers)
CORS_ALLOW_CREDENTIALS = True
```

---

## Static and Media Files

### Development

Static files are served automatically by Django's development server.

### Production with WhiteNoise

```bash
pip install whitenoise
```

**Already configured in production.py:**

```python
MIDDLEWARE.insert(1, 'whitenoise.middleware.WhiteNoiseMiddleware')
STATICFILES_STORAGE = 'whitenoise.storage.CompressedManifestStaticFilesStorage'
```

**Collect static files:**

```bash
python manage.py collectstatic --noinput
```

---

## Logging Setup

Add to `base.py`:

```python
LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'verbose': {
            'format': '{levelname} {asctime} {module} {message}',
            'style': '{',
        },
    },
    'handlers': {
        'file': {
            'level': 'INFO',
            'class': 'logging.handlers.RotatingFileHandler',
            'filename': BASE_DIR / 'logs/django.log',
            'maxBytes': 1024 * 1024 * 10,  # 10 MB
            'backupCount': 10,
            'formatter': 'verbose',
        },
        'console': {
            'level': 'DEBUG',
            'class': 'logging.StreamHandler',
            'formatter': 'verbose',
        },
    },
    'loggers': {
        'django': {
            'handlers': ['file', 'console'],
            'level': 'INFO',
            'propagate': True,
        },
        'apps': {
            'handlers': ['file', 'console'],
            'level': 'DEBUG',
            'propagate': False,
        },
    },
}
```

---

## Security Checklist

### Before Deployment

- [ ] Set `DEBUG = False`
- [ ] Use strong `SECRET_KEY`
- [ ] Configure `ALLOWED_HOSTS` properly
- [ ] Enable HTTPS with SSL/TLS
- [ ] Set secure cookie flags
- [ ] Configure CORS properly
- [ ] Use environment variables for secrets
- [ ] Enable HSTS
- [ ] Set up rate limiting/throttling
- [ ] Configure proper permissions
- [ ] Sanitize user input
- [ ] Use parameterized queries (Django ORM does this)
- [ ] Keep dependencies updated
- [ ] Set up error monitoring (Sentry)
- [ ] Configure logging
- [ ] Review exposed endpoints

### Run Security Check

```bash
python manage.py check --deploy
```

---

## Deployment Preparation

### 1. Generate SECRET_KEY

```python
from django.core.management.utils import get_random_secret_key
print(get_random_secret_key())
```

### 2. Collect Static Files

```bash
python manage.py collectstatic --noinput
```

### 3. Run Migrations

```bash
python manage.py migrate
```

### 4. Create Superuser

```bash
python manage.py createsuperuser
```

### 5. Test Production Settings

```bash
DJANGO_SETTINGS_MODULE=config.settings.production python manage.py check --deploy
```

### 6. Run Server

**Development:**
```bash
python manage.py runserver
```

**Production (with Gunicorn):**
```bash
gunicorn config.wsgi:application --bind 0.0.0.0:8000 --workers 3
```

---

## Common Deployment Platforms

### Heroku

```bash
# Install Heroku CLI
heroku login

# Create app
heroku create myapp

# Add PostgreSQL
heroku addons:create heroku-postgresql:hobby-dev

# Set environment variables
heroku config:set SECRET_KEY=your-secret-key
heroku config:set DEBUG=False

# Deploy
git push heroku main

# Run migrations
heroku run python manage.py migrate

# Create superuser
heroku run python manage.py createsuperuser
```

### Docker

**Dockerfile:**
```dockerfile
FROM python:3.11-slim

ENV PYTHONUNBUFFERED=1

WORKDIR /app

COPY requirements/production.txt .
RUN pip install --no-cache-dir -r production.txt

COPY . .

RUN python manage.py collectstatic --noinput

CMD ["gunicorn", "config.wsgi:application", "--bind", "0.0.0.0:8000"]
```

**docker-compose.yml:**
```yaml
version: '3.8'

services:
  db:
    image: postgres:15
    environment:
      POSTGRES_DB: myproject
      POSTGRES_USER: myprojectuser
      POSTGRES_PASSWORD: password
    volumes:
      - postgres_data:/var/lib/postgresql/data

  web:
    build: .
    command: gunicorn config.wsgi:application --bind 0.0.0.0:8000
    volumes:
      - .:/app
    ports:
      - "8000:8000"
    depends_on:
      - db
    environment:
      - DATABASE_URL=postgresql://myprojectuser:password@db:5432/myproject
      - SECRET_KEY=your-secret-key
      - DEBUG=False

volumes:
  postgres_data:
```

---

## Next Steps

1. Set up continuous integration (GitHub Actions, GitLab CI)
2. Configure automated testing
3. Set up automated deployments
4. Monitor application performance
5. Set up backup strategies
6. Configure CDN for static files
7. Implement caching (Redis)
8. Set up load balancing (if needed)

## Resources

- [Django Deployment Checklist](https://docs.djangoproject.com/en/stable/howto/deployment/checklist/)
- [DRF Best Practices](https://www.django-rest-framework.org/#development)
- [Twelve-Factor App Methodology](https://12factor.net/)
