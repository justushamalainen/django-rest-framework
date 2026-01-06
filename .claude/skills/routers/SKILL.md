---
version: 1.0
last_updated: 2026-01-06
difficulty: beginner
keywords: routers, viewsets, urls, routing, defaultrouter, actions
dependencies: djangorestframework>=3.14
source_files:
  - rest_framework/routers.py
  - rest_framework/viewsets.py
---

# DRF Routers

Routers automatically generate URL patterns for your ViewSets. Instead of manually defining URLs for each CRUD operation, routers do it for you.

## Simple Recommendation

**Use DefaultRouter. That's it.**

Unless you have specific needs (covered in reference docs), DefaultRouter works for 95% of use cases.

## Quick Start

Here's everything you need to know:

```python
# models.py
from django.db import models

class Book(models.Model):
    title = models.CharField(max_length=200)
    author = models.CharField(max_length=100)
    isbn = models.CharField(max_length=13, unique=True)
    published_date = models.DateField()

# serializers.py
from rest_framework import serializers
from .models import Book

class BookSerializer(serializers.ModelSerializer):
    class Meta:
        model = Book
        fields = ['id', 'title', 'author', 'isbn', 'published_date']

# views.py
from rest_framework import viewsets
from rest_framework.decorators import action
from rest_framework.response import Response
from .models import Book
from .serializers import BookSerializer

class BookViewSet(viewsets.ModelViewSet):
    """
    Automatically provides:
    - list (GET /books/)
    - create (POST /books/)
    - retrieve (GET /books/{id}/)
    - update (PUT /books/{id}/)
    - partial_update (PATCH /books/{id}/)
    - destroy (DELETE /books/{id}/)
    """
    queryset = Book.objects.all()
    serializer_class = BookSerializer

    @action(detail=True, methods=['post'])
    def publish(self, request, pk=None):
        """
        Custom action for a specific book.
        URL: POST /books/{id}/publish/
        """
        book = self.get_object()
        # Do something with the book
        return Response({'status': 'published'})

    @action(detail=False, methods=['get'])
    def recent(self, request):
        """
        Custom action for the collection.
        URL: GET /books/recent/
        """
        recent_books = Book.objects.order_by('-published_date')[:10]
        serializer = self.get_serializer(recent_books, many=True)
        return Response(serializer.data)

# urls.py
from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import BookViewSet

router = DefaultRouter()
router.register(r'books', BookViewSet, basename='book')

urlpatterns = [
    path('api/', include(router.urls)),
]
```

**Generated URLs:**
```
GET    /api/              -> API root (list of all endpoints)
GET    /api/books/        -> List all books
POST   /api/books/        -> Create new book
GET    /api/books/1/      -> Get book 1
PUT    /api/books/1/      -> Update book 1 (full)
PATCH  /api/books/1/      -> Update book 1 (partial)
DELETE /api/books/1/      -> Delete book 1
POST   /api/books/1/publish/  -> Custom action: publish book 1
GET    /api/books/recent/     -> Custom action: recent books
```

**Test it:**
```bash
# List all books
curl http://localhost:8000/api/books/

# Create a book
curl -X POST http://localhost:8000/api/books/ \
  -H "Content-Type: application/json" \
  -d '{"title": "Django Guide", "author": "Jane Doe", "isbn": "1234567890123", "published_date": "2024-01-01"}'

# Get specific book
curl http://localhost:8000/api/books/1/

# Update book
curl -X PATCH http://localhost:8000/api/books/1/ \
  -H "Content-Type: application/json" \
  -d '{"title": "Django Complete Guide"}'

# Custom action
curl -X POST http://localhost:8000/api/books/1/publish/

# Recent books
curl http://localhost:8000/api/books/recent/
```

## The @action Decorator

Use `@action` to add custom endpoints beyond CRUD:

### Detail Actions (operate on a specific object)

```python
@action(detail=True, methods=['post'])
def publish(self, request, pk=None):
    """URL: POST /books/{id}/publish/"""
    book = self.get_object()
    book.published = True
    book.save()
    return Response({'status': 'published'})

@action(detail=True, methods=['get'])
def reviews(self, request, pk=None):
    """URL: GET /books/{id}/reviews/"""
    book = self.get_object()
    reviews = book.reviews.all()
    return Response({'reviews': list(reviews.values())})
```

### List Actions (operate on the collection)

```python
@action(detail=False, methods=['get'])
def recent(self, request):
    """URL: GET /books/recent/"""
    recent_books = self.get_queryset().order_by('-published_date')[:10]
    serializer = self.get_serializer(recent_books, many=True)
    return Response(serializer.data)

@action(detail=False, methods=['post'])
def bulk_import(self, request):
    """URL: POST /books/bulk_import/"""
    # Handle bulk import logic
    return Response({'imported': 42})
```

### Custom URL Paths and Names

```python
@action(detail=True, url_path='mark-favorite', url_name='mark-favorite')
def mark_as_favorite(self, request, pk=None):
    """
    URL: POST /books/{id}/mark-favorite/
    URL Name: book-mark-favorite (for reverse())
    """
    book = self.get_object()
    # Mark as favorite
    return Response({'status': 'favorited'})
```

## Custom Lookup Fields

By default, routers use `pk` (primary key) for detail lookups. You can customize this:

### Using Slug

```python
class BookViewSet(viewsets.ModelViewSet):
    queryset = Book.objects.all()
    serializer_class = BookSerializer
    lookup_field = 'isbn'  # Use ISBN instead of pk

# URLs: /books/978-0-123456-78-9/
```

### Using UUID

```python
import uuid
from django.db import models

class Book(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4)
    title = models.CharField(max_length=200)

class BookViewSet(viewsets.ModelViewSet):
    queryset = Book.objects.all()
    serializer_class = BookSerializer
    lookup_field = 'id'
    lookup_value_converter = 'uuid'  # Use UUID path converter

# URLs: /books/550e8400-e29b-41d4-a716-446655440000/
```

### Custom Lookup Field

```python
class BookViewSet(viewsets.ModelViewSet):
    queryset = Book.objects.all()
    serializer_class = BookSerializer
    lookup_field = 'slug'
    lookup_url_kwarg = 'book_slug'  # Optional: different URL param name

# URLs: /books/django-complete-guide/
```

## Common Mistakes

### ❌ Mistake 1: Forgetting to include router URLs

**Wrong:**
```python
router = DefaultRouter()
router.register(r'books', BookViewSet)

urlpatterns = [
    # Router URLs not included!
]
```

**✅ Correct:**
```python
router = DefaultRouter()
router.register(r'books', BookViewSet)

urlpatterns = [
    path('api/', include(router.urls)),
]
```

### ❌ Mistake 2: Wrong detail parameter

**Wrong:**
```python
@action(detail=False, methods=['post'])  # Should be detail=True!
def publish(self, request, pk=None):
    book = self.get_object()  # This will fail!
    # ...
```

**Why it fails:** `detail=False` creates a list-level URL (`/books/publish/`), but the code expects a specific object ID.

**✅ Correct:**
```python
# For operations on a specific object
@action(detail=True, methods=['post'])  # /books/{id}/publish/
def publish(self, request, pk=None):
    book = self.get_object()  # Works!
    # ...

# For operations on the collection
@action(detail=False, methods=['get'])  # /books/recent/
def recent(self, request):
    books = self.get_queryset()  # Works!
    # ...
```

### ❌ Mistake 3: Missing basename when no queryset

**Wrong:**
```python
class BookViewSet(viewsets.ViewSet):  # Not ModelViewSet!
    # No queryset attribute

    def list(self, request):
        books = Book.objects.all()
        # ...

router.register(r'books', BookViewSet)  # Will crash!
```

**Why it fails:** Router needs basename to generate URL names. Without a queryset, it can't auto-determine the basename.

**✅ Correct:**
```python
# Explicitly provide basename
router.register(r'books', BookViewSet, basename='book')

# Now URL names work: book-list, book-detail, etc.
```

## URL Names for Reversing

Router generates predictable URL names:

```python
router.register(r'books', BookViewSet, basename='book')

# Generated URL names:
# - book-list: /books/
# - book-detail: /books/{pk}/
# - book-{action_name}: /books/{pk}/{action_name}/

# Usage:
from django.urls import reverse

reverse('book-list')                    # /books/
reverse('book-detail', kwargs={'pk': 1}) # /books/1/
reverse('book-publish', kwargs={'pk': 1}) # /books/1/publish/
reverse('book-recent')                   # /books/recent/
```

## Multiple ViewSets

Register multiple ViewSets on the same router:

```python
router = DefaultRouter()
router.register(r'books', BookViewSet, basename='book')
router.register(r'authors', AuthorViewSet, basename='author')
router.register(r'publishers', PublisherViewSet, basename='publisher')

urlpatterns = [
    path('api/', include(router.urls)),
]

# Generates:
# /api/ - API root
# /api/books/
# /api/authors/
# /api/publishers/
```

## Advanced Topics

For more complex scenarios, see the reference documentation:

- **[Router Types](./reference/router-types.md)** - SimpleRouter vs DefaultRouter, configuration options

**For special cases only** (most APIs don't need these):
- **[Advanced Routing](../advanced-routing/)** - Custom routers, nested resources (e.g., /authors/1/books/)

## Next Steps

After mastering routers, continue to:
- **viewsets** skill - Deep dive into ViewSet implementation
- **api-documentation** skill - Auto-generate API documentation from routes
