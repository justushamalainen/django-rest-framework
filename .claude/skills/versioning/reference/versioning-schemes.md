# DRF Versioning Schemes Reference

This document covers the two most practical versioning schemes in Django REST Framework.

## Table of Contents

1. [URLPathVersioning (Recommended)](#urlpathversioning)
2. [AcceptHeaderVersioning](#acceptheaderversioning)

---

## URLPathVersioning

**Recommended Approach** - Version is included in the URL path.

### How It Works

The version is part of the URL path and extracted via a URL pattern capture group.

```
GET /api/v1/books/
GET /api/v2/books/
```

### Configuration

```python
# settings.py
REST_FRAMEWORK = {
    'DEFAULT_VERSIONING_CLASS': 'rest_framework.versioning.URLPathVersioning',
    'DEFAULT_VERSION': 'v1',
    'ALLOWED_VERSIONS': ['v1', 'v2', 'v3'],
    'VERSION_PARAM': 'version',  # Name of the URL kwarg
}
```

### URL Configuration

**Option 1: Using re_path with regex**

```python
from django.urls import re_path
from myapp.views import BookViewSet

urlpatterns = [
    re_path(
        r'^api/(?P<version>v[1-3])/books/$',
        BookViewSet.as_view({'get': 'list'}),
        name='book-list'
    ),
]
```

**Option 2: Multiple routers (cleaner for complex APIs)**

```python
from django.urls import path, include
from rest_framework import routers
from myapp import views

# V1 Router
router_v1 = routers.DefaultRouter()
router_v1.register(r'books', views.BookViewSet)
router_v1.register(r'authors', views.AuthorViewSet)

# V2 Router
router_v2 = routers.DefaultRouter()
router_v2.register(r'books', views.BookViewSet)
router_v2.register(r'authors', views.AuthorViewSet)

urlpatterns = [
    path('api/v1/', include(router_v1.urls)),
    path('api/v2/', include(router_v2.urls)),
]
```

### Accessing Version in Views

```python
from rest_framework import viewsets

class BookViewSet(viewsets.ModelViewSet):
    queryset = Book.objects.all()

    def get_serializer_class(self):
        if self.request.version == 'v1':
            return BookSerializerV1
        elif self.request.version == 'v2':
            return BookSerializerV2
        return BookSerializerV3

    def list(self, request, *args, **kwargs):
        version = request.version  # 'v1', 'v2', etc.
        print(f"Request version: {version}")
        return super().list(request, *args, **kwargs)
```

### Pros and Cons

**Advantages:**
- Clear and visible in URLs
- Easy to test in browsers
- Works everywhere (no special headers needed)
- Excellent for documentation
- Easy to cache (different URLs)
- Bookmark-friendly

**Disadvantages:**
- URL changes with each version
- Can complicate URL routing

**Best For:** Most APIs, public APIs, browser-based testing

---

## AcceptHeaderVersioning

**RESTful Approach** - Version is specified in the Accept header.

### How It Works

The version is included as a parameter in the Accept header media type.

```
GET /api/books/
Accept: application/json; version=1.0
```

### Configuration

```python
# settings.py
REST_FRAMEWORK = {
    'DEFAULT_VERSIONING_CLASS': 'rest_framework.versioning.AcceptHeaderVersioning',
    'DEFAULT_VERSION': '1.0',
    'ALLOWED_VERSIONS': ['1.0', '2.0', '3.0'],
    'VERSION_PARAM': 'version',  # Parameter name in Accept header
}
```

### URL Configuration

URLs remain clean and version-agnostic:

```python
from django.urls import path, include
from rest_framework import routers
from myapp.views import BookViewSet

router = routers.DefaultRouter()
router.register(r'books', BookViewSet)

urlpatterns = [
    path('api/', include(router.urls)),
]
```

### Client Usage

**cURL:**
```bash
# Version 1.0
curl -H "Accept: application/json; version=1.0" http://localhost:8000/api/books/

# Version 2.0
curl -H "Accept: application/json; version=2.0" http://localhost:8000/api/books/

# Default version (if header omitted)
curl http://localhost:8000/api/books/
```

**JavaScript (Fetch API):**
```javascript
fetch('http://localhost:8000/api/books/', {
    headers: {
        'Accept': 'application/json; version=2.0'
    }
})
```

**Python (requests):**
```python
import requests

response = requests.get(
    'http://localhost:8000/api/books/',
    headers={'Accept': 'application/json; version=2.0'}
)
```

### Pros and Cons

**Advantages:**
- RESTful and follows HTTP standards
- URLs stay clean and version-agnostic
- Better semantic separation
- Professional/enterprise standard

**Disadvantages:**
- Harder to test in browsers
- Not visible in URL (less transparent)
- Some caching layers ignore headers
- Requires client header control

**Best For:** Enterprise APIs, mobile apps, APIs with sophisticated clients

---

## Choosing the Right Scheme

### Use URLPathVersioning if:
- You want maximum clarity and visibility
- You're building a public API
- You need easy browser testing
- Documentation is important
- **This is our recommendation for most use cases**

### Use AcceptHeaderVersioning if:
- You want a RESTful approach
- Your clients can control HTTP headers
- URL cleanliness is critical
- You're building for mobile/enterprise clients

---

## Other Versioning Schemes

DRF also provides three other versioning schemes that we don't recommend for most use cases:

- **NamespaceVersioning**: Uses Django URL namespaces. More boilerplate, better for large projects with separate modules per version.
- **QueryParameterVersioning**: Version as query param (`?version=v1`). Simple but clutters URLs.
- **HostNameVersioning**: Version in subdomain (`v1.api.example.com`). Requires DNS/infrastructure setup.

For details on these schemes, see the [DRF documentation](https://www.django-rest-framework.org/api-guide/versioning/).

---

## Implementation Source

All versioning classes are implemented in:
`/home/user/django-rest-framework/rest_framework/versioning.py`

See the source code for implementation details and customization options.
