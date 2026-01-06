---
skill: pagination-filtering
description: Master Django REST Framework's pagination and filtering strategies with decision trees, performance tips, and production-ready patterns
dependencies: []
related_skills: [viewsets, serializers]
---

# Pagination and Filtering in Django REST Framework

This skill teaches you how to implement pagination and filtering in Django REST Framework for handling large datasets with excellent API UX.

## Quick Start: PageNumberPagination

The most common pagination setup:

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
GET /api/products/              # First page
GET /api/products/?page=2        # Second page
GET /api/products/?page_size=20  # Custom page size
```

## Decision Tree: Choosing Pagination

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
    │       ✓ Total count included
    │       ✗ Performance degrades with high page numbers
    │
    ├─ Data exports/direct access (offset 100, limit 50)
    │   └─ Use: LimitOffsetPagination
    │       ✓ Flexible direct access
    │       ✓ Useful for data exports
    │       ✗ Same performance issues as PageNumber
    │
    └─ Large datasets/infinite scroll (millions of records)
        └─ Use: CursorPagination (see reference docs)
            ✓ Excellent performance at any position
            ✓ Consistent results during updates
            ✗ Cannot jump to arbitrary pages
```

## Decision Tree: Choosing Filters

```
START: What filtering do you need?
│
├─ Text search across multiple fields
│   └─ Use: SearchFilter
│       Example: ?search=laptop
│
├─ Sorting/ordering results
│   └─ Use: OrderingFilter
│       Example: ?ordering=-created_at,name
│
├─ Field filtering with operators
│   └─ Use: DjangoFilterBackend (django-filter)
│       Example: ?price__gte=100&category=electronics
│       Requires: pip install django-filter
│
└─ Combine multiple filters
    └─ Set: filter_backends = [SearchFilter, OrderingFilter, DjangoFilterBackend]
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
# ?search=laptop
# ?ordering=-price
# ?search=laptop&ordering=-price
```

### Search Field Prefixes

Control search behavior with prefixes:

```python
search_fields = [
    '^name',        # Starts with (istartswith)
    '=sku',         # Exact match (iexact)
    '@description', # Full-text search (PostgreSQL only)
    'name',         # Contains (default: icontains)
]
```

## Django-Filter Integration

For advanced field filtering:

```bash
pip install django-filter
```

```python
# settings.py
INSTALLED_APPS = [
    ...
    'django_filters',
]

# views.py
from django_filters import rest_framework as filters

class ProductFilter(filters.FilterSet):
    min_price = filters.NumberFilter(field_name='price', lookup_expr='gte')
    max_price = filters.NumberFilter(field_name='price', lookup_expr='lte')
    name = filters.CharFilter(lookup_expr='icontains')

    class Meta:
        model = Product
        fields = ['category', 'in_stock']

class ProductViewSet(viewsets.ModelViewSet):
    queryset = Product.objects.all()
    serializer_class = ProductSerializer
    filter_backends = [filters.DjangoFilterBackend]
    filterset_class = ProductFilter

# API Usage:
# ?category=electronics
# ?min_price=100&max_price=500
# ?name=laptop&in_stock=true
```

## Combining All Three

```python
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import filters

class ProductViewSet(viewsets.ModelViewSet):
    queryset = Product.objects.all()
    serializer_class = ProductSerializer

    # Apply filters in this order
    filter_backends = [
        DjangoFilterBackend,      # Field filtering
        filters.SearchFilter,      # Text search
        filters.OrderingFilter,    # Ordering
    ]

    filterset_class = ProductFilter
    search_fields = ['name', 'description']
    ordering_fields = ['price', 'created_at', 'name']
    ordering = ['-created_at']

# API Usage:
# ?category=electronics&min_price=100&search=laptop&ordering=-price
```

## Common Mistakes

### 1. Not Setting max_page_size

**Problem:** Users can request unlimited page sizes.

```python
# BAD
class MyPagination(PageNumberPagination):
    page_size = 10
    page_size_query_param = 'page_size'
    # Missing max_page_size!

# GOOD
class MyPagination(PageNumberPagination):
    page_size = 10
    page_size_query_param = 'page_size'
    max_page_size = 100
```

### 2. SearchFilter on Non-Indexed Fields

**Problem:** Searching unindexed fields causes slow queries.

```python
# BAD
class Product(models.Model):
    name = models.CharField(max_length=200)  # No db_index

class ProductViewSet(viewsets.ModelViewSet):
    search_fields = ['name']  # Slow!

# GOOD
class Product(models.Model):
    name = models.CharField(max_length=200, db_index=True)

class ProductViewSet(viewsets.ModelViewSet):
    search_fields = ['name']  # Fast!
```

### 3. Not Using select_related for Related Fields

**Problem:** N+1 query problem when searching/filtering related fields.

```python
# BAD
class OrderViewSet(viewsets.ModelViewSet):
    queryset = Order.objects.all()
    search_fields = ['customer__name']  # N+1 queries

# GOOD
class OrderViewSet(viewsets.ModelViewSet):
    queryset = Order.objects.select_related('customer')
    search_fields = ['customer__name']  # Optimized
```

### 4. No Default Ordering

**Problem:** Unpredictable result ordering affects pagination consistency.

```python
# BAD
class ProductViewSet(viewsets.ModelViewSet):
    queryset = Product.objects.all()  # Undefined order

# GOOD
class ProductViewSet(viewsets.ModelViewSet):
    queryset = Product.objects.all().order_by('-created_at', 'id')
    ordering = ['-created_at', 'id']
```

## Performance Best Practices

### 1. Add Database Indexes

```python
class Product(models.Model):
    name = models.CharField(max_length=200, db_index=True)
    price = models.DecimalField(max_digits=10, decimal_places=2, db_index=True)
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)

    class Meta:
        indexes = [
            models.Index(fields=['-created_at', 'id']),
            models.Index(fields=['category', '-price']),
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
        )
```

### 3. Use only() to Limit Fields

```python
class ProductViewSet(viewsets.ModelViewSet):
    def get_queryset(self):
        queryset = Product.objects.all()

        if self.action == 'list':
            # Only fetch essential fields for list view
            queryset = queryset.only(
                'id', 'name', 'price', 'image_url'
            )

        return queryset
```

## Reference Documentation

For detailed implementation guides:

- **[Pagination Types Reference](./reference/pagination-types.md)** - PageNumber and LimitOffset pagination
- **[Filter Backends](./reference/filter-backends.md)** - SearchFilter, OrderingFilter, DjangoFilterBackend

## Related Source Files

Explore the DRF source code:

- `/home/user/django-rest-framework/rest_framework/pagination.py` - All pagination classes
- `/home/user/django-rest-framework/rest_framework/filters.py` - Built-in filter backends

## Next Steps

1. Start with PageNumberPagination for most APIs
2. Add SearchFilter and OrderingFilter for better UX
3. Use django-filter for advanced field filtering
4. Optimize with indexes and queryset methods
5. Consider CursorPagination for very large datasets

Remember: Start simple and optimize based on actual usage patterns!
