# JWT vs OAuth2: Decision Guide and Integration

Comprehensive guide to choosing between JWT (djangorestframework-simplejwt) and OAuth2 (django-oauth-toolkit) with complete integration examples.

## Table of Contents
1. [Quick Decision Matrix](#quick-decision-matrix)
2. [Understanding the Difference](#understanding-the-difference)
3. [JWT with djangorestframework-simplejwt](#jwt-with-djangorestframework-simplejwt)
4. [OAuth2 with django-oauth-toolkit](#oauth2-with-django-oauth-toolkit)
5. [Comparison Table](#comparison-table)
6. [Migration Strategies](#migration-strategies)

---

## Quick Decision Matrix

### Choose JWT (simplejwt) when:

✅ **First-party applications**
- Your mobile app
- Your SPA (React/Vue/Angular)
- Your own microservices

✅ **Simple authentication needs**
- User logs in, gets token
- Token has short expiry
- Refresh token pattern

✅ **Stateless architecture**
- No token storage in database
- Claims embedded in token
- Horizontal scaling

✅ **Quick setup required**
- Minimal configuration
- Works out of the box
- Easy to understand

### Choose OAuth2 (django-oauth-toolkit) when:

✅ **Third-party access**
- Public API for external developers
- "Login with MyApp" functionality
- Partner integrations

✅ **Fine-grained permissions**
- Scope-based access control
- User can grant/revoke specific permissions
- Different access levels per client

✅ **Multiple client types**
- Web applications
- Mobile apps
- Server-to-server
- Each with different flows

✅ **Enterprise requirements**
- OAuth2 compliance mandated
- Complex authorization flows
- Token management UI needed

---

## Understanding the Difference

### JWT: What It Is

**JSON Web Token** is a token format, not an authentication protocol.

```
eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJ1c2VyX2lkIjoxMjMsImV4cCI6MTYzMjM0NTY3OH0.signature
   └── Header ──┘                       └──────── Payload ───────┘                └─ Signature ─┘
```

**Key Characteristics:**
- Self-contained (includes user data)
- Stateless (no database lookup)
- Signed (can verify authenticity)
- Short-lived (typically 5-15 minutes)
- Cannot be revoked (until expiry)

**Typical Flow:**
```
1. User logs in → Gets access token (JWT) + refresh token
2. Client uses access token for requests
3. When access token expires → Use refresh token to get new access token
4. When refresh token expires → User logs in again
```

### OAuth2: What It Is

**OAuth 2.0** is an authorization framework/protocol.

**Key Characteristics:**
- Protocol with multiple flows (authorization code, client credentials, etc.)
- Supports scopes (fine-grained permissions)
- Tokens stored in database (can be revoked)
- Designed for third-party access
- More complex setup

**Typical Flow (Authorization Code):**
```
1. User clicks "Login with MyApp"
2. Redirected to authorization page
3. User grants permissions (scopes)
4. App receives authorization code
5. App exchanges code for access token
6. App uses access token for API requests
```

### Key Distinction

```
JWT        = Token format (how token looks)
OAuth2     = Authorization protocol (how to get/use tokens)

You can use JWT tokens WITH OAuth2!
Django-oauth-toolkit can issue JWT tokens.
```

---

## JWT with djangorestframework-simplejwt

### Installation

```bash
pip install djangorestframework-simplejwt
```

### Basic Configuration

```python
# settings.py
from datetime import timedelta

INSTALLED_APPS = [
    ...
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
    'ROTATE_REFRESH_TOKENS': True,  # Issue new refresh token on refresh
    'BLACKLIST_AFTER_ROTATION': True,  # Blacklist old refresh token
    'UPDATE_LAST_LOGIN': True,

    'ALGORITHM': 'HS256',
    'SIGNING_KEY': SECRET_KEY,
    'VERIFYING_KEY': None,
    'AUDIENCE': None,
    'ISSUER': None,

    'AUTH_HEADER_TYPES': ('Bearer',),
    'AUTH_HEADER_NAME': 'HTTP_AUTHORIZATION',
    'USER_ID_FIELD': 'id',
    'USER_ID_CLAIM': 'user_id',

    'AUTH_TOKEN_CLASSES': ('rest_framework_simplejwt.tokens.AccessToken',),
    'TOKEN_TYPE_CLAIM': 'token_type',

    'JTI_CLAIM': 'jti',  # Token ID for blacklisting

    'SLIDING_TOKEN_REFRESH_EXP_CLAIM': 'refresh_exp',
    'SLIDING_TOKEN_LIFETIME': timedelta(minutes=5),
    'SLIDING_TOKEN_REFRESH_LIFETIME': timedelta(days=1),
}
```

### URL Configuration

```python
# urls.py
from django.urls import path
from rest_framework_simplejwt.views import (
    TokenObtainPairView,
    TokenRefreshView,
    TokenVerifyView,
)

urlpatterns = [
    # Get access + refresh tokens
    path('api/token/', TokenObtainPairView.as_view(), name='token_obtain_pair'),

    # Refresh access token
    path('api/token/refresh/', TokenRefreshView.as_view(), name='token_refresh'),

    # Verify token is valid
    path('api/token/verify/', TokenVerifyView.as_view(), name='token_verify'),
]
```

### Basic Usage

```python
# Login
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

# Use access token
GET /api/protected/
Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...

# Refresh when access token expires
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

### Custom Claims

```python
# myapp/serializers.py
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer
from rest_framework_simplejwt.views import TokenObtainPairView

class CustomTokenObtainPairSerializer(TokenObtainPairSerializer):
    @classmethod
    def get_token(cls, user):
        token = super().get_token(user)

        # Add custom claims
        token['username'] = user.username
        token['email'] = user.email
        token['is_staff'] = user.is_staff

        return token

class CustomTokenObtainPairView(TokenObtainPairView):
    serializer_class = CustomTokenObtainPairSerializer

# urls.py
urlpatterns = [
    path('api/token/', CustomTokenObtainPairView.as_view(), name='token_obtain_pair'),
]
```

### Token Blacklisting (Logout)

```python
# settings.py
INSTALLED_APPS = [
    ...
    'rest_framework_simplejwt.token_blacklist',
]

# Run migrations
python manage.py migrate

# myapp/views.py
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from rest_framework import status
from rest_framework_simplejwt.tokens import RefreshToken

class LogoutView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        try:
            refresh_token = request.data["refresh"]
            token = RefreshToken(refresh_token)
            token.blacklist()  # Blacklist the refresh token

            return Response({
                "detail": "Successfully logged out."
            }, status=status.HTTP_200_OK)
        except Exception as e:
            return Response({
                "detail": str(e)
            }, status=status.HTTP_400_BAD_REQUEST)

# urls.py
urlpatterns = [
    path('api/logout/', LogoutView.as_view(), name='logout'),
]
```

### Frontend Integration (React Example)

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
        // Add access token to request
        options.headers = {
            ...options.headers,
            'Authorization': `Bearer ${this.accessToken}`
        };

        let response = await fetch(url, options);

        // If 401, try to refresh token
        if (response.status === 401) {
            const refreshed = await this.refreshAccessToken();
            if (refreshed) {
                // Retry request with new token
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
                if (data.refresh) {  // If rotating
                    this.refreshToken = data.refresh;
                }
                return true;
            }
        } catch (error) {
            console.error('Failed to refresh token:', error);
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

---

## OAuth2 with django-oauth-toolkit

### Installation

```bash
pip install django-oauth-toolkit
```

### Basic Configuration

```python
# settings.py
INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'rest_framework',
    'oauth2_provider',  # Add this
    'myapp',
]

REST_FRAMEWORK = {
    'DEFAULT_AUTHENTICATION_CLASSES': [
        'oauth2_provider.contrib.rest_framework.OAuth2Authentication',
    ],
    'DEFAULT_PERMISSION_CLASSES': [
        'rest_framework.permissions.IsAuthenticated',
    ],
}

OAUTH2_PROVIDER = {
    'SCOPES': {
        'read': 'Read scope',
        'write': 'Write scope',
        'groups': 'Access to your groups',
        'profile': 'Access to your profile',
    },
    'ACCESS_TOKEN_EXPIRE_SECONDS': 3600,  # 1 hour
    'AUTHORIZATION_CODE_EXPIRE_SECONDS': 60,
    'REFRESH_TOKEN_EXPIRE_SECONDS': 86400,  # 1 day
    'ROTATE_REFRESH_TOKEN': True,
}
```

### URL Configuration

```python
# urls.py
from django.urls import path, include

urlpatterns = [
    path('admin/', admin.site.urls),
    path('o/', include('oauth2_provider.urls', namespace='oauth2_provider')),
    path('api/', include('myapp.urls')),
]
```

### Run Migrations

```bash
python manage.py migrate
```

### Create OAuth2 Application

**Via Django Admin:**
1. Go to `/admin/oauth2_provider/application/`
2. Click "Add Application"
3. Fill in:
   - **User**: Select user
   - **Client type**: Confidential or Public
   - **Authorization grant type**:
     - Authorization code (for web apps)
     - Client credentials (for server-to-server)
     - Resource owner password-based (for first-party apps)
   - **Name**: Your app name
4. Save and note the **Client ID** and **Client Secret**

**Programmatically:**
```python
from oauth2_provider.models import Application

app = Application.objects.create(
    name="My Mobile App",
    user=user,
    client_type=Application.CLIENT_CONFIDENTIAL,
    authorization_grant_type=Application.GRANT_PASSWORD,
)
print(f"Client ID: {app.client_id}")
print(f"Client Secret: {app.client_secret}")
```

### OAuth2 Flows

#### Flow 1: Resource Owner Password (First-party Apps)

**Best for:** Your own mobile/desktop apps

```bash
# Get access token
curl -X POST http://localhost:8000/o/token/ \
    -d "grant_type=password" \
    -d "username=john" \
    -d "password=secret123" \
    -d "client_id=YOUR_CLIENT_ID" \
    -d "client_secret=YOUR_CLIENT_SECRET"

# Response:
{
    "access_token": "oL2h...",
    "expires_in": 3600,
    "token_type": "Bearer",
    "scope": "read write",
    "refresh_token": "PK9a..."
}

# Use access token
curl http://localhost:8000/api/protected/ \
    -H "Authorization: Bearer oL2h..."

# Refresh token
curl -X POST http://localhost:8000/o/token/ \
    -d "grant_type=refresh_token" \
    -d "refresh_token=PK9a..." \
    -d "client_id=YOUR_CLIENT_ID" \
    -d "client_secret=YOUR_CLIENT_SECRET"
```

#### Flow 2: Authorization Code (Third-party Web Apps)

**Best for:** "Login with MyApp" functionality

```python
# Step 1: Redirect user to authorization page
https://myapp.com/o/authorize/
    ?response_type=code
    &client_id=YOUR_CLIENT_ID
    &redirect_uri=https://clientapp.com/callback
    &scope=read+write
    &state=random_state_string

# Step 2: User approves, redirected back with code
https://clientapp.com/callback
    ?code=AUTHORIZATION_CODE
    &state=random_state_string

# Step 3: Exchange code for token
POST https://myapp.com/o/token/
{
    "grant_type": "authorization_code",
    "code": "AUTHORIZATION_CODE",
    "redirect_uri": "https://clientapp.com/callback",
    "client_id": "YOUR_CLIENT_ID",
    "client_secret": "YOUR_CLIENT_SECRET"
}

# Response:
{
    "access_token": "oL2h...",
    "expires_in": 3600,
    "token_type": "Bearer",
    "scope": "read write",
    "refresh_token": "PK9a..."
}
```

#### Flow 3: Client Credentials (Server-to-Server)

**Best for:** Backend services, cron jobs

```bash
curl -X POST http://localhost:8000/o/token/ \
    -d "grant_type=client_credentials" \
    -d "client_id=YOUR_CLIENT_ID" \
    -d "client_secret=YOUR_CLIENT_SECRET"

# Response:
{
    "access_token": "oL2h...",
    "expires_in": 3600,
    "token_type": "Bearer",
    "scope": "read write"
}
```

### Scope-Based Permissions

```python
# myapp/views.py
from rest_framework.views import APIView
from rest_framework.response import Response
from oauth2_provider.contrib.rest_framework import TokenHasReadWriteScope, TokenHasScope

class ProfileView(APIView):
    permission_classes = [TokenHasScope]
    required_scopes = ['profile']

    def get(self, request):
        return Response({
            'username': request.user.username,
            'email': request.user.email,
        })

class DataView(APIView):
    permission_classes = [TokenHasReadWriteScope]

    def get(self, request):
        # Requires 'read' scope
        return Response({'data': 'read'})

    def post(self, request):
        # Requires 'write' scope
        return Response({'data': 'written'})
```

### Custom Scopes and Validators

```python
# myapp/validators.py
from oauth2_provider.scopes import BaseScopes

class CustomScopes(BaseScopes):
    def get_all_scopes(self):
        return {
            'read': 'Read access',
            'write': 'Write access',
            'admin': 'Admin access',
            'read:profile': 'Read user profile',
            'write:profile': 'Update user profile',
            'read:data': 'Read data',
            'write:data': 'Modify data',
        }

    def get_available_scopes(self, application=None, request=None, *args, **kwargs):
        scopes = self.get_all_scopes()

        # Restrict admin scope to staff users
        if request and not request.user.is_staff:
            scopes.pop('admin', None)

        return scopes

    def get_default_scopes(self, application=None, request=None, *args, **kwargs):
        return ['read']

# settings.py
OAUTH2_PROVIDER = {
    'SCOPES_BACKEND_CLASS': 'myapp.validators.CustomScopes',
    ...
}
```

### Revoke Tokens (Logout)

```python
# myapp/views.py
from rest_framework.views import APIView
from rest_framework.response import Response
from oauth2_provider.models import AccessToken, RefreshToken

class RevokeTokenView(APIView):
    def post(self, request):
        # Revoke current access token
        if hasattr(request, 'auth') and request.auth:
            request.auth.delete()

        # Optionally revoke all user's tokens
        if request.data.get('revoke_all'):
            AccessToken.objects.filter(user=request.user).delete()
            RefreshToken.objects.filter(user=request.user).delete()

        return Response({'detail': 'Token revoked'})
```

---

## Comparison Table

| Feature | JWT (simplejwt) | OAuth2 (django-oauth-toolkit) |
|---------|----------------|-------------------------------|
| **Setup Complexity** | Low | Medium-High |
| **Token Storage** | Client only (stateless) | Database (can revoke) |
| **Token Revocation** | Limited (blacklist) | Full support |
| **Scopes** | No built-in | Yes, full support |
| **Third-party Access** | Not designed for | Primary use case |
| **Multiple Clients** | Manual setup | Built-in |
| **Token Expiry** | Yes (built-in) | Yes (built-in) |
| **Refresh Tokens** | Yes | Yes |
| **Performance** | Faster (no DB lookup) | Slower (DB lookup) |
| **Scaling** | Easier (stateless) | Harder (database) |
| **Authorization Flows** | Password-based only | Multiple (code, client, etc.) |
| **Standard Compliance** | JWT standard | OAuth2 standard |
| **Best For** | First-party apps | Third-party integrations |
| **Token Format** | JWT | Opaque or JWT |
| **User Interface** | None | Admin interface |

---

## Migration Strategies

### From Token to JWT

```python
# Step 1: Add JWT alongside TokenAuthentication
REST_FRAMEWORK = {
    'DEFAULT_AUTHENTICATION_CLASSES': [
        'rest_framework.authentication.TokenAuthentication',  # Keep existing
        'rest_framework_simplejwt.authentication.JWTAuthentication',  # Add new
    ],
}

# Step 2: Add JWT endpoints
urlpatterns = [
    path('api/token/', TokenObtainPairView.as_view()),  # New JWT endpoint
    path('api/auth/token/', obtain_auth_token),  # Old token endpoint
]

# Step 3: Migrate clients gradually
# - New clients use JWT
# - Old clients continue using Token
# - Eventually deprecate TokenAuthentication

# Step 4: Remove TokenAuthentication after all clients migrated
```

### From JWT to OAuth2

```python
# Step 1: Install django-oauth-toolkit
pip install django-oauth-toolkit

# Step 2: Configure OAuth2 with password grant type
OAUTH2_PROVIDER = {
    'AUTHORIZATION_CODE_EXPIRE_SECONDS': 60,
    'ACCESS_TOKEN_EXPIRE_SECONDS': 900,  # Match your JWT expiry
    'REFRESH_TOKEN_EXPIRE_SECONDS': 604800,  # Match your refresh token
}

# Step 3: Add OAuth2 authentication alongside JWT
REST_FRAMEWORK = {
    'DEFAULT_AUTHENTICATION_CLASSES': [
        'rest_framework_simplejwt.authentication.JWTAuthentication',  # Keep
        'oauth2_provider.contrib.rest_framework.OAuth2Authentication',  # Add
    ],
}

# Step 4: Create OAuth2 applications for existing clients

# Step 5: Update client code to use OAuth2
# Before (JWT):
# POST /api/token/ {"username": "...", "password": "..."}

# After (OAuth2):
# POST /o/token/ {"grant_type": "password", "username": "...", "password": "...",
#                 "client_id": "...", "client_secret": "..."}

# Step 6: Remove JWT after all clients migrated
```

### Hybrid Approach (JWT + OAuth2)

Use OAuth2 flows to issue JWT tokens:

```python
# settings.py
OAUTH2_PROVIDER = {
    'OAUTH2_VALIDATOR_CLASS': 'myapp.validators.CustomOAuth2Validator',
    ...
}

# myapp/validators.py
from oauth2_provider.oauth2_validators import OAuth2Validator
from rest_framework_simplejwt.tokens import AccessToken

class CustomOAuth2Validator(OAuth2Validator):
    def save_bearer_token(self, token, request, *args, **kwargs):
        # Generate JWT instead of opaque token
        from rest_framework_simplejwt.tokens import RefreshToken

        refresh = RefreshToken.for_user(request.user)

        # Override token in response
        token['access_token'] = str(refresh.access_token)
        token['refresh_token'] = str(refresh)

        # Don't save to database (stateless)
        return None
```

---

## Recommended Approaches

### For Mobile/SPA (First-party)

```python
# Use JWT with simplejwt
# Simple, fast, stateless
pip install djangorestframework-simplejwt

SIMPLE_JWT = {
    'ACCESS_TOKEN_LIFETIME': timedelta(minutes=15),
    'REFRESH_TOKEN_LIFETIME': timedelta(days=7),
    'ROTATE_REFRESH_TOKENS': True,
    'BLACKLIST_AFTER_ROTATION': True,
}
```

### For Public API (Third-party)

```python
# Use OAuth2 with django-oauth-toolkit
# Standard, flexible, revocable
pip install django-oauth-toolkit

OAUTH2_PROVIDER = {
    'SCOPES': {
        'read': 'Read access to your data',
        'write': 'Write access to your data',
    },
    'ACCESS_TOKEN_EXPIRE_SECONDS': 3600,
}
```

### For Both

```python
# Use both - OAuth2 to manage clients, JWT as token format
pip install django-oauth-toolkit djangorestframework-simplejwt

# Configure OAuth2 to issue JWTs (custom validator)
# Best of both worlds:
# - OAuth2 flows and scopes
# - JWT statelessness and performance
```

---

## Next Steps

- **Built-in Auth** → [builtin-auth.md](builtin-auth.md)
- **Token Setup** → [token-auth-setup.md](token-auth-setup.md)
- **Custom Auth** → [custom-auth.md](custom-auth.md)
- **Code Examples** → [examples/auth-patterns.py](examples/auth-patterns.py)

## References

- simplejwt: https://github.com/jazzband/djangorestframework-simplejwt
- django-oauth-toolkit: https://github.com/jazzband/django-oauth-toolkit
- OAuth2 RFC: https://tools.ietf.org/html/rfc6749
- JWT RFC: https://tools.ietf.org/html/rfc7519
- DRF Docs: `/home/user/django-rest-framework/docs/api-guide/authentication.md` (lines 360-455)
