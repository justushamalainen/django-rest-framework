# drf-spectacular Integration

drf-spectacular is the **recommended** third-party package for generating OpenAPI 3.0 schemas in Django REST Framework. It provides superior schema quality, extensive customization options, and excellent support for modern OpenAPI features.

## Why drf-spectacular?

**Advantages over built-in schema generation:**

- **Better schema quality** - More accurate type inference and validation rules
- **Extensive customization** - Decorators and extensions for fine-grained control
- **Client generation support** - Optimized for OpenAPI Generator and other tools
- **Active maintenance** - Regular updates and new feature support
- **Plugin ecosystem** - Built-in support for popular DRF packages
- **Advanced features** - Polymorphism, authentication flows, versioning, i18n
- **Better documentation** - Comprehensive docs and examples

## Installation

```bash
# Install drf-spectacular
pip install drf-spectacular

# Optional: for sidecar UI serving
pip install drf-spectacular[sidecar]
```

## Basic Setup

### 1. Add to INSTALLED_APPS

```python
# settings.py
INSTALLED_APPS = [
    # ...
    'rest_framework',
    'drf_spectacular',
    # ...
]
```

### 2. Configure REST Framework

```python
# settings.py
REST_FRAMEWORK = {
    # Use drf-spectacular's AutoSchema
    'DEFAULT_SCHEMA_CLASS': 'drf_spectacular.openapi.AutoSchema',
}
```

### 3. Configure drf-spectacular

```python
# settings.py
SPECTACULAR_SETTINGS = {
    'TITLE': 'My API',
    'DESCRIPTION': 'Comprehensive API for managing resources',
    'VERSION': '1.0.0',
    'SERVE_INCLUDE_SCHEMA': False,

    # Schema generation behavior
    'COMPONENT_SPLIT_REQUEST': False,  # Use same schema for request/response
    'COMPONENT_NO_READ_ONLY_REQUIRED': False,

    # Sorting
    'SORT_OPERATIONS': True,
    'SORT_OPERATION_PARAMETERS': True,

    # Security
    'SERVE_PERMISSIONS': ['rest_framework.permissions.AllowAny'],
    'SERVE_AUTHENTICATION': None,

    # Swagger UI configuration
    'SWAGGER_UI_SETTINGS': {
        'deepLinking': True,
        'persistAuthorization': True,
        'displayOperationId': True,
    },

    # Additional settings
    'PREPROCESSING_HOOKS': [],
    'POSTPROCESSING_HOOKS': [],
}
```

### 4. Add URL Routes

```python
# urls.py
from drf_spectacular.views import (
    SpectacularAPIView,
    SpectacularRedocView,
    SpectacularSwaggerView,
)

urlpatterns = [
    # Your API endpoints
    path('api/', include('myapp.urls')),

    # Schema endpoints
    path('api/schema/', SpectacularAPIView.as_view(), name='schema'),

    # Swagger UI
    path('api/schema/swagger-ui/', SpectacularSwaggerView.as_view(url_name='schema'), name='swagger-ui'),

    # ReDoc
    path('api/schema/redoc/', SpectacularRedocView.as_view(url_name='schema'), name='redoc'),
]
```

Now visit:
- **Schema:** http://localhost:8000/api/schema/
- **Swagger UI:** http://localhost:8000/api/schema/swagger-ui/
- **ReDoc:** http://localhost:8000/api/schema/redoc/

## Using @extend_schema Decorator

The `@extend_schema` decorator is the primary way to customize schema generation:

### Basic Usage

```python
from drf_spectacular.utils import extend_schema
from rest_framework.views import APIView
from rest_framework.response import Response

class ProductListView(APIView):
    @extend_schema(
        summary='List products',
        description='Returns a paginated list of all products',
        tags=['Products'],
    )
    def get(self, request):
        return Response([])

    @extend_schema(
        summary='Create product',
        description='Create a new product with the provided details',
        tags=['Products'],
    )
    def post(self, request):
        return Response({}, status=201)
```

### Request/Response Serializers

```python
from drf_spectacular.utils import extend_schema

class UserView(APIView):
    @extend_schema(
        request=UserInputSerializer,
        responses={
            201: UserOutputSerializer,
            400: ErrorSerializer,
        },
        summary='Create user account',
    )
    def post(self, request):
        input_serializer = UserInputSerializer(data=request.data)
        input_serializer.is_valid(raise_exception=True)
        user = input_serializer.save()
        output_serializer = UserOutputSerializer(user)
        return Response(output_serializer.data, status=201)
```

### Query Parameters

```python
from drf_spectacular.utils import extend_schema, OpenApiParameter
from drf_spectacular.types import OpenApiTypes

class ProductListView(APIView):
    @extend_schema(
        parameters=[
            OpenApiParameter(
                name='category',
                type=OpenApiTypes.STR,
                location=OpenApiParameter.QUERY,
                description='Filter by category',
                enum=['electronics', 'clothing', 'books'],
            ),
            OpenApiParameter(
                name='min_price',
                type=OpenApiTypes.FLOAT,
                location=OpenApiParameter.QUERY,
                description='Minimum price filter',
            ),
            OpenApiParameter(
                name='max_price',
                type=OpenApiTypes.FLOAT,
                location=OpenApiParameter.QUERY,
                description='Maximum price filter',
            ),
            OpenApiParameter(
                name='in_stock',
                type=OpenApiTypes.BOOL,
                location=OpenApiParameter.QUERY,
                description='Filter by stock availability',
                default=True,
            ),
        ],
        summary='List products',
        tags=['Products'],
    )
    def get(self, request):
        # Filter logic here
        return Response([])
```

### Multiple Response Types

```python
from drf_spectacular.utils import extend_schema, OpenApiResponse

class ProductDetailView(APIView):
    @extend_schema(
        responses={
            200: ProductSerializer,
            404: OpenApiResponse(
                response=ErrorSerializer,
                description='Product not found'
            ),
            403: OpenApiResponse(
                description='Access denied'
            ),
        },
        summary='Retrieve product',
    )
    def get(self, request, pk):
        return Response({})
```

### Examples in Schema

```python
from drf_spectacular.utils import extend_schema, OpenApiExample

class ProductView(APIView):
    @extend_schema(
        request=ProductSerializer,
        responses=ProductSerializer,
        examples=[
            OpenApiExample(
                'Valid Product Example',
                value={
                    'name': 'Laptop',
                    'price': '999.99',
                    'category': 'electronics',
                    'in_stock': True,
                },
                request_only=False,
                response_only=False,
            ),
            OpenApiExample(
                'Out of Stock Product',
                value={
                    'name': 'Monitor',
                    'price': '299.99',
                    'category': 'electronics',
                    'in_stock': False,
                },
                response_only=True,
            ),
        ],
        summary='Create or retrieve product',
    )
    def post(self, request):
        return Response({})
```

## ViewSet Integration

drf-spectacular works seamlessly with ViewSets:

### Basic ViewSet

```python
from rest_framework import viewsets
from drf_spectacular.utils import extend_schema, extend_schema_view

@extend_schema_view(
    list=extend_schema(summary='List all products', tags=['Products']),
    retrieve=extend_schema(summary='Get product details', tags=['Products']),
    create=extend_schema(summary='Create new product', tags=['Products']),
    update=extend_schema(summary='Update product', tags=['Products']),
    partial_update=extend_schema(summary='Partially update product', tags=['Products']),
    destroy=extend_schema(summary='Delete product', tags=['Products']),
)
class ProductViewSet(viewsets.ModelViewSet):
    queryset = Product.objects.all()
    serializer_class = ProductSerializer
```

### Custom Actions

```python
from rest_framework.decorators import action
from drf_spectacular.utils import extend_schema

class ProductViewSet(viewsets.ModelViewSet):
    queryset = Product.objects.all()
    serializer_class = ProductSerializer

    @extend_schema(
        summary='Get featured products',
        description='Returns a list of featured products',
        responses=ProductSerializer(many=True),
        tags=['Products', 'Featured'],
    )
    @action(detail=False, methods=['get'])
    def featured(self, request):
        featured = self.queryset.filter(is_featured=True)
        serializer = self.get_serializer(featured, many=True)
        return Response(serializer.data)

    @extend_schema(
        summary='Mark product as featured',
        request=None,
        responses={200: ProductSerializer},
        tags=['Products', 'Admin'],
    )
    @action(detail=True, methods=['post'])
    def feature(self, request, pk=None):
        product = self.get_object()
        product.is_featured = True
        product.save()
        serializer = self.get_serializer(product)
        return Response(serializer.data)
```

## Authentication & Security

### Configuring Auth Schemes

```python
# settings.py
SPECTACULAR_SETTINGS = {
    # ... other settings ...

    'SECURITY': [
        {
            'type': 'http',
            'scheme': 'bearer',
            'bearerFormat': 'JWT',
        },
        {
            'type': 'apiKey',
            'in': 'header',
            'name': 'X-API-Key',
        }
    ],

    # Or use auto-detection
    'APPEND_COMPONENTS': {
        'securitySchemes': {
            'BearerAuth': {
                'type': 'http',
                'scheme': 'bearer',
                'bearerFormat': 'JWT',
            },
            'ApiKeyAuth': {
                'type': 'apiKey',
                'in': 'header',
                'name': 'X-API-Key',
            },
            'OAuth2': {
                'type': 'oauth2',
                'flows': {
                    'authorizationCode': {
                        'authorizationUrl': 'https://example.com/oauth/authorize',
                        'tokenUrl': 'https://example.com/oauth/token',
                        'scopes': {
                            'read': 'Read access',
                            'write': 'Write access',
                        }
                    }
                }
            }
        }
    },
}
```

### Per-Endpoint Security

```python
from drf_spectacular.utils import extend_schema

class ProductView(APIView):
    @extend_schema(
        auth=['BearerAuth'],  # Require specific auth
        summary='Create product (authenticated)',
    )
    def post(self, request):
        return Response({})

    @extend_schema(
        auth=[],  # No auth required
        summary='List products (public)',
    )
    def get(self, request):
        return Response([])
```

## Polymorphic Serializers

Handle polymorphic/discriminated unions:

### Using @extend_schema_serializer

```python
from drf_spectacular.utils import extend_schema_serializer, PolymorphicProxySerializer
from rest_framework import serializers

class AnimalSerializer(serializers.Serializer):
    type = serializers.CharField()
    name = serializers.CharField()

class DogSerializer(AnimalSerializer):
    breed = serializers.CharField()
    good_boy = serializers.BooleanField(default=True)

class CatSerializer(AnimalSerializer):
    lives_remaining = serializers.IntegerField(default=9)

# Create polymorphic proxy
AnimalPolymorphicSerializer = PolymorphicProxySerializer(
    component_name='Animal',
    serializers=[DogSerializer, CatSerializer],
    resource_type_field_name='type',
)

class AnimalView(APIView):
    @extend_schema(
        request=AnimalPolymorphicSerializer,
        responses=AnimalPolymorphicSerializer,
    )
    def post(self, request):
        animal_type = request.data.get('type')
        if animal_type == 'dog':
            serializer = DogSerializer(data=request.data)
        else:
            serializer = CatSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        return Response(serializer.data)
```

## File Upload Documentation

```python
from drf_spectacular.utils import extend_schema
from drf_spectacular.types import OpenApiTypes

class FileUploadView(APIView):
    @extend_schema(
        request={
            'multipart/form-data': {
                'type': 'object',
                'properties': {
                    'file': {
                        'type': 'string',
                        'format': 'binary'
                    },
                    'description': {
                        'type': 'string'
                    }
                }
            }
        },
        responses={201: FileSerializer},
        summary='Upload file',
    )
    def post(self, request):
        file = request.FILES['file']
        # Process file
        return Response({'id': 1, 'filename': file.name}, status=201)
```

## Pagination Support

drf-spectacular automatically detects and documents pagination:

```python
from rest_framework.pagination import PageNumberPagination

class CustomPagination(PageNumberPagination):
    page_size = 20
    page_size_query_param = 'page_size'
    max_page_size = 100

class ProductViewSet(viewsets.ModelViewSet):
    queryset = Product.objects.all()
    serializer_class = ProductSerializer
    pagination_class = CustomPagination

# Automatically generates schema with pagination parameters:
# - page: page number
# - page_size: items per page
```

## Filter Backend Support

Works with django-filter and other filter backends:

```python
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import filters

class ProductViewSet(viewsets.ModelViewSet):
    queryset = Product.objects.all()
    serializer_class = ProductSerializer
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['category', 'in_stock']
    search_fields = ['name', 'description']
    ordering_fields = ['price', 'created_at']

# Automatically generates schema with filter parameters
```

## Versioning

Handle API versioning:

```python
# settings.py
REST_FRAMEWORK = {
    'DEFAULT_VERSIONING_CLASS': 'rest_framework.versioning.URLPathVersioning',
}

SPECTACULAR_SETTINGS = {
    'VERSION': '1.0.0',
    'SCHEMA_PATH_PREFIX': r'/api/v[0-9]',
    'SCHEMA_PATH_PREFIX_TRIM': True,
}

# urls.py - Multiple versions
from drf_spectacular.views import SpectacularAPIView

urlpatterns = [
    path('api/v1/', include('api.v1.urls')),
    path('api/v2/', include('api.v2.urls')),

    # Separate schemas per version
    path('api/v1/schema/', SpectacularAPIView.as_view(urlconf='api.v1.urls'), name='schema-v1'),
    path('api/v2/schema/', SpectacularAPIView.as_view(urlconf='api.v2.urls'), name='schema-v2'),
]
```

## Excluding Endpoints

```python
from drf_spectacular.utils import extend_schema

class InternalView(APIView):
    # Exclude from schema completely
    @extend_schema(exclude=True)
    def get(self, request):
        return Response({})
```

## Custom Extensions

Add custom OpenAPI extensions:

```python
from drf_spectacular.utils import extend_schema

class ProductView(APIView):
    @extend_schema(
        extensions={
            'x-rate-limit': '100/hour',
            'x-cache-ttl': 3600,
            'x-internal-id': 'prod-001',
        }
    )
    def get(self, request):
        return Response({})
```

## Preprocessing & Postprocessing Hooks

Modify the entire schema:

```python
# myapp/schema_hooks.py

def preprocessing_hook(endpoints):
    """
    Filter or modify endpoints before schema generation.

    endpoints: list of (path, path_regex, method, callback) tuples
    """
    # Remove all internal endpoints
    return [
        (path, path_regex, method, callback)
        for path, path_regex, method, callback in endpoints
        if not path.startswith('/internal/')
    ]

def postprocessing_hook(result, generator, request, public):
    """
    Modify the complete schema after generation.

    result: dict containing the OpenAPI schema
    generator: SchemaGenerator instance
    request: HttpRequest or None
    public: bool indicating if schema is public
    """
    # Add custom metadata
    result['info']['x-api-id'] = 'my-api'
    result['info']['contact'] = {
        'name': 'API Support',
        'email': 'support@example.com',
    }

    # Add servers
    result['servers'] = [
        {'url': 'https://api.example.com', 'description': 'Production'},
        {'url': 'https://staging-api.example.com', 'description': 'Staging'},
    ]

    return result

# settings.py
SPECTACULAR_SETTINGS = {
    'PREPROCESSING_HOOKS': ['myapp.schema_hooks.preprocessing_hook'],
    'POSTPROCESSING_HOOKS': ['myapp.schema_hooks.postprocessing_hook'],
}
```

## Generating Static Schema

```bash
# Generate schema file
python manage.py spectacular --file schema.yml

# Generate as JSON
python manage.py spectacular --format openapi-json --file schema.json

# Validate schema
python manage.py spectacular --validate

# Custom generator
python manage.py spectacular --file schema.yml --generator path.to.GeneratorClass
```

## Testing Schema

```python
# tests.py
from django.test import TestCase
from rest_framework.test import APIClient

class SchemaTestCase(TestCase):
    def test_schema_generation(self):
        client = APIClient()
        response = client.get('/api/schema/')
        self.assertEqual(response.status_code, 200)
        schema = response.json()

        # Validate schema structure
        self.assertIn('openapi', schema)
        self.assertIn('info', schema)
        self.assertIn('paths', schema)

        # Validate specific endpoints
        self.assertIn('/api/products/', schema['paths'])
        self.assertIn('get', schema['paths']['/api/products/'])
```

## Common Configuration Options

```python
# settings.py
SPECTACULAR_SETTINGS = {
    # Core settings
    'TITLE': 'My API',
    'DESCRIPTION': 'API Documentation',
    'VERSION': '1.0.0',
    'CONTACT': {'email': 'api@example.com'},
    'LICENSE': {'name': 'MIT'},

    # Schema generation
    'COMPONENT_SPLIT_REQUEST': False,
    'COMPONENT_NO_READ_ONLY_REQUIRED': False,
    'ENUM_NAME_OVERRIDES': {},

    # Operation settings
    'OPERATION_ID_FUNCTION': 'drf_spectacular.utils.camelize_operation_id',
    'TAGS': [],
    'SORT_OPERATIONS': True,

    # Security
    'SERVE_PERMISSIONS': ['rest_framework.permissions.AllowAny'],
    'SERVE_AUTHENTICATION': None,
    'SERVE_PUBLIC': True,

    # UI settings
    'SWAGGER_UI_DIST': 'SIDECAR',
    'SWAGGER_UI_FAVICON_HREF': 'SIDECAR',
    'REDOC_DIST': 'SIDECAR',

    # Advanced
    'SCHEMA_PATH_PREFIX': r'',
    'DEFAULT_GENERATOR_CLASS': 'drf_spectacular.generators.SchemaGenerator',
    'CAMELIZE_NAMES': False,
}
```

## Best Practices

1. **Use @extend_schema liberally** - Document all endpoints
2. **Add examples** - Help users understand data formats
3. **Document error responses** - Include all possible status codes
4. **Use tags consistently** - Organize endpoints logically
5. **Leverage polymorphism** - Use PolymorphicProxySerializer for unions
6. **Test schema generation** - Validate regularly
7. **Version your API** - Use proper versioning schemes
8. **Add authentication docs** - Document all auth methods
9. **Use preprocessing hooks** - Filter internal endpoints
10. **Customize operation IDs** - Make them readable and stable

## Troubleshooting

### Schema not updating

```bash
# Clear cache and regenerate
python manage.py spectacular --file schema.yml --validate
```

### Missing parameters

```python
# Ensure filter backends implement get_schema_operation_parameters()
# Or use @extend_schema(parameters=[...])
```

### Incorrect types

```python
# Use OpenApiTypes explicitly
from drf_spectacular.types import OpenApiTypes
from drf_spectacular.utils import extend_schema, OpenApiParameter

@extend_schema(
    parameters=[
        OpenApiParameter('id', OpenApiTypes.INT, OpenApiParameter.PATH),
    ]
)
```

## Related Documentation

- [OpenAPI Generation](openapi-generation.md) - Built-in schema generation
- [Schema Customization](schema-customization.md) - AutoSchema customization
- [Swagger UI & ReDoc](swagger-redoc.md) - Interactive documentation UIs
- [Official drf-spectacular docs](https://drf-spectacular.readthedocs.io/)
