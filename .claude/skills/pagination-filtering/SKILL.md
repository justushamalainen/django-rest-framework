---
skill: pagination-filtering
description: Master Django REST Framework's pagination and filtering strategies with decision trees, performance tips, and production-ready patterns
dependencies: []
related_skills: [viewsets, serializers, performance]
---

# Pagination and Filtering in Django REST Framework

This skill teaches you how to implement efficient pagination and filtering in Django REST Framework, helping you handle large datasets while providing excellent API UX.

## What You'll Learn

By completing this skill, you will understand:

- How to choose the right pagination strategy for your use case
- The differences between PageNumberPagination, LimitOffsetPagination, and CursorPagination
- How to implement custom pagination classes
- How to use SearchFilter, OrderingFilter, and DjangoFilterBackend
- How to create custom filter backends for complex requirements
- Performance implications of different pagination and filtering strategies
- Common pitfalls and how to avoid them

## Quick Start: Basic PageNumberPagination

The simplest way to add pagination to your API:

```python
# settings.py
REST_FRAMEWORK = {
    'DEFAULT_PAGINATION_CLASS': 'rest_framework.pagination.PageNumberPagination',
    'PAGE_SIZE': 10
}

# views.py
from rest_framework import viewsets
from rest_framework.pagination import PageNumberPagination

class StandardResultsSetPagination(PageNumberPagination):
    page_size = 10
    page_size_query_param = 'page_size'
    max_page_size = 100

class ProductViewSet(viewsets.ModelViewSet):
    queryset = Product.objects.all()
    serializer_class = ProductSerializer
    pagination_class = StandardResultsSetPagination
```

**API Usage:**
```bash
# Get first page
GET /api/products/

# Get specific page
GET /api/products/?page=2

# Customize page size
GET /api/products/?page=2&page_size=20
```

**Response format:**
```json
{
  "count": 150,
  "next": "http://api.example.com/products/?page=3",
  "previous": "http://api.example.com/products/?page=1",
  "results": [
    {"id": 1, "name": "Product 1"},
    {"id": 2, "name": "Product 2"}
  ]
}
```

## Decision Tree: Choosing a Pagination Strategy

```
START: Do you need pagination?
│
├─ NO → Use no pagination (small, stable datasets only)
│
└─ YES → What's your primary use case?
    │
    ├─ Simple page navigation (page 1, 2, 3...)
    │   └─ Use: PageNumberPagination
    │       ✓ User-friendly page numbers
    │       ✓ Easy to implement
    │       ✗ Performance degrades with high page numbers
    │       ✗ Inconsistent results with frequent updates
    │
    ├─ Direct jumping/data science (offset 100, limit 50)
    │   └─ Use: LimitOffsetPagination
    │       ✓ Flexible direct access
    │       ✓ Useful for data exports
    │       ✗ Same performance issues as PageNumber
    │       ✗ More complex for end users
    │
    ├─ Real-time feeds/infinite scroll
    │   └─ Use: CursorPagination
    │       ✓ Excellent performance at any position
    │       ✓ Consistent results during updates
    │       ✓ No skipped/duplicate records
    │       ✗ Cannot jump to arbitrary pages
    │       ✗ Requires unique, ordered field (e.g., timestamp)
    │
    └─ Complex requirements (custom response format)
        └─ Create custom pagination class
            → See: reference/custom-pagination.md
```

### When to Use Each Strategy

**PageNumberPagination**: Best for
- Admin interfaces
- Search results
- User-facing lists with page numbers
- Datasets where total count is needed

**LimitOffsetPagination**: Best for
- Data exports
- Integration with external systems expecting limit/offset
- When you need precise control over positioning

**CursorPagination**: Best for
- Activity feeds (Twitter, Facebook style)
- Real-time data streams
- Large datasets (millions of records)
- Mobile app infinite scroll
- When consistency during pagination is critical

## Decision Tree: Choosing Filter Backends

```
START: What filtering do you need?
│
├─ Text search across multiple fields
│   └─ Use: SearchFilter
│       Example: search=laptop
│       → Searches across multiple fields with various strategies
│       → See: reference/filter-backends.md#searchfilter
│
├─ Sorting/ordering results
│   └─ Use: OrderingFilter
│       Example: ordering=-created_at,name
│       → Client controls sort order
│       → See: reference/filter-backends.md#orderingfilter
│
├─ Exact field matching with operators
│   └─ Use: DjangoFilterBackend (django-filter package)
│       Example: price__gte=100&category=electronics
│       → Complex filtering with Django ORM lookups
│       → Requires: pip install django-filter
│
├─ Complex business logic filtering
│   └─ Create custom filter backend
│       → Full control over queryset filtering
│       → See: reference/custom-filters.md
│
└─ Combine multiple filters
    └─ Set multiple filter_backends on your view
        filter_backends = [SearchFilter, OrderingFilter, DjangoFilterBackend]
```

## Adding Search and Ordering

```python
from rest_framework import viewsets, filters

class ProductViewSet(viewsets.ModelViewSet):
    queryset = Product.objects.all()
    serializer_class = ProductSerializer
    filter_backends = [filters.SearchFilter, filters.OrderingFilter]

    # SearchFilter configuration
    search_fields = ['name', 'description', '^sku']  # ^ = starts with

    # OrderingFilter configuration
    ordering_fields = ['name', 'price', 'created_at']
    ordering = ['-created_at']  # Default ordering

# API Usage:
# Search: GET /api/products/?search=laptop
# Order: GET /api/products/?ordering=-price
# Both: GET /api/products/?search=laptop&ordering=-price
```

## Advanced Search Field Prefixes

SearchFilter supports special prefixes for different matching strategies:

```python
search_fields = [
    '^name',        # Starts with (istartswith)
    '=sku',         # Exact match (iexact)
    '@description', # Full-text search (PostgreSQL only)
    '$regex_field', # Regex match (iregex)
    'name',         # Contains (default: icontains)
]
```

## Common Mistakes and How to Avoid Them

### 1. Not Setting max_page_size

**Problem**: Users can request unlimited page sizes, causing performance issues.

```python
# BAD: No limit
class MyPagination(PageNumberPagination):
    page_size = 10
    page_size_query_param = 'page_size'
    # Missing: max_page_size
```

```python
# GOOD: Set a reasonable limit
class MyPagination(PageNumberPagination):
    page_size = 10
    page_size_query_param = 'page_size'
    max_page_size = 100  # Prevent abuse
```

### 2. Using PageNumber/LimitOffset with Large Datasets

**Problem**: Querying page 1000 of a dataset requires the database to scan millions of rows.

```python
# BAD: For large, frequently updated datasets
class ActivityViewSet(viewsets.ModelViewSet):
    queryset = Activity.objects.all()  # Millions of records
    pagination_class = PageNumberPagination  # Slow for high page numbers
```

```python
# GOOD: Use cursor pagination for large datasets
class ActivityViewSet(viewsets.ModelViewSet):
    queryset = Activity.objects.all()
    pagination_class = CursorPagination  # Consistent performance
```

### 3. CursorPagination Without Unique Ordering

**Problem**: CursorPagination requires a unique or nearly-unique ordering field.

```python
# BAD: Non-unique ordering
class MyCursorPagination(CursorPagination):
    ordering = 'status'  # Many records with same status
```

```python
# GOOD: Add a unique tiebreaker
class MyCursorPagination(CursorPagination):
    ordering = ['-created', 'id']  # created + id ensures uniqueness
```

### 4. SearchFilter on Non-Indexed Fields

**Problem**: Searching on unindexed fields causes slow queries.

```python
# BAD: No database index
class Product(models.Model):
    name = models.CharField(max_length=200)  # No db_index
    sku = models.CharField(max_length=50)    # No db_index

class ProductViewSet(viewsets.ModelViewSet):
    search_fields = ['name', 'sku']  # Will be slow!
```

```python
# GOOD: Add indexes to searched fields
class Product(models.Model):
    name = models.CharField(max_length=200, db_index=True)
    sku = models.CharField(max_length=50, db_index=True)

class ProductViewSet(viewsets.ModelViewSet):
    search_fields = ['name', 'sku']  # Now fast!
```

### 5. Searching Related Fields Without select_related

**Problem**: N+1 query problem when searching across relationships.

```python
# BAD: Searches related field without optimization
class OrderViewSet(viewsets.ModelViewSet):
    queryset = Order.objects.all()  # No select_related
    search_fields = ['customer__name']  # Causes N+1 queries
```

```python
# GOOD: Use select_related for foreign keys
class OrderViewSet(viewsets.ModelViewSet):
    queryset = Order.objects.select_related('customer')
    search_fields = ['customer__name']  # Optimized
```

### 6. Not Using distinct() with M2M Search

**Problem**: Searching many-to-many relationships can return duplicate results.

```python
# BAD: Can return duplicate products
class Product(models.Model):
    tags = models.ManyToManyField('Tag')

class ProductViewSet(viewsets.ModelViewSet):
    queryset = Product.objects.all()
    search_fields = ['tags__name']  # Returns duplicates if product has multiple matching tags
```

**Solution**: DRF's SearchFilter automatically handles this, but be aware:
- It uses EXISTS subquery for better performance
- This is handled internally, but affects query performance

### 7. Overriding filter_queryset Incorrectly

**Problem**: Breaking the filter chain by not calling super().

```python
# BAD: Doesn't call super()
class MyView(viewsets.ModelViewSet):
    def filter_queryset(self, queryset):
        return queryset.filter(is_active=True)  # Breaks pagination and filters!
```

```python
# GOOD: Call super() to maintain chain
class MyView(viewsets.ModelViewSet):
    def filter_queryset(self, queryset):
        queryset = super().filter_queryset(queryset)
        return queryset.filter(is_active=True)
```

### 8. Mixing Pagination with .count() Queries

**Problem**: Unnecessary count queries on every request.

```python
# BAD: Calling count() when using pagination
def list(self, request, *args, **kwargs):
    queryset = self.filter_queryset(self.get_queryset())
    total = queryset.count()  # Unnecessary - pagination handles this
    page = self.paginate_queryset(queryset)
    # ...
```

```python
# GOOD: Let pagination handle counting
def list(self, request, *args, **kwargs):
    queryset = self.filter_queryset(self.get_queryset())
    page = self.paginate_queryset(queryset)
    if page is not None:
        serializer = self.get_serializer(page, many=True)
        return self.get_paginated_response(serializer.data)
    # Pagination class handles count efficiently
```

### 9. Not Validating ordering_fields

**Problem**: Allowing ordering on computed properties or write-only fields.

```python
# BAD: No restriction on ordering fields
class ProductViewSet(viewsets.ModelViewSet):
    filter_backends = [OrderingFilter]
    ordering_fields = '__all__'  # Dangerous! Includes all fields
```

```python
# GOOD: Explicitly list orderable fields
class ProductViewSet(viewsets.ModelViewSet):
    filter_backends = [OrderingFilter]
    ordering_fields = ['name', 'price', 'created_at']  # Only indexed/safe fields
```

### 10. Forgetting to Set Default Ordering

**Problem**: Unpredictable result ordering affects pagination consistency.

```python
# BAD: No default ordering
class ProductViewSet(viewsets.ModelViewSet):
    queryset = Product.objects.all()  # Undefined order
    pagination_class = PageNumberPagination
```

```python
# GOOD: Always set default ordering
class ProductViewSet(viewsets.ModelViewSet):
    queryset = Product.objects.all().order_by('-created_at', 'id')
    pagination_class = PageNumberPagination
    # or
    ordering = ['-created_at', 'id']  # If using OrderingFilter
```

## Performance Best Practices

### 1. Database Indexing
```python
class Product(models.Model):
    name = models.CharField(max_length=200, db_index=True)
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)

    class Meta:
        indexes = [
            models.Index(fields=['-created_at', 'id']),  # For cursor pagination
        ]
```

### 2. Optimize QuerySets
```python
class OrderViewSet(viewsets.ModelViewSet):
    def get_queryset(self):
        return Order.objects.select_related(
            'customer', 'shipping_address'
        ).prefetch_related(
            'items__product'
        ).only(
            'id', 'status', 'total', 'created_at',
            'customer__name', 'customer__email'
        )
```

### 3. Use CursorPagination for Large Datasets
```python
class LargeFeedPagination(CursorPagination):
    page_size = 20
    ordering = '-created_at'
    cursor_query_param = 'cursor'
```

### 4. Cache Count Queries
```python
from django.core.cache import cache

class CachedCountPagination(PageNumberPagination):
    def get_count(self, queryset):
        cache_key = f'count:{queryset.query}'
        count = cache.get(cache_key)
        if count is None:
            count = super().get_count(queryset)
            cache.set(cache_key, count, 300)  # Cache for 5 minutes
        return count
```

## Testing Your Pagination and Filters

```python
from rest_framework.test import APITestCase

class ProductPaginationTests(APITestCase):
    def setUp(self):
        # Create 25 products
        for i in range(25):
            Product.objects.create(name=f'Product {i}')

    def test_pagination_returns_10_items(self):
        response = self.client.get('/api/products/')
        self.assertEqual(len(response.data['results']), 10)
        self.assertEqual(response.data['count'], 25)

    def test_search_filter(self):
        response = self.client.get('/api/products/?search=Product 1')
        # Should return Product 1, 10-19
        self.assertEqual(response.data['count'], 11)

    def test_ordering(self):
        response = self.client.get('/api/products/?ordering=-name')
        first_product = response.data['results'][0]
        self.assertEqual(first_product['name'], 'Product 9')
```

## Reference Documentation

For detailed implementation guides and advanced patterns:

- **[Pagination Types Reference](./reference/pagination-types.md)** - Deep dive into PageNumber, LimitOffset, and Cursor pagination
- **[Custom Pagination](./reference/custom-pagination.md)** - Creating custom pagination classes
- **[Filter Backends](./reference/filter-backends.md)** - SearchFilter, OrderingFilter, DjangoFilterBackend
- **[Custom Filters](./reference/custom-filters.md)** - Building custom filter backends
- **[Code Examples](./reference/examples/pagination-filtering-patterns.py)** - Production-ready code patterns

## Related Source Files

Explore the DRF source code:

- `/home/user/django-rest-framework/rest_framework/pagination.py` - All pagination classes
- `/home/user/django-rest-framework/rest_framework/filters.py` - Built-in filter backends

## Next Steps

1. Start with PageNumberPagination for simple use cases
2. Add SearchFilter and OrderingFilter for better UX
3. Optimize with indexes and queryset methods
4. Consider CursorPagination for large datasets
5. Create custom pagination/filters for specific requirements

Remember: The best pagination strategy balances performance, UX, and your specific use case. Start simple and optimize based on actual usage patterns.
