# Version Handling - Essential Patterns

This document covers how to access version information and implement version-specific logic in your Django REST Framework API.

## Table of Contents

1. [Accessing Version Information](#accessing-version-information)
2. [Version-Specific Serializers](#version-specific-serializers)
3. [Version-Specific View Logic](#version-specific-view-logic)
4. [Deprecation Pattern](#deprecation-pattern)
5. [Testing Versioned APIs](#testing-versioned-apis)

---

## Accessing Version Information

### In Views

The version is available via `request.version`:

```python
from rest_framework.views import APIView
from rest_framework.response import Response

class BookListView(APIView):
    def get(self, request):
        version = request.version  # 'v1', 'v2', etc.

        if version == 'v1':
            data = {'message': 'Version 1'}
        else:
            data = {'message': 'Version 2+'}

        return Response(data)
```

### In ViewSets

```python
from rest_framework import viewsets

class BookViewSet(viewsets.ModelViewSet):
    queryset = Book.objects.all()

    def list(self, request, *args, **kwargs):
        version = request.version
        print(f"Serving version: {version}")
        return super().list(request, *args, **kwargs)
```

---

## Version-Specific Serializers

### Using get_serializer_class() (Recommended)

This is the simplest and most common pattern for handling version differences:

```python
from rest_framework import viewsets
from myapp.serializers import BookSerializerV1, BookSerializerV2, BookSerializerV3

class BookViewSet(viewsets.ModelViewSet):
    queryset = Book.objects.all()

    def get_serializer_class(self):
        """Return version-specific serializer"""
        if self.request.version == 'v1':
            return BookSerializerV1
        elif self.request.version == 'v2':
            return BookSerializerV2
        return BookSerializerV3  # Default to latest
```

### Example Serializers

```python
from rest_framework import serializers

# Version 1: Simple structure
class BookSerializerV1(serializers.ModelSerializer):
    author_name = serializers.CharField(source='author.name', read_only=True)

    class Meta:
        model = Book
        fields = ['id', 'title', 'author_name', 'price']


# Version 2: Nested author, added ISBN
class BookSerializerV2(serializers.ModelSerializer):
    author = AuthorSerializer(read_only=True)
    isbn = serializers.CharField(max_length=13)

    class Meta:
        model = Book
        fields = ['id', 'title', 'author', 'isbn', 'price']


# Version 3: Added categories
class BookSerializerV3(serializers.ModelSerializer):
    author = AuthorSerializer(read_only=True)
    categories = CategorySerializer(many=True, read_only=True)

    class Meta:
        model = Book
        fields = ['id', 'title', 'author', 'isbn', 'price', 'categories']
```

---

## Version-Specific View Logic

### Conditional Querysets

```python
class BookViewSet(viewsets.ModelViewSet):
    serializer_class = BookSerializer

    def get_queryset(self):
        """Version-specific filtering and optimization"""
        queryset = Book.objects.all()

        if self.request.version == 'v1':
            # V1: Only return published books
            return queryset.filter(published=True)
        elif self.request.version == 'v2':
            # V2: Return all, select related author
            return queryset.select_related('author')
        else:
            # V3+: Full optimization
            return queryset.select_related('author').prefetch_related('categories')
```

### Version-Specific Actions

```python
from rest_framework.decorators import action
from rest_framework.response import Response

class BookViewSet(viewsets.ModelViewSet):
    queryset = Book.objects.all()
    serializer_class = BookSerializer

    @action(detail=True, methods=['post'])
    def publish(self, request, pk=None):
        """Publish behavior changes by version"""
        book = self.get_object()

        if request.version == 'v1':
            # V1: Simple publish
            book.published = True
            book.save()
            return Response({'status': 'published'})

        else:
            # V2+: Publish with validation
            if not book.isbn:
                return Response(
                    {'error': 'ISBN required to publish'},
                    status=400
                )
            book.published = True
            book.save()
            return Response({'status': 'published', 'isbn': book.isbn})
```

---

## Deprecation Pattern

### Adding Warning Headers

When deprecating an old version, add a Warning header to inform clients:

```python
class BookViewSet(viewsets.ModelViewSet):
    queryset = Book.objects.all()
    serializer_class = BookSerializer

    def finalize_response(self, request, response, *args, **kwargs):
        """Add deprecation header to all responses"""
        response = super().finalize_response(request, response, *args, **kwargs)

        if request.version == 'v1':
            response['Warning'] = (
                '299 - "API v1 is deprecated. '
                'Will be removed on 2024-12-31. '
                'Please migrate to v2."'
            )

        return response
```

---

## Testing Versioned APIs

### Test All Versions

Always test all supported versions to ensure backwards compatibility:

```python
from rest_framework.test import APITestCase

class BookAPITestCase(APITestCase):
    def setUp(self):
        self.author = Author.objects.create(name="Test Author")
        self.book = Book.objects.create(
            title="Test Book",
            author=self.author,
            isbn="1234567890123",
            price="29.99",
            published=True
        )

    def test_v1_endpoint(self):
        """Test v1 returns correct fields"""
        response = self.client.get('/api/v1/books/')
        self.assertEqual(response.status_code, 200)
        # V1 has author_name, not nested author
        self.assertIn('author_name', response.data[0])
        self.assertNotIn('isbn', response.data[0])

    def test_v2_endpoint(self):
        """Test v2 returns nested author and ISBN"""
        response = self.client.get('/api/v2/books/')
        self.assertEqual(response.status_code, 200)
        self.assertIn('author', response.data[0])
        self.assertIn('isbn', response.data[0])

    def test_invalid_version_returns_404(self):
        """Invalid version should return 404"""
        response = self.client.get('/api/v99/books/')
        self.assertEqual(response.status_code, 404)
```

### Test Deprecation Warnings

```python
class DeprecationTestCase(APITestCase):
    def test_v1_deprecation_warning(self):
        """Test that v1 includes deprecation warning"""
        response = self.client.get('/api/v1/books/')
        self.assertIn('Warning', response)
        self.assertIn('deprecated', response['Warning'].lower())

    def test_v2_no_deprecation(self):
        """Test that v2 doesn't include warning"""
        response = self.client.get('/api/v2/books/')
        self.assertNotIn('Warning', response)
```

---

## Best Practices

1. **Always provide a default version** - Don't leave clients guessing
2. **Use get_serializer_class()** - Simplest pattern for version-specific serializers
3. **Test all supported versions** - Don't break old versions silently
4. **Keep version logic simple** - Don't overuse conditional logic
5. **Plan deprecation timeline** - Give clients 6-12 months notice
6. **Add deprecation warnings** - Use Warning headers
7. **Limit supported versions** - Support 2-3 versions maximum

## Resources

- DRF Versioning Source: `/home/user/django-rest-framework/rest_framework/versioning.py`
- [DRF Versioning Docs](https://www.django-rest-framework.org/api-guide/versioning/)
