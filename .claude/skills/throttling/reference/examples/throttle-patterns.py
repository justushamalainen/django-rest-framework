"""
DRF Throttling Patterns - Working Code Examples

This file contains complete, working examples of various throttling patterns.
Each example includes the throttle class, view usage, and settings configuration.
"""

from rest_framework.throttling import (
    SimpleRateThrottle,
    UserRateThrottle,
    AnonRateThrottle,
    ScopedRateThrottle,
    BaseThrottle
)
from rest_framework.views import APIView
from rest_framework.viewsets import ModelViewSet
from rest_framework.response import Response
from rest_framework.decorators import action
from rest_framework.exceptions import Throttled
from django.core.cache import cache, caches
from django.contrib.auth.models import User
from datetime import datetime
import time
import hashlib


# ==============================================================================
# BASIC THROTTLING PATTERNS
# ==============================================================================

class BasicAPIView(APIView):
    """
    Basic view with global throttles from settings.

    Settings required:
        REST_FRAMEWORK = {
            'DEFAULT_THROTTLE_CLASSES': [
                'rest_framework.throttling.AnonRateThrottle',
                'rest_framework.throttling.UserRateThrottle',
            ],
            'DEFAULT_THROTTLE_RATES': {
                'anon': '100/day',
                'user': '1000/day',
            }
        }
    """
    def get(self, request):
        return Response({'message': 'Success'})


class PerViewThrottleAPIView(APIView):
    """
    View with specific throttle classes (overrides global defaults).
    """
    throttle_classes = [AnonRateThrottle]

    def get(self, request):
        return Response({'message': 'Only anonymous throttling applied'})


class NoThrottleAPIView(APIView):
    """
    View with throttling disabled.
    """
    throttle_classes = []

    def get(self, request):
        return Response({'message': 'No throttling on this endpoint'})


# ==============================================================================
# BURST + SUSTAINED THROTTLING
# ==============================================================================

class BurstRateThrottle(UserRateThrottle):
    """
    Throttle to prevent rapid burst requests.

    Settings:
        'DEFAULT_THROTTLE_RATES': {
            'burst': '60/min',  # Max 1 per second sustained
        }
    """
    scope = 'burst'


class SustainedRateThrottle(UserRateThrottle):
    """
    Throttle for overall daily limit.

    Settings:
        'DEFAULT_THROTTLE_RATES': {
            'sustained': '10000/day',  # About 7/minute average
        }
    """
    scope = 'sustained'


class BurstProtectedView(APIView):
    """
    View protected by both burst and sustained throttles.
    User must satisfy BOTH limits.
    """
    throttle_classes = [BurstRateThrottle, SustainedRateThrottle]

    def get(self, request):
        return Response({'message': 'Protected by burst + sustained throttles'})


# ==============================================================================
# SUBSCRIPTION TIER THROTTLING
# ==============================================================================

class SubscriptionRateThrottle(SimpleRateThrottle):
    """
    Different rate limits based on user subscription tier.

    Assumes user model has 'subscription_tier' attribute.

    Settings:
        'DEFAULT_THROTTLE_RATES': {
            'tier_free': '100/day',
            'tier_basic': '1000/day',
            'tier_premium': '10000/day',
            'tier_enterprise': '100000/day',
        }

    Cache keys:
        - throttle_tier_free_42 (user 42 on free tier)
        - throttle_tier_premium_123 (user 123 on premium tier)
    """

    def get_cache_key(self, request, view):
        if not request.user.is_authenticated:
            return None  # Don't throttle anonymous users

        # Get user's subscription tier (with fallback)
        tier = getattr(request.user, 'subscription_tier', 'free')
        self.scope = f'tier_{tier}'

        # Validate tier has configured rate
        if self.scope not in self.THROTTLE_RATES:
            self.scope = 'tier_free'  # Fallback to free tier

        # Update rate for this request
        self.rate = self.get_rate()
        self.num_requests, self.duration = self.parse_rate(self.rate)

        return self.cache_format % {
            'scope': self.scope,
            'ident': request.user.pk
        }


class SubscriptionAPIView(APIView):
    """
    API endpoint with subscription-based throttling.
    """
    throttle_classes = [SubscriptionRateThrottle]

    def get(self, request):
        tier = getattr(request.user, 'subscription_tier', 'free')
        return Response({
            'message': 'Success',
            'tier': tier
        })


# ==============================================================================
# API KEY THROTTLING
# ==============================================================================

class APIKeyRateThrottle(SimpleRateThrottle):
    """
    Throttle based on API key instead of user.

    Expects API key in 'X-API-Key' header.

    Settings:
        'DEFAULT_THROTTLE_RATES': {
            'api_key': '1000/hour',
        }

    Usage:
        curl -H "X-API-Key: your-api-key-here" http://api.example.com/
    """
    scope = 'api_key'

    def get_cache_key(self, request, view):
        # Get API key from header
        api_key = request.META.get('HTTP_X_API_KEY')

        if not api_key:
            # No API key provided - could fallback to IP or return None
            return None

        return self.cache_format % {
            'scope': self.scope,
            'ident': api_key
        }


class APIKeyProtectedView(APIView):
    """
    View protected by API key throttling.
    """
    throttle_classes = [APIKeyRateThrottle]

    def get(self, request):
        api_key = request.META.get('HTTP_X_API_KEY', 'none')
        return Response({
            'message': 'Success',
            'api_key': api_key[:8] + '...' if api_key != 'none' else 'none'
        })


# ==============================================================================
# METHOD-BASED THROTTLING
# ==============================================================================

class MethodRateThrottle(SimpleRateThrottle):
    """
    Different rate limits per HTTP method.

    Settings:
        'DEFAULT_THROTTLE_RATES': {
            'method_get': '1000/hour',
            'method_post': '100/hour',
            'method_put': '100/hour',
            'method_patch': '100/hour',
            'method_delete': '50/hour',
        }
    """

    def get_cache_key(self, request, view):
        # Identify user
        if request.user.is_authenticated:
            ident = request.user.pk
        else:
            ident = self.get_ident(request)

        # Set scope based on HTTP method
        method = request.method.lower()
        self.scope = f'method_{method}'

        # Check if rate is configured for this method
        if self.scope not in self.THROTTLE_RATES:
            return None  # No throttling for this method

        # Update rate
        self.rate = self.get_rate()
        self.num_requests, self.duration = self.parse_rate(self.rate)

        return self.cache_format % {
            'scope': self.scope,
            'ident': ident
        }


class MethodThrottledView(APIView):
    """
    View with different throttles per method.
    """
    throttle_classes = [MethodRateThrottle]

    def get(self, request):
        return Response({'message': 'GET allowed 1000/hour'})

    def post(self, request):
        return Response({'message': 'POST allowed 100/hour'})

    def delete(self, request):
        return Response({'message': 'DELETE allowed 50/hour'})


# ==============================================================================
# TIME-BASED THROTTLING
# ==============================================================================

class TimeBasisRateThrottle(SimpleRateThrottle):
    """
    Different rate limits based on time of day (peak vs off-peak hours).

    Settings:
        'DEFAULT_THROTTLE_RATES': {
            'peak_hours': '100/hour',    # 9 AM - 5 PM
            'off_peak': '1000/hour',     # Outside business hours
        }
    """

    def get_cache_key(self, request, view):
        # Identify user
        if request.user.is_authenticated:
            ident = request.user.pk
        else:
            ident = self.get_ident(request)

        # Determine if peak hours (9 AM - 5 PM)
        hour = datetime.now().hour
        if 9 <= hour < 17:
            self.scope = 'peak_hours'
        else:
            self.scope = 'off_peak'

        # Update rate
        self.rate = self.get_rate()
        self.num_requests, self.duration = self.parse_rate(self.rate)

        return self.cache_format % {
            'scope': self.scope,
            'ident': ident
        }


class TimeBasedView(APIView):
    """
    View with time-based throttling.
    """
    throttle_classes = [TimeBasisRateThrottle]

    def get(self, request):
        hour = datetime.now().hour
        period = 'peak' if 9 <= hour < 17 else 'off-peak'
        return Response({
            'message': 'Success',
            'period': period,
            'hour': hour
        })


# ==============================================================================
# SCOPED THROTTLING
# ==============================================================================

class ContactsView(APIView):
    """
    View with contacts-specific throttle scope.
    """
    throttle_classes = [ScopedRateThrottle]
    throttle_scope = 'contacts'

    def get(self, request):
        return Response({'contacts': []})

    def post(self, request):
        return Response({'status': 'contact created'})


class UploadsView(APIView):
    """
    View with uploads-specific throttle scope (stricter limits).
    """
    throttle_classes = [ScopedRateThrottle]
    throttle_scope = 'uploads'

    def post(self, request):
        return Response({'status': 'file uploaded'})


class MessagesView(APIView):
    """
    View with messages-specific throttle scope.
    """
    throttle_classes = [ScopedRateThrottle]
    throttle_scope = 'messages'

    def get(self, request):
        return Response({'messages': []})

    def post(self, request):
        return Response({'status': 'message sent'})


# Settings for scoped throttling:
# 'DEFAULT_THROTTLE_RATES': {
#     'contacts': '1000/day',
#     'uploads': '20/day',
#     'messages': '100/hour',
# }


# ==============================================================================
# VIEWSET PER-ACTION THROTTLING
# ==============================================================================

class DocumentUploadThrottle(UserRateThrottle):
    scope = 'document_upload'


class DocumentModifyThrottle(UserRateThrottle):
    scope = 'document_modify'


class DocumentReadThrottle(UserRateThrottle):
    scope = 'document_read'


class DocumentViewSet(ModelViewSet):
    """
    ViewSet with different throttles per action.

    Settings:
        'DEFAULT_THROTTLE_RATES': {
            'document_upload': '10/hour',
            'document_modify': '50/hour',
            'document_read': '1000/hour',
        }
    """
    # Assuming you have a Document model
    # queryset = Document.objects.all()
    # serializer_class = DocumentSerializer

    def get_throttles(self):
        """
        Return different throttles based on action.
        """
        if self.action == 'create':
            throttle_classes = [DocumentUploadThrottle]
        elif self.action in ['update', 'partial_update', 'destroy']:
            throttle_classes = [DocumentModifyThrottle]
        else:  # list, retrieve
            throttle_classes = [DocumentReadThrottle]

        return [throttle() for throttle in throttle_classes]


class DocumentViewSetWithScope(ModelViewSet):
    """
    Alternative: Using ScopedRateThrottle with dynamic scope.
    """
    throttle_classes = [ScopedRateThrottle]

    @property
    def throttle_scope(self):
        """
        Return scope name based on current action.
        """
        if self.action == 'create':
            return 'document_upload'
        elif self.action in ['update', 'partial_update', 'destroy']:
            return 'document_modify'
        else:
            return 'document_read'


# ==============================================================================
# CUSTOM ALGORITHM: CONCURRENT REQUEST THROTTLE
# ==============================================================================

class ConcurrentRequestThrottle(BaseThrottle):
    """
    Throttle based on number of concurrent requests, not rate.
    Limits simultaneous requests per user.

    Configuration:
        class MyThrottle(ConcurrentRequestThrottle):
            max_concurrent = 5  # Max 5 simultaneous requests
            timeout = 60  # Request assumed finished after 60 seconds
    """
    max_concurrent = 5
    timeout = 60

    def allow_request(self, request, view):
        if not request.user.is_authenticated:
            return True  # Don't throttle anonymous

        cache_key = f'concurrent_requests_{request.user.pk}'
        now = time.time()

        # Get current request timestamps
        requests = cache.get(cache_key, [])

        # Remove finished requests (older than timeout)
        active_requests = [ts for ts in requests if now - ts < self.timeout]

        # Check if at limit
        if len(active_requests) >= self.max_concurrent:
            cache.set(cache_key, active_requests, self.timeout)
            return False

        # Add this request
        active_requests.append(now)
        cache.set(cache_key, active_requests, self.timeout)
        return True

    def wait(self):
        # Can't calculate specific wait time for concurrent throttling
        return self.timeout


class ConcurrentLimitedView(APIView):
    """
    View with concurrent request limiting.
    """
    throttle_classes = [ConcurrentRequestThrottle]

    def get(self, request):
        import time
        time.sleep(2)  # Simulate slow operation
        return Response({'message': 'Processed'})


# ==============================================================================
# CUSTOM ALGORITHM: TOKEN BUCKET THROTTLE
# ==============================================================================

class TokenBucketThrottle(BaseThrottle):
    """
    Token bucket algorithm for smoother rate limiting.
    Allows bursts while maintaining average rate.

    Configuration:
        rate = 100  # Tokens per period
        period = 3600  # Period in seconds (1 hour)
        capacity = 150  # Max tokens (allows bursts above rate)
    """
    rate = 100
    period = 3600
    capacity = 150

    def allow_request(self, request, view):
        # Identify user
        if request.user.is_authenticated:
            ident = request.user.pk
        else:
            ident = self.get_ident(request)

        cache_key = f'token_bucket_{ident}'
        now = time.time()

        # Get bucket state
        bucket = cache.get(cache_key)
        if bucket is None:
            bucket = {
                'tokens': self.capacity,
                'last_update': now
            }

        # Calculate tokens to add based on time passed
        time_passed = now - bucket['last_update']
        tokens_to_add = time_passed * (self.rate / self.period)

        # Update bucket
        bucket['tokens'] = min(self.capacity, bucket['tokens'] + tokens_to_add)
        bucket['last_update'] = now

        # Check if request can be served
        if bucket['tokens'] >= 1:
            bucket['tokens'] -= 1
            cache.set(cache_key, bucket, self.period * 2)
            return True
        else:
            cache.set(cache_key, bucket, self.period * 2)
            self.bucket = bucket  # Save for wait() calculation
            return False

    def wait(self):
        """Calculate time until next token available."""
        if hasattr(self, 'bucket'):
            tokens_needed = 1 - self.bucket['tokens']
            time_per_token = self.period / self.rate
            return tokens_needed * time_per_token
        return None

    def get_ident(self, request):
        """Get client IP address."""
        xff = request.META.get('HTTP_X_FORWARDED_FOR')
        remote_addr = request.META.get('REMOTE_ADDR')
        return ''.join(xff.split()) if xff else remote_addr


class TokenBucketView(APIView):
    """
    View with token bucket throttling.
    """
    throttle_classes = [TokenBucketThrottle]

    def get(self, request):
        return Response({'message': 'Token bucket allows smooth bursts'})


# ==============================================================================
# CONDITIONAL THROTTLING
# ==============================================================================

class ConditionalRateThrottle(UserRateThrottle):
    """
    Only throttle under certain conditions (e.g., high system load).
    """
    scope = 'user'

    def allow_request(self, request, view):
        # Check system condition from cache (set by monitoring task)
        system_load = cache.get('system_load', 'normal')

        if system_load == 'high':
            # Apply throttling under high load
            return super().allow_request(request, view)
        else:
            # No throttling under normal conditions
            return True


class ConditionalView(APIView):
    """
    View that only throttles under high load.
    """
    throttle_classes = [ConditionalRateThrottle]

    def get(self, request):
        load = cache.get('system_load', 'normal')
        return Response({
            'message': 'Success',
            'system_load': load,
            'throttling_active': load == 'high'
        })


# ==============================================================================
# CUSTOM ERROR MESSAGES
# ==============================================================================

class CustomMessageThrottle(SimpleRateThrottle):
    """
    Throttle with custom error message.
    """
    scope = 'custom_message'

    def get_cache_key(self, request, view):
        if request.user.is_authenticated:
            ident = request.user.pk
        else:
            ident = self.get_ident(request)

        return self.cache_format % {
            'scope': self.scope,
            'ident': ident
        }

    def throttle_failure(self):
        """
        Override to provide custom error message.
        """
        wait = self.wait()

        # Raise with custom message
        raise Throttled(
            detail={
                'message': 'Rate limit exceeded. Please slow down!',
                'limit': f'{self.num_requests} requests per {self.duration} seconds',
                'retry_after_seconds': int(wait) if wait else None,
                'retry_after_minutes': int(wait / 60) if wait else None,
            },
            wait=wait
        )


class CustomMessageView(APIView):
    """
    View with custom throttle error messages.

    Settings:
        'DEFAULT_THROTTLE_RATES': {
            'custom_message': '10/min',
        }
    """
    throttle_classes = [CustomMessageThrottle]

    def get(self, request):
        return Response({'message': 'Success'})


# ==============================================================================
# MULTI-FACTOR THROTTLING
# ==============================================================================

class MultiFactorRateThrottle(SimpleRateThrottle):
    """
    Throttle based on combination of user, endpoint, and method.
    Each combination gets independent limit.
    """
    scope = 'multi_factor'

    def get_cache_key(self, request, view):
        # Build identifier from multiple factors
        factors = []

        # User or IP
        if request.user.is_authenticated:
            factors.append(f'user_{request.user.pk}')
        else:
            factors.append(f'ip_{self.get_ident(request)}')

        # Endpoint path
        factors.append(f'path_{request.path}')

        # HTTP method
        factors.append(f'method_{request.method}')

        # Create unique identifier hash
        combined = '|'.join(factors)
        ident = hashlib.md5(combined.encode()).hexdigest()

        return self.cache_format % {
            'scope': self.scope,
            'ident': ident
        }


class MultiFactorView(APIView):
    """
    View with multi-factor throttling.
    Each user+endpoint+method combination is throttled separately.

    Settings:
        'DEFAULT_THROTTLE_RATES': {
            'multi_factor': '100/hour',
        }
    """
    throttle_classes = [MultiFactorRateThrottle]

    def get(self, request):
        return Response({'message': 'GET request'})

    def post(self, request):
        return Response({'message': 'POST request'})


# ==============================================================================
# SETTINGS CONFIGURATION EXAMPLES
# ==============================================================================

"""
Complete settings.py configuration for all examples above:

# settings.py

CACHES = {
    'default': {
        'BACKEND': 'django.core.cache.backends.redis.RedisCache',
        'LOCATION': 'redis://127.0.0.1:6379/1',
        'OPTIONS': {
            'CLIENT_CLASS': 'django_redis.client.DefaultClient',
        },
    }
}

REST_FRAMEWORK = {
    'DEFAULT_THROTTLE_CLASSES': [
        'rest_framework.throttling.AnonRateThrottle',
        'rest_framework.throttling.UserRateThrottle',
    ],
    'DEFAULT_THROTTLE_RATES': {
        # Basic rates
        'anon': '100/day',
        'user': '1000/day',

        # Burst + sustained
        'burst': '60/min',
        'sustained': '10000/day',

        # Subscription tiers
        'tier_free': '100/day',
        'tier_basic': '1000/day',
        'tier_premium': '10000/day',
        'tier_enterprise': '100000/day',

        # API key throttling
        'api_key': '1000/hour',

        # Method-based
        'method_get': '1000/hour',
        'method_post': '100/hour',
        'method_put': '100/hour',
        'method_patch': '100/hour',
        'method_delete': '50/hour',

        # Time-based
        'peak_hours': '100/hour',
        'off_peak': '1000/hour',

        # Scoped
        'contacts': '1000/day',
        'uploads': '20/day',
        'messages': '100/hour',

        # ViewSet actions
        'document_upload': '10/hour',
        'document_modify': '50/hour',
        'document_read': '1000/hour',

        # Custom messages
        'custom_message': '10/min',

        # Multi-factor
        'multi_factor': '100/hour',
    },
    'NUM_PROXIES': 1,  # Adjust based on your proxy setup
}
"""


# ==============================================================================
# TESTING UTILITIES
# ==============================================================================

def clear_throttle_for_user(user_id, scope='user'):
    """
    Clear throttle cache for specific user.
    Useful for testing or admin overrides.
    """
    cache_key = f'throttle_{scope}_{user_id}'
    cache.delete(cache_key)


def get_throttle_status(user_id, scope='user'):
    """
    Get current throttle status for user.
    Returns list of request timestamps.
    """
    cache_key = f'throttle_{scope}_{user_id}'
    history = cache.get(cache_key, [])
    return {
        'cache_key': cache_key,
        'request_count': len(history),
        'timestamps': history,
    }


def clear_all_throttles():
    """
    Clear all throttle caches.
    WARNING: Use with caution!
    """
    cache.clear()


# ==============================================================================
# TEST CASES
# ==============================================================================

"""
Example test cases for throttling:

from django.test import TestCase
from django.contrib.auth.models import User
from rest_framework.test import APIClient
from django.core.cache import cache


class ThrottleTestCase(TestCase):
    def setUp(self):
        cache.clear()
        self.client = APIClient()
        self.user = User.objects.create_user('test', 'test@example.com', 'pass')

    def test_anonymous_throttle(self):
        '''Test that anonymous users are throttled.'''
        # Make requests up to limit
        for i in range(100):  # Assuming 100/day limit
            response = self.client.get('/api/endpoint/')
            self.assertEqual(response.status_code, 200)

        # Next request should be throttled
        response = self.client.get('/api/endpoint/')
        self.assertEqual(response.status_code, 429)
        self.assertIn('Retry-After', response)

    def test_authenticated_higher_limit(self):
        '''Test that authenticated users have higher limit.'''
        self.client.force_authenticate(user=self.user)

        # Should allow more than anonymous limit
        for i in range(150):
            response = self.client.get('/api/endpoint/')
            self.assertEqual(response.status_code, 200)

    def test_burst_throttle(self):
        '''Test burst throttle prevents rapid requests.'''
        self.client.force_authenticate(user=self.user)

        # Rapid requests
        for i in range(60):  # Assuming 60/min burst limit
            response = self.client.get('/api/burst-protected/')
            self.assertEqual(response.status_code, 200)

        # 61st request in same minute should be throttled
        response = self.client.get('/api/burst-protected/')
        self.assertEqual(response.status_code, 429)

    def test_scope_independence(self):
        '''Test that different scopes have independent limits.'''
        self.client.force_authenticate(user=self.user)

        # Exhaust contacts scope
        for i in range(100):
            self.client.get('/api/contacts/')

        # Contacts should be throttled
        response = self.client.get('/api/contacts/')
        self.assertEqual(response.status_code, 429)

        # But uploads scope should still work
        response = self.client.post('/api/uploads/')
        self.assertEqual(response.status_code, 200)

    def test_custom_error_message(self):
        '''Test custom throttle error message.'''
        self.client.force_authenticate(user=self.user)

        # Exhaust limit
        for i in range(10):  # Assuming 10/min limit
            self.client.get('/api/custom-message/')

        # Check custom error message
        response = self.client.get('/api/custom-message/')
        self.assertEqual(response.status_code, 429)
        self.assertIn('message', response.data)
        self.assertIn('limit', response.data)
        self.assertIn('retry_after_seconds', response.data)
"""
