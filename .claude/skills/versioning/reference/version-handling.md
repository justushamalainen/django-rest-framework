# Version Handling - Patterns and Best Practices

This document covers how to access version information in your views, implement version-specific logic, and handle common versioning scenarios.

## Table of Contents

1. [Accessing Version Information](#accessing-version-information)
2. [Version-Specific Serializers](#version-specific-serializers)
3. [Version-Specific View Logic](#version-specific-view-logic)
4. [Deprecation Patterns](#deprecation-patterns)
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
        # Access the version
        version = request.version  # 'v1', 'v2', etc.

        # Use it for conditional logic
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

### In Serializers

Pass the version via context:

```python
class BookSerializer(serializers.ModelSerializer):
    class Meta:
        model = Book
        fields = ['id', 'title']

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # Access version from context
        request = self.context.get('request')
        if request and request.version == 'v1':
            # Remove fields for v1
            self.fields.pop('isbn', None)
```

### In Permissions

```python
from rest_framework import permissions

class VersionBasedPermission(permissions.BasePermission):
    def has_permission(self, request, view):
        # V1 is read-only
        if request.version == 'v1':
            return request.method in permissions.SAFE_METHODS

        # V2+ allows all methods
        return True
```

---

## Version-Specific Serializers

### Pattern 1: get_serializer_class() Method

**Best for:** Simple version differences

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

### Pattern 2: Serializer Factory

**Best for:** Complex version mapping

```python
# serializers/__init__.py
from .v1 import BookSerializerV1
from .v2 import BookSerializerV2
from .v3 import BookSerializerV3

SERIALIZER_VERSIONS = {
    'v1': BookSerializerV1,
    'v2': BookSerializerV2,
    'v3': BookSerializerV3,
}

def get_book_serializer(version):
    """Factory function for version-specific serializers"""
    return SERIALIZER_VERSIONS.get(version, BookSerializerV3)
```

**Usage:**

```python
from myapp.serializers import get_book_serializer

class BookViewSet(viewsets.ModelViewSet):
    queryset = Book.objects.all()

    def get_serializer_class(self):
        return get_book_serializer(self.request.version)
```

### Pattern 3: Inheritance Chain

**Best for:** Incremental changes between versions

```python
# Base serializer
class BookSerializerV1(serializers.ModelSerializer):
    class Meta:
        model = Book
        fields = ['id', 'title', 'author_name']

# V2 adds ISBN
class BookSerializerV2(BookSerializerV1):
    isbn = serializers.CharField(max_length=13)

    class Meta(BookSerializerV1.Meta):
        fields = BookSerializerV1.Meta.fields + ['isbn']

# V3 adds categories
class BookSerializerV3(BookSerializerV2):
    categories = CategorySerializer(many=True)

    class Meta(BookSerializerV2.Meta):
        fields = BookSerializerV2.Meta.fields + ['categories']
```

### Pattern 4: Dynamic Field Removal

**Best for:** Removing fields in newer versions

```python
class BookSerializer(serializers.ModelSerializer):
    deprecated_field = serializers.CharField(required=False)

    class Meta:
        model = Book
        fields = ['id', 'title', 'deprecated_field', 'new_field']

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        request = self.context.get('request')
        if request:
            # Remove deprecated field in v2+
            if request.version != 'v1':
                self.fields.pop('deprecated_field', None)

            # Remove new field in v1
            if request.version == 'v1':
                self.fields.pop('new_field', None)
```

---

## Version-Specific View Logic

### Pattern 1: Conditional Querysets

```python
class BookViewSet(viewsets.ModelViewSet):
    serializer_class = BookSerializer

    def get_queryset(self):
        """Version-specific filtering"""
        queryset = Book.objects.all()

        if self.request.version == 'v1':
            # V1: Only return published books
            return queryset.filter(published=True)
        elif self.request.version == 'v2':
            # V2: Return all, but annotate
            return queryset.select_related('author')
        else:
            # V3+: Full optimization
            return queryset.select_related('author').prefetch_related('categories')
```

### Pattern 2: Different Action Behavior

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

        elif request.version == 'v2':
            # V2: Publish with validation
            if not book.isbn:
                return Response(
                    {'error': 'ISBN required to publish'},
                    status=400
                )
            book.published = True
            book.save()
            return Response({'status': 'published', 'isbn': book.isbn})

        else:
            # V3+: Publish with notifications
            book.published = True
            book.save()
            # Send notifications...
            return Response({
                'status': 'published',
                'isbn': book.isbn,
                'notification_sent': True
            })
```

### Pattern 3: Version-Specific Pagination

```python
from rest_framework.pagination import PageNumberPagination, CursorPagination

class BookViewSet(viewsets.ModelViewSet):
    queryset = Book.objects.all()
    serializer_class = BookSerializer

    def get_paginator(self):
        """Use different pagination per version"""
        if self.request.version == 'v1':
            # V1: Simple page number
            paginator = PageNumberPagination()
            paginator.page_size = 10
        else:
            # V2+: Cursor for better performance
            paginator = CursorPagination()
            paginator.page_size = 20
        return paginator
```

### Pattern 4: Validation Changes

```python
from rest_framework import serializers

class BookSerializerV1(serializers.ModelSerializer):
    class Meta:
        model = Book
        fields = ['title', 'pages']

    def validate_pages(self, value):
        # V1: Any positive number
        if value <= 0:
            raise serializers.ValidationError("Pages must be positive")
        return value


class BookSerializerV2(serializers.ModelSerializer):
    class Meta:
        model = Book
        fields = ['title', 'pages']

    def validate_pages(self, value):
        # V2: Stricter validation
        if value < 10:
            raise serializers.ValidationError("Books must have at least 10 pages")
        if value > 10000:
            raise serializers.ValidationError("Books cannot exceed 10,000 pages")
        return value
```

---

## Deprecation Patterns

### Pattern 1: Deprecation Warning Header

```python
from rest_framework.views import APIView
from rest_framework.response import Response
from datetime import datetime

class DeprecatedMixin:
    """Mixin to add deprecation warnings"""

    deprecation_date = None  # Set this in subclass
    deprecation_message = "This API version is deprecated"

    def finalize_response(self, request, response, *args, **kwargs):
        """Add deprecation header to all responses"""
        response = super().finalize_response(request, response, *args, **kwargs)

        if request.version == 'v1':  # Deprecated version
            warning = f'299 - "{self.deprecation_message}'
            if self.deprecation_date:
                warning += f' Will be removed on {self.deprecation_date}'
            warning += '"'
            response['Warning'] = warning

        return response


class BookViewSet(DeprecatedMixin, viewsets.ModelViewSet):
    deprecation_date = "2024-12-31"
    deprecation_message = "API v1 is deprecated. Please migrate to v2."
    queryset = Book.objects.all()
    serializer_class = BookSerializer
```

### Pattern 2: Sunset Header

```python
from django.utils import timezone

class SunsetMixin:
    """Add Sunset header for deprecated endpoints"""

    sunset_date = None

    def finalize_response(self, request, response, *args, **kwargs):
        response = super().finalize_response(request, response, *args, **kwargs)

        if self.sunset_date and request.version in ['v1', 'v2']:
            # RFC 8594 Sunset header
            response['Sunset'] = self.sunset_date.strftime('%a, %d %b %Y %H:%M:%S GMT')
            response['Link'] = '</api/v3/>; rel="successor-version"'

        return response
```

### Pattern 3: Deprecation Notice in Response

```python
class BookViewSet(viewsets.ModelViewSet):
    queryset = Book.objects.all()
    serializer_class = BookSerializer

    def list(self, request, *args, **kwargs):
        response = super().list(request, *args, **kwargs)

        # Add deprecation notice to response body
        if request.version == 'v1':
            if isinstance(response.data, dict):
                response.data['_meta'] = {
                    'deprecation_warning': 'API v1 will be sunset on 2024-12-31',
                    'migration_guide': 'https://docs.example.com/api/v2-migration'
                }

        return response
```

### Pattern 4: Gradual Feature Sunset

```python
class BookViewSet(viewsets.ModelViewSet):
    queryset = Book.objects.all()
    serializer_class = BookSerializer

    @action(detail=True, methods=['post'])
    def legacy_action(self, request, pk=None):
        """This action only works in v1"""
        if request.version != 'v1':
            return Response(
                {
                    'error': 'This endpoint is only available in API v1',
                    'message': 'Please use /api/v2/books/{id}/new-action/ instead'
                },
                status=410  # 410 Gone
            )

        # Legacy logic here
        return Response({'status': 'legacy action performed'})
```

### Pattern 5: Version Blacklist/Whitelist

```python
from rest_framework import permissions

class VersionRequiredPermission(permissions.BasePermission):
    """Only allow specific versions"""

    allowed_versions = ['v2', 'v3']
    message = "This endpoint requires API v2 or higher"

    def has_permission(self, request, view):
        if request.version not in self.allowed_versions:
            return False
        return True


class NewFeatureViewSet(viewsets.ModelViewSet):
    """ViewSet only available in v2+"""
    permission_classes = [VersionRequiredPermission]
    queryset = NewFeature.objects.all()
    serializer_class = NewFeatureSerializer
```

---

## Testing Versioned APIs

### Test All Versions

```python
from rest_framework.test import APITestCase
from django.urls import reverse

class BookAPITestCase(APITestCase):
    def setUp(self):
        self.book = Book.objects.create(
            title="Test Book",
            isbn="1234567890123"
        )

    def test_v1_list_endpoint(self):
        """Test v1 returns correct fields"""
        url = '/api/v1/books/'
        response = self.client.get(url)

        self.assertEqual(response.status_code, 200)
        # V1 doesn't include ISBN
        self.assertNotIn('isbn', response.data[0])

    def test_v2_list_endpoint(self):
        """Test v2 returns ISBN"""
        url = '/api/v2/books/'
        response = self.client.get(url)

        self.assertEqual(response.status_code, 200)
        # V2 includes ISBN
        self.assertIn('isbn', response.data[0])

    def test_v3_list_endpoint(self):
        """Test v3 returns categories"""
        url = '/api/v3/books/'
        response = self.client.get(url)

        self.assertEqual(response.status_code, 200)
        # V3 includes categories
        self.assertIn('categories', response.data[0])
```

### Test Version Negotiation

```python
class VersionNegotiationTestCase(APITestCase):
    def test_default_version(self):
        """Test that default version is used when not specified"""
        url = '/api/books/'
        response = self.client.get(url)

        # Should use DEFAULT_VERSION from settings
        self.assertEqual(response.wsgi_request.version, 'v1')

    def test_invalid_version(self):
        """Test that invalid version returns 404"""
        url = '/api/v99/books/'
        response = self.client.get(url)

        self.assertEqual(response.status_code, 404)

    def test_accept_header_version(self):
        """Test AcceptHeaderVersioning"""
        url = '/api/books/'
        response = self.client.get(
            url,
            HTTP_ACCEPT='application/json; version=2.0'
        )

        self.assertEqual(response.wsgi_request.version, '2.0')
```

### Test Deprecation Warnings

```python
class DeprecationTestCase(APITestCase):
    def test_v1_deprecation_warning(self):
        """Test that v1 includes deprecation warning"""
        url = '/api/v1/books/'
        response = self.client.get(url)

        # Check for Warning header
        self.assertIn('Warning', response)
        self.assertIn('deprecated', response['Warning'].lower())

    def test_v2_no_deprecation(self):
        """Test that v2 doesn't include warning"""
        url = '/api/v2/books/'
        response = self.client.get(url)

        self.assertNotIn('Warning', response)
```

### Parametrized Tests

```python
from django.test import override_settings

class MultiVersionTestCase(APITestCase):
    versions = ['v1', 'v2', 'v3']

    def test_all_versions_return_200(self):
        """Test that all versions return successful response"""
        for version in self.versions:
            with self.subTest(version=version):
                url = f'/api/{version}/books/'
                response = self.client.get(url)
                self.assertEqual(response.status_code, 200)

    def test_version_specific_fields(self):
        """Test that each version returns expected fields"""
        expected_fields = {
            'v1': ['id', 'title'],
            'v2': ['id', 'title', 'isbn'],
            'v3': ['id', 'title', 'isbn', 'categories'],
        }

        for version, fields in expected_fields.items():
            with self.subTest(version=version):
                url = f'/api/{version}/books/'
                response = self.client.get(url)
                for field in fields:
                    self.assertIn(field, response.data[0])
```

---

## Best Practices

1. **Always provide a default version** - Don't leave clients guessing
2. **Document version differences** - Make migration guides
3. **Test all supported versions** - Don't break old versions silently
4. **Use semantic versioning** - v1, v2, v3 (not 1.0.1, 1.0.2)
5. **Plan deprecation timeline** - Give clients 6-12 months notice
6. **Add deprecation warnings** - Use Warning or Sunset headers
7. **Keep version logic simple** - Don't overuse conditional logic
8. **Consider separate views** - For major version differences
9. **Maintain backwards compatibility** - When possible, don't version
10. **Limit supported versions** - Support 2-3 versions maximum

## Common Mistakes

1. **Creating versions for minor changes** - Only version breaking changes
2. **No deprecation plan** - Always have sunset dates
3. **Testing only latest version** - Test all active versions
4. **Inconsistent version behavior** - Keep version handling uniform
5. **Too many versions** - Maintain only what's necessary
6. **Forgetting to document** - Always document version differences

## Resources

- DRF Versioning Source: `/home/user/django-rest-framework/rest_framework/versioning.py`
- [DRF Versioning Docs](https://www.django-rest-framework.org/api-guide/versioning/)
- [RFC 8594 - Sunset Header](https://tools.ietf.org/html/rfc8594)
- [API Versioning Best Practices](https://www.django-rest-framework.org/api-guide/versioning/#best-practices)
