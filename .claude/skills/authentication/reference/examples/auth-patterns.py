"""
Complete Authentication Patterns for Django REST Framework

This file contains production-ready code examples for common authentication
patterns. All code is tested and follows security best practices.

Usage:
    Copy the relevant code into your Django project and adapt as needed.

Table of Contents:
    1. Token Authentication with Lifecycle Management
    2. API Key Authentication with Scopes
    3. JWT Authentication with Custom Claims
    4. Session + Token Hybrid Authentication
    5. Rate-Limited Login View
    6. Two-Factor Authentication
    7. API Key Management Views
    8. Custom Permission Classes
"""

# ==============================================================================
# 1. Token Authentication with Lifecycle Management
# ==============================================================================

from django.conf import settings
from django.db import models
from django.utils import timezone
from rest_framework import authentication, exceptions
from rest_framework.authtoken.models import Token as DefaultToken
from datetime import timedelta
import secrets


class ManagedToken(models.Model):
    """
    Token with expiration, device tracking, and usage monitoring.
    Drop-in replacement for rest_framework.authtoken.models.Token
    """
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='auth_tokens'
    )
    key = models.CharField(max_length=40, unique=True, db_index=True)
    created = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField()
    last_used = models.DateTimeField(null=True, blank=True)

    # Device tracking
    device_name = models.CharField(max_length=100, blank=True)
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    user_agent = models.TextField(blank=True)

    class Meta:
        ordering = ['-created']
        verbose_name = 'Managed Token'
        verbose_name_plural = 'Managed Tokens'

    def __str__(self):
        return f"{self.user.username} - {self.device_name or 'Unknown Device'}"

    def save(self, *args, **kwargs):
        if not self.key:
            self.key = self.generate_key()
        if not self.expires_at:
            self.expires_at = timezone.now() + timedelta(days=30)
        super().save(*args, **kwargs)

    @staticmethod
    def generate_key():
        return secrets.token_hex(20)

    def is_expired(self):
        return timezone.now() > self.expires_at

    def extend_expiry(self, days=30):
        """Extend token expiration by specified days."""
        self.expires_at = timezone.now() + timedelta(days=days)
        self.save(update_fields=['expires_at'])

    def update_usage(self, request):
        """Update last used timestamp and IP."""
        self.last_used = timezone.now()
        self.ip_address = self.get_client_ip(request)
        self.save(update_fields=['last_used', 'ip_address'])

    @staticmethod
    def get_client_ip(request):
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            ip = x_forwarded_for.split(',')[0]
        else:
            ip = request.META.get('REMOTE_ADDR')
        return ip


class ManagedTokenAuthentication(authentication.TokenAuthentication):
    """
    Token authentication with expiration and usage tracking.
    """
    model = ManagedToken

    def authenticate_credentials(self, key):
        try:
            token = self.model.objects.select_related('user').get(key=key)
        except self.model.DoesNotExist:
            raise exceptions.AuthenticationFailed('Invalid token.')

        if not token.user.is_active:
            raise exceptions.AuthenticationFailed('User inactive or deleted.')

        if token.is_expired():
            token.delete()  # Clean up expired token
            raise exceptions.AuthenticationFailed('Token has expired.')

        # Update usage (in background to avoid blocking request)
        # In production, use Celery task for this
        token.update_usage(self.request)

        return (token.user, token)

    def authenticate(self, request):
        # Store request for use in authenticate_credentials
        self.request = request
        return super().authenticate(request)


# ==============================================================================
# 2. API Key Authentication with Scopes
# ==============================================================================

class APIKey(models.Model):
    """
    API Key model with scope-based permissions.
    """
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='api_keys'
    )
    key = models.CharField(max_length=64, unique=True, db_index=True)
    name = models.CharField(max_length=100, help_text="Descriptive name")
    created = models.DateTimeField(auto_now_add=True)
    last_used = models.DateTimeField(null=True, blank=True)
    is_active = models.BooleanField(default=True)

    # Scopes define what this key can access
    scopes = models.JSONField(
        default=list,
        help_text="List of scopes: ['read', 'write', 'admin']"
    )

    # Optional: IP whitelist
    allowed_ips = models.JSONField(
        default=list,
        blank=True,
        help_text="List of allowed IP addresses. Empty = all IPs allowed."
    )

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
        return secrets.token_urlsafe(48)

    def has_scope(self, scope):
        """Check if this key has a specific scope."""
        if not self.scopes:  # Empty list = all scopes
            return True
        return scope in self.scopes

    def is_ip_allowed(self, ip):
        """Check if IP is allowed to use this key."""
        if not self.allowed_ips:  # Empty list = all IPs allowed
            return True
        return ip in self.allowed_ips


class APIKeyAuthentication(authentication.BaseAuthentication):
    """
    API Key authentication with scope and IP checking.
    """
    def authenticate(self, request):
        # Support multiple header formats
        api_key = self.get_api_key(request)
        if not api_key:
            return None

        return self.authenticate_credentials(api_key, request)

    def get_api_key(self, request):
        """Extract API key from various header formats."""
        # Format 1: X-API-Key header
        api_key = request.META.get('HTTP_X_API_KEY')
        if api_key:
            return api_key

        # Format 2: Authorization: ApiKey <key>
        auth_header = request.META.get('HTTP_AUTHORIZATION', '').split()
        if len(auth_header) == 2 and auth_header[0].lower() == 'apikey':
            return auth_header[1]

        return None

    def authenticate_credentials(self, key, request):
        try:
            api_key = APIKey.objects.select_related('user').get(
                key=key,
                is_active=True
            )
        except APIKey.DoesNotExist:
            raise exceptions.AuthenticationFailed('Invalid API key.')

        if not api_key.user.is_active:
            raise exceptions.AuthenticationFailed('User inactive or deleted.')

        # Check IP whitelist
        client_ip = self.get_client_ip(request)
        if not api_key.is_ip_allowed(client_ip):
            raise exceptions.AuthenticationFailed(
                f'API key not allowed from IP: {client_ip}'
            )

        # Update last used
        api_key.last_used = timezone.now()
        api_key.save(update_fields=['last_used'])

        return (api_key.user, api_key)

    @staticmethod
    def get_client_ip(request):
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            return x_forwarded_for.split(',')[0].strip()
        return request.META.get('REMOTE_ADDR')

    def authenticate_header(self, request):
        return 'ApiKey'


# ==============================================================================
# 3. JWT Authentication with Custom Claims
# ==============================================================================

import jwt
from datetime import datetime


class CustomJWTAuthentication(authentication.BaseAuthentication):
    """
    JWT authentication with custom claims and validation.
    Requires: pip install pyjwt
    """
    def authenticate(self, request):
        auth_header = request.META.get('HTTP_AUTHORIZATION', '').split()

        if not auth_header or auth_header[0].lower() != 'bearer':
            return None

        if len(auth_header) != 2:
            raise exceptions.AuthenticationFailed('Invalid token header.')

        try:
            token = auth_header[1]
            payload = self.decode_jwt(token)
        except jwt.ExpiredSignatureError:
            raise exceptions.AuthenticationFailed('Token has expired.')
        except jwt.InvalidTokenError as e:
            raise exceptions.AuthenticationFailed(f'Invalid token: {str(e)}')

        return self.authenticate_credentials(payload, request)

    def decode_jwt(self, token):
        """Decode and validate JWT token."""
        return jwt.decode(
            token,
            settings.SECRET_KEY,
            algorithms=['HS256'],
            options={
                'verify_exp': True,
                'verify_iat': True,
            }
        )

    def authenticate_credentials(self, payload, request):
        """Validate payload and return user."""
        from django.contrib.auth import get_user_model
        User = get_user_model()

        try:
            user_id = payload.get('user_id')
            user = User.objects.get(pk=user_id)
        except User.DoesNotExist:
            raise exceptions.AuthenticationFailed('User not found.')

        if not user.is_active:
            raise exceptions.AuthenticationFailed('User inactive.')

        # Validate custom claims
        self.validate_custom_claims(payload, user, request)

        return (user, payload)

    def validate_custom_claims(self, payload, user, request):
        """Validate custom JWT claims."""
        # Example: Check if user still has required role
        required_role = payload.get('role')
        if required_role == 'admin' and not user.is_staff:
            raise exceptions.AuthenticationFailed(
                'User no longer has admin role.'
            )

        # Example: Validate token version (for invalidating old tokens)
        token_version = payload.get('version', 1)
        user_token_version = getattr(user, 'token_version', 1)
        if token_version < user_token_version:
            raise exceptions.AuthenticationFailed(
                'Token has been invalidated. Please login again.'
            )

    @staticmethod
    def generate_jwt(user, expires_in_hours=24, **extra_claims):
        """Generate JWT token with custom claims."""
        now = datetime.utcnow()
        payload = {
            'user_id': user.pk,
            'username': user.username,
            'email': user.email,
            'role': 'admin' if user.is_staff else 'user',
            'version': getattr(user, 'token_version', 1),
            'exp': now + timedelta(hours=expires_in_hours),
            'iat': now,
            'iss': 'myapp',  # Issuer
        }
        payload.update(extra_claims)  # Add any extra claims

        return jwt.encode(payload, settings.SECRET_KEY, algorithm='HS256')


# ==============================================================================
# 4. Session + Token Hybrid Authentication
# ==============================================================================

class HybridAuthentication(authentication.BaseAuthentication):
    """
    Supports both session (for browsable API) and token authentication.
    Tries session first, then token.
    """
    def authenticate(self, request):
        # Try session authentication first
        user = getattr(request._request, 'user', None)
        if user and user.is_authenticated:
            # For session auth, enforce CSRF for unsafe methods
            if request.method in ['POST', 'PUT', 'PATCH', 'DELETE']:
                self.enforce_csrf(request)
            return (user, None)

        # Try token authentication
        return self.authenticate_token(request)

    def authenticate_token(self, request):
        """Authenticate using token."""
        auth_header = authentication.get_authorization_header(request).split()

        if not auth_header or auth_header[0].lower() != b'token':
            return None

        if len(auth_header) != 2:
            raise exceptions.AuthenticationFailed('Invalid token header.')

        try:
            token_key = auth_header[1].decode()
        except UnicodeError:
            raise exceptions.AuthenticationFailed('Invalid token characters.')

        return self.authenticate_token_credentials(token_key)

    def authenticate_token_credentials(self, key):
        """Validate token and return user."""
        try:
            token = DefaultToken.objects.select_related('user').get(key=key)
        except DefaultToken.DoesNotExist:
            raise exceptions.AuthenticationFailed('Invalid token.')

        if not token.user.is_active:
            raise exceptions.AuthenticationFailed('User inactive.')

        return (token.user, token)

    def enforce_csrf(self, request):
        """Enforce CSRF validation for session-based requests."""
        from django.middleware.csrf import CsrfViewMiddleware

        def dummy_get_response(request):
            return None

        check = CsrfViewMiddleware(dummy_get_response)
        check.process_request(request)
        reason = check.process_view(request, None, (), {})
        if reason:
            raise exceptions.PermissionDenied(f'CSRF Failed: {reason}')


# ==============================================================================
# 5. Rate-Limited Login View
# ==============================================================================

from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.throttling import AnonRateThrottle
from django.contrib.auth import authenticate
import logging

logger = logging.getLogger(__name__)


class LoginRateThrottle(AnonRateThrottle):
    """Strict rate limiting for login attempts."""
    rate = '5/hour'  # 5 attempts per hour per IP


class LoginView(APIView):
    """
    Secure login view with rate limiting, logging, and device tracking.
    """
    authentication_classes = []
    permission_classes = []
    throttle_classes = [LoginRateThrottle]

    def post(self, request):
        username = request.data.get('username')
        password = request.data.get('password')
        device_name = request.data.get('device_name', 'Unknown Device')

        if not username or not password:
            return Response(
                {'error': 'Username and password required.'},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Authenticate user
        user = authenticate(request=request, username=username, password=password)

        if not user:
            # Log failed attempt
            logger.warning(
                f'Failed login attempt for username={username} '
                f'from IP={self.get_client_ip(request)}'
            )
            return Response(
                {'error': 'Invalid username or password.'},
                status=status.HTTP_401_UNAUTHORIZED
            )

        # Log successful login
        logger.info(
            f'Successful login for user={user.username} '
            f'from IP={self.get_client_ip(request)}'
        )

        # Create or get token (use ManagedToken if available)
        token = self.create_token(user, request, device_name)

        return Response({
            'token': token.key,
            'user': {
                'id': user.pk,
                'username': user.username,
                'email': user.email,
            },
            'expires_at': token.expires_at if hasattr(token, 'expires_at') else None,
        })

    def create_token(self, user, request, device_name):
        """Create token with device tracking."""
        # Try to use ManagedToken if available
        try:
            token = ManagedToken.objects.create(
                user=user,
                device_name=device_name,
                ip_address=ManagedToken.get_client_ip(request),
                user_agent=request.META.get('HTTP_USER_AGENT', '')[:500],
            )
        except Exception:
            # Fall back to default Token
            token, created = DefaultToken.objects.get_or_create(user=user)

        return token

    @staticmethod
    def get_client_ip(request):
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            return x_forwarded_for.split(',')[0].strip()
        return request.META.get('REMOTE_ADDR')


class LogoutView(APIView):
    """
    Secure logout view that deletes the token.
    """
    def post(self, request):
        # Delete the user's token
        if hasattr(request, 'auth') and request.auth:
            request.auth.delete()
            return Response({'detail': 'Successfully logged out.'})

        return Response(
            {'error': 'Not authenticated.'},
            status=status.HTTP_400_BAD_REQUEST
        )


# ==============================================================================
# 6. Two-Factor Authentication
# ==============================================================================

import pyotp  # pip install pyotp
from django.core.cache import cache


class TwoFactorAuth(models.Model):
    """Two-factor authentication settings for users."""
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='two_factor'
    )
    secret = models.CharField(max_length=32, blank=True)
    is_enabled = models.BooleanField(default=False)
    backup_codes = models.JSONField(default=list, blank=True)
    created = models.DateTimeField(auto_now_add=True)

    def generate_secret(self):
        """Generate new TOTP secret."""
        self.secret = pyotp.random_base32()
        self.save(update_fields=['secret'])
        return self.secret

    def get_totp_uri(self):
        """Get provisioning URI for QR code."""
        totp = pyotp.TOTP(self.secret)
        return totp.provisioning_uri(
            name=self.user.email,
            issuer_name='MyApp'
        )

    def verify_token(self, token):
        """Verify TOTP token."""
        totp = pyotp.TOTP(self.secret)
        return totp.verify(token, valid_window=1)

    def generate_backup_codes(self, count=10):
        """Generate backup codes for recovery."""
        self.backup_codes = [
            secrets.token_hex(4) for _ in range(count)
        ]
        self.save(update_fields=['backup_codes'])
        return self.backup_codes

    def use_backup_code(self, code):
        """Use a backup code (one-time use)."""
        if code in self.backup_codes:
            self.backup_codes.remove(code)
            self.save(update_fields=['backup_codes'])
            return True
        return False


class TwoFactorLoginView(APIView):
    """Login flow with 2FA support."""
    authentication_classes = []
    permission_classes = []
    throttle_classes = [LoginRateThrottle]

    def post(self, request):
        username = request.data.get('username')
        password = request.data.get('password')

        user = authenticate(username=username, password=password)
        if not user:
            return Response(
                {'error': 'Invalid credentials.'},
                status=status.HTTP_401_UNAUTHORIZED
            )

        # Check if 2FA is enabled
        try:
            two_factor = user.two_factor
            if two_factor.is_enabled:
                # Generate temporary token
                temp_token = secrets.token_urlsafe(32)
                cache.set(f'2fa_{temp_token}', user.pk, timeout=300)  # 5 min

                return Response({
                    'temp_token': temp_token,
                    'requires_2fa': True,
                })
        except TwoFactorAuth.DoesNotExist:
            pass

        # No 2FA - create token directly
        token, created = DefaultToken.objects.get_or_create(user=user)
        return Response({'token': token.key})


class VerifyTwoFactorView(APIView):
    """Verify 2FA code and issue token."""
    authentication_classes = []
    permission_classes = []

    def post(self, request):
        temp_token = request.data.get('temp_token')
        code = request.data.get('code')

        # Get user from temp token
        user_id = cache.get(f'2fa_{temp_token}')
        if not user_id:
            return Response(
                {'error': 'Invalid or expired temporary token.'},
                status=status.HTTP_401_UNAUTHORIZED
            )

        from django.contrib.auth import get_user_model
        User = get_user_model()
        user = User.objects.get(pk=user_id)

        # Verify TOTP code or backup code
        two_factor = user.two_factor
        if two_factor.verify_token(code):
            valid = True
        elif two_factor.use_backup_code(code):
            valid = True
        else:
            valid = False

        if not valid:
            return Response(
                {'error': 'Invalid 2FA code.'},
                status=status.HTTP_401_UNAUTHORIZED
            )

        # Delete temp token
        cache.delete(f'2fa_{temp_token}')

        # Issue real token
        token, created = DefaultToken.objects.get_or_create(user=user)
        return Response({
            'token': token.key,
            'user': {
                'id': user.pk,
                'username': user.username,
            }
        })


# ==============================================================================
# 7. API Key Management Views
# ==============================================================================

from rest_framework.permissions import IsAuthenticated


class APIKeyListCreateView(APIView):
    """List and create API keys for authenticated user."""
    permission_classes = [IsAuthenticated]

    def get(self, request):
        """List all API keys for user."""
        keys = APIKey.objects.filter(user=request.user)
        data = [{
            'id': key.id,
            'name': key.name,
            'key': key.key[:8] + '...',  # Partial key
            'created': key.created,
            'last_used': key.last_used,
            'is_active': key.is_active,
            'scopes': key.scopes,
        } for key in keys]

        return Response(data)

    def post(self, request):
        """Create new API key."""
        name = request.data.get('name', 'API Key')
        scopes = request.data.get('scopes', [])
        allowed_ips = request.data.get('allowed_ips', [])

        # Validate scopes
        valid_scopes = ['read', 'write', 'admin']
        if not all(scope in valid_scopes for scope in scopes):
            return Response(
                {'error': f'Invalid scopes. Valid: {valid_scopes}'},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Create key
        api_key = APIKey.objects.create(
            user=request.user,
            name=name,
            scopes=scopes,
            allowed_ips=allowed_ips,
        )

        return Response({
            'id': api_key.id,
            'name': api_key.name,
            'key': api_key.key,  # Full key shown only once!
            'created': api_key.created,
            'scopes': api_key.scopes,
        }, status=status.HTTP_201_CREATED)


class APIKeyDetailView(APIView):
    """Manage individual API key."""
    permission_classes = [IsAuthenticated]

    def delete(self, request, key_id):
        """Delete (revoke) API key."""
        try:
            api_key = APIKey.objects.get(id=key_id, user=request.user)
            api_key.delete()
            return Response({'detail': 'API key deleted.'})
        except APIKey.DoesNotExist:
            return Response(
                {'error': 'API key not found.'},
                status=status.HTTP_404_NOT_FOUND
            )

    def patch(self, request, key_id):
        """Update API key (name, scopes, active status)."""
        try:
            api_key = APIKey.objects.get(id=key_id, user=request.user)
        except APIKey.DoesNotExist:
            return Response(
                {'error': 'API key not found.'},
                status=status.HTTP_404_NOT_FOUND
            )

        # Update fields
        if 'name' in request.data:
            api_key.name = request.data['name']
        if 'is_active' in request.data:
            api_key.is_active = request.data['is_active']
        if 'scopes' in request.data:
            api_key.scopes = request.data['scopes']

        api_key.save()

        return Response({
            'id': api_key.id,
            'name': api_key.name,
            'is_active': api_key.is_active,
            'scopes': api_key.scopes,
        })


# ==============================================================================
# 8. Custom Permission Classes
# ==============================================================================

from rest_framework import permissions


class HasAPIKeyScope(permissions.BasePermission):
    """
    Permission to check if API key has required scope.
    Usage: Set required_scopes on view.
    """
    def has_permission(self, request, view):
        # Get required scopes from view
        required_scopes = getattr(view, 'required_scopes', [])
        if not required_scopes:
            return True

        # Check if authenticated via API key
        if not isinstance(request.auth, APIKey):
            return True  # Not API key auth, allow

        # Check if key has all required scopes
        for scope in required_scopes:
            if not request.auth.has_scope(scope):
                return False

        return True

    def has_object_permission(self, request, view, obj):
        # Same logic for object-level
        return self.has_permission(request, view)


class IsOwnerOrAdmin(permissions.BasePermission):
    """
    Object-level permission to only allow owners or admins.
    """
    def has_object_permission(self, request, view, obj):
        # Admin can access everything
        if request.user.is_staff:
            return True

        # Check if user is owner
        return obj.user == request.user


class IsAuthenticatedOrReadOnly(permissions.BasePermission):
    """
    Allow read-only access to anyone, but write access only to authenticated.
    """
    def has_permission(self, request, view):
        # Read permissions for everyone
        if request.method in permissions.SAFE_METHODS:
            return True

        # Write permissions only for authenticated
        return request.user and request.user.is_authenticated


# ==============================================================================
# Usage Examples
# ==============================================================================

"""
# Example 1: Using ManagedToken in views
from rest_framework.views import APIView
from rest_framework.response import Response

class MyView(APIView):
    authentication_classes = [ManagedTokenAuthentication]
    permission_classes = [IsAuthenticated]

    def get(self, request):
        # request.auth is the ManagedToken instance
        token = request.auth
        return Response({
            'device': token.device_name,
            'expires_at': token.expires_at,
            'last_used': token.last_used,
        })

# Example 2: Using API Key with scopes
class ProtectedView(APIView):
    authentication_classes = [APIKeyAuthentication]
    permission_classes = [IsAuthenticated, HasAPIKeyScope]
    required_scopes = ['read', 'write']

    def get(self, request):
        # Only API keys with 'read' and 'write' scopes can access
        return Response({'data': 'protected'})

# Example 3: Using JWT
class JWTProtectedView(APIView):
    authentication_classes = [CustomJWTAuthentication]
    permission_classes = [IsAuthenticated]

    def get(self, request):
        # request.auth is the JWT payload
        payload = request.auth
        return Response({
            'role': payload.get('role'),
            'exp': payload.get('exp'),
        })

# Example 4: URL Configuration
from django.urls import path

urlpatterns = [
    # Authentication
    path('api/auth/login/', LoginView.as_view(), name='login'),
    path('api/auth/logout/', LogoutView.as_view(), name='logout'),
    path('api/auth/2fa/verify/', VerifyTwoFactorView.as_view(), name='verify_2fa'),

    # API Key Management
    path('api/keys/', APIKeyListCreateView.as_view(), name='api_keys'),
    path('api/keys/<int:key_id>/', APIKeyDetailView.as_view(), name='api_key_detail'),
]
"""
