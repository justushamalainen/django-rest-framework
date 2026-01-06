"""
Complete working examples for DRF API documentation patterns.

This module demonstrates:
- Built-in OpenAPI schema generation
- Custom AutoSchema implementations
- drf-spectacular integration
- Filter and pagination documentation
- Authentication schema configuration
- Request/response differentiation
- Custom field documentation
"""

# ============================================================================
# EXAMPLE 1: Basic Schema Setup with get_schema_view()
# ============================================================================

from rest_framework.schemas import get_schema_view
from django.urls import path, include

# Simple schema endpoint
schema_view = get_schema_view(
    title='Product API',
    description='API for managing products and orders',
    version='1.0.0',
)

basic_urlpatterns = [
    path('api/schema/', schema_view, name='openapi-schema'),
    path('api/', include('products.urls')),
]


# ============================================================================
# EXAMPLE 2: Custom SchemaGenerator with Metadata
# ============================================================================

from rest_framework.schemas.openapi import SchemaGenerator


class EnhancedSchemaGenerator(SchemaGenerator):
    """Add comprehensive metadata to the OpenAPI schema."""

    def get_schema(self, request=None, public=False):
        schema = super().get_schema(request, public)

        # Add contact information
        schema['info']['contact'] = {
            'name': 'API Support Team',
            'email': 'api-support@example.com',
            'url': 'https://example.com/support'
        }

        # Add license
        schema['info']['license'] = {
            'name': 'MIT',
            'url': 'https://opensource.org/licenses/MIT'
        }

        # Add terms of service
        schema['info']['termsOfService'] = 'https://example.com/terms'

        # Add server configurations
        schema['servers'] = [
            {
                'url': 'https://api.example.com',
                'description': 'Production server'
            },
            {
                'url': 'https://staging-api.example.com',
                'description': 'Staging server'
            },
            {
                'url': 'http://localhost:8000',
                'description': 'Development server'
            }
        ]

        # Add security schemes
        schema['components']['securitySchemes'] = {
            'BearerAuth': {
                'type': 'http',
                'scheme': 'bearer',
                'bearerFormat': 'JWT',
                'description': 'JWT Bearer token authentication'
            },
            'ApiKeyAuth': {
                'type': 'apiKey',
                'in': 'header',
                'name': 'X-API-Key',
                'description': 'API key for service-to-service authentication'
            },
        }

        # Add common error response schemas
        if 'schemas' not in schema['components']:
            schema['components']['schemas'] = {}

        schema['components']['schemas']['Error'] = {
            'type': 'object',
            'properties': {
                'error': {
                    'type': 'string',
                    'description': 'Error message'
                },
                'code': {
                    'type': 'string',
                    'description': 'Error code'
                },
                'details': {
                    'type': 'object',
                    'description': 'Additional error details',
                    'additionalProperties': True
                }
            },
            'required': ['error']
        }

        return schema


# Use custom generator
enhanced_schema_view = get_schema_view(
    title='Enhanced API',
    version='1.0.0',
    generator_class=EnhancedSchemaGenerator,
)


# ============================================================================
# EXAMPLE 3: Custom AutoSchema for Field Documentation
# ============================================================================

from rest_framework.schemas.openapi import AutoSchema
from rest_framework import serializers
from decimal import Decimal


class CustomField(serializers.Field):
    """Example custom field."""
    pass


class DocumentedAutoSchema(AutoSchema):
    """
    Enhanced AutoSchema with support for:
    - Custom field types
    - Better examples
    - Enhanced descriptions
    - Rate limiting annotations
    """

    def get_operation(self, path, method):
        operation = super().get_operation(path, method)

        # Add rate limiting information
        rate_limits = {
            'GET': '1000 requests per hour',
            'POST': '100 requests per hour',
            'PUT': '100 requests per hour',
            'PATCH': '100 requests per hour',
            'DELETE': '50 requests per hour',
        }

        operation['x-rate-limit'] = rate_limits.get(method, '100 requests per hour')

        # Add cache information for GET requests
        if method == 'GET':
            operation['x-cache-ttl'] = 300  # 5 minutes

        return operation

    def get_responses(self, path, method):
        """Add comprehensive error responses."""
        responses = super().get_responses(path, method)

        # Add common error responses
        if method in ('GET', 'PUT', 'PATCH', 'DELETE'):
            responses['404'] = {
                'description': 'Resource not found',
                'content': {
                    'application/json': {
                        'schema': {'$ref': '#/components/schemas/Error'}
                    }
                }
            }

        if method in ('POST', 'PUT', 'PATCH'):
            responses['400'] = {
                'description': 'Invalid request data',
                'content': {
                    'application/json': {
                        'schema': {'$ref': '#/components/schemas/Error'},
                        'example': {
                            'error': 'Validation failed',
                            'code': 'VALIDATION_ERROR',
                            'details': {
                                'name': ['This field is required.']
                            }
                        }
                    }
                }
            }

        # Add authentication errors
        responses['401'] = {
            'description': 'Authentication credentials were not provided or are invalid',
        }

        # Add permission errors for write operations
        if method in ('POST', 'PUT', 'PATCH', 'DELETE'):
            responses['403'] = {
                'description': 'Permission denied',
            }

        # Add server error
        responses['500'] = {
            'description': 'Internal server error',
        }

        return responses

    def map_field(self, field):
        """Handle custom field types and add examples."""

        # Handle custom field
        if isinstance(field, CustomField):
            return {
                'type': 'string',
                'format': 'custom-format',
                'description': field.help_text or 'Custom field',
            }

        # Get default schema
        schema = super().map_field(field)

        # Add examples for common fields
        if isinstance(field, serializers.EmailField):
            schema['example'] = 'user@example.com'

        elif isinstance(field, serializers.URLField):
            schema['example'] = 'https://www.example.com'

        elif isinstance(field, serializers.DateTimeField):
            schema['example'] = '2024-01-15T10:30:00Z'

        elif isinstance(field, serializers.DateField):
            schema['example'] = '2024-01-15'

        elif isinstance(field, serializers.TimeField):
            schema['example'] = '10:30:00'

        elif isinstance(field, serializers.DecimalField):
            schema['example'] = '19.99'

        elif isinstance(field, serializers.UUIDField):
            schema['example'] = '123e4567-e89b-12d3-a456-426614174000'

        elif isinstance(field, serializers.CharField) and field.max_length:
            # Add example text of appropriate length
            example_length = min(field.max_length, 20)
            schema['example'] = 'Sample text'[:example_length]

        return schema

    def get_tags(self, path, method):
        """Generate context-aware tags."""
        tags = []

        # Add model-based tag if available
        if hasattr(self.view, 'queryset') and self.view.queryset is not None:
            model = self.view.queryset.model
            model_name = model._meta.verbose_name_plural.title()
            tags.append(model_name)

        # Add operation category
        if method == 'GET':
            tags.append('Read Operations')
        elif method in ('POST', 'PUT', 'PATCH', 'DELETE'):
            tags.append('Write Operations')

        # Add permission-based tags
        if hasattr(self.view, 'permission_classes'):
            for perm_class in self.view.permission_classes:
                if 'Admin' in perm_class.__name__:
                    tags.append('Admin Only')
                    break

        return tags or super().get_tags(path, method)


# ============================================================================
# EXAMPLE 4: Request/Response Differentiation
# ============================================================================

from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status


class UserInputSerializer(serializers.Serializer):
    """Serializer for user input (create/update)."""
    username = serializers.CharField(max_length=150)
    email = serializers.EmailField()
    password = serializers.CharField(write_only=True, min_length=8)
    first_name = serializers.CharField(max_length=30, required=False)
    last_name = serializers.CharField(max_length=30, required=False)


class UserOutputSerializer(serializers.Serializer):
    """Serializer for user output (responses)."""
    id = serializers.IntegerField(read_only=True)
    username = serializers.CharField()
    email = serializers.EmailField()
    first_name = serializers.CharField()
    last_name = serializers.CharField()
    date_joined = serializers.DateTimeField(read_only=True)
    last_login = serializers.DateTimeField(read_only=True, allow_null=True)
    is_active = serializers.BooleanField()


class DualSerializerAutoSchema(DocumentedAutoSchema):
    """AutoSchema that uses different serializers for request/response."""

    def get_request_serializer(self, path, method):
        """Get serializer for request body."""
        if hasattr(self.view, 'input_serializer_class'):
            return self.view.input_serializer_class()
        return super().get_request_serializer(path, method)

    def get_response_serializer(self, path, method):
        """Get serializer for response body."""
        if hasattr(self.view, 'output_serializer_class'):
            return self.view.output_serializer_class()
        return super().get_response_serializer(path, method)


class UserCreateView(APIView):
    """
    Create a new user account.

    This endpoint allows registration of new users. The password
    is validated and securely hashed before storage. A confirmation
    email is sent to the provided email address.
    """
    schema = DualSerializerAutoSchema()
    input_serializer_class = UserInputSerializer
    output_serializer_class = UserOutputSerializer

    def post(self, request):
        """
        Create a new user.

        Returns the created user details without the password.
        """
        input_serializer = self.input_serializer_class(data=request.data)
        input_serializer.is_valid(raise_exception=True)

        # Create user (simplified)
        user_data = input_serializer.validated_data
        # ... create user logic ...

        output_serializer = self.output_serializer_class({
            'id': 1,
            'username': user_data['username'],
            'email': user_data['email'],
            'first_name': user_data.get('first_name', ''),
            'last_name': user_data.get('last_name', ''),
            'date_joined': '2024-01-15T10:30:00Z',
            'last_login': None,
            'is_active': True,
        })

        return Response(output_serializer.data, status=status.HTTP_201_CREATED)


# ============================================================================
# EXAMPLE 5: Pagination Documentation
# ============================================================================

from rest_framework.pagination import PageNumberPagination
from rest_framework.generics import ListAPIView


class CustomPagination(PageNumberPagination):
    """
    Custom pagination class with configurable page size.

    Query parameters:
    - page: Page number (default: 1)
    - page_size: Items per page (default: 20, max: 100)
    """
    page_size = 20
    page_size_query_param = 'page_size'
    max_page_size = 100
    page_query_param = 'page'


class ProductSerializer(serializers.Serializer):
    """Product serializer."""
    id = serializers.IntegerField(read_only=True)
    name = serializers.CharField(max_length=200)
    description = serializers.CharField(allow_blank=True)
    price = serializers.DecimalField(max_digits=10, decimal_places=2)
    category = serializers.ChoiceField(
        choices=['electronics', 'clothing', 'books', 'other']
    )
    in_stock = serializers.BooleanField(default=True)
    created_at = serializers.DateTimeField(read_only=True)


class ProductListView(ListAPIView):
    """
    List all products.

    Returns a paginated list of products. Supports filtering,
    searching, and ordering.
    """
    schema = DocumentedAutoSchema(
        tags=['Products', 'Catalog'],
        operation_id_base='Product',
    )
    serializer_class = ProductSerializer
    pagination_class = CustomPagination

    def get_queryset(self):
        # Simplified - would normally return Product.objects.all()
        return []


# ============================================================================
# EXAMPLE 6: Filter Backend Documentation
# ============================================================================

from rest_framework.filters import BaseFilterBackend


class CategoryFilterBackend(BaseFilterBackend):
    """Filter products by category."""

    def filter_queryset(self, request, queryset, view):
        category = request.query_params.get('category')
        if category:
            queryset = queryset.filter(category=category)
        return queryset

    def get_schema_operation_parameters(self, view):
        """Provide schema for filter parameters."""
        return [
            {
                'name': 'category',
                'in': 'query',
                'description': 'Filter products by category',
                'required': False,
                'schema': {
                    'type': 'string',
                    'enum': ['electronics', 'clothing', 'books', 'other']
                },
                'example': 'electronics'
            }
        ]


class PriceRangeFilterBackend(BaseFilterBackend):
    """Filter products by price range."""

    def filter_queryset(self, request, queryset, view):
        min_price = request.query_params.get('min_price')
        max_price = request.query_params.get('max_price')

        if min_price:
            queryset = queryset.filter(price__gte=min_price)
        if max_price:
            queryset = queryset.filter(price__lte=max_price)

        return queryset

    def get_schema_operation_parameters(self, view):
        return [
            {
                'name': 'min_price',
                'in': 'query',
                'description': 'Minimum price (inclusive)',
                'required': False,
                'schema': {'type': 'number', 'format': 'decimal'},
                'example': 10.00
            },
            {
                'name': 'max_price',
                'in': 'query',
                'description': 'Maximum price (inclusive)',
                'required': False,
                'schema': {'type': 'number', 'format': 'decimal'},
                'example': 100.00
            }
        ]


class FilteredProductListView(ListAPIView):
    """
    List products with filtering.

    Supports filtering by category and price range.
    """
    schema = DocumentedAutoSchema(tags=['Products'])
    serializer_class = ProductSerializer
    pagination_class = CustomPagination
    filter_backends = [CategoryFilterBackend, PriceRangeFilterBackend]

    def get_queryset(self):
        return []  # Would return Product.objects.all()


# ============================================================================
# EXAMPLE 7: drf-spectacular Integration
# ============================================================================

try:
    from drf_spectacular.utils import (
        extend_schema,
        extend_schema_view,
        OpenApiParameter,
        OpenApiExample,
        OpenApiResponse,
    )
    from drf_spectacular.types import OpenApiTypes
    from rest_framework import viewsets

    class SpectacularProductSerializer(serializers.Serializer):
        """Product serializer for drf-spectacular example."""
        id = serializers.IntegerField(read_only=True)
        name = serializers.CharField(max_length=200)
        price = serializers.DecimalField(max_digits=10, decimal_places=2)
        category = serializers.ChoiceField(
            choices=['electronics', 'clothing', 'books']
        )

    @extend_schema_view(
        list=extend_schema(
            summary='List all products',
            description='Returns a paginated list of all products',
            parameters=[
                OpenApiParameter(
                    name='category',
                    type=OpenApiTypes.STR,
                    location=OpenApiParameter.QUERY,
                    description='Filter by category',
                    enum=['electronics', 'clothing', 'books'],
                ),
                OpenApiParameter(
                    name='search',
                    type=OpenApiTypes.STR,
                    location=OpenApiParameter.QUERY,
                    description='Search in product name and description',
                ),
            ],
            tags=['Products'],
        ),
        retrieve=extend_schema(
            summary='Get product details',
            description='Returns detailed information about a specific product',
            responses={
                200: SpectacularProductSerializer,
                404: OpenApiResponse(description='Product not found'),
            },
            tags=['Products'],
        ),
        create=extend_schema(
            summary='Create new product',
            description='Create a new product with the provided details',
            request=SpectacularProductSerializer,
            responses={
                201: SpectacularProductSerializer,
                400: OpenApiResponse(description='Invalid data'),
            },
            examples=[
                OpenApiExample(
                    'Electronics Product',
                    value={
                        'name': 'Wireless Mouse',
                        'price': '29.99',
                        'category': 'electronics',
                    },
                    request_only=True,
                ),
                OpenApiExample(
                    'Clothing Product',
                    value={
                        'name': 'Cotton T-Shirt',
                        'price': '19.99',
                        'category': 'clothing',
                    },
                    request_only=True,
                ),
            ],
            tags=['Products', 'Admin'],
        ),
        update=extend_schema(
            summary='Update product',
            description='Update all fields of a product',
            tags=['Products', 'Admin'],
        ),
        partial_update=extend_schema(
            summary='Partially update product',
            description='Update specific fields of a product',
            tags=['Products', 'Admin'],
        ),
        destroy=extend_schema(
            summary='Delete product',
            description='Permanently delete a product',
            responses={
                204: OpenApiResponse(description='Product deleted successfully'),
                404: OpenApiResponse(description='Product not found'),
            },
            tags=['Products', 'Admin'],
        ),
    )
    class SpectacularProductViewSet(viewsets.ModelViewSet):
        """
        Product management API.

        Provides CRUD operations for products with filtering,
        search, and pagination support.
        """
        serializer_class = SpectacularProductSerializer
        pagination_class = CustomPagination

        def get_queryset(self):
            return []  # Would return Product.objects.all()

except ImportError:
    # drf-spectacular not installed
    pass


# ============================================================================
# EXAMPLE 8: Complete URL Configuration
# ============================================================================

from django.urls import path, include
from rest_framework.routers import DefaultRouter

# Router for viewsets
router = DefaultRouter()
try:
    router.register('spectacular-products', SpectacularProductViewSet, basename='spectacular-product')
except NameError:
    pass

complete_urlpatterns = [
    # Basic schema with custom generator
    path(
        'api/schema/',
        get_schema_view(
            title='Complete API',
            description='Comprehensive API documentation example',
            version='1.0.0',
            generator_class=EnhancedSchemaGenerator,
        ),
        name='openapi-schema'
    ),

    # API endpoints
    path('api/users/', UserCreateView.as_view(), name='user-create'),
    path('api/products/', ProductListView.as_view(), name='product-list'),
    path('api/products/filtered/', FilteredProductListView.as_view(), name='product-filtered'),
    path('api/', include(router.urls)),
]


# ============================================================================
# EXAMPLE 9: Settings Configuration
# ============================================================================

# settings.py additions for schema generation
SCHEMA_SETTINGS = {
    'REST_FRAMEWORK': {
        # Use custom AutoSchema as default
        'DEFAULT_SCHEMA_CLASS': 'myapp.schema.DocumentedAutoSchema',

        # Schema coercion settings
        'SCHEMA_COERCE_PATH_PK': True,  # Use model field name instead of 'pk'
        'SCHEMA_COERCE_METHOD_NAMES': {
            'retrieve': 'read',
            'destroy': 'delete',
        },
    },

    # For drf-spectacular
    'SPECTACULAR_SETTINGS': {
        'TITLE': 'My API',
        'DESCRIPTION': 'Comprehensive API for managing resources',
        'VERSION': '1.0.0',
        'SERVE_INCLUDE_SCHEMA': False,

        # Schema behavior
        'COMPONENT_SPLIT_REQUEST': False,
        'COMPONENT_NO_READ_ONLY_REQUIRED': False,

        # Sorting
        'SORT_OPERATIONS': True,
        'SORT_OPERATION_PARAMETERS': True,

        # Security
        'SERVE_PERMISSIONS': ['rest_framework.permissions.AllowAny'],
        'SERVE_AUTHENTICATION': None,

        # Swagger UI
        'SWAGGER_UI_SETTINGS': {
            'deepLinking': True,
            'persistAuthorization': True,
            'displayOperationId': True,
            'filter': True,
        },

        # Additional metadata
        'CONTACT': {
            'name': 'API Support',
            'email': 'api@example.com',
        },
        'LICENSE': {
            'name': 'MIT',
            'url': 'https://opensource.org/licenses/MIT',
        },
    },
}


# ============================================================================
# EXAMPLE 10: Management Command for Schema Generation
# ============================================================================

from django.core.management.base import BaseCommand
import yaml
import json


class Command(BaseCommand):
    """Generate OpenAPI schema with custom settings."""

    help = 'Generate OpenAPI schema file'

    def add_arguments(self, parser):
        parser.add_argument(
            '--format',
            type=str,
            default='yaml',
            choices=['yaml', 'json'],
            help='Output format (yaml or json)'
        )
        parser.add_argument(
            '--file',
            type=str,
            help='Output file path'
        )
        parser.add_argument(
            '--public',
            action='store_true',
            help='Generate public schema (bypass permissions)'
        )

    def handle(self, *args, **options):
        # Generate schema
        generator = EnhancedSchemaGenerator(
            title='My API',
            description='API Documentation',
            version='1.0.0',
        )
        schema = generator.get_schema(public=options['public'])

        # Format output
        if options['format'] == 'yaml':
            output = yaml.dump(schema, default_flow_style=False, sort_keys=False)
        else:
            output = json.dumps(schema, indent=2)

        # Write to file or stdout
        if options['file']:
            with open(options['file'], 'w') as f:
                f.write(output)
            self.stdout.write(
                self.style.SUCCESS(f"Schema written to {options['file']}")
            )
        else:
            self.stdout.write(output)


# Usage:
# python manage.py generate_schema --format yaml --file schema.yml
# python manage.py generate_schema --format json --file schema.json --public
