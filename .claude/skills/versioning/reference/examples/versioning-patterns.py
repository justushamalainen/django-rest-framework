"""
API Versioning Patterns - Working Code Examples

This file contains practical examples of URLPathVersioning (recommended)
and AcceptHeaderVersioning (alternative).

Source reference: /home/user/django-rest-framework/rest_framework/versioning.py
"""

# =============================================================================
# URLPathVersioning (Recommended)
# =============================================================================

# --- Settings Configuration ---
REST_FRAMEWORK = {
    'DEFAULT_VERSIONING_CLASS': 'rest_framework.versioning.URLPathVersioning',
    'DEFAULT_VERSION': 'v1',
    'ALLOWED_VERSIONS': ['v1', 'v2', 'v3'],
    'VERSION_PARAM': 'version',
}

# --- Serializers ---
from rest_framework import serializers

class BookSerializerV1(serializers.ModelSerializer):
    """Version 1: Simple structure"""
    author_name = serializers.CharField(source='author.name', read_only=True)

    class Meta:
        model = Book
        fields = ['id', 'title', 'author_name', 'price']


class BookSerializerV2(serializers.ModelSerializer):
    """Version 2: Nested author, added ISBN"""
    author = AuthorSerializer(read_only=True)

    class Meta:
        model = Book
        fields = ['id', 'title', 'author', 'isbn', 'price']


# --- Views ---
from rest_framework import viewsets

class BookViewSet(viewsets.ModelViewSet):
    """ViewSet that serves different serializers based on API version"""
    queryset = Book.objects.all()

    def get_serializer_class(self):
        """Return version-specific serializer"""
        if self.request.version == 'v1':
            return BookSerializerV1
        return BookSerializerV2

    def get_queryset(self):
        """Version-specific query optimization"""
        queryset = Book.objects.all()

        if self.request.version == 'v1':
            # V1: Only published books
            return queryset.filter(published=True)
        else:
            # V2+: All books with optimizations
            return queryset.select_related('author')


# --- URL Configuration ---
from django.urls import path, include
from rest_framework import routers

router_v1 = routers.DefaultRouter()
router_v1.register(r'books', BookViewSet)

router_v2 = routers.DefaultRouter()
router_v2.register(r'books', BookViewSet)

urlpatterns = [
    path('api/v1/', include(router_v1.urls)),
    path('api/v2/', include(router_v2.urls)),
]

# Usage:
# GET /api/v1/books/
# GET /api/v2/books/


# =============================================================================
# AcceptHeaderVersioning (Alternative)
# =============================================================================

# If you prefer RESTful approach with clean URLs:

ACCEPT_HEADER_SETTINGS = {
    'DEFAULT_VERSIONING_CLASS': 'rest_framework.versioning.AcceptHeaderVersioning',
    'DEFAULT_VERSION': '1.0',
    'ALLOWED_VERSIONS': ['1.0', '2.0'],
}

# Same views and serializers work, but URLs are simpler:
router = routers.DefaultRouter()
router.register(r'books', BookViewSet)

urlpatterns_accept = [
    path('api/', include(router.urls)),
]

# Usage:
# curl -H "Accept: application/json; version=1.0" http://localhost:8000/api/books/
# curl -H "Accept: application/json; version=2.0" http://localhost:8000/api/books/


# =============================================================================
# Testing Versioned APIs
# =============================================================================

from rest_framework.test import APITestCase

class BookVersioningTestCase(APITestCase):
    """Test all API versions"""

    def setUp(self):
        self.book = Book.objects.create(
            title="Test Book",
            author=Author.objects.create(name="Test Author"),
            isbn="1234567890123",
            price="29.99",
            published=True
        )

    def test_v1_returns_author_name(self):
        """V1 should return author as string"""
        response = self.client.get('/api/v1/books/')
        self.assertEqual(response.status_code, 200)
        self.assertIn('author_name', response.data[0])

    def test_v2_returns_nested_author(self):
        """V2 should return author as object"""
        response = self.client.get('/api/v2/books/')
        self.assertEqual(response.status_code, 200)
        self.assertIn('author', response.data[0])
        self.assertIn('isbn', response.data[0])
