# Token Authentication Setup Guide

Step-by-step setup for TokenAuthentication with lifecycle management and security best practices.

## Basic Setup

### 1. Install and Configure

```python
# settings.py
INSTALLED_APPS = [
    'rest_framework',
    'rest_framework.authtoken',  # Add this
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

### 2. Run Migrations

```bash
python manage.py migrate
# Creates authtoken_token table with: key, user, created
```

### 3. Create Login Endpoint

```python
# urls.py
from rest_framework.authtoken import views

urlpatterns = [
    path('api/auth/login/', views.obtain_auth_token),
]
```

### 4. Test It

```bash
# Login
curl -X POST http://localhost:8000/api/auth/login/ \
    -d "username=john" -d "password=secret123"
# Response: {"token": "9944b09199c62bcf9418ad846dd0e4bbdfc6ee4b"}

# Use token
curl -H "Authorization: Token 9944b09199c62bcf9418ad846dd0e4bbdfc6ee4b" \
    http://localhost:8000/api/protected/
```

## Token Generation

### Option 1: Automatic on User Creation (Signal)

```python
# myapp/signals.py
from django.conf import settings
from django.db.models.signals import post_save
from django.dispatch import receiver
from rest_framework.authtoken.models import Token

@receiver(post_save, sender=settings.AUTH_USER_MODEL)
def create_auth_token(sender, instance=None, created=False, **kwargs):
    if created:
        Token.objects.create(user=instance)

# myapp/apps.py
class MyappConfig(AppConfig):
    name = 'myapp'

    def ready(self):
        import myapp.signals
```

### Option 2: Custom Login Endpoint

```python
# views.py
from rest_framework.authtoken.views import ObtainAuthToken
from rest_framework.authtoken.models import Token
from rest_framework.response import Response

class CustomAuthToken(ObtainAuthToken):
    def post(self, request, *args, **kwargs):
        serializer = self.serializer_class(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.validated_data['user']

        token, created = Token.objects.get_or_create(user=user)

        return Response({
            'token': token.key,
            'user_id': user.pk,
            'username': user.username,
        })
```

## Token Lifecycle

### Logout

```python
# views.py
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated

class LogoutView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        request.auth.delete()
        return Response({'detail': 'Logged out successfully'})
```

### Token Rotation

```python
class RotateTokenView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        request.auth.delete()
        token = Token.objects.create(user=request.user)
        return Response({'token': token.key})
```

## Security Checklist

### 1. HTTPS Only

```python
# settings.py - Production
SECURE_SSL_REDIRECT = True
SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')
```

### 2. Rate Limiting

```python
from rest_framework.throttling import AnonRateThrottle

class LoginRateThrottle(AnonRateThrottle):
    rate = '5/hour'

class LoginView(ObtainAuthToken):
    throttle_classes = [LoginRateThrottle]
```

### 3. Token in Headers Only

```python
# ✅ GOOD: Authorization header
Authorization: Token 9944b09199c62bcf9418ad846dd0e4bbdfc6ee4b

# ❌ BAD: URL parameter (gets logged)
/api/resource/?token=9944b09199c62bcf9418ad846dd0e4bbdfc6ee4b
```

### 4. Secure Client Storage

```javascript
// ✅ BEST: In-memory (requires refresh handling)
let authToken = response.token;

// ⚠️ RISKY: localStorage (vulnerable to XSS)
localStorage.setItem('token', response.token);
```

### 5. Token Expiry

Default tokens don't expire. For expiring tokens, use **django-rest-knox**:

```bash
pip install django-rest-knox
```

Knox provides:
- Token expiry
- Multiple tokens per user (multi-device)
- Per-token device tracking
- Logout from specific device

## Troubleshooting

### "Invalid token" error

Check token format:
```bash
# ✅ Correct
curl -H "Authorization: Token abc123..."

# ❌ Wrong
curl -H "Authorization: Bearer abc123..."  # Wrong keyword
curl -H "Authorization: Token: abc123..."  # Extra colon
```

### CORS issues

```python
# Install django-cors-headers
pip install django-cors-headers

# settings.py
INSTALLED_APPS = ['corsheaders', ...]
MIDDLEWARE = ['corsheaders.middleware.CorsMiddleware', ...]

CORS_ALLOWED_ORIGINS = [
    "http://localhost:3000",
]

CORS_ALLOW_HEADERS = [
    'authorization',  # Must include this
    'content-type',
]
```

### Token not created

Ensure signal is connected:
```python
# Check in apps.py
def ready(self):
    import myapp.signals  # Must import
```

## Next Steps

- **JWT Guide** → [jwt-guide.md](jwt-guide.md) - Token expiry and refresh
- **DRF Source** → `/home/user/django-rest-framework/rest_framework/authentication.py`
- **Token Models** → `/home/user/django-rest-framework/rest_framework/authtoken/models.py`
