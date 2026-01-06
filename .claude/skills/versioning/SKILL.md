---
version: 1.0
last_updated: 2026-01-06
difficulty: intermediate
keywords: versioning, api-versioning, url-path, backwards-compatibility
dependencies: djangorestframework>=3.14, django>=4.2
estimated_time: 15-20 minutes
---

# Django REST Framework API Versioning

## What You'll Learn

By mastering this skill, you will:

- Understand when to version your API
- Implement URLPathVersioning (the recommended approach)
- Access version information in views and serializers
- Create version-specific serializers
- Handle deprecation with Warning headers
- Avoid common versioning mistakes

## Before You Start

### Prerequisites

**Required Knowledge:**
- Basic Django REST Framework (serializers, views, URLs)
- HTTP fundamentals

**Recommended:** Complete the DRF Quickstart first

### When to Version Your API

**Create a new version when you have breaking changes:**
- Removing a field from responses
- Changing field data type (string → integer)
- Renaming fields or endpoints
- Changing endpoint behavior significantly

**DON'T version for non-breaking changes:**
- Adding optional fields (backwards compatible)
- Fixing bugs
- Performance improvements
- Adding new endpoints

---

## Our Recommendation: Use URLPathVersioning

**Why URLPathVersioning?**
- Clear and visible in URLs
- Easy to test in browsers
- Works everywhere (no special headers needed)
- Simple to document
- Easy to cache
- Bookmark-friendly

**URL format:** `/api/v1/books/`, `/api/v2/books/`

### Alternative: AcceptHeaderVersioning

If you need a RESTful approach with clean URLs, consider AcceptHeaderVersioning where the version is in the Accept header (`Accept: application/json; version=1.0`). However, this is harder to test and requires client header control. For most use cases, stick with URLPathVersioning.

---

## Quick Start: URLPathVersioning

### Step 1: Configure Versioning

Edit your `settings.py`:

```python
REST_FRAMEWORK = {
    'DEFAULT_VERSIONING_CLASS': 'rest_framework.versioning.URLPathVersioning',
    'DEFAULT_VERSION': 'v1',
    'ALLOWED_VERSIONS': ['v1', 'v2', 'v3'],
    'VERSION_PARAM': 'version',
}
```

### Step 2: Update URL Configuration

**Option A: Using re_path with regex**

```python
from django.urls import re_path
from myapp.views import BookViewSet

urlpatterns = [
    re_path(
        r'^api/(?P<version>v[1-3])/books/$',
        BookViewSet.as_view({'get': 'list', 'post': 'create'}),
        name='book-list'
    ),
]
```

**Option B: Using routers (recommended for multiple endpoints)**

```python
from django.urls import path, include
from rest_framework import routers
from myapp.views import BookViewSet

router_v1 = routers.DefaultRouter()
router_v1.register(r'books', BookViewSet)

router_v2 = routers.DefaultRouter()
router_v2.register(r'books', BookViewSet)

urlpatterns = [
    path('api/v1/', include(router_v1.urls)),
    path('api/v2/', include(router_v2.urls)),
]
```

### Step 3: Access Version in Views

```python
from rest_framework import viewsets
from rest_framework.response import Response

class BookViewSet(viewsets.ModelViewSet):
    queryset = Book.objects.all()

    def get_serializer_class(self):
        # Use different serializers per version
        if self.request.version == 'v1':
            return BookSerializerV1
        elif self.request.version == 'v2':
            return BookSerializerV2
        return BookSerializerV3

    def list(self, request, *args, **kwargs):
        # Version-specific logic
        if request.version == 'v1':
            queryset = self.get_queryset().filter(published=True)
        else:
            queryset = self.get_queryset()

        serializer = self.get_serializer(queryset, many=True)
        return Response(serializer.data)
```

### Step 4: Create Version-Specific Serializers

```python
from rest_framework import serializers

class BookSerializerV1(serializers.ModelSerializer):
    """Version 1: Simple structure"""
    author_name = serializers.CharField(source='author.name', read_only=True)

    class Meta:
        model = Book
        fields = ['id', 'title', 'author_name', 'price']


class BookSerializerV2(serializers.ModelSerializer):
    """Version 2: Nested author, added ISBN"""
    author = AuthorSerializer(read_only=True)

    class Meta:
        model = Book
        fields = ['id', 'title', 'author', 'isbn', 'price']
```

### Step 5: Test Your Versioned API

```bash
# Version 1
curl http://localhost:8000/api/v1/books/

# Version 2
curl http://localhost:8000/api/v2/books/

# Invalid version (returns 404)
curl http://localhost:8000/api/v99/books/
```

---

## Common Mistakes and Solutions

### 1. Not Setting DEFAULT_VERSION

**Error:** `AssertionError: 'version' is not set in request.`

**Solution:** Always configure a default version in settings:
```python
REST_FRAMEWORK = {
    'DEFAULT_VERSION': 'v1',  # Always set this!
}
```

### 2. Forgetting to Capture Version in URL Pattern

**Error:** Version is always None in views.

**Solution:** Make sure your regex captures the version parameter:
```python
# Wrong - no capture group
re_path(r'^api/v1/books/$', ...)

# Correct - captures version parameter
re_path(r'^api/(?P<version>v[1-3])/books/$', ...)
```

### 3. Creating New Version for Every Change

**Mistake:** Creating v1, v2, v3, v4 for minor additions.

**Solution:** Only version for breaking changes. Adding optional fields is backwards compatible!

### 4. Not Testing All Versions

**Problem:** Old versions break silently.

**Solution:** Test all supported versions:
```python
from rest_framework.test import APITestCase

class BookAPITestCase(APITestCase):
    def test_v1_endpoint(self):
        response = self.client.get('/api/v1/books/')
        self.assertEqual(response.status_code, 200)

    def test_v2_endpoint(self):
        response = self.client.get('/api/v2/books/')
        self.assertEqual(response.status_code, 200)
```

---

## Deprecation: Adding Warning Headers

When you're ready to deprecate an old version, add a Warning header:

```python
class BookViewSet(viewsets.ModelViewSet):
    queryset = Book.objects.all()
    serializer_class = BookSerializer

    def finalize_response(self, request, response, *args, **kwargs):
        response = super().finalize_response(request, response, *args, **kwargs)

        if request.version == 'v1':
            response['Warning'] = '299 - "API v1 is deprecated. Please migrate to v2."'

        return response
```

---

## Next Steps

For more details:

1. **See all versioning schemes:** [reference/versioning-schemes.md](reference/versioning-schemes.md)
2. **Learn version handling patterns:** [reference/version-handling.md](reference/version-handling.md)
3. **Study complete examples:** [reference/examples/versioning-patterns.py](reference/examples/versioning-patterns.py)

## Resources

- [DRF Versioning Documentation](https://www.django-rest-framework.org/api-guide/versioning/)
- [DRF Source Code](/home/user/django-rest-framework/rest_framework/versioning.py)
