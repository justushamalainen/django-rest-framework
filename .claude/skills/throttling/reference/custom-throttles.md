# Custom Throttle Classes

Creating custom throttling logic for specialized rate limiting requirements.

## Creating a Custom Throttle

Two approaches depending on complexity:

1. **Extend SimpleRateThrottle** - For standard rate-based throttling with custom identity logic
2. **Extend BaseThrottle** - For completely custom throttling algorithms

## Approach 1: Extending SimpleRateThrottle

Most common approach. Override `get_cache_key()` to customize who/what gets throttled.

### Basic Template

```python
from rest_framework.throttling import SimpleRateThrottle

class MyCustomThrottle(SimpleRateThrottle):
    scope = 'my_custom_scope'  # Must match key in DEFAULT_THROTTLE_RATES

    def get_cache_key(self, request, view):
        """
        Return unique cache key for this request.
        Return None to skip throttling.
        """
        # Your custom logic here
        ident = self.get_custom_identifier(request, view)

        if ident is None:
            return None  # Skip throttling

        return self.cache_format % {
            'scope': self.scope,
            'ident': ident
        }

    def get_custom_identifier(self, request, view):
        """Custom logic to identify who/what to throttle."""
        # Examples: user role, API key, request path, etc.
        pass
```

### Configuration

```python
# settings.py
REST_FRAMEWORK = {
    'DEFAULT_THROTTLE_RATES': {
        'my_custom_scope': '100/hour',
    }
}
```

## Common Custom Throttle Patterns

### 1. Subscription Tier Throttling

Different rate limits based on user subscription level:

```python
from rest_framework.throttling import SimpleRateThrottle

class SubscriptionRateThrottle(SimpleRateThrottle):
    def get_cache_key(self, request, view):
        if not request.user.is_authenticated:
            return None  # Don't throttle anonymous

        # Determine subscription tier
        tier = getattr(request.user, 'subscription_tier', 'free')
        self.scope = f'tier_{tier}'

        # Check if rate is configured for this tier
        if self.scope not in self.THROTTLE_RATES:
            self.scope = 'tier_free'  # Fallback

        # Update rate dynamically
        self.rate = self.get_rate()
        self.num_requests, self.duration = self.parse_rate(self.rate)

        return self.cache_format % {
            'scope': self.scope,
            'ident': request.user.pk
        }

# settings.py
'DEFAULT_THROTTLE_RATES': {
    'tier_free': '100/day',
    'tier_basic': '1000/day',
    'tier_premium': '10000/day',
    'tier_enterprise': '100000/day',
}
```

### 2. API Key Throttling

Throttle by API key instead of user:

```python
from rest_framework.throttling import SimpleRateThrottle

class APIKeyRateThrottle(SimpleRateThrottle):
    scope = 'api_key'

    def get_cache_key(self, request, view):
        # Get API key from header
        api_key = request.META.get('HTTP_X_API_KEY')

        if not api_key:
            return None  # No API key = no throttling (or use IP)

        return self.cache_format % {
            'scope': self.scope,
            'ident': api_key
        }

# settings.py
'DEFAULT_THROTTLE_RATES': {
    'api_key': '1000/hour',
}
```

### 3. Method-Based Throttling

Different limits for different HTTP methods:

```python
from rest_framework.throttling import SimpleRateThrottle

class MethodRateThrottle(SimpleRateThrottle):
    def get_cache_key(self, request, view):
        if not request.user.is_authenticated:
            ident = self.get_ident(request)
        else:
            ident = request.user.pk

        # Different scope per method
        method = request.method.lower()
        self.scope = f'method_{method}'

        # Update rate for this method
        if self.scope not in self.THROTTLE_RATES:
            return None  # No rate configured for this method

        self.rate = self.get_rate()
        self.num_requests, self.duration = self.parse_rate(self.rate)

        return self.cache_format % {
            'scope': self.scope,
            'ident': ident
        }

# settings.py
'DEFAULT_THROTTLE_RATES': {
    'method_get': '1000/hour',
    'method_post': '100/hour',
    'method_put': '100/hour',
    'method_patch': '100/hour',
    'method_delete': '50/hour',
}
```

### 4. Time-Based Throttling

Different limits during peak hours:

```python
from rest_framework.throttling import SimpleRateThrottle
from datetime import datetime

class TimeBasisRateThrottle(SimpleRateThrottle):
    def get_cache_key(self, request, view):
        if not request.user.is_authenticated:
            ident = self.get_ident(request)
        else:
            ident = request.user.pk

        # Determine if peak hours (e.g., 9am-5pm)
        hour = datetime.now().hour
        if 9 <= hour < 17:
            self.scope = 'peak_hours'
        else:
            self.scope = 'off_peak'

        self.rate = self.get_rate()
        self.num_requests, self.duration = self.parse_rate(self.rate)

        return self.cache_format % {
            'scope': self.scope,
            'ident': ident
        }

# settings.py
'DEFAULT_THROTTLE_RATES': {
    'peak_hours': '100/hour',    # Stricter during peak
    'off_peak': '1000/hour',     # Relaxed during off-peak
}
```

### 5. Endpoint-Specific Throttling

Throttle based on URL path:

```python
from rest_framework.throttling import SimpleRateThrottle

class EndpointRateThrottle(SimpleRateThrottle):
    def get_cache_key(self, request, view):
        if not request.user.is_authenticated:
            ident = self.get_ident(request)
        else:
            ident = request.user.pk

        # Use view name or path as part of scope
        view_name = getattr(view, 'suffix', None) or view.__class__.__name__
        self.scope = f'endpoint_{view_name.lower()}'

        if self.scope not in self.THROTTLE_RATES:
            self.scope = 'default'  # Fallback

        self.rate = self.get_rate()
        self.num_requests, self.duration = self.parse_rate(self.rate)

        return self.cache_format % {
            'scope': self.scope,
            'ident': ident
        }

# settings.py
'DEFAULT_THROTTLE_RATES': {
    'default': '1000/hour',
    'endpoint_upload': '10/hour',
    'endpoint_export': '5/hour',
}
```

### 6. Role-Based Throttling

Different limits for different user roles:

```python
from rest_framework.throttling import SimpleRateThrottle

class RoleBasedRateThrottle(SimpleRateThrottle):
    def get_cache_key(self, request, view):
        if not request.user.is_authenticated:
            self.scope = 'anonymous'
            ident = self.get_ident(request)
        else:
            # Get user role
            if request.user.is_staff:
                self.scope = 'role_staff'
            elif hasattr(request.user, 'is_premium') and request.user.is_premium:
                self.scope = 'role_premium'
            else:
                self.scope = 'role_regular'

            ident = request.user.pk

        self.rate = self.get_rate()
        self.num_requests, self.duration = self.parse_rate(self.rate)

        return self.cache_format % {
            'scope': self.scope,
            'ident': ident
        }

# settings.py
'DEFAULT_THROTTLE_RATES': {
    'anonymous': '100/day',
    'role_regular': '1000/day',
    'role_premium': '10000/day',
    'role_staff': '100000/day',
}
```

### 7. Combined Identifier Throttling

Throttle by combination of factors:

```python
from rest_framework.throttling import SimpleRateThrottle
import hashlib

class CombinedRateThrottle(SimpleRateThrottle):
    scope = 'combined'

    def get_cache_key(self, request, view):
        # Combine multiple factors into identifier
        factors = []

        # User or IP
        if request.user.is_authenticated:
            factors.append(f"user:{request.user.pk}")
        else:
            factors.append(f"ip:{self.get_ident(request)}")

        # Add endpoint
        factors.append(f"endpoint:{request.path}")

        # Add method
        factors.append(f"method:{request.method}")

        # Create hash of combined factors
        combined = "|".join(factors)
        ident = hashlib.md5(combined.encode()).hexdigest()

        return self.cache_format % {
            'scope': self.scope,
            'ident': ident
        }

# settings.py
'DEFAULT_THROTTLE_RATES': {
    'combined': '100/hour',
}
```

## Approach 2: Extending BaseThrottle

For completely custom throttling algorithms that don't follow the rate-based pattern.

### Template

```python
from rest_framework.throttling import BaseThrottle
from django.core.cache import cache

class CustomAlgorithmThrottle(BaseThrottle):
    def allow_request(self, request, view):
        """
        Return True to allow, False to throttle.
        Implement your custom algorithm here.
        """
        # Your custom throttling logic
        return True  # or False

    def wait(self):
        """
        Return seconds to wait, or None.
        """
        return None
```

### Example: Concurrent Request Throttle

Limit number of concurrent requests per user:

```python
from rest_framework.throttling import BaseThrottle
from django.core.cache import cache
import time

class ConcurrentRequestThrottle(BaseThrottle):
    """
    Throttle based on number of concurrent requests, not rate.
    """
    max_concurrent = 5  # Max 5 concurrent requests per user
    timeout = 60  # Request assumed finished after 60 seconds

    def allow_request(self, request, view):
        if not request.user.is_authenticated:
            return True  # Don't throttle anonymous

        cache_key = f'concurrent_{request.user.pk}'

        # Get current request timestamps
        requests = cache.get(cache_key, [])
        now = time.time()

        # Remove finished requests (older than timeout)
        requests = [ts for ts in requests if now - ts < self.timeout]

        # Check if at limit
        if len(requests) >= self.max_concurrent:
            cache.set(cache_key, requests, self.timeout)
            return False

        # Add this request
        requests.append(now)
        cache.set(cache_key, requests, self.timeout)
        return True

    def wait(self):
        # Can't calculate wait time for concurrent throttling
        return None
```

### Example: Token Bucket Throttle

More lenient burst handling with token bucket algorithm:

```python
from rest_framework.throttling import BaseThrottle
from django.core.cache import cache
import time

class TokenBucketThrottle(BaseThrottle):
    """
    Token bucket algorithm for smoother rate limiting.
    Allows bursts while maintaining average rate.
    """
    rate = 100  # Tokens per period
    period = 3600  # Period in seconds (1 hour)
    capacity = 150  # Max tokens in bucket (allows bursts)

    def allow_request(self, request, view):
        if not request.user.is_authenticated:
            ident = self.get_ident(request)
        else:
            ident = request.user.pk

        cache_key = f'token_bucket_{ident}'
        now = time.time()

        # Get bucket state
        bucket = cache.get(cache_key)
        if bucket is None:
            bucket = {'tokens': self.capacity, 'last_update': now}

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
            self.bucket = bucket  # Store for wait() calculation
            return False

    def wait(self):
        if hasattr(self, 'bucket'):
            # Calculate time to get next token
            tokens_needed = 1 - self.bucket['tokens']
            time_per_token = self.period / self.rate
            return tokens_needed * time_per_token
        return None

    def get_ident(self, request):
        xff = request.META.get('HTTP_X_FORWARDED_FOR')
        remote_addr = request.META.get('REMOTE_ADDR')
        return ''.join(xff.split()) if xff else remote_addr
```

### Example: Conditional Throttle

Throttle only under certain conditions:

```python
from rest_framework.throttling import UserRateThrottle
from django.core.cache import cache

class ConditionalRateThrottle(UserRateThrottle):
    """
    Only throttle when system is under high load.
    """
    def allow_request(self, request, view):
        # Check system load from cache (set by monitoring task)
        system_load = cache.get('system_load', 'normal')

        if system_load == 'high':
            # Apply throttling under high load
            return super().allow_request(request, view)
        else:
            # No throttling under normal load
            return True
```

## Dynamic Rate Configuration

Override `get_rate()` to calculate rates dynamically:

```python
from rest_framework.throttling import SimpleRateThrottle

class DynamicRateThrottle(SimpleRateThrottle):
    scope = 'dynamic'

    def get_rate(self):
        """
        Calculate rate dynamically based on user properties.
        """
        if not hasattr(self, 'request'):
            return super().get_rate()

        request = self.request

        if not request.user.is_authenticated:
            return '100/hour'

        # Calculate based on user's subscription
        if hasattr(request.user, 'subscription'):
            subscription = request.user.subscription
            if subscription.tier == 'premium':
                return '10000/day'
            elif subscription.tier == 'basic':
                return '1000/day'

        return '100/day'  # Default

    def allow_request(self, request, view):
        # Store request for get_rate() to access
        self.request = request
        return super().allow_request(request, view)
```

## Custom Cache Keys

Customize cache key format for special cases:

```python
from rest_framework.throttling import SimpleRateThrottle

class CustomCacheKeyThrottle(SimpleRateThrottle):
    scope = 'custom'

    def get_cache_key(self, request, view):
        if not request.user.is_authenticated:
            return None

        # Custom cache key format
        # Include organization ID for multi-tenant throttling
        org_id = getattr(request.user, 'organization_id', 'default')

        return f'throttle:{self.scope}:org:{org_id}:user:{request.user.pk}'
```

## Custom Error Messages

Override throttle failure to provide custom messages:

```python
from rest_framework.throttling import SimpleRateThrottle
from rest_framework.exceptions import Throttled

class CustomMessageThrottle(SimpleRateThrottle):
    scope = 'custom'

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
        # Calculate wait time
        wait = self.wait()

        # Raise custom exception
        raise Throttled(
            detail=f'Rate limit exceeded. You are limited to {self.num_requests} '
                   f'requests per {self.duration} seconds. '
                   f'Please try again in {int(wait)} seconds.',
            wait=wait
        )
```

## Testing Custom Throttles

```python
from django.test import TestCase
from django.contrib.auth.models import User
from django.core.cache import cache
from rest_framework.test import APIRequestFactory
from rest_framework.views import APIView
from myapp.throttles import SubscriptionRateThrottle

class SubscriptionThrottleTestCase(TestCase):
    def setUp(self):
        cache.clear()
        self.factory = APIRequestFactory()
        self.view = APIView.as_view()
        self.throttle = SubscriptionRateThrottle()

    def test_free_tier_throttle(self):
        """Test that free tier gets correct rate limit."""
        user = User.objects.create_user('free_user', 'free@example.com', 'pass')
        user.subscription_tier = 'free'
        user.save()

        request = self.factory.get('/api/test/')
        request.user = user

        # Should allow up to free tier limit
        for i in range(100):  # Assuming free tier is 100/day
            allowed = self.throttle.allow_request(request, self.view)
            if i < 100:
                self.assertTrue(allowed)
            else:
                self.assertFalse(allowed)

    def test_premium_tier_higher_limit(self):
        """Test that premium tier gets higher limit."""
        user = User.objects.create_user('premium_user', 'premium@example.com', 'pass')
        user.subscription_tier = 'premium'
        user.save()

        request = self.factory.get('/api/test/')
        request.user = user

        # Should allow more than free tier
        for i in range(150):
            allowed = self.throttle.allow_request(request, self.view)
            self.assertTrue(allowed)  # Premium allows more

    def test_different_users_independent_limits(self):
        """Test that different users have independent throttle limits."""
        user1 = User.objects.create_user('user1', 'user1@example.com', 'pass')
        user2 = User.objects.create_user('user2', 'user2@example.com', 'pass')

        request1 = self.factory.get('/api/test/')
        request1.user = user1

        request2 = self.factory.get('/api/test/')
        request2.user = user2

        # Exhaust user1's limit
        for i in range(100):
            self.throttle.allow_request(request1, self.view)

        # user1 should be throttled
        self.assertFalse(self.throttle.allow_request(request1, self.view))

        # user2 should still be allowed
        self.assertTrue(self.throttle.allow_request(request2, self.view))
```

## Best Practices

### 1. Always Return Cache Key or None

```python
def get_cache_key(self, request, view):
    # GOOD: Always return string or None
    if should_skip_throttling:
        return None
    return f'throttle:{scope}:{ident}'

    # BAD: Never return empty string or other falsy values
    # return ''  # Wrong!
```

### 2. Validate Configuration

```python
def __init__(self):
    super().__init__()

    # Validate required settings
    if self.scope not in self.THROTTLE_RATES:
        from django.core.exceptions import ImproperlyConfigured
        raise ImproperlyConfigured(
            f"Throttle rate not configured for scope '{self.scope}'"
        )
```

### 3. Handle Anonymous Users

```python
def get_cache_key(self, request, view):
    # Always check authentication
    if request.user and request.user.is_authenticated:
        ident = request.user.pk
    else:
        ident = self.get_ident(request)  # Use IP
```

### 4. Use Appropriate Cache Timeout

```python
def allow_request(self, request, view):
    # ...
    # Set cache timeout longer than rate period to handle clock skew
    cache_timeout = self.duration * 2
    self.cache.set(self.key, self.history, cache_timeout)
```

### 5. Document Scope Requirements

```python
class MyThrottle(SimpleRateThrottle):
    """
    Custom throttle for subscription-based rate limiting.

    Required settings:
        DEFAULT_THROTTLE_RATES = {
            'tier_free': '100/day',
            'tier_basic': '1000/day',
            'tier_premium': '10000/day',
        }

    Required user model attributes:
        - subscription_tier: str ('free', 'basic', or 'premium')
    """
    pass
```
