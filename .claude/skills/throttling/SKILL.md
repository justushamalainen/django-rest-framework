---
description: Rate limiting and throttling in Django REST Framework. Use when implementing API rate limits, protecting against abuse, managing burst requests, creating custom throttle classes, or configuring different rate limits for authenticated vs anonymous users. Covers built-in throttles (AnonRateThrottle, UserRateThrottle, ScopedRateThrottle), custom throttles, cache configuration, and per-view throttling.
---

# DRF Throttling

Implementing rate limiting and request throttling to protect your API from abuse and ensure fair resource usage.

## What You'll Learn

- **Built-in Throttle Classes** - AnonRateThrottle, UserRateThrottle, ScopedRateThrottle and when to use each
- **Rate Formats** - Understanding rate strings like "100/hour", "1000/day", and supported time periods
- **Custom Throttle Classes** - Creating specialized throttling logic with custom cache keys and rate calculation
- **Cache Configuration** - Setting up Django cache backends for throttle state storage
- **Per-View Throttling** - Applying different rate limits to specific views and actions
- **Burst Protection** - Managing sudden traffic spikes with appropriate rate windows
- **Throttle Responses** - Customizing 429 Too Many Requests responses with Retry-After headers
- **Anti-patterns** - Common mistakes that lead to ineffective throttling or cache issues

## Quick Start

### Basic User Rate Limiting

Limit authenticated users to 1000 requests/day, anonymous users to 100 requests/day:

```python
# settings.py
REST_FRAMEWORK = {
    'DEFAULT_THROTTLE_CLASSES': [
        'rest_framework.throttling.AnonRateThrottle',
        'rest_framework.throttling.UserRateThrottle'
    ],
    'DEFAULT_THROTTLE_RATES': {
        'anon': '100/day',
        'user': '1000/day'
    }
}

# Configure cache backend (required for throttling)
CACHES = {
    'default': {
        'BACKEND': 'django.core.cache.backends.locmem.LocMemCache',
        'LOCATION': 'unique-snowflake',
    }
}
```

**Effect:**
- Anonymous users (identified by IP): 100 requests per day
- Authenticated users (identified by user ID): 1000 requests per day
- Automatic 429 response with Retry-After header when limit exceeded

### Per-View Throttling

Apply specific rate limits to individual views:

```python
from rest_framework.throttling import UserRateThrottle
from rest_framework.viewsets import ModelViewSet

class BurstRateThrottle(UserRateThrottle):
    scope = 'burst'

class SustainedRateThrottle(UserRateThrottle):
    scope = 'sustained'

class UploadViewSet(ModelViewSet):
    throttle_classes = [BurstRateThrottle, SustainedRateThrottle]

    # settings.py:
    # 'DEFAULT_THROTTLE_RATES': {
    #     'burst': '60/min',
    #     'sustained': '1000/day'
    # }
```

**Effect:** Both throttles must pass. User can burst up to 60 requests/min but still limited to 1000/day total.

### Scoped Throttling for Different Endpoints

Different rate limits for different API sections:

```python
from rest_framework.throttling import ScopedRateThrottle

class ContactRateThrottle(ScopedRateThrottle):
    pass

class ContactView(APIView):
    throttle_classes = [ContactRateThrottle]
    throttle_scope = 'contacts'

class UploadView(APIView):
    throttle_classes = [ContactRateThrottle]
    throttle_scope = 'uploads'

# settings.py
REST_FRAMEWORK = {
    'DEFAULT_THROTTLE_RATES': {
        'contacts': '1000/day',
        'uploads': '20/day'
    }
}
```

**Effect:** Each scope has independent rate limits tracked separately.

## Throttle Decision Tree

### Choose Your Throttling Strategy

```
START: What type of rate limiting do you need?

├─ Different limits for anonymous vs authenticated users?
│  ├─ Anonymous only → AnonRateThrottle (doesn't throttle authenticated)
│  ├─ Authenticated only → UserRateThrottle (uses IP for anonymous)
│  └─ Both separately → Use both AnonRateThrottle + UserRateThrottle
│
├─ Different limits for different API endpoints?
│  └─ ScopedRateThrottle (set throttle_scope on each view)
│
├─ Multiple rate limits (burst + sustained)?
│  └─ Multiple throttle classes with different scopes
│     Example: BurstThrottle (60/min) + SustainedThrottle (1000/day)
│
├─ Custom throttling logic?
│  ├─ Based on user properties (subscription tier, role) → Custom throttle
│  ├─ Based on request properties (endpoint, method) → Custom throttle
│  ├─ Based on external factors (time of day, load) → Custom throttle
│  └─ Different rate calculation → Override parse_rate()
│
└─ No rate limiting?
   └─ Omit throttle_classes or set to empty list []
```

## How Throttling Works

### Execution Flow

1. **Throttle Check** - Before view processing
   - Called for EVERY request before permission checks
   - Multiple throttle classes all must pass (ALL must return True)
   - If ANY throttle fails, immediate 429 response

2. **Rate Calculation** - Per throttle class
   - Parse rate string (e.g., "100/day" → 100 requests per 86400 seconds)
   - Generate unique cache key based on identity (IP, user ID, scope)
   - Retrieve request history from cache

3. **History Management** - Sliding window algorithm
   - Store timestamps of recent requests in cache
   - Expire old timestamps outside the rate window
   - Count remaining requests in current window
   - Allow or deny based on count vs limit

4. **Response Headers** - On throttle failure
   - HTTP 429 Too Many Requests
   - `Retry-After` header with seconds to wait
   - Exception message: "Request was throttled. Expected available in X seconds."

### Cache Key Format

Throttles use this cache key pattern:
```python
cache_key = 'throttle_{scope}_{ident}'
```

Examples:
- `throttle_anon_192.168.1.100` - Anonymous user from IP 192.168.1.100
- `throttle_user_42` - Authenticated user with pk=42
- `throttle_uploads_42` - User 42 in 'uploads' scope

## Common Use Cases

### 1. Basic API Protection

Protect your API with sensible defaults:

```python
# settings.py
REST_FRAMEWORK = {
    'DEFAULT_THROTTLE_CLASSES': [
        'rest_framework.throttling.AnonRateThrottle',
        'rest_framework.throttling.UserRateThrottle',
    ],
    'DEFAULT_THROTTLE_RATES': {
        'anon': '100/hour',
        'user': '1000/hour',
    }
}
```

### 2. Burst Protection with Multiple Throttles

Prevent rapid-fire requests while allowing high daily usage:

```python
class BurstRateThrottle(UserRateThrottle):
    scope = 'burst'

class SustainedRateThrottle(UserRateThrottle):
    scope = 'sustained'

class APIView(viewsets.ModelViewSet):
    throttle_classes = [BurstRateThrottle, SustainedRateThrottle]

# settings.py
'DEFAULT_THROTTLE_RATES': {
    'burst': '60/min',      # Max 60 requests per minute
    'sustained': '10000/day' # Max 10,000 requests per day
}
```

### 3. High-Risk Endpoint Protection

Stricter limits on expensive or sensitive operations:

```python
from rest_framework.throttling import UserRateThrottle

class UploadRateThrottle(UserRateThrottle):
    scope = 'uploads'

class PasswordResetThrottle(AnonRateThrottle):
    scope = 'password_reset'

class FileUploadView(APIView):
    throttle_classes = [UploadRateThrottle]

class PasswordResetView(APIView):
    throttle_classes = [PasswordResetThrottle]

# settings.py
'DEFAULT_THROTTLE_RATES': {
    'uploads': '10/hour',
    'password_reset': '3/hour',
}
```

### 4. Subscription-Based Throttling

Different limits based on user subscription tier:

```python
from rest_framework.throttling import UserRateThrottle

class SubscriptionRateThrottle(UserRateThrottle):
    def get_cache_key(self, request, view):
        if not request.user.is_authenticated:
            return None  # Don't throttle anonymous users

        # Different scope per subscription tier
        tier = request.user.subscription_tier
        self.scope = f'tier_{tier}'

        return self.cache_format % {
            'scope': self.scope,
            'ident': request.user.pk
        }

# settings.py
'DEFAULT_THROTTLE_RATES': {
    'tier_free': '100/day',
    'tier_basic': '1000/day',
    'tier_premium': '10000/day',
}
```

## Common Mistakes

### ❌ Mistake 1: No Cache Backend Configured

```python
# WRONG: Throttling requires cache backend
REST_FRAMEWORK = {
    'DEFAULT_THROTTLE_CLASSES': ['rest_framework.throttling.UserRateThrottle'],
    'DEFAULT_THROTTLE_RATES': {'user': '1000/day'}
}
# No CACHES setting = throttling doesn't work!

# CORRECT: Always configure cache backend
CACHES = {
    'default': {
        'BACKEND': 'django.core.cache.backends.redis.RedisCache',
        'LOCATION': 'redis://127.0.0.1:6379/1',
    }
}
```

### ❌ Mistake 2: Using LocMemCache in Production

```python
# WRONG: LocMemCache doesn't persist across workers/restarts
CACHES = {
    'default': {
        'BACKEND': 'django.core.cache.backends.locmem.LocMemCache',
    }
}
# Each gunicorn worker has separate cache = inconsistent throttling

# CORRECT: Use persistent cache backend in production
CACHES = {
    'default': {
        'BACKEND': 'django.core.cache.backends.redis.RedisCache',
        'LOCATION': 'redis://127.0.0.1:6379/1',
    }
}
```

### ❌ Mistake 3: Forgetting Scope Configuration

```python
# WRONG: Throttle class with scope but no rate configured
class CustomThrottle(UserRateThrottle):
    scope = 'custom'

# settings.py - missing 'custom' key
'DEFAULT_THROTTLE_RATES': {
    'user': '1000/day',
    # No 'custom' rate!
}
# Results in: ImproperlyConfigured: No default throttle rate set for 'custom' scope

# CORRECT: Define rate for every scope
'DEFAULT_THROTTLE_RATES': {
    'user': '1000/day',
    'custom': '500/hour',
}
```

### ❌ Mistake 4: Returning Cache Key for Unauthenticated When Using UserRateThrottle

```python
# WRONG: Custom throttle returns None for anonymous users but extends UserRateThrottle
class BadThrottle(UserRateThrottle):
    def get_cache_key(self, request, view):
        if not request.user.is_authenticated:
            return None  # Wants to skip anonymous
        return super().get_cache_key(request, view)

# UserRateThrottle already handles anonymous with IP address!
# This creates confusion about intended behavior

# CORRECT: Use AnonRateThrottle if you want to throttle anonymous separately
# Or override properly if you truly want to skip them:
class AuthenticatedOnlyThrottle(SimpleRateThrottle):
    scope = 'authenticated'

    def get_cache_key(self, request, view):
        if not request.user.is_authenticated:
            return None  # Explicitly skip throttling for anonymous

        return self.cache_format % {
            'scope': self.scope,
            'ident': request.user.pk
        }
```

### ❌ Mistake 5: Conflicting Throttle Rates

```python
# WRONG: Multiple throttles with same scope
class Throttle1(UserRateThrottle):
    scope = 'user'  # Uses 'user' scope

class Throttle2(UserRateThrottle):
    scope = 'user'  # Same scope!

throttle_classes = [Throttle1, Throttle2]
# Both check same cache key = redundant and confusing

# CORRECT: Use different scopes for different purposes
class BurstThrottle(UserRateThrottle):
    scope = 'burst'

class SustainedThrottle(UserRateThrottle):
    scope = 'sustained'

throttle_classes = [BurstThrottle, SustainedThrottle]

'DEFAULT_THROTTLE_RATES': {
    'burst': '60/min',
    'sustained': '1000/day'
}
```

### ❌ Mistake 6: Overly Aggressive Rate Limits

```python
# WRONG: Rates too strict for real usage
'DEFAULT_THROTTLE_RATES': {
    'user': '10/hour',  # Only 10 requests per hour!
}
# Users doing legitimate work will hit limit quickly

# CORRECT: Set reasonable limits based on actual usage patterns
'DEFAULT_THROTTLE_RATES': {
    'burst': '60/min',     # Allow 1 request per second sustained
    'sustained': '5000/day' # Allows ~3.5 requests per minute average
}
# Monitor actual usage and adjust accordingly
```

## Rate Format Reference

Supported rate string formats:

```python
'100/second' or '100/s'   # 100 requests per second
'100/minute' or '100/min' or '100/m'  # 100 requests per minute
'100/hour' or '100/h'     # 100 requests per hour
'100/day' or '100/d'      # 100 requests per day (86400 seconds)
```

Rate parsing:
- Number before `/` = max requests in time period
- Letter after `/` = time period (first character: s/m/h/d)
- Periods: s=1sec, m=60sec, h=3600sec, d=86400sec

## Reference Files

### Built-in Throttles
**[reference/builtin-throttles.md](reference/builtin-throttles.md)**
- AnonRateThrottle - Throttle anonymous users by IP
- UserRateThrottle - Throttle by user ID or IP
- ScopedRateThrottle - Different rates for different scopes
- SimpleRateThrottle - Base class for rate throttles

### Custom Throttles
**[reference/custom-throttles.md](reference/custom-throttles.md)**
- Creating custom throttle classes
- Overriding get_cache_key()
- Custom rate determination
- Dynamic rate calculation
- Advanced patterns (time-based, subscription-based)

### Rate Configuration
**[reference/rate-configuration.md](reference/rate-configuration.md)**
- Cache backend setup (Redis, Memcached, database)
- Rate format specifications
- Global vs per-view throttling
- Multiple throttle configuration
- NUM_PROXIES setting for correct IP detection

### Working Examples
**[reference/examples/throttle-patterns.py](reference/examples/throttle-patterns.py)**
- Complete working code examples
- Subscription tier throttling
- Time-based throttling
- Method-based throttling
- Custom cache key patterns
- Testing throttles
