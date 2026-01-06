# Built-in Throttle Classes

DRF provides several built-in throttle classes for common rate limiting scenarios.

## BaseThrottle

The abstract base class for all throttles.

```python
from rest_framework.throttling import BaseThrottle

class BaseThrottle:
    def allow_request(self, request, view):
        """
        Return `True` if the request should be allowed, `False` otherwise.
        Must be overridden.
        """
        raise NotImplementedError('.allow_request() must be overridden')

    def get_ident(self, request):
        """
        Identify the machine making the request.
        Returns IP address from HTTP_X_FORWARDED_FOR or REMOTE_ADDR.
        """
        # Handles proxy forwarding based on NUM_PROXIES setting

    def wait(self):
        """
        Return recommended seconds to wait before next request.
        Used for Retry-After header. Returns None if not applicable.
        """
        return None
```

### Key Methods

**`allow_request(request, view)`** - REQUIRED
- Called before view processing
- Return `True` to allow, `False` to throttle (429 response)
- Has access to request and view objects

**`get_ident(request)`** - Helper for IP identification
- Respects `X-Forwarded-For` header
- Handles proxy chains via `NUM_PROXIES` setting
- Returns client IP address as string

**`wait()`** - Optional
- Calculate seconds until user can retry
- Used for `Retry-After` response header
- Return `None` if calculation not possible

## SimpleRateThrottle

Base class for rate-based throttles. Implements sliding window algorithm with cache storage.

```python
from rest_framework.throttling import SimpleRateThrottle

class SimpleRateThrottle(BaseThrottle):
    cache = default_cache  # Django cache instance
    timer = time.time      # Time function (can override for testing)
    cache_format = 'throttle_%(scope)s_%(ident)s'
    scope = None           # Must be set in subclass
    THROTTLE_RATES = api_settings.DEFAULT_THROTTLE_RATES

    def get_cache_key(self, request, view):
        """
        Return unique cache key for throttling.
        Return None to skip throttling for this request.
        Must be overridden.
        """
        raise NotImplementedError('.get_cache_key() must be overridden')

    def get_rate(self):
        """Get rate string from settings based on scope."""
        return self.THROTTLE_RATES[self.scope]

    def parse_rate(self, rate):
        """
        Parse rate string like '100/hour' into (100, 3600).
        Returns (num_requests, duration_in_seconds).
        """
        pass

    def allow_request(self, request, view):
        """
        Implement sliding window check:
        1. Get cache key
        2. Retrieve request history from cache
        3. Remove old timestamps outside window
        4. Check if under limit
        5. Update cache with new timestamp if allowed
        """
        pass

    def wait(self):
        """Calculate seconds until next available slot."""
        pass
```

### How SimpleRateThrottle Works

1. **Initialization**
   ```python
   def __init__(self):
       self.rate = self.get_rate()  # e.g., "100/hour"
       self.num_requests, self.duration = self.parse_rate(self.rate)
       # num_requests = 100, duration = 3600
   ```

2. **Request Check**
   ```python
   def allow_request(self, request, view):
       self.key = self.get_cache_key(request, view)
       if self.key is None:
           return True  # Skip throttling

       self.history = self.cache.get(self.key, [])
       self.now = self.timer()

       # Remove old timestamps
       while self.history and self.history[-1] <= self.now - self.duration:
           self.history.pop()

       # Check limit
       if len(self.history) >= self.num_requests:
           return False  # Throttled!

       # Add timestamp and save
       self.history.insert(0, self.now)
       self.cache.set(self.key, self.history, self.duration)
       return True
   ```

3. **Wait Calculation**
   ```python
   def wait(self):
       if self.history:
           # Time until oldest request expires
           remaining_duration = self.duration - (self.now - self.history[-1])
       else:
           remaining_duration = self.duration

       # Distribute wait across available slots
       available_requests = self.num_requests - len(self.history) + 1
       return remaining_duration / float(available_requests)
   ```

### Configuration

Set rates in Django settings:

```python
REST_FRAMEWORK = {
    'DEFAULT_THROTTLE_RATES': {
        'anon': '100/day',
        'user': '1000/day',
        'burst': '60/min',
        'custom_scope': '500/hour',
    }
}
```

### Custom Cache Backend

Use a specific cache for throttling:

```python
from django.core.cache import caches

class CustomRateThrottle(SimpleRateThrottle):
    cache = caches['throttle_cache']  # Use dedicated cache
```

## AnonRateThrottle

Throttles anonymous (unauthenticated) users by IP address. Does NOT throttle authenticated users.

```python
from rest_framework.throttling import AnonRateThrottle

class AnonRateThrottle(SimpleRateThrottle):
    scope = 'anon'

    def get_cache_key(self, request, view):
        if request.user and request.user.is_authenticated:
            return None  # Skip throttling for authenticated users

        return self.cache_format % {
            'scope': self.scope,
            'ident': self.get_ident(request)
        }
```

### Usage

```python
# settings.py
REST_FRAMEWORK = {
    'DEFAULT_THROTTLE_CLASSES': [
        'rest_framework.throttling.AnonRateThrottle',
    ],
    'DEFAULT_THROTTLE_RATES': {
        'anon': '100/day',
    }
}
```

Or per-view:

```python
from rest_framework.throttling import AnonRateThrottle
from rest_framework.views import APIView

class PublicAPIView(APIView):
    throttle_classes = [AnonRateThrottle]
```

### How It Works

- **Authenticated users**: `get_cache_key()` returns `None` → not throttled
- **Anonymous users**: Uses IP address as identifier
- **Cache key**: `throttle_anon_192.168.1.100`
- **Rate**: Configured with `'anon'` key in `DEFAULT_THROTTLE_RATES`

### Use Cases

- Public API endpoints that allow anonymous access
- Preventing anonymous abuse while allowing authenticated heavy usage
- Registration/signup endpoints
- Password reset endpoints

## UserRateThrottle

Throttles based on user ID (authenticated) or IP address (anonymous).

```python
from rest_framework.throttling import UserRateThrottle

class UserRateThrottle(SimpleRateThrottle):
    scope = 'user'

    def get_cache_key(self, request, view):
        if request.user and request.user.is_authenticated:
            ident = request.user.pk
        else:
            ident = self.get_ident(request)

        return self.cache_format % {
            'scope': self.scope,
            'ident': ident
        }
```

### Usage

```python
# settings.py
REST_FRAMEWORK = {
    'DEFAULT_THROTTLE_CLASSES': [
        'rest_framework.throttling.UserRateThrottle',
    ],
    'DEFAULT_THROTTLE_RATES': {
        'user': '1000/day',
    }
}
```

### How It Works

- **Authenticated users**: Uses `request.user.pk` as identifier
- **Anonymous users**: Uses IP address as identifier
- **Cache keys**:
  - Authenticated: `throttle_user_42`
  - Anonymous: `throttle_user_192.168.1.100`
- **Rate**: Configured with `'user'` key

### Use Cases

- General API protection
- Same rate limit for both authenticated and anonymous users
- Simple single-tier throttling

### Combining with AnonRateThrottle

Common pattern for different rates:

```python
REST_FRAMEWORK = {
    'DEFAULT_THROTTLE_CLASSES': [
        'rest_framework.throttling.AnonRateThrottle',
        'rest_framework.throttling.UserRateThrottle',
    ],
    'DEFAULT_THROTTLE_RATES': {
        'anon': '100/day',   # Anonymous: 100/day
        'user': '1000/day',  # Authenticated: 1000/day
    }
}
```

**How it works together:**
- Anonymous user: Only `AnonRateThrottle` applies (100/day limit)
- Authenticated user: Only `UserRateThrottle` applies (1000/day limit)
- `AnonRateThrottle` returns `None` for authenticated, so they skip that check

## ScopedRateThrottle

Different rate limits for different API endpoints or view actions. Each scope is tracked independently.

```python
from rest_framework.throttling import ScopedRateThrottle

class ScopedRateThrottle(SimpleRateThrottle):
    scope_attr = 'throttle_scope'

    def __init__(self):
        # Don't call super().__init__() - wait for view context
        pass

    def allow_request(self, request, view):
        # Get scope from view attribute
        self.scope = getattr(view, self.scope_attr, None)

        if not self.scope:
            return True  # No scope = no throttling

        # Now initialize rate
        self.rate = self.get_rate()
        self.num_requests, self.duration = self.parse_rate(self.rate)

        return super().allow_request(request, view)

    def get_cache_key(self, request, view):
        if request.user and request.user.is_authenticated:
            ident = request.user.pk
        else:
            ident = self.get_ident(request)

        return self.cache_format % {
            'scope': self.scope,
            'ident': ident
        }
```

### Usage

Set `throttle_scope` attribute on views:

```python
from rest_framework.throttling import ScopedRateThrottle
from rest_framework.views import APIView

class ContactsView(APIView):
    throttle_classes = [ScopedRateThrottle]
    throttle_scope = 'contacts'

class UploadsView(APIView):
    throttle_classes = [ScopedRateThrottle]
    throttle_scope = 'uploads'

class MessagesView(APIView):
    throttle_classes = [ScopedRateThrottle]
    throttle_scope = 'messages'

# settings.py
REST_FRAMEWORK = {
    'DEFAULT_THROTTLE_RATES': {
        'contacts': '1000/day',
        'uploads': '20/day',
        'messages': '100/hour',
    }
}
```

### How It Works

- **Scope determination**: Read from `view.throttle_scope` attribute
- **Independent tracking**: Each scope has separate rate limit and cache key
- **Cache keys**:
  - `throttle_contacts_42` (user 42 in contacts scope)
  - `throttle_uploads_42` (user 42 in uploads scope)
  - `throttle_messages_192.168.1.100` (anonymous in messages scope)
- **No scope**: If view has no `throttle_scope`, throttle is skipped

### Use Cases

- Different endpoints with different sensitivity (uploads vs reads)
- Different rate limits per resource type
- Per-action throttling in ViewSets

### ViewSet Per-Action Throttling

```python
from rest_framework.viewsets import ModelViewSet
from rest_framework.throttling import ScopedRateThrottle

class DocumentViewSet(ModelViewSet):
    throttle_classes = [ScopedRateThrottle]

    def get_throttle_scope(self):
        """Determine scope based on action."""
        if self.action == 'create':
            return 'document_create'
        elif self.action in ['update', 'partial_update', 'destroy']:
            return 'document_modify'
        else:  # list, retrieve
            return 'document_read'

    @property
    def throttle_scope(self):
        return self.get_throttle_scope()

# settings.py
'DEFAULT_THROTTLE_RATES': {
    'document_read': '1000/hour',
    'document_create': '100/hour',
    'document_modify': '200/hour',
}
```

## Comparison Table

| Throttle Class | Who It Throttles | Identifier | Scope | Use Case |
|---------------|------------------|------------|-------|----------|
| **AnonRateThrottle** | Anonymous only | IP address | `'anon'` | Public endpoints, protect against anonymous abuse |
| **UserRateThrottle** | Everyone | User ID or IP | `'user'` | General API protection, same rate for all |
| **ScopedRateThrottle** | Everyone | User ID or IP | Per-view | Different rates for different endpoints |

## Cache Key Examples

Given:
- Authenticated user with `pk=42`
- Anonymous user from IP `192.168.1.100`
- View with `throttle_scope = 'uploads'`

Cache keys generated:

| Throttle | User Type | Cache Key |
|----------|-----------|-----------|
| AnonRateThrottle | Authenticated | `None` (skipped) |
| AnonRateThrottle | Anonymous | `throttle_anon_192.168.1.100` |
| UserRateThrottle | Authenticated | `throttle_user_42` |
| UserRateThrottle | Anonymous | `throttle_user_192.168.1.100` |
| ScopedRateThrottle | Authenticated | `throttle_uploads_42` |
| ScopedRateThrottle | Anonymous | `throttle_uploads_192.168.1.100` |

## Testing Throttles

```python
from rest_framework.test import APITestCase
from rest_framework.throttling import UserRateThrottle
from django.contrib.auth.models import User
from django.core.cache import cache

class ThrottleTests(APITestCase):
    def setUp(self):
        cache.clear()
        self.user = User.objects.create_user('test', 'test@example.com', 'pass')

    def test_user_throttle_rate(self):
        """Test that throttle enforces rate limit."""
        self.client.force_authenticate(user=self.user)

        # Make requests up to limit
        for i in range(10):  # Assuming rate is 10/day
            response = self.client.get('/api/endpoint/')
            self.assertEqual(response.status_code, 200)

        # Next request should be throttled
        response = self.client.get('/api/endpoint/')
        self.assertEqual(response.status_code, 429)
        self.assertIn('Retry-After', response)

    def test_anon_throttle_separate_from_user(self):
        """Test that anonymous and authenticated users have separate limits."""
        # Anonymous request
        response = self.client.get('/api/endpoint/')
        self.assertEqual(response.status_code, 200)

        # Authenticated request (different throttle)
        self.client.force_authenticate(user=self.user)
        response = self.client.get('/api/endpoint/')
        self.assertEqual(response.status_code, 200)
```

## NUM_PROXIES Configuration

When behind proxies, configure correct IP detection:

```python
# settings.py
REST_FRAMEWORK = {
    'NUM_PROXIES': 1,  # Number of proxies between client and server
}

# How it works:
# X-Forwarded-For: client, proxy1, proxy2
# NUM_PROXIES = 0 → Use REMOTE_ADDR
# NUM_PROXIES = 1 → Use proxy2 (rightmost)
# NUM_PROXIES = 2 → Use proxy1 (second from right)
# NUM_PROXIES = None → Use all of X-Forwarded-For (default)
```

This ensures correct client identification for anonymous throttling.
