# OpenAPI Schema Generation

Django REST Framework's built-in OpenAPI 3.0 schema generation automatically creates machine-readable API documentation from your views, serializers, and URL patterns.

**Note:** While DRF's built-in schema generation is deprecated in favor of drf-spectacular, it remains functional and useful for simple use cases.

## Overview

Schema generation has several key components:

- **SchemaGenerator** - Top-level class that walks URL patterns and collects schema information
- **AutoSchema** - Per-view introspection that generates operation details
- **SchemaView** - APIView subclass that serves schemas dynamically
- **generateschema** - Management command for generating static schemas

## Installation

```bash
# Required dependencies
pip install pyyaml uritemplate inflection

# pyyaml: YAML format output
# uritemplate: Path parameter extraction
# inflection: Pluralization for list endpoints
```

## Using get_schema_view()

The `get_schema_view()` helper creates a view that serves your schema dynamically:

### Basic Setup

```python
# urls.py
from rest_framework.schemas import get_schema_view

urlpatterns = [
    path(
        'api/schema/',
        get_schema_view(
            title='My API',
            description='API for managing resources',
            version='1.0.0',
        ),
        name='openapi-schema'
    ),
    path('api/', include('myapp.urls')),
]
```

### get_schema_view() Parameters

```python
schema_view = get_schema_view(
    # Required - API metadata
    title='My API',
    description='Comprehensive API documentation',
    version='2.0.0',

    # Optional - Schema configuration
    url='https://api.example.com/',  # Canonical base URL
    urlconf='myproject.urls',        # URL conf to inspect
    patterns=None,                    # Limit to specific patterns
    public=False,                     # Bypass permission checks

    # Optional - View configuration
    generator_class=None,                           # Custom SchemaGenerator
    authentication_classes=api_settings.DEFAULT_AUTHENTICATION_CLASSES,
    permission_classes=api_settings.DEFAULT_PERMISSION_CLASSES,
    renderer_classes=None,            # Auto-detected
)
```

### Limiting Schema Scope

Generate schemas for specific URL patterns only:

```python
# Only include API endpoints, exclude admin/auth
from django.urls import path, include

api_patterns = [
    path('products/', include('products.urls')),
    path('orders/', include('orders.urls')),
]

schema_view = get_schema_view(
    title='Public API',
    patterns=api_patterns,  # Only these endpoints
    public=True,            # Don't check permissions
)

urlpatterns = [
    path('api/', include(api_patterns)),
    path('api/schema/', schema_view, name='api-schema'),
]
```

### Multiple Schema Endpoints

Create separate schemas for different audiences:

```python
# Public API schema
public_schema = get_schema_view(
    title='Public API',
    version='1.0.0',
    patterns=[path('api/v1/', include('api.public_urls'))],
    public=True,
)

# Admin API schema
admin_schema = get_schema_view(
    title='Admin API',
    version='1.0.0',
    patterns=[path('api/v1/admin/', include('api.admin_urls'))],
    authentication_classes=[SessionAuthentication],
    permission_classes=[IsAdminUser],
)

urlpatterns = [
    path('api/schema/', public_schema, name='public-schema'),
    path('api/admin/schema/', admin_schema, name='admin-schema'),
]
```

## SchemaGenerator

The SchemaGenerator class is responsible for walking your URL patterns and building the complete schema.

### Basic Usage

```python
from rest_framework.schemas.openapi import SchemaGenerator

# Create generator
generator = SchemaGenerator(
    title='My API',
    description='API documentation',
    version='1.0.0',
    url='https://api.example.com/',
)

# Generate schema
schema = generator.get_schema()

# schema is a dict with OpenAPI 3.0 structure:
# {
#     'openapi': '3.0.2',
#     'info': {...},
#     'paths': {...},
#     'components': {...}
# }
```

### Customizing SchemaGenerator

Override methods to customize the generated schema:

```python
from rest_framework.schemas.openapi import SchemaGenerator

class CustomSchemaGenerator(SchemaGenerator):
    """Add custom metadata and external docs."""

    def get_schema(self, request=None, public=False):
        schema = super().get_schema(request, public)

        # Add contact information
        schema['info']['contact'] = {
            'name': 'API Support Team',
            'email': 'api-support@example.com',
            'url': 'https://example.com/support'
        }

        # Add terms of service
        schema['info']['termsOfService'] = 'https://example.com/terms'

        # Add license
        schema['info']['license'] = {
            'name': 'Apache 2.0',
            'url': 'https://www.apache.org/licenses/LICENSE-2.0.html'
        }

        # Add external documentation
        schema['externalDocs'] = {
            'description': 'Full API Documentation',
            'url': 'https://docs.example.com/api'
        }

        # Add security schemes
        schema['components']['securitySchemes'] = {
            'BearerAuth': {
                'type': 'http',
                'scheme': 'bearer',
                'bearerFormat': 'JWT',
            },
            'ApiKeyAuth': {
                'type': 'apiKey',
                'in': 'header',
                'name': 'X-API-Key',
            }
        }

        # Apply security globally
        schema['security'] = [
            {'BearerAuth': []},
            {'ApiKeyAuth': []}
        ]

        return schema

    def get_info(self):
        """Customize the info object."""
        info = super().get_info()
        info['x-custom-field'] = 'custom-value'
        return info

# Use custom generator
schema_view = get_schema_view(
    title='My API',
    generator_class=CustomSchemaGenerator,
)
```

### Adding Servers Configuration

```python
class ServerSchemaGenerator(SchemaGenerator):
    """Add multiple server configurations."""

    def get_schema(self, request=None, public=False):
        schema = super().get_schema(request, public)

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

        return schema
```

## Static Schema Generation

Generate a static schema file using the management command:

### Basic Command Usage

```bash
# Generate YAML schema (default)
python manage.py generateschema > schema.yml

# Generate JSON schema
python manage.py generateschema --format openapi-json > schema.json

# Write directly to file
python manage.py generateschema --file api-schema.yml

# Use specific URL conf
python manage.py generateschema --urlconf myproject.api_urls

# Specify title and version
python manage.py generateschema --title "My API" --version "2.0.0"
```

### Available Options

```bash
python manage.py generateschema --help

Options:
  --title TITLE         Schema title
  --description DESC    Schema description
  --version VERSION     Schema version
  --url URL             Schema base URL
  --urlconf URLCONF     URL conf import path
  --format FORMAT       Output format: openapi, openapi-json
  --file FILE           Output file path
  --generator CLASS     Custom SchemaGenerator class
```

### Using Custom Generator in Command

```python
# management/commands/generate_custom_schema.py
from django.core.management.base import BaseCommand
from rest_framework.schemas.openapi import SchemaGenerator
import yaml

class CustomSchemaGenerator(SchemaGenerator):
    def get_schema(self, request=None, public=False):
        schema = super().get_schema(request, public)
        # Add custom modifications
        schema['info']['x-api-id'] = 'my-api'
        return schema

class Command(BaseCommand):
    help = 'Generate custom OpenAPI schema'

    def add_arguments(self, parser):
        parser.add_argument('--file', type=str, help='Output file')

    def handle(self, *args, **options):
        generator = CustomSchemaGenerator(
            title='My API',
            version='1.0.0'
        )
        schema = generator.get_schema(public=True)

        output = yaml.dump(schema, default_flow_style=False)

        if options['file']:
            with open(options['file'], 'w') as f:
                f.write(output)
        else:
            self.stdout.write(output)
```

## Understanding the Generated Schema

The generated OpenAPI 3.0 schema follows this structure:

```yaml
openapi: 3.0.2
info:
  title: My API
  version: 1.0.0
  description: API documentation

paths:
  /api/products/:
    get:
      operationId: listProducts
      description: List all products
      parameters: []
      responses:
        '200':
          description: ''
          content:
            application/json:
              schema:
                type: array
                items:
                  $ref: '#/components/schemas/Product'
      tags:
        - products

    post:
      operationId: createProduct
      description: Create a new product
      requestBody:
        content:
          application/json:
            schema:
              $ref: '#/components/schemas/Product'
      responses:
        '201':
          description: ''
          content:
            application/json:
              schema:
                $ref: '#/components/schemas/Product'
      tags:
        - products

  /api/products/{id}/:
    get:
      operationId: retrieveProduct
      description: Retrieve a product
      parameters:
        - name: id
          in: path
          required: true
          description: A unique integer identifying this product
          schema:
            type: string
      responses:
        '200':
          description: ''
          content:
            application/json:
              schema:
                $ref: '#/components/schemas/Product'
      tags:
        - products

components:
  schemas:
    Product:
      type: object
      properties:
        id:
          type: integer
          readOnly: true
        name:
          type: string
          maxLength: 200
        price:
          type: string
          format: decimal
        description:
          type: string
          nullable: true
        created_at:
          type: string
          format: date-time
          readOnly: true
      required:
        - name
        - price
```

## Renderer Classes

SchemaView uses specific renderers based on configuration:

```python
# Default renderers when coreapi is NOT installed
from rest_framework import renderers

schema_view = get_schema_view(
    title='My API',
    renderer_classes=[
        renderers.OpenAPIRenderer,        # YAML format
        renderers.JSONOpenAPIRenderer,    # JSON format
        renderers.BrowsableAPIRenderer,   # HTML browsable API
    ]
)

# Access different formats:
# /api/schema/           -> YAML (default)
# /api/schema/?format=json -> JSON
# /api/schema/ (in browser) -> Browsable API
```

## Excluding Views from Schema

### Exclude Entire View

```python
from rest_framework.views import APIView

class InternalAPIView(APIView):
    schema = None  # Exclude from schema

    def get(self, request):
        return Response({'status': 'internal'})
```

### Exclude via URL Pattern

```python
from rest_framework.views import APIView

class InternalView(APIView):
    def get(self, request):
        return Response({})

# Mark as excluded in URL conf
urlpatterns = [
    path('internal/', InternalView.as_view(schema=None)),
]
```

## Common Patterns

### Environment-Specific Schemas

```python
from django.conf import settings
from rest_framework.schemas.openapi import SchemaGenerator

class EnvironmentSchemaGenerator(SchemaGenerator):
    """Adjust schema based on environment."""

    def get_schema(self, request=None, public=False):
        schema = super().get_schema(request, public)

        if settings.DEBUG:
            # Add debug-specific info
            schema['info']['x-environment'] = 'development'
            schema['servers'] = [
                {'url': 'http://localhost:8000', 'description': 'Local'}
            ]
        else:
            schema['info']['x-environment'] = 'production'
            schema['servers'] = [
                {'url': 'https://api.example.com', 'description': 'Production'}
            ]

        return schema
```

### Version-Specific Schemas

```python
# urls.py - Multiple API versions
from rest_framework.schemas import get_schema_view

urlpatterns = [
    # V1 API
    path('api/v1/', include('api.v1.urls')),
    path(
        'api/v1/schema/',
        get_schema_view(
            title='My API',
            version='1.0.0',
            patterns=[path('api/v1/', include('api.v1.urls'))],
        ),
        name='v1-schema'
    ),

    # V2 API
    path('api/v2/', include('api.v2.urls')),
    path(
        'api/v2/schema/',
        get_schema_view(
            title='My API',
            version='2.0.0',
            patterns=[path('api/v2/', include('api.v2.urls'))],
        ),
        name='v2-schema'
    ),
]
```

## Troubleshooting

### Schema is Empty

**Problem:** Generated schema has no paths

```python
# Check these common issues:

# 1. Views must be APIView subclasses
from rest_framework.views import APIView  # ✅ Included
from django.views import View            # ❌ Not included

# 2. Views must have schema attribute
class MyView(APIView):
    schema = None  # ❌ Explicitly excluded

# 3. URL patterns must be included
schema_view = get_schema_view(
    patterns=api_patterns,  # ❌ Ensure this includes your views
)
```

### Missing Dependencies Error

**Problem:** ImportError or AttributeError

```bash
# Solution: Install required packages
pip install pyyaml uritemplate inflection

# Or switch to drf-spectacular
pip install drf-spectacular
```

### Incorrect Path Parameters

**Problem:** Path parameters shown as `{id}` instead of descriptive names

```python
# Solution: Use SCHEMA_COERCE_PATH_PK setting
REST_FRAMEWORK = {
    'SCHEMA_COERCE_PATH_PK': True,  # Replaces {pk} with {id}
}
```

## Related Documentation

- [Schema Customization](schema-customization.md) - Customize AutoSchema for specific views
- [drf-spectacular](drf-spectacular.md) - Advanced schema generation (recommended)
- [Swagger UI & ReDoc](swagger-redoc.md) - Interactive documentation UIs
