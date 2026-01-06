# Filter Backends: SearchFilter, OrderingFilter, and DjangoFilterBackend

Essential guide to Django REST Framework's built-in filter backends for searching, sorting, and filtering.

## Overview

Filter backends process querysets before pagination, allowing clients to search, filter, and sort via query parameters.

```python
class MyViewSet(viewsets.ModelViewSet):
    queryset = Product.objects.all()
    filter_backends = [SearchFilter, OrderingFilter, DjangoFilterBackend]

    # Request flow:
    # 1. get_queryset() → base queryset
    # 2. SearchFilter → filtered by search
    # 3. OrderingFilter → sorted
    # 4. DjangoFilterBackend → field filters applied
    # 5. Pagination → page of results
```

---

## SearchFilter

### Basic Usage

```python
from rest_framework import viewsets, filters

class ProductViewSet(viewsets.ModelViewSet):
    queryset = Product.objects.all()
    filter_backends = [filters.SearchFilter]
    search_fields = ['name', 'description', 'category__name']

# API Usage:
# GET /api/products/?search=laptop
```

### Search Field Prefixes

Control search behavior with special prefixes:

```python
class ProductViewSet(viewsets.ModelViewSet):
    search_fields = [
        '^name',           # Starts with (istartswith)
        '=sku',            # Exact match (iexact)
        '@description',    # Full-text search (PostgreSQL only)
        'tags__name',      # No prefix = contains (icontains)
    ]

# Examples:
# ?search=LAP → matches "laptop", "lapis" (^ prefix)
# ?search=SKU123 → matches only "SKU123" (= prefix)
# ?search=laptop → matches "laptop", "my laptop" (no prefix)
```

| Prefix | Lookup | Example | Matches |
|--------|--------|---------|---------|
| `^` | istartswith | `^laptop` | "laptop", "Laptop Pro" |
| `=` | iexact | `=laptop` | "laptop", "LAPTOP" (exact) |
| `@` | search | `@laptop computer` | PostgreSQL full-text |
| (none) | icontains | `laptop` | "laptop", "my laptop" |

### Searching Related Fields

```python
class OrderViewSet(viewsets.ModelViewSet):
    queryset = Order.objects.select_related('customer')
    filter_backends = [filters.SearchFilter]
    search_fields = [
        '=order_number',
        'customer__email',
        'customer__first_name',
        'items__product__name',  # Many-to-many through relation
    ]

# API Usage:
# ?search=john@example.com
# ?search=laptop
```

### Performance Tips

```python
# 1. Add database indexes
class Product(models.Model):
    name = models.CharField(max_length=200, db_index=True)
    sku = models.CharField(max_length=50, db_index=True)

# 2. Use select_related for ForeignKey searches
class OrderViewSet(viewsets.ModelViewSet):
    def get_queryset(self):
        return Order.objects.select_related('customer')

    search_fields = ['customer__email']

# 3. Use prefetch_related for Many-to-Many
class ProductViewSet(viewsets.ModelViewSet):
    def get_queryset(self):
        return Product.objects.prefetch_related('tags')

    search_fields = ['tags__name']
```

---

## OrderingFilter

### Basic Usage

```python
from rest_framework import filters

class ProductViewSet(viewsets.ModelViewSet):
    queryset = Product.objects.all()
    filter_backends = [filters.OrderingFilter]
    ordering_fields = ['name', 'price', 'created_at']
    ordering = ['-created_at']  # Default ordering

# API Usage:
# GET /api/products/?ordering=price           # Ascending
# GET /api/products/?ordering=-price          # Descending
# GET /api/products/?ordering=name,-created_at # Multiple fields
```

### Ordering Configurations

```python
class ProductViewSet(viewsets.ModelViewSet):
    filter_backends = [filters.OrderingFilter]

    # 1. Explicit list (recommended)
    ordering_fields = ['name', 'price', 'stock', 'created_at']

    # 2. Allow all model fields (use with caution!)
    ordering_fields = '__all__'

    # 3. Include related fields
    ordering_fields = [
        'name',
        'category__name',
        'manufacturer__country',
    ]

    # 4. Default ordering
    ordering = ['-created_at']
```

### Ordering with Related Fields

```python
class OrderViewSet(viewsets.ModelViewSet):
    queryset = Order.objects.select_related('customer')
    filter_backends = [filters.OrderingFilter]
    ordering_fields = [
        'created_at',
        'total',
        'customer__last_name',
        'customer__email',
    ]

# API Usage:
# ?ordering=customer__last_name
```

### Performance Tips

```python
# 1. Index ordering fields
class Product(models.Model):
    price = models.DecimalField(max_digits=10, decimal_places=2, db_index=True)
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)

    class Meta:
        indexes = [
            models.Index(fields=['price']),
            models.Index(fields=['-created_at']),
            models.Index(fields=['category', '-price']),  # Composite
        ]

# 2. Use select_related for foreign key ordering
class OrderViewSet(viewsets.ModelViewSet):
    def get_queryset(self):
        return Order.objects.select_related('customer')

    ordering_fields = ['customer__last_name']
```

---

## DjangoFilterBackend

### Installation

```bash
pip install django-filter
```

```python
# settings.py
INSTALLED_APPS = [
    ...
    'django_filters',
]

REST_FRAMEWORK = {
    'DEFAULT_FILTER_BACKENDS': [
        'django_filters.rest_framework.DjangoFilterBackend',
    ]
}
```

### Simple Filtering (No FilterSet)

```python
class ProductViewSet(viewsets.ModelViewSet):
    queryset = Product.objects.all()
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ['category', 'manufacturer', 'in_stock']

# API Usage:
# GET /api/products/?category=electronics&in_stock=true
```

### FilterSet for Advanced Filtering

```python
from django_filters import rest_framework as filters

class ProductFilter(filters.FilterSet):
    # Price range
    min_price = filters.NumberFilter(field_name='price', lookup_expr='gte')
    max_price = filters.NumberFilter(field_name='price', lookup_expr='lte')

    # Date range
    created_after = filters.DateTimeFilter(
        field_name='created_at', lookup_expr='gte'
    )

    # Text search
    name = filters.CharFilter(lookup_expr='icontains')

    # Boolean
    is_featured = filters.BooleanFilter()

    class Meta:
        model = Product
        fields = {
            'price': ['exact', 'gte', 'lte'],
            'category': ['exact'],
        }

class ProductViewSet(viewsets.ModelViewSet):
    queryset = Product.objects.all()
    filter_backends = [filters.DjangoFilterBackend]
    filterset_class = ProductFilter

# API Usage:
# ?min_price=100&max_price=500
# ?name=laptop
# ?category=electronics&is_featured=true
```

### Common Lookup Expressions

```python
class ProductFilter(filters.FilterSet):
    class Meta:
        model = Product
        fields = {
            'name': ['exact', 'icontains', 'istartswith'],
            'price': ['exact', 'gte', 'lte', 'gt', 'lt'],
            'created_at': ['exact', 'year', 'month', 'gte', 'lte'],
            'category': ['exact', 'in'],
        }

# Generates these filter options:
# ?name=exact_match
# ?name__icontains=partial
# ?price__gte=100
# ?price__lte=500
# ?created_at__year=2024
# ?category__in=electronics,books
```

---

## Combining Multiple Filter Backends

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

    # DjangoFilterBackend configuration
    filterset_class = ProductFilter

    # SearchFilter configuration
    search_fields = ['name', 'description']

    # OrderingFilter configuration
    ordering_fields = ['price', 'created_at', 'name']
    ordering = ['-created_at']

# API Usage combining all filters:
# /api/products/?category=electronics&min_price=100&search=laptop&ordering=-price
```

---

## Performance Best Practices

### 1. Database Indexes

```python
class Product(models.Model):
    name = models.CharField(max_length=200, db_index=True)
    price = models.DecimalField(max_digits=10, decimal_places=2, db_index=True)
    category = models.ForeignKey('Category', on_delete=models.CASCADE, db_index=True)
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)

    class Meta:
        indexes = [
            models.Index(fields=['category', '-price']),
            models.Index(fields=['-created_at']),
            models.Index(fields=['name']),
        ]
```

### 2. Optimize Queries

```python
class ProductViewSet(viewsets.ModelViewSet):
    def get_queryset(self):
        return Product.objects.select_related(
            'category', 'manufacturer'
        ).prefetch_related(
            'tags', 'images'
        ).only(
            'id', 'name', 'price', 'category__name'
        )
```

### 3. Limit Filter Complexity

```python
# BAD: Allows unlimited filter combinations
filterset_fields = '__all__'

# GOOD: Explicitly define allowed filters
filterset_fields = ['category', 'price', 'in_stock']
```

---

## Summary

- **SearchFilter**: Text search across multiple fields with various matching strategies
- **OrderingFilter**: Client-controlled sorting with support for related fields
- **DjangoFilterBackend**: Complex field filtering with Django ORM lookups

Use them together for powerful, performant filtering:

```python
filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
```

Key tips:
1. Always index filtered and ordered fields
2. Use `select_related()` for ForeignKey filters
3. Use `prefetch_related()` for M2M filters
4. Explicitly define allowed filter/ordering fields
5. Test performance with realistic data volumes
