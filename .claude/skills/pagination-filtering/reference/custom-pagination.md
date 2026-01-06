# Creating Custom Pagination Classes

Learn how to create custom pagination classes for specialized requirements, including custom response formats, business logic, and performance optimizations.

## Why Create Custom Pagination?

Create custom pagination when you need:

1. **Custom Response Format**: Different JSON structure than DRF's default
2. **Business Logic**: Pagination behavior based on user permissions or subscription level
3. **Performance Optimizations**: Caching, approximate counts, or specialized queries
4. **Legacy API Compatibility**: Match existing API response format
5. **Additional Metadata**: Include extra information in paginated responses

## Understanding BasePagination

All pagination classes inherit from `BasePagination`:

```python
from rest_framework.pagination import BasePagination

class BasePagination:
    display_page_controls = False

    def paginate_queryset(self, queryset, request, view=None):
        """
        Paginate the queryset and return a list of results.
        Must return a list or None.
        """
        raise NotImplementedError('paginate_queryset() must be implemented.')

    def get_paginated_response(self, data):
        """
        Return a Response object with the paginated data.
        """
        raise NotImplementedError('get_paginated_response() must be implemented.')

    def get_paginated_response_schema(self, schema):
        """
        Return the OpenAPI schema for this pagination.
        """
        return schema

    def to_html(self):
        """
        Return HTML for browsable API page controls (optional).
        """
        raise NotImplementedError('to_html() must be implemented.')
```

## Basic Custom Pagination Example

### Simple Custom Format

```python
from rest_framework.pagination import PageNumberPagination
from rest_framework.response import Response

class CustomFormatPagination(PageNumberPagination):
    page_size = 10

    def get_paginated_response(self, data):
        return Response({
            'links': {
                'next': self.get_next_link(),
                'previous': self.get_previous_link()
            },
            'meta': {
                'total_items': self.page.paginator.count,
                'total_pages': self.page.paginator.num_pages,
                'current_page': self.page.number,
                'per_page': self.page_size,
            },
            'data': data
        })

# Response:
# {
#   "links": {
#     "next": "http://api.example.com/?page=3",
#     "previous": "http://api.example.com/?page=1"
#   },
#   "meta": {
#     "total_items": 150,
#     "total_pages": 15,
#     "current_page": 2,
#     "per_page": 10
#   },
#   "data": [...]
# }
```

### Envelope-style Pagination

```python
class EnvelopePagination(PageNumberPagination):
    page_size = 20

    def get_paginated_response(self, data):
        return Response({
            'status': 'success',
            'pagination': {
                'count': self.page.paginator.count,
                'page': self.page.number,
                'pages': self.page.paginator.num_pages,
                'per_page': self.page_size,
                'has_next': self.page.has_next(),
                'has_previous': self.page.has_previous(),
            },
            'results': data
        })
```

## Advanced Custom Pagination Examples

### 1. Pagination with Dynamic Page Size by User Type

```python
from rest_framework.pagination import PageNumberPagination

class UserTierPagination(PageNumberPagination):
    """
    Adjust page size based on user subscription level.
    """
    page_size = 10
    page_size_query_param = 'page_size'

    def get_page_size(self, request):
        # Premium users get larger page sizes
        if request.user.is_authenticated:
            if request.user.subscription == 'premium':
                self.max_page_size = 200
                return request.query_params.get(self.page_size_query_param, 50)
            elif request.user.subscription == 'basic':
                self.max_page_size = 100
                return request.query_params.get(self.page_size_query_param, 25)

        # Anonymous users get small pages
        self.max_page_size = 20
        return super().get_page_size(request)

    def get_paginated_response(self, data):
        response_data = {
            'count': self.page.paginator.count,
            'next': self.get_next_link(),
            'previous': self.get_previous_link(),
            'results': data,
        }

        # Add subscription info for authenticated users
        if self.request.user.is_authenticated:
            response_data['subscription'] = {
                'tier': self.request.user.subscription,
                'max_page_size': self.max_page_size,
            }

        return Response(response_data)
```

### 2. Cached Count Pagination

```python
from django.core.cache import cache
from rest_framework.pagination import PageNumberPagination
import hashlib

class CachedCountPagination(PageNumberPagination):
    """
    Cache the count query for better performance.
    """
    page_size = 25
    cache_timeout = 300  # 5 minutes

    def get_cache_key(self, queryset):
        """Generate a cache key based on the queryset."""
        query_str = str(queryset.query)
        return f'pagination_count:{hashlib.md5(query_str.encode()).hexdigest()}'

    def paginate_queryset(self, queryset, request, view=None):
        self.request = request
        page_size = self.get_page_size(request)

        if not page_size:
            return None

        # Try to get count from cache
        cache_key = self.get_cache_key(queryset)
        cached_count = cache.get(cache_key)

        if cached_count is not None:
            # Use cached count
            from django.core.paginator import Paginator
            paginator = Paginator(queryset, page_size)
            # Inject cached count
            paginator._count = cached_count
        else:
            paginator = self.django_paginator_class(queryset, page_size)
            # Cache the count
            cache.set(cache_key, paginator.count, self.cache_timeout)

        page_number = self.get_page_number(request, paginator)

        try:
            self.page = paginator.page(page_number)
        except InvalidPage as exc:
            msg = self.invalid_page_message.format(
                page_number=page_number, message=str(exc)
            )
            raise NotFound(msg)

        if paginator.num_pages > 1 and self.template is not None:
            self.display_page_controls = True

        return list(self.page)

    def get_paginated_response(self, data):
        return Response({
            'count': self.page.paginator.count,
            'next': self.get_next_link(),
            'previous': self.get_previous_link(),
            'cached': True,  # Indicate count is cached
            'results': data,
        })
```

### 3. Approximate Count for Large Tables

```python
from rest_framework.pagination import PageNumberPagination
from django.db import connection

class ApproximateCountPagination(PageNumberPagination):
    """
    Use approximate row counts for large tables (PostgreSQL).
    Much faster but less accurate.
    """
    page_size = 20
    approximate_threshold = 100000  # Use approximate count above this

    def get_approximate_count(self, model):
        """
        Get approximate row count from PostgreSQL statistics.
        """
        with connection.cursor() as cursor:
            cursor.execute(
                """
                SELECT reltuples::bigint AS approximate_row_count
                FROM pg_class
                WHERE relname = %s
                """,
                [model._meta.db_table]
            )
            result = cursor.fetchone()
            return int(result[0]) if result else None

    def paginate_queryset(self, queryset, request, view=None):
        self.request = request
        page_size = self.get_page_size(request)

        if not page_size:
            return None

        # Get actual count
        actual_count = queryset.count()

        # Decide whether to use approximate count
        if actual_count > self.approximate_threshold:
            approx_count = self.get_approximate_count(queryset.model)
            if approx_count:
                # Use approximate count for display
                self.is_approximate = True
                self.display_count = approx_count
            else:
                self.is_approximate = False
                self.display_count = actual_count
        else:
            self.is_approximate = False
            self.display_count = actual_count

        paginator = self.django_paginator_class(queryset, page_size)
        page_number = self.get_page_number(request, paginator)

        try:
            self.page = paginator.page(page_number)
        except InvalidPage as exc:
            msg = self.invalid_page_message.format(
                page_number=page_number, message=str(exc)
            )
            raise NotFound(msg)

        if paginator.num_pages > 1 and self.template is not None:
            self.display_page_controls = True

        return list(self.page)

    def get_paginated_response(self, data):
        response_data = {
            'count': self.display_count,
            'is_approximate': self.is_approximate,
            'next': self.get_next_link(),
            'previous': self.get_previous_link(),
            'results': data,
        }

        if self.is_approximate:
            response_data['count_note'] = 'Approximate count for performance'

        return Response(response_data)
```

### 4. Header-based Pagination

```python
from rest_framework.pagination import PageNumberPagination
from rest_framework.response import Response

class HeaderPagination(PageNumberPagination):
    """
    Put pagination info in headers instead of response body.
    Useful for REST purists who want clean response bodies.
    """
    page_size = 25

    def get_paginated_response(self, data):
        headers = {
            'X-Total-Count': self.page.paginator.count,
            'X-Page': self.page.number,
            'X-Total-Pages': self.page.paginator.num_pages,
        }

        if self.get_next_link():
            headers['Link-Next'] = self.get_next_link()

        if self.get_previous_link():
            headers['Link-Previous'] = self.get_previous_link()

        return Response(data, headers=headers)

# Response:
# Headers:
#   X-Total-Count: 150
#   X-Page: 2
#   X-Total-Pages: 6
#   Link-Next: http://api.example.com/?page=3
#   Link-Previous: http://api.example.com/?page=1
# Body:
#   [... just the data ...]
```

### 5. Pageless (No-Pagination) Mode

```python
from rest_framework.pagination import PageNumberPagination

class OptionalPagination(PageNumberPagination):
    """
    Allow clients to disable pagination with ?paginate=false.
    Use with caution on potentially large datasets!
    """
    page_size = 20
    max_page_size = 100

    def paginate_queryset(self, queryset, request, view=None):
        # Check if client wants no pagination
        if request.query_params.get('paginate', 'true').lower() == 'false':
            # Enforce a hard limit for safety
            max_unpaginated = 1000
            count = queryset.count()

            if count > max_unpaginated:
                from rest_framework.exceptions import ValidationError
                raise ValidationError(
                    f'Cannot return {count} items unpaginated. '
                    f'Maximum is {max_unpaginated}. Use pagination.'
                )

            # Return None to indicate no pagination
            return None

        # Use normal pagination
        return super().paginate_queryset(queryset, request, view)
```

### 6. Batch Pagination for Data Export

```python
from rest_framework.pagination import LimitOffsetPagination
from rest_framework.response import Response

class BatchPagination(LimitOffsetPagination):
    """
    Optimized pagination for batch data exports.
    Includes batch info and progress indicators.
    """
    default_limit = 100
    max_limit = 1000

    def get_paginated_response(self, data):
        total = self.count
        current_offset = self.offset
        limit = self.limit

        # Calculate batch information
        current_batch = (current_offset // limit) + 1
        total_batches = (total + limit - 1) // limit
        progress_percent = (current_offset + len(data)) / total * 100

        return Response({
            'export_info': {
                'total_items': total,
                'current_batch': current_batch,
                'total_batches': total_batches,
                'progress_percent': round(progress_percent, 2),
                'items_in_batch': len(data),
            },
            'pagination': {
                'limit': limit,
                'offset': current_offset,
                'next': self.get_next_link(),
                'previous': self.get_previous_link(),
            },
            'data': data,
        })

# Response:
# {
#   "export_info": {
#     "total_items": 10000,
#     "current_batch": 5,
#     "total_batches": 100,
#     "progress_percent": 5.0,
#     "items_in_batch": 100
#   },
#   "pagination": {...},
#   "data": [...]
# }
```

### 7. Multi-Cursor Pagination

```python
from rest_framework.pagination import CursorPagination
from rest_framework.response import Response

class MultiCursorPagination(CursorPagination):
    """
    Support multiple cursor positions for parallel data fetching.
    Useful for mobile apps that want to prefetch data.
    """
    page_size = 20
    ordering = '-created_at'

    def get_paginated_response(self, data):
        # Calculate cursors for next 3 pages
        next_cursors = []

        if self.has_next:
            next_cursors.append({
                'page': 2,
                'cursor': self.get_next_link().split('cursor=')[-1]
            })

            # You'd need to calculate additional cursors
            # This is simplified - real implementation would
            # need to encode additional cursor positions

        return Response({
            'next': self.get_next_link(),
            'previous': self.get_previous_link(),
            'prefetch_cursors': next_cursors,  # For client prefetching
            'results': data,
        })
```

### 8. Filtered Count Pagination

```python
from rest_framework.pagination import PageNumberPagination
from rest_framework.response import Response

class FilteredCountPagination(PageNumberPagination):
    """
    Show both filtered count and total unfiltered count.
    """
    page_size = 20

    def paginate_queryset(self, queryset, request, view=None):
        # Store the original unfiltered queryset count
        if hasattr(view, 'get_queryset'):
            self.total_count = view.get_queryset().count()
        else:
            self.total_count = None

        return super().paginate_queryset(queryset, request, view)

    def get_paginated_response(self, data):
        response_data = {
            'filtered_count': self.page.paginator.count,
            'next': self.get_next_link(),
            'previous': self.get_previous_link(),
            'results': data,
        }

        if self.total_count is not None:
            response_data['total_count'] = self.total_count
            response_data['is_filtered'] = (
                self.total_count != self.page.paginator.count
            )

        return Response(response_data)

# Response shows:
# {
#   "filtered_count": 45,    # Items matching search/filter
#   "total_count": 1000,     # Total items in database
#   "is_filtered": true,
#   "results": [...]
# }
```

## Testing Custom Pagination

```python
from rest_framework.test import APITestCase
from django.test import override_settings

class CustomPaginationTests(APITestCase):
    def setUp(self):
        # Create test data
        for i in range(50):
            Product.objects.create(name=f'Product {i}')

    def test_custom_response_format(self):
        """Test custom pagination response structure."""
        response = self.client.get('/api/products/')

        self.assertEqual(response.status_code, 200)
        self.assertIn('meta', response.data)
        self.assertIn('data', response.data)
        self.assertEqual(response.data['meta']['total_items'], 50)

    def test_user_tier_pagination(self):
        """Test pagination adjusts to user tier."""
        # Anonymous user
        response = self.client.get('/api/products/')
        self.assertEqual(len(response.data['results']), 10)

        # Premium user
        self.client.force_authenticate(user=self.premium_user)
        response = self.client.get('/api/products/?page_size=50')
        self.assertEqual(len(response.data['results']), 50)

    def test_cached_count(self):
        """Test count is cached."""
        from django.core.cache import cache
        cache.clear()

        # First request
        response = self.client.get('/api/products/')
        self.assertFalse(response.data.get('cached', False))

        # Second request (should be cached)
        response = self.client.get('/api/products/')
        self.assertTrue(response.data.get('cached', False))

    def test_optional_pagination(self):
        """Test disabling pagination."""
        # With pagination
        response = self.client.get('/api/products/')
        self.assertIn('count', response.data)

        # Without pagination
        response = self.client.get('/api/products/?paginate=false')
        self.assertIsInstance(response.data, list)
        self.assertEqual(len(response.data), 50)

    def test_header_pagination(self):
        """Test pagination info in headers."""
        response = self.client.get('/api/products/')

        self.assertIn('X-Total-Count', response)
        self.assertEqual(response['X-Total-Count'], '50')
        self.assertIn('X-Page', response)
```

## Common Patterns

### Pattern 1: Conditional Pagination Class

```python
class ConditionalView(viewsets.ModelViewSet):
    """
    Choose pagination class based on request parameters.
    """
    def get_pagination_class(self):
        if 'cursor' in self.request.query_params:
            return CursorPagination
        elif 'offset' in self.request.query_params:
            return LimitOffsetPagination
        return PageNumberPagination

    @property
    def pagination_class(self):
        return self.get_pagination_class()
```

### Pattern 2: Schema Generation

```python
class CustomFormatPagination(PageNumberPagination):
    def get_paginated_response_schema(self, schema):
        """
        Provide OpenAPI schema for custom format.
        """
        return {
            'type': 'object',
            'properties': {
                'meta': {
                    'type': 'object',
                    'properties': {
                        'total_items': {'type': 'integer'},
                        'total_pages': {'type': 'integer'},
                        'current_page': {'type': 'integer'},
                        'per_page': {'type': 'integer'},
                    }
                },
                'links': {
                    'type': 'object',
                    'properties': {
                        'next': {'type': 'string', 'format': 'uri', 'nullable': True},
                        'previous': {'type': 'string', 'format': 'uri', 'nullable': True},
                    }
                },
                'data': schema,
            }
        }
```

### Pattern 3: Performance Monitoring

```python
import time
from django.core.cache import cache

class MonitoredPagination(PageNumberPagination):
    """
    Track pagination performance metrics.
    """
    def paginate_queryset(self, queryset, request, view=None):
        start_time = time.time()

        result = super().paginate_queryset(queryset, request, view)

        elapsed = time.time() - start_time

        # Log slow queries
        if elapsed > 1.0:
            import logging
            logger = logging.getLogger('pagination')
            logger.warning(
                f'Slow pagination: {elapsed:.2f}s for {view.__class__.__name__} '
                f'page {request.query_params.get("page", 1)}'
            )

        # Store for response header
        self.query_time = elapsed

        return result

    def get_paginated_response(self, data):
        response = super().get_paginated_response(data)
        response['X-Query-Time'] = f'{self.query_time:.3f}s'
        return response
```

## Best Practices

1. **Always Set max_page_size**: Prevent abuse
2. **Document Your Format**: Especially if deviating from DRF defaults
3. **Include OpenAPI Schema**: Helps with API documentation
4. **Test Edge Cases**: Empty results, single page, last page
5. **Consider Caching**: For expensive count queries
6. **Monitor Performance**: Track slow pagination queries
7. **Validate Input**: Check page sizes and parameters
8. **Backward Compatibility**: Version your API if changing pagination format

## Summary

Custom pagination gives you full control over:
- Response format
- Performance optimizations
- Business logic
- Additional metadata
- Client experience

Start with built-in classes and customize only when needed. Most use cases are covered by PageNumber, LimitOffset, or Cursor pagination with minor tweaks to `get_paginated_response()`.
