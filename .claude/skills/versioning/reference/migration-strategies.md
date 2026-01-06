# API Version Migration Strategies

This document covers strategies for migrating between API versions, maintaining backwards compatibility, and managing version lifecycle.

## Table of Contents

1. [Planning a Version Migration](#planning-a-version-migration)
2. [Migration Patterns](#migration-patterns)
3. [Backwards Compatibility](#backwards-compatibility)
4. [Client Migration Guide](#client-migration-guide)
5. [Version Lifecycle Management](#version-lifecycle-management)

---

## Planning a Version Migration

### When to Create a New Version

Create a new version when you need to make **breaking changes**:

**Breaking Changes (Require New Version):**
- ❌ Removing a field from responses
- ❌ Changing field data type (string → integer)
- ❌ Renaming fields or endpoints
- ❌ Changing endpoint behavior significantly
- ❌ Requiring new required fields
- ❌ Changing authentication mechanism
- ❌ Modifying error response structure

**Non-Breaking Changes (Don't Require Version):**
- ✅ Adding optional fields
- ✅ Adding new endpoints
- ✅ Adding optional query parameters
- ✅ Improving performance
- ✅ Fixing bugs
- ✅ Adding pagination
- ✅ Improving documentation

### Migration Timeline Template

```
Week 0: Announce upcoming v2, document changes
Week 2: Release v2 (both v1 and v2 available)
Week 4: Add deprecation warnings to v1
Week 8: Remind users of v1 sunset date
Week 12: Last call - v1 will be removed soon
Week 16: Remove v1, v2 becomes default
```

---

## Migration Patterns

### Pattern 1: Parallel Versions (Recommended)

**Strategy:** Run both versions simultaneously during transition period.

```python
# urls.py - Both versions available
from django.urls import path, include
from rest_framework import routers
from myapp.views import v1, v2

# V1 Router
router_v1 = routers.DefaultRouter()
router_v1.register(r'books', v1.BookViewSet)
router_v1.register(r'authors', v1.AuthorViewSet)

# V2 Router
router_v2 = routers.DefaultRouter()
router_v2.register(r'books', v2.BookViewSet)
router_v2.register(r'authors', v2.AuthorViewSet)

urlpatterns = [
    path('api/v1/', include(router_v1.urls)),  # Old version
    path('api/v2/', include(router_v2.urls)),  # New version
]
```

**Benefits:**
- Zero downtime
- Clients migrate at their own pace
- Easy rollback if issues arise
- Clear separation of concerns

**Implementation:**

```python
# myapp/views/v1.py
class BookViewSet(viewsets.ModelViewSet):
    """V1: Legacy implementation"""
    queryset = Book.objects.all()
    serializer_class = BookSerializerV1


# myapp/views/v2.py
class BookViewSet(viewsets.ModelViewSet):
    """V2: New implementation with breaking changes"""
    queryset = Book.objects.all()
    serializer_class = BookSerializerV2

    def get_queryset(self):
        # V2 includes enhanced filtering
        queryset = super().get_queryset()
        return queryset.select_related('author').prefetch_related('categories')
```

### Pattern 2: Adapter/Translator Pattern

**Strategy:** Use adapters to translate between old and new formats.

```python
class BookSerializerV1(serializers.ModelSerializer):
    """V1: author_name as string"""
    author_name = serializers.CharField(source='author.name')

    class Meta:
        model = Book
        fields = ['id', 'title', 'author_name', 'price']


class BookSerializerV2(serializers.ModelSerializer):
    """V2: author as nested object"""
    author = AuthorSerializer()

    class Meta:
        model = Book
        fields = ['id', 'title', 'author', 'isbn', 'price']


class BookSerializerAdapter:
    """Adapter to convert between formats"""

    @staticmethod
    def v2_to_v1(v2_data):
        """Convert v2 format to v1 format"""
        return {
            'id': v2_data['id'],
            'title': v2_data['title'],
            'author_name': v2_data['author']['name'],
            'price': v2_data['price'],
            # Omit 'isbn' (not in v1)
        }

    @staticmethod
    def v1_to_v2(v1_data, author_id):
        """Convert v1 format to v2 format"""
        return {
            'id': v1_data['id'],
            'title': v1_data['title'],
            'author': {'id': author_id, 'name': v1_data['author_name']},
            'isbn': '',  # Default value
            'price': v1_data['price'],
        }
```

### Pattern 3: Feature Flags

**Strategy:** Use feature flags to gradually roll out changes.

```python
# settings.py
FEATURE_FLAGS = {
    'use_v2_serialization': False,  # Toggle this
    'enable_v2_filtering': False,
}


# views.py
from django.conf import settings

class BookViewSet(viewsets.ModelViewSet):
    queryset = Book.objects.all()

    def get_serializer_class(self):
        """Use feature flag to control serializer"""
        if settings.FEATURE_FLAGS.get('use_v2_serialization'):
            return BookSerializerV2
        return BookSerializerV1

    def get_queryset(self):
        queryset = super().get_queryset()

        if settings.FEATURE_FLAGS.get('enable_v2_filtering'):
            # New filtering logic
            return queryset.filter(active=True)

        # Old logic
        return queryset
```

### Pattern 4: Deprecation with Fallback

**Strategy:** Maintain old behavior with warnings, fallback to new.

```python
class BookViewSet(viewsets.ModelViewSet):
    queryset = Book.objects.all()

    def get_serializer_class(self):
        if self.request.version == 'v1':
            # Log usage of deprecated version
            import logging
            logger = logging.getLogger(__name__)
            logger.warning(
                f"V1 API used by {self.request.user} - "
                f"This version is deprecated"
            )
            return BookSerializerV1

        return BookSerializerV2

    def list(self, request, *args, **kwargs):
        """Handle deprecated query parameters"""
        # V1 used 'author' param, V2 uses 'author_id'
        if 'author' in request.query_params:
            # Fallback for old parameter name
            warnings.warn(
                "Query parameter 'author' is deprecated. Use 'author_id'",
                DeprecationWarning
            )
            # Map old param to new
            request.query_params._mutable = True
            request.query_params['author_id'] = request.query_params.pop('author')
            request.query_params._mutable = False

        return super().list(request, *args, **kwargs)
```

### Pattern 5: Proxy/Facade Pattern

**Strategy:** V1 endpoints proxy to V2 with transformation.

```python
class BookViewSetV1(viewsets.ModelViewSet):
    """V1: Proxies to V2 with data transformation"""

    def list(self, request, *args, **kwargs):
        # Get data from V2 logic
        v2_viewset = BookViewSetV2()
        v2_viewset.request = request
        v2_viewset.format_kwarg = self.format_kwarg

        v2_response = v2_viewset.list(request, *args, **kwargs)

        # Transform V2 response to V1 format
        v1_data = [
            BookSerializerAdapter.v2_to_v1(item)
            for item in v2_response.data
        ]

        return Response(v1_data)


class BookViewSetV2(viewsets.ModelViewSet):
    """V2: Main implementation"""
    queryset = Book.objects.all()
    serializer_class = BookSerializerV2
```

---

## Backwards Compatibility

### Maintaining Compatibility in Serializers

```python
class BackwardsCompatibleSerializer(serializers.ModelSerializer):
    """Serializer that handles both old and new field names"""

    # New field name
    author_id = serializers.IntegerField(source='author.id')

    # Legacy field name (write-only for compatibility)
    author_name = serializers.CharField(
        write_only=True,
        required=False,
        help_text="DEPRECATED: Use author_id instead"
    )

    class Meta:
        model = Book
        fields = ['id', 'title', 'author_id', 'author_name', 'price']

    def create(self, validated_data):
        # Handle legacy field
        if 'author_name' in validated_data:
            author_name = validated_data.pop('author_name')
            # Look up author by name
            try:
                author = Author.objects.get(name=author_name)
                validated_data['author'] = author
            except Author.DoesNotExist:
                raise serializers.ValidationError({
                    'author_name': 'Author not found'
                })

        return super().create(validated_data)
```

### Handling Renamed Fields

```python
class RenamedFieldSerializer(serializers.ModelSerializer):
    """Handle field rename from 'desc' to 'description'"""

    # New field name
    description = serializers.CharField()

    # Old field name (for backwards compatibility)
    desc = serializers.CharField(
        source='description',
        required=False,
        write_only=True,
        help_text="DEPRECATED: Use 'description'"
    )

    class Meta:
        model = Book
        fields = ['id', 'title', 'description', 'desc']

    def to_representation(self, instance):
        """Include both old and new field names in response"""
        data = super().to_representation(instance)

        # For backwards compatibility, include 'desc' in response
        if self.context.get('request') and self.context['request'].version == 'v1':
            data['desc'] = data['description']

        return data
```

### URL Redirection for Deprecated Endpoints

```python
# urls.py
from django.views.generic import RedirectView

urlpatterns = [
    # Old endpoint (deprecated) - redirects to new
    path(
        'api/v1/old-books/',
        RedirectView.as_view(
            url='/api/v2/books/',
            permanent=False  # 302, not 301
        ),
        name='old-books-redirect'
    ),

    # New endpoint
    path('api/v2/books/', BookViewSet.as_view({'get': 'list'})),
]
```

---

## Client Migration Guide

### Documentation Template

```markdown
# Migrating from API v1 to v2

## Timeline
- **v2 Release Date:** 2024-01-15
- **v1 Deprecation Date:** 2024-03-15
- **v1 Sunset Date:** 2024-07-15

## Breaking Changes

### 1. Author Field Changed from String to Object

**V1 Response:**
{
  "id": 1,
  "title": "Book Title",
  "author_name": "John Smith"
}

**V2 Response:**
{
  "id": 1,
  "title": "Book Title",
  "author": {
    "id": 5,
    "name": "John Smith",
    "email": "john@example.com"
  }
}

**Migration Steps:**
1. Update your client to parse nested author object
2. Use author.id for relationships instead of author_name
3. Test with v2 endpoint before switching

### 2. New Required Field: ISBN

**V2 Change:**
All books now require an ISBN field (13 digits).

**Migration Steps:**
1. Add isbn field to your book creation requests
2. Update existing books with ISBN values
3. Handle validation errors for missing ISBN

### 3. Pagination Now Required

**V1:** Returned all results
**V2:** Results are paginated (20 per page)

**Migration Steps:**
1. Implement pagination handling in your client
2. Use 'next' and 'previous' links for navigation
3. Adjust page size with ?page_size=N (max 100)

## Code Examples

### JavaScript (Fetch API)

// V1 Code
fetch('/api/v1/books/')
  .then(r => r.json())
  .then(books => {
    books.forEach(book => {
      console.log(book.author_name);  // String
    });
  });

// V2 Code
fetch('/api/v2/books/')
  .then(r => r.json())
  .then(data => {
    data.results.forEach(book => {  // Note: paginated
      console.log(book.author.name);  // Object
    });

    // Handle pagination
    if (data.next) {
      fetch(data.next).then(/* ... */);
    }
  });

### Python (requests)

# V1 Code
import requests

response = requests.get('http://api.example.com/v1/books/')
books = response.json()
for book in books:
    print(book['author_name'])

# V2 Code
import requests

response = requests.get('http://api.example.com/v2/books/')
data = response.json()

for book in data['results']:  # Paginated
    print(book['author']['name'])  # Nested object

# Handle pagination
while data['next']:
    response = requests.get(data['next'])
    data = response.json()
    # Process data['results']...

## Testing Both Versions

You can test both versions side-by-side:
- V1: http://api.example.com/v1/books/
- V2: http://api.example.com/v2/books/

## Need Help?

Contact support@example.com or visit our migration guide:
https://docs.example.com/api/v2-migration
```

---

## Version Lifecycle Management

### Phase 1: Planning (Weeks 1-2)

```python
# Document all breaking changes
BREAKING_CHANGES = {
    'v1_to_v2': [
        {
            'type': 'field_type_change',
            'field': 'author',
            'old': 'string (author name)',
            'new': 'object (author details)',
            'impact': 'high',
            'endpoints': ['/api/books/', '/api/books/{id}/'],
        },
        {
            'type': 'new_required_field',
            'field': 'isbn',
            'required_in': 'v2',
            'impact': 'medium',
            'endpoints': ['/api/books/'],
        },
        {
            'type': 'pagination_added',
            'old': 'all results returned',
            'new': '20 results per page',
            'impact': 'high',
            'endpoints': ['/api/books/', '/api/authors/'],
        },
    ]
}

# Create migration timeline
MIGRATION_TIMELINE = {
    'announcement_date': '2024-01-15',
    'v2_release_date': '2024-02-01',
    'deprecation_warning_date': '2024-03-15',
    'v1_sunset_date': '2024-07-15',
    'minimum_support_period_days': 180,  # 6 months
}
```

### Phase 2: Release (Week 3)

```python
# Release v2 alongside v1
# urls.py
urlpatterns = [
    path('api/v1/', include('myapp.urls.v1')),  # Still supported
    path('api/v2/', include('myapp.urls.v2')),  # New version
]

# Add monitoring
import logging
logger = logging.getLogger(__name__)

class VersionMetricsMixin:
    """Track version usage"""

    def dispatch(self, request, *args, **kwargs):
        # Log version usage
        logger.info(f"API request - version: {request.version}")

        # Increment metrics
        # metrics.increment(f'api.version.{request.version}')

        return super().dispatch(request, *args, **kwargs)
```

### Phase 3: Deprecation Warning (Week 6)

```python
from datetime import datetime, timedelta

class DeprecationWarningMixin:
    """Add deprecation warnings to v1"""

    def finalize_response(self, request, response, *args, **kwargs):
        response = super().finalize_response(request, response, *args, **kwargs)

        if request.version == 'v1':
            # Add Warning header (RFC 7234)
            sunset_date = datetime(2024, 7, 15)
            days_remaining = (sunset_date - datetime.now()).days

            response['Warning'] = (
                f'299 - "API v1 is deprecated and will be removed in {days_remaining} days. '
                f'Please migrate to v2: https://docs.example.com/api/v2-migration"'
            )

            # Add Sunset header (RFC 8594)
            response['Sunset'] = sunset_date.strftime('%a, %d %b %Y %H:%M:%S GMT')

            # Link to new version
            response['Link'] = '</api/v2/>; rel="successor-version"'

        return response
```

### Phase 4: Monitoring (Ongoing)

```python
class VersionMonitoringMiddleware:
    """Monitor version usage and send alerts"""

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        version = getattr(request, 'version', None)

        # Track usage
        if version == 'v1':
            # Log for analytics
            logger.info(f"V1 usage - User: {request.user}, Path: {request.path}")

            # Alert if approaching sunset
            self.check_sunset_approaching(version)

        response = self.get_response(request)
        return response

    def check_sunset_approaching(self, version):
        """Alert if sunset is approaching and usage is still high"""
        from django.core.cache import cache

        # Get v1 usage count
        usage_key = f'api_usage_{version}_today'
        usage = cache.get(usage_key, 0)
        cache.set(usage_key, usage + 1, timeout=86400)  # 24 hours

        # Alert if usage is high
        if usage > 1000:  # Threshold
            # Send alert to team
            logger.warning(
                f"High usage of deprecated {version}: {usage} requests today"
            )
```

### Phase 5: Sunset (Week 16)

```python
class VersionSunsetMixin:
    """Return 410 Gone for sunset versions"""

    sunset_versions = ['v1']

    def dispatch(self, request, *args, **kwargs):
        if request.version in self.sunset_versions:
            return Response(
                {
                    'error': 'Gone',
                    'message': f'API {request.version} has been sunset',
                    'sunset_date': '2024-07-15',
                    'migration_guide': 'https://docs.example.com/api/v2-migration',
                    'current_version': 'v2',
                    'available_versions': ['v2', 'v3'],
                },
                status=410  # 410 Gone
            )

        return super().dispatch(request, *args, **kwargs)
```

---

## Best Practices

1. **Give Ample Notice:** Minimum 6 months between deprecation and sunset
2. **Monitor Usage:** Track which clients use which versions
3. **Provide Migration Tools:** Scripts, adapters, documentation
4. **Version Configuration:** Store in database for dynamic control
5. **Test Thoroughly:** Ensure both versions work during transition
6. **Clear Communication:** Email, dashboard notices, API responses
7. **Gradual Rollout:** Use feature flags for complex migrations
8. **Maintain Changelog:** Document all version changes
9. **Support Window:** Support N and N-1 versions only
10. **Rollback Plan:** Be able to revert if issues arise

## Anti-Patterns to Avoid

1. ❌ **No deprecation notice** - Surprise sunset angers users
2. ❌ **Too many versions** - Supporting 5+ versions is unsustainable
3. ❌ **Version for every change** - Only version breaking changes
4. ❌ **No migration docs** - Clients need clear guidance
5. ❌ **Sudden removal** - Always give warning period
6. ❌ **Breaking v1 while it's supported** - Keep it stable
7. ❌ **No monitoring** - You need to know who's using what
8. ❌ **Inconsistent behavior** - v1 and v2 should be predictable

## Resources

- [Semantic Versioning](https://semver.org/)
- [RFC 8594 - Sunset HTTP Header](https://tools.ietf.org/html/rfc8594)
- [RFC 7234 - HTTP Caching (Warning header)](https://tools.ietf.org/html/rfc7234)
- [API Evolution Best Practices](https://www.django-rest-framework.org/topics/versioning/)
