# Router Types Reference

This document provides a detailed comparison of all router types in Django REST Framework.

## Table of Contents
- [BaseRouter](#baserouter)
- [SimpleRouter](#simplerouter)
- [DefaultRouter](#defaultrouter)
- [Feature Comparison](#feature-comparison)
- [Configuration Options](#configuration-options)

## BaseRouter

BaseRouter is the abstract base class that all routers inherit from. You typically don't use it directly, but understanding it helps when creating custom routers.

**Key features:**
- Registry system for storing ViewSet registrations
- `register()` method for adding ViewSets
- `get_urls()` abstract method that subclasses must implement
- Automatic basename generation from ViewSet queryset
- URL caching for performance

**Source code structure:**
```python
class BaseRouter:
    def __init__(self):
        self.registry = []  # List of (prefix, viewset, basename) tuples

    def register(self, prefix, viewset, basename=None):
        """Register a ViewSet with the router"""
        if basename is None:
            basename = self.get_default_basename(viewset)

        # Check for duplicate basename
        if self.is_already_registered(basename):
            raise ImproperlyConfigured(...)

        self.registry.append((prefix, viewset, basename))

        # Invalidate cached URLs
        if hasattr(self, '_urls'):
            del self._urls

    def get_default_basename(self, viewset):
        """Generate basename from viewset.queryset if available"""
        raise NotImplementedError('get_default_basename must be overridden')

    def get_urls(self):
        """Generate URL patterns from registered ViewSets"""
        raise NotImplementedError('get_urls must be overridden')

    @property
    def urls(self):
        """Cached URL patterns"""
        if not hasattr(self, '_urls'):
            self._urls = self.get_urls()
        return self._urls
```

**When you'll interact with BaseRouter:**
- Creating custom routers (inherit from BaseRouter or SimpleRouter)
- Understanding router internals for debugging
- Extending router functionality

## SimpleRouter

SimpleRouter is the basic router that generates standard CRUD URL patterns.

### URL Patterns Generated

For a ViewSet registered as `router.register(r'books', BookViewSet, basename='book')`:

| URL Pattern | Name | HTTP Methods | ViewSet Action | Description |
|-------------|------|--------------|----------------|-------------|
| `^books/$` | book-list | GET, POST | list, create | Collection endpoint |
| `^books/(?P<pk>[^/.]+)/$` | book-detail | GET, PUT, PATCH, DELETE | retrieve, update, partial_update, destroy | Instance endpoint |
| `^books/(?P<pk>[^/.]+)/{url_path}/$` | book-{url_name} | Varies | Custom @action | Detail-level custom actions |
| `^books/{url_path}/$` | book-{url_name} | Varies | Custom @action | List-level custom actions |

### Routes Configuration

SimpleRouter defines routes as namedtuples:

```python
from collections import namedtuple

Route = namedtuple('Route', ['url', 'mapping', 'name', 'detail', 'initkwargs'])
DynamicRoute = namedtuple('DynamicRoute', ['url', 'name', 'detail', 'initkwargs'])

class SimpleRouter(BaseRouter):
    routes = [
        # List route
        Route(
            url=r'^{prefix}{trailing_slash}$',
            mapping={
                'get': 'list',
                'post': 'create'
            },
            name='{basename}-list',
            detail=False,
            initkwargs={'suffix': 'List'}
        ),
        # Dynamically generated list routes (@action with detail=False)
        DynamicRoute(
            url=r'^{prefix}/{url_path}{trailing_slash}$',
            name='{basename}-{url_name}',
            detail=False,
            initkwargs={}
        ),
        # Detail route
        Route(
            url=r'^{prefix}/{lookup}{trailing_slash}$',
            mapping={
                'get': 'retrieve',
                'put': 'update',
                'patch': 'partial_update',
                'delete': 'destroy'
            },
            name='{basename}-detail',
            detail=True,
            initkwargs={'suffix': 'Instance'}
        ),
        # Dynamically generated detail routes (@action with detail=True)
        DynamicRoute(
            url=r'^{prefix}/{lookup}/{url_path}{trailing_slash}$',
            name='{basename}-{url_name}',
            detail=True,
            initkwargs={}
        ),
    ]
```

### Lookup Field Configuration

SimpleRouter supports custom lookup patterns:

```python
class BookViewSet(viewsets.ModelViewSet):
    queryset = Book.objects.all()
    serializer_class = BookSerializer

    # Default lookup
    lookup_field = 'pk'  # URL: /books/1/

    # Custom lookup field
    lookup_field = 'isbn'  # URL: /books/978-0-123456-78-9/
    lookup_url_kwarg = 'isbn'  # Optional: use different URL parameter name

    # Custom lookup regex (for regex paths)
    lookup_value_regex = '[0-9]{3}-[0-9]-[0-9]{6}-[0-9]{2}-[0-9]'

    # Custom lookup converter (for simple paths, Django 2.0+)
    lookup_value_converter = 'slug'  # Uses <slug:isbn> instead of regex
```

**Lookup converters available (when use_regex_path=False):**
- `int` - matches positive integers
- `str` - matches any non-empty string except '/'
- `slug` - matches ASCII letters, numbers, hyphens, underscores
- `uuid` - matches UUID format
- `path` - matches any string, including '/'

### Constructor Parameters

```python
SimpleRouter(trailing_slash=True, use_regex_path=True)
```

**Parameters:**

**trailing_slash** (bool, default=True):
- `True`: URLs end with `/` (e.g., `/books/`)
- `False`: URLs without trailing slash (e.g., `/books`)

```python
# With trailing slash (default)
router = SimpleRouter(trailing_slash=True)
# /books/
# /books/1/
# /books/1/activate/

# Without trailing slash
router = SimpleRouter(trailing_slash=False)
# /books
# /books/1
# /books/1/activate
```

**use_regex_path** (bool, default=True):
- `True`: Use `re_path()` with regex patterns (legacy, pre-Django 2.0)
- `False`: Use `path()` with path converters (Django 2.0+, cleaner)

```python
# Using regex paths (default, legacy)
router = SimpleRouter(use_regex_path=True)
# re_path(r'^books/(?P<pk>[^/.]+)/$', ...)

# Using simple paths (Django 2.0+, recommended)
router = SimpleRouter(use_regex_path=False)
# path('books/<str:pk>/', ...)
# path('books/<int:pk>/', ...)  # if lookup_value_converter='int'
```

### Methods

**get_default_basename(viewset)**
```python
def get_default_basename(self, viewset):
    """
    Auto-generate basename from viewset.queryset.model._meta.object_name
    """
    queryset = getattr(viewset, 'queryset', None)

    assert queryset is not None, (
        '`basename` argument not specified, and could not automatically '
        'determine the name from the viewset, as it does not have a '
        '`.queryset` attribute.'
    )

    return queryset.model._meta.object_name.lower()
```

Example:
```python
class BookViewSet(viewsets.ModelViewSet):
    queryset = Book.objects.all()
    # Auto-generated basename: 'book'

class AuthorViewSet(viewsets.ModelViewSet):
    queryset = Author.objects.all()
    # Auto-generated basename: 'author'
```

**get_lookup_regex(viewset, lookup_prefix='')**
```python
def get_lookup_regex(self, viewset, lookup_prefix=''):
    """
    Generate the lookup pattern for URL matching.
    Used for nested routers and custom lookup fields.
    """
    lookup_field = getattr(viewset, 'lookup_field', 'pk')
    lookup_url_kwarg = getattr(viewset, 'lookup_url_kwarg', None) or lookup_field

    if self._use_regex:
        lookup_value = getattr(viewset, 'lookup_value_regex', '[^/.]+')
        return f'(?P<{lookup_prefix}{lookup_url_kwarg}>{lookup_value})'
    else:
        lookup_value = getattr(viewset, 'lookup_value_converter', 'str')
        return f'<{lookup_value}:{lookup_prefix}{lookup_url_kwarg}>'
```

**get_routes(viewset)**
```python
def get_routes(self, viewset):
    """
    Augment self.routes with dynamically generated routes from @action decorators.
    Returns a list of Route namedtuples.
    """
    # Get standard actions (list, create, retrieve, etc.)
    known_actions = list(flatten([
        route.mapping.values()
        for route in self.routes
        if isinstance(route, Route)
    ]))

    # Get custom actions from @action decorators
    extra_actions = viewset.get_extra_actions()

    # Validate that custom actions don't conflict with standard actions
    not_allowed = [
        action.__name__
        for action in extra_actions
        if action.__name__ in known_actions
    ]
    if not_allowed:
        raise ImproperlyConfigured(
            f'Cannot use @action decorator on: {", ".join(not_allowed)}'
        )

    # Separate detail and list actions
    detail_actions = [action for action in extra_actions if action.detail]
    list_actions = [action for action in extra_actions if not action.detail]

    # Build final routes list
    routes = []
    for route in self.routes:
        if isinstance(route, DynamicRoute) and route.detail:
            routes += [self._get_dynamic_route(route, action) for action in detail_actions]
        elif isinstance(route, DynamicRoute) and not route.detail:
            routes += [self._get_dynamic_route(route, action) for action in list_actions]
        else:
            routes.append(route)

    return routes
```

**get_urls()**
```python
def get_urls(self):
    """
    Generate list of URL patterns from registered ViewSets.
    This is the main method that creates all the URLs.
    """
    ret = []

    for prefix, viewset, basename in self.registry:
        lookup = self.get_lookup_regex(viewset)
        routes = self.get_routes(viewset)

        for route in routes:
            # Only include actions that exist on the viewset
            mapping = self.get_method_map(viewset, route.mapping)
            if not mapping:
                continue

            # Build URL pattern
            regex = route.url.format(
                prefix=prefix,
                lookup=lookup,
                trailing_slash=self.trailing_slash
            )

            # Remove leading slash if no prefix (for app-level routers)
            if not prefix:
                if self._url_conf is path:
                    if regex[0] == '/':
                        regex = regex[1:]
                elif regex[:2] == '^/':
                    regex = '^' + regex[2:]

            # Create view with action mapping
            initkwargs = route.initkwargs.copy()
            initkwargs.update({
                'basename': basename,
                'detail': route.detail,
            })

            view = viewset.as_view(mapping, **initkwargs)
            name = route.name.format(basename=basename)
            ret.append(self._url_conf(regex, view, name=name))

    return ret
```

### When to Use SimpleRouter

**Best for:**
- Microservices and internal APIs
- When you don't need a browsable API root
- When you want minimal, clean URLs
- Production APIs where performance matters
- APIs consumed only by machines (not humans)

**Advantages:**
- Lightweight - no extra views
- Clean URL structure
- No format suffixes overhead
- Slightly faster URL resolution
- More predictable URL patterns

**Disadvantages:**
- No API root view for discoverability
- No format suffix support (.json, .api)
- Less helpful for API exploration during development

## DefaultRouter

DefaultRouter extends SimpleRouter with additional features for API discoverability and format suffixes.

### Additional Features

**1. API Root View**

DefaultRouter adds a root view that lists all registered endpoints:

```python
GET /api/
{
    "users": "http://localhost:8000/api/users/",
    "posts": "http://localhost:8000/api/posts/",
    "comments": "http://localhost:8000/api/comments/"
}
```

The root view is automatically generated from registered ViewSets:

```python
class DefaultRouter(SimpleRouter):
    include_root_view = True
    root_view_name = 'api-root'
    APIRootView = APIRootView  # The view class used

    def get_api_root_view(self, api_urls=None):
        """Return a basic root view listing all endpoints"""
        api_root_dict = {}
        list_name = self.routes[0].name  # e.g., '{basename}-list'

        for prefix, viewset, basename in self.registry:
            api_root_dict[prefix] = list_name.format(basename=basename)

        return self.APIRootView.as_view(api_root_dict=api_root_dict)
```

**2. Format Suffixes**

DefaultRouter automatically adds format suffix patterns:

```python
# Without format suffixes (SimpleRouter)
/api/users/
/api/users/1/

# With format suffixes (DefaultRouter)
/api/users/
/api/users.json
/api/users.api
/api/users/1/
/api/users/1.json
/api/users/1.api
```

This allows clients to request specific formats:
```bash
# Get JSON response
curl http://localhost:8000/api/users.json

# Get browsable API
curl http://localhost:8000/api/users.api
```

### Constructor Parameters

```python
DefaultRouter(
    trailing_slash=True,
    use_regex_path=True,
    root_renderers=None
)
```

**Additional parameters:**

**root_renderers** (list, default=None):
- Override renderer classes for the API root view
- If None, uses `settings.DEFAULT_RENDERER_CLASSES`

```python
from rest_framework.renderers import JSONRenderer, BrowsableAPIRenderer

# Only allow JSON for root view
router = DefaultRouter(root_renderers=[JSONRenderer])

# Custom renderers
router = DefaultRouter(root_renderers=[CustomRenderer])
```

### Configuration Attributes

```python
class DefaultRouter(SimpleRouter):
    # Enable/disable root view
    include_root_view = True

    # Enable/disable format suffixes (.json, .api)
    include_format_suffixes = True

    # URL name for root view
    root_view_name = 'api-root'

    # Classes used (can be overridden in subclass)
    APIRootView = APIRootView
    APISchemaView = SchemaView
    SchemaGenerator = SchemaGenerator
```

### Customizing the Root View

**Method 1: Configure existing root view**
```python
router = DefaultRouter()
router.root_view_name = 'my-api-root'  # Custom URL name
router.include_root_view = False  # Disable root view
```

**Method 2: Override APIRootView class**
```python
from rest_framework.routers import DefaultRouter, APIRootView
from rest_framework.response import Response

class CustomAPIRootView(APIRootView):
    """Custom root view with additional information"""

    def get(self, request, *args, **kwargs):
        ret = super().get(request, *args, **kwargs)
        # Add custom data
        ret.data['version'] = 'v1'
        ret.data['description'] = 'My API'
        return ret

class CustomRouter(DefaultRouter):
    APIRootView = CustomAPIRootView

router = CustomRouter()
```

**Method 3: Override get_api_root_view()**
```python
from rest_framework.decorators import api_view
from rest_framework.response import Response
from rest_framework.reverse import reverse

class CustomRouter(DefaultRouter):
    def get_api_root_view(self, api_urls=None):
        """Return completely custom root view"""

        @api_view(['GET'])
        def custom_root(request, format=None):
            return Response({
                'message': 'Welcome to my API',
                'version': '1.0',
                'endpoints': {
                    'users': reverse('user-list', request=request, format=format),
                    'posts': reverse('post-list', request=request, format=format),
                },
                'documentation': 'https://docs.example.com',
            })

        return custom_root

router = CustomRouter()
```

### get_urls() Implementation

```python
def get_urls(self):
    """
    Generate URL patterns including root view and format suffixes.
    """
    # Get standard URLs from SimpleRouter
    urls = super().get_urls()

    # Add API root view
    if self.include_root_view:
        view = self.get_api_root_view(api_urls=urls)
        root_url = path('', view, name=self.root_view_name)
        urls.append(root_url)

    # Add format suffix patterns (.json, .api)
    if self.include_format_suffixes:
        urls = format_suffix_patterns(urls)

    return urls
```

### When to Use DefaultRouter

**Best for:**
- Development environments
- Public APIs
- Browsable APIs for documentation
- When you want API discoverability
- APIs consumed by humans and machines

**Advantages:**
- API root view for easy navigation
- Format suffix support for content negotiation
- Better developer experience
- Helpful during development and testing
- Industry-standard pattern

**Disadvantages:**
- Slightly more overhead (root view, format suffixes)
- More complex URL patterns
- May expose internal structure in production

## Feature Comparison

| Feature | BaseRouter | SimpleRouter | DefaultRouter |
|---------|------------|--------------|---------------|
| **Basic Usage** |
| Register ViewSets | ✅ | ✅ | ✅ |
| Auto-generate CRUD URLs | ❌ | ✅ | ✅ |
| Support @action decorator | ❌ | ✅ | ✅ |
| Custom lookup fields | ❌ | ✅ | ✅ |
| **URL Patterns** |
| List endpoint (GET/POST) | ❌ | ✅ | ✅ |
| Detail endpoint (GET/PUT/PATCH/DELETE) | ❌ | ✅ | ✅ |
| Custom actions (detail=True) | ❌ | ✅ | ✅ |
| Custom actions (detail=False) | ❌ | ✅ | ✅ |
| API root view | ❌ | ❌ | ✅ |
| Format suffixes (.json, .api) | ❌ | ❌ | ✅ |
| **Configuration** |
| trailing_slash option | ❌ | ✅ | ✅ |
| use_regex_path option | ❌ | ✅ | ✅ |
| Custom root renderers | ❌ | ❌ | ✅ |
| Disable root view | N/A | N/A | ✅ |
| Disable format suffixes | N/A | N/A | ✅ |
| **Performance** |
| Minimal overhead | ✅ | ✅ | ⚠️ (slight overhead) |
| URL caching | ✅ | ✅ | ✅ |
| **Use Cases** |
| Base for custom routers | ✅ | ⚠️ (can also extend) | ⚠️ (can also extend) |
| Production APIs | ❌ | ✅ | ✅ |
| Development APIs | ❌ | ⚠️ | ✅ (recommended) |
| Microservices | ❌ | ✅ | ⚠️ |
| Public APIs | ❌ | ⚠️ | ✅ (recommended) |

## Configuration Options

### Trailing Slash Configuration

```python
# Default: URLs end with /
router = DefaultRouter()  # trailing_slash=True
# /api/users/
# /api/users/1/

# No trailing slash
router = DefaultRouter(trailing_slash=False)
# /api/users
# /api/users/1

# Per-Django settings (affects redirect behavior)
# settings.py
APPEND_SLASH = True  # Redirect /api/users to /api/users/
```

**Best practices:**
- Use trailing slashes (default) for most APIs
- Match your Django APPEND_SLASH setting
- Be consistent across your entire API
- Document your choice for API consumers

### Path Type Configuration

```python
# Legacy: Regex paths (Django < 2.0 style)
router = SimpleRouter(use_regex_path=True)
# re_path(r'^books/(?P<pk>[^/.]+)/$', ...)

# Modern: Simple paths (Django 2.0+, recommended)
router = SimpleRouter(use_regex_path=False)
# path('books/<str:pk>/', ...)

# With custom lookup converter
class BookViewSet(viewsets.ModelViewSet):
    queryset = Book.objects.all()
    lookup_field = 'pk'
    lookup_value_converter = 'int'  # <int:pk> instead of <str:pk>
```

**When to use each:**
- `use_regex_path=False` (recommended): Cleaner, easier to read, Django 2.0+
- `use_regex_path=True`: Complex patterns, legacy compatibility, custom regex

### Format Suffix Configuration

```python
# Default: Format suffixes enabled
router = DefaultRouter()
router.include_format_suffixes = True
# /api/users/
# /api/users.json
# /api/users.api

# Disable format suffixes
router = DefaultRouter()
router.include_format_suffixes = False
# /api/users/ (only)

# Custom format_suffix_patterns (advanced)
from rest_framework.urlpatterns import format_suffix_patterns

urls = router.urls
urls = format_suffix_patterns(urls, allowed=['json', 'xml'])
```

### Root View Configuration

```python
# Default: Root view enabled
router = DefaultRouter()
router.include_root_view = True

# Disable root view (no GET /)
router = DefaultRouter()
router.include_root_view = False

# Custom root view name
router = DefaultRouter()
router.root_view_name = 'custom-root'

# Custom root renderers (JSON only)
from rest_framework.renderers import JSONRenderer
router = DefaultRouter(root_renderers=[JSONRenderer])
```

### Complete Configuration Example

```python
from rest_framework.routers import DefaultRouter
from rest_framework.renderers import JSONRenderer, BrowsableAPIRenderer

# Create router with all options
router = DefaultRouter(
    trailing_slash=True,          # URLs end with /
    use_regex_path=False,         # Use modern path() patterns
    root_renderers=[              # Custom root view renderers
        JSONRenderer,
        BrowsableAPIRenderer,
    ]
)

# Configure router attributes
router.include_root_view = True
router.include_format_suffixes = True
router.root_view_name = 'api-root'

# Register ViewSets
router.register(r'users', UserViewSet, basename='user')
router.register(r'posts', PostViewSet, basename='post')

# Use in URLconf
from django.urls import path, include

urlpatterns = [
    path('api/v1/', include(router.urls)),
]
```

## Summary

**Choose SimpleRouter when:**
- You need clean, minimal URLs
- You don't need an API root view
- You're building microservices or internal APIs
- Performance is critical
- You don't need format suffixes

**Choose DefaultRouter when:**
- You want a browsable API (development or production)
- You need an API root view for discoverability
- You want format suffixes (.json, .api)
- You're building public APIs
- Developer experience matters

**Extend BaseRouter when:**
- You need completely custom URL patterns
- Existing routers don't fit your use case
- You're integrating with legacy URL structures
- You need specialized routing logic

Both SimpleRouter and DefaultRouter are excellent choices for most DRF projects. DefaultRouter is the most common choice (80%+ of projects) because of its helpful features during development and in production.
