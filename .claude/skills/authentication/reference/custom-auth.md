# Creating Custom Authentication Classes

Learn how to build custom authentication classes for specific use cases like API keys, custom headers, multi-factor authentication, and more.

## Table of Contents
1. [BaseAuthentication Overview](#baseauthentication-overview)
2. [Simple Custom Authentication](#simple-custom-authentication)
3. [API Key Authentication](#api-key-authentication)
4. [Header-Based Authentication](#header-based-authentication)
5. [JWT with Custom Claims](#jwt-with-custom-claims)
6. [Multi-Factor Authentication Hook](#multi-factor-authentication-hook)
7. [Best Practices](#best-practices)

---

## BaseAuthentication Overview

All authentication classes must inherit from `BaseAuthentication` and implement:

```python
from rest_framework.authentication import BaseAuthentication
from rest_framework import exceptions

class CustomAuth(BaseAuthentication):
    def authenticate(self, request):
        """
        Returns:
        - (user, auth) tuple if authentication succeeds
        - None if authentication is not attempted
        Raises:
        - AuthenticationFailed if authentication attempted but fails
        """
        pass

    def authenticate_header(self, request):
        """
        Returns:
        - String for WWW-Authenticate header (for 401 responses)
        - None to return 403 instead of 401
        """
        pass
```

### Return Values

| Return | Meaning | When to Use |
|--------|---------|-------------|
| `(user, auth)` | Success | Valid credentials provided |
| `None` | Not attempted | No credentials in request |
| Raise `AuthenticationFailed` | Failed | Invalid credentials provided |

### Key Decision: Return None vs Raise Exception

```python
# ✅ CORRECT: Return None if auth not attempted
def authenticate(self, request):
    auth_header = request.META.get('HTTP_X_API_KEY')
    if not auth_header:
        return None  # No API key provided, try next auth class

    # API key provided but invalid
    if not self.is_valid_key(auth_header):
        raise exceptions.AuthenticationFailed('Invalid API key')

    return (user, api_key)

# ❌ WRONG: Raising exception when no credentials
def authenticate(self, request):
    auth_header = request.META.get('HTTP_X_API_KEY')
    if not auth_header:
        raise exceptions.AuthenticationFailed('No API key')  # Wrong!
    # This prevents other authentication classes from being tried
```

---

## Simple Custom Authentication

### Example 1: Username from Header

Authenticate users based on a custom header (for development/testing):

```python
# myapp/authentication.py
from django.contrib.auth import get_user_model
from rest_framework import authentication, exceptions

User = get_user_model()

class HeaderAuthentication(authentication.BaseAuthentication):
    """
    Authenticate based on X-Username header.
    WARNING: Only for development/testing!
    """
    def authenticate(self, request):
        username = request.META.get('HTTP_X_USERNAME')

        # No header provided - auth not attempted
        if not username:
            return None

        # Header provided - try to authenticate
        try:
            user = User.objects.get(username=username)
        except User.DoesNotExist:
            raise exceptions.AuthenticationFailed('No such user')

        # Check user is active
        if not user.is_active:
            raise exceptions.AuthenticationFailed('User inactive')

        return (user, None)  # auth can be None or any object

    def authenticate_header(self, request):
        # Return value for WWW-Authenticate header
        return 'X-Username'
```

**Usage:**
```python
# settings.py
REST_FRAMEWORK = {
    'DEFAULT_AUTHENTICATION_CLASSES': [
        'myapp.authentication.HeaderAuthentication',
    ],
}

# Test with curl
curl -H "X-Username: john" http://localhost:8000/api/resource/
```

---

## API Key Authentication

### Complete Implementation

```python
# myapp/models.py
from django.db import models
from django.conf import settings
import secrets

class APIKey(models.Model):
    """
    API Key model for application/service authentication.
    """
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='api_keys'
    )
    key = models.CharField(max_length=64, unique=True, db_index=True)
    name = models.CharField(max_length=100, help_text="Descriptive name for this key")
    created = models.DateTimeField(auto_now_add=True)
    last_used = models.DateTimeField(null=True, blank=True)
    is_active = models.BooleanField(default=True)

    # Optional: Scope/permissions for this key
    scopes = models.JSONField(default=list, blank=True)

    class Meta:
        ordering = ['-created']

    def __str__(self):
        return f"{self.name} ({self.key[:8]}...)"

    def save(self, *args, **kwargs):
        if not self.key:
            self.key = self.generate_key()
        super().save(*args, **kwargs)

    @staticmethod
    def generate_key():
        # Generate cryptographically secure key
        return secrets.token_urlsafe(48)  # 64 character key

    def has_scope(self, scope):
        """Check if this key has a specific scope."""
        return scope in self.scopes if self.scopes else True

# myapp/authentication.py
from django.utils import timezone
from rest_framework import authentication, exceptions
from .models import APIKey

class APIKeyAuthentication(authentication.BaseAuthentication):
    """
    Authentication based on API keys.

    Clients should authenticate by passing the API key in the
    "X-API-Key" HTTP header.
    """
    keyword = 'X-API-Key'

    def authenticate(self, request):
        api_key = request.META.get('HTTP_X_API_KEY')

        if not api_key:
            return None  # No API key provided

        return self.authenticate_credentials(api_key)

    def authenticate_credentials(self, key):
        try:
            api_key = APIKey.objects.select_related('user').get(
                key=key,
                is_active=True
            )
        except APIKey.DoesNotExist:
            raise exceptions.AuthenticationFailed('Invalid API key')

        if not api_key.user.is_active:
            raise exceptions.AuthenticationFailed('User inactive or deleted')

        # Update last used timestamp
        api_key.last_used = timezone.now()
        api_key.save(update_fields=['last_used'])

        # Return user and api_key object
        # request.auth will be the APIKey instance
        return (api_key.user, api_key)

    def authenticate_header(self, request):
        return self.keyword
```

### Management Views

```python
# myapp/views.py
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from rest_framework import status
from .models import APIKey

class APIKeyListView(APIView):
    """List all API keys for the authenticated user."""
    permission_classes = [IsAuthenticated]

    def get(self, request):
        keys = APIKey.objects.filter(user=request.user)
        data = [{
            'id': key.id,
            'name': key.name,
            'key': key.key[:8] + '...',  # Don't expose full key
            'created': key.created,
            'last_used': key.last_used,
            'is_active': key.is_active,
        } for key in keys]
        return Response(data)

    def post(self, request):
        """Create a new API key."""
        name = request.data.get('name', 'API Key')
        scopes = request.data.get('scopes', [])

        api_key = APIKey.objects.create(
            user=request.user,
            name=name,
            scopes=scopes
        )

        return Response({
            'id': api_key.id,
            'name': api_key.name,
            'key': api_key.key,  # Full key shown only once!
            'created': api_key.created,
        }, status=status.HTTP_201_CREATED)

class APIKeyDetailView(APIView):
    """Manage individual API key."""
    permission_classes = [IsAuthenticated]

    def delete(self, request, key_id):
        """Revoke an API key."""
        try:
            api_key = APIKey.objects.get(id=key_id, user=request.user)
            api_key.delete()
            return Response({'detail': 'API key revoked'})
        except APIKey.DoesNotExist:
            return Response(
                {'detail': 'API key not found'},
                status=status.HTTP_404_NOT_FOUND
            )
```

### Scope-Based Permissions

```python
# myapp/permissions.py
from rest_framework import permissions

class HasAPIKeyScope(permissions.BasePermission):
    """
    Permission to check if API key has required scope.
    """
    def has_permission(self, request, view):
        # Get required scope from view
        required_scope = getattr(view, 'required_scope', None)
        if not required_scope:
            return True  # No scope required

        # Check if authenticated via API key
        if not hasattr(request.auth, 'has_scope'):
            return True  # Not API key auth, allow other auth methods

        # Check scope
        return request.auth.has_scope(required_scope)

# Usage in views
class ProtectedView(APIView):
    authentication_classes = [APIKeyAuthentication]
    permission_classes = [IsAuthenticated, HasAPIKeyScope]
    required_scope = 'read:data'

    def get(self, request):
        return Response({'data': 'secret'})
```

---

## Header-Based Authentication

### Example: API Key in Custom Header Format

```python
# Support multiple header formats
class FlexibleAPIKeyAuthentication(authentication.BaseAuthentication):
    """
    Support multiple API key formats:
    1. X-API-Key: <key>
    2. Authorization: ApiKey <key>
    3. Authorization: Bearer <key>
    """
    def authenticate(self, request):
        # Try X-API-Key header first
        api_key = request.META.get('HTTP_X_API_KEY')
        if api_key:
            return self.authenticate_credentials(api_key)

        # Try Authorization header
        auth_header = request.META.get('HTTP_AUTHORIZATION', '').split()
        if len(auth_header) == 2:
            auth_type, key = auth_header
            if auth_type.lower() in ['apikey', 'bearer']:
                return self.authenticate_credentials(key)

        # No API key found
        return None

    def authenticate_credentials(self, key):
        try:
            api_key = APIKey.objects.select_related('user').get(
                key=key,
                is_active=True
            )
            return (api_key.user, api_key)
        except APIKey.DoesNotExist:
            raise exceptions.AuthenticationFailed('Invalid API key')
```

---

## JWT with Custom Claims

### Custom JWT Authentication

```python
# myapp/authentication.py
import jwt
from django.conf import settings
from django.contrib.auth import get_user_model
from rest_framework import authentication, exceptions
from datetime import datetime, timedelta

User = get_user_model()

class CustomJWTAuthentication(authentication.BaseAuthentication):
    """
    Custom JWT authentication with additional claims.
    """
    def authenticate(self, request):
        auth_header = request.META.get('HTTP_AUTHORIZATION', '').split()

        if not auth_header or auth_header[0].lower() != 'bearer':
            return None

        if len(auth_header) == 1:
            raise exceptions.AuthenticationFailed('Invalid token header. No credentials provided.')
        elif len(auth_header) > 2:
            raise exceptions.AuthenticationFailed('Invalid token header. Token string should not contain spaces.')

        try:
            token = auth_header[1]
            payload = self.decode_jwt(token)
        except jwt.ExpiredSignatureError:
            raise exceptions.AuthenticationFailed('Token has expired')
        except jwt.InvalidTokenError:
            raise exceptions.AuthenticationFailed('Invalid token')

        return self.authenticate_credentials(payload)

    def decode_jwt(self, token):
        """Decode and validate JWT token."""
        return jwt.decode(
            token,
            settings.SECRET_KEY,
            algorithms=['HS256']
        )

    def authenticate_credentials(self, payload):
        """Get user from token payload."""
        try:
            user_id = payload.get('user_id')
            user = User.objects.get(pk=user_id)
        except User.DoesNotExist:
            raise exceptions.AuthenticationFailed('User not found')

        if not user.is_active:
            raise exceptions.AuthenticationFailed('User inactive')

        # Check custom claims
        required_role = payload.get('role')
        if required_role == 'admin' and not user.is_staff:
            raise exceptions.AuthenticationFailed('Insufficient permissions')

        return (user, payload)

    @staticmethod
    def generate_jwt(user, expires_in_hours=24):
        """Generate JWT token for user."""
        payload = {
            'user_id': user.pk,
            'username': user.username,
            'email': user.email,
            'role': 'admin' if user.is_staff else 'user',
            'exp': datetime.utcnow() + timedelta(hours=expires_in_hours),
            'iat': datetime.utcnow(),
        }
        return jwt.encode(payload, settings.SECRET_KEY, algorithm='HS256')

# myapp/views.py
class JWTLoginView(APIView):
    authentication_classes = []
    permission_classes = []

    def post(self, request):
        username = request.data.get('username')
        password = request.data.get('password')

        user = authenticate(username=username, password=password)
        if not user:
            raise exceptions.AuthenticationFailed('Invalid credentials')

        token = CustomJWTAuthentication.generate_jwt(user)
        return Response({
            'token': token,
            'user': {
                'id': user.pk,
                'username': user.username,
                'email': user.email,
            }
        })
```

---

## Multi-Factor Authentication Hook

### Two-Factor Authentication Flow

```python
# myapp/models.py
from django.db import models
from django.conf import settings
import pyotp

class TwoFactorAuth(models.Model):
    """Store 2FA settings for users."""
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='two_factor'
    )
    secret = models.CharField(max_length=32)
    is_enabled = models.BooleanField(default=False)
    backup_codes = models.JSONField(default=list)

    def verify_token(self, token):
        """Verify TOTP token."""
        totp = pyotp.TOTP(self.secret)
        return totp.verify(token, valid_window=1)

# myapp/authentication.py
class TwoFactorAuthentication(authentication.BaseAuthentication):
    """
    Requires 2FA verification after initial authentication.

    Flow:
    1. User logs in with username/password -> gets temporary token
    2. User submits TOTP code with temporary token -> gets full token
    """
    def authenticate(self, request):
        # Get token from header
        auth_header = request.META.get('HTTP_AUTHORIZATION', '').split()
        if not auth_header or auth_header[0].lower() != 'bearer':
            return None

        if len(auth_header) != 2:
            raise exceptions.AuthenticationFailed('Invalid token header')

        token = auth_header[1]

        # Check if this is a temporary (pre-2FA) token
        if token.startswith('temp_'):
            raise exceptions.AuthenticationFailed('2FA required. Please verify with TOTP code.')

        # Validate full token (after 2FA)
        try:
            payload = jwt.decode(token, settings.SECRET_KEY, algorithms=['HS256'])
            user = User.objects.get(pk=payload['user_id'])

            # Verify 2FA was completed
            if not payload.get('two_factor_verified'):
                raise exceptions.AuthenticationFailed('2FA not verified')

            return (user, payload)

        except (jwt.InvalidTokenError, User.DoesNotExist):
            raise exceptions.AuthenticationFailed('Invalid token')

# myapp/views.py
class LoginView(APIView):
    """Step 1: Username/password login."""
    authentication_classes = []
    permission_classes = []

    def post(self, request):
        username = request.data.get('username')
        password = request.data.get('password')

        user = authenticate(username=username, password=password)
        if not user:
            raise exceptions.AuthenticationFailed('Invalid credentials')

        # Check if 2FA is enabled
        try:
            two_factor = user.two_factor
            if two_factor.is_enabled:
                # Return temporary token
                temp_token = f"temp_{secrets.token_urlsafe(32)}"
                # Store temp token in cache with user ID
                cache.set(temp_token, user.pk, timeout=300)  # 5 minutes

                return Response({
                    'temp_token': temp_token,
                    'requires_2fa': True,
                })
        except TwoFactorAuth.DoesNotExist:
            pass

        # No 2FA required - return full token
        token = self.generate_full_token(user)
        return Response({'token': token})

    def generate_full_token(self, user, two_factor_verified=False):
        payload = {
            'user_id': user.pk,
            'two_factor_verified': two_factor_verified,
            'exp': datetime.utcnow() + timedelta(hours=24),
        }
        return jwt.encode(payload, settings.SECRET_KEY, algorithm='HS256')

class VerifyTOTPView(APIView):
    """Step 2: Verify TOTP code."""
    authentication_classes = []
    permission_classes = []

    def post(self, request):
        temp_token = request.data.get('temp_token')
        totp_code = request.data.get('code')

        # Get user from temp token
        user_id = cache.get(temp_token)
        if not user_id:
            raise exceptions.AuthenticationFailed('Temporary token expired')

        user = User.objects.get(pk=user_id)

        # Verify TOTP
        if not user.two_factor.verify_token(totp_code):
            raise exceptions.AuthenticationFailed('Invalid 2FA code')

        # Delete temp token
        cache.delete(temp_token)

        # Return full token with 2FA verified
        token = LoginView().generate_full_token(user, two_factor_verified=True)
        return Response({'token': token})
```

---

## Best Practices

### 1. Always Validate User State

```python
def authenticate_credentials(self, credentials):
    user = self.get_user(credentials)

    # ✅ Always check if user is active
    if not user.is_active:
        raise exceptions.AuthenticationFailed('User inactive or deleted')

    # ✅ Check additional conditions
    if hasattr(user, 'profile') and user.profile.is_banned:
        raise exceptions.AuthenticationFailed('User account banned')

    return (user, credentials)
```

### 2. Use select_related for Performance

```python
# ❌ BAD: Causes N+1 queries
token = Token.objects.get(key=key)
user = token.user  # Additional query

# ✅ GOOD: Single query
token = Token.objects.select_related('user').get(key=key)
user = token.user  # No additional query
```

### 3. Implement Rate Limiting

```python
from rest_framework.throttling import AnonRateThrottle

class CustomAuthRateThrottle(AnonRateThrottle):
    rate = '5/minute'

class LoginView(APIView):
    throttle_classes = [CustomAuthRateThrottle]
```

### 4. Log Authentication Events

```python
import logging
logger = logging.getLogger(__name__)

def authenticate(self, request):
    try:
        result = self.do_authentication(request)
        if result:
            user, auth = result
            logger.info(f'Successful authentication for user {user.username}')
        return result
    except exceptions.AuthenticationFailed as e:
        logger.warning(f'Failed authentication attempt: {str(e)}')
        raise
```

### 5. Provide Clear Error Messages

```python
# ✅ GOOD: Specific, actionable errors
if not api_key:
    return None  # Not attempted

if api_key.is_expired():
    raise exceptions.AuthenticationFailed(
        'API key expired. Please generate a new key.'
    )

if not api_key.has_scope('read:data'):
    raise exceptions.AuthenticationFailed(
        'API key does not have required scope: read:data'
    )

# ❌ BAD: Vague errors
raise exceptions.AuthenticationFailed('Error')
```

### 6. Test Your Authentication

```python
# myapp/tests/test_authentication.py
from django.test import TestCase
from rest_framework.test import APIRequestFactory
from myapp.authentication import APIKeyAuthentication
from myapp.models import APIKey

class APIKeyAuthenticationTest(TestCase):
    def setUp(self):
        self.factory = APIRequestFactory()
        self.auth = APIKeyAuthentication()
        self.user = User.objects.create(username='testuser')
        self.api_key = APIKey.objects.create(user=self.user, name='Test Key')

    def test_valid_api_key(self):
        request = self.factory.get('/', HTTP_X_API_KEY=self.api_key.key)
        user, auth = self.auth.authenticate(request)
        self.assertEqual(user, self.user)

    def test_invalid_api_key(self):
        request = self.factory.get('/', HTTP_X_API_KEY='invalid')
        with self.assertRaises(exceptions.AuthenticationFailed):
            self.auth.authenticate(request)

    def test_no_api_key(self):
        request = self.factory.get('/')
        result = self.auth.authenticate(request)
        self.assertIsNone(result)
```

---

## Complete Example: Signature-Based Authentication

```python
# Advanced: HMAC signature authentication (like AWS)
import hmac
import hashlib
from django.utils import timezone
from datetime import timedelta

class SignatureAuthentication(authentication.BaseAuthentication):
    """
    HMAC signature-based authentication.

    Client signs request with secret key:
    Signature = HMAC-SHA256(secret_key, "method:path:timestamp:body")

    Headers:
    - X-API-Key: <api_key_id>
    - X-Timestamp: <unix_timestamp>
    - X-Signature: <hmac_signature>
    """
    def authenticate(self, request):
        api_key_id = request.META.get('HTTP_X_API_KEY')
        timestamp = request.META.get('HTTP_X_TIMESTAMP')
        signature = request.META.get('HTTP_X_SIGNATURE')

        if not all([api_key_id, timestamp, signature]):
            return None

        # Verify timestamp (prevent replay attacks)
        try:
            request_time = timezone.datetime.fromtimestamp(int(timestamp))
            if timezone.now() - request_time > timedelta(minutes=5):
                raise exceptions.AuthenticationFailed('Request timestamp too old')
        except ValueError:
            raise exceptions.AuthenticationFailed('Invalid timestamp')

        # Get API key
        try:
            api_key = APIKey.objects.select_related('user').get(
                id=api_key_id,
                is_active=True
            )
        except APIKey.DoesNotExist:
            raise exceptions.AuthenticationFailed('Invalid API key')

        # Verify signature
        expected_signature = self.calculate_signature(
            secret=api_key.key,
            method=request.method,
            path=request.path,
            timestamp=timestamp,
            body=request.body
        )

        if not hmac.compare_digest(signature, expected_signature):
            raise exceptions.AuthenticationFailed('Invalid signature')

        return (api_key.user, api_key)

    @staticmethod
    def calculate_signature(secret, method, path, timestamp, body):
        """Calculate HMAC signature."""
        message = f"{method}:{path}:{timestamp}:{body.decode('utf-8')}"
        signature = hmac.new(
            secret.encode('utf-8'),
            message.encode('utf-8'),
            hashlib.sha256
        ).hexdigest()
        return signature
```

---

## Next Steps

- **Built-in Auth Classes** → [builtin-auth.md](builtin-auth.md)
- **Token Setup Guide** → [token-auth-setup.md](token-auth-setup.md)
- **JWT vs OAuth** → [jwt-oauth-guide.md](jwt-oauth-guide.md)
- **Code Examples** → [examples/auth-patterns.py](examples/auth-patterns.py)

## References

- DRF BaseAuthentication: `/home/user/django-rest-framework/rest_framework/authentication.py` (lines 33-50)
- Official Docs: `/home/user/django-rest-framework/docs/api-guide/authentication.md` (lines 315-353)
