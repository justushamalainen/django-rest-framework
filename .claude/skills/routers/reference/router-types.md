# Router Types Reference

Django REST Framework provides two main router types: **DefaultRouter** and **SimpleRouter**.

## DefaultRouter

**Use this for 95% of projects.** DefaultRouter provides everything you need for a production-ready API.

### What It Provides

```python
from rest_framework.routers import DefaultRouter

router = DefaultRouter()
router.register(r'books', BookViewSet, basename='book')
```

**Generated URLs:**
- Standard CRUD endpoints (list, create, retrieve, update, destroy)
- Custom @action endpoints
- **API root view** at `/` that lists all endpoints
- **Format suffix support** (.json, .api)

### API Root View

The root view provides API discoverability:

```bash
GET /api/

{
    "books": "http://localhost:8000/api/books/",
    "authors": "http://localhost:8000/api/authors/",
    "publishers": "http://localhost:8000/api/publishers/"
}
```

This is incredibly helpful for:
- API exploration during development
- Auto-generated API documentation
- Client discovery of available endpoints
- Human-friendly browsable API

### Format Suffixes

DefaultRouter adds format suffix URLs automatically:

```bash
# Regular URLs
GET /api/books/
GET /api/books/1/

# With format suffixes
GET /api/books.json      # Force JSON response
GET /api/books.api       # Force browsable API
GET /api/books/1.json    # Force JSON for detail
```

### Configuration

```python
# Basic configuration
router = DefaultRouter()

# Disable trailing slashes
router = DefaultRouter(trailing_slash=False)
# URLs: /api/books instead of /api/books/

# Custom root renderers (JSON only)
from rest_framework.renderers import JSONRenderer
router = DefaultRouter(root_renderers=[JSONRenderer])

# Disable root view (not recommended)
router = DefaultRouter()
router.include_root_view = False

# Disable format suffixes (not recommended)
router = DefaultRouter()
router.include_format_suffixes = False
```

### Complete Example

```python
from django.urls import path, include
from rest_framework.routers import DefaultRouter
from rest_framework.renderers import JSONRenderer, BrowsableAPIRenderer

# Create router with options
router = DefaultRouter(
    trailing_slash=True,          # URLs end with /
    use_regex_path=False,         # Use modern path() patterns (Django 2.0+)
    root_renderers=[              # Custom root renderers
        JSONRenderer,
        BrowsableAPIRenderer,
    ]
)

# Configure attributes
router.include_root_view = True
router.include_format_suffixes = True
router.root_view_name = 'api-root'

# Register ViewSets
router.register(r'books', BookViewSet, basename='book')
router.register(r'authors', AuthorViewSet, basename='author')
router.register(r'publishers', PublisherViewSet, basename='publisher')

# Include in URLconf
urlpatterns = [
    path('api/', include(router.urls)),
]
```

### Customizing the Root View

Add custom information to the API root:

```python
from rest_framework.routers import DefaultRouter, APIRootView
from rest_framework.response import Response

class CustomAPIRootView(APIRootView):
    def get(self, request, *args, **kwargs):
        ret = super().get(request, *args, **kwargs)
        ret.data['version'] = '1.0'
        ret.data['description'] = 'My API'
        ret.data['documentation'] = 'https://docs.example.com'
        return ret

class CustomRouter(DefaultRouter):
    APIRootView = CustomAPIRootView

router = CustomRouter()
```

### When to Use DefaultRouter

✅ **Use DefaultRouter when:**
- Building any production API (most common choice)
- You want a browsable API
- You need API discoverability
- You're building a public API
- Developer experience matters
- You want format suffixes
- You're not sure which to use (default to this!)

## SimpleRouter

**Only use if you specifically don't want an API root view.**

SimpleRouter provides the same CRUD URL generation as DefaultRouter, but **without** the API root view and format suffixes.

### What It Provides

```python
from rest_framework.routers import SimpleRouter

router = SimpleRouter()
router.register(r'books', BookViewSet, basename='book')
```

**Generated URLs:**
- Standard CRUD endpoints (list, create, retrieve, update, destroy)
- Custom @action endpoints
- **No API root view**
- **No format suffixes**

### When to Use SimpleRouter

✅ **Use SimpleRouter when:**
- You specifically don't want an API root view
- You're building a microservice with a single resource
- You want absolutely minimal URLs
- You're integrating with a legacy system that can't handle the root view

❌ **Don't use SimpleRouter if:**
- You're not sure (use DefaultRouter instead)
- You might want an API root later
- You want format suffixes

### Example

```python
from rest_framework.routers import SimpleRouter

router = SimpleRouter()
router.register(r'books', BookViewSet)

urlpatterns = [
    path('api/', include(router.urls)),
]

# Generated URLs:
# GET/POST /api/books/
# GET/PUT/PATCH/DELETE /api/books/{pk}/
# (No GET /api/ endpoint)
```

## Quick Decision Guide

**Choose DefaultRouter** → 95% of projects

**Choose SimpleRouter** → Only if you specifically don't want an API root view

## Summary

Both routers generate the same CRUD URLs. The only differences:

| Feature | SimpleRouter | DefaultRouter |
|---------|-------------|---------------|
| CRUD URLs | ✅ | ✅ |
| @action support | ✅ | ✅ |
| API root view | ❌ | ✅ |
| Format suffixes | ❌ | ✅ |
| Use case | Minimal APIs | Most APIs (default choice) |

**Recommendation:** Use DefaultRouter unless you have a specific reason not to.
