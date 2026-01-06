# DRF Versioning Schemes - Complete Reference

This document provides detailed information about all five versioning schemes available in Django REST Framework.

## Table of Contents

1. [URLPathVersioning](#urlpathversioning)
2. [AcceptHeaderVersioning](#acceptheaderversioning)
3. [NamespaceVersioning](#namespaceversioning)
4. [QueryParameterVersioning](#queryparameterversioning)
5. [HostNameVersioning](#hostnameversioning)
6. [Comparison Matrix](#comparison-matrix)

---

## URLPathVersioning

**Most Common Choice** - Version is included in the URL path.

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
router_v1.register(r'books', views.BookViewSetV1)
router_v1.register(r'authors', views.AuthorViewSetV1)

# V2 Router
router_v2 = routers.DefaultRouter()
router_v2.register(r'books', views.BookViewSetV2)
router_v2.register(r'authors', views.AuthorViewSetV2)

urlpatterns = [
    path('api/v1/', include(router_v1.urls)),
    path('api/v2/', include(router_v2.urls)),
]
```

### Accessing Version in Views

```python
class BookViewSet(viewsets.ModelViewSet):
    def list(self, request, *args, **kwargs):
        version = request.version  # 'v1', 'v2', etc.
        print(f"Request version: {version}")
        return super().list(request, *args, **kwargs)
```

### Pros and Cons

**Advantages:**
- ✓ Clear and visible in URLs
- ✓ Easy to test in browsers
- ✓ Works everywhere (no special headers needed)
- ✓ Excellent for documentation
- ✓ Easy to cache (different URLs)
- ✓ Bookmark-friendly

**Disadvantages:**
- ✗ URL changes with each version
- ✗ Can complicate URL routing
- ✗ Verbose for many endpoints

**Best For:** Public APIs, documentation-heavy APIs, browser-based testing

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
- ✓ RESTful and follows HTTP standards
- ✓ URLs stay clean and version-agnostic
- ✓ Better semantic separation
- ✓ Professional/enterprise standard
- ✓ Single URL for all versions

**Disadvantages:**
- ✗ Harder to test in browsers
- ✗ Not visible in URL (less transparent)
- ✗ Some caching layers ignore headers
- ✗ Requires client header control

**Best For:** Enterprise APIs, mobile apps, APIs with sophisticated clients

---

## NamespaceVersioning

**Django-Native Approach** - Uses Django's URL namespace feature.

### How It Works

Version is determined by the URL namespace in Django's URL configuration.

```
GET /api/v1/books/  (namespace: 'v1')
GET /api/v2/books/  (namespace: 'v2')
```

### Configuration

```python
# settings.py
REST_FRAMEWORK = {
    'DEFAULT_VERSIONING_CLASS': 'rest_framework.versioning.NamespaceVersioning',
    'DEFAULT_VERSION': 'v1',
    'ALLOWED_VERSIONS': ['v1', 'v2', 'v3'],
}
```

### URL Configuration

Organize views in separate modules per version:

```
myapp/
├── views/
│   ├── __init__.py
│   ├── v1.py
│   └── v2.py
```

**myapp/views/v1.py:**
```python
from rest_framework import viewsets
from myapp.models import Book
from myapp.serializers.v1 import BookSerializer

class BookViewSet(viewsets.ModelViewSet):
    queryset = Book.objects.all()
    serializer_class = BookSerializer
```

**myapp/views/v2.py:**
```python
from rest_framework import viewsets
from myapp.models import Book
from myapp.serializers.v2 import BookSerializer

class BookViewSet(viewsets.ModelViewSet):
    queryset = Book.objects.all()
    serializer_class = BookSerializer
```

**myapp/urls.py:**
```python
from django.urls import path, include
from rest_framework import routers
from myapp.views import v1, v2

# V1 URLs
router_v1 = routers.DefaultRouter()
router_v1.register(r'books', v1.BookViewSet)

v1_urls = (router_v1.urls, 'v1')

# V2 URLs
router_v2 = routers.DefaultRouter()
router_v2.register(r'books', v2.BookViewSet)

v2_urls = (router_v2.urls, 'v2')

# Main URLs
urlpatterns = [
    path('api/v1/', include(v1_urls)),
    path('api/v2/', include(v2_urls)),
]
```

### Reverse URL Generation

```python
from rest_framework.reverse import reverse

# In a view
url = reverse('book-list', request=request)
# Automatically includes namespace: /api/v1/books/ or /api/v2/books/
```

### Pros and Cons

**Advantages:**
- ✓ Uses Django's built-in namespace system
- ✓ Clean code organization (views by version)
- ✓ Easy to maintain separate version modules
- ✓ Familiar to Django developers
- ✓ Clear separation of concerns

**Disadvantages:**
- ✗ More boilerplate code
- ✗ Requires careful URL configuration
- ✗ Can lead to code duplication
- ✗ More file/module management

**Best For:** Large projects, teams familiar with Django, complex version differences

---

## QueryParameterVersioning

**Simple Approach** - Version is a query string parameter.

### How It Works

Version is passed as a query parameter in the URL.

```
GET /api/books/?version=v1
GET /api/books/?version=v2
```

### Configuration

```python
# settings.py
REST_FRAMEWORK = {
    'DEFAULT_VERSIONING_CLASS': 'rest_framework.versioning.QueryParameterVersioning',
    'DEFAULT_VERSION': 'v1',
    'ALLOWED_VERSIONS': ['v1', 'v2', 'v3'],
    'VERSION_PARAM': 'version',  # Query parameter name
}
```

### URL Configuration

Simple, clean URL patterns:

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
# Version 1
curl "http://localhost:8000/api/books/?version=v1"

# Version 2
curl "http://localhost:8000/api/books/?version=v2"

# Default version (no parameter)
curl http://localhost:8000/api/books/
```

**JavaScript:**
```javascript
fetch('http://localhost:8000/api/books/?version=v2')
```

### Combining with Other Query Parameters

```python
# Works seamlessly with filtering, pagination, etc.
GET /api/books/?version=v2&search=django&page=2
```

### Pros and Cons

**Advantages:**
- ✓ Extremely simple to implement
- ✓ Easy to test (just change URL)
- ✓ Works everywhere
- ✓ No special client requirements
- ✓ Base URL stays consistent

**Disadvantages:**
- ✗ Clutters URLs with version parameter
- ✗ Not considered "RESTful" by purists
- ✗ Query params may be logged/cached unexpectedly
- ✗ Less clear than path-based versioning

**Best For:** Internal APIs, quick prototypes, simple applications

---

## HostNameVersioning

**Infrastructure Approach** - Version is in the hostname/subdomain.

### How It Works

Different versions are hosted on different subdomains.

```
GET https://v1.api.example.com/books/
GET https://v2.api.example.com/books/
```

### Configuration

```python
# settings.py
REST_FRAMEWORK = {
    'DEFAULT_VERSIONING_CLASS': 'rest_framework.versioning.HostNameVersioning',
    'DEFAULT_VERSION': 'v1',
    'ALLOWED_VERSIONS': ['v1', 'v2', 'v3'],
}

# Allow all subdomains
ALLOWED_HOSTS = [
    'v1.api.example.com',
    'v2.api.example.com',
    'v3.api.example.com',
]
```

### URL Configuration

```python
from django.urls import path, include
from rest_framework import routers
from myapp.views import BookViewSet

router = routers.DefaultRouter()
router.register(r'books', BookViewSet)

urlpatterns = [
    path('', include(router.urls)),
]
```

### Infrastructure Setup

Requires DNS configuration:

```
# DNS records
v1.api.example.com  CNAME  api-v1.example.com
v2.api.example.com  CNAME  api-v2.example.com
```

### Nginx Configuration Example

```nginx
server {
    server_name v1.api.example.com;

    location / {
        proxy_pass http://127.0.0.1:8001;  # V1 instance
    }
}

server {
    server_name v2.api.example.com;

    location / {
        proxy_pass http://127.0.0.1:8002;  # V2 instance
    }
}
```

### Pros and Cons

**Advantages:**
- ✓ Complete separation of versions
- ✓ Can run different codebases
- ✓ Easy to route/load balance by version
- ✓ Excellent caching (different hosts)
- ✓ Can scale versions independently

**Disadvantages:**
- ✗ Requires DNS management
- ✗ SSL certificate complexity (wildcard needed)
- ✗ More infrastructure overhead
- ✗ CORS configuration required
- ✗ Deployment complexity

**Best For:** Microservices, large-scale APIs, separate deployment pipelines

---

## Comparison Matrix

| Feature | URLPath | AcceptHeader | Namespace | QueryParam | HostName |
|---------|---------|--------------|-----------|------------|----------|
| **Visibility** | High | Low | High | Medium | High |
| **Browser Testing** | Easy | Hard | Easy | Easy | Medium |
| **RESTful** | Medium | High | Medium | Low | High |
| **Caching** | Excellent | Medium | Excellent | Medium | Excellent |
| **Setup Complexity** | Low | Low | Medium | Low | High |
| **Client Complexity** | Low | Medium | Low | Low | Low |
| **URL Cleanliness** | Medium | High | Medium | Low | High |
| **Documentation** | Easy | Medium | Easy | Easy | Medium |
| **Mobile Apps** | Good | Excellent | Good | Good | Medium |
| **Bookmarkable** | Yes | No | Yes | Yes* | Yes |
| **Infrastructure** | Simple | Simple | Simple | Simple | Complex |

*Bookmarkable but ugly with query params

## Choosing the Right Scheme

### Use URLPathVersioning if:
- You want maximum clarity and visibility
- You're building a public API
- You need easy browser testing
- Documentation is important

### Use AcceptHeaderVersioning if:
- You want a RESTful approach
- Your clients control HTTP headers
- URL cleanliness matters
- You're building for mobile/enterprise

### Use NamespaceVersioning if:
- You have a large Django project
- You want separate view modules per version
- Your team prefers Django-native solutions
- Version differences are significant

### Use QueryParameterVersioning if:
- You need something simple and quick
- Your clients can't control headers
- It's an internal/prototype API
- You want minimal configuration

### Use HostNameVersioning if:
- You have microservices architecture
- Versions need complete separation
- You can manage DNS/infrastructure
- You need independent scaling per version

## Implementation Source

All versioning classes are implemented in:
`/home/user/django-rest-framework/rest_framework/versioning.py`

See the source code for implementation details and customization options.
