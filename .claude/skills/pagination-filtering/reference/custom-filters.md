# Creating Custom Filter Backends

Learn how to create custom filter backends for specialized filtering requirements, complex business logic, and performance optimizations.

## Why Create Custom Filter Backends?

Create custom filter backends when you need:

1. **Complex Business Logic**: Filtering based on user permissions, subscriptions, or business rules
2. **Performance Optimizations**: Specialized query optimizations or caching
3. **Legacy API Compatibility**: Match existing filter parameter formats
4. **Custom Query Parameters**: Non-standard filtering approaches
5. **Multiple Field Filtering**: Complex filters spanning multiple fields
6. **Dynamic Filtering**: Filters that change based on context

## Understanding BaseFilterBackend

All filter backends inherit from `BaseFilterBackend`:

```python
from rest_framework.filters import BaseFilterBackend

class BaseFilterBackend:
    def filter_queryset(self, request, queryset, view):
        """
        Return a filtered queryset.
        This is the only required method.
        """
        raise NotImplementedError(".filter_queryset() must be overridden.")

    def get_schema_fields(self, view):
        """
        Return a list of coreapi.Field instances for API schema.
        (Deprecated - use get_schema_operation_parameters instead)
        """
        return []

    def get_schema_operation_parameters(self, view):
        """
        Return OpenAPI parameter definitions.
        """
        return []
```

## Basic Custom Filter Backend

### Simple Field Filter

```python
from rest_framework.filters import BaseFilterBackend

class IsActiveFilter(BaseFilterBackend):
    """
    Filter to show only active items by default.
    """
    def filter_queryset(self, request, queryset, view):
        # Check if client wants inactive items
        show_inactive = request.query_params.get('show_inactive', 'false')

        if show_inactive.lower() != 'true':
            queryset = queryset.filter(is_active=True)

        return queryset

    def get_schema_operation_parameters(self, view):
        return [
            {
                'name': 'show_inactive',
                'required': False,
                'in': 'query',
                'description': 'Include inactive items',
                'schema': {
                    'type': 'boolean',
                },
            },
        ]

# Usage
class ProductViewSet(viewsets.ModelViewSet):
    queryset = Product.objects.all()
    filter_backends = [IsActiveFilter]

# API Usage:
# GET /api/products/              → Only active items
# GET /api/products/?show_inactive=true → All items
```

## Common Custom Filter Patterns

### 1. Permission-Based Filtering

```python
class OwnerFilterBackend(BaseFilterBackend):
    """
    Filter objects to only show items owned by the current user.
    Staff users can see all items.
    """
    def filter_queryset(self, request, queryset, view):
        # Staff can see everything
        if request.user.is_staff:
            return queryset

        # Regular users only see their own items
        if request.user.is_authenticated:
            return queryset.filter(owner=request.user)

        # Anonymous users see nothing
        return queryset.none()


class OrganizationFilterBackend(BaseFilterBackend):
    """
    Filter objects by user's organization(s).
    """
    def filter_queryset(self, request, queryset, view):
        if not request.user.is_authenticated:
            return queryset.none()

        # Users can only see items from their organizations
        user_orgs = request.user.organizations.all()
        return queryset.filter(organization__in=user_orgs)


class DocumentViewSet(viewsets.ModelViewSet):
    queryset = Document.objects.all()
    filter_backends = [OrganizationFilterBackend, OwnerFilterBackend]
```

### 2. Date Range Filter

```python
from datetime import datetime, timedelta
from django.utils import timezone

class DateRangeFilterBackend(BaseFilterBackend):
    """
    Filter by date range with support for relative dates.
    """
    def filter_queryset(self, request, queryset, view):
        # Get date field from view
        date_field = getattr(view, 'date_filter_field', 'created_at')

        # Handle start date
        start_date = request.query_params.get('start_date')
        if start_date:
            if start_date == 'today':
                start_date = timezone.now().replace(
                    hour=0, minute=0, second=0, microsecond=0
                )
            elif start_date == 'yesterday':
                start_date = timezone.now() - timedelta(days=1)
                start_date = start_date.replace(
                    hour=0, minute=0, second=0, microsecond=0
                )
            elif start_date == 'last_week':
                start_date = timezone.now() - timedelta(days=7)
            elif start_date == 'last_month':
                start_date = timezone.now() - timedelta(days=30)
            else:
                # Parse ISO date
                try:
                    start_date = datetime.fromisoformat(start_date)
                except ValueError:
                    pass  # Invalid date, ignore

            if start_date:
                queryset = queryset.filter(**{
                    f'{date_field}__gte': start_date
                })

        # Handle end date
        end_date = request.query_params.get('end_date')
        if end_date:
            try:
                end_date = datetime.fromisoformat(end_date)
                queryset = queryset.filter(**{
                    f'{date_field}__lte': end_date
                })
            except ValueError:
                pass

        return queryset

    def get_schema_operation_parameters(self, view):
        return [
            {
                'name': 'start_date',
                'required': False,
                'in': 'query',
                'description': 'Filter from date (ISO format or: today, yesterday, last_week, last_month)',
                'schema': {'type': 'string'},
            },
            {
                'name': 'end_date',
                'required': False,
                'in': 'query',
                'description': 'Filter until date (ISO format)',
                'schema': {'type': 'string', 'format': 'date-time'},
            },
        ]


class OrderViewSet(viewsets.ModelViewSet):
    queryset = Order.objects.all()
    filter_backends = [DateRangeFilterBackend]
    date_filter_field = 'created_at'

# API Usage:
# ?start_date=today
# ?start_date=last_week&end_date=2024-01-15T00:00:00
```

### 3. Geolocation Filter

```python
from django.contrib.gis.measure import D  # Distance
from django.contrib.gis.geos import Point

class NearbyFilterBackend(BaseFilterBackend):
    """
    Filter objects by proximity to a location.
    Requires GeoDjango and location field on model.
    """
    def filter_queryset(self, request, queryset, view):
        lat = request.query_params.get('lat')
        lng = request.query_params.get('lng')
        radius = request.query_params.get('radius', '10')  # km

        if lat and lng:
            try:
                lat = float(lat)
                lng = float(lng)
                radius = float(radius)

                user_location = Point(lng, lat, srid=4326)
                location_field = getattr(view, 'location_field', 'location')

                queryset = queryset.filter(**{
                    f'{location_field}__distance_lte': (
                        user_location,
                        D(km=radius)
                    )
                })

                # Order by distance
                queryset = queryset.annotate(
                    distance=Distance(location_field, user_location)
                ).order_by('distance')

            except (ValueError, TypeError):
                pass  # Invalid coordinates

        return queryset

    def get_schema_operation_parameters(self, view):
        return [
            {
                'name': 'lat',
                'required': False,
                'in': 'query',
                'description': 'Latitude',
                'schema': {'type': 'number'},
            },
            {
                'name': 'lng',
                'required': False,
                'in': 'query',
                'description': 'Longitude',
                'schema': {'type': 'number'},
            },
            {
                'name': 'radius',
                'required': False,
                'in': 'query',
                'description': 'Search radius in kilometers (default: 10)',
                'schema': {'type': 'number'},
            },
        ]


class StoreViewSet(viewsets.ModelViewSet):
    queryset = Store.objects.all()
    filter_backends = [NearbyFilterBackend]
    location_field = 'coordinates'

# API Usage:
# ?lat=37.7749&lng=-122.4194&radius=5  → Stores within 5km
```

### 4. Full-Text Search Filter

```python
from django.contrib.postgres.search import (
    SearchQuery, SearchRank, SearchVector
)

class FullTextSearchFilter(BaseFilterBackend):
    """
    PostgreSQL full-text search with ranking.
    """
    search_param = 'q'

    def filter_queryset(self, request, queryset, view):
        search_term = request.query_params.get(self.search_param)

        if not search_term:
            return queryset

        # Get search fields from view
        search_fields = getattr(view, 'search_fields', ['name'])

        # Create search vector from fields
        search_vector = SearchVector(*search_fields)

        # Create search query
        search_query = SearchQuery(search_term)

        # Filter and rank results
        queryset = queryset.annotate(
            search=search_vector,
            rank=SearchRank(search_vector, search_query)
        ).filter(
            search=search_query
        ).order_by('-rank')

        return queryset

    def get_schema_operation_parameters(self, view):
        return [
            {
                'name': self.search_param,
                'required': False,
                'in': 'query',
                'description': 'Full-text search query',
                'schema': {'type': 'string'},
            },
        ]


class ArticleViewSet(viewsets.ModelViewSet):
    queryset = Article.objects.all()
    filter_backends = [FullTextSearchFilter]
    search_fields = ['title', 'content', 'tags']

# API Usage:
# ?q=django rest framework
```

### 5. Status Workflow Filter

```python
class StatusWorkflowFilter(BaseFilterBackend):
    """
    Filter based on status and workflow transitions.
    """
    def filter_queryset(self, request, queryset, view):
        status = request.query_params.get('status')
        workflow_stage = request.query_params.get('stage')

        if status:
            # Split comma-separated statuses
            statuses = [s.strip() for s in status.split(',')]
            queryset = queryset.filter(status__in=statuses)

        if workflow_stage:
            # Define workflow stages
            stages = {
                'pending': ['draft', 'submitted', 'in_review'],
                'active': ['approved', 'published', 'in_progress'],
                'completed': ['completed', 'archived', 'closed'],
            }

            if workflow_stage in stages:
                queryset = queryset.filter(status__in=stages[workflow_stage])

        # Filter by user action required
        action_required = request.query_params.get('action_required')
        if action_required == 'true' and request.user.is_authenticated:
            # Complex logic to determine if user action is needed
            queryset = queryset.filter(
                assigned_to=request.user,
                status__in=['submitted', 'in_review']
            )

        return queryset

    def get_schema_operation_parameters(self, view):
        return [
            {
                'name': 'status',
                'required': False,
                'in': 'query',
                'description': 'Filter by status (comma-separated)',
                'schema': {'type': 'string'},
            },
            {
                'name': 'stage',
                'required': False,
                'in': 'query',
                'description': 'Filter by workflow stage: pending, active, completed',
                'schema': {
                    'type': 'string',
                    'enum': ['pending', 'active', 'completed'],
                },
            },
            {
                'name': 'action_required',
                'required': False,
                'in': 'query',
                'description': 'Show items requiring user action',
                'schema': {'type': 'boolean'},
            },
        ]


class TaskViewSet(viewsets.ModelViewSet):
    queryset = Task.objects.all()
    filter_backends = [StatusWorkflowFilter]

# API Usage:
# ?status=draft,submitted
# ?stage=pending
# ?action_required=true
```

### 6. Tag/Label Filter

```python
from django.db.models import Q, Count

class TagFilterBackend(BaseFilterBackend):
    """
    Filter by tags with AND/OR logic support.
    """
    def filter_queryset(self, request, queryset, view):
        tags = request.query_params.get('tags')
        tags_logic = request.query_params.get('tags_logic', 'or')  # 'or' or 'and'

        if not tags:
            return queryset

        tag_list = [tag.strip() for tag in tags.split(',')]

        if tags_logic == 'and':
            # Must have ALL tags
            for tag in tag_list:
                queryset = queryset.filter(tags__name=tag)

            # Remove duplicates from multiple joins
            queryset = queryset.annotate(
                tag_count=Count('tags')
            ).filter(tag_count__gte=len(tag_list))

        else:  # 'or'
            # Must have ANY tag
            queryset = queryset.filter(
                tags__name__in=tag_list
            ).distinct()

        return queryset

    def get_schema_operation_parameters(self, view):
        return [
            {
                'name': 'tags',
                'required': False,
                'in': 'query',
                'description': 'Filter by tags (comma-separated)',
                'schema': {'type': 'string'},
            },
            {
                'name': 'tags_logic',
                'required': False,
                'in': 'query',
                'description': 'Tag matching logic: "or" (any tag) or "and" (all tags)',
                'schema': {
                    'type': 'string',
                    'enum': ['or', 'and'],
                    'default': 'or',
                },
            },
        ]


class BlogPostViewSet(viewsets.ModelViewSet):
    queryset = BlogPost.objects.all()
    filter_backends = [TagFilterBackend]

# API Usage:
# ?tags=python,django              → Posts with python OR django
# ?tags=python,django&tags_logic=and → Posts with python AND django
```

### 7. Cached Filter

```python
from django.core.cache import cache
import hashlib

class CachedFilterBackend(BaseFilterBackend):
    """
    Cache filter results for expensive queries.
    """
    cache_timeout = 300  # 5 minutes

    def get_cache_key(self, request, view):
        """Generate cache key from request parameters."""
        # Include relevant query params
        params = request.query_params.dict()
        params_str = str(sorted(params.items()))

        # Include view and user info
        cache_key_parts = [
            view.__class__.__name__,
            str(request.user.id) if request.user.is_authenticated else 'anon',
            params_str,
        ]

        cache_key = hashlib.md5(
            ''.join(cache_key_parts).encode()
        ).hexdigest()

        return f'filter_cache:{cache_key}'

    def filter_queryset(self, request, queryset, view):
        # Check if caching is disabled
        if request.query_params.get('no_cache') == 'true':
            return self.apply_filters(request, queryset, view)

        # Try to get from cache
        cache_key = self.get_cache_key(request, view)
        cached_ids = cache.get(cache_key)

        if cached_ids is not None:
            # Return cached results
            return queryset.filter(id__in=cached_ids)

        # Apply filters
        filtered = self.apply_filters(request, queryset, view)

        # Cache the IDs
        ids = list(filtered.values_list('id', flat=True))
        cache.set(cache_key, ids, self.cache_timeout)

        return filtered

    def apply_filters(self, request, queryset, view):
        """Implement your actual filtering logic here."""
        # Example: Complex aggregation or expensive query
        popular = request.query_params.get('popular')
        if popular == 'true':
            queryset = queryset.annotate(
                total_engagement=Count('likes') + Count('comments')
            ).filter(total_engagement__gte=100)

        return queryset


class PopularItemsViewSet(viewsets.ModelViewSet):
    queryset = Item.objects.all()
    filter_backends = [CachedFilterBackend]
```

## Advanced Techniques

### Combining Multiple Custom Filters

```python
class MultiFilterBackend(BaseFilterBackend):
    """
    Combine multiple filtering strategies in one backend.
    """
    def filter_queryset(self, request, queryset, view):
        # Apply filters in sequence
        queryset = self.apply_permission_filter(request, queryset, view)
        queryset = self.apply_date_filter(request, queryset)
        queryset = self.apply_status_filter(request, queryset)
        queryset = self.apply_search_filter(request, queryset)

        return queryset

    def apply_permission_filter(self, request, queryset, view):
        """Filter based on user permissions."""
        if not request.user.is_staff:
            queryset = queryset.filter(is_public=True)
        return queryset

    def apply_date_filter(self, request, queryset):
        """Filter by date range."""
        date_from = request.query_params.get('from')
        if date_from:
            queryset = queryset.filter(created_at__gte=date_from)
        return queryset

    def apply_status_filter(self, request, queryset):
        """Filter by status."""
        status = request.query_params.get('status')
        if status:
            queryset = queryset.filter(status=status)
        return queryset

    def apply_search_filter(self, request, queryset):
        """Basic search."""
        search = request.query_params.get('search')
        if search:
            queryset = queryset.filter(
                Q(title__icontains=search) |
                Q(description__icontains=search)
            )
        return queryset
```

### Dynamic Filter Fields

```python
class DynamicFieldFilter(BaseFilterBackend):
    """
    Allow filtering on any field defined in view.filterable_fields.
    """
    def filter_queryset(self, request, queryset, view):
        filterable_fields = getattr(view, 'filterable_fields', [])

        for field in filterable_fields:
            value = request.query_params.get(field)
            if value:
                # Handle different field types
                if '__' in field:  # Lookup expression
                    queryset = queryset.filter(**{field: value})
                else:
                    # Try exact match first
                    try:
                        queryset = queryset.filter(**{field: value})
                    except (ValueError, ValidationError):
                        # Try contains for text fields
                        queryset = queryset.filter(**{f'{field}__icontains': value})

        return queryset


class ProductViewSet(viewsets.ModelViewSet):
    queryset = Product.objects.all()
    filter_backends = [DynamicFieldFilter]
    filterable_fields = [
        'category',
        'manufacturer',
        'price__gte',
        'price__lte',
        'in_stock',
    ]

# API Usage:
# ?category=electronics&price__gte=100&in_stock=true
```

### Filter with Validation

```python
from rest_framework.exceptions import ValidationError

class ValidatedFilterBackend(BaseFilterBackend):
    """
    Filter with parameter validation.
    """
    def filter_queryset(self, request, queryset, view):
        # Validate price range
        min_price = request.query_params.get('min_price')
        max_price = request.query_params.get('max_price')

        if min_price:
            try:
                min_price = float(min_price)
                if min_price < 0:
                    raise ValidationError({'min_price': 'Must be >= 0'})
                queryset = queryset.filter(price__gte=min_price)
            except ValueError:
                raise ValidationError({'min_price': 'Must be a number'})

        if max_price:
            try:
                max_price = float(max_price)
                if max_price < 0:
                    raise ValidationError({'max_price': 'Must be >= 0'})
                queryset = queryset.filter(price__lte=max_price)
            except ValueError:
                raise ValidationError({'max_price': 'Must be a number'})

        # Validate that min <= max
        if min_price and max_price and min_price > max_price:
            raise ValidationError(
                'min_price cannot be greater than max_price'
            )

        return queryset
```

## Performance Optimization

### 1. Optimize with select_related and prefetch_related

```python
class OptimizedFilterBackend(BaseFilterBackend):
    """
    Automatically optimize queries based on filters.
    """
    def filter_queryset(self, request, queryset, view):
        # Check which filters are active
        has_category_filter = 'category' in request.query_params
        has_manufacturer_filter = 'manufacturer' in request.query_params

        # Optimize based on filters
        if has_category_filter or has_manufacturer_filter:
            queryset = queryset.select_related('category', 'manufacturer')

        if 'tags' in request.query_params:
            queryset = queryset.prefetch_related('tags')

        # Apply filters
        category = request.query_params.get('category')
        if category:
            queryset = queryset.filter(category__slug=category)

        return queryset
```

### 2. Use only() to Limit Fields

```python
class LightweightFilterBackend(BaseFilterBackend):
    """
    Limit queried fields for list views.
    """
    def filter_queryset(self, request, queryset, view):
        # For list actions, only fetch necessary fields
        if view.action == 'list':
            list_fields = getattr(view, 'list_fields', None)
            if list_fields:
                queryset = queryset.only(*list_fields)

        return queryset


class ProductViewSet(viewsets.ModelViewSet):
    queryset = Product.objects.all()
    filter_backends = [LightweightFilterBackend]
    list_fields = ['id', 'name', 'price', 'image_url']  # Only these for list
```

## Testing Custom Filters

```python
from rest_framework.test import APITestCase
from django.contrib.auth import get_user_model

User = get_user_model()


class CustomFilterTests(APITestCase):
    def setUp(self):
        self.user = User.objects.create_user('testuser', password='test')
        self.staff = User.objects.create_user('staff', is_staff=True, password='test')

        self.product1 = Product.objects.create(
            name='Active Product', is_active=True, price=100
        )
        self.product2 = Product.objects.create(
            name='Inactive Product', is_active=False, price=200
        )

    def test_is_active_filter_default(self):
        """Test default shows only active items."""
        response = self.client.get('/api/products/')
        self.assertEqual(len(response.data['results']), 1)
        self.assertEqual(response.data['results'][0]['name'], 'Active Product')

    def test_is_active_filter_with_inactive(self):
        """Test showing inactive items."""
        response = self.client.get('/api/products/?show_inactive=true')
        self.assertEqual(len(response.data['results']), 2)

    def test_permission_filter_anonymous(self):
        """Test anonymous user sees nothing."""
        response = self.client.get('/api/documents/')
        self.assertEqual(len(response.data['results']), 0)

    def test_permission_filter_authenticated(self):
        """Test authenticated user sees their own."""
        self.client.force_authenticate(user=self.user)
        response = self.client.get('/api/documents/')
        # Should only see documents owned by user

    def test_date_range_filter(self):
        """Test date range filtering."""
        response = self.client.get('/api/orders/?start_date=last_week')
        # Verify only orders from last week

    def test_filter_validation(self):
        """Test filter parameter validation."""
        response = self.client.get('/api/products/?min_price=-10')
        self.assertEqual(response.status_code, 400)
        self.assertIn('min_price', response.data)
```

## Best Practices

1. **Keep Filters Simple**: One filter backend = one concern
2. **Document Parameters**: Use `get_schema_operation_parameters()`
3. **Validate Input**: Don't trust user input
4. **Optimize Queries**: Use select_related/prefetch_related
5. **Cache When Appropriate**: For expensive queries
6. **Test Thoroughly**: Test all parameter combinations
7. **Security First**: Filter sensitive data based on permissions
8. **Fail Gracefully**: Handle invalid parameters without errors

## Summary

Custom filter backends give you complete control over:
- Complex business logic
- Permission-based filtering
- Performance optimizations
- Custom query parameters
- Integration with existing systems

Start with built-in filters (SearchFilter, OrderingFilter, DjangoFilterBackend) and create custom backends only when needed for specialized requirements.
