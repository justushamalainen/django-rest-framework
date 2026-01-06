# Built-in Authentication Classes

Django REST Framework provides four built-in authentication classes. This guide explains each in detail with practical examples and best practices.

## Overview

All authentication classes inherit from `BaseAuthentication` and implement:
- `authenticate(request)` - Returns `(user, auth)` tuple or `None`
- `authenticate_header(request)` - Returns WWW-Authenticate header value (optional)

**Key Concept**: DRF tries each authentication class in order. The first successful authentication sets `request.user` and `request.auth`. If all return `None`, the user is `AnonymousUser`.

## BasicAuthentication

### What It Is
HTTP Basic Authentication using username and password encoded in the Authorization header.

### How It Works
```
Authorization: Basic dXNlcm5hbWU6cGFzc3dvcmQ=
                     └── base64("username:password")
```

### Configuration
```python
# settings.py
REST_FRAMEWORK = {
    'DEFAULT_AUTHENTICATION_CLASSES': [
        'rest_framework.authentication.BasicAuthentication',
    ],
}

# Or per-view
from rest_framework.authentication import BasicAuthentication
from rest_framework.permissions import IsAuthenticated

class MyView(APIView):
    authentication_classes = [BasicAuthentication]
    permission_classes = [IsAuthenticated]
```

### Request/Response Credentials
- `request.user` → Django `User` instance
- `request.auth` → `None`
- Failed auth → `401 Unauthorized` with `WWW-Authenticate: Basic realm="api"`

### When to Use
✅ **Good for:**
- Local development and testing
- Internal admin tools over VPN
- Quick prototyping
- Integration test suites

❌ **Bad for:**
- Production APIs (credentials in every request)
- Public-facing services
- Mobile applications

### Example: Testing View
```python
from rest_framework.test import APITestCase
from django.contrib.auth import get_user_model
import base64

class MyAPITest(APITestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user(
            username='testuser',
            password='testpass123'
        )

    def test_with_basic_auth(self):
        credentials = base64.b64encode(b'testuser:testpass123').decode('ascii')
        self.client.credentials(HTTP_AUTHORIZATION=f'Basic {credentials}')
        response = self.client.get('/api/resource/')
        self.assertEqual(response.status_code, 200)
```

### Custom Realm
```python
from rest_framework.authentication import BasicAuthentication

class MyBasicAuthentication(BasicAuthentication):
    www_authenticate_realm = 'my-secure-api'
    # Returns: WWW-Authenticate: Basic realm="my-secure-api"
```

### Security Considerations
⚠️ **Critical Requirements:**
1. **HTTPS Only** - Credentials are only base64 encoded, not encrypted
2. **Short-lived Sessions** - Don't cache credentials
3. **Rate Limiting** - Prevent brute force attacks
4. **Strong Passwords** - Enforce password policies

```python
# Enforce HTTPS in production
SECURE_SSL_REDIRECT = True

# Use with rate limiting
from rest_framework.throttling import UserRateThrottle

class ProtectedView(APIView):
    authentication_classes = [BasicAuthentication]
    throttle_classes = [UserRateThrottle]
```

---

## SessionAuthentication

### What It Is
Uses Django's session framework. User logs in once, then Django session cookie authenticates subsequent requests.

### How It Works
1. User logs in via Django's login view
2. Server sets `sessionid` cookie
3. API requests include cookie automatically (same-origin)
4. DRF validates session and enforces CSRF protection

### Configuration
```python
# settings.py
INSTALLED_APPS = [
    'django.contrib.sessions',  # Required
    ...
]

MIDDLEWARE = [
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',  # Required for CSRF
    ...
]

REST_FRAMEWORK = {
    'DEFAULT_AUTHENTICATION_CLASSES': [
        'rest_framework.authentication.SessionAuthentication',
    ],
}
```

### Request/Response Credentials
- `request.user` → Django `User` instance from session
- `request.auth` → `None`
- Failed auth → `403 Forbidden` (no WWW-Authenticate header)

### When to Use
✅ **Good for:**
- Same-origin AJAX requests
- Hybrid apps (traditional Django + API)
- Browsable API interface
- When you want Django's login views

❌ **Bad for:**
- Mobile applications (cookies are problematic)
- Third-party API consumers
- Cross-origin requests (CORS complexity)
- Stateless architectures

### Example: SPA with Session Auth
```python
# views.py
from django.contrib.auth import login
from django.contrib.auth.forms import AuthenticationForm
from rest_framework.decorators import api_view, authentication_classes, permission_classes
from rest_framework.authentication import SessionAuthentication
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

@api_view(['POST'])
@authentication_classes([])  # No auth for login
@permission_classes([])
def login_view(request):
    form = AuthenticationForm(data=request.data)
    if form.is_valid():
        user = form.get_user()
        login(request, user)
        return Response({'detail': 'Logged in successfully'})
    return Response(form.errors, status=400)

@api_view(['GET'])
@authentication_classes([SessionAuthentication])
@permission_classes([IsAuthenticated])
def protected_view(request):
    return Response({
        'user': request.user.username,
        'message': 'You are authenticated via session'
    })
```

### Frontend Integration
```javascript
// JavaScript client (same-origin)
// 1. Login
fetch('/api/login/', {
    method: 'POST',
    headers: {
        'Content-Type': 'application/json',
    },
    body: JSON.stringify({
        username: 'john',
        password: 'secret123'
    }),
    credentials: 'include'  // Important: include cookies
})

// 2. Get CSRF token (from cookie or meta tag)
function getCookie(name) {
    let cookieValue = null;
    if (document.cookie && document.cookie !== '') {
        const cookies = document.cookie.split(';');
        for (let i = 0; i < cookies.length; i++) {
            const cookie = cookies[i].trim();
            if (cookie.substring(0, name.length + 1) === (name + '=')) {
                cookieValue = decodeURIComponent(cookie.substring(name.length + 1));
                break;
            }
        }
    }
    return cookieValue;
}

const csrftoken = getCookie('csrftoken');

// 3. Make authenticated request
fetch('/api/protected/', {
    method: 'POST',
    headers: {
        'Content-Type': 'application/json',
        'X-CSRFToken': csrftoken,  // Required for POST/PUT/DELETE
    },
    credentials: 'include',
    body: JSON.stringify({data: 'value'})
})
```

### CSRF Protection
SessionAuthentication automatically enforces CSRF for unsafe methods (POST, PUT, PATCH, DELETE).

**Important**: Only authenticated requests require CSRF tokens. Anonymous requests don't need CSRF tokens (unlike standard Django behavior).

```python
# This is built into SessionAuthentication
def enforce_csrf(self, request):
    check = CSRFCheck(dummy_get_response)
    check.process_request(request)
    reason = check.process_view(request, None, (), {})
    if reason:
        raise exceptions.PermissionDenied('CSRF Failed: %s' % reason)
```

### Security Considerations
✅ **Best Practices:**
1. **Always use Django's login view** - Don't bypass CSRF on login pages
2. **Configure CSRF settings** properly for your deployment
3. **Use HTTPS** in production
4. **Set secure cookie flags**

```python
# Production settings
SESSION_COOKIE_SECURE = True      # HTTPS only
SESSION_COOKIE_HTTPONLY = True    # No JavaScript access
SESSION_COOKIE_SAMESITE = 'Lax'   # CSRF protection
CSRF_COOKIE_SECURE = True         # HTTPS only
```

---

## TokenAuthentication

### What It Is
Simple token-based authentication. Each user has a single token stored in the database.

### How It Works
1. User authenticates (username/password) → receives token
2. Client stores token (localStorage, secure storage)
3. Client includes token in Authorization header
4. DRF looks up token in database, returns user

```
Authorization: Token 9944b09199c62bcf9418ad846dd0e4bbdfc6ee4b
```

### Configuration
```python
# settings.py
INSTALLED_APPS = [
    ...
    'rest_framework.authtoken',  # Required
]

REST_FRAMEWORK = {
    'DEFAULT_AUTHENTICATION_CLASSES': [
        'rest_framework.authentication.TokenAuthentication',
    ],
}
```

```bash
# Create token table
python manage.py migrate
```

### Request/Response Credentials
- `request.user` → Django `User` instance
- `request.auth` → `rest_framework.authtoken.models.Token` instance
- Failed auth → `401 Unauthorized` with `WWW-Authenticate: Token`

### When to Use
✅ **Good for:**
- Mobile applications
- Single-page applications (SPAs)
- Desktop applications
- Simple API authentication
- Stateless APIs (no session storage)

❌ **Bad for:**
- When you need token expiry (use django-rest-knox instead)
- Multiple devices per user (one token per user)
- High-security requirements (no built-in rotation)

### Complete Setup Example
See [token-auth-setup.md](token-auth-setup.md) for full lifecycle management.

### Basic Usage
```python
# Create token for user
from rest_framework.authtoken.models import Token

token = Token.objects.create(user=user)
print(token.key)  # '9944b09199c62bcf9418ad846dd0e4bbdfc6ee4b'

# Or get existing token
token, created = Token.objects.get_or_create(user=user)

# Delete token (logout)
token.delete()
```

### Custom Token Keyword
```python
# Use "Bearer" instead of "Token"
from rest_framework.authentication import TokenAuthentication

class BearerTokenAuthentication(TokenAuthentication):
    keyword = 'Bearer'
    # Now expects: Authorization: Bearer <token>
```

### Custom Token Model
```python
# models.py
from rest_framework.authtoken.models import Token as DefaultToken

class CustomToken(DefaultToken):
    # Add custom fields
    device_name = models.CharField(max_length=100, blank=True)
    ip_address = models.GenericIPAddressField(null=True)
    last_used = models.DateTimeField(null=True)

    class Meta:
        abstract = False  # Make concrete model

# authentication.py
from rest_framework.authentication import TokenAuthentication

class CustomTokenAuthentication(TokenAuthentication):
    model = CustomToken

    def authenticate_credentials(self, key):
        model = self.get_model()
        try:
            token = model.objects.select_related('user').get(key=key)
        except model.DoesNotExist:
            raise exceptions.AuthenticationFailed('Invalid token.')

        if not token.user.is_active:
            raise exceptions.AuthenticationFailed('User inactive or deleted.')

        # Update last used
        token.last_used = timezone.now()
        token.save(update_fields=['last_used'])

        return (token.user, token)
```

### Security Considerations
⚠️ **Important Limitations:**
1. **No expiry by default** - Tokens are valid forever
2. **One token per user** - Can't track/revoke per-device
3. **Database lookup** - Slower than JWT for high-scale

✅ **Best Practices:**
1. **HTTPS only** in production
2. **Implement token rotation** for sensitive operations
3. **Monitor token usage** (add last_used field)
4. **Provide logout endpoint** to delete tokens
5. **Consider django-rest-knox** for better features

---

## RemoteUserAuthentication

### What It Is
Delegates authentication to your web server (Apache, Nginx). The web server sets `REMOTE_USER` environment variable.

### How It Works
1. Web server performs authentication (e.g., LDAP, Kerberos, Client Certificates)
2. Web server sets `REMOTE_USER` header/env variable
3. Django reads `REMOTE_USER` and authenticates user
4. DRF provides user object

### Configuration
```python
# settings.py
AUTHENTICATION_BACKENDS = [
    'django.contrib.auth.backends.RemoteUserBackend',
]

MIDDLEWARE = [
    ...
    'django.contrib.auth.middleware.RemoteUserMiddleware',
    ...
]

REST_FRAMEWORK = {
    'DEFAULT_AUTHENTICATION_CLASSES': [
        'rest_framework.authentication.RemoteUserAuthentication',
    ],
}
```

### Request/Response Credentials
- `request.user` → Django `User` instance (created automatically if doesn't exist)
- `request.auth` → `None`
- Failed auth → `None` returned (web server should block unauthenticated)

### When to Use
✅ **Good for:**
- Enterprise environments with SSO
- Apache/Nginx authentication modules
- Client certificate authentication
- Integration with LDAP/Active Directory
- Kerberos authentication

❌ **Bad for:**
- Simple token-based APIs
- When you control authentication logic
- Mobile applications

### Example: Apache Configuration
```apache
<Location /api/>
    AuthType Basic
    AuthName "API Authentication"
    AuthUserFile /etc/apache2/.htpasswd
    Require valid-user

    WSGIPassAuthorization On
</Location>
```

### Example: Nginx Configuration
```nginx
location /api/ {
    auth_basic "API Authentication";
    auth_basic_user_file /etc/nginx/.htpasswd;

    proxy_pass http://django;
    proxy_set_header REMOTE_USER $remote_user;
}
```

### Custom Header Name
```python
from rest_framework.authentication import RemoteUserAuthentication

class CustomHeaderAuthentication(RemoteUserAuthentication):
    header = 'HTTP_X_REMOTE_USER'  # Use X-Remote-User header
```

### Auto-creating Users
By default, `RemoteUserBackend` creates users that don't exist:

```python
# Customize user creation
from django.contrib.auth.backends import RemoteUserBackend

class CustomRemoteUserBackend(RemoteUserBackend):
    create_unknown_user = False  # Don't auto-create users

    def configure_user(self, request, user):
        """
        Configure newly created user.
        """
        user.email = f"{user.username}@company.com"
        user.save()
        return user
```

### Security Considerations
⚠️ **Critical Requirements:**
1. **Secure web server** - Authentication is only as strong as your web server config
2. **Don't bypass web server** - Ensure Django can't be accessed directly
3. **Trust the header** - Only works if REMOTE_USER can't be spoofed
4. **Use with firewall** - Ensure only web server can reach Django

✅ **Best Practices:**
```python
# Ensure web server is properly configured
if not settings.DEBUG:
    assert 'django.contrib.auth.middleware.RemoteUserMiddleware' in settings.MIDDLEWARE
    assert 'django.contrib.auth.backends.RemoteUserBackend' in settings.AUTHENTICATION_BACKENDS
```

---

## Combining Multiple Authentication Schemes

You can use multiple authentication classes together:

```python
REST_FRAMEWORK = {
    'DEFAULT_AUTHENTICATION_CLASSES': [
        'rest_framework.authentication.SessionAuthentication',  # Try first
        'rest_framework.authentication.TokenAuthentication',    # Then this
        'rest_framework.authentication.BasicAuthentication',    # Finally this
    ],
}
```

**How it works:**
1. DRF tries each class in order
2. First class that returns `(user, auth)` wins
3. If all return `None`, user is `AnonymousUser`
4. If any raises `AuthenticationFailed`, authentication stops immediately

**Common combination:**
```python
# Support both browser (session) and API clients (token)
'DEFAULT_AUTHENTICATION_CLASSES': [
    'rest_framework.authentication.SessionAuthentication',  # For browsable API
    'rest_framework.authentication.TokenAuthentication',    # For API clients
]
```

**Per-view override:**
```python
class MyView(APIView):
    # Only allow token auth for this view
    authentication_classes = [TokenAuthentication]
```

---

## Comparison Table

| Feature | Basic | Session | Token | RemoteUser |
|---------|-------|---------|-------|------------|
| **State** | Stateless | Stateful | Stateless | Stateless |
| **Credentials in every request** | Yes | No (cookie) | Yes | Yes (header) |
| **Requires database** | Yes | Yes | Yes | Yes |
| **CSRF protection** | No | Yes | No | No |
| **Mobile-friendly** | No | No | Yes | No |
| **Built-in expiry** | No | Yes | No | No |
| **Production ready** | ❌ | ✅ | ✅ | ✅ |
| **Best for** | Testing | Same-origin | APIs | Enterprise SSO |

---

## Next Steps

- **Token Setup Guide** → [token-auth-setup.md](token-auth-setup.md)
- **Custom Authentication** → [custom-auth.md](custom-auth.md)
- **JWT vs OAuth** → [jwt-oauth-guide.md](jwt-oauth-guide.md)
- **Code Examples** → [examples/auth-patterns.py](examples/auth-patterns.py)
