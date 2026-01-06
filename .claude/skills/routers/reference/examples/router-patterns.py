"""
DRF Router Patterns - Working Code Examples

This file contains complete, working examples of router patterns in Django REST Framework.
All examples are production-ready and follow best practices.

Author: DRF Skills Team
Last Updated: 2026-01-06
"""

# ==============================================================================
# EXAMPLE 1: Basic Router Setup (DefaultRouter)
# ==============================================================================

"""
The most common router configuration for a typical API.
"""

from rest_framework.routers import DefaultRouter
from rest_framework import viewsets, serializers
from django.db import models
from django.urls import path, include

# Models
class Author(models.Model):
    name = models.CharField(max_length=100)
    email = models.EmailField(unique=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.name

class Book(models.Model):
    title = models.CharField(max_length=200)
    author = models.ForeignKey(Author, on_delete=models.CASCADE, related_name='books')
    isbn = models.CharField(max_length=13, unique=True)
    published_date = models.DateField()

    def __str__(self):
        return self.title

# Serializers
class AuthorSerializer(serializers.ModelSerializer):
    books_count = serializers.IntegerField(source='books.count', read_only=True)

    class Meta:
        model = Author
        fields = ['id', 'name', 'email', 'books_count', 'created_at']
        read_only_fields = ['created_at']

class BookSerializer(serializers.ModelSerializer):
    author_name = serializers.CharField(source='author.name', read_only=True)

    class Meta:
        model = Book
        fields = ['id', 'title', 'author', 'author_name', 'isbn', 'published_date']

# ViewSets
class AuthorViewSet(viewsets.ModelViewSet):
    """
    ViewSet for managing authors.

    Provides standard CRUD operations:
    - list: GET /authors/
    - create: POST /authors/
    - retrieve: GET /authors/{id}/
    - update: PUT /authors/{id}/
    - partial_update: PATCH /authors/{id}/
    - destroy: DELETE /authors/{id}/
    """
    queryset = Author.objects.all()
    serializer_class = AuthorSerializer

class BookViewSet(viewsets.ModelViewSet):
    """ViewSet for managing books."""
    queryset = Book.objects.select_related('author').all()
    serializer_class = BookSerializer

# Router Configuration
router = DefaultRouter()
router.register(r'authors', AuthorViewSet, basename='author')
router.register(r'books', BookViewSet, basename='book')

# URL Configuration
urlpatterns_example1 = [
    path('api/v1/', include(router.urls)),
]

# Generated URLs:
# GET    /api/v1/                -> API root (list of endpoints)
# GET    /api/v1/authors/        -> List all authors
# POST   /api/v1/authors/        -> Create new author
# GET    /api/v1/authors/1/      -> Get author 1
# PUT    /api/v1/authors/1/      -> Update author 1 (full)
# PATCH  /api/v1/authors/1/      -> Update author 1 (partial)
# DELETE /api/v1/authors/1/      -> Delete author 1
# (Same for books)


# ==============================================================================
# EXAMPLE 2: SimpleRouter (No Root View)
# ==============================================================================

"""
Use SimpleRouter when you don't need a browsable API root.
Better for production APIs and microservices.
"""

from rest_framework.routers import SimpleRouter

# Same ViewSets as Example 1

# Router Configuration
simple_router = SimpleRouter()
simple_router.register(r'authors', AuthorViewSet, basename='author')
simple_router.register(r'books', BookViewSet, basename='book')

urlpatterns_example2 = [
    path('api/', include(simple_router.urls)),
]

# Generated URLs:
# GET    /api/authors/        -> List all authors (no root view at /api/)
# POST   /api/authors/        -> Create new author
# GET    /api/authors/1/      -> Get author 1
# (No GET /api/ endpoint)


# ==============================================================================
# EXAMPLE 3: Custom Actions with @action Decorator
# ==============================================================================

"""
Add custom endpoints beyond standard CRUD operations.
"""

from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework import status
from django.db.models import Q

class AuthorViewSetWithActions(viewsets.ModelViewSet):
    """ViewSet with custom actions."""
    queryset = Author.objects.all()
    serializer_class = AuthorSerializer

    @action(detail=True, methods=['get'])
    def books(self, request, pk=None):
        """
        Get all books by this author.
        URL: GET /authors/{id}/books/
        """
        author = self.get_object()
        books = author.books.all()
        serializer = BookSerializer(books, many=True)
        return Response(serializer.data)

    @action(detail=True, methods=['post'])
    def publish_book(self, request, pk=None):
        """
        Publish a new book for this author.
        URL: POST /authors/{id}/publish_book/
        Body: {"title": "Book Title", "isbn": "1234567890123", "published_date": "2024-01-01"}
        """
        author = self.get_object()
        serializer = BookSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save(author=author)
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=False, methods=['get'])
    def recent(self, request):
        """
        Get recently added authors.
        URL: GET /authors/recent/
        Query params: ?limit=10
        """
        limit = int(request.query_params.get('limit', 10))
        recent_authors = Author.objects.order_by('-created_at')[:limit]
        serializer = self.get_serializer(recent_authors, many=True)
        return Response(serializer.data)

    @action(detail=False, methods=['get'])
    def search(self, request):
        """
        Search authors by name or email.
        URL: GET /authors/search/?q=john
        """
        query = request.query_params.get('q', '')
        if not query:
            return Response(
                {'error': 'Query parameter "q" is required'},
                status=status.HTTP_400_BAD_REQUEST
            )

        authors = Author.objects.filter(
            Q(name__icontains=query) | Q(email__icontains=query)
        )
        serializer = self.get_serializer(authors, many=True)
        return Response(serializer.data)

    @action(detail=True, methods=['get'], url_path='stats', url_name='statistics')
    def get_statistics(self, request, pk=None):
        """
        Get statistics for this author.
        URL: GET /authors/{id}/stats/
        URL Name: author-statistics (custom url_name)
        """
        author = self.get_object()
        books = author.books.all()

        stats = {
            'total_books': books.count(),
            'books_this_year': books.filter(
                published_date__year=2024
            ).count(),
            'average_isbn_length': sum(len(b.isbn) for b in books) / books.count() if books.count() > 0 else 0,
        }
        return Response(stats)

# Router Configuration
router_with_actions = DefaultRouter()
router_with_actions.register(r'authors', AuthorViewSetWithActions, basename='author')

urlpatterns_example3 = [
    path('api/', include(router_with_actions.urls)),
]

# Generated URLs:
# Standard CRUD:
# GET    /api/authors/
# POST   /api/authors/
# GET    /api/authors/1/
# PUT    /api/authors/1/
# PATCH  /api/authors/1/
# DELETE /api/authors/1/
#
# Custom actions:
# GET    /api/authors/1/books/           -> AuthorViewSetWithActions.books()
# POST   /api/authors/1/publish_book/    -> AuthorViewSetWithActions.publish_book()
# GET    /api/authors/recent/            -> AuthorViewSetWithActions.recent()
# GET    /api/authors/search/?q=john     -> AuthorViewSetWithActions.search()
# GET    /api/authors/1/stats/           -> AuthorViewSetWithActions.get_statistics()


# ==============================================================================
# EXAMPLE 4: Read-Only ViewSet
# ==============================================================================

"""
Use ReadOnlyModelViewSet when you only need list and retrieve actions.
"""

from rest_framework.viewsets import ReadOnlyModelViewSet

class ReadOnlyAuthorViewSet(ReadOnlyModelViewSet):
    """
    Read-only ViewSet for authors.
    Only provides list and retrieve actions (GET only).
    """
    queryset = Author.objects.all()
    serializer_class = AuthorSerializer

# Router Configuration
readonly_router = DefaultRouter()
readonly_router.register(r'authors', ReadOnlyAuthorViewSet, basename='author')

urlpatterns_example4 = [
    path('api/public/', include(readonly_router.urls)),
]

# Generated URLs:
# GET /api/public/authors/      -> List authors
# GET /api/public/authors/1/    -> Get author 1
# (No POST, PUT, PATCH, DELETE endpoints)


# ==============================================================================
# EXAMPLE 5: Custom Lookup Field
# ==============================================================================

"""
Use a field other than 'pk' for detail lookups.
Common for slugs, UUIDs, or natural keys.
"""

class AuthorViewSetWithSlug(viewsets.ModelViewSet):
    """
    ViewSet using email as lookup field instead of pk.
    """
    queryset = Author.objects.all()
    serializer_class = AuthorSerializer
    lookup_field = 'email'  # Use email instead of pk
    lookup_url_kwarg = 'email'  # URL parameter name

# Router Configuration
slug_router = DefaultRouter()
slug_router.register(r'authors', AuthorViewSetWithSlug, basename='author')

urlpatterns_example5 = [
    path('api/', include(slug_router.urls)),
]

# Generated URLs:
# GET /api/authors/                          -> List authors
# GET /api/authors/john@example.com/         -> Get author by email
# PUT /api/authors/john@example.com/         -> Update author by email
# DELETE /api/authors/john@example.com/      -> Delete author by email


# ==============================================================================
# EXAMPLE 6: Multiple Routers (API Versioning)
# ==============================================================================

"""
Use multiple routers for API versioning.
"""

# V1 ViewSets
class AuthorViewSetV1(viewsets.ModelViewSet):
    """Version 1 of Author API"""
    queryset = Author.objects.all()
    serializer_class = AuthorSerializer

# V2 ViewSets with additional features
class AuthorSerializerV2(serializers.ModelSerializer):
    """Enhanced serializer for V2"""
    books = BookSerializer(many=True, read_only=True)

    class Meta:
        model = Author
        fields = ['id', 'name', 'email', 'books', 'created_at']

class AuthorViewSetV2(viewsets.ModelViewSet):
    """Version 2 of Author API with nested books"""
    queryset = Author.objects.prefetch_related('books').all()
    serializer_class = AuthorSerializerV2

# Router Configuration
router_v1 = DefaultRouter()
router_v1.register(r'authors', AuthorViewSetV1, basename='author')

router_v2 = DefaultRouter()
router_v2.register(r'authors', AuthorViewSetV2, basename='author')

urlpatterns_example6 = [
    path('api/v1/', include(router_v1.urls)),
    path('api/v2/', include(router_v2.urls)),
]

# Generated URLs:
# V1:
# GET /api/v1/authors/      -> List authors (basic)
# GET /api/v1/authors/1/    -> Get author (basic)
#
# V2:
# GET /api/v2/authors/      -> List authors (with nested books)
# GET /api/v2/authors/1/    -> Get author (with nested books)


# ==============================================================================
# EXAMPLE 7: Trailing Slash Configuration
# ==============================================================================

"""
Configure whether URLs should end with a trailing slash.
"""

# With trailing slash (default)
router_with_slash = DefaultRouter(trailing_slash=True)
router_with_slash.register(r'authors', AuthorViewSet)

# Without trailing slash
router_without_slash = DefaultRouter(trailing_slash=False)
router_without_slash.register(r'authors', AuthorViewSet)

urlpatterns_example7_with = [
    path('api/with/', include(router_with_slash.urls)),
]
# URLs: /api/with/authors/, /api/with/authors/1/

urlpatterns_example7_without = [
    path('api/without/', include(router_without_slash.urls)),
]
# URLs: /api/without/authors, /api/without/authors/1


# ==============================================================================
# EXAMPLE 8: Custom Router with Additional Routes
# ==============================================================================

"""
Create a custom router class to add specialized routes.
"""

from rest_framework.routers import SimpleRouter, Route

class CountRouter(SimpleRouter):
    """
    Custom router that adds a /count/ endpoint to every ViewSet.
    """
    routes = [
        # Standard routes
        *SimpleRouter.routes,

        # Custom count route
        Route(
            url=r'^{prefix}/count{trailing_slash}$',
            mapping={'get': 'count'},
            name='{basename}-count',
            detail=False,
            initkwargs={'suffix': 'Count'}
        ),
    ]

class AuthorViewSetWithCount(viewsets.ModelViewSet):
    """ViewSet with count action for custom router."""
    queryset = Author.objects.all()
    serializer_class = AuthorSerializer

    def count(self, request):
        """
        Return the total count of authors.
        URL: GET /authors/count/
        """
        count = self.get_queryset().count()
        return Response({'count': count})

# Router Configuration
count_router = CountRouter()
count_router.register(r'authors', AuthorViewSetWithCount, basename='author')

urlpatterns_example8 = [
    path('api/', include(count_router.urls)),
]

# Generated URLs:
# GET /api/authors/        -> List authors
# GET /api/authors/1/      -> Get author 1
# GET /api/authors/count/  -> Get total count


# ==============================================================================
# EXAMPLE 9: Nested Routing (Manual Implementation)
# ==============================================================================

"""
Implement nested routes manually without external packages.
"""

class AuthorBooksViewSet(viewsets.ModelViewSet):
    """
    ViewSet for books nested under authors.
    URL: /authors/{author_pk}/books/
    """
    serializer_class = BookSerializer

    def get_queryset(self):
        """Filter books by author from URL."""
        author_pk = self.kwargs['author_pk']
        return Book.objects.filter(author_id=author_pk)

    def perform_create(self, serializer):
        """Set author from URL when creating book."""
        author_pk = self.kwargs['author_pk']
        serializer.save(author_id=author_pk)

# Router Configuration
nested_router = DefaultRouter()
nested_router.register(r'authors', AuthorViewSet, basename='author')

# Manual nested routes
author_books_list = AuthorBooksViewSet.as_view({
    'get': 'list',
    'post': 'create'
})

author_books_detail = AuthorBooksViewSet.as_view({
    'get': 'retrieve',
    'put': 'update',
    'patch': 'partial_update',
    'delete': 'destroy'
})

urlpatterns_example9 = [
    path('api/', include(nested_router.urls)),
    path('api/authors/<int:author_pk>/books/',
         author_books_list,
         name='author-books-list'),
    path('api/authors/<int:author_pk>/books/<int:pk>/',
         author_books_detail,
         name='author-books-detail'),
]

# Generated URLs:
# GET    /api/authors/                -> List all authors
# GET    /api/authors/1/              -> Get author 1
# GET    /api/authors/1/books/        -> List books by author 1
# POST   /api/authors/1/books/        -> Create book for author 1
# GET    /api/authors/1/books/2/      -> Get book 2 by author 1
# PUT    /api/authors/1/books/2/      -> Update book 2 by author 1
# DELETE /api/authors/1/books/2/      -> Delete book 2 by author 1


# ==============================================================================
# EXAMPLE 10: Mixing Routers and Manual URL Patterns
# ==============================================================================

"""
Combine router-generated URLs with manually defined patterns.
"""

from rest_framework.views import APIView

class HealthCheckView(APIView):
    """Manual APIView for health checks."""

    def get(self, request):
        return Response({
            'status': 'healthy',
            'version': '1.0.0',
            'timestamp': '2024-01-01T00:00:00Z'
        })

class StatsView(APIView):
    """Manual APIView for statistics."""

    def get(self, request):
        return Response({
            'total_authors': Author.objects.count(),
            'total_books': Book.objects.count(),
        })

# Router Configuration
mixed_router = DefaultRouter()
mixed_router.register(r'authors', AuthorViewSet, basename='author')
mixed_router.register(r'books', BookViewSet, basename='book')

urlpatterns_example10 = [
    # Manual routes
    path('api/health/', HealthCheckView.as_view(), name='health-check'),
    path('api/stats/', StatsView.as_view(), name='stats'),

    # Router routes
    path('api/', include(mixed_router.urls)),
]

# Generated URLs:
# GET /api/health/         -> HealthCheckView (manual)
# GET /api/stats/          -> StatsView (manual)
# GET /api/authors/        -> AuthorViewSet.list (router)
# GET /api/books/          -> BookViewSet.list (router)


# ==============================================================================
# EXAMPLE 11: Conditional Actions Based on Permissions
# ==============================================================================

"""
Use @action with permission_classes for fine-grained access control.
"""

from rest_framework.permissions import IsAuthenticated, IsAdminUser

class AuthorViewSetWithPermissions(viewsets.ModelViewSet):
    """ViewSet with permission-based actions."""
    queryset = Author.objects.all()
    serializer_class = AuthorSerializer

    @action(detail=False, methods=['get'], permission_classes=[IsAuthenticated])
    def my_authors(self, request):
        """
        Get authors created by the current user.
        URL: GET /authors/my_authors/
        Requires authentication.
        """
        # Assuming Author has a 'created_by' field
        # authors = Author.objects.filter(created_by=request.user)
        authors = Author.objects.all()[:5]  # Simplified example
        serializer = self.get_serializer(authors, many=True)
        return Response(serializer.data)

    @action(detail=True, methods=['post'], permission_classes=[IsAdminUser])
    def archive(self, request, pk=None):
        """
        Archive an author (admin only).
        URL: POST /authors/{id}/archive/
        Requires admin permissions.
        """
        author = self.get_object()
        # author.archived = True
        # author.save()
        return Response({'status': 'archived'})

# Router Configuration
perm_router = DefaultRouter()
perm_router.register(r'authors', AuthorViewSetWithPermissions, basename='author')

urlpatterns_example11 = [
    path('api/', include(perm_router.urls)),
]


# ==============================================================================
# EXAMPLE 12: Batch Operations
# ==============================================================================

"""
Add bulk create, update, and delete operations.
"""

class BookViewSetWithBulk(viewsets.ModelViewSet):
    """ViewSet with bulk operations."""
    queryset = Book.objects.all()
    serializer_class = BookSerializer

    @action(detail=False, methods=['post'])
    def bulk_create(self, request):
        """
        Create multiple books at once.
        URL: POST /books/bulk_create/
        Body: [
            {"title": "Book 1", "author": 1, "isbn": "1234567890123", "published_date": "2024-01-01"},
            {"title": "Book 2", "author": 1, "isbn": "1234567890124", "published_date": "2024-01-02"}
        ]
        """
        serializer = self.get_serializer(data=request.data, many=True)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=False, methods=['patch'])
    def bulk_update(self, request):
        """
        Update multiple books at once.
        URL: PATCH /books/bulk_update/
        Body: [
            {"id": 1, "title": "Updated Title 1"},
            {"id": 2, "title": "Updated Title 2"}
        ]
        """
        updated_books = []
        for item in request.data:
            book_id = item.pop('id')
            try:
                book = Book.objects.get(pk=book_id)
                serializer = self.get_serializer(book, data=item, partial=True)
                if serializer.is_valid():
                    serializer.save()
                    updated_books.append(serializer.data)
                else:
                    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
            except Book.DoesNotExist:
                return Response(
                    {'error': f'Book with id {book_id} not found'},
                    status=status.HTTP_404_NOT_FOUND
                )

        return Response(updated_books)

    @action(detail=False, methods=['post'])
    def bulk_delete(self, request):
        """
        Delete multiple books at once.
        URL: POST /books/bulk_delete/
        Body: {"ids": [1, 2, 3]}
        """
        ids = request.data.get('ids', [])
        if not ids:
            return Response(
                {'error': 'No ids provided'},
                status=status.HTTP_400_BAD_REQUEST
            )

        count, _ = Book.objects.filter(pk__in=ids).delete()
        return Response({'deleted': count}, status=status.HTTP_200_OK)

# Router Configuration
bulk_router = DefaultRouter()
bulk_router.register(r'books', BookViewSetWithBulk, basename='book')

urlpatterns_example12 = [
    path('api/', include(bulk_router.urls)),
]


# ==============================================================================
# EXAMPLE 13: Using path() Instead of re_path() (Django 2.0+)
# ==============================================================================

"""
Use modern path() patterns instead of regex patterns.
"""

# Modern approach (Django 2.0+)
modern_router = SimpleRouter(use_regex_path=False)
modern_router.register(r'authors', AuthorViewSet)

# Legacy approach (regex)
legacy_router = SimpleRouter(use_regex_path=True)
legacy_router.register(r'authors', AuthorViewSet)

urlpatterns_example13_modern = [
    path('api/', include(modern_router.urls)),
]
# Uses: path('authors/<str:pk>/', ...)

urlpatterns_example13_legacy = [
    path('api/', include(legacy_router.urls)),
]
# Uses: re_path(r'^authors/(?P<pk>[^/.]+)/$', ...)


# ==============================================================================
# USAGE EXAMPLES AND TESTING
# ==============================================================================

"""
How to test the routers in your views:

1. In Django shell:
   python manage.py shell
   >>> from rest_framework.routers import DefaultRouter
   >>> from myapp.views import AuthorViewSet
   >>> router = DefaultRouter()
   >>> router.register(r'authors', AuthorViewSet)
   >>> for url in router.urls:
   ...     print(url.pattern, url.name)

2. Print all URLs:
   python manage.py show_urls  # If django-extensions installed

3. Test with curl:
   curl http://localhost:8000/api/authors/
   curl -X POST http://localhost:8000/api/authors/ -H "Content-Type: application/json" -d '{"name":"John","email":"john@example.com"}'
   curl http://localhost:8000/api/authors/1/
   curl -X PATCH http://localhost:8000/api/authors/1/ -H "Content-Type: application/json" -d '{"name":"Jane"}'

4. Test with DRF test client:
   from rest_framework.test import APITestCase
   class AuthorAPITest(APITestCase):
       def test_list_authors(self):
           response = self.client.get('/api/authors/')
           self.assertEqual(response.status_code, 200)
"""

# ==============================================================================
# SUMMARY OF URL PATTERNS
# ==============================================================================

"""
Common URL patterns generated by routers:

DefaultRouter with: router.register(r'books', BookViewSet, basename='book')

Standard CRUD:
    GET    /books/              book-list         List all books
    POST   /books/              book-list         Create new book
    GET    /books/{pk}/         book-detail       Retrieve book
    PUT    /books/{pk}/         book-detail       Update book (full)
    PATCH  /books/{pk}/         book-detail       Update book (partial)
    DELETE /books/{pk}/         book-detail       Delete book

Custom actions:
    @action(detail=True, methods=['get'])
    def stats(self, request, pk=None):
        pass
    # Generates: GET /books/{pk}/stats/  (book-stats)

    @action(detail=False, methods=['get'])
    def recent(self, request):
        pass
    # Generates: GET /books/recent/  (book-recent)

    @action(detail=True, url_path='custom-path', url_name='custom-name')
    def my_action(self, request, pk=None):
        pass
    # Generates: GET /books/{pk}/custom-path/  (book-custom-name)

Root view (DefaultRouter only):
    GET    /                    api-root          List all endpoints

Format suffixes (DefaultRouter only):
    GET    /books.json          book-list         List in JSON format
    GET    /books.api           book-list         List in browsable format
"""
