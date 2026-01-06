"""
API Versioning Patterns - Working Code Examples

This file contains complete, working examples of all DRF versioning patterns.
Copy and adapt these patterns for your own API versioning needs.

Each pattern includes:
- Complete settings configuration
- URL configuration
- Model definitions
- Serializers (all versions)
- Views (all versions)
- Usage examples

Source reference: /home/user/django-rest-framework/rest_framework/versioning.py
"""

# =============================================================================
# Pattern 1: URLPathVersioning (Most Common)
# =============================================================================

# --- Settings Configuration ---
URLPATH_VERSIONING_SETTINGS = {
    'DEFAULT_VERSIONING_CLASS': 'rest_framework.versioning.URLPathVersioning',
    'DEFAULT_VERSION': 'v1',
    'ALLOWED_VERSIONS': ['v1', 'v2', 'v3'],
    'VERSION_PARAM': 'version',
}

# --- Models ---
from django.db import models
from django.contrib.auth.models import User

class Author(models.Model):
    name = models.CharField(max_length=100)
    email = models.EmailField()
    birth_date = models.DateField(null=True, blank=True)
    bio = models.TextField(blank=True)

    def __str__(self):
        return self.name


class Category(models.Model):
    name = models.CharField(max_length=50)
    slug = models.SlugField(unique=True)

    def __str__(self):
        return self.name


class Book(models.Model):
    title = models.CharField(max_length=200)
    author = models.ForeignKey(Author, on_delete=models.CASCADE, related_name='books')
    isbn = models.CharField(max_length=13, unique=True, blank=True, default='')
    pages = models.IntegerField()
    price = models.DecimalField(max_digits=8, decimal_places=2)
    published_date = models.DateField()
    published = models.BooleanField(default=False)
    categories = models.ManyToManyField(Category, related_name='books', blank=True)

    class Meta:
        ordering = ['-published_date']

    def __str__(self):
        return self.title


# --- Serializers V1 ---
from rest_framework import serializers

class AuthorSerializerV1(serializers.ModelSerializer):
    """V1: Simple author representation"""
    class Meta:
        model = Author
        fields = ['id', 'name']


class BookSerializerV1(serializers.ModelSerializer):
    """V1: Simple structure, author as string"""
    author_name = serializers.CharField(source='author.name', read_only=True)

    class Meta:
        model = Book
        fields = ['id', 'title', 'author_name', 'price', 'published_date']
        read_only_fields = ['id']


# --- Serializers V2 ---
class AuthorSerializerV2(serializers.ModelSerializer):
    """V2: Full author details"""
    book_count = serializers.IntegerField(source='books.count', read_only=True)

    class Meta:
        model = Author
        fields = ['id', 'name', 'email', 'book_count']


class BookSerializerV2(serializers.ModelSerializer):
    """V2: Nested author, added ISBN"""
    author = AuthorSerializerV2(read_only=True)
    author_id = serializers.PrimaryKeyRelatedField(
        queryset=Author.objects.all(),
        source='author',
        write_only=True
    )

    class Meta:
        model = Book
        fields = ['id', 'title', 'author', 'author_id', 'isbn', 'price', 'published_date']
        read_only_fields = ['id']

    def validate_isbn(self, value):
        """V2 requires valid ISBN"""
        if value and (not value.isdigit() or len(value) != 13):
            raise serializers.ValidationError("ISBN must be exactly 13 digits")
        return value


# --- Serializers V3 ---
class CategorySerializer(serializers.ModelSerializer):
    class Meta:
        model = Category
        fields = ['id', 'name', 'slug']


class BookSerializerV3(serializers.ModelSerializer):
    """V3: Added categories (M2M)"""
    author = AuthorSerializerV2(read_only=True)
    author_id = serializers.PrimaryKeyRelatedField(
        queryset=Author.objects.all(),
        source='author',
        write_only=True
    )
    categories = CategorySerializer(many=True, read_only=True)
    category_ids = serializers.PrimaryKeyRelatedField(
        queryset=Category.objects.all(),
        many=True,
        write_only=True,
        required=False
    )

    class Meta:
        model = Book
        fields = [
            'id', 'title', 'author', 'author_id',
            'isbn', 'price', 'published_date', 'published',
            'categories', 'category_ids'
        ]
        read_only_fields = ['id']

    def create(self, validated_data):
        category_ids = validated_data.pop('category_ids', [])
        book = Book.objects.create(**validated_data)
        book.categories.set(category_ids)
        return book

    def update(self, instance, validated_data):
        category_ids = validated_data.pop('category_ids', None)

        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        instance.save()

        if category_ids is not None:
            instance.categories.set(category_ids)

        return instance


# --- Views ---
from rest_framework import viewsets, filters
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticatedOrReadOnly


class BookViewSet(viewsets.ModelViewSet):
    """
    ViewSet that serves different serializers based on API version.

    Supports v1, v2, and v3 with different features per version.
    """
    queryset = Book.objects.all()
    permission_classes = [IsAuthenticatedOrReadOnly]
    filter_backends = [filters.SearchFilter, filters.OrderingFilter]
    search_fields = ['title', 'author__name']
    ordering_fields = ['published_date', 'price', 'title']

    def get_serializer_class(self):
        """Return version-specific serializer"""
        if self.request.version == 'v1':
            return BookSerializerV1
        elif self.request.version == 'v2':
            return BookSerializerV2
        return BookSerializerV3

    def get_queryset(self):
        """Version-specific query optimization"""
        queryset = Book.objects.all()

        if self.request.version == 'v1':
            # V1: Only published books, no optimization
            return queryset.filter(published=True)

        elif self.request.version == 'v2':
            # V2: Select related author
            return queryset.select_related('author')

        else:
            # V3: Full optimization with categories
            return queryset.select_related('author').prefetch_related('categories')

    @action(detail=True, methods=['post'])
    def publish(self, request, pk=None):
        """
        Publish a book - behavior varies by version.

        V1: Simple publish
        V2: Requires ISBN
        V3: Sends notifications
        """
        book = self.get_object()

        if request.version == 'v1':
            # V1: Simple publish
            book.published = True
            book.save()
            return Response({'status': 'published'})

        elif request.version == 'v2':
            # V2: Validate ISBN required
            if not book.isbn:
                return Response(
                    {'error': 'ISBN is required to publish in v2'},
                    status=400
                )
            book.published = True
            book.save()
            return Response({
                'status': 'published',
                'isbn': book.isbn
            })

        else:
            # V3: Full validation and response
            if not book.isbn:
                return Response(
                    {'error': 'ISBN is required to publish'},
                    status=400
                )
            if not book.categories.exists():
                return Response(
                    {'error': 'At least one category is required in v3'},
                    status=400
                )

            book.published = True
            book.save()

            return Response({
                'status': 'published',
                'isbn': book.isbn,
                'categories': [cat.name for cat in book.categories.all()],
                'notification_sent': True  # Simulated
            })


# --- URL Configuration (Option 1: Regex) ---
from django.urls import re_path

urlpatterns_regex = [
    re_path(
        r'^api/(?P<version>v[1-3])/books/$',
        BookViewSet.as_view({'get': 'list', 'post': 'create'}),
        name='book-list'
    ),
    re_path(
        r'^api/(?P<version>v[1-3])/books/(?P<pk>[0-9]+)/$',
        BookViewSet.as_view({
            'get': 'retrieve',
            'put': 'update',
            'patch': 'partial_update',
            'delete': 'destroy'
        }),
        name='book-detail'
    ),
    re_path(
        r'^api/(?P<version>v[1-3])/books/(?P<pk>[0-9]+)/publish/$',
        BookViewSet.as_view({'post': 'publish'}),
        name='book-publish'
    ),
]

# --- URL Configuration (Option 2: Routers - Cleaner) ---
from django.urls import path, include
from rest_framework import routers

# V1 Router
router_v1 = routers.DefaultRouter()
router_v1.register(r'books', BookViewSet, basename='book')

# V2 Router
router_v2 = routers.DefaultRouter()
router_v2.register(r'books', BookViewSet, basename='book')

# V3 Router
router_v3 = routers.DefaultRouter()
router_v3.register(r'books', BookViewSet, basename='book')

urlpatterns_routers = [
    path('api/v1/', include(router_v1.urls)),
    path('api/v2/', include(router_v2.urls)),
    path('api/v3/', include(router_v3.urls)),
]


# =============================================================================
# Pattern 2: AcceptHeaderVersioning
# =============================================================================

ACCEPT_HEADER_VERSIONING_SETTINGS = {
    'DEFAULT_VERSIONING_CLASS': 'rest_framework.versioning.AcceptHeaderVersioning',
    'DEFAULT_VERSION': '1.0',
    'ALLOWED_VERSIONS': ['1.0', '2.0', '3.0'],
    'VERSION_PARAM': 'version',
}

# Same models and serializers, but version accessed differently

class BookViewSetAcceptHeader(viewsets.ModelViewSet):
    """ViewSet using Accept header versioning"""
    queryset = Book.objects.all()

    def get_serializer_class(self):
        """Map version from Accept header"""
        version_map = {
            '1.0': BookSerializerV1,
            '2.0': BookSerializerV2,
            '3.0': BookSerializerV3,
        }
        return version_map.get(self.request.version, BookSerializerV3)


# URL Configuration (clean, no version in URL)
from rest_framework import routers

router_accept = routers.DefaultRouter()
router_accept.register(r'books', BookViewSetAcceptHeader)

urlpatterns_accept = [
    path('api/', include(router_accept.urls)),
]

# Usage:
"""
curl -H "Accept: application/json; version=1.0" http://localhost:8000/api/books/
curl -H "Accept: application/json; version=2.0" http://localhost:8000/api/books/
"""


# =============================================================================
# Pattern 3: NamespaceVersioning
# =============================================================================

NAMESPACE_VERSIONING_SETTINGS = {
    'DEFAULT_VERSIONING_CLASS': 'rest_framework.versioning.NamespaceVersioning',
    'DEFAULT_VERSION': 'v1',
    'ALLOWED_VERSIONS': ['v1', 'v2', 'v3'],
}

# Organize views by version module
# myapp/views/v1.py
class BookViewSetV1(viewsets.ModelViewSet):
    """V1 specific implementation"""
    queryset = Book.objects.filter(published=True)
    serializer_class = BookSerializerV1


# myapp/views/v2.py
class BookViewSetV2(viewsets.ModelViewSet):
    """V2 specific implementation"""
    queryset = Book.objects.select_related('author')
    serializer_class = BookSerializerV2


# myapp/views/v3.py
class BookViewSetV3(viewsets.ModelViewSet):
    """V3 specific implementation"""
    queryset = Book.objects.select_related('author').prefetch_related('categories')
    serializer_class = BookSerializerV3


# URL Configuration with namespaces
router_ns_v1 = routers.DefaultRouter()
router_ns_v1.register(r'books', BookViewSetV1)

router_ns_v2 = routers.DefaultRouter()
router_ns_v2.register(r'books', BookViewSetV2)

router_ns_v3 = routers.DefaultRouter()
router_ns_v3.register(r'books', BookViewSetV3)

urlpatterns_namespace = [
    path('api/v1/', include((router_ns_v1.urls, 'v1'))),
    path('api/v2/', include((router_ns_v2.urls, 'v2'))),
    path('api/v3/', include((router_ns_v3.urls, 'v3'))),
]


# =============================================================================
# Pattern 4: QueryParameterVersioning
# =============================================================================

QUERY_PARAM_VERSIONING_SETTINGS = {
    'DEFAULT_VERSIONING_CLASS': 'rest_framework.versioning.QueryParameterVersioning',
    'DEFAULT_VERSION': 'v1',
    'ALLOWED_VERSIONS': ['v1', 'v2', 'v3'],
    'VERSION_PARAM': 'version',
}

# Same viewset as URLPath
class BookViewSetQueryParam(viewsets.ModelViewSet):
    """ViewSet using query parameter versioning"""
    queryset = Book.objects.all()

    def get_serializer_class(self):
        if self.request.version == 'v1':
            return BookSerializerV1
        elif self.request.version == 'v2':
            return BookSerializerV2
        return BookSerializerV3


# URL Configuration (simple, no version in path)
router_qp = routers.DefaultRouter()
router_qp.register(r'books', BookViewSetQueryParam)

urlpatterns_query_param = [
    path('api/', include(router_qp.urls)),
]

# Usage:
"""
curl "http://localhost:8000/api/books/?version=v1"
curl "http://localhost:8000/api/books/?version=v2"
curl "http://localhost:8000/api/books/?version=v3&search=django"
"""


# =============================================================================
# Pattern 5: HostNameVersioning
# =============================================================================

HOSTNAME_VERSIONING_SETTINGS = {
    'DEFAULT_VERSIONING_CLASS': 'rest_framework.versioning.HostNameVersioning',
    'DEFAULT_VERSION': 'v1',
    'ALLOWED_VERSIONS': ['v1', 'v2', 'v3'],
}

# Additional Django settings required
HOSTNAME_DJANGO_SETTINGS = {
    'ALLOWED_HOSTS': [
        'v1.api.example.com',
        'v2.api.example.com',
        'v3.api.example.com',
    ]
}

# Same viewset logic
class BookViewSetHostname(viewsets.ModelViewSet):
    """ViewSet using hostname versioning"""
    queryset = Book.objects.all()

    def get_serializer_class(self):
        if self.request.version == 'v1':
            return BookSerializerV1
        elif self.request.version == 'v2':
            return BookSerializerV2
        return BookSerializerV3


# URL Configuration (simple)
router_hostname = routers.DefaultRouter()
router_hostname.register(r'books', BookViewSetHostname)

urlpatterns_hostname = [
    path('', include(router_hostname.urls)),
]

# Usage (requires DNS setup):
"""
curl https://v1.api.example.com/books/
curl https://v2.api.example.com/books/
curl https://v3.api.example.com/books/
"""


# =============================================================================
# Pattern 6: Version-Specific Permissions
# =============================================================================

from rest_framework import permissions

class VersionBasedPermission(permissions.BasePermission):
    """
    Custom permission that varies by version.

    V1: Read-only for everyone
    V2: Authenticated users can create
    V3: Full CRUD for authenticated users
    """

    def has_permission(self, request, view):
        if request.version == 'v1':
            # V1: Read-only
            return request.method in permissions.SAFE_METHODS

        elif request.version == 'v2':
            # V2: Authenticated can read/create
            if request.method in permissions.SAFE_METHODS:
                return True
            return request.user and request.user.is_authenticated

        else:
            # V3: Full CRUD for authenticated
            return request.user and request.user.is_authenticated


class BookViewSetWithVersionPermission(viewsets.ModelViewSet):
    """ViewSet with version-based permissions"""
    queryset = Book.objects.all()
    serializer_class = BookSerializerV3
    permission_classes = [VersionBasedPermission]


# =============================================================================
# Pattern 7: Deprecation Warning Middleware
# =============================================================================

class DeprecationWarningMixin:
    """
    Mixin to add deprecation warnings to responses.

    Add to any ViewSet to warn about deprecated versions.
    """

    deprecated_versions = ['v1']
    deprecation_message = "This API version is deprecated"
    sunset_date = "2024-12-31"
    migration_url = "https://docs.example.com/api/migration"

    def finalize_response(self, request, response, *args, **kwargs):
        """Add deprecation headers"""
        response = super().finalize_response(request, response, *args, **kwargs)

        if request.version in self.deprecated_versions:
            # Warning header (RFC 7234)
            response['Warning'] = (
                f'299 - "{self.deprecation_message}. '
                f'Will be removed on {self.sunset_date}. '
                f'See migration guide: {self.migration_url}"'
            )

            # Sunset header (RFC 8594)
            from datetime import datetime
            sunset = datetime.strptime(self.sunset_date, '%Y-%m-%d')
            response['Sunset'] = sunset.strftime('%a, %d %b %Y %H:%M:%S GMT')

        return response


class BookViewSetWithDeprecation(DeprecationWarningMixin, viewsets.ModelViewSet):
    """ViewSet that warns about deprecated versions"""
    deprecated_versions = ['v1']
    queryset = Book.objects.all()
    serializer_class = BookSerializerV3


# =============================================================================
# Pattern 8: Testing Versioned APIs
# =============================================================================

from rest_framework.test import APITestCase

class BookVersioningTestCase(APITestCase):
    """Test all API versions"""

    def setUp(self):
        """Create test data"""
        self.author = Author.objects.create(
            name="Test Author",
            email="test@example.com"
        )
        self.book = Book.objects.create(
            title="Test Book",
            author=self.author,
            isbn="1234567890123",
            pages=300,
            price="29.99",
            published_date="2024-01-15",
            published=True
        )

    def test_v1_returns_author_name_string(self):
        """V1 should return author as string"""
        response = self.client.get('/api/v1/books/')
        self.assertEqual(response.status_code, 200)
        self.assertIn('author_name', response.data[0])
        self.assertEqual(response.data[0]['author_name'], 'Test Author')
        self.assertNotIn('isbn', response.data[0])  # ISBN not in v1

    def test_v2_returns_nested_author(self):
        """V2 should return author as object"""
        response = self.client.get('/api/v2/books/')
        self.assertEqual(response.status_code, 200)
        self.assertIn('author', response.data[0])
        self.assertIsInstance(response.data[0]['author'], dict)
        self.assertIn('isbn', response.data[0])  # ISBN in v2

    def test_v3_returns_categories(self):
        """V3 should return categories"""
        response = self.client.get('/api/v3/books/')
        self.assertEqual(response.status_code, 200)
        self.assertIn('categories', response.data[0])

    def test_invalid_version_returns_404(self):
        """Invalid version should return 404"""
        response = self.client.get('/api/v99/books/')
        self.assertEqual(response.status_code, 404)

    def test_default_version_used(self):
        """When no version specified, use default"""
        response = self.client.get('/api/books/')
        self.assertEqual(response.wsgi_request.version, 'v1')  # DEFAULT_VERSION


# =============================================================================
# Usage Examples
# =============================================================================

"""
# 1. URLPathVersioning
GET  /api/v1/books/
POST /api/v2/books/
GET  /api/v3/books/123/

# 2. AcceptHeaderVersioning
curl -H "Accept: application/json; version=1.0" http://localhost:8000/api/books/

# 3. NamespaceVersioning
GET /api/v1/books/  # Uses namespace 'v1'

# 4. QueryParameterVersioning
GET /api/books/?version=v1
GET /api/books/?version=v2&search=django

# 5. HostNameVersioning
GET https://v1.api.example.com/books/
GET https://v2.api.example.com/books/

# Creating a book in different versions

# V1 (simple, no ISBN)
POST /api/v1/books/
{
    "title": "Django Book",
    "author_name": "Jane Smith",
    "price": "39.99",
    "published_date": "2024-01-15"
}

# V2 (requires author_id and ISBN)
POST /api/v2/books/
{
    "title": "Django Book",
    "author_id": 5,
    "isbn": "1234567890123",
    "price": "39.99",
    "published_date": "2024-01-15"
}

# V3 (includes categories)
POST /api/v3/books/
{
    "title": "Django Book",
    "author_id": 5,
    "isbn": "1234567890123",
    "price": "39.99",
    "published_date": "2024-01-15",
    "category_ids": [1, 3, 5]
}
"""


# =============================================================================
# Summary of All Patterns
# =============================================================================

"""
Pattern 1: URLPathVersioning
- Most common and user-friendly
- Version in URL: /api/v1/books/
- Easy to test and document

Pattern 2: AcceptHeaderVersioning
- RESTful approach
- Version in Accept header
- Clean URLs

Pattern 3: NamespaceVersioning
- Uses Django namespaces
- Separate view modules per version
- Good for large projects

Pattern 4: QueryParameterVersioning
- Version as query param: ?version=v1
- Simplest to implement
- Less clean URLs

Pattern 5: HostNameVersioning
- Version in subdomain: v1.api.example.com
- Requires DNS/infrastructure setup
- Good for microservices

Pattern 6: Version-Specific Permissions
- Different permissions per version
- Gradual feature rollout

Pattern 7: Deprecation Warnings
- Add Warning/Sunset headers
- Guide users to migrate

Pattern 8: Comprehensive Testing
- Test all versions
- Ensure backwards compatibility

Choose based on your needs:
- Public API: URLPathVersioning
- Enterprise/Mobile: AcceptHeaderVersioning
- Large Django project: NamespaceVersioning
- Quick prototype: QueryParameterVersioning
- Microservices: HostNameVersioning
"""
