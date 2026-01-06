# Rate Configuration and Cache Setup

Comprehensive guide to configuring throttling rates, cache backends, and deployment considerations.

## Rate Format Specification

### Supported Rate Formats

DRF accepts rate strings in the format: `<number>/<period>`

```python
'DEFAULT_THROTTLE_RATES': {
    # Seconds
    '10/second' or '10/sec' or '10/s': 10 requests per second,

    # Minutes
    '100/minute' or '100/min' or '100/m': 100 requests per 60 seconds,

    # Hours
    '1000/hour' or '1000/h': 1000 requests per 3600 seconds,

    # Days
    '5000/day' or '5000/d': 5000 requests per 86400 seconds,
}
```

### Period Conversion

```python
# Internal conversion (done by parse_rate method)
rate_map = {
    's': 1,       # 1 second
    'm': 60,      # 60 seconds
    'h': 3600,    # 3600 seconds (1 hour)
    'd': 86400,   # 86400 seconds (24 hours)
}

# Example: "1000/hour"
# Parsed as: (1000, 3600)
# Meaning: 1000 requests allowed within any 3600 second window
```

### Rate Examples

```python
REST_FRAMEWORK = {
    'DEFAULT_THROTTLE_RATES': {
        # Very restrictive (for sensitive operations)
        'password_reset': '3/hour',
        'account_creation': '5/day',

        # Moderate (for authenticated APIs)
        'user': '1000/day',
        'burst': '60/min',

        # Generous (for public read-only APIs)
        'anon': '100/hour',
        'public_read': '10000/day',

        # Very high (for internal services)
        'internal': '100000/day',
    }
}
```

### Choosing Appropriate Rates

Consider:
1. **Operation cost** - Database queries, external APIs, file operations
2. **Expected usage patterns** - How often do legitimate users access this?
3. **Abuse potential** - How much damage can spam/abuse cause?
4. **Business requirements** - Subscription tiers, SLA guarantees

**General Guidelines:**
```python
# Read operations (low cost)
'read': '10000/day'  # ~7 requests per minute sustained

# Write operations (moderate cost)
'write': '1000/day'  # ~40 requests per hour sustained

# Expensive operations (high cost)
'expensive': '100/day'  # ~4 requests per hour sustained

# Sensitive operations (security critical)
'sensitive': '10/hour'  # Very limited
```

## Cache Backend Configuration

### Overview

Throttling REQUIRES a cache backend. Without it, throttling will not work.

**Key Requirements:**
- Must persist across requests
- Must support expiration (TTL)
- Must be shared across workers in production

### Development: LocMemCache

For development and testing only:

```python
# settings.py
CACHES = {
    'default': {
        'BACKEND': 'django.core.cache.backends.locmem.LocMemCache',
        'LOCATION': 'unique-snowflake',
    }
}
```

**Limitations:**
- Not shared between processes/workers
- Lost on server restart
- OK for development, NEVER for production

### Production: Redis (Recommended)

Best choice for production environments:

```python
# settings.py
CACHES = {
    'default': {
        'BACKEND': 'django.core.cache.backends.redis.RedisCache',
        'LOCATION': 'redis://127.0.0.1:6379/1',
        'OPTIONS': {
            'CLIENT_CLASS': 'django_redis.client.DefaultClient',
        },
        'KEY_PREFIX': 'drf_throttle',
        'TIMEOUT': 86400,  # 24 hours default
    }
}
```

**Installation:**
```bash
pip install redis django-redis
```

**Advantages:**
- Persistent and shared across workers
- Fast in-memory operations
- Native TTL support
- Survives restarts (if persistence configured)
- Scales well

**Redis Configuration Options:**

```python
CACHES = {
    'default': {
        'BACKEND': 'django.core.cache.backends.redis.RedisCache',
        'LOCATION': 'redis://127.0.0.1:6379/1',
        'OPTIONS': {
            'CLIENT_CLASS': 'django_redis.client.DefaultClient',
            'CONNECTION_POOL_KWARGS': {
                'max_connections': 50,
                'retry_on_timeout': True,
            },
            'SOCKET_CONNECT_TIMEOUT': 5,
            'SOCKET_TIMEOUT': 5,
            'COMPRESSOR': 'django_redis.compressors.zlib.ZlibCompressor',
            'IGNORE_EXCEPTIONS': True,  # Don't crash if Redis is down
        },
        'KEY_PREFIX': 'myapp',
        'VERSION': 1,
    }
}
```

### Production: Memcached

Alternative to Redis:

```python
# settings.py
CACHES = {
    'default': {
        'BACKEND': 'django.core.cache.backends.memcached.PyMemcacheCache',
        'LOCATION': '127.0.0.1:11211',
        'OPTIONS': {
            'no_delay': True,
            'ignore_exc': True,
            'max_pool_size': 4,
            'use_pooling': True,
        }
    }
}
```

**Installation:**
```bash
pip install pymemcache
```

**Advantages:**
- Fast and simple
- Shared across workers
- Good for simple caching needs

**Disadvantages:**
- Less feature-rich than Redis
- No persistence across restarts
- Less flexible data structures

### Dedicated Throttle Cache

Use separate cache for throttling:

```python
CACHES = {
    'default': {
        'BACKEND': 'django.core.cache.backends.redis.RedisCache',
        'LOCATION': 'redis://127.0.0.1:6379/1',
    },
    'throttle': {
        'BACKEND': 'django.core.cache.backends.redis.RedisCache',
        'LOCATION': 'redis://127.0.0.1:6379/2',  # Different Redis DB
        'OPTIONS': {
            'CLIENT_CLASS': 'django_redis.client.DefaultClient',
        },
    }
}

# Use in throttle classes
from django.core.cache import caches

class CustomThrottle(SimpleRateThrottle):
    cache = caches['throttle']  # Use dedicated cache
    scope = 'custom'

    def get_cache_key(self, request, view):
        # ...
        pass
```

**Benefits:**
- Isolate throttle data from other cached data
- Different eviction policies
- Easier to monitor throttle-specific cache usage
- Can use different Redis instance for scaling

### Database Cache (Not Recommended)

For completeness, but not recommended:

```python
# settings.py
CACHES = {
    'default': {
        'BACKEND': 'django.core.cache.backends.db.DatabaseCache',
        'LOCATION': 'cache_table',
    }
}
```

Setup:
```bash
python manage.py createcachetable
```

**Why Not Recommended:**
- Slow compared to Redis/Memcached
- Adds database load
- Can become a bottleneck
- Better than nothing, but avoid in production

## Global Throttle Configuration

### Default Throttle Classes

Applied to ALL views unless overridden:

```python
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
```

### Multiple Global Throttles

All throttles must pass (AND logic):

```python
REST_FRAMEWORK = {
    'DEFAULT_THROTTLE_CLASSES': [
        'myapp.throttles.BurstRateThrottle',   # 60 per minute
        'myapp.throttles.SustainedRateThrottle', # 5000 per day
    ],
    'DEFAULT_THROTTLE_RATES': {
        'burst': '60/min',
        'sustained': '5000/day',
    }
}
```

User must satisfy BOTH:
- Under 60 requests per minute (burst protection)
- Under 5000 requests per day (sustained protection)

## Per-View Throttle Configuration

### Override Default Throttles

```python
from rest_framework.throttling import AnonRateThrottle
from rest_framework.views import APIView

class MyView(APIView):
    # Override global default
    throttle_classes = [AnonRateThrottle]

    def get(self, request):
        return Response({'message': 'Success'})
```

### Disable Throttling for Specific View

```python
class UnthrottledView(APIView):
    throttle_classes = []  # Empty list = no throttling

    def get(self, request):
        return Response({'message': 'No limits!'})
```

### Custom Throttle on Specific View

```python
from myapp.throttles import StrictRateThrottle

class SensitiveView(APIView):
    throttle_classes = [StrictRateThrottle]

    def post(self, request):
        # Process sensitive operation
        return Response({'status': 'processed'})
```

## ViewSet Per-Action Throttling

### Method 1: Using get_throttles()

```python
from rest_framework.viewsets import ModelViewSet
from rest_framework.throttling import UserRateThrottle, AnonRateThrottle
from myapp.throttles import UploadRateThrottle

class DocumentViewSet(ModelViewSet):
    def get_throttles(self):
        """
        Different throttles per action.
        """
        if self.action == 'create':
            # Strict limit on uploads
            throttle_classes = [UploadRateThrottle]
        elif self.action in ['update', 'partial_update', 'destroy']:
            # Moderate limit on modifications
            throttle_classes = [UserRateThrottle]
        else:  # list, retrieve
            # Lenient limit on reads
            throttle_classes = [AnonRateThrottle]

        return [throttle() for throttle in throttle_classes]
```

### Method 2: Using ScopedRateThrottle

```python
from rest_framework.throttling import ScopedRateThrottle

class DocumentViewSet(ModelViewSet):
    throttle_classes = [ScopedRateThrottle]

    @property
    def throttle_scope(self):
        """
        Dynamic scope based on action.
        """
        if self.action == 'create':
            return 'documents_create'
        elif self.action in ['update', 'partial_update', 'destroy']:
            return 'documents_modify'
        else:
            return 'documents_read'

# settings.py
'DEFAULT_THROTTLE_RATES': {
    'documents_create': '10/hour',
    'documents_modify': '50/hour',
    'documents_read': '1000/hour',
}
```

### Method 3: Action Decorators

```python
from rest_framework.decorators import action
from rest_framework.throttling import UserRateThrottle
from myapp.throttles import UploadRateThrottle

class DocumentViewSet(ModelViewSet):
    throttle_classes = [UserRateThrottle]  # Default for all actions

    @action(detail=True, methods=['post'], throttle_classes=[UploadRateThrottle])
    def upload(self, request, pk=None):
        """Custom action with specific throttle."""
        # Upload logic
        return Response({'status': 'uploaded'})
```

## Proxy Configuration (NUM_PROXIES)

### Understanding NUM_PROXIES

When behind proxies/load balancers, DRF needs to identify the real client IP from `X-Forwarded-For` header.

```python
REST_FRAMEWORK = {
    'NUM_PROXIES': None,  # Default: use entire X-Forwarded-For
    'NUM_PROXIES': 0,     # Ignore X-Forwarded-For, use REMOTE_ADDR
    'NUM_PROXIES': 1,     # Behind 1 proxy
    'NUM_PROXIES': 2,     # Behind 2 proxies
}
```

### How It Works

```
Client Request → Proxy1 → Proxy2 → Django

X-Forwarded-For: 203.0.113.1, 198.51.100.5, 192.0.2.1
                 ^client      ^proxy1        ^proxy2
```

Configuration effects:
```python
# NUM_PROXIES = None (default)
# Uses: "203.0.113.1198.51.100.5192.0.2.1" (joined, no spaces)

# NUM_PROXIES = 0
# Uses: REMOTE_ADDR (192.0.2.1 - last proxy)

# NUM_PROXIES = 1
# Uses: 192.0.2.1 (rightmost value, last proxy)

# NUM_PROXIES = 2
# Uses: 198.51.100.5 (second from right)

# NUM_PROXIES = 3 (or more than available)
# Uses: 203.0.113.1 (client IP)
```

### Production Setup

**AWS ALB / ELB:**
```python
REST_FRAMEWORK = {
    'NUM_PROXIES': 1,  # ALB adds one proxy
}
```

**Nginx Proxy:**
```python
REST_FRAMEWORK = {
    'NUM_PROXIES': 1,  # Nginx adds one proxy
}
```

**Cloudflare + Nginx:**
```python
REST_FRAMEWORK = {
    'NUM_PROXIES': 2,  # Two proxies in chain
}
```

**No Proxies (Direct):**
```python
REST_FRAMEWORK = {
    'NUM_PROXIES': 0,  # Use REMOTE_ADDR directly
}
```

### Testing Proxy Configuration

```python
# In your view or throttle, check what DRF sees:
from rest_framework.throttling import BaseThrottle

throttle = BaseThrottle()
client_ip = throttle.get_ident(request)
print(f"Client identified as: {client_ip}")
```

## Environment-Specific Configuration

### Development Settings

```python
# settings/development.py
CACHES = {
    'default': {
        'BACKEND': 'django.core.cache.backends.locmem.LocMemCache',
    }
}

REST_FRAMEWORK = {
    'DEFAULT_THROTTLE_CLASSES': [
        'rest_framework.throttling.AnonRateThrottle',
    ],
    'DEFAULT_THROTTLE_RATES': {
        'anon': '1000/hour',  # Lenient for testing
    }
}
```

### Production Settings

```python
# settings/production.py
CACHES = {
    'default': {
        'BACKEND': 'django.core.cache.backends.redis.RedisCache',
        'LOCATION': os.environ.get('REDIS_URL', 'redis://127.0.0.1:6379/1'),
        'OPTIONS': {
            'CLIENT_CLASS': 'django_redis.client.DefaultClient',
            'SOCKET_CONNECT_TIMEOUT': 5,
            'SOCKET_TIMEOUT': 5,
            'IGNORE_EXCEPTIONS': True,  # Graceful degradation
        },
    }
}

REST_FRAMEWORK = {
    'DEFAULT_THROTTLE_CLASSES': [
        'rest_framework.throttling.AnonRateThrottle',
        'rest_framework.throttling.UserRateThrottle',
    ],
    'DEFAULT_THROTTLE_RATES': {
        'anon': '100/day',
        'user': '1000/day',
    },
    'NUM_PROXIES': int(os.environ.get('NUM_PROXIES', 1)),
}
```

### Testing Settings

```python
# settings/testing.py
CACHES = {
    'default': {
        'BACKEND': 'django.core.cache.backends.locmem.LocMemCache',
    }
}

REST_FRAMEWORK = {
    'DEFAULT_THROTTLE_CLASSES': [],  # Disable for most tests
    'DEFAULT_THROTTLE_RATES': {
        'test': '10/min',  # Low limit for throttle-specific tests
    }
}
```

## Monitoring and Debugging

### Check Cache Connection

```python
from django.core.cache import cache

# Test cache is working
cache.set('test_key', 'test_value', 60)
value = cache.get('test_key')
assert value == 'test_value', "Cache not working!"
```

### View Throttle Keys

```python
from django.core.cache import cache
from rest_framework.throttling import UserRateThrottle

# Get cache key for user
throttle = UserRateThrottle()
cache_key = 'throttle_user_42'  # For user with pk=42

history = cache.get(cache_key)
print(f"Request history: {history}")
# Output: [1641234567.89, 1641234565.12, 1641234560.45, ...]
```

### Clear Throttle for User

```python
from django.core.cache import cache

# Clear throttle for specific user
cache_key = 'throttle_user_42'
cache.delete(cache_key)

# Clear all throttles (be careful!)
cache.clear()
```

### Django Admin Command

Create management command to inspect throttles:

```python
# myapp/management/commands/check_throttles.py
from django.core.management.base import BaseCommand
from django.core.cache import cache

class Command(BaseCommand):
    help = 'Check throttle status for users'

    def add_arguments(self, parser):
        parser.add_argument('user_id', type=int)

    def handle(self, *args, **options):
        user_id = options['user_id']
        cache_key = f'throttle_user_{user_id}'

        history = cache.get(cache_key)
        if history:
            self.stdout.write(f"User {user_id} has {len(history)} requests in history")
            self.stdout.write(f"Timestamps: {history}")
        else:
            self.stdout.write(f"No throttle data for user {user_id}")
```

Usage:
```bash
python manage.py check_throttles 42
```

## Graceful Degradation

Handle cache failures gracefully:

```python
# settings.py - Redis with fallback
CACHES = {
    'default': {
        'BACKEND': 'django.core.cache.backends.redis.RedisCache',
        'LOCATION': 'redis://127.0.0.1:6379/1',
        'OPTIONS': {
            'IGNORE_EXCEPTIONS': True,  # Don't crash on Redis failure
        },
    }
}

# Custom throttle with error handling
from rest_framework.throttling import SimpleRateThrottle
import logging

logger = logging.getLogger(__name__)

class GracefulRateThrottle(SimpleRateThrottle):
    scope = 'graceful'

    def get_cache_key(self, request, view):
        if request.user.is_authenticated:
            ident = request.user.pk
        else:
            ident = self.get_ident(request)

        return self.cache_format % {
            'scope': self.scope,
            'ident': ident
        }

    def allow_request(self, request, view):
        try:
            return super().allow_request(request, view)
        except Exception as e:
            logger.error(f"Throttle cache error: {e}")
            # Allow request on cache failure (degraded mode)
            return True
```

This ensures your API stays up even if cache backend fails, though without throttling protection.
