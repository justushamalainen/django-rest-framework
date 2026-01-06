---
skill: authentication
description: Master Django REST Framework authentication - from Basic/Token/Session to JWT/OAuth, with security best practices
dependencies:
  - rest_framework.authentication
  - rest_framework.authtoken
related_skills:
  - permissions
  - throttling
references:
  - /home/user/django-rest-framework/rest_framework/authentication.py
  - /home/user/django-rest-framework/rest_framework/authtoken/
  - /home/user/django-rest-framework/docs/api-guide/authentication.md
---

# DRF Authentication Skill

Authentication is the mechanism of associating an incoming request with identifying credentials. This skill will teach you how to choose, implement, and secure authentication in Django REST Framework.

## What You'll Learn

- **Built-in Authentication Schemes**: BasicAuthentication, SessionAuthentication, TokenAuthentication, and RemoteUserAuthentication
- **Token Management**: Complete lifecycle management including generation, storage, rotation, and revocation
- **Custom Authentication**: How to build custom authentication classes that fit your specific needs
- **JWT vs OAuth**: Decision framework for choosing between JWT (simplejwt) and OAuth2 (django-oauth-toolkit)
- **Security Best Practices**: HTTPS requirements, token storage, CSRF protection, and common vulnerabilities
- **Integration Patterns**: Real-world examples of authentication flows for SPAs, mobile apps, and third-party integrations
- **Troubleshooting**: Common mistakes and how to debug authentication issues

## Quick Start: TokenAuthentication

The most common authentication scheme for API clients. Here's a complete working example:

### 1. Install and Configure

```python
# settings.py
INSTALLED_APPS = [
    ...
    'rest_framework',
    'rest_framework.authtoken',  # Add this
    ...
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

```bash
# Run migrations to create token table
python manage.py migrate
```

### 2. Create Token Endpoint

```python
# urls.py
from django.urls import path
from rest_framework.authtoken import views

urlpatterns = [
    path('api/auth/token/', views.obtain_auth_token, name='api_token_auth'),
]
```

### 3. Use in Views

```python
# views.py
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated

class ProtectedView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        return Response({
            'message': f'Hello, {request.user.username}!',
            'user_id': request.user.id,
            'token_key': request.auth.key[:8] + '...',  # request.auth is the Token object
        })
```

### 4. Client Usage

```bash
# Login and get token
curl -X POST http://localhost:8000/api/auth/token/ \
    -d "username=john" \
    -d "password=secret123"
# Response: {"token": "9944b09199c62bcf9418ad846dd0e4bbdfc6ee4b"}

# Use token in requests
curl -X GET http://localhost:8000/api/protected/ \
    -H "Authorization: Token 9944b09199c62bcf9418ad846dd0e4bbdfc6ee4b"
```

## Decision Tree: Which Authentication Scheme?

### Start Here: What are you building?

```
┌─────────────────────────────────────────────┐
│ What type of client consumes your API?     │
└─────────────────────────────────────────────┘
                    ↓
        ┌───────────┴───────────┐
        ↓                       ↓
   Same-origin              Cross-origin
   AJAX/SPA                 or Mobile App
        ↓                       ↓
        │                   ┌───┴────┐
        │                   ↓        ↓
        │              Native App   Third-party
        │                   ↓        Integration
        │                   │             ↓
        ↓                   ↓             ↓
```

### Decision Matrix

| Use Case | Recommended Scheme | Why? |
|----------|-------------------|------|
| **Development/Testing** | `BasicAuthentication` | Simple, built-in, no setup required |
| **Same-origin AJAX** | `SessionAuthentication` | Uses Django sessions, CSRF protection, familiar login flow |
| **Mobile Apps** | `TokenAuthentication` or `JWT` | Stateless, works across devices, no cookies |
| **SPA (React/Vue/Angular)** | `TokenAuthentication` or `JWT` | Stateless, store in memory/localStorage |
| **Third-party API Access** | `OAuth2` | Standard protocol, scoped permissions, token refresh |
| **Microservices** | `JWT` | Stateless, no database lookups, includes claims |
| **Enterprise SSO** | `RemoteUserAuthentication` | Delegate to web server (Apache/Nginx) |
| **High Security Requirements** | `OAuth2` with PKCE or `JWT` with short expiry | Token refresh, fine-grained control |

### Quick Guidelines

**Choose BasicAuthentication when:**
- Developing locally
- Writing integration tests
- Building admin tools for internal use only
- ⚠️ NEVER in production without HTTPS

**Choose SessionAuthentication when:**
- Building a traditional Django app with API endpoints
- Your frontend and backend are same-origin
- You want to use Django's built-in login views
- ⚠️ Requires CSRF tokens for non-safe methods

**Choose TokenAuthentication when:**
- Building a mobile app
- Need simple stateless authentication
- Don't need token expiry (use django-rest-knox for expiry)
- ⚠️ Tokens don't expire by default - implement rotation

**Choose JWT (simplejwt) when:**
- Need token expiry and refresh
- Building microservices
- Want to include claims in the token
- Need stateless authentication at scale
- ⚠️ Can't revoke tokens easily - use short expiry

**Choose OAuth2 (django-oauth-toolkit) when:**
- Building a public API for third parties
- Need fine-grained scopes/permissions
- Want token refresh flows
- Need to support multiple client types
- ⚠️ More complex setup and maintenance

## Authentication Flow Patterns

### Pattern 1: Token Login Flow (Mobile/SPA)

```
Client                          Server
  │                               │
  ├──── POST /api/auth/token/ ───→│ (username, password)
  │                               │
  │←────── {"token": "abc..."}────┤
  │                               │
  ├──── GET /api/resource/ ───────→│ (Authorization: Token abc...)
  │                               │
  │←────── {"data": [...]}────────┤
```

### Pattern 2: Session Login Flow (Same-origin)

```
Client                          Server
  │                               │
  ├──── POST /accounts/login/ ───→│ (username, password)
  │                               │
  │←── Set-Cookie: sessionid ─────┤
  │                               │
  ├──── GET /api/resource/ ───────→│ (Cookie: sessionid, X-CSRFToken)
  │                               │
  │←────── {"data": [...]}────────┤
```

### Pattern 3: JWT with Refresh (SPA/Mobile)

```
Client                          Server
  │                               │
  ├──── POST /api/token/ ─────────→│ (username, password)
  │                               │
  │←── {"access": "...", "refresh": "..."}──┤
  │                               │
  ├──── GET /api/resource/ ───────→│ (Authorization: Bearer access_token)
  │                               │
  │←────── {"data": [...]}────────┤
  │                               │
  │  (access token expires)       │
  │                               │
  ├──── POST /api/token/refresh/ ─→│ (refresh: "...")
  │                               │
  │←────── {"access": "..."}──────┤
```

## Common Mistakes and Solutions

### Mistake 1: Using BasicAuthentication in Production
```python
# ❌ DON'T: Credentials sent with every request
REST_FRAMEWORK = {
    'DEFAULT_AUTHENTICATION_CLASSES': [
        'rest_framework.authentication.BasicAuthentication',
    ],
}
```

**Why it's bad:** Username/password sent in every request header (base64 encoded, not encrypted). Easy to intercept without HTTPS.

**Solution:** Use token-based authentication for production APIs.

### Mistake 2: Storing Tokens in localStorage
```javascript
// ⚠️ RISKY: Vulnerable to XSS attacks
localStorage.setItem('token', response.token);
```

**Why it's risky:** XSS attacks can read localStorage. Any injected script can steal tokens.

**Better approach:**
```javascript
// Store in memory (lost on refresh - implement refresh tokens)
let authToken = response.token;

// Or use httpOnly cookies (set from server)
// Server: Set-Cookie: token=...; HttpOnly; Secure; SameSite=Strict
```

### Mistake 3: No Token Expiry
```python
# ❌ DON'T: Default Token model never expires
token = Token.objects.create(user=user)
```

**Solution:** Use django-rest-knox or implement custom expiry:
```python
from django.utils import timezone
from datetime import timedelta

class ExpiringToken(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    key = models.CharField(max_length=40, primary_key=True)
    created = models.DateTimeField(auto_now_add=True)

    def is_expired(self):
        return timezone.now() > self.created + timedelta(hours=24)
```

### Mistake 4: Missing CSRF Token with SessionAuthentication
```javascript
// ❌ DON'T: POST without CSRF token
fetch('/api/resource/', {
    method: 'POST',
    body: JSON.stringify(data),
})
```

**Solution:** Include CSRF token in requests:
```javascript
// ✅ DO: Include CSRF token
const csrftoken = document.querySelector('[name=csrfmiddlewaretoken]').value;
fetch('/api/resource/', {
    method: 'POST',
    headers: {
        'X-CSRFToken': csrftoken,
        'Content-Type': 'application/json',
    },
    body: JSON.stringify(data),
})
```

### Mistake 5: Not Using HTTPS in Production
```python
# ❌ DON'T: Allow authentication over HTTP
SECURE_SSL_REDIRECT = False  # Default
```

**Solution:** Always enforce HTTPS:
```python
# ✅ DO: Enforce HTTPS in production
SECURE_SSL_REDIRECT = True
SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')
SESSION_COOKIE_SECURE = True
CSRF_COOKIE_SECURE = True
```

### Mistake 6: Returning Token in GET Response
```python
# ❌ DON'T: GET requests are logged/cached
def get_token(request):
    return Response({'token': request.auth.key})  # Appears in logs!
```

**Solution:** Only return tokens in POST responses, never GET.

### Mistake 7: Not Handling Authentication in authenticate()
```python
# ❌ DON'T: Always return user
class BadAuth(BaseAuthentication):
    def authenticate(self, request):
        username = request.META.get('HTTP_X_USER')
        user = User.objects.get(username=username)  # Always returns user!
        return (user, None)
```

**Solution:** Return None if auth not attempted, raise exception if attempted but failed:
```python
# ✅ DO: Proper authentication logic
class GoodAuth(BaseAuthentication):
    def authenticate(self, request):
        username = request.META.get('HTTP_X_USER')
        if not username:
            return None  # Auth not attempted

        try:
            user = User.objects.get(username=username)
        except User.DoesNotExist:
            raise exceptions.AuthenticationFailed('Invalid user')

        if not user.is_active:
            raise exceptions.AuthenticationFailed('User inactive')

        return (user, None)
```

## Next Steps

1. **Read Built-in Auth Reference** → [reference/builtin-auth.md](reference/builtin-auth.md)
   - Deep dive into each authentication class
   - When to use each one
   - Configuration options

2. **Complete Token Setup** → [reference/token-auth-setup.md](reference/token-auth-setup.md)
   - Full lifecycle management
   - Security checklist
   - Production deployment

3. **Build Custom Auth** → [reference/custom-auth.md](reference/custom-auth.md)
   - API key authentication
   - Header-based authentication
   - Multi-factor authentication hooks

4. **Choose JWT vs OAuth** → [reference/jwt-oauth-guide.md](reference/jwt-oauth-guide.md)
   - Detailed comparison
   - Integration guides
   - Migration strategies

5. **See Working Examples** → [reference/examples/auth-patterns.py](reference/examples/auth-patterns.py)
   - Production-ready code
   - Complete authentication flows
   - Error handling patterns

## Reference Files

- **Source Code**: `/home/user/django-rest-framework/rest_framework/authentication.py`
- **Token Models**: `/home/user/django-rest-framework/rest_framework/authtoken/models.py`
- **Token Views**: `/home/user/django-rest-framework/rest_framework/authtoken/views.py`
- **Official Docs**: `/home/user/django-rest-framework/docs/api-guide/authentication.md`
