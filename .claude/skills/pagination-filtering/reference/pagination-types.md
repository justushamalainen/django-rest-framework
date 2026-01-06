# Pagination Types: PageNumber and LimitOffset

A focused guide to the two most commonly used pagination strategies in Django REST Framework.

## Overview Table

| Feature | PageNumberPagination | LimitOffsetPagination |
|---------|---------------------|----------------------|
| URL Style | `?page=3` | `?limit=10&offset=20` |
| Jump to Page | Yes | Yes |
| Total Count | Yes | Yes |
| User Experience | Most intuitive | Flexible |
| Best For | User-facing APIs | Data exports |

## PageNumberPagination

### Overview

PageNumberPagination divides results into pages numbered 1, 2, 3, etc. This is the most user-friendly pagination style.

### Implementation

```python
from rest_framework.pagination import PageNumberPagination

class StandardPageNumberPagination(PageNumberPagination):
    page_size = 10
    page_size_query_param = 'page_size'
    max_page_size = 100
    page_query_param = 'page'  # default
```

### Response Format

```json
{
  "count": 150,
  "next": "http://api.example.com/products/?page=3",
  "previous": "http://api.example.com/products/?page=1",
  "results": [
    {"id": 21, "name": "Product 21"},
    {"id": 22, "name": "Product 22"}
  ]
}
```

### API Usage Examples

```bash
# First page (page=1 is implied)
GET /api/products/

# Specific page
GET /api/products/?page=2

# Custom page size
GET /api/products/?page=2&page_size=20
```

### Pros

1. **User-Friendly**: Most intuitive for end users
2. **Total Count**: Provides total number of items
3. **Direct Access**: Can jump to any page
4. **Easy Navigation**: Next/previous links included

### Cons

1. **Performance Issues**: High page numbers require scanning many rows
2. **Inconsistent Results**: Items can be skipped if data changes between requests
3. **Expensive COUNT Query**: Every request requires counting total items

### When to Use

- Admin interfaces
- Search results with page numbers
- Datasets under 100,000 items
- When users need to see total count
- When users need to jump to specific pages

---

## LimitOffsetPagination

### Overview

LimitOffsetPagination uses SQL `LIMIT` and `OFFSET` directly, giving clients precise control over data slicing.

### Implementation

```python
from rest_framework.pagination import LimitOffsetPagination

class StandardLimitOffsetPagination(LimitOffsetPagination):
    default_limit = 10
    limit_query_param = 'limit'  # default
    offset_query_param = 'offset'  # default
    max_limit = 100
```

### Response Format

```json
{
  "count": 150,
  "next": "http://api.example.com/products/?limit=10&offset=20",
  "previous": "http://api.example.com/products/?limit=10&offset=0",
  "results": [
    {"id": 11, "name": "Product 11"},
    {"id": 12, "name": "Product 12"}
  ]
}
```

### API Usage Examples

```bash
# First 10 items (offset=0 is implied)
GET /api/products/?limit=10

# Items 21-30
GET /api/products/?limit=10&offset=20

# Items 101-150 (useful for data exports)
GET /api/products/?limit=50&offset=100
```

### Pros

1. **Direct Access**: Request any slice of data
2. **Flexible**: Great for data exports and batch processing
3. **Predictable**: `offset=20&limit=10` always means items 21-30
4. **Total Count**: Provides total number of items

### Cons

1. **Same Performance Issues as PageNumber**: High offsets are slow
2. **Same Consistency Issues**: Data changes affect results
3. **Less User-Friendly**: Most users don't think in terms of "offset 40"
4. **Complex UI**: Harder to build pagination controls

### Use Cases

```python
# Data Export with Progress
def export_all_products():
    batch_size = 100
    offset = 0
    all_data = []

    while True:
        url = f'/api/products/?limit={batch_size}&offset={offset}'
        response = requests.get(url)
        data = response.json()

        all_data.extend(data['results'])

        if not data['next']:
            break

        offset += batch_size
        print(f"Exported {len(all_data)}/{data['count']} items")

    return all_data
```

### When to Use

- Data export APIs
- Integration with systems expecting limit/offset
- Batch processing
- ETL processes
- When you need direct access to arbitrary slices

---

## Choosing Between Them

### Use PageNumberPagination When:
- Building user-facing interfaces
- Users expect traditional page numbers
- Total count is important
- Dataset is under 100,000 items

### Use LimitOffsetPagination When:
- Building data export functionality
- Integrating with external systems
- Performing batch operations
- Need precise control over data slicing

### Consider CursorPagination When:
- Working with millions of records
- Building infinite scroll feeds
- Consistency during pagination is critical
- See DRF documentation for CursorPagination details

## Performance Tips

Both PageNumber and LimitOffset pagination have similar performance characteristics. To optimize:

### 1. Add Database Indexes

```python
class Product(models.Model):
    name = models.CharField(max_length=200, db_index=True)
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)

    class Meta:
        indexes = [
            models.Index(fields=['-created_at']),
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

### 3. Consider Caching Count Queries

```python
from django.core.cache import cache

class CachedPageNumberPagination(PageNumberPagination):
    page_size = 10

    def get_count(self, queryset):
        cache_key = f'pagination_count:{hash(str(queryset.query))}'
        count = cache.get(cache_key)
        if count is None:
            count = queryset.count()
            cache.set(cache_key, count, 300)  # Cache for 5 minutes
        return count
```

## Summary

Both PageNumberPagination and LimitOffsetPagination are suitable for most use cases:

- **PageNumber** is more user-friendly and should be your default choice
- **LimitOffset** is more flexible for programmatic access and exports
- Both have similar performance characteristics
- For very large datasets (millions of records), consider CursorPagination

Start with PageNumberPagination and switch to LimitOffset only if you need its specific features.
