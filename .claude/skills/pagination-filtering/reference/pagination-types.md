# Pagination Types: Complete Reference

A detailed comparison of Django REST Framework's built-in pagination classes with real-world examples, performance considerations, and migration strategies.

## Overview Table

| Feature | PageNumberPagination | LimitOffsetPagination | CursorPagination |
|---------|---------------------|----------------------|------------------|
| URL Style | `?page=3` | `?limit=10&offset=20` | `?cursor=cD0yMDIw` |
| Jump to Page | Yes | Yes | No |
| Total Count | Yes | Yes | No |
| Performance | Degrades with high page numbers | Degrades with high offsets | Consistent at any position |
| Consistency | Poor (data changes affect results) | Poor | Excellent |
| Client UX | Most intuitive | Flexible | Good for feeds |
| Database Load | O(n) for high pages | O(n) for high offsets | O(1) |

## PageNumberPagination

### Overview

PageNumberPagination divides results into pages numbered 1, 2, 3, etc. This is the most user-friendly pagination style and is what most users expect to see.

### Implementation

```python
from rest_framework.pagination import PageNumberPagination

class StandardPageNumberPagination(PageNumberPagination):
    # The default page size (required)
    page_size = 10

    # Allow client to override page size via ?page_size=20
    page_size_query_param = 'page_size'

    # Maximum page size client can request
    max_page_size = 100

    # The query parameter name for the page number
    page_query_param = 'page'  # default

    # Strings that represent the last page
    last_page_strings = ('last',)  # default

    # Custom error message
    invalid_page_message = 'Invalid page number.'
```

### Response Format

```json
{
  "count": 150,
  "next": "http://api.example.com/products/?page=3",
  "previous": "http://api.example.com/products/?page=1",
  "results": [
    {"id": 21, "name": "Product 21"},
    {"id": 22, "name": "Product 22"},
    ...
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

# Last page
GET /api/products/?page=last
```

### Pros

1. **User-Friendly**: Most intuitive for end users
2. **Total Count**: Provides total number of items
3. **Direct Access**: Can jump to any page
4. **Easy Navigation**: Next/previous links included
5. **Standard UI**: Works well with traditional pagination controls

### Cons

1. **Performance Issues**: Page 1000 requires scanning ~10,000 rows
   ```sql
   -- What happens for page 100 with page_size=10
   SELECT * FROM products ORDER BY created_at LIMIT 10 OFFSET 990;
   -- Database must read 990 rows just to skip them!
   ```

2. **Inconsistent Results**: Items can be skipped or duplicated
   ```
   User on page 1: [A, B, C, D, E]
   (Item B is deleted)
   User clicks next → page 2: [D, E, F, G, H]
   Item C was skipped!
   ```

3. **Expensive COUNT Query**: Every request requires counting total items
   ```sql
   SELECT COUNT(*) FROM products WHERE ...;
   -- Can be slow on large tables
   ```

### Performance Optimization

```python
# 1. Use database indexes
class Product(models.Model):
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)

    class Meta:
        indexes = [
            models.Index(fields=['-created_at']),
        ]

# 2. Cache count for relatively static data
from django.core.cache import cache

class CachedPageNumberPagination(PageNumberPagination):
    page_size = 10

    def get_count(self, queryset):
        cache_key = f'pagination_count:{queryset.query.__str__()}'
        count = cache.get(cache_key)
        if count is None:
            count = queryset.count()
            cache.set(cache_key, count, 300)  # Cache for 5 minutes
        return count

# 3. Use approximate counts for large tables
class ApproximatePageNumberPagination(PageNumberPagination):
    page_size = 10

    def get_count(self, queryset):
        # For PostgreSQL: Use approximate count for large tables
        if queryset.count() > 100000:
            from django.db import connection
            with connection.cursor() as cursor:
                cursor.execute(
                    f"SELECT reltuples::bigint FROM pg_class "
                    f"WHERE relname = %s",
                    [queryset.model._meta.db_table]
                )
                return int(cursor.fetchone()[0])
        return queryset.count()
```

### When to Use

- Admin interfaces
- Search results with page numbers
- Datasets under 100,000 items
- When users need to see total count
- When users need to jump to specific pages

### When to Avoid

- Very large datasets (millions of rows)
- Real-time feeds with frequent updates
- Mobile infinite scroll
- When performance at high page numbers matters

---

## LimitOffsetPagination

### Overview

LimitOffsetPagination uses SQL `LIMIT` and `OFFSET` directly, giving clients precise control over which slice of data they retrieve.

### Implementation

```python
from rest_framework.pagination import LimitOffsetPagination

class StandardLimitOffsetPagination(LimitOffsetPagination):
    # Default limit if not specified
    default_limit = 10

    # Query parameter for limit
    limit_query_param = 'limit'  # default

    # Query parameter for offset
    offset_query_param = 'offset'  # default

    # Maximum limit client can request
    max_limit = 100

    # Custom error message
    invalid_offset_message = 'Invalid offset value.'
```

### Response Format

```json
{
  "count": 150,
  "next": "http://api.example.com/products/?limit=10&offset=20",
  "previous": "http://api.example.com/products/?limit=10&offset=0",
  "results": [
    {"id": 11, "name": "Product 11"},
    {"id": 12, "name": "Product 12"},
    ...
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

# All items (up to max_limit)
GET /api/products/?limit=100
```

### Pros

1. **Direct Access**: Request any slice of data
2. **Flexible**: Great for data exports and batch processing
3. **Predictable**: `offset=20&limit=10` always means items 21-30
4. **Total Count**: Provides total number of items
5. **Simple Math**: Easy to calculate which items you'll get

### Cons

1. **Same Performance Issues as PageNumber**: High offsets are slow
   ```sql
   -- Getting items 10,000-10,010
   SELECT * FROM products ORDER BY created_at LIMIT 10 OFFSET 10000;
   -- Database still reads 10,000 rows
   ```

2. **Same Consistency Issues**: Data changes affect results

3. **Less User-Friendly**: Most users don't think in terms of "offset 40"

4. **Complex UI**: Harder to build pagination controls

### Use Cases

```python
# 1. Data Export with Progress
class ExportView(APIView):
    def get(self, request):
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

        return Response(all_data)

# 2. Parallel Data Fetching
async def fetch_all_products():
    total = 10000
    batch_size = 100
    tasks = []

    for offset in range(0, total, batch_size):
        url = f'/api/products/?limit={batch_size}&offset={offset}'
        tasks.append(fetch_url(url))

    results = await asyncio.gather(*tasks)
    return results

# 3. Skip to Specific Item
# "Show me items starting from item 500"
GET /api/products/?offset=500&limit=20
```

### Performance Optimization

Same as PageNumberPagination, since both use OFFSET:

```python
# Use indexes and consider approximate counts
class OptimizedLimitOffsetPagination(LimitOffsetPagination):
    default_limit = 10
    max_limit = 100

    def get_count(self, queryset):
        # Cache or approximate for large tables
        return super().get_count(queryset)
```

### When to Use

- Data export APIs
- Integration with systems expecting limit/offset
- Batch processing
- When you need direct access to arbitrary slices
- ETL processes

### When to Avoid

- User-facing pagination (page numbers are clearer)
- Very large datasets
- Real-time feeds
- Mobile infinite scroll

---

## CursorPagination

### Overview

CursorPagination uses an opaque cursor to page through results efficiently. It filters based on the ordering field value rather than counting/skipping rows.

### How It Works

```python
# Traditional approach (slow):
SELECT * FROM products ORDER BY created_at LIMIT 10 OFFSET 1000;
# Reads 1010 rows, returns 10

# Cursor approach (fast):
SELECT * FROM products
WHERE created_at > '2024-01-15 10:30:00'
ORDER BY created_at LIMIT 10;
# Reads 10 rows, returns 10
```

### Implementation

```python
from rest_framework.pagination import CursorPagination

class StandardCursorPagination(CursorPagination):
    # Page size (required)
    page_size = 20

    # Ordering field (MUST be unique or nearly-unique)
    ordering = '-created'  # or ['-created', 'id']

    # Query parameter for the cursor
    cursor_query_param = 'cursor'  # default

    # Allow client to override page size
    page_size_query_param = 'page_size'
    max_page_size = 100

    # Maximum offset for handling duplicate timestamps
    offset_cutoff = 1000  # default

    # Custom error message
    invalid_cursor_message = 'Invalid cursor'
```

### Ordering Requirements

```python
# BAD: Non-unique ordering
class BadCursorPagination(CursorPagination):
    ordering = 'status'  # Many items can have same status
    # Results in: (offset=50, position='active')
    # Lots of items with offset > 0 = slow!

# BETTER: Add unique tiebreaker
class GoodCursorPagination(CursorPagination):
    ordering = ['-created', 'id']
    # Results in: (offset=0, position='2024-01-15 10:30:00')
    # Most items have offset=0 = fast!

# BEST: Unique ordering field
class BestCursorPagination(CursorPagination):
    ordering = '-id'  # id is unique
```

### Response Format

```json
{
  "next": "http://api.example.com/products/?cursor=cD0yMDI0LTAxLTE1KzEwJTNBMzAlM0EwMA%3D%3D",
  "previous": "http://api.example.com/products/?cursor=cj0xJnA9MjAyNC0wMS0xNSswOSUzQTIwJTNBMDA%3D",
  "results": [
    {"id": 21, "name": "Product 21", "created": "2024-01-15T10:30:00Z"},
    {"id": 22, "name": "Product 22", "created": "2024-01-15T10:29:00Z"},
    ...
  ]
}
```

Note: No `count` field - total count is not provided (expensive to calculate).

### API Usage Examples

```bash
# First page
GET /api/products/

# Next page (cursor from previous response)
GET /api/products/?cursor=cD0yMDI0LTAxLTE1KzEwJTNBMzAlM0EwMA%3D%3D

# Previous page (cursor from current response)
GET /api/products/?cursor=cj0xJnA9MjAyNC0wMS0xNSswOSUzQTIwJTNBMDA%3D

# Custom page size
GET /api/products/?page_size=50
```

### Pros

1. **Consistent Performance**: Same speed at page 1 or page 10,000
   ```sql
   -- Always filters, never offsets
   WHERE created_at > '2024-01-15' LIMIT 10
   ```

2. **No Skipped/Duplicate Items**: Stable results during data changes
   ```
   User sees: [A, B, C, D, E]
   (Item B is deleted)
   User clicks next: [F, G, H, I, J]
   No items skipped!
   ```

3. **Scalable**: Works great with millions of rows

4. **Efficient**: Uses WHERE clause instead of OFFSET

### Cons

1. **Cannot Jump to Arbitrary Pages**: Only next/previous navigation
   ```python
   # Not possible with cursor pagination:
   GET /api/products/?page=100
   ```

2. **No Total Count**: Calculating total count defeats the purpose

3. **Requires Unique Ordering**: Must have a unique or nearly-unique field

4. **Opaque Cursors**: Users can't understand or modify cursors

5. **Complex Bookmarking**: Can't easily save "page 5" for later

### Detailed Examples

```python
# Example 1: Activity Feed (Twitter-style)
class ActivityFeedPagination(CursorPagination):
    page_size = 20
    ordering = '-created_at'

class ActivityViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = Activity.objects.all()
    serializer_class = ActivitySerializer
    pagination_class = ActivityFeedPagination

# Example 2: Time-Series Data
class TimeSeriesPagination(CursorPagination):
    page_size = 100
    ordering = '-timestamp'

class MetricsViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = Metric.objects.all()
    serializer_class = MetricSerializer
    pagination_class = TimeSeriesPagination
    # Great for: Scrolling through millions of data points

# Example 3: Ordered by Multiple Fields
class ProductCursorPagination(CursorPagination):
    page_size = 20
    ordering = ['-popularity', '-created', 'id']
    # Falls back to more unique fields

# Example 4: Reverse Chronological with Filter
class FilteredCursorPagination(CursorPagination):
    page_size = 20
    ordering = '-created_at'

class RecentOrdersViewSet(viewsets.ModelViewSet):
    serializer_class = OrderSerializer
    pagination_class = FilteredCursorPagination

    def get_queryset(self):
        # Filters work great with cursor pagination
        return Order.objects.filter(
            status='completed',
            created_at__gte=timezone.now() - timedelta(days=30)
        )
```

### Performance Optimization

```python
# 1. Ensure proper indexing
class Activity(models.Model):
    created_at = models.DateTimeField(auto_now_add=True)
    user = models.ForeignKey(User, on_delete=models.CASCADE)

    class Meta:
        indexes = [
            # Index MUST match ordering
            models.Index(fields=['-created_at']),
            # Or composite index for multi-field ordering
            models.Index(fields=['-created_at', 'id']),
        ]

# 2. Use select_related/prefetch_related
class ActivityViewSet(viewsets.ReadOnlyModelViewSet):
    pagination_class = ActivityFeedPagination

    def get_queryset(self):
        return Activity.objects.select_related(
            'user', 'target'
        ).prefetch_related(
            'comments'
        )

# 3. Ensure offset_cutoff is reasonable
class CustomCursorPagination(CursorPagination):
    page_size = 20
    ordering = ['-created', 'id']
    offset_cutoff = 1000  # Prevents malicious large offsets
```

### Migration from PageNumber to Cursor

```python
# Phase 1: Support both
class HybridView(viewsets.ModelViewSet):
    def get_pagination_class(self):
        # Check if client sends cursor parameter
        if 'cursor' in self.request.query_params:
            return CursorPagination
        return PageNumberPagination

# Phase 2: Guide clients
class DeprecatedPageView(viewsets.ModelViewSet):
    def list(self, request, *args, **kwargs):
        if 'page' in request.query_params:
            warnings.warn(
                "page parameter is deprecated. Use cursor pagination.",
                DeprecationWarning
            )
        return super().list(request, *args, **kwargs)

# Phase 3: Switch fully to cursor
class ModernView(viewsets.ModelViewSet):
    pagination_class = CursorPagination
```

### When to Use

- Activity feeds/timelines
- Real-time data streams
- Large datasets (millions of records)
- Mobile app infinite scroll
- When consistency is critical
- When you need consistent performance

### When to Avoid

- Admin interfaces needing page numbers
- When users need to jump to page X
- When total count is required
- When ordering field is not unique
- Data export (use LimitOffset instead)

---

## Comparison by Use Case

### Admin Interface
**Winner**: PageNumberPagination
- Users expect page numbers
- Total count is useful
- Dataset usually not huge

### Mobile App Feed
**Winner**: CursorPagination
- Infinite scroll pattern
- Consistent performance
- No duplicate items

### Data Export API
**Winner**: LimitOffsetPagination
- Direct slice access
- Predictable batching
- Parallel fetching

### Public Search Results
**Winner**: PageNumberPagination
- Familiar UX
- "Jump to page" functionality
- Total result count

### Real-time Activity Feed
**Winner**: CursorPagination
- New items don't mess up pagination
- Scales to millions
- Consistent experience

### Analytics Dashboard
**Winner**: LimitOffsetPagination or None
- Often need specific data ranges
- Might not need pagination
- Direct access to slices

---

## Summary Decision Matrix

Choose based on your priorities:

| Priority | Recommendation |
|----------|---------------|
| User-friendly UI | PageNumberPagination |
| Performance | CursorPagination |
| Data exports | LimitOffsetPagination |
| Consistency during updates | CursorPagination |
| Total count required | PageNumber or LimitOffset |
| Jump to arbitrary page | PageNumber or LimitOffset |
| Million+ records | CursorPagination |
| Simple implementation | PageNumberPagination |

Remember: You can always change pagination strategies later, but it requires client updates. Choose wisely based on your expected scale and use case.
