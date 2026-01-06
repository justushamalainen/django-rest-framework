---
version: 1.0
last_updated: 2026-01-06
difficulty: intermediate
keywords: versioning, api-versioning, url-path, accept-header, namespace, query-parameter, hostname, backwards-compatibility
dependencies: djangorestframework>=3.14, django>=4.2
estimated_time: 20-45 minutes
---

# Django REST Framework API Versioning

## What You'll Learn

By mastering this skill, you will:

- Understand when and why to version your API
- Choose the right versioning strategy for your use case
- Implement all five DRF versioning schemes (URLPath, AcceptHeader, Namespace, QueryParameter, HostName)
- Access version information in views and serializers
- Create version-specific serializers and logic
- Handle deprecation and migration between versions
- Apply versioning best practices and avoid common mistakes
- Know when NOT to create a new version

## Before You Start

### Prerequisites

**Required Knowledge:**
- Basic Django REST Framework understanding (serializers, views, URLs)
- HTTP fundamentals (headers, URLs, status codes)
- REST API design principles

**Recommended Reading:**
- Complete the [DRF Quickstart](../quickstart/SKILL.md) first
- Understand [serializers](../serializers/SKILL.md) and [views](../views/SKILL.md)

### When to Version Your API

**Version when you need to:**
- Make breaking changes (removing fields, changing data types)
- Change endpoint behavior significantly
- Support multiple client versions simultaneously
- Maintain backwards compatibility during transitions

**DON'T version for:**
- Adding optional fields (backwards compatible)
- Fixing bugs (that's not a version change)
- Internal implementation changes
- Performance improvements
- Minor behavior tweaks

---

## Quick Start: URLPathVersioning

The most common and user-friendly approach. Version is in the URL path.

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

Edit `urls.py`:

```python
from django.urls import path, re_path
from myapp.views import BookViewSet

urlpatterns = [
    # Version in URL path
    re_path(
        r'^api/(?P<version>v[1-3])/books/$',
        BookViewSet.as_view({'get': 'list', 'post': 'create'}),
        name='book-list'
    ),
    re_path(
        r'^api/(?P<version>v[1-3])/books/(?P<pk>[0-9]+)/$',
        BookViewSet.as_view({'get': 'retrieve', 'put': 'update', 'delete': 'destroy'}),
        name='book-detail'
    ),
]
```

Or with routers:

```python
from django.urls import path, include
from rest_framework import routers

router_v1 = routers.DefaultRouter()
router_v1.register(r'books', BookViewSet)

router_v2 = routers.DefaultRouter()
router_v2.register(r'books', BookViewSetV2)

urlpatterns = [
    path('api/v1/', include((router_v1.urls, 'v1'))),
    path('api/v2/', include((router_v2.urls, 'v2'))),
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
            # Legacy behavior
            queryset = self.get_queryset().filter(published=True)
        else:
            # New behavior
            queryset = self.get_queryset()

        serializer = self.get_serializer(queryset, many=True)
        return Response(serializer.data)
```

### Step 4: Test Your Versioned API

```bash
# Version 1
curl http://localhost:8000/api/v1/books/

# Version 2
curl http://localhost:8000/api/v2/books/

# Invalid version (returns 404)
curl http://localhost:8000/api/v99/books/
```

**Congratulations!** You now have a versioned API.

---

## Versioning Strategy Decision Tree

Use this tree to choose the right versioning approach:

```
Do your clients control the HTTP headers?
│
├─ YES: Can they set Accept header?
│   │
│   ├─ YES: Use AcceptHeaderVersioning
│   │        ✓ RESTful, follows standards
│   │        ✓ URL stays clean
│   │        ✗ Harder to test in browser
│   │
│   └─ NO: Use QueryParameterVersioning
│            ✓ Easy to test
│            ✓ Works everywhere
│            ✗ Clutters URLs
│
└─ NO: Are you hosting multiple subdomains?
    │
    ├─ YES: Use HostNameVersioning
    │        ✓ Clean separation
    │        ✓ Easy caching/routing
    │        ✗ Infrastructure overhead
    │
    └─ NO: Use URLPathVersioning or NamespaceVersioning
             ✓ Clear and visible
             ✓ Browser-friendly
             ✓ Easy to cache
             ✗ URL changes with version
```

**Recommendation:** Start with URLPathVersioning. It's the most transparent and developer-friendly.

For detailed comparison of all schemes, see [reference/versioning-schemes.md](reference/versioning-schemes.md).

---

## Version-Specific Serializers

A common pattern for handling version differences:

```python
from rest_framework import serializers

class BookSerializerV1(serializers.ModelSerializer):
    """Version 1: Simple structure"""
    class Meta:
        model = Book
        fields = ['id', 'title', 'author_name', 'price']

class BookSerializerV2(serializers.ModelSerializer):
    """Version 2: Nested author, added ISBN"""
    author = AuthorSerializer(read_only=True)
    isbn = serializers.CharField(max_length=13)

    class Meta:
        model = Book
        fields = ['id', 'title', 'author', 'isbn', 'price']

class BookSerializerV3(serializers.ModelSerializer):
    """Version 3: Added categories (M2M)"""
    author = AuthorSerializer(read_only=True)
    categories = CategorySerializer(many=True, read_only=True)

    class Meta:
        model = Book
        fields = ['id', 'title', 'author', 'isbn', 'price', 'categories']
```

For more patterns, see [reference/version-handling.md](reference/version-handling.md).

---

## Common Mistakes and Solutions

### 1. Not Setting DEFAULT_VERSION

**Error:** `AssertionError: 'version' is not set in request.`

**Solution:** Always configure a default version:
```python
REST_FRAMEWORK = {
    'DEFAULT_VERSION': 'v1',  # Always set this!
}
```

### 2. Forgetting to Capture Version in URL Pattern

**Error:** Version is always None in views.

**Solution:** Make sure your regex captures the version:
```python
# Wrong - no capture group
re_path(r'^api/v1/books/$', ...)

# Correct - captures version parameter
re_path(r'^api/(?P<version>v[1-3])/books/$', ...)
```

### 3. Creating New Version for Every Change

**Mistake:** Creating v1, v2, v3, v4 for minor additions.

**Solution:** Only version for breaking changes:
```python
# DON'T create new version for this:
class BookSerializerV2(serializers.ModelSerializer):
    optional_field = serializers.CharField(required=False)  # Backwards compatible!

# DO create new version for this:
class BookSerializerV2(serializers.ModelSerializer):
    author = AuthorSerializer()  # Changed from string to object - BREAKING!
```

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

### 5. Mixing Versioning Strategies

**Problem:** Using URL versioning for some endpoints, header versioning for others.

**Solution:** Pick ONE strategy and stick to it across your entire API.

### 6. Not Planning Deprecation

**Problem:** Supporting too many old versions forever.

**Solution:** Document deprecation timeline:
```python
class BookViewSetV1(viewsets.ModelViewSet):
    """
    DEPRECATED: This version will be removed on 2024-12-31.
    Please migrate to v2.
    """
    def list(self, request, *args, **kwargs):
        # Add deprecation warning header
        response = super().list(request, *args, **kwargs)
        response['Warning'] = '299 - "API version v1 is deprecated. Use v2."'
        return response
```

For migration strategies, see [reference/migration-strategies.md](reference/migration-strategies.md).

---

## All Versioning Schemes Overview

### 1. URLPathVersioning (Recommended)
```bash
GET /api/v1/books/
```
**Best for:** Most APIs, public APIs, browser testing

### 2. AcceptHeaderVersioning
```bash
GET /api/books/
Accept: application/json; version=1.0
```
**Best for:** RESTful purists, mobile apps, APIs with header control

### 3. NamespaceVersioning
```bash
GET /api/v1/books/  # Uses Django URL namespaces
```
**Best for:** Large projects with separate view modules per version

### 4. QueryParameterVersioning
```bash
GET /api/books/?version=v1
```
**Best for:** Quick prototypes, limited client capabilities

### 5. HostNameVersioning
```bash
GET https://v1.api.example.com/books/
```
**Best for:** Microservices, separate infrastructure per version

See detailed examples in [reference/versioning-schemes.md](reference/versioning-schemes.md).

---

## Next Steps

Now that you understand versioning basics:

1. **Review all schemes:** [reference/versioning-schemes.md](reference/versioning-schemes.md)
2. **Learn version handling:** [reference/version-handling.md](reference/version-handling.md)
3. **Plan migrations:** [reference/migration-strategies.md](reference/migration-strategies.md)
4. **Study examples:** [reference/examples/versioning-patterns.py](reference/examples/versioning-patterns.py)

## Resources

- [DRF Versioning Documentation](https://www.django-rest-framework.org/api-guide/versioning/)
- [DRF Source Code](/home/user/django-rest-framework/rest_framework/versioning.py)
- [API Versioning Best Practices](https://www.django-rest-framework.org/api-guide/versioning/#api-versioning)
- [Semantic Versioning](https://semver.org/)
