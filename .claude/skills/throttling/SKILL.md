---
description: Rate limiting and throttling in Django REST Framework. Use when implementing API rate limits, protecting against abuse, managing burst requests, creating custom throttle classes, or configuring different rate limits for authenticated vs anonymous users. Covers built-in throttles (AnonRateThrottle, UserRateThrottle, ScopedRateThrottle), custom throttles, cache configuration, and per-view throttling.
---

# DRF Throttling (Rate Limiting)

Protect your API from abuse with request rate limiting.

## Quick Start

Complete working example with production-ready configuration:

```python
# settings.py
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

# Production: Use Redis (works with multiple workers)
CACHES = {
    'default': {
        'BACKEND': 'django.core.cache.backends.redis.RedisCache',
        'LOCATION': 'redis://127.0.0.1:6379/1',
    }
}

# Development: Use LocMemCache (single process only)
CACHES = {
    'default': {
        'BACKEND': 'django.core.cache.backends.locmem.LocMemCache',
        'LOCATION': 'unique-snowflake',
    }
}
```

Effect:
- Anonymous users (by IP): 100 requests/day
- Authenticated users (by user ID): 1000 requests/day
- Returns HTTP 429 with Retry-After header when exceeded

## Built-in Throttles

### AnonRateThrottle
Throttles unauthenticated users by IP address. Does not throttle authenticated users.

```python
'rest_framework.throttling.AnonRateThrottle'
# Rate key: 'anon'
```

### UserRateThrottle
Throttles authenticated users by user ID, unauthenticated by IP.

```python
'rest_framework.throttling.UserRateThrottle'
# Rate key: 'user'
```

### ScopedRateThrottle
Different rate limits for different API endpoints.

```python
from rest_framework.throttling import ScopedRateThrottle

class ContactView(APIView):
    throttle_classes = [ScopedRateThrottle]
    throttle_scope = 'contacts'

class UploadView(APIView):
    throttle_classes = [ScopedRateThrottle]
    throttle_scope = 'uploads'

# settings.py
'DEFAULT_THROTTLE_RATES': {
    'contacts': '1000/day',
    'uploads': '20/day',
}
```

### Rate Format

```python
'100/second'  # or '100/s'
'100/minute'  # or '100/min' or '100/m'
'100/hour'    # or '100/h'
'100/day'     # or '100/d'
```

## Per-View Throttling

Override throttle_classes on specific views:

```python
from rest_framework.throttling import UserRateThrottle

class BurstRateThrottle(UserRateThrottle):
    scope = 'burst'

class SustainedRateThrottle(UserRateThrottle):
    scope = 'sustained'

class UploadViewSet(ModelViewSet):
    # Both throttles must pass (AND logic)
    throttle_classes = [BurstRateThrottle, SustainedRateThrottle]

# settings.py
'DEFAULT_THROTTLE_RATES': {
    'burst': '60/min',      # Max 60 requests per minute
    'sustained': '1000/day', # Max 1000 requests per day
}
```

Effect: Users can burst up to 60 req/min but are still limited to 1000 req/day total.

## Custom Throttle

Create custom throttling logic based on user properties:

```python
from rest_framework.throttling import UserRateThrottle

class SubscriptionRateThrottle(UserRateThrottle):
    """Different rate limits per subscription tier"""

    def get_cache_key(self, request, view):
        if not request.user.is_authenticated:
            return None  # Don't throttle anonymous users

        # Get user's subscription tier
        tier = getattr(request.user, 'subscription_tier', 'free')

        # Use tier-specific scope
        self.scope = f'tier_{tier}'

        # Generate cache key: 'throttle_tier_premium_42'
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

# views.py
class APIView(viewsets.ModelViewSet):
    throttle_classes = [SubscriptionRateThrottle]
```

### Custom Throttle Template

```python
from rest_framework.throttling import SimpleRateThrottle

class CustomThrottle(SimpleRateThrottle):
    scope = 'custom'  # Must match key in DEFAULT_THROTTLE_RATES

    def get_cache_key(self, request, view):
        # Return None to skip throttling for this request
        if some_condition:
            return None

        # Return unique identifier for throttling
        ident = self.get_ident()  # Gets IP or custom identifier

        return self.cache_format % {
            'scope': self.scope,
            'ident': ident
        }
```

## Common Mistakes

### No Cache Backend Configured

```python
# WRONG: Throttling silently fails without cache backend
REST_FRAMEWORK = {
    'DEFAULT_THROTTLE_CLASSES': ['rest_framework.throttling.UserRateThrottle'],
    'DEFAULT_THROTTLE_RATES': {'user': '1000/day'}
}
# Missing CACHES setting!

# CORRECT: Always configure cache
CACHES = {
    'default': {
        'BACKEND': 'django.core.cache.backends.redis.RedisCache',
        'LOCATION': 'redis://127.0.0.1:6379/1',
    }
}
```

### LocMemCache in Production

```python
# WRONG: LocMemCache doesn't work with multiple workers
CACHES = {
    'default': {
        'BACKEND': 'django.core.cache.backends.locmem.LocMemCache',
    }
}
# Each gunicorn/uwsgi worker has separate cache = inconsistent throttling
# User could get 1000 requests per worker instead of 1000 total!

# CORRECT: Use Redis or Memcached in production
CACHES = {
    'default': {
        'BACKEND': 'django.core.cache.backends.redis.RedisCache',
        'LOCATION': 'redis://127.0.0.1:6379/1',
    }
}
```

### Missing Scope in DEFAULT_THROTTLE_RATES

```python
# WRONG: Custom scope without rate configuration
class CustomThrottle(UserRateThrottle):
    scope = 'custom'

'DEFAULT_THROTTLE_RATES': {
    'user': '1000/day',
    # Missing 'custom' rate!
}
# Error: ImproperlyConfigured: No default throttle rate set for 'custom' scope

# CORRECT: Define rate for every scope
'DEFAULT_THROTTLE_RATES': {
    'user': '1000/day',
    'custom': '500/hour',
}
```

## Next Steps

- Start with AnonRateThrottle + UserRateThrottle for basic protection
- Use Redis cache backend in production
- Add ScopedRateThrottle for endpoint-specific limits
- Create custom throttles for subscription tiers or special logic
- Monitor throttle responses and adjust rates based on actual usage
