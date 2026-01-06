# Custom Routers Reference

This document covers creating custom router classes with specialized URL patterns and routing logic.

## Table of Contents
- [When to Create a Custom Router](#when-to-create-a-custom-router)
- [Extending SimpleRouter](#extending-simplerouter)
- [Extending DefaultRouter](#extending-defaultrouter)
- [Custom Route Patterns](#custom-route-patterns)
- [Advanced Customizations](#advanced-customizations)
- [Real-World Examples](#real-world-examples)

## When to Create a Custom Router

Create a custom router when you need:

1. **Non-standard URL patterns** - URLs that don't fit REST conventions
2. **Additional routes** - Extra endpoints beyond standard CRUD
3. **Legacy URL compatibility** - Match existing URL structures
4. **Special URL formatting** - Custom prefixes, suffixes, or patterns
5. **Domain-specific conventions** - Industry-specific URL patterns
6. **Custom action handling** - Specialized @action behavior
7. **Nested resources** - Parent-child relationships in URLs

**Don't create a custom router when:**
- You only need a few custom endpoints (use @action instead)
- You have non-RESTful operations (use regular views/viewsets)
- Your customizations are ViewSet-specific (customize the ViewSet instead)

## Extending SimpleRouter

The most common approach is extending SimpleRouter to add or modify routes.

### Basic Extension Pattern

```python
from rest_framework.routers import SimpleRouter, Route

class CustomRouter(SimpleRouter):
    """
    Custom router with additional routes.
    """
    routes = [
        # Include all standard SimpleRouter routes
        *SimpleRouter.routes,

        # Add your custom routes
        Route(
            url=r'^{prefix}/custom-action{trailing_slash}$',
            mapping={'get': 'custom_action'},
            name='{basename}-custom-action',
            detail=False,
            initkwargs={}
        ),
    ]
```

### Example 1: Add a "Schema" Endpoint

Add a `/schema/` endpoint to every registered ViewSet:

```python
from rest_framework.routers import SimpleRouter, Route

class SchemaRouter(SimpleRouter):
    """
    Router that adds a /schema/ endpoint to each ViewSet.
    """
    routes = [
        # Standard routes
        *SimpleRouter.routes,

        # Schema route
        Route(
            url=r'^{prefix}/schema{trailing_slash}$',
            mapping={'get': 'get_schema'},
            name='{basename}-schema',
            detail=False,
            initkwargs={'suffix': 'Schema'}
        ),
    ]

# ViewSet implementation
class UserViewSet(viewsets.ModelViewSet):
    queryset = User.objects.all()
    serializer_class = UserSerializer

    def get_schema(self, request):
        """Return schema information for this endpoint"""
        return Response({
            'model': 'User',
            'fields': ['id', 'username', 'email'],
            'actions': ['list', 'create', 'retrieve', 'update', 'destroy'],
        })

# Usage
router = SchemaRouter()
router.register(r'users', UserViewSet)

# Generated URLs:
# GET /users/schema/  -> calls get_schema()
```

### Example 2: Add "Search" Endpoint

Add a `/search/` endpoint for text search:

```python
from rest_framework.routers import SimpleRouter, Route

class SearchRouter(SimpleRouter):
    """
    Router that adds a search endpoint to each ViewSet.
    """
    routes = [
        # Standard list route
        Route(
            url=r'^{prefix}{trailing_slash}$',
            mapping={'get': 'list', 'post': 'create'},
            name='{basename}-list',
            detail=False,
            initkwargs={'suffix': 'List'}
        ),
        # CUSTOM: Search route (before dynamic routes)
        Route(
            url=r'^{prefix}/search{trailing_slash}$',
            mapping={'get': 'search'},
            name='{basename}-search',
            detail=False,
            initkwargs={'suffix': 'Search'}
        ),
        # Dynamic list routes (@action decorator)
        SimpleRouter.routes[1],

        # Standard detail route
        SimpleRouter.routes[2],

        # Dynamic detail routes
        SimpleRouter.routes[3],
    ]

# ViewSet implementation
from django.db.models import Q

class BookViewSet(viewsets.ModelViewSet):
    queryset = Book.objects.all()
    serializer_class = BookSerializer

    def search(self, request):
        """
        Search books by title or author name.
        GET /books/search/?q=django
        """
        query = request.query_params.get('q', '')
        books = self.queryset.filter(
            Q(title__icontains=query) | Q(author__name__icontains=query)
        )
        serializer = self.get_serializer(books, many=True)
        return Response(serializer.data)

# Usage
router = SearchRouter()
router.register(r'books', BookViewSet)

# Generated URLs:
# GET /books/search/?q=django  -> calls search()
```

### Example 3: Add "Bulk Operations" Endpoints

Add endpoints for bulk create, update, and delete:

```python
from rest_framework.routers import SimpleRouter, Route

class BulkRouter(SimpleRouter):
    """
    Router that adds bulk operation endpoints.
    """
    routes = [
        # Standard routes
        *SimpleRouter.routes,

        # Bulk operations
        Route(
            url=r'^{prefix}/bulk{trailing_slash}$',
            mapping={
                'post': 'bulk_create',
                'put': 'bulk_update',
                'delete': 'bulk_destroy',
            },
            name='{basename}-bulk',
            detail=False,
            initkwargs={'suffix': 'Bulk'}
        ),
    ]

# ViewSet implementation
class BookViewSet(viewsets.ModelViewSet):
    queryset = Book.objects.all()
    serializer_class = BookSerializer

    def bulk_create(self, request):
        """
        Create multiple books at once.
        POST /books/bulk/ with [{"title": "..."}, {"title": "..."}]
        """
        serializer = self.get_serializer(data=request.data, many=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data, status=status.HTTP_201_CREATED)

    def bulk_update(self, request):
        """
        Update multiple books at once.
        PUT /books/bulk/ with [{"id": 1, "title": "..."}, ...]
        """
        instances = []
        for item in request.data:
            pk = item.pop('id')
            instance = self.get_queryset().get(pk=pk)
            serializer = self.get_serializer(instance, data=item, partial=True)
            serializer.is_valid(raise_exception=True)
            serializer.save()
            instances.append(serializer.data)
        return Response(instances)

    def bulk_destroy(self, request):
        """
        Delete multiple books at once.
        DELETE /books/bulk/ with {"ids": [1, 2, 3]}
        """
        ids = request.data.get('ids', [])
        count = self.get_queryset().filter(pk__in=ids).delete()
        return Response({'deleted': count[0]}, status=status.HTTP_204_NO_CONTENT)

# Usage
router = BulkRouter()
router.register(r'books', BookViewSet)

# Generated URLs:
# POST   /books/bulk/  -> bulk_create()
# PUT    /books/bulk/  -> bulk_update()
# DELETE /books/bulk/  -> bulk_destroy()
```

## Extending DefaultRouter

When extending DefaultRouter, you inherit both the root view and format suffixes.

### Example 4: Custom Root View with Metadata

```python
from rest_framework.routers import DefaultRouter, APIRootView
from rest_framework.response import Response
from rest_framework.reverse import reverse

class MetadataAPIRootView(APIRootView):
    """
    Custom root view with API metadata.
    """
    def get(self, request, *args, **kwargs):
        ret = super().get(request, *args, **kwargs)

        # Add metadata
        ret.data = {
            'version': 'v1',
            'description': 'My API',
            'authentication': 'Token-based',
            'endpoints': ret.data,
            'documentation': request.build_absolute_uri('/docs/'),
        }
        return ret

class MetadataRouter(DefaultRouter):
    """
    DefaultRouter with custom root view.
    """
    APIRootView = MetadataAPIRootView

# Usage
router = MetadataRouter()
router.register(r'users', UserViewSet)
router.register(r'posts', PostViewSet)

# GET / returns:
# {
#     "version": "v1",
#     "description": "My API",
#     "authentication": "Token-based",
#     "endpoints": {
#         "users": "http://localhost:8000/users/",
#         "posts": "http://localhost:8000/posts/"
#     },
#     "documentation": "http://localhost:8000/docs/"
# }
```

### Example 5: Versioned Router

Create a router that adds version prefix to all URLs:

```python
from rest_framework.routers import DefaultRouter

class VersionedRouter(DefaultRouter):
    """
    Router that adds API version to all URLs.
    """
    def __init__(self, version='v1', *args, **kwargs):
        self.version = version
        self.root_view_name = f'api-root-{version}'
        super().__init__(*args, **kwargs)

    def get_urls(self):
        """Prefix all URLs with version"""
        urls = super().get_urls()

        # Update URL patterns to include version
        # (This is a simplified example; real implementation would be more complex)
        return urls

# Usage
router_v1 = VersionedRouter(version='v1')
router_v1.register(r'users', UserV1ViewSet)

router_v2 = VersionedRouter(version='v2')
router_v2.register(r'users', UserV2ViewSet)

urlpatterns = [
    path('api/v1/', include(router_v1.urls)),
    path('api/v2/', include(router_v2.urls)),
]
```

## Custom Route Patterns

### Understanding Route and DynamicRoute

```python
from collections import namedtuple

# Static route (defined in router)
Route = namedtuple('Route', ['url', 'mapping', 'name', 'detail', 'initkwargs'])

# Dynamic route (generated from @action decorators)
DynamicRoute = namedtuple('DynamicRoute', ['url', 'name', 'detail', 'initkwargs'])
```

**Route fields:**
- `url`: URL pattern with placeholders ({prefix}, {lookup}, {trailing_slash})
- `mapping`: Dict mapping HTTP methods to ViewSet actions
- `name`: URL name pattern (e.g., '{basename}-list')
- `detail`: Boolean - whether this is a detail route (requires pk)
- `initkwargs`: Additional kwargs passed to ViewSet.as_view()

### Example 6: Add "Count" Endpoint

Add `/count/` to return the total count:

```python
from rest_framework.routers import SimpleRouter, Route

class CountRouter(SimpleRouter):
    """
    Router that adds a count endpoint.
    """
    routes = [
        # Standard list route
        Route(
            url=r'^{prefix}{trailing_slash}$',
            mapping={'get': 'list', 'post': 'create'},
            name='{basename}-list',
            detail=False,
            initkwargs={'suffix': 'List'}
        ),
        # COUNT ROUTE - must come before dynamic routes
        Route(
            url=r'^{prefix}/count{trailing_slash}$',
            mapping={'get': 'count'},
            name='{basename}-count',
            detail=False,
            initkwargs={'suffix': 'Count'}
        ),
        # Include remaining routes
        *SimpleRouter.routes[1:],
    ]

# ViewSet implementation
class BookViewSet(viewsets.ModelViewSet):
    queryset = Book.objects.all()
    serializer_class = BookSerializer

    def count(self, request):
        """
        Return the count of books.
        GET /books/count/
        """
        count = self.get_queryset().count()
        return Response({'count': count})

# Usage
router = CountRouter()
router.register(r'books', BookViewSet)

# Generated URL:
# GET /books/count/  -> returns {"count": 42}
```

### Example 7: Add "Export" Endpoint with Multiple Formats

```python
from rest_framework.routers import SimpleRouter, Route

class ExportRouter(SimpleRouter):
    """
    Router that adds export endpoints.
    """
    routes = [
        *SimpleRouter.routes,

        # Export routes
        Route(
            url=r'^{prefix}/export{trailing_slash}$',
            mapping={'get': 'export'},
            name='{basename}-export',
            detail=False,
            initkwargs={'suffix': 'Export'}
        ),
        Route(
            url=r'^{prefix}/export/csv{trailing_slash}$',
            mapping={'get': 'export_csv'},
            name='{basename}-export-csv',
            detail=False,
            initkwargs={'suffix': 'ExportCSV'}
        ),
        Route(
            url=r'^{prefix}/export/excel{trailing_slash}$',
            mapping={'get': 'export_excel'},
            name='{basename}-export-excel',
            detail=False,
            initkwargs={'suffix': 'ExportExcel'}
        ),
    ]

# ViewSet implementation
import csv
from django.http import HttpResponse

class BookViewSet(viewsets.ModelViewSet):
    queryset = Book.objects.all()
    serializer_class = BookSerializer

    def export(self, request):
        """Export metadata"""
        return Response({
            'formats': ['csv', 'excel'],
            'urls': {
                'csv': reverse('book-export-csv', request=request),
                'excel': reverse('book-export-excel', request=request),
            }
        })

    def export_csv(self, request):
        """Export as CSV"""
        response = HttpResponse(content_type='text/csv')
        response['Content-Disposition'] = 'attachment; filename="books.csv"'

        writer = csv.writer(response)
        writer.writerow(['ID', 'Title', 'Author', 'ISBN'])
        for book in self.get_queryset():
            writer.writerow([book.id, book.title, book.author.name, book.isbn])

        return response

    def export_excel(self, request):
        """Export as Excel (simplified)"""
        # In real implementation, use openpyxl or xlsxwriter
        return Response({'message': 'Excel export not implemented'})

# Usage
router = ExportRouter()
router.register(r'books', BookViewSet)

# Generated URLs:
# GET /books/export/       -> export metadata
# GET /books/export/csv/   -> download CSV
# GET /books/export/excel/ -> download Excel
```

## Advanced Customizations

### Example 8: Override get_lookup_regex for Custom Patterns

```python
from rest_framework.routers import SimpleRouter

class SlugRouter(SimpleRouter):
    """
    Router that uses slug instead of pk by default.
    """
    def get_lookup_regex(self, viewset, lookup_prefix=''):
        """
        Default to slug lookup instead of pk.
        """
        lookup_field = getattr(viewset, 'lookup_field', 'slug')  # Changed default
        lookup_url_kwarg = getattr(viewset, 'lookup_url_kwarg', None) or lookup_field

        if self._use_regex:
            # Slug pattern: alphanumeric, hyphens, underscores
            lookup_value = getattr(
                viewset,
                'lookup_value_regex',
                '[-a-zA-Z0-9_]+'  # Changed default pattern
            )
            return f'(?P<{lookup_prefix}{lookup_url_kwarg}>{lookup_value})'
        else:
            lookup_value = getattr(viewset, 'lookup_value_converter', 'slug')
            return f'<{lookup_value}:{lookup_prefix}{lookup_url_kwarg}>'

# ViewSet (no need to specify lookup_field if using slug)
class ArticleViewSet(viewsets.ModelViewSet):
    queryset = Article.objects.all()
    serializer_class = ArticleSerializer
    # lookup_field = 'slug'  # Not needed with SlugRouter!

# Usage
router = SlugRouter()
router.register(r'articles', ArticleViewSet)

# Generated URLs:
# GET /articles/my-article-slug/
```

### Example 9: Add "History" Route for Audited Models

```python
from rest_framework.routers import SimpleRouter, Route

class HistoryRouter(SimpleRouter):
    """
    Router that adds a history endpoint for audited models.
    """
    routes = [
        *SimpleRouter.routes,

        # History route
        Route(
            url=r'^{prefix}/{lookup}/history{trailing_slash}$',
            mapping={'get': 'history'},
            name='{basename}-history',
            detail=True,
            initkwargs={'suffix': 'History'}
        ),
    ]

# ViewSet implementation (using django-simple-history)
from simple_history.models import HistoricalRecords

class AuditedBookViewSet(viewsets.ModelViewSet):
    queryset = Book.objects.all()
    serializer_class = BookSerializer

    def history(self, request, pk=None):
        """
        Get historical changes for this book.
        GET /books/1/history/
        """
        book = self.get_object()
        history = book.history.all()

        history_data = [{
            'id': record.history_id,
            'date': record.history_date,
            'user': record.history_user.username if record.history_user else None,
            'change_type': record.history_type,
            'changes': record.get_changed_fields(),
        } for record in history]

        return Response(history_data)

# Usage
router = HistoryRouter()
router.register(r'books', AuditedBookViewSet)

# Generated URL:
# GET /books/1/history/  -> list of changes
```

### Example 10: Override get_routes for Conditional Routes

```python
from rest_framework.routers import SimpleRouter

class ConditionalRouter(SimpleRouter):
    """
    Router that includes routes conditionally based on ViewSet attributes.
    """
    def get_routes(self, viewset):
        """
        Override to conditionally include routes.
        """
        routes = super().get_routes(viewset)

        # Only include delete route if ViewSet allows it
        if not getattr(viewset, 'allow_delete', True):
            routes = [
                route for route in routes
                if 'destroy' not in getattr(route, 'mapping', {}).values()
            ]

        # Only include create route if ViewSet allows it
        if not getattr(viewset, 'allow_create', True):
            routes = [
                route for route in routes
                if 'create' not in getattr(route, 'mapping', {}).values()
            ]

        return routes

# ViewSet with restrictions
class ProtectedBookViewSet(viewsets.ModelViewSet):
    queryset = Book.objects.all()
    serializer_class = BookSerializer

    # Disable deletion through API
    allow_delete = False

    # Disable creation through API
    allow_create = False

# Usage
router = ConditionalRouter()
router.register(r'books', ProtectedBookViewSet)

# Generated URLs:
# GET    /books/      -> list (allowed)
# GET    /books/1/    -> retrieve (allowed)
# PUT    /books/1/    -> update (allowed)
# PATCH  /books/1/    -> partial_update (allowed)
# POST   /books/      -> NOT GENERATED (disabled)
# DELETE /books/1/    -> NOT GENERATED (disabled)
```

## Real-World Examples

### Example 11: Multi-Tenant Router

Router that adds tenant prefix to all URLs:

```python
from rest_framework.routers import DefaultRouter
from django.urls import path

class TenantRouter(DefaultRouter):
    """
    Router that adds tenant ID to all URLs.
    """
    def get_urls(self):
        """
        Generate URLs with tenant prefix.
        """
        urls = []

        for prefix, viewset, basename in self.registry:
            lookup = self.get_lookup_regex(viewset)
            routes = self.get_routes(viewset)

            for route in routes:
                mapping = self.get_method_map(viewset, route.mapping)
                if not mapping:
                    continue

                # Add tenant prefix to URL
                tenant_prefix = '<slug:tenant_slug>/'
                regex = route.url.format(
                    prefix=tenant_prefix + prefix,
                    lookup=lookup,
                    trailing_slash=self.trailing_slash
                )

                initkwargs = route.initkwargs.copy()
                initkwargs.update({
                    'basename': basename,
                    'detail': route.detail,
                })

                view = viewset.as_view(mapping, **initkwargs)
                name = route.name.format(basename=basename)
                urls.append(self._url_conf(regex, view, name=name))

        # Add root view with tenant prefix
        if self.include_root_view:
            view = self.get_api_root_view(api_urls=urls)
            root_url = path('<slug:tenant_slug>/', view, name=self.root_view_name)
            urls.append(root_url)

        if self.include_format_suffixes:
            from rest_framework.urlpatterns import format_suffix_patterns
            urls = format_suffix_patterns(urls)

        return urls

# ViewSet with tenant support
class TenantBookViewSet(viewsets.ModelViewSet):
    serializer_class = BookSerializer

    def get_queryset(self):
        """Filter by tenant from URL"""
        tenant_slug = self.kwargs['tenant_slug']
        return Book.objects.filter(tenant__slug=tenant_slug)

# Usage
router = TenantRouter()
router.register(r'books', TenantBookViewSet)

# Generated URLs:
# GET /{tenant}/books/
# GET /{tenant}/books/1/
```

### Example 12: Read-Only Router

Router that only generates GET endpoints:

```python
from rest_framework.routers import SimpleRouter, Route, DynamicRoute

class ReadOnlyRouter(SimpleRouter):
    """
    Router that only generates read-only routes (GET methods).
    Perfect for public APIs or reporting endpoints.
    """
    routes = [
        # List route - GET only
        Route(
            url=r'^{prefix}{trailing_slash}$',
            mapping={'get': 'list'},  # Only GET
            name='{basename}-list',
            detail=False,
            initkwargs={'suffix': 'List'}
        ),
        # Dynamic list routes - will filter to GET only
        DynamicRoute(
            url=r'^{prefix}/{url_path}{trailing_slash}$',
            name='{basename}-{url_name}',
            detail=False,
            initkwargs={}
        ),
        # Detail route - GET only
        Route(
            url=r'^{prefix}/{lookup}{trailing_slash}$',
            mapping={'get': 'retrieve'},  # Only GET
            name='{basename}-detail',
            detail=True,
            initkwargs={'suffix': 'Instance'}
        ),
        # Dynamic detail routes - will filter to GET only
        DynamicRoute(
            url=r'^{prefix}/{lookup}/{url_path}{trailing_slash}$',
            name='{basename}-{url_name}',
            detail=True,
            initkwargs={}
        ),
    ]

    def get_method_map(self, viewset, method_map):
        """Override to only allow GET methods"""
        bound_methods = super().get_method_map(viewset, method_map)
        # Filter to only GET methods
        return {k: v for k, v in bound_methods.items() if k == 'get'}

# Usage
router = ReadOnlyRouter()
router.register(r'reports', ReportViewSet)

# Generated URLs (all read-only):
# GET /reports/
# GET /reports/1/
```

### Example 13: Documentation Router

Router that adds OpenAPI/Swagger documentation endpoints:

```python
from rest_framework.routers import DefaultRouter, Route

class DocumentationRouter(DefaultRouter):
    """
    Router that adds documentation endpoints to each resource.
    """
    routes = [
        *DefaultRouter.routes,

        # Documentation route
        Route(
            url=r'^{prefix}/docs{trailing_slash}$',
            mapping={'get': 'get_docs'},
            name='{basename}-docs',
            detail=False,
            initkwargs={'suffix': 'Docs'}
        ),
    ]

# ViewSet with documentation
class DocumentedBookViewSet(viewsets.ModelViewSet):
    """
    ViewSet for managing books.

    This ViewSet provides full CRUD operations for books.
    """
    queryset = Book.objects.all()
    serializer_class = BookSerializer

    def get_docs(self, request):
        """
        Get OpenAPI documentation for this endpoint.
        GET /books/docs/
        """
        return Response({
            'resource': 'Book',
            'description': self.__class__.__doc__,
            'endpoints': [
                {'method': 'GET', 'path': '/books/', 'description': 'List all books'},
                {'method': 'POST', 'path': '/books/', 'description': 'Create a book'},
                {'method': 'GET', 'path': '/books/{id}/', 'description': 'Get a book'},
                {'method': 'PUT', 'path': '/books/{id}/', 'description': 'Update a book'},
                {'method': 'DELETE', 'path': '/books/{id}/', 'description': 'Delete a book'},
            ],
            'schema': {
                'type': 'object',
                'properties': {
                    'id': {'type': 'integer'},
                    'title': {'type': 'string'},
                    'author': {'type': 'integer'},
                    'isbn': {'type': 'string'},
                },
            },
        })

# Usage
router = DocumentationRouter()
router.register(r'books', DocumentedBookViewSet)

# Generated URL:
# GET /books/docs/  -> returns documentation
```

## Best Practices for Custom Routers

1. **Extend, don't replace** - Start with SimpleRouter or DefaultRouter
2. **Document your routes** - Add docstrings explaining custom behavior
3. **Test thoroughly** - Custom routers can be hard to debug
4. **Keep it simple** - Complex routing logic should be in views
5. **Follow conventions** - Don't break REST principles without good reason
6. **Consider alternatives** - Sometimes @action is better than a custom router
7. **Version your routers** - Custom routers can break APIs, version them
8. **Make it reusable** - Design routers to be used across multiple projects

## Debugging Custom Routers

```python
# Print all registered routes
router = CustomRouter()
router.register(r'books', BookViewSet)

print("Registry:", router.registry)
print("\nGenerated URLs:")
for pattern in router.urls:
    print(f"  {pattern.pattern} -> {pattern.name}")

# Use Django's show_urls command (django-extensions)
# pip install django-extensions
# python manage.py show_urls

# Or create a management command to dump routes
from django.core.management.base import BaseCommand

class Command(BaseCommand):
    def handle(self, *args, **options):
        from myapp.urls import router
        for pattern in router.urls:
            self.stdout.write(f"{pattern.pattern} -> {pattern.name}")
```

## Summary

Custom routers are powerful for:
- Adding consistent endpoints across all resources
- Implementing organization-specific URL patterns
- Supporting legacy URL structures
- Adding specialized functionality (export, history, etc.)

Key techniques:
- Extend `SimpleRouter.routes` to add new route patterns
- Override `get_lookup_regex()` for custom lookup patterns
- Override `get_routes()` for conditional route inclusion
- Override `get_urls()` for complete URL generation control
- Extend `DefaultRouter` for custom root views

Remember: Most use cases don't need custom routers. Use @action for ViewSet-specific endpoints and regular URL patterns for non-ViewSet views.
