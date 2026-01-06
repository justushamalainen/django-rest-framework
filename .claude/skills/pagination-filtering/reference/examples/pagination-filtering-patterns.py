"""
Django REST Framework: Pagination and Filtering Patterns
=========================================================

Production-ready code examples demonstrating pagination and filtering strategies.
These examples are designed to be copied and adapted for real projects.

Contents:
1. Basic Pagination Patterns
2. Advanced Pagination Examples
3. Search and Ordering Examples
4. Django-filter Integration
5. Custom Filter Backends
6. Complete Real-World Examples
7. Performance Optimization Patterns
8. Testing Examples
"""

# =============================================================================
# PART 1: BASIC PAGINATION PATTERNS
# =============================================================================

from rest_framework.pagination import (
    PageNumberPagination,
    LimitOffsetPagination,
    CursorPagination,
)
from rest_framework.response import Response


# Example 1.1: Standard Page Number Pagination
class StandardResultsPagination(PageNumberPagination):
    """
    Standard pagination with customizable page size.

    API Usage:
        GET /api/products/                    # Page 1, default size
        GET /api/products/?page=2             # Page 2
        GET /api/products/?page=2&page_size=20 # Page 2, custom size
    """
    page_size = 10
    page_size_query_param = 'page_size'
    max_page_size = 100


# Example 1.2: Limit/Offset Pagination
class StandardLimitOffsetPagination(LimitOffsetPagination):
    """
    SQL-style LIMIT/OFFSET pagination.

    API Usage:
        GET /api/products/?limit=10              # First 10 items
        GET /api/products/?limit=10&offset=20    # Items 21-30
    """
    default_limit = 10
    max_limit = 100


# Example 1.3: Cursor Pagination
class StandardCursorPagination(CursorPagination):
    """
    High-performance cursor-based pagination.

    API Usage:
        GET /api/products/                # First page
        GET /api/products/?cursor=xyz123  # Next page (cursor from response)
    """
    page_size = 20
    ordering = '-created_at'
    cursor_query_param = 'cursor'


# =============================================================================
# PART 2: ADVANCED PAGINATION EXAMPLES
# =============================================================================

from django.core.cache import cache
import hashlib


# Example 2.1: Custom Response Format
class CustomFormatPagination(PageNumberPagination):
    """
    Pagination with custom JSON structure.

    Response:
    {
        "meta": {
            "total": 150,
            "page": 2,
            "pages": 15,
            "per_page": 10
        },
        "links": {
            "next": "...",
            "previous": "..."
        },
        "data": [...]
    }
    """
    page_size = 10

    def get_paginated_response(self, data):
        return Response({
            'meta': {
                'total': self.page.paginator.count,
                'page': self.page.number,
                'pages': self.page.paginator.num_pages,
                'per_page': self.page_size,
            },
            'links': {
                'next': self.get_next_link(),
                'previous': self.get_previous_link(),
            },
            'data': data,
        })

    def get_paginated_response_schema(self, schema):
        return {
            'type': 'object',
            'properties': {
                'meta': {
                    'type': 'object',
                    'properties': {
                        'total': {'type': 'integer'},
                        'page': {'type': 'integer'},
                        'pages': {'type': 'integer'},
                        'per_page': {'type': 'integer'},
                    }
                },
                'links': {
                    'type': 'object',
                    'properties': {
                        'next': {'type': 'string', 'nullable': True},
                        'previous': {'type': 'string', 'nullable': True},
                    }
                },
                'data': schema,
            }
        }


# Example 2.2: Cached Count Pagination
class CachedCountPagination(PageNumberPagination):
    """
    Cache expensive count queries for better performance.
    """
    page_size = 25
    cache_timeout = 300  # 5 minutes

    def get_cache_key(self, queryset):
        query_str = str(queryset.query)
        return f'pagination_count:{hashlib.md5(query_str.encode()).hexdigest()}'

    def paginate_queryset(self, queryset, request, view=None):
        self.request = request
        page_size = self.get_page_size(request)

        if not page_size:
            return None

        cache_key = self.get_cache_key(queryset)
        cached_count = cache.get(cache_key)

        from django.core.paginator import Paginator
        paginator = Paginator(queryset, page_size)

        if cached_count is not None:
            paginator._count = cached_count
        else:
            count = paginator.count
            cache.set(cache_key, count, self.cache_timeout)

        page_number = self.get_page_number(request, paginator)

        from rest_framework.exceptions import NotFound
        from django.core.paginator import InvalidPage
        try:
            self.page = paginator.page(page_number)
        except InvalidPage as exc:
            raise NotFound(f'Invalid page: {exc}')

        if paginator.num_pages > 1 and self.template is not None:
            self.display_page_controls = True

        return list(self.page)


# Example 2.3: User-Tier Based Pagination
class UserTierPagination(PageNumberPagination):
    """
    Adjust page size limits based on user subscription tier.
    """
    page_size = 10
    page_size_query_param = 'page_size'

    def get_page_size(self, request):
        if request.user.is_authenticated:
            # Set max page size based on user tier
            tier = getattr(request.user, 'subscription_tier', 'free')

            if tier == 'enterprise':
                self.max_page_size = 1000
                default = 100
            elif tier == 'premium':
                self.max_page_size = 200
                default = 50
            elif tier == 'basic':
                self.max_page_size = 100
                default = 25
            else:  # free
                self.max_page_size = 20
                default = 10

            return int(request.query_params.get(
                self.page_size_query_param, default
            ))

        # Anonymous users get minimal page size
        self.max_page_size = 10
        return super().get_page_size(request)


# Example 2.4: Multi-Cursor Pagination for Feed Prefetching
class FeedCursorPagination(CursorPagination):
    """
    Cursor pagination optimized for social feeds.
    Includes multiple cursors for client-side prefetching.
    """
    page_size = 20
    ordering = '-created_at'

    def get_paginated_response(self, data):
        response_data = {
            'next': self.get_next_link(),
            'previous': self.get_previous_link(),
            'results': data,
        }

        # Add metadata for feed optimization
        if self.page:
            response_data['meta'] = {
                'has_more': self.has_next,
                'items_in_page': len(self.page),
            }

        return Response(response_data)


# =============================================================================
# PART 3: SEARCH AND ORDERING EXAMPLES
# =============================================================================

from rest_framework import viewsets, filters
from django.db.models import Q


# Example 3.1: Basic Search and Ordering
class ProductViewSet(viewsets.ModelViewSet):
    """
    Product API with search and ordering.

    API Usage:
        GET /api/products/?search=laptop
        GET /api/products/?ordering=-price
        GET /api/products/?search=laptop&ordering=name
    """
    queryset = None  # Set in get_queryset
    filter_backends = [filters.SearchFilter, filters.OrderingFilter]

    # SearchFilter configuration
    search_fields = [
        '^name',              # Starts with
        '=sku',               # Exact match
        'description',        # Contains
        'category__name',     # Related field
    ]

    # OrderingFilter configuration
    ordering_fields = ['name', 'price', 'created_at', 'popularity']
    ordering = ['-created_at']  # Default ordering

    def get_queryset(self):
        return Product.objects.select_related('category').filter(is_active=True)


# Example 3.2: Advanced Search with Custom Backend
class AdvancedSearchFilter(filters.SearchFilter):
    """
    Custom search with dynamic fields based on user permissions.
    """
    search_param = 'q'

    def get_search_fields(self, view, request):
        base_fields = ['name', 'description']

        if request.user.is_authenticated:
            if request.user.is_staff:
                # Staff can search internal fields
                base_fields.extend(['internal_code', 'supplier_notes'])

            # Premium users can search by SKU
            if hasattr(request.user, 'is_premium') and request.user.is_premium:
                base_fields.append('=sku')

        return base_fields

    def get_search_terms(self, request):
        terms = super().get_search_terms(request)
        # Filter out very short terms
        return [term for term in terms if len(term) >= 2]


class AdvancedProductViewSet(viewsets.ModelViewSet):
    """
    Product API with advanced search.
    """
    queryset = None
    filter_backends = [AdvancedSearchFilter, filters.OrderingFilter]
    ordering_fields = '__all__'  # Allow ordering by any field

    def get_queryset(self):
        return Product.objects.select_related(
            'category', 'manufacturer'
        ).prefetch_related(
            'tags', 'images'
        )


# =============================================================================
# PART 4: DJANGO-FILTER INTEGRATION
# =============================================================================

from django_filters import rest_framework as django_filters
from django.db.models import Count, Avg


# Example 4.1: Basic FilterSet
class ProductFilter(django_filters.FilterSet):
    """
    Advanced filtering for products.

    API Usage:
        ?min_price=100&max_price=500
        ?category=electronics
        ?name=laptop
        ?in_stock=true
    """
    # Price range
    min_price = django_filters.NumberFilter(field_name='price', lookup_expr='gte')
    max_price = django_filters.NumberFilter(field_name='price', lookup_expr='lte')

    # Text search
    name = django_filters.CharFilter(lookup_expr='icontains')

    # Boolean
    in_stock = django_filters.BooleanFilter()

    # Date range
    created_after = django_filters.DateTimeFilter(
        field_name='created_at', lookup_expr='gte'
    )

    class Meta:
        model = Product
        fields = {
            'category': ['exact'],
            'manufacturer': ['exact'],
            'status': ['exact', 'in'],
        }


# Example 4.2: Advanced FilterSet with Method Filters
class AdvancedProductFilter(django_filters.FilterSet):
    """
    FilterSet with custom method filters.

    API Usage:
        ?price_tier=budget  # 0-50
        ?price_tier=mid     # 50-200
        ?price_tier=premium # 200+
        ?popularity=high
        ?has_discount=true
    """
    # Price tiers
    price_tier = django_filters.ChoiceFilter(
        choices=[
            ('budget', 'Budget'),
            ('mid', 'Mid-range'),
            ('premium', 'Premium'),
        ],
        method='filter_price_tier'
    )

    # Popularity
    popularity = django_filters.ChoiceFilter(
        choices=[
            ('high', 'High'),
            ('medium', 'Medium'),
            ('low', 'Low'),
        ],
        method='filter_popularity'
    )

    # Has discount
    has_discount = django_filters.BooleanFilter(method='filter_has_discount')

    # Multi-select categories
    categories = django_filters.ModelMultipleChoiceFilter(
        field_name='category',
        queryset=Category.objects.all(),
    )

    def filter_price_tier(self, queryset, name, value):
        tiers = {
            'budget': (0, 50),
            'mid': (50, 200),
            'premium': (200, 999999),
        }
        if value in tiers:
            min_price, max_price = tiers[value]
            return queryset.filter(price__gte=min_price, price__lt=max_price)
        return queryset

    def filter_popularity(self, queryset, name, value):
        # Annotate with view count and filter
        queryset = queryset.annotate(view_count=Count('views'))

        if value == 'high':
            return queryset.filter(view_count__gte=1000)
        elif value == 'medium':
            return queryset.filter(view_count__gte=100, view_count__lt=1000)
        elif value == 'low':
            return queryset.filter(view_count__lt=100)

        return queryset

    def filter_has_discount(self, queryset, name, value):
        if value:
            return queryset.exclude(discount_percent=0)
        return queryset.filter(discount_percent=0)

    class Meta:
        model = Product
        fields = []


class FilteredProductViewSet(viewsets.ModelViewSet):
    """
    Product API with comprehensive filtering.
    """
    queryset = Product.objects.all()
    filter_backends = [
        django_filters.DjangoFilterBackend,
        filters.SearchFilter,
        filters.OrderingFilter,
    ]
    filterset_class = AdvancedProductFilter
    search_fields = ['name', 'description']
    ordering_fields = ['name', 'price', 'created_at']


# =============================================================================
# PART 5: CUSTOM FILTER BACKENDS
# =============================================================================

from rest_framework.filters import BaseFilterBackend
from datetime import datetime, timedelta
from django.utils import timezone


# Example 5.1: Permission-Based Filter
class OwnerFilterBackend(BaseFilterBackend):
    """
    Filter objects to only show items owned by current user.
    Staff users can see all items.
    """
    def filter_queryset(self, request, queryset, view):
        if request.user.is_staff:
            return queryset

        if request.user.is_authenticated:
            return queryset.filter(owner=request.user)

        return queryset.none()


# Example 5.2: Date Range Filter with Shortcuts
class DateRangeFilterBackend(BaseFilterBackend):
    """
    Filter by date range with convenient shortcuts.

    API Usage:
        ?start_date=today
        ?start_date=yesterday
        ?start_date=last_week
        ?start_date=last_month
        ?start_date=2024-01-01&end_date=2024-12-31
    """
    def filter_queryset(self, request, queryset, view):
        date_field = getattr(view, 'date_filter_field', 'created_at')

        # Handle start date
        start_date = request.query_params.get('start_date')
        if start_date:
            start_date = self.parse_date(start_date)
            if start_date:
                queryset = queryset.filter(**{f'{date_field}__gte': start_date})

        # Handle end date
        end_date = request.query_params.get('end_date')
        if end_date:
            end_date = self.parse_date(end_date, is_end=True)
            if end_date:
                queryset = queryset.filter(**{f'{date_field}__lte': end_date})

        return queryset

    def parse_date(self, date_str, is_end=False):
        """Parse date string with shortcuts."""
        now = timezone.now()

        shortcuts = {
            'today': now.replace(hour=0, minute=0, second=0, microsecond=0),
            'yesterday': now - timedelta(days=1),
            'last_week': now - timedelta(days=7),
            'last_month': now - timedelta(days=30),
            'last_year': now - timedelta(days=365),
        }

        if date_str in shortcuts:
            date = shortcuts[date_str]
            if is_end and date_str == 'today':
                # For end of today
                return date.replace(hour=23, minute=59, second=59)
            return date

        # Try parsing ISO format
        try:
            return datetime.fromisoformat(date_str.replace('Z', '+00:00'))
        except ValueError:
            return None

    def get_schema_operation_parameters(self, view):
        return [
            {
                'name': 'start_date',
                'required': False,
                'in': 'query',
                'description': 'Start date (ISO format or: today, yesterday, last_week, last_month)',
                'schema': {'type': 'string'},
            },
            {
                'name': 'end_date',
                'required': False,
                'in': 'query',
                'description': 'End date (ISO format)',
                'schema': {'type': 'string', 'format': 'date-time'},
            },
        ]


# Example 5.3: Tag Filter with AND/OR Logic
class TagFilterBackend(BaseFilterBackend):
    """
    Filter by tags with configurable logic.

    API Usage:
        ?tags=python,django               # Items with python OR django
        ?tags=python,django&tags_logic=and # Items with python AND django
    """
    def filter_queryset(self, request, queryset, view):
        tags = request.query_params.get('tags')
        if not tags:
            return queryset

        tag_list = [tag.strip() for tag in tags.split(',')]
        tags_logic = request.query_params.get('tags_logic', 'or')

        if tags_logic == 'and':
            # Must have all tags
            for tag in tag_list:
                queryset = queryset.filter(tags__name=tag)
            return queryset.distinct()
        else:
            # Must have any tag
            return queryset.filter(tags__name__in=tag_list).distinct()

    def get_schema_operation_parameters(self, view):
        return [
            {
                'name': 'tags',
                'required': False,
                'in': 'query',
                'description': 'Comma-separated tag names',
                'schema': {'type': 'string'},
            },
            {
                'name': 'tags_logic',
                'required': False,
                'in': 'query',
                'description': 'Logic for matching tags: "or" or "and"',
                'schema': {
                    'type': 'string',
                    'enum': ['or', 'and'],
                    'default': 'or',
                },
            },
        ]


# =============================================================================
# PART 6: COMPLETE REAL-WORLD EXAMPLES
# =============================================================================

# Example 6.1: E-commerce Product API
class EcommerceProductViewSet(viewsets.ModelViewSet):
    """
    Complete e-commerce product API with pagination, search, and filtering.

    Features:
    - Pagination with customizable page size
    - Search by name, description, SKU
    - Filter by category, price range, stock status
    - Order by popularity, price, name, date
    - Permission-based visibility

    API Examples:
        GET /api/products/
        GET /api/products/?page=2&page_size=20
        GET /api/products/?search=laptop&ordering=-price
        GET /api/products/?category=electronics&min_price=100&max_price=500
        GET /api/products/?in_stock=true&ordering=-popularity
    """
    serializer_class = ProductSerializer
    pagination_class = StandardResultsPagination
    filter_backends = [
        django_filters.DjangoFilterBackend,
        filters.SearchFilter,
        filters.OrderingFilter,
    ]
    filterset_class = AdvancedProductFilter
    search_fields = ['^name', '=sku', 'description', 'category__name']
    ordering_fields = ['name', 'price', 'created_at', 'popularity']
    ordering = ['-popularity', '-created_at']

    def get_queryset(self):
        """Optimized queryset with proper joins."""
        queryset = Product.objects.select_related(
            'category',
            'manufacturer',
        ).prefetch_related(
            'images',
            'tags',
        ).annotate(
            popularity=Count('orders') + Count('views')
        )

        # Filter active products for regular users
        if not self.request.user.is_staff:
            queryset = queryset.filter(is_active=True, is_published=True)

        return queryset


# Example 6.2: Social Media Activity Feed
class ActivityFeedViewSet(viewsets.ReadOnlyModelViewSet):
    """
    Social media activity feed with cursor pagination.

    Features:
    - Cursor pagination for consistent infinite scroll
    - Permission-based filtering (only see own org's activities)
    - Date range filtering
    - Activity type filtering

    API Examples:
        GET /api/feed/
        GET /api/feed/?cursor=xyz123
        GET /api/feed/?activity_type=comment,like
        GET /api/feed/?start_date=last_week
    """
    serializer_class = ActivitySerializer
    pagination_class = FeedCursorPagination
    filter_backends = [DateRangeFilterBackend]
    date_filter_field = 'created_at'

    def get_queryset(self):
        """Return activities visible to current user."""
        user = self.request.user

        if not user.is_authenticated:
            return Activity.objects.none()

        # Base queryset with optimizations
        queryset = Activity.objects.select_related(
            'user',
            'target_user',
        ).prefetch_related(
            'comments',
        )

        # Filter by user's organizations
        user_orgs = user.organizations.all()
        queryset = queryset.filter(organization__in=user_orgs)

        # Optional activity type filter
        activity_types = self.request.query_params.get('activity_type')
        if activity_types:
            types = [t.strip() for t in activity_types.split(',')]
            queryset = queryset.filter(activity_type__in=types)

        return queryset


# Example 6.3: Order Management API
class OrderViewSet(viewsets.ModelViewSet):
    """
    Order management with comprehensive filtering.

    Features:
    - Standard pagination
    - Search by order number, customer name, email
    - Filter by status, date range, price range
    - Order by date, total, status
    - Permission-based access control

    API Examples:
        GET /api/orders/?status=pending,processing
        GET /api/orders/?search=john@example.com
        GET /api/orders/?min_total=100&start_date=2024-01-01
        GET /api/orders/?ordering=-created_at
    """
    serializer_class = OrderSerializer
    pagination_class = StandardResultsPagination
    filter_backends = [
        django_filters.DjangoFilterBackend,
        filters.SearchFilter,
        filters.OrderingFilter,
        OwnerFilterBackend,
        DateRangeFilterBackend,
    ]
    filterset_class = OrderFilter
    search_fields = [
        '=order_number',
        'customer__email',
        'customer__first_name',
        'customer__last_name',
    ]
    ordering_fields = ['created_at', 'total', 'status']
    ordering = ['-created_at']
    date_filter_field = 'created_at'

    def get_queryset(self):
        """Optimized order queryset."""
        return Order.objects.select_related(
            'customer',
            'shipping_address',
            'billing_address',
        ).prefetch_related(
            'items__product',
        )


# =============================================================================
# PART 7: PERFORMANCE OPTIMIZATION PATTERNS
# =============================================================================

# Example 7.1: Optimized Queryset Mixin
class OptimizedQuerysetMixin:
    """
    Mixin to optimize querysets based on action.
    """
    def get_queryset(self):
        queryset = super().get_queryset()

        # For list view, only fetch necessary fields
        if self.action == 'list':
            list_fields = getattr(self, 'list_only_fields', None)
            if list_fields:
                queryset = queryset.only(*list_fields)

        # For detail view, fetch related data
        elif self.action == 'retrieve':
            detail_select = getattr(self, 'detail_select_related', [])
            detail_prefetch = getattr(self, 'detail_prefetch_related', [])

            if detail_select:
                queryset = queryset.select_related(*detail_select)
            if detail_prefetch:
                queryset = queryset.prefetch_related(*detail_prefetch)

        return queryset


class OptimizedProductViewSet(OptimizedQuerysetMixin, viewsets.ModelViewSet):
    """
    Product API with optimized queries for different actions.
    """
    queryset = Product.objects.all()
    serializer_class = ProductSerializer

    # List view: only essential fields
    list_only_fields = [
        'id', 'name', 'price', 'image_url', 'is_available'
    ]

    # Detail view: include relations
    detail_select_related = ['category', 'manufacturer']
    detail_prefetch_related = ['images', 'reviews', 'tags']


# Example 7.2: Conditional Pagination
class ConditionalPaginationMixin:
    """
    Choose pagination class based on request or data size.
    """
    default_pagination_class = StandardResultsPagination
    large_dataset_pagination_class = CursorPagination
    large_dataset_threshold = 10000

    @property
    def pagination_class(self):
        # Check if cursor parameter is present
        if 'cursor' in self.request.query_params:
            return self.large_dataset_pagination_class

        # Check dataset size
        queryset = self.filter_queryset(self.get_queryset())
        if queryset.count() > self.large_dataset_threshold:
            return self.large_dataset_pagination_class

        return self.default_pagination_class


# =============================================================================
# PART 8: TESTING EXAMPLES
# =============================================================================

from rest_framework.test import APITestCase
from django.contrib.auth import get_user_model

User = get_user_model()


class PaginationFilteringTests(APITestCase):
    """
    Comprehensive tests for pagination and filtering.
    """

    def setUp(self):
        """Create test data."""
        self.user = User.objects.create_user('testuser', password='test')
        self.staff = User.objects.create_user('staff', is_staff=True, password='test')

        # Create test products
        for i in range(50):
            Product.objects.create(
                name=f'Product {i}',
                sku=f'SKU{i:03d}',
                price=10.00 * i,
                category=Category.objects.first(),
                is_active=i % 2 == 0,  # Every other product is active
            )

    def test_pagination_default(self):
        """Test default pagination."""
        response = self.client.get('/api/products/')

        self.assertEqual(response.status_code, 200)
        self.assertIn('count', response.data)
        self.assertIn('results', response.data)
        self.assertEqual(len(response.data['results']), 10)

    def test_pagination_custom_page_size(self):
        """Test custom page size."""
        response = self.client.get('/api/products/?page_size=20')

        self.assertEqual(len(response.data['results']), 20)

    def test_pagination_page_navigation(self):
        """Test navigating between pages."""
        # Get first page
        response = self.client.get('/api/products/')
        first_item = response.data['results'][0]

        # Get second page
        response = self.client.get('/api/products/?page=2')
        second_page_first_item = response.data['results'][0]

        # Items should be different
        self.assertNotEqual(first_item['id'], second_page_first_item['id'])

    def test_search_filter(self):
        """Test search functionality."""
        response = self.client.get('/api/products/?search=Product 1')

        # Should find Product 1, 10-19
        self.assertGreater(response.data['count'], 0)
        for item in response.data['results']:
            self.assertIn('1', item['name'])

    def test_ordering_ascending(self):
        """Test ascending ordering."""
        response = self.client.get('/api/products/?ordering=price')

        results = response.data['results']
        prices = [float(item['price']) for item in results]

        # Verify ascending order
        self.assertEqual(prices, sorted(prices))

    def test_ordering_descending(self):
        """Test descending ordering."""
        response = self.client.get('/api/products/?ordering=-price')

        results = response.data['results']
        prices = [float(item['price']) for item in results]

        # Verify descending order
        self.assertEqual(prices, sorted(prices, reverse=True))

    def test_combined_search_and_filter(self):
        """Test combining search and ordering."""
        response = self.client.get(
            '/api/products/?search=Product&ordering=-price'
        )

        self.assertEqual(response.status_code, 200)
        self.assertGreater(response.data['count'], 0)

    def test_price_range_filter(self):
        """Test filtering by price range."""
        response = self.client.get('/api/products/?min_price=100&max_price=300')

        for item in response.data['results']:
            price = float(item['price'])
            self.assertGreaterEqual(price, 100)
            self.assertLessEqual(price, 300)

    def test_permission_filter_anonymous(self):
        """Test permission filtering for anonymous users."""
        response = self.client.get('/api/orders/')

        # Anonymous users should see no orders
        self.assertEqual(response.data['count'], 0)

    def test_permission_filter_authenticated(self):
        """Test permission filtering for authenticated users."""
        self.client.force_authenticate(user=self.user)
        response = self.client.get('/api/orders/')

        # Should only see own orders
        for item in response.data['results']:
            self.assertEqual(item['owner'], self.user.id)

    def test_date_range_filter(self):
        """Test date range filtering."""
        response = self.client.get('/api/orders/?start_date=last_week')

        self.assertEqual(response.status_code, 200)

    def test_pagination_invalid_page(self):
        """Test handling of invalid page number."""
        response = self.client.get('/api/products/?page=999')

        self.assertEqual(response.status_code, 404)

    def test_max_page_size_enforced(self):
        """Test that max page size is enforced."""
        response = self.client.get('/api/products/?page_size=9999')

        # Should be limited to max_page_size
        self.assertLessEqual(len(response.data['results']), 100)


# =============================================================================
# MODELS (for reference)
# =============================================================================

from django.db import models
from django.contrib.auth import get_user_model


class Category(models.Model):
    name = models.CharField(max_length=100)
    slug = models.SlugField(unique=True)

    class Meta:
        verbose_name_plural = 'categories'


class Product(models.Model):
    name = models.CharField(max_length=200, db_index=True)
    sku = models.CharField(max_length=50, unique=True, db_index=True)
    description = models.TextField()
    price = models.DecimalField(max_digits=10, decimal_places=2, db_index=True)
    category = models.ForeignKey(Category, on_delete=models.CASCADE, related_name='products')
    manufacturer = models.ForeignKey('Manufacturer', on_delete=models.CASCADE, null=True)
    is_active = models.BooleanField(default=True, db_index=True)
    is_published = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)
    updated_at = models.DateTimeField(auto_now=True)
    discount_percent = models.IntegerField(default=0)

    class Meta:
        indexes = [
            models.Index(fields=['-created_at']),
            models.Index(fields=['category', '-price']),
            models.Index(fields=['-created_at', 'id']),  # For cursor pagination
        ]
        ordering = ['-created_at']


class Order(models.Model):
    order_number = models.CharField(max_length=50, unique=True, db_index=True)
    customer = models.ForeignKey(get_user_model(), on_delete=models.CASCADE, related_name='orders')
    owner = models.ForeignKey(get_user_model(), on_delete=models.CASCADE, related_name='owned_orders')
    status = models.CharField(max_length=20, choices=[
        ('pending', 'Pending'),
        ('processing', 'Processing'),
        ('shipped', 'Shipped'),
        ('delivered', 'Delivered'),
    ])
    total = models.DecimalField(max_digits=10, decimal_places=2)
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)

    class Meta:
        indexes = [
            models.Index(fields=['-created_at']),
            models.Index(fields=['owner', '-created_at']),
        ]


# =============================================================================
# SERIALIZERS (for reference)
# =============================================================================

from rest_framework import serializers


class ProductSerializer(serializers.ModelSerializer):
    category_name = serializers.CharField(source='category.name', read_only=True)

    class Meta:
        model = Product
        fields = [
            'id', 'name', 'sku', 'description', 'price',
            'category', 'category_name', 'is_active', 'created_at'
        ]


class OrderSerializer(serializers.ModelSerializer):
    customer_email = serializers.EmailField(source='customer.email', read_only=True)

    class Meta:
        model = Order
        fields = [
            'id', 'order_number', 'customer', 'customer_email',
            'status', 'total', 'created_at'
        ]


class ActivitySerializer(serializers.ModelSerializer):
    class Meta:
        model = Activity
        fields = ['id', 'user', 'activity_type', 'content', 'created_at']


# =============================================================================
# USAGE SUMMARY
# =============================================================================

"""
Quick Reference for Using These Patterns:

1. BASIC PAGINATION:
   - Use StandardResultsPagination for most APIs
   - Use CursorPagination for feeds and large datasets
   - Use LimitOffsetPagination for data exports

2. SEARCH AND ORDERING:
   - Add SearchFilter and OrderingFilter to filter_backends
   - Define search_fields and ordering_fields
   - Use prefixes (^, =, @, $) for search behavior

3. ADVANCED FILTERING:
   - Use django-filter for complex field filtering
   - Create FilterSet classes for custom logic
   - Use method filters for business logic

4. CUSTOM FILTERS:
   - Inherit from BaseFilterBackend
   - Implement filter_queryset()
   - Add get_schema_operation_parameters() for docs

5. PERFORMANCE:
   - Use select_related() for ForeignKey
   - Use prefetch_related() for M2M
   - Add database indexes on filtered/ordered fields
   - Cache expensive count queries
   - Use only() to limit fetched fields

6. TESTING:
   - Test pagination boundaries
   - Test filter combinations
   - Test permission-based filtering
   - Test invalid inputs

Remember:
- Start simple, add complexity only when needed
- Always index filtered and ordered fields
- Cache expensive operations
- Document your API parameters
- Test edge cases
"""
