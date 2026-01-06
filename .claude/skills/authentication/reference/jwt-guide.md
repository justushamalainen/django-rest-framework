# JWT Authentication with SimpleJWT

Complete guide to implementing JWT authentication using djangorestframework-simplejwt, the most popular JWT library for Django REST Framework.

## Why JWT?

**Use JWT when you need:**
- Automatic token expiry and refresh
- Stateless authentication (no database lookups)
- Claims embedded in tokens
- Microservices architecture

**Don't use JWT when:**
- You need simple authentication (use Token)
- You need immediate token revocation
- Third-party API access (consider OAuth2)

## Installation

```bash
pip install djangorestframework-simplejwt
```

## Basic Configuration

```python
# settings.py
from datetime import timedelta

INSTALLED_APPS = [
    'rest_framework',
    'rest_framework_simplejwt',
]

REST_FRAMEWORK = {
    'DEFAULT_AUTHENTICATION_CLASSES': [
        'rest_framework_simplejwt.authentication.JWTAuthentication',
    ],
    'DEFAULT_PERMISSION_CLASSES': [
        'rest_framework.permissions.IsAuthenticated',
    ],
}

SIMPLE_JWT = {
    'ACCESS_TOKEN_LIFETIME': timedelta(minutes=15),
    'REFRESH_TOKEN_LIFETIME': timedelta(days=7),
    'ROTATE_REFRESH_TOKENS': True,
    'BLACKLIST_AFTER_ROTATION': True,
    'UPDATE_LAST_LOGIN': True,

    'ALGORITHM': 'HS256',
    'SIGNING_KEY': SECRET_KEY,
    'AUTH_HEADER_TYPES': ('Bearer',),
    'USER_ID_FIELD': 'id',
    'USER_ID_CLAIM': 'user_id',
}
```

## URL Configuration

```python
# urls.py
from rest_framework_simplejwt.views import (
    TokenObtainPairView,
    TokenRefreshView,
    TokenVerifyView,
)

urlpatterns = [
    path('api/token/', TokenObtainPairView.as_view(), name='token_obtain_pair'),
    path('api/token/refresh/', TokenRefreshView.as_view(), name='token_refresh'),
    path('api/token/verify/', TokenVerifyView.as_view(), name='token_verify'),
]
```

## Usage

### Login and Get Tokens

```bash
POST /api/token/
{
    "username": "john",
    "password": "secret123"
}

# Response:
{
    "access": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
    "refresh": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."
}
```

### Use Access Token

```bash
GET /api/protected/
Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...
```

### Refresh Access Token

```bash
POST /api/token/refresh/
{
    "refresh": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."
}

# Response:
{
    "access": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
    "refresh": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."  # New if ROTATE_REFRESH_TOKENS
}
```

## Custom Claims

Add custom data to tokens:

```python
# myapp/serializers.py
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer

class CustomTokenObtainPairSerializer(TokenObtainPairSerializer):
    @classmethod
    def get_token(cls, user):
        token = super().get_token(user)

        # Add custom claims
        token['username'] = user.username
        token['email'] = user.email
        token['is_staff'] = user.is_staff

        return token

# myapp/views.py
from rest_framework_simplejwt.views import TokenObtainPairView

class CustomTokenObtainPairView(TokenObtainPairView):
    serializer_class = CustomTokenObtainPairSerializer

# urls.py
urlpatterns = [
    path('api/token/', CustomTokenObtainPairView.as_view()),
]
```

## Token Blacklisting (Logout)

Enable blacklisting to support logout:

```python
# settings.py
INSTALLED_APPS = [
    'rest_framework_simplejwt.token_blacklist',
]

SIMPLE_JWT = {
    'ROTATE_REFRESH_TOKENS': True,
    'BLACKLIST_AFTER_ROTATION': True,
}
```

```bash
python manage.py migrate
```

```python
# views.py
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from rest_framework_simplejwt.tokens import RefreshToken

class LogoutView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        try:
            refresh_token = request.data["refresh"]
            token = RefreshToken(refresh_token)
            token.blacklist()

            return Response({"detail": "Successfully logged out"})
        except Exception as e:
            return Response({"detail": str(e)}, status=400)
```

## Frontend Integration (React)

```javascript
// authService.js
class AuthService {
    constructor() {
        this.accessToken = null;
        this.refreshToken = null;
    }

    async login(username, password) {
        const response = await fetch('/api/token/', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ username, password })
        });

        if (response.ok) {
            const data = await response.json();
            this.accessToken = data.access;
            this.refreshToken = data.refresh;
            return true;
        }
        return false;
    }

    async apiCall(url, options = {}) {
        options.headers = {
            ...options.headers,
            'Authorization': `Bearer ${this.accessToken}`
        };

        let response = await fetch(url, options);

        // Auto-refresh on 401
        if (response.status === 401) {
            const refreshed = await this.refreshAccessToken();
            if (refreshed) {
                options.headers['Authorization'] = `Bearer ${this.accessToken}`;
                response = await fetch(url, options);
            }
        }

        return response;
    }

    async refreshAccessToken() {
        try {
            const response = await fetch('/api/token/refresh/', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ refresh: this.refreshToken })
            });

            if (response.ok) {
                const data = await response.json();
                this.accessToken = data.access;
                if (data.refresh) {
                    this.refreshToken = data.refresh;
                }
                return true;
            }
        } catch (error) {
            console.error('Token refresh failed:', error);
        }
        return false;
    }

    async logout() {
        await fetch('/api/logout/', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'Authorization': `Bearer ${this.accessToken}`
            },
            body: JSON.stringify({ refresh: this.refreshToken })
        });

        this.accessToken = null;
        this.refreshToken = null;
    }
}

export default new AuthService();
```

## Security Best Practices

### 1. Short Access Token Lifetime

```python
SIMPLE_JWT = {
    'ACCESS_TOKEN_LIFETIME': timedelta(minutes=5),  # Short
    'REFRESH_TOKEN_LIFETIME': timedelta(days=1),    # Longer
}
```

### 2. Rotate Refresh Tokens

```python
SIMPLE_JWT = {
    'ROTATE_REFRESH_TOKENS': True,
    'BLACKLIST_AFTER_ROTATION': True,
}
```

### 3. Store Tokens Securely

```javascript
// ✅ BEST: In-memory only
let accessToken = data.access;
let refreshToken = data.refresh;

// ⚠️ ACCEPTABLE: httpOnly cookies (server-side)
// Set-Cookie: refresh_token=...; HttpOnly; Secure; SameSite=Strict

// ❌ AVOID: localStorage (XSS vulnerable)
localStorage.setItem('access', data.access);
```

### 4. HTTPS Required

```python
# settings.py
SECURE_SSL_REDIRECT = True
```

### 5. Token Claims Validation

```python
# Custom authentication to validate claims
from rest_framework_simplejwt.authentication import JWTAuthentication
from rest_framework import exceptions

class CustomJWTAuthentication(JWTAuthentication):
    def get_user(self, validated_token):
        user = super().get_user(validated_token)

        # Custom validation
        if not user.is_active:
            raise exceptions.AuthenticationFailed('User inactive')

        return user
```

## JWT vs Token Comparison

| Feature | JWT | DRF Token |
|---------|-----|-----------|
| **Database lookup** | No (stateless) | Yes |
| **Token expiry** | Built-in | No (manual) |
| **Refresh tokens** | Yes | No |
| **Claims in token** | Yes | No |
| **Revocation** | Limited (blacklist) | Immediate (delete) |
| **Multi-device** | Yes | One token per user |
| **Performance** | Faster | Slower |

## Common Settings

```python
SIMPLE_JWT = {
    # Token lifetimes
    'ACCESS_TOKEN_LIFETIME': timedelta(minutes=15),
    'REFRESH_TOKEN_LIFETIME': timedelta(days=7),

    # Rotation
    'ROTATE_REFRESH_TOKENS': True,
    'BLACKLIST_AFTER_ROTATION': True,

    # User tracking
    'UPDATE_LAST_LOGIN': True,

    # Algorithm
    'ALGORITHM': 'HS256',  # or 'RS256' for asymmetric
    'SIGNING_KEY': SECRET_KEY,

    # Header
    'AUTH_HEADER_TYPES': ('Bearer',),
    'AUTH_HEADER_NAME': 'HTTP_AUTHORIZATION',

    # Claims
    'USER_ID_FIELD': 'id',
    'USER_ID_CLAIM': 'user_id',
    'TOKEN_TYPE_CLAIM': 'token_type',
    'JTI_CLAIM': 'jti',

    # Sliding tokens (alternative to refresh)
    'SLIDING_TOKEN_LIFETIME': timedelta(minutes=5),
    'SLIDING_TOKEN_REFRESH_LIFETIME': timedelta(days=1),
}
```

## Troubleshooting

### Token has expired

Ensure client refreshes before expiry:
```javascript
// Check token expiry before each request
const tokenExpiry = JSON.parse(atob(token.split('.')[1])).exp;
if (Date.now() >= tokenExpiry * 1000) {
    await refreshAccessToken();
}
```

### Token verification failed

Check SIGNING_KEY matches between token creation and verification:
```python
# Both must use same SECRET_KEY
SIMPLE_JWT = {
    'SIGNING_KEY': SECRET_KEY,
}
```

### "Authorization header must contain two space-delimited values"

Check header format:
```bash
# ✅ Correct
Authorization: Bearer eyJhbGci...

# ❌ Wrong
Authorization: eyJhbGci...  # Missing "Bearer"
```

## Need OAuth2?

For third-party API access with fine-grained permissions, use **django-oauth-toolkit**:

```bash
pip install django-oauth-toolkit
```

OAuth2 provides:
- Authorization code flow
- Client credentials flow
- Scope-based permissions
- Token management UI

See: https://django-oauth-toolkit.readthedocs.io/

## References

- **SimpleJWT Docs**: https://django-rest-framework-simplejwt.readthedocs.io/
- **JWT Spec**: https://tools.ietf.org/html/rfc7519
- **DRF Auth**: `/home/user/django-rest-framework/rest_framework/authentication.py`
