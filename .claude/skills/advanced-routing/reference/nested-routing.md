# Nested Routing Reference

This document covers patterns for implementing nested resource URLs in Django REST Framework.

## Table of Contents
- [Understanding Nested Resources](#understanding-nested-resources)
- [Manual Nested Routing](#manual-nested-routing)
- [Using drf-nested-routers](#using-drf-nested-routers)
- [Custom Nested Router Implementation](#custom-nested-router-implementation)
- [Common Patterns](#common-patterns)
- [Best Practices](#best-practices)

## Understanding Nested Resources

Nested resources represent parent-child relationships in URLs:

```
# Flat structure (typical DRF)
/api/authors/1/
/api/books/1/

# Nested structure
/api/authors/1/books/
/api/authors/1/books/2/
```

**When to use nested URLs:**
- Parent-child relationships are fundamental to the domain
- Operations are always in context of a parent
- API consumers expect hierarchical access
- Resources don't make sense independently

**When NOT to use nested URLs:**
- More than 2-3 levels of nesting
- Resources can be accessed independently
- Filtering is sufficient (e.g., `/books/?author=1`)
- URL complexity outweighs benefits

## Manual Nested Routing

The simplest approach: manually define nested URL patterns.

### Example 1: Basic Nested Routes

```python
# models.py
from django.db import models

class Author(models.Model):
    name = models.CharField(max_length=100)
    email = models.EmailField()

class Book(models.Model):
    title = models.CharField(max_length=200)
    author = models.ForeignKey(Author, on_delete=models.CASCADE, related_name='books')
    isbn = models.CharField(max_length=13)

# serializers.py
from rest_framework import serializers

class BookSerializer(serializers.ModelSerializer):
    class Meta:
        model = Book
        fields = ['id', 'title', 'isbn', 'author']
        read_only_fields = ['author']  # Author comes from URL

class AuthorSerializer(serializers.ModelSerializer):
    books_count = serializers.IntegerField(source='books.count', read_only=True)

    class Meta:
        model = Author
        fields = ['id', 'name', 'email', 'books_count']

# views.py
from rest_framework import viewsets, status
from rest_framework.response import Response

class AuthorViewSet(viewsets.ModelViewSet):
    """Standard ViewSet for authors"""
    queryset = Author.objects.all()
    serializer_class = AuthorSerializer

class AuthorBookViewSet(viewsets.ModelViewSet):
    """
    ViewSet for books nested under authors.
    URL: /authors/{author_pk}/books/
    """
    serializer_class = BookSerializer

    def get_queryset(self):
        """Filter books by author from URL"""
        author_pk = self.kwargs['author_pk']
        return Book.objects.filter(author_id=author_pk)

    def perform_create(self, serializer):
        """Set author from URL when creating book"""
        author_pk = self.kwargs['author_pk']
        serializer.save(author_id=author_pk)

# urls.py
from django.urls import path, include
from rest_framework.routers import DefaultRouter

# Main router for authors
router = DefaultRouter()
router.register(r'authors', AuthorViewSet, basename='author')

# Manual nested routes for books
from .views import AuthorBookViewSet

author_books_list = AuthorBookViewSet.as_view({
    'get': 'list',
    'post': 'create'
})

author_books_detail = AuthorBookViewSet.as_view({
    'get': 'retrieve',
    'put': 'update',
    'patch': 'partial_update',
    'delete': 'destroy'
})

urlpatterns = [
    path('api/', include(router.urls)),
    path('api/authors/<int:author_pk>/books/',
         author_books_list,
         name='author-books-list'),
    path('api/authors/<int:author_pk>/books/<int:pk>/',
         author_books_detail,
         name='author-books-detail'),
]

# Generated URLs:
# GET    /api/authors/                     -> list authors
# POST   /api/authors/                     -> create author
# GET    /api/authors/1/                   -> get author 1
# PUT    /api/authors/1/                   -> update author 1
# DELETE /api/authors/1/                   -> delete author 1
# GET    /api/authors/1/books/             -> list books by author 1
# POST   /api/authors/1/books/             -> create book for author 1
# GET    /api/authors/1/books/2/           -> get book 2 by author 1
# PUT    /api/authors/1/books/2/           -> update book 2 by author 1
# DELETE /api/authors/1/books/2/           -> delete book 2 by author 1
```

### Example 2: @action for Simple Nested Resources

For read-only or simple nested resources, use @action:

```python
from rest_framework import viewsets
from rest_framework.decorators import action
from rest_framework.response import Response

class AuthorViewSet(viewsets.ModelViewSet):
    """
    ViewSet for authors with nested books endpoint.
    """
    queryset = Author.objects.all()
    serializer_class = AuthorSerializer

    @action(detail=True, methods=['get'])
    def books(self, request, pk=None):
        """
        List all books by this author.
        GET /authors/1/books/
        """
        author = self.get_object()
        books = author.books.all()
        serializer = BookSerializer(books, many=True)
        return Response(serializer.data)

    @action(detail=True, methods=['post'])
    def books(self, request, pk=None):
        """
        Create a book for this author.
        POST /authors/1/books/
        """
        author = self.get_object()
        serializer = BookSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save(author=author)
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

# urls.py
router = DefaultRouter()
router.register(r'authors', AuthorViewSet, basename='author')

urlpatterns = [
    path('api/', include(router.urls)),
]

# Generated URLs:
# GET  /api/authors/1/books/  -> list books
# POST /api/authors/1/books/  -> create book
# (No detail endpoints for individual books)
```

**Limitations of @action approach:**
- Can't easily handle detail operations (GET/PUT/DELETE single nested item)
- URL names don't follow standard patterns
- Can't use router's full ViewSet features

## Using drf-nested-routers

The `drf-nested-routers` package simplifies nested routing.

### Installation

```bash
pip install drf-nested-routers
```

### Example 3: Basic drf-nested-routers Usage

```python
# views.py
from rest_framework import viewsets

class AuthorViewSet(viewsets.ModelViewSet):
    queryset = Author.objects.all()
    serializer_class = AuthorSerializer

class BookViewSet(viewsets.ModelViewSet):
    queryset = Book.objects.all()
    serializer_class = BookSerializer

    def get_queryset(self):
        """Filter by author if nested under /authors/{id}/books/"""
        queryset = super().get_queryset()

        # Check if this is a nested route
        author_pk = self.kwargs.get('author_pk')
        if author_pk is not None:
            queryset = queryset.filter(author_id=author_pk)

        return queryset

    def perform_create(self, serializer):
        """Set author from URL when creating nested"""
        author_pk = self.kwargs.get('author_pk')
        if author_pk is not None:
            serializer.save(author_id=author_pk)
        else:
            serializer.save()

# urls.py
from rest_framework.routers import DefaultRouter
from rest_framework_nested import routers

# Create main router
router = DefaultRouter()
router.register(r'authors', AuthorViewSet, basename='author')
router.register(r'books', BookViewSet, basename='book')  # Flat access too

# Create nested router for authors -> books
authors_router = routers.NestedDefaultRouter(router, r'authors', lookup='author')
authors_router.register(r'books', BookViewSet, basename='author-books')

urlpatterns = [
    path('api/', include(router.urls)),
    path('api/', include(authors_router.urls)),
]

# Generated URLs:
# Authors (flat)
# GET    /api/authors/
# POST   /api/authors/
# GET    /api/authors/1/
# PUT    /api/authors/1/
# DELETE /api/authors/1/

# Books (flat - optional)
# GET    /api/books/
# POST   /api/books/
# GET    /api/books/1/

# Books (nested under author)
# GET    /api/authors/1/books/
# POST   /api/authors/1/books/
# GET    /api/authors/1/books/2/
# PUT    /api/authors/1/books/2/
# DELETE /api/authors/1/books/2/
```

### Example 4: Three-Level Nesting

```python
# models.py
class Publisher(models.Model):
    name = models.CharField(max_length=100)

class Author(models.Model):
    name = models.CharField(max_length=100)
    publisher = models.ForeignKey(Publisher, on_delete=models.CASCADE, related_name='authors')

class Book(models.Model):
    title = models.CharField(max_length=200)
    author = models.ForeignKey(Author, on_delete=models.CASCADE, related_name='books')

# views.py
class PublisherViewSet(viewsets.ModelViewSet):
    queryset = Publisher.objects.all()
    serializer_class = PublisherSerializer

class AuthorViewSet(viewsets.ModelViewSet):
    queryset = Author.objects.all()
    serializer_class = AuthorSerializer

    def get_queryset(self):
        queryset = super().get_queryset()
        publisher_pk = self.kwargs.get('publisher_pk')
        if publisher_pk:
            queryset = queryset.filter(publisher_id=publisher_pk)
        return queryset

    def perform_create(self, serializer):
        publisher_pk = self.kwargs.get('publisher_pk')
        if publisher_pk:
            serializer.save(publisher_id=publisher_pk)
        else:
            serializer.save()

class BookViewSet(viewsets.ModelViewSet):
    queryset = Book.objects.all()
    serializer_class = BookSerializer

    def get_queryset(self):
        queryset = super().get_queryset()
        author_pk = self.kwargs.get('author_pk')
        if author_pk:
            queryset = queryset.filter(author_id=author_pk)
        return queryset

    def perform_create(self, serializer):
        author_pk = self.kwargs.get('author_pk')
        if author_pk:
            serializer.save(author_id=author_pk)
        else:
            serializer.save()

# urls.py
from rest_framework.routers import DefaultRouter
from rest_framework_nested import routers

# Level 1: Publishers
router = DefaultRouter()
router.register(r'publishers', PublisherViewSet, basename='publisher')

# Level 2: Publishers -> Authors
publishers_router = routers.NestedDefaultRouter(
    router, r'publishers', lookup='publisher'
)
publishers_router.register(r'authors', AuthorViewSet, basename='publisher-authors')

# Level 3: Publishers -> Authors -> Books
authors_router = routers.NestedDefaultRouter(
    publishers_router, r'authors', lookup='author'
)
authors_router.register(r'books', BookViewSet, basename='publisher-author-books')

urlpatterns = [
    path('api/', include(router.urls)),
    path('api/', include(publishers_router.urls)),
    path('api/', include(authors_router.urls)),
]

# Generated URLs:
# GET /api/publishers/
# GET /api/publishers/1/
# GET /api/publishers/1/authors/
# GET /api/publishers/1/authors/2/
# GET /api/publishers/1/authors/2/books/
# GET /api/publishers/1/authors/2/books/3/
```

**Warning:** Three-level nesting is often too deep. Consider:
- `/api/books/?publisher=1&author=2` (flat with filters)
- Providing multiple access paths (flat + nested)

## Custom Nested Router Implementation

You can implement nested routing without external packages.

### Example 5: Simple Nested Router

```python
from rest_framework.routers import DefaultRouter
from django.urls import path

class NestedRouterMixin:
    """
    Mixin to add nested routing capability to a ViewSet.
    """
    def get_queryset(self):
        queryset = super().get_queryset()

        # Check for parent filtering
        for key, value in self.kwargs.items():
            if key.endswith('_pk') and key != 'pk':
                # Extract parent field name (e.g., 'author_pk' -> 'author')
                field_name = key[:-3]  # Remove '_pk'
                queryset = queryset.filter(**{f'{field_name}_id': value})

        return queryset

    def perform_create(self, serializer):
        # Automatically set parent relationships
        parent_data = {}
        for key, value in self.kwargs.items():
            if key.endswith('_pk') and key != 'pk':
                field_name = key[:-3]
                parent_data[f'{field_name}_id'] = value

        serializer.save(**parent_data)

# Usage
class BookViewSet(NestedRouterMixin, viewsets.ModelViewSet):
    queryset = Book.objects.all()
    serializer_class = BookSerializer

# Manual URL configuration
from django.urls import path

def nested_route(parent_pattern, parent_basename, child_viewset, child_basename):
    """
    Generate nested routes for a child ViewSet.
    """
    list_view = child_viewset.as_view({'get': 'list', 'post': 'create'})
    detail_view = child_viewset.as_view({
        'get': 'retrieve',
        'put': 'update',
        'patch': 'partial_update',
        'delete': 'destroy'
    })

    return [
        path(
            f'{parent_pattern}/<int:{parent_basename}_pk>/{child_basename}/',
            list_view,
            name=f'{parent_basename}-{child_basename}-list'
        ),
        path(
            f'{parent_pattern}/<int:{parent_basename}_pk>/{child_basename}/<int:pk>/',
            detail_view,
            name=f'{parent_basename}-{child_basename}-detail'
        ),
    ]

# urls.py
router = DefaultRouter()
router.register(r'authors', AuthorViewSet, basename='author')

urlpatterns = [
    path('api/', include(router.urls)),
    *nested_route('api/authors', 'author', BookViewSet, 'books'),
]
```

### Example 6: Advanced Nested Router Class

```python
from rest_framework.routers import SimpleRouter
from django.urls import path

class NestedRouter(SimpleRouter):
    """
    Custom router that handles nested resources.
    """
    def __init__(self, parent_router, parent_prefix, parent_lookup='parent', *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.parent_router = parent_router
        self.parent_prefix = parent_prefix
        self.parent_lookup = parent_lookup

    def get_urls(self):
        """
        Generate nested URLs.
        """
        urls = []

        for prefix, viewset, basename in self.registry:
            lookup = self.get_lookup_regex(viewset)
            routes = self.get_routes(viewset)

            for route in routes:
                mapping = self.get_method_map(viewset, route.mapping)
                if not mapping:
                    continue

                # Build nested URL with parent prefix
                parent_lookup_regex = f'<int:{self.parent_lookup}_pk>'
                nested_prefix = f'{self.parent_prefix}/{parent_lookup_regex}/{prefix}'

                regex = route.url.format(
                    prefix=nested_prefix,
                    lookup=lookup,
                    trailing_slash=self.trailing_slash
                )

                # Remove leading ^ and trailing $ for path()
                if regex.startswith('^'):
                    regex = regex[1:]
                if regex.endswith('$'):
                    regex = regex[:-1]

                initkwargs = route.initkwargs.copy()
                initkwargs.update({
                    'basename': basename,
                    'detail': route.detail,
                })

                view = viewset.as_view(mapping, **initkwargs)
                name = route.name.format(basename=basename)
                urls.append(path(regex, view, name=name))

        return urls

# Usage
router = DefaultRouter()
router.register(r'authors', AuthorViewSet, basename='author')

nested_router = NestedRouter(router, r'authors', lookup='author')
nested_router.register(r'books', BookViewSet, basename='author-books')

urlpatterns = [
    path('api/', include(router.urls)),
    path('api/', include(nested_router.urls)),
]
```

## Common Patterns

### Pattern 1: Optional Nested Access (Flat + Nested)

Allow accessing resources both ways:

```python
# Flat access
GET /api/books/              # All books
GET /api/books/1/            # Specific book

# Nested access
GET /api/authors/1/books/    # Books by author 1
GET /api/authors/1/books/1/  # Book 1 by author 1
```

Implementation:

```python
class BookViewSet(viewsets.ModelViewSet):
    queryset = Book.objects.all()
    serializer_class = BookSerializer

    def get_queryset(self):
        """Support both flat and nested access"""
        queryset = super().get_queryset()

        # If nested under author, filter by author
        author_pk = self.kwargs.get('author_pk')
        if author_pk is not None:
            queryset = queryset.filter(author_id=author_pk)

        # Also support flat filtering via query params
        author_param = self.request.query_params.get('author')
        if author_param:
            queryset = queryset.filter(author_id=author_param)

        return queryset

# Register both routes
router = DefaultRouter()
router.register(r'books', BookViewSet, basename='book')

nested_router = NestedRouter(router, r'authors', lookup='author')
nested_router.register(r'books', BookViewSet, basename='author-books')
```

### Pattern 2: Read-Only Nested, Writable Flat

Nested routes for reading, flat routes for writing:

```python
class BookViewSet(viewsets.ModelViewSet):
    queryset = Book.objects.all()
    serializer_class = BookSerializer

    def get_permissions(self):
        """Allow write operations only on flat routes"""
        if self.kwargs.get('author_pk'):
            # Nested route - read-only
            if self.action in ['create', 'update', 'partial_update', 'destroy']:
                return [permissions.IsAdminUser()]
        return super().get_permissions()

# Or use ReadOnlyModelViewSet for nested
from rest_framework.viewsets import ReadOnlyModelViewSet

class AuthorBooksViewSet(ReadOnlyModelViewSet):
    """Read-only view of books nested under author"""
    queryset = Book.objects.all()
    serializer_class = BookSerializer

    def get_queryset(self):
        return super().get_queryset().filter(author_id=self.kwargs['author_pk'])

# Full CRUD for flat routes
class BookViewSet(viewsets.ModelViewSet):
    queryset = Book.objects.all()
    serializer_class = BookSerializer

# URLs
router = DefaultRouter()
router.register(r'books', BookViewSet, basename='book')

nested_router = NestedRouter(router, r'authors', lookup='author')
nested_router.register(r'books', AuthorBooksViewSet, basename='author-books')
```

### Pattern 3: Shallow Nesting

Only nest list routes, not detail routes:

```python
# Nested list only
GET /api/authors/1/books/     # List books by author 1
POST /api/authors/1/books/    # Create book for author 1

# Flat detail routes (shorter URLs)
GET /api/books/1/             # Get book 1
PUT /api/books/1/             # Update book 1
DELETE /api/books/1/          # Delete book 1
```

Implementation:

```python
# Custom shallow nested routes
urlpatterns = [
    # Flat routes for single books
    path('api/', include(router.urls)),

    # Nested routes for lists only
    path('api/authors/<int:author_pk>/books/',
         BookViewSet.as_view({'get': 'list', 'post': 'create'}),
         name='author-books-list'),
]
```

## Best Practices

### 1. Limit Nesting Depth

**Bad:**
```python
/api/publishers/1/authors/2/books/3/chapters/4/sections/5/
```

**Good:**
```python
/api/publishers/1/
/api/authors/2/
/api/books/3/
/api/chapters/4/
/api/sections/5/

# Or use query parameters
/api/sections/5/?book=3
```

### 2. Provide Multiple Access Paths

```python
# Both should work
GET /api/books/?author=1
GET /api/authors/1/books/
```

### 3. Validate Parent Relationships

```python
class BookViewSet(viewsets.ModelViewSet):
    def retrieve(self, request, author_pk=None, pk=None):
        """Validate book belongs to author"""
        try:
            book = Book.objects.get(pk=pk, author_id=author_pk)
        except Book.DoesNotExist:
            return Response(
                {'error': 'Book not found for this author'},
                status=status.HTTP_404_NOT_FOUND
            )

        serializer = self.get_serializer(book)
        return Response(serializer.data)
```

### 4. Use Prefetch for Performance

```python
class AuthorViewSet(viewsets.ModelViewSet):
    def get_queryset(self):
        """Optimize nested book queries"""
        queryset = Author.objects.all()

        if self.action == 'list':
            # Prefetch books when listing authors
            queryset = queryset.prefetch_related('books')

        return queryset
```

### 5. Clear URL Naming

```python
# Good URL names
author-list
author-detail
author-books-list
author-books-detail

# Bad URL names
author-book  # Ambiguous
book  # Not clear this is nested
```

### 6. Document Nested Routes

```python
class AuthorViewSet(viewsets.ModelViewSet):
    """
    ViewSet for managing authors.

    Endpoints:
    - GET /authors/ - List all authors
    - GET /authors/{id}/ - Get specific author
    - GET /authors/{id}/books/ - List books by this author
    - POST /authors/{id}/books/ - Create book for this author

    Note: Books can also be accessed via /books/ endpoints.
    """
    pass
```

## Summary

**Nested routing approaches:**

1. **@action decorator** - Simple, read-only nested resources
2. **Manual URL patterns** - Full control, no dependencies
3. **drf-nested-routers** - Easy, full-featured, requires package
4. **Custom router** - Flexible, reusable, more complex

**When to use:**
- Clear parent-child relationships
- Operations always in parent context
- API consumers expect hierarchical structure
- 1-2 levels of nesting maximum

**When NOT to use:**
- Deep nesting (3+ levels)
- Resources accessed independently
- Query parameters work as well
- URL complexity hurts usability

**Best practices:**
- Limit nesting depth to 2 levels
- Provide both flat and nested access
- Validate parent relationships
- Optimize queries with prefetch_related
- Document your URL structure clearly
