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

Authentication is the mechanism of associating an incoming request with identifying credentials. This skill teaches you how to choose, implement, and secure authentication in Django REST Framework.

## Quick Start: TokenAuthentication

The most common authentication for API clients:

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
}
```

```bash
python manage.py migrate
```

```python
# urls.py
from rest_framework.authtoken import views

urlpatterns = [
    path('api/auth/token/', views.obtain_auth_token),
]
```

```bash
# Login and get token
curl -X POST http://localhost:8000/api/auth/token/ \
    -d "username=john" -d "password=secret123"
# Response: {"token": "9944b09199c62bcf9418ad846dd0e4bbdfc6ee4b"}

# Use token
curl -H "Authorization: Token 9944b09199c62bcf9418ad846dd0e4bbdfc6ee4b" \
    http://localhost:8000/api/protected/
```

## Decision Tree: Which Authentication?

| Use Case | Recommended | Why? |
|----------|-------------|------|
| **Mobile Apps** | Token or JWT | Stateless, works across devices |
| **SPAs (React/Vue)** | Token or JWT | Store in memory, no cookies needed |
| **Same-origin AJAX** | Session | Uses Django sessions, familiar flow |
| **Development/Testing** | Basic | Simple, no setup required |
| **Third-party API** | OAuth2 | Standard protocol, scoped permissions |
| **Microservices** | JWT | Stateless, no database lookups |

### Quick Guidelines

**Choose Token when:**
- Building a mobile app
- Need simple stateless authentication
- Don't need automatic expiry (or use django-rest-knox)

**Choose JWT (simplejwt) when:**
- Need built-in token expiry and refresh
- Building microservices
- Want claims in the token

**Choose Session when:**
- Frontend and backend are same-origin
- Want to use Django's built-in login views
- Need CSRF protection

**Choose OAuth2 when:**
- Building a public API for third parties
- Need fine-grained scopes/permissions

## Built-in Authentication Classes

DRF provides four authentication classes. All return `(user, auth)` on success or `None` if not attempted.

### BasicAuthentication

Sends credentials (base64 encoded) in every request header.

```python
# Authorization: Basic dXNlcm5hbWU6cGFzc3dvcmQ=
```

**Good for:** Testing, development, internal tools
**Bad for:** Production (credentials in every request)
**Security:** Requires HTTPS

### SessionAuthentication

Uses Django's session framework. User logs in once, then session cookie authenticates requests.

**Good for:** Same-origin AJAX, hybrid Django + API apps
**Bad for:** Mobile apps, cross-origin requests
**Security:** Enforces CSRF for POST/PUT/DELETE

```python
# Requires CSRF token in header
fetch('/api/resource/', {
    method: 'POST',
    headers: {
        'X-CSRFToken': csrftoken,
        'Content-Type': 'application/json',
    },
    credentials: 'include',
})
```

### TokenAuthentication

Each user has a single token in the database. Token is sent in Authorization header.

```python
# Authorization: Token 9944b09199c62bcf9418ad846dd0e4bbdfc6ee4b
```

**Good for:** Mobile apps, SPAs, simple APIs
**Bad for:** When you need expiry (use knox) or multiple devices per user
**Security:** HTTPS required, tokens don't expire by default

See [token-auth-setup.md](reference/token-auth-setup.md) for complete setup.

### RemoteUserAuthentication

Delegates authentication to web server (Apache/Nginx with LDAP, Kerberos, etc.)

**Good for:** Enterprise SSO, client certificates
**Bad for:** Simple APIs, mobile apps

### Combining Multiple Schemes

```python
REST_FRAMEWORK = {
    'DEFAULT_AUTHENTICATION_CLASSES': [
        'rest_framework.authentication.SessionAuthentication',  # Try first
        'rest_framework.authentication.TokenAuthentication',    # Then this
    ],
}
```

DRF tries each class in order until one succeeds.

## Common Security Mistakes

### 1. Using BasicAuthentication in Production

```python
# ❌ DON'T: Credentials in every request
'rest_framework.authentication.BasicAuthentication'
```

**Solution:** Use token-based authentication.

### 2. Storing Tokens in localStorage

```javascript
// ⚠️ RISKY: Vulnerable to XSS
localStorage.setItem('token', response.token);
```

**Better:** Store in memory or use httpOnly cookies.

### 3. No Token Expiry

Default Token model never expires.

**Solution:** Use django-rest-knox or JWT for automatic expiry.

### 4. Missing CSRF Token with SessionAuthentication

```javascript
// ❌ DON'T: POST without CSRF
fetch('/api/resource/', { method: 'POST' })
```

**Solution:** Include CSRF token in X-CSRFToken header.

### 5. Not Using HTTPS

```python
# ❌ DON'T in production
SECURE_SSL_REDIRECT = False
```

**Solution:** Always enforce HTTPS:

```python
# settings.py
SECURE_SSL_REDIRECT = True
SESSION_COOKIE_SECURE = True
CSRF_COOKIE_SECURE = True
```

## Authentication Flows

### Token Flow (Mobile/SPA)

```
1. POST /api/auth/token/ {username, password}
2. Response: {token: "abc..."}
3. Store token in memory/secure storage
4. GET /api/resource/ (Authorization: Token abc...)
```

### JWT Flow (with Refresh)

```
1. POST /api/token/ {username, password}
2. Response: {access: "...", refresh: "..."}
3. GET /api/resource/ (Authorization: Bearer access_token)
4. When access expires: POST /api/token/refresh/ {refresh: "..."}
```

### Session Flow (Same-origin)

```
1. POST /accounts/login/ {username, password}
2. Response sets Cookie: sessionid
3. GET /api/resource/ (Cookie sent automatically, include X-CSRFToken)
```

## Next Steps

1. **Token Setup** → [reference/token-auth-setup.md](reference/token-auth-setup.md)
   - Complete lifecycle management
   - Security checklist
   - Production deployment

2. **JWT Guide** → [reference/jwt-guide.md](reference/jwt-guide.md)
   - SimpleJWT integration
   - Custom claims
   - Token refresh

## Reference Files

- **Source Code**: `/home/user/django-rest-framework/rest_framework/authentication.py`
- **Token Models**: `/home/user/django-rest-framework/rest_framework/authtoken/models.py`
- **Official Docs**: `/home/user/django-rest-framework/docs/api-guide/authentication.md`
