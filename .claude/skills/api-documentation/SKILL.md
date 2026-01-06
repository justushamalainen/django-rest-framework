---
skill: api-documentation
description: Master Django REST Framework's API documentation and schema generation - built-in OpenAPI, AutoSchema, drf-spectacular, Swagger UI, and ReDoc
dependencies:
  - rest_framework.schemas
  - pyyaml
  - uritemplate
  - inflection
tags:
  - openapi
  - schema
  - documentation
  - swagger
  - redoc
  - drf-spectacular
related_skills:
  - viewsets
  - serializers
  - views
version: 1.0.0
---

# API Documentation & Schema Generation

Generate comprehensive, interactive API documentation for your Django REST Framework APIs using OpenAPI schemas, AutoSchema customization, drf-spectacular, Swagger UI, and ReDoc.

## What You'll Learn

By mastering this skill, you'll be able to:

- **Generate OpenAPI 3.0 schemas** automatically from your DRF API views
- **Use `get_schema_view()`** to serve dynamic schemas from your API
- **Customize schema generation** with AutoSchema subclasses and decorators
- **Set up drf-spectacular** for advanced schema generation (recommended)
- **Integrate Swagger UI and ReDoc** for interactive API documentation
- **Handle custom fields and serializers** in schema generation
- **Configure operation IDs, tags, and descriptions** for better documentation
- **Generate static schemas** with the `generateschema` management command
- **Customize schema metadata** including titles, descriptions, and versions
- **Debug common schema generation issues** like duplicate operation IDs

## Quick Start

### Basic Schema Generation

```python
# urls.py - Add a dynamic schema endpoint
from rest_framework.schemas import get_schema_view

urlpatterns = [
    # Generate OpenAPI schema dynamically
    path(
        'api/schema/',
        get_schema_view(
            title='My API',
            description='API for managing resources',
            version='1.0.0',
        ),
        name='openapi-schema'
    ),
    # Your API endpoints
    path('api/', include('myapp.urls')),
]
```

### Install Required Dependencies

```bash
# For built-in schema generation
pip install pyyaml uritemplate inflection

# For drf-spectacular (recommended)
pip install drf-spectacular
```

### Generate a Static Schema

```bash
# Generate a static OpenAPI schema file
python manage.py generateschema --file openapi-schema.yml

# Or as JSON
python manage.py generateschema --format openapi-json --file openapi-schema.json
```

### Basic AutoSchema Customization

```python
from rest_framework.schemas.openapi import AutoSchema
from rest_framework.views import APIView

class CustomAutoSchema(AutoSchema):
    """Custom schema with additional metadata."""

    def get_operation(self, path, method):
        operation = super().get_operation(path, method)
        # Add custom metadata
        operation['x-custom-field'] = 'custom-value'
        return operation

class MyAPIView(APIView):
    schema = CustomAutoSchema()

    def get(self, request):
        """List all items.

        Returns a list of all available items in the system.
        """
        return Response({'items': []})
```

## Decision Tree: Choosing Your Documentation Strategy

```
Start: Need API Documentation?
│
├─> Do you need extensive customization and client generation?
│   └─> YES → Use drf-spectacular
│       ├─> Install: pip install drf-spectacular
│       ├─> See: reference/drf-spectacular.md
│       └─> Best for: Production APIs, client SDK generation, complex schemas
│
├─> Do you need basic OpenAPI schema with minimal setup?
│   └─> YES → Use built-in schema generation
│       ├─> Install: pip install pyyaml uritemplate inflection
│       ├─> See: reference/openapi-generation.md
│       └─> Best for: Simple APIs, quick prototypes, learning
│
├─> Need to customize specific views or fields?
│   └─> YES → Extend AutoSchema
│       ├─> Override: get_operation(), map_field(), get_tags()
│       ├─> See: reference/schema-customization.md
│       └─> Best for: Custom fields, special behaviors
│
├─> Want interactive documentation UI?
│   └─> YES → Add Swagger UI or ReDoc
│       ├─> Swagger UI: Interactive API testing
│       ├─> ReDoc: Clean, responsive documentation
│       ├─> See: reference/swagger-redoc.md
│       └─> Best for: Public APIs, developer portals
│
└─> Need static schema for external tools?
    └─> YES → Use generateschema command
        ├─> Output: YAML or JSON file
        ├─> Use with: Code generators, testing tools
        └─> Best for: Contract-first development, CI/CD
```

## Common Schema Patterns

### 1. Per-View Schema Customization

```python
from rest_framework.views import APIView
from rest_framework.schemas.openapi import AutoSchema

class ProductListView(APIView):
    """Product list with custom schema."""
    schema = AutoSchema(
        tags=['Products'],
        operation_id_base='Product',
        component_name='Product'
    )

    def get(self, request):
        """List products.

        Returns a paginated list of all products.
        Supports filtering by category and price range.
        """
        pass
```

### 2. Custom Schema Generator

```python
from rest_framework.schemas.openapi import SchemaGenerator

class CustomSchemaGenerator(SchemaGenerator):
    """Add custom metadata to the schema."""

    def get_schema(self, request=None, public=False):
        schema = super().get_schema(request, public)
        # Add API metadata
        schema['info']['contact'] = {
            'name': 'API Support',
            'email': 'api@example.com'
        }
        schema['info']['termsOfService'] = 'https://example.com/terms'
        return schema

# Use in get_schema_view()
schema_view = get_schema_view(
    title='My API',
    generator_class=CustomSchemaGenerator,
)
```

### 3. Excluding Views from Schema

```python
from rest_framework.views import APIView

class InternalAPIView(APIView):
    # Exclude this view from schema generation
    schema = None

    def get(self, request):
        """Internal endpoint - not in public schema."""
        pass
```

## Common Mistakes and Solutions

### Mistake 1: Missing Dependencies

```python
# ❌ WRONG - Schema generation fails silently
urlpatterns = [
    path('schema/', get_schema_view(title='API')),
]

# Error: ImportError or AttributeError related to uritemplate/inflection
```

**Solution:** Install all required dependencies

```bash
# ✅ CORRECT - Install dependencies first
pip install pyyaml uritemplate inflection

# Or use drf-spectacular instead
pip install drf-spectacular
```

### Mistake 2: Duplicate Operation IDs

```python
# ❌ WRONG - Multiple views with the same model/serializer
class UserListView(ListAPIView):
    queryset = User.objects.all()
    serializer_class = UserSerializer
    # operationId: listUsers

class ActiveUserListView(ListAPIView):
    queryset = User.objects.filter(is_active=True)
    serializer_class = UserSerializer
    # operationId: listUsers (DUPLICATE!)
```

**Solution:** Specify unique operation_id_base

```python
# ✅ CORRECT - Unique operation IDs
from rest_framework.schemas.openapi import AutoSchema

class ActiveUserListView(ListAPIView):
    schema = AutoSchema(operation_id_base='ActiveUser')
    queryset = User.objects.filter(is_active=True)
    serializer_class = UserSerializer
    # operationId: listActiveUsers (unique)
```

### Mistake 3: Poor API Descriptions

```python
# ❌ WRONG - No docstrings or generic descriptions
class ProductView(APIView):
    def get(self, request, pk):
        pass  # No description generated

    def post(self, request):
        pass  # No description generated
```

**Solution:** Add detailed docstrings

```python
# ✅ CORRECT - Rich docstrings for better docs
class ProductView(APIView):
    """
    Manage individual products.

    Provides endpoints for retrieving and creating products.
    """

    def get(self, request, pk):
        """
        Retrieve a product.

        Returns detailed information about a specific product
        including pricing, inventory, and specifications.
        """
        pass

    def post(self, request):
        """
        Create a new product.

        Creates a new product with the provided details.
        Requires admin permissions.
        """
        pass
```

### Mistake 4: Custom Fields Without Schema Support

```python
# ❌ WRONG - Custom field with no schema mapping
class ColorField(serializers.Field):
    def to_representation(self, value):
        return value.hex_code

    def to_internal_value(self, data):
        return Color.objects.get(hex_code=data)

class ProductSerializer(serializers.Serializer):
    color = ColorField()  # No schema generated for this field
```

**Solution:** Extend AutoSchema to map custom fields

```python
# ✅ CORRECT - Add schema mapping for custom fields
from rest_framework.schemas.openapi import AutoSchema

class CustomFieldAutoSchema(AutoSchema):
    def map_field(self, field):
        if isinstance(field, ColorField):
            return {
                'type': 'string',
                'format': 'hex-color',
                'pattern': '^#[0-9A-Fa-f]{6}$',
                'example': '#FF5733'
            }
        return super().map_field(field)

class ProductView(APIView):
    schema = CustomFieldAutoSchema()
    serializer_class = ProductSerializer
```

### Mistake 5: Not Handling Permissions in Schema

```python
# ❌ WRONG - Exposing internal endpoints in public schema
schema_view = get_schema_view(
    title='Public API',
    public=True,  # Shows ALL endpoints, even admin-only
)
```

**Solution:** Use permissions and public parameter correctly

```python
# ✅ CORRECT - Respect view permissions
from rest_framework.permissions import AllowAny

schema_view = get_schema_view(
    title='Public API',
    public=False,  # Respect view permissions
    permission_classes=[AllowAny],  # Schema itself is public
)

# Or generate separate schemas
public_schema = get_schema_view(
    title='Public API',
    patterns=[path('api/public/', include('public.urls'))],
)

admin_schema = get_schema_view(
    title='Admin API',
    patterns=[path('api/admin/', include('admin.urls'))],
)
```

### Mistake 6: Forgetting Request/Response Differentiation

```python
# ❌ WRONG - Same serializer for read/write with read-only fields
class UserSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True)
    last_login = serializers.DateTimeField(read_only=True)

    class Meta:
        model = User
        fields = ['id', 'username', 'password', 'last_login']

# Schema doesn't clearly differentiate request vs response
```

**Solution:** Use separate serializers or override AutoSchema methods

```python
# ✅ CORRECT - Clear request/response serializers
class UserInputSerializer(serializers.Serializer):
    username = serializers.CharField()
    password = serializers.CharField()

class UserOutputSerializer(serializers.Serializer):
    id = serializers.IntegerField()
    username = serializers.CharField()
    last_login = serializers.DateTimeField()

class CustomAutoSchema(AutoSchema):
    def get_request_serializer(self, path, method):
        if method in ('POST', 'PUT', 'PATCH'):
            return self.view.input_serializer_class()
        return self.get_serializer(path, method)

    def get_response_serializer(self, path, method):
        return self.view.output_serializer_class()

class UserView(APIView):
    schema = CustomAutoSchema()
    input_serializer_class = UserInputSerializer
    output_serializer_class = UserOutputSerializer
```

## Reference Documentation

For detailed information on specific topics:

- **[OpenAPI Generation](reference/openapi-generation.md)** - Built-in schema generation, SchemaGenerator, generateschema command
- **[Schema Customization](reference/schema-customization.md)** - AutoSchema subclassing, custom fields, operation IDs
- **[drf-spectacular Integration](reference/drf-spectacular.md)** - Advanced schema generation with drf-spectacular (recommended)
- **[Swagger UI & ReDoc](reference/swagger-redoc.md)** - Setting up interactive documentation interfaces
- **[Code Examples](reference/examples/documentation-patterns.py)** - Complete working examples

## Key Source Files

Understanding these core files will help you customize schema generation:

- `/rest_framework/schemas/__init__.py` - Public API: get_schema_view(), AutoSchema, SchemaGenerator
- `/rest_framework/schemas/openapi.py` - OpenAPI 3.0 schema generation, AutoSchema implementation
- `/rest_framework/schemas/generators.py` - SchemaGenerator, EndpointEnumerator, URL pattern inspection
- `/rest_framework/schemas/inspectors.py` - ViewInspector base class for schema introspection
- `/rest_framework/schemas/views.py` - SchemaView for serving schemas dynamically

## Best Practices

1. **Use drf-spectacular for production** - It provides better schema quality and more features
2. **Add docstrings to all views and methods** - They become your API documentation
3. **Specify explicit tags and operation IDs** - Makes documentation more organized
4. **Test your schema regularly** - Validate with OpenAPI validators
5. **Version your schema** - Track changes with semantic versioning
6. **Customize schemas at the right level** - Use AutoSchema for view-level, SchemaGenerator for API-level
7. **Document query parameters and filters** - Ensure filter backends provide schema support
8. **Handle custom fields properly** - Always extend AutoSchema.map_field() for custom fields
9. **Separate public and internal schemas** - Use different schema endpoints for different audiences
10. **Keep schemas in version control** - Commit generated schemas for change tracking

## Testing Your Schema

```bash
# Generate and validate your schema
python manage.py generateschema --file schema.yml

# Validate with OpenAPI tools
pip install openapi-spec-validator
openapi-spec-validator schema.yml

# Test Swagger UI
# Visit: http://localhost:8000/api/schema/swagger-ui/

# Test ReDoc
# Visit: http://localhost:8000/api/schema/redoc/
```

## Next Steps

After mastering schema generation:

1. Set up **client SDK generation** using your schema
2. Implement **contract testing** with your OpenAPI schema
3. Configure **API versioning** with multiple schemas
4. Add **authentication flows** to your schema
5. Set up **automated schema validation** in CI/CD
