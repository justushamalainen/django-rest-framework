# Complete Token Authentication Setup Guide

This guide provides end-to-end setup for TokenAuthentication with lifecycle management, security best practices, and troubleshooting.

## Table of Contents
1. [Basic Setup](#basic-setup)
2. [Token Generation Strategies](#token-generation-strategies)
3. [Token Lifecycle Management](#token-lifecycle-management)
4. [Security Checklist](#security-checklist)
5. [Advanced Features](#advanced-features)
6. [Troubleshooting](#troubleshooting)

---

## Basic Setup

### Step 1: Install and Configure

```python
# settings.py
INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'rest_framework',
    'rest_framework.authtoken',  # Add this line
    'myapp',
]

REST_FRAMEWORK = {
    'DEFAULT_AUTHENTICATION_CLASSES': [
        'rest_framework.authentication.TokenAuthentication',
    ],
    'DEFAULT_PERMISSION_CLASSES': [
        'rest_framework.permissions.IsAuthenticated',
    ],
}
```

### Step 2: Run Migrations

```bash
python manage.py migrate

# This creates the authtoken_token table:
# - key (CharField, max_length=40, primary_key)
# - user (OneToOneField to User)
# - created (DateTimeField, auto_now_add)
```

### Step 3: Create Login Endpoint

```python
# urls.py
from django.urls import path
from rest_framework.authtoken import views as auth_views
from . import views

urlpatterns = [
    # Built-in token auth endpoint
    path('api/auth/login/', auth_views.obtain_auth_token, name='api_login'),

    # Your protected endpoints
    path('api/profile/', views.UserProfileView.as_view(), name='user_profile'),
]
```

### Step 4: Create Protected Views

```python
# views.py
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated

class UserProfileView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        return Response({
            'username': request.user.username,
            'email': request.user.email,
            'token_created': request.auth.created,  # request.auth is Token instance
        })
```

### Step 5: Test with curl

```bash
# Login and get token
curl -X POST http://localhost:8000/api/auth/login/ \
    -H "Content-Type: application/json" \
    -d '{"username": "john", "password": "secret123"}'

# Response:
# {"token": "9944b09199c62bcf9418ad846dd0e4bbdfc6ee4b"}

# Use token to access protected endpoint
curl -X GET http://localhost:8000/api/profile/ \
    -H "Authorization: Token 9944b09199c62bcf9418ad846dd0e4bbdfc6ee4b"
```

---

## Token Generation Strategies

### Strategy 1: Automatic Token on User Creation (via Signals)

**Best for:** Every user should have a token by default.

```python
# myapp/signals.py
from django.conf import settings
from django.db.models.signals import post_save
from django.dispatch import receiver
from rest_framework.authtoken.models import Token

@receiver(post_save, sender=settings.AUTH_USER_MODEL)
def create_auth_token(sender, instance=None, created=False, **kwargs):
    """
    Automatically create a token whenever a new user is created.
    """
    if created:
        Token.objects.create(user=instance)

# myapp/apps.py
from django.apps import AppConfig

class MyappConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'myapp'

    def ready(self):
        import myapp.signals  # Import signals
```

**Generate tokens for existing users:**
```bash
python manage.py shell
>>> from django.contrib.auth import get_user_model
>>> from rest_framework.authtoken.models import Token
>>> User = get_user_model()
>>> for user in User.objects.all():
...     Token.objects.get_or_create(user=user)
```

### Strategy 2: Token on Login (Explicit)

**Best for:** Tokens created only when user explicitly logs in via API.

```python
# views.py
from rest_framework.authtoken.views import ObtainAuthToken
from rest_framework.authtoken.models import Token
from rest_framework.response import Response

class CustomAuthToken(ObtainAuthToken):
    """
    Custom login endpoint that returns additional user info.
    """
    def post(self, request, *args, **kwargs):
        serializer = self.serializer_class(
            data=request.data,
            context={'request': request}
        )
        serializer.is_valid(raise_exception=True)
        user = serializer.validated_data['user']

        # Get or create token
        token, created = Token.objects.get_or_create(user=user)

        return Response({
            'token': token.key,
            'user_id': user.pk,
            'username': user.username,
            'email': user.email,
            'is_new_token': created,
        })

# urls.py
urlpatterns = [
    path('api/auth/login/', CustomAuthToken.as_view(), name='api_login'),
]
```

### Strategy 3: Management Command

**Best for:** Creating tokens for specific users or batch operations.

```bash
# Django >= 3.6.4 includes built-in command
python manage.py drf_create_token username

# Output:
# Generated token 9944b09199c62bcf9418ad846dd0e4bbdfc6ee4b for user username

# Regenerate token (if compromised)
python manage.py drf_create_token -r username
```

### Strategy 4: Django Admin

**Best for:** Manual token management for specific users.

```python
# myapp/admin.py
from rest_framework.authtoken.admin import TokenAdmin

# Optimize for large user bases
TokenAdmin.raw_id_fields = ['user']
```

Access at: `http://localhost:8000/admin/authtoken/token/`

---

## Token Lifecycle Management

### Login Flow

```python
# views.py
from rest_framework.authtoken.views import ObtainAuthToken
from rest_framework.authtoken.models import Token
from rest_framework.response import Response
from django.utils import timezone

class LoginView(ObtainAuthToken):
    def post(self, request, *args, **kwargs):
        serializer = self.serializer_class(
            data=request.data,
            context={'request': request}
        )
        serializer.is_valid(raise_exception=True)
        user = serializer.validated_data['user']

        # Get or create token
        token, created = Token.objects.get_or_create(user=user)

        # Optional: Track last login
        user.last_login = timezone.now()
        user.save(update_fields=['last_login'])

        return Response({
            'token': token.key,
            'user_id': user.pk,
            'username': user.username,
        })
```

### Logout Flow

```python
# views.py
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from rest_framework import status

class LogoutView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        # Delete the user's token
        request.auth.delete()

        return Response({
            'detail': 'Successfully logged out.'
        }, status=status.HTTP_200_OK)

# urls.py
urlpatterns = [
    path('api/auth/logout/', LogoutView.as_view(), name='api_logout'),
]
```

### Token Rotation

```python
# views.py
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from rest_framework.authtoken.models import Token

class RotateTokenView(APIView):
    """
    Rotate user's token (delete old, create new).
    Use when token may be compromised.
    """
    permission_classes = [IsAuthenticated]

    def post(self, request):
        # Delete old token
        request.auth.delete()

        # Create new token
        token = Token.objects.create(user=request.user)

        return Response({
            'token': token.key,
            'detail': 'Token rotated successfully.'
        })

# urls.py
urlpatterns = [
    path('api/auth/rotate-token/', RotateTokenView.as_view(), name='rotate_token'),
]
```

### Token Expiry (Custom Implementation)

**Note:** Default Token model doesn't have expiry. Here's how to add it:

```python
# myapp/models.py
from django.db import models
from django.conf import settings
from rest_framework.authtoken.models import Token as DefaultToken
from django.utils import timezone
from datetime import timedelta

class ExpiringToken(models.Model):
    """
    Token with expiration time.
    Alternative: Use django-rest-knox package for this functionality.
    """
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='expiring_auth_token'
    )
    key = models.CharField(max_length=40, primary_key=True)
    created = models.DateTimeField(auto_now_add=True)
    expires_in = models.DurationField(default=timedelta(days=7))

    def save(self, *args, **kwargs):
        if not self.key:
            self.key = self.generate_key()
        return super().save(*args, **kwargs)

    @staticmethod
    def generate_key():
        import secrets
        return secrets.token_hex(20)

    def is_expired(self):
        return timezone.now() > (self.created + self.expires_in)

    def __str__(self):
        return self.key

# myapp/authentication.py
from rest_framework.authentication import TokenAuthentication
from rest_framework import exceptions
from .models import ExpiringToken

class ExpiringTokenAuthentication(TokenAuthentication):
    model = ExpiringToken

    def authenticate_credentials(self, key):
        try:
            token = self.model.objects.select_related('user').get(key=key)
        except self.model.DoesNotExist:
            raise exceptions.AuthenticationFailed('Invalid token.')

        if not token.user.is_active:
            raise exceptions.AuthenticationFailed('User inactive or deleted.')

        if token.is_expired():
            # Delete expired token
            token.delete()
            raise exceptions.AuthenticationFailed('Token has expired.')

        return (token.user, token)

# settings.py
REST_FRAMEWORK = {
    'DEFAULT_AUTHENTICATION_CLASSES': [
        'myapp.authentication.ExpiringTokenAuthentication',
    ],
}
```

### Cleanup Expired Tokens (Management Command)

```python
# myapp/management/commands/cleanup_tokens.py
from django.core.management.base import BaseCommand
from django.utils import timezone
from myapp.models import ExpiringToken

class Command(BaseCommand):
    help = 'Delete expired authentication tokens'

    def handle(self, *args, **options):
        now = timezone.now()
        expired_tokens = ExpiringToken.objects.filter(
            created__lt=now - models.F('expires_in')
        )
        count = expired_tokens.count()
        expired_tokens.delete()
        self.stdout.write(
            self.style.SUCCESS(f'Deleted {count} expired tokens')
        )

# Run via cron:
# 0 0 * * * python manage.py cleanup_tokens
```

---

## Security Checklist

### ✅ Essential Security Measures

#### 1. HTTPS Only (Critical)

```python
# settings.py - Production
SECURE_SSL_REDIRECT = True
SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')

# Never send tokens over HTTP
if not settings.DEBUG:
    assert SECURE_SSL_REDIRECT, "HTTPS must be enforced in production"
```

#### 2. Secure Token Storage (Client-side)

```javascript
// ❌ BAD: localStorage is vulnerable to XSS
localStorage.setItem('token', response.token);

// ✅ BETTER: In-memory storage (lost on page refresh)
let authToken = null;

async function login(username, password) {
    const response = await fetch('/api/auth/login/', {
        method: 'POST',
        body: JSON.stringify({ username, password }),
    });
    const data = await response.json();
    authToken = data.token;  // Store in memory
}

// ✅ BEST: Use HttpOnly cookies (if possible)
// Server sets: Set-Cookie: token=...; HttpOnly; Secure; SameSite=Strict
```

#### 3. Rate Limiting

```python
# settings.py
REST_FRAMEWORK = {
    'DEFAULT_THROTTLE_CLASSES': [
        'rest_framework.throttling.AnonRateThrottle',
        'rest_framework.throttling.UserRateThrottle'
    ],
    'DEFAULT_THROTTLE_RATES': {
        'anon': '100/hour',
        'user': '1000/hour',
        'login': '5/hour',  # Custom rate for login
    }
}

# views.py
from rest_framework.throttling import AnonRateThrottle

class LoginRateThrottle(AnonRateThrottle):
    rate = '5/hour'

class LoginView(ObtainAuthToken):
    throttle_classes = [LoginRateThrottle]
```

#### 4. Token Validation

```python
# Always check user is active and token is valid
class TokenAuthentication(BaseAuthentication):
    def authenticate_credentials(self, key):
        try:
            token = Token.objects.select_related('user').get(key=key)
        except Token.DoesNotExist:
            raise exceptions.AuthenticationFailed('Invalid token.')

        if not token.user.is_active:
            raise exceptions.AuthenticationFailed('User inactive or deleted.')

        # Optional: Check token age
        if (timezone.now() - token.created).days > 30:
            raise exceptions.AuthenticationFailed('Token expired.')

        return (token.user, token)
```

#### 5. Audit Logging

```python
# Log authentication attempts
import logging
logger = logging.getLogger(__name__)

class LoginView(ObtainAuthToken):
    def post(self, request, *args, **kwargs):
        try:
            serializer = self.serializer_class(data=request.data)
            serializer.is_valid(raise_exception=True)
            user = serializer.validated_data['user']

            # Log successful login
            logger.info(f'Successful login for user {user.username} from {request.META.get("REMOTE_ADDR")}')

            token, created = Token.objects.get_or_create(user=user)
            return Response({'token': token.key})

        except Exception as e:
            # Log failed login attempt
            logger.warning(f'Failed login attempt from {request.META.get("REMOTE_ADDR")}: {str(e)}')
            raise
```

#### 6. Token in Authorization Header (Not URL)

```python
# ❌ BAD: Token in URL (logged by servers, cached)
/api/resource/?token=9944b09199c62bcf9418ad846dd0e4bbdfc6ee4b

# ✅ GOOD: Token in Authorization header
GET /api/resource/
Authorization: Token 9944b09199c62bcf9418ad846dd0e4bbdfc6ee4b
```

#### 7. Invalidate Tokens on Password Change

```python
# myapp/signals.py
from django.contrib.auth.signals import user_logged_in
from django.dispatch import receiver
from rest_framework.authtoken.models import Token

@receiver(user_logged_in)
def invalidate_token_on_password_change(sender, request, user, **kwargs):
    """
    Delete token when password changes to force re-login.
    """
    if hasattr(user, 'auth_token'):
        user.auth_token.delete()
```

### 🔒 Advanced Security Measures

#### 8. IP Whitelisting (Optional)

```python
# myapp/authentication.py
from rest_framework.authentication import TokenAuthentication
from rest_framework import exceptions

class IPRestrictedTokenAuthentication(TokenAuthentication):
    def authenticate_credentials(self, key):
        user, token = super().authenticate_credentials(key)

        # Check IP address
        ip = self.get_client_ip(self.request)
        if not self.is_ip_allowed(ip, user):
            raise exceptions.AuthenticationFailed('Access denied from this IP.')

        return (user, token)

    def get_client_ip(self, request):
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            ip = x_forwarded_for.split(',')[0]
        else:
            ip = request.META.get('REMOTE_ADDR')
        return ip

    def is_ip_allowed(self, ip, user):
        # Implement your IP whitelist logic
        allowed_ips = ['192.168.1.0/24', '10.0.0.0/8']
        # ... check if ip in allowed_ips
        return True
```

#### 9. Token Prefix/Versioning

```python
# Helps identify token type and version
class VersionedTokenAuthentication(TokenAuthentication):
    keyword = 'Bearer'

    def authenticate_credentials(self, key):
        # Support versioned tokens: v1_<token>, v2_<token>
        if '_' in key:
            version, actual_key = key.split('_', 1)
            if version == 'v1':
                return self.authenticate_v1(actual_key)
            elif version == 'v2':
                return self.authenticate_v2(actual_key)

        return super().authenticate_credentials(key)
```

---

## Advanced Features

### Multiple Tokens Per User (Multi-device Support)

**Use Case:** User logs in from phone, tablet, and desktop - each gets separate token.

**Solution:** Use [django-rest-knox](https://github.com/James1345/django-rest-knox) package.

```bash
pip install django-rest-knox
```

```python
# settings.py
INSTALLED_APPS = [
    ...
    'knox',
]

REST_FRAMEWORK = {
    'DEFAULT_AUTHENTICATION_CLASSES': [
        'knox.auth.TokenAuthentication',
    ],
}

# Run migrations
python manage.py migrate
```

```python
# urls.py
from knox import views as knox_views

urlpatterns = [
    path('api/auth/login/', LoginView.as_view(), name='knox_login'),
    path('api/auth/logout/', knox_views.LogoutView.as_view(), name='knox_logout'),
    path('api/auth/logoutall/', knox_views.LogoutAllView.as_view(), name='knox_logoutall'),
]
```

Knox provides:
- Multiple tokens per user
- Token expiry
- Token refresh
- Per-token device tracking
- Logout from specific device
- Logout from all devices

### Custom Token Generation

```python
# Generate stronger tokens
from rest_framework.authtoken.models import Token
import secrets

class SecureToken(Token):
    class Meta:
        proxy = True

    @staticmethod
    def generate_key():
        # Generate 32-byte (256-bit) token
        return secrets.token_urlsafe(32)
```

### Token in Custom Header

```python
# Accept token in X-API-Key header instead of Authorization
class CustomHeaderTokenAuthentication(TokenAuthentication):
    def authenticate(self, request):
        # Try custom header first
        token = request.META.get('HTTP_X_API_KEY')
        if token:
            return self.authenticate_credentials(token)

        # Fall back to standard Authorization header
        return super().authenticate(request)
```

---

## Troubleshooting

### Issue 1: "Invalid token" error

**Symptoms:** Token exists in database but authentication fails.

**Causes:**
1. Token not being sent correctly
2. Wrong authorization format
3. Whitespace in token

**Debug:**
```python
# Check what's being sent
print(request.META.get('HTTP_AUTHORIZATION'))
# Should be: b'Token 9944b09199c62bcf9418ad846dd0e4bbdfc6ee4b'

# Check token in database
from rest_framework.authtoken.models import Token
token = Token.objects.get(key='9944b09199c62bcf9418ad846dd0e4bbdfc6ee4b')
print(token.user, token.user.is_active)
```

**Fix:**
```bash
# Correct format
curl -H "Authorization: Token 9944b09199c62bcf9418ad846dd0e4bbdfc6ee4b" ...

# ❌ Wrong formats:
# "Bearer 9944b09..." (wrong keyword)
# "Token: 9944b09..." (colon after Token)
# "Token9944b09..." (no space)
```

### Issue 2: Token not created on user creation

**Cause:** Signal not connected or not in installed app.

**Fix:**
```python
# Ensure signal is imported in apps.py
class MyappConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'myapp'

    def ready(self):
        import myapp.signals  # This imports and connects signals

# Create tokens for existing users
from django.contrib.auth import get_user_model
from rest_framework.authtoken.models import Token
for user in get_user_model().objects.all():
    Token.objects.get_or_create(user=user)
```

### Issue 3: CORS issues with token authentication

**Cause:** Browser not sending Authorization header due to CORS.

**Fix:**
```python
# Install django-cors-headers
pip install django-cors-headers

# settings.py
INSTALLED_APPS = [
    ...
    'corsheaders',
]

MIDDLEWARE = [
    'corsheaders.middleware.CorsMiddleware',
    'django.middleware.common.CommonMiddleware',
    ...
]

CORS_ALLOWED_ORIGINS = [
    "http://localhost:3000",  # React dev server
    "https://myapp.com",
]

# Allow Authorization header
CORS_ALLOW_HEADERS = [
    'accept',
    'accept-encoding',
    'authorization',  # Important!
    'content-type',
    'dnt',
    'origin',
    'user-agent',
    'x-csrftoken',
    'x-requested-with',
]
```

### Issue 4: Performance issues with token lookup

**Cause:** N+1 queries or missing database index.

**Fix:**
```python
# Use select_related to avoid N+1
token = Token.objects.select_related('user').get(key=key)

# Ensure database index on key field (already exists as primary key)

# For custom token models, add index:
class CustomToken(models.Model):
    key = models.CharField(max_length=40, db_index=True)
```

### Issue 5: Token doesn't work in production

**Checklist:**
```python
# 1. Check authtoken app is installed
assert 'rest_framework.authtoken' in settings.INSTALLED_APPS

# 2. Check migrations are run
python manage.py showmigrations authtoken

# 3. Check authentication class is configured
print(settings.REST_FRAMEWORK['DEFAULT_AUTHENTICATION_CLASSES'])

# 4. Check HTTPS is enforced
print(settings.SECURE_SSL_REDIRECT)

# 5. Check for Apache/Nginx blocking Authorization header
# Apache: WSGIPassAuthorization On
# Nginx: proxy_pass_header Authorization;
```

### Issue 6: "Authentication credentials were not provided"

**Cause:** Request not including token or wrong format.

**Debug:**
```python
# Add custom exception handler to log details
from rest_framework.views import exception_handler
import logging

logger = logging.getLogger(__name__)

def custom_exception_handler(exc, context):
    response = exception_handler(exc, context)

    if response is not None and response.status_code == 401:
        request = context.get('request')
        logger.error(f'Authentication failed: {exc}')
        logger.error(f'Headers: {request.META}')

    return response

# settings.py
REST_FRAMEWORK = {
    'EXCEPTION_HANDLER': 'myapp.handlers.custom_exception_handler'
}
```

---

## Next Steps

- **Built-in Auth Classes** → [builtin-auth.md](builtin-auth.md)
- **Custom Authentication** → [custom-auth.md](custom-auth.md)
- **JWT vs OAuth** → [jwt-oauth-guide.md](jwt-oauth-guide.md)
- **Code Examples** → [examples/auth-patterns.py](examples/auth-patterns.py)

## References

- DRF Source: `/home/user/django-rest-framework/rest_framework/authentication.py`
- Token Models: `/home/user/django-rest-framework/rest_framework/authtoken/models.py`
- Token Views: `/home/user/django-rest-framework/rest_framework/authtoken/views.py`
- Official Docs: `/home/user/django-rest-framework/docs/api-guide/authentication.md`
