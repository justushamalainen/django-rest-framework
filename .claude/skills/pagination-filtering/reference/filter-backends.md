# Filter Backends: Complete Reference

Comprehensive guide to Django REST Framework's built-in filter backends: SearchFilter, OrderingFilter, and DjangoFilterBackend.

## Overview

Filter backends process the queryset before pagination, allowing clients to search, filter, and sort results via query parameters.

```python
# How filter backends work
class MyViewSet(viewsets.ModelViewSet):
    queryset = Product.objects.all()
    filter_backends = [SearchFilter, OrderingFilter]  # Applied in order

    # Request flow:
    # 1. get_queryset() → queryset
    # 2. SearchFilter.filter_queryset() → filtered queryset
    # 3. OrderingFilter.filter_queryset() → ordered queryset
    # 4. Pagination → page of results
```

## SearchFilter

### Overview

SearchFilter enables text search across multiple model fields using query parameters.

### Basic Usage

```python
from rest_framework import viewsets, filters

class ProductViewSet(viewsets.ModelViewSet):
    queryset = Product.objects.all()
    serializer_class = ProductSerializer
    filter_backends = [filters.SearchFilter]

    # Define which fields are searchable
    search_fields = ['name', 'description', 'category__name']

# API Usage:
# GET /api/products/?search=laptop
# Searches for "laptop" in name, description, and category.name
```

### Search Field Prefixes

Control the search behavior with special prefixes:

```python
class ProductViewSet(viewsets.ModelViewSet):
    search_fields = [
        '^name',           # Starts with (istartswith)
        '=sku',            # Exact match (iexact)
        '@description',    # Full-text search (PostgreSQL only)
        '$catalog_id',     # Regex match (iregex)
        'tags__name',      # No prefix = contains (icontains)
    ]

# Examples:
# ?search=LAP → matches "laptop", "lapis", not "slap"  (^ prefix)
# ?search=SKU123 → matches only exactly "SKU123"        (= prefix)
# ?search=laptop computer → full-text search             (@ prefix)
# ?search=^[A-Z] → matches items starting with capital   ($ prefix)
# ?search=top → matches "laptop", "desktop", "stop"      (no prefix)
```

### Prefix Behavior Table

| Prefix | Lookup | Example | Matches | Doesn't Match |
|--------|--------|---------|---------|---------------|
| `^` | istartswith | `^laptop` | "laptop", "Laptop Pro" | "my laptop" |
| `=` | iexact | `=laptop` | "laptop", "LAPTOP" | "laptop pro" |
| `@` | search | `@laptop computer` | (PostgreSQL full-text) | (varies) |
| `$` | iregex | `$lap.*top` | "laptop", "lap top" | "top" |
| (none) | icontains | `laptop` | "laptop", "my laptop" | "lap" |

### Searching Related Fields

```python
class OrderViewSet(viewsets.ModelViewSet):
    queryset = Order.objects.select_related('customer', 'shipping_address')
    filter_backends = [filters.SearchFilter]

    search_fields = [
        'order_number',
        'customer__email',           # Foreign key
        'customer__first_name',
        'customer__last_name',
        'items__product__name',      # Many-to-many through relation
        'shipping_address__city',
        'shipping_address__postal_code',
    ]

# API Usage:
# ?search=john@example.com → finds orders by customer email
# ?search=New York → finds orders shipping to New York
# ?search=laptop → finds orders containing laptop products
```

### Search Term Processing

```python
# Multiple search terms (AND logic)
# ?search=laptop 15 inch
# Searches for records containing "laptop" AND "15" AND "inch"

# Quoted phrases (kept together)
# ?search="gaming laptop" 15
# Searches for exact phrase "gaming laptop" AND "15"

# Comma-separated (treated as separate terms)
# ?search=laptop,desktop
# Searches for "laptop" AND "desktop"
```

### Advanced Search Configuration

```python
from rest_framework import filters

class AdvancedSearchFilter(filters.SearchFilter):
    """
    Custom search filter with advanced features.
    """
    search_param = 'q'  # Use ?q= instead of ?search=
    search_title = 'Search'
    search_description = 'Search across product fields'

    def get_search_fields(self, view, request):
        """
        Dynamically determine search fields based on user permissions.
        """
        base_fields = ['name', 'description']

        if request.user.is_staff:
            # Staff can search internal fields
            base_fields.extend(['internal_id', 'notes'])

        if request.query_params.get('search_sku'):
            # Allow SKU search if specifically requested
            base_fields.append('=sku')

        return base_fields

    def get_search_terms(self, request):
        """
        Override to customize search term parsing.
        """
        terms = super().get_search_terms(request)

        # Remove very short terms
        terms = [term for term in terms if len(term) >= 3]

        return terms

class ProductViewSet(viewsets.ModelViewSet):
    filter_backends = [AdvancedSearchFilter]
```

### Performance Considerations

```python
# 1. Add database indexes
class Product(models.Model):
    name = models.CharField(max_length=200, db_index=True)
    sku = models.CharField(max_length=50, db_index=True)

    class Meta:
        indexes = [
            models.Index(fields=['name']),
            models.Index(fields=['sku']),
            # For PostgreSQL full-text search
            GinIndex(fields=['search_vector']),  # If using SearchVectorField
        ]

# 2. Use select_related for ForeignKey searches
class OrderViewSet(viewsets.ModelViewSet):
    def get_queryset(self):
        return Order.objects.select_related('customer', 'shipping_address')

    search_fields = ['customer__email', 'shipping_address__city']

# 3. Use prefetch_related for Many-to-Many
class ProductViewSet(viewsets.ModelViewSet):
    def get_queryset(self):
        return Product.objects.prefetch_related('tags', 'categories')

    search_fields = ['tags__name', 'categories__name']

# 4. Limit searchable fields
# BAD: Too many fields
search_fields = ['field1', 'field2', 'field3', ..., 'field20']  # Slow!

# GOOD: Focused search
search_fields = ['^name', '=sku', 'description']  # Fast

# 5. Use PostgreSQL full-text search for large text fields
class Product(models.Model):
    description = models.TextField()
    search_vector = SearchVectorField(null=True)

    class Meta:
        indexes = [GinIndex(fields=['search_vector'])]

class ProductViewSet(viewsets.ModelViewSet):
    search_fields = ['@search_vector']  # Much faster than @description
```

### Distinct() Handling

SearchFilter automatically handles duplicates from M2M relationships:

```python
# Example: Product with many tags
# Product 1: tags=[electronics, sale]
# Search: ?search=electronics
# Without distinct: Product 1 might appear twice
# SearchFilter uses EXISTS subquery to avoid this

# The filter generates:
# WHERE EXISTS (
#     SELECT 1 FROM product_tags
#     WHERE product_tags.product_id = product.id
#     AND product_tags.name ILIKE '%electronics%'
# )
```

---

## OrderingFilter

### Overview

OrderingFilter allows clients to control the sort order of results.

### Basic Usage

```python
from rest_framework import filters

class ProductViewSet(viewsets.ModelViewSet):
    queryset = Product.objects.all()
    filter_backends = [filters.OrderingFilter]

    # Fields clients can order by
    ordering_fields = ['name', 'price', 'created_at']

    # Default ordering if not specified
    ordering = ['-created_at']

# API Usage:
# GET /api/products/?ordering=price           # Ascending by price
# GET /api/products/?ordering=-price          # Descending by price
# GET /api/products/?ordering=name,-created_at # Multiple fields
```

### Ordering Field Configurations

```python
class ProductViewSet(viewsets.ModelViewSet):
    filter_backends = [filters.OrderingFilter]

    # 1. Explicit list (recommended)
    ordering_fields = ['name', 'price', 'stock', 'created_at']

    # 2. Allow all model fields (use with caution!)
    ordering_fields = '__all__'

    # 3. Field aliases (field_name, display_name)
    ordering_fields = [
        ('price', 'Price'),
        ('created_at', 'Date Created'),
        ('stock_quantity', 'Stock'),
    ]

    # 4. Include related fields
    ordering_fields = [
        'name',
        'category__name',           # Order by related field
        'manufacturer__country',
    ]

    # 5. Include annotated fields
    def get_queryset(self):
        return Product.objects.annotate(
            total_sales=Count('orders')
        )

    ordering_fields = ['name', 'price', 'total_sales']  # Includes annotation
```

### Dynamic Ordering Fields

```python
class CustomOrderingFilter(filters.OrderingFilter):
    """
    Allow different ordering fields based on user permissions.
    """
    def get_valid_fields(self, queryset, view, context=None):
        if context is None:
            context = {}

        valid_fields = [
            ('name', 'Name'),
            ('price', 'Price'),
            ('created_at', 'Created'),
        ]

        # Staff can order by internal fields
        if context.get('request') and context['request'].user.is_staff:
            valid_fields.extend([
                ('cost', 'Cost'),
                ('profit_margin', 'Margin'),
                ('internal_priority', 'Priority'),
            ])

        return valid_fields

class ProductViewSet(viewsets.ModelViewSet):
    filter_backends = [CustomOrderingFilter]
```

### Multiple Field Ordering

```python
# Client can specify multiple fields
# GET /api/products/?ordering=category,-price,name

# Translates to:
queryset.order_by('category', '-price', 'name')

# First by category ascending, then price descending, then name ascending
```

### Ordering with Related Fields

```python
class OrderViewSet(viewsets.ModelViewSet):
    queryset = Order.objects.select_related('customer', 'shipping_address')
    filter_backends = [filters.OrderingFilter]

    ordering_fields = [
        'created_at',
        'total',
        'customer__last_name',    # Order by customer's last name
        'customer__email',
        'shipping_address__city',
    ]

    ordering = ['-created_at']  # Default

# API Usage:
# ?ordering=customer__last_name → Orders sorted by customer name
```

### Custom Ordering Parameter

```python
class CustomOrderingFilter(filters.OrderingFilter):
    ordering_param = 'sort'  # Use ?sort= instead of ?ordering=
    ordering_title = 'Sort By'
    ordering_description = 'Sort results by field'

class ProductViewSet(viewsets.ModelViewSet):
    filter_backends = [CustomOrderingFilter]

# API Usage:
# GET /api/products/?sort=-price
```

### Security: Validating Ordering Fields

```python
class SafeOrderingFilter(filters.OrderingFilter):
    """
    Prevent ordering by computed properties or dangerous fields.
    """
    def remove_invalid_fields(self, queryset, fields, view, request):
        valid_fields = super().remove_invalid_fields(
            queryset, fields, view, request
        )

        # Additional validation
        dangerous_fields = ['password', 'secret_key', 'api_token']

        valid_fields = [
            field for field in valid_fields
            if field.lstrip('-') not in dangerous_fields
        ]

        return valid_fields
```

### Performance Considerations

```python
# 1. Index ordering fields
class Product(models.Model):
    price = models.DecimalField(max_digits=10, decimal_places=2, db_index=True)
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)

    class Meta:
        indexes = [
            models.Index(fields=['price']),
            models.Index(fields=['-created_at']),
            models.Index(fields=['category', '-price']),  # Composite index
        ]

# 2. Use select_related for foreign key ordering
class OrderViewSet(viewsets.ModelViewSet):
    def get_queryset(self):
        return Order.objects.select_related('customer')

    ordering_fields = ['customer__last_name']

# 3. Be careful with ordering by computed fields
class ProductViewSet(viewsets.ModelViewSet):
    def get_queryset(self):
        # This can be expensive!
        return Product.objects.annotate(
            review_count=Count('reviews'),
            avg_rating=Avg('reviews__rating')
        )

    ordering_fields = ['review_count', 'avg_rating']
    # Make sure to have proper indexes and limit dataset size

# 4. Avoid ordering by properties
class Product(models.Model):
    @property
    def computed_value(self):  # This can't be used in ORDER BY
        return self.price * self.quantity

# Instead, use annotations:
class ProductViewSet(viewsets.ModelViewSet):
    def get_queryset(self):
        return Product.objects.annotate(
            computed_value=F('price') * F('quantity')
        )

    ordering_fields = ['computed_value']
```

---

## DjangoFilterBackend

### Overview

DjangoFilterBackend provides advanced filtering using the `django-filter` package, supporting exact matches, ranges, and complex lookups.

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

### Basic Usage

```python
from django_filters import rest_framework as filters

class ProductFilter(filters.FilterSet):
    min_price = filters.NumberFilter(field_name='price', lookup_expr='gte')
    max_price = filters.NumberFilter(field_name='price', lookup_expr='lte')
    name = filters.CharFilter(lookup_expr='icontains')

    class Meta:
        model = Product
        fields = ['category', 'in_stock']  # Exact match filters

class ProductViewSet(viewsets.ModelViewSet):
    queryset = Product.objects.all()
    serializer_class = ProductSerializer
    filter_backends = [filters.DjangoFilterBackend]
    filterset_class = ProductFilter

# API Usage:
# GET /api/products/?category=electronics
# GET /api/products/?min_price=100&max_price=500
# GET /api/products/?name=laptop&in_stock=true
```

### Simple Filtering (No FilterSet)

```python
class ProductViewSet(viewsets.ModelViewSet):
    queryset = Product.objects.all()
    filter_backends = [DjangoFilterBackend]

    # Simple field filtering
    filterset_fields = ['category', 'manufacturer', 'in_stock']

# API Usage:
# GET /api/products/?category=electronics&in_stock=true
```

### Advanced FilterSet

```python
from django_filters import rest_framework as filters

class ProductFilter(filters.FilterSet):
    # Price range
    min_price = filters.NumberFilter(field_name='price', lookup_expr='gte')
    max_price = filters.NumberFilter(field_name='price', lookup_expr='lte')
    price_range = filters.RangeFilter(field_name='price')

    # Date range
    created_after = filters.DateTimeFilter(
        field_name='created_at', lookup_expr='gte'
    )
    created_before = filters.DateTimeFilter(
        field_name='created_at', lookup_expr='lte'
    )

    # Text search
    name = filters.CharFilter(lookup_expr='icontains')

    # Boolean
    is_featured = filters.BooleanFilter()

    # Choice filter
    status = filters.ChoiceFilter(choices=[
        ('draft', 'Draft'),
        ('published', 'Published'),
        ('archived', 'Archived'),
    ])

    # Multiple choice
    categories = filters.MultipleChoiceFilter(
        field_name='category__slug',
        choices=[
            ('electronics', 'Electronics'),
            ('books', 'Books'),
            ('clothing', 'Clothing'),
        ]
    )

    # Related field
    manufacturer = filters.CharFilter(
        field_name='manufacturer__name',
        lookup_expr='icontains'
    )

    # Custom method filter
    has_discount = filters.BooleanFilter(method='filter_has_discount')

    def filter_has_discount(self, queryset, name, value):
        if value:
            return queryset.filter(discount_percent__gt=0)
        return queryset.filter(discount_percent=0)

    class Meta:
        model = Product
        fields = {
            'price': ['exact', 'gte', 'lte'],
            'stock': ['exact', 'gte'],
            'category': ['exact'],
        }

# API Usage examples:
# ?min_price=100&max_price=500
# ?price_range_min=100&price_range_max=500  (alternative)
# ?created_after=2024-01-01&created_before=2024-12-31
# ?name=laptop
# ?is_featured=true
# ?status=published
# ?categories=electronics,books  (multiple values)
# ?manufacturer=apple
# ?has_discount=true
# ?price__gte=100&stock__gte=10  (using Meta fields)
```

### Common Lookup Expressions

```python
class ProductFilter(filters.FilterSet):
    class Meta:
        model = Product
        fields = {
            'name': ['exact', 'icontains', 'istartswith'],
            'price': ['exact', 'gte', 'lte', 'gt', 'lt'],
            'created_at': ['exact', 'year', 'month', 'date', 'gte', 'lte'],
            'category': ['exact', 'in'],
        }

# Generates these filter options:
# ?name=exact_match
# ?name__icontains=partial
# ?name__istartswith=prefix
# ?price=100
# ?price__gte=100
# ?price__lte=500
# ?created_at__year=2024
# ?created_at__month=12
# ?category__in=electronics,books
```

### Method Filters for Complex Logic

```python
class ProductFilter(filters.FilterSet):
    # Custom filters with business logic
    popularity = filters.CharFilter(method='filter_by_popularity')
    price_tier = filters.CharFilter(method='filter_by_price_tier')
    search = filters.CharFilter(method='filter_search')

    def filter_by_popularity(self, queryset, name, value):
        """
        Filter by popularity: high, medium, low
        """
        if value == 'high':
            return queryset.filter(view_count__gte=1000)
        elif value == 'medium':
            return queryset.filter(view_count__gte=100, view_count__lt=1000)
        elif value == 'low':
            return queryset.filter(view_count__lt=100)
        return queryset

    def filter_by_price_tier(self, queryset, name, value):
        """
        Filter by price tier: budget, mid, premium
        """
        tiers = {
            'budget': (0, 50),
            'mid': (50, 200),
            'premium': (200, float('inf'))
        }
        if value in tiers:
            min_price, max_price = tiers[value]
            return queryset.filter(price__gte=min_price, price__lt=max_price)
        return queryset

    def filter_search(self, queryset, name, value):
        """
        Combined search across multiple fields.
        """
        from django.db.models import Q
        return queryset.filter(
            Q(name__icontains=value) |
            Q(description__icontains=value) |
            Q(sku__iexact=value)
        )

    class Meta:
        model = Product
        fields = []

# API Usage:
# ?popularity=high
# ?price_tier=mid
# ?search=laptop
```

### Combining Multiple Filter Backends

```python
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import filters

class ProductViewSet(viewsets.ModelViewSet):
    queryset = Product.objects.all()
    serializer_class = ProductSerializer

    # Apply filters in this order
    filter_backends = [
        DjangoFilterBackend,      # First: Field filtering
        filters.SearchFilter,      # Then: Text search
        filters.OrderingFilter,    # Finally: Ordering
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
# 1. Filter by category=electronics and price >= 100
# 2. Search for "laptop" in name/description
# 3. Order results by price descending
```

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
            models.Index(fields=['category', '-price']),  # Common filter combo
            models.Index(fields=['-created_at']),
            models.Index(fields=['name']),
        ]
```

### 2. Optimize Queries

```python
class ProductViewSet(viewsets.ModelViewSet):
    def get_queryset(self):
        queryset = Product.objects.select_related(
            'category', 'manufacturer'
        ).prefetch_related(
            'tags', 'images'
        ).only(
            'id', 'name', 'price', 'category__name', 'manufacturer__name'
        )
        return queryset
```

### 3. Limit Filter Complexity

```python
# BAD: Allows unlimited filter combinations
filterset_fields = '__all__'

# GOOD: Explicitly define allowed filters
filterset_fields = ['category', 'price', 'in_stock']
```

## Testing Filters

```python
from rest_framework.test import APITestCase

class FilterTests(APITestCase):
    def setUp(self):
        self.product1 = Product.objects.create(
            name='Laptop', price=999, category='electronics'
        )
        self.product2 = Product.objects.create(
            name='Book', price=29, category='books'
        )

    def test_search_filter(self):
        response = self.client.get('/api/products/?search=laptop')
        self.assertEqual(len(response.data['results']), 1)
        self.assertEqual(response.data['results'][0]['name'], 'Laptop')

    def test_ordering_filter(self):
        response = self.client.get('/api/products/?ordering=-price')
        self.assertEqual(response.data['results'][0]['name'], 'Laptop')

    def test_django_filter(self):
        response = self.client.get('/api/products/?category=electronics')
        self.assertEqual(len(response.data['results']), 1)

    def test_combined_filters(self):
        response = self.client.get(
            '/api/products/?min_price=20&search=book&ordering=price'
        )
        self.assertEqual(len(response.data['results']), 1)
```

## Summary

- **SearchFilter**: Text search across multiple fields
- **OrderingFilter**: Client-controlled sorting
- **DjangoFilterBackend**: Complex field filtering with lookups

Use them together for powerful, performant APIs!
