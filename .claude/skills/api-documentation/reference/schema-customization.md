# Schema Customization

Customize how your DRF API is represented in OpenAPI schemas using AutoSchema subclasses, custom field mappings, operation IDs, and per-view schema configuration.

## AutoSchema Overview

AutoSchema is a descriptor class that handles per-view schema introspection. Every APIView has a `schema` attribute that is an AutoSchema instance by default.

```python
from rest_framework.views import APIView
from rest_framework.schemas.openapi import AutoSchema

class MyView(APIView):
    schema = AutoSchema()  # Default schema introspection

    def get(self, request):
        """Get method description."""
        return Response({})
```

## AutoSchema Initialization Parameters

AutoSchema accepts several `__init__()` kwargs for common customizations:

```python
from rest_framework.schemas.openapi import AutoSchema

class ProductView(APIView):
    schema = AutoSchema(
        tags=['Products', 'E-commerce'],  # Custom tags
        operation_id_base='Product',       # Base for operationId
        component_name='ProductSchema',    # Component name in schema
    )
```

### tags Parameter

Controls how operations are grouped in documentation:

```python
# Single tag
class ProductListView(APIView):
    schema = AutoSchema(tags=['Products'])

# Multiple tags
class FeaturedProductView(APIView):
    schema = AutoSchema(tags=['Products', 'Featured', 'Marketing'])

# Default behavior (without tags parameter):
# Tags are derived from first URL segment
# /api/products/ -> tag: 'products'
# /api/users/{id}/ -> tag: 'users'
```

### operation_id_base Parameter

Sets the base name for operation IDs:

```python
# Without operation_id_base (auto-detected from model/serializer/view)
class ProductListView(ListAPIView):
    queryset = Product.objects.all()
    serializer_class = ProductSerializer
    # operationId: listProducts (from Product model)

# With explicit operation_id_base
class ActiveProductListView(ListAPIView):
    schema = AutoSchema(operation_id_base='ActiveProduct')
    queryset = Product.objects.filter(is_active=True)
    serializer_class = ProductSerializer
    # operationId: listActiveProducts (explicit)

# Operation ID format: {action}{OperationIdBase}
# Actions: list, retrieve, create, update, partialUpdate, destroy
```

### component_name Parameter

Sets the schema component name:

```python
# Default: derived from serializer class name
class ProductSerializer(serializers.Serializer):
    name = serializers.CharField()
    # Component name: 'Product' (removes 'Serializer' suffix)

# Custom component name
class ProductView(APIView):
    schema = AutoSchema(component_name='ProductDetail')
    serializer_class = ProductSerializer
    # Component name: 'ProductDetail'
```

## Subclassing AutoSchema

Create custom AutoSchema subclasses to modify schema generation behavior:

### Basic Custom AutoSchema

```python
from rest_framework.schemas.openapi import AutoSchema

class CustomAutoSchema(AutoSchema):
    """Add custom metadata to all operations."""

    def get_operation(self, path, method):
        operation = super().get_operation(path, method)

        # Add custom extensions (x- prefix)
        operation['x-custom-field'] = 'custom-value'
        operation['x-rate-limit'] = '100/hour'

        return operation

class ProductView(APIView):
    schema = CustomAutoSchema()
```

### Adding Security Requirements

```python
class AuthenticatedAutoSchema(AutoSchema):
    """Add authentication requirements to operations."""

    def get_operation(self, path, method):
        operation = super().get_operation(path, method)

        # Add security requirements
        if method in ('POST', 'PUT', 'PATCH', 'DELETE'):
            operation['security'] = [
                {'BearerAuth': []},
                {'ApiKeyAuth': []},
            ]

        return operation
```

### Custom Operation Descriptions

```python
class DescriptiveAutoSchema(AutoSchema):
    """Enhance operation descriptions."""

    def get_description(self, path, method):
        description = super().get_description(path, method)

        # Add common warnings or notes
        if method == 'DELETE':
            description += '\n\n**Warning:** This action cannot be undone.'

        if method == 'POST':
            description += '\n\n**Note:** Rate limiting applies (100 requests/hour).'

        return description
```

## Customizing Field Mappings

Override `map_field()` to handle custom field types:

### Basic Field Mapping

```python
from rest_framework.schemas.openapi import AutoSchema
from myapp.fields import ColorField, GeoPointField

class CustomFieldAutoSchema(AutoSchema):
    """Add support for custom field types."""

    def map_field(self, field):
        # Handle ColorField
        if isinstance(field, ColorField):
            return {
                'type': 'string',
                'format': 'hex-color',
                'pattern': '^#[0-9A-Fa-f]{6}$',
                'example': '#FF5733'
            }

        # Handle GeoPointField
        if isinstance(field, GeoPointField):
            return {
                'type': 'object',
                'properties': {
                    'latitude': {'type': 'number', 'format': 'double'},
                    'longitude': {'type': 'number', 'format': 'double'}
                },
                'required': ['latitude', 'longitude']
            }

        # Handle SerializerMethodField
        if isinstance(field, serializers.SerializerMethodField):
            # Try to infer type from method return annotation
            method_name = field.method_name or f'get_{field.field_name}'
            method = getattr(self.view.get_serializer().__class__, method_name, None)

            if method and hasattr(method, '__annotations__'):
                return_type = method.__annotations__.get('return')
                if return_type == str:
                    return {'type': 'string'}
                elif return_type == int:
                    return {'type': 'integer'}

            # Default for unknown SerializerMethodField
            return {'type': 'string', 'readOnly': True}

        # Fall back to default handling
        return super().map_field(field)
```

### Adding Examples to Fields

```python
class ExampleAutoSchema(AutoSchema):
    """Add examples to field schemas."""

    def map_field(self, field):
        schema = super().map_field(field)

        # Add examples based on field type
        if isinstance(field, serializers.EmailField):
            schema['example'] = 'user@example.com'
        elif isinstance(field, serializers.URLField):
            schema['example'] = 'https://example.com'
        elif isinstance(field, serializers.DateTimeField):
            schema['example'] = '2024-01-15T10:30:00Z'
        elif isinstance(field, serializers.DecimalField):
            schema['example'] = '19.99'

        return schema
```

### Handling Polymorphic Serializers

```python
class PolymorphicAutoSchema(AutoSchema):
    """Handle polymorphic serializers with oneOf."""

    def map_serializer(self, serializer):
        # Check if this is a polymorphic serializer
        if hasattr(serializer, 'get_polymorphic_serializers'):
            # Return oneOf schema
            return {
                'oneOf': [
                    self.map_serializer(child_serializer())
                    for child_serializer in serializer.get_polymorphic_serializers()
                ],
                'discriminator': {
                    'propertyName': 'type',
                    'mapping': serializer.get_discriminator_mapping()
                }
            }

        return super().map_serializer(serializer)
```

## Customizing Operation IDs

Override methods that generate operation IDs:

### Custom Operation ID Logic

```python
class CustomOperationIdSchema(AutoSchema):
    """Generate custom operation IDs."""

    def get_operation_id(self, path, method):
        # Get the default operation ID
        operation_id = super().get_operation_id(path, method)

        # Add API version prefix
        return f'v1_{operation_id}'

    def get_operation_id_base(self, path, method, action):
        # Custom logic for base name
        if hasattr(self.view, 'model_name'):
            return self.view.model_name

        return super().get_operation_id_base(path, method, action)
```

### Preventing Duplicate Operation IDs

```python
class UniqueOperationIdSchema(AutoSchema):
    """Ensure unique operation IDs by including path info."""

    def get_operation_id(self, path, method):
        operation_id = super().get_operation_id(path, method)

        # Add path hash to make unique
        path_segments = [seg for seg in path.split('/') if seg and '{' not in seg]
        if len(path_segments) > 1:
            # Include parent resource in operation ID
            operation_id = f'{path_segments[-2]}_{operation_id}'

        return operation_id
```

## Customizing Tags

Override `get_tags()` to control operation grouping:

```python
class CustomTagsSchema(AutoSchema):
    """Generate context-aware tags."""

    def get_tags(self, path, method):
        tags = []

        # Add resource tag
        if hasattr(self.view, 'queryset'):
            model_name = self.view.queryset.model.__name__
            tags.append(model_name)

        # Add method-specific tags
        if method in ('POST', 'PUT', 'PATCH'):
            tags.append('Write Operations')
        else:
            tags.append('Read Operations')

        # Add permission-based tags
        if hasattr(self.view, 'permission_classes'):
            for perm_class in self.view.permission_classes:
                if perm_class.__name__ == 'IsAdminUser':
                    tags.append('Admin Only')

        return tags
```

## Request/Response Customization

Differentiate between request and response schemas:

### Separate Request/Response Serializers

```python
class DualSerializerAutoSchema(AutoSchema):
    """Use different serializers for request and response."""

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

# Usage
class UserCreateView(APIView):
    schema = DualSerializerAutoSchema()
    input_serializer_class = UserInputSerializer
    output_serializer_class = UserOutputSerializer

    def post(self, request):
        input_serializer = self.input_serializer_class(data=request.data)
        input_serializer.is_valid(raise_exception=True)
        user = input_serializer.save()
        output_serializer = self.output_serializer_class(user)
        return Response(output_serializer.data)
```

### Custom Response Codes

```python
class CustomResponseSchema(AutoSchema):
    """Add custom response codes and descriptions."""

    def get_responses(self, path, method):
        responses = super().get_responses(path, method)

        # Add error responses
        responses['400'] = {
            'description': 'Bad Request - Invalid input data',
            'content': {
                'application/json': {
                    'schema': {
                        'type': 'object',
                        'properties': {
                            'error': {'type': 'string'},
                            'details': {'type': 'object'}
                        }
                    }
                }
            }
        }

        responses['401'] = {
            'description': 'Unauthorized - Authentication required'
        }

        if method in ('POST', 'PUT', 'PATCH', 'DELETE'):
            responses['403'] = {
                'description': 'Forbidden - Insufficient permissions'
            }

        responses['500'] = {
            'description': 'Internal Server Error'
        }

        return responses
```

## Pagination Schema Customization

Handle custom pagination schemes:

```python
class CustomPaginationSchema(AutoSchema):
    """Support for custom pagination."""

    def get_responses(self, path, method):
        responses = super().get_responses(path, method)

        # Customize pagination response for list views
        if method == 'GET' and self.is_list_view(path, method):
            responses['200']['content']['application/json']['schema'] = {
                'type': 'object',
                'properties': {
                    'count': {'type': 'integer'},
                    'next': {'type': 'string', 'nullable': True, 'format': 'uri'},
                    'previous': {'type': 'string', 'nullable': True, 'format': 'uri'},
                    'results': responses['200']['content']['application/json']['schema']
                }
            }

        return responses

    def is_list_view(self, path, method):
        """Check if this is a list view."""
        from rest_framework.schemas.utils import is_list_view
        return is_list_view(path, method, self.view)
```

## Filter Backend Integration

Ensure filter backends provide schema parameters:

```python
from rest_framework.filters import BaseFilterBackend

class CustomFilterBackend(BaseFilterBackend):
    """Custom filter with schema support."""

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
                'description': 'Filter by product category',
                'required': False,
                'schema': {
                    'type': 'string',
                    'enum': ['electronics', 'clothing', 'books']
                }
            }
        ]
```

## Using DEFAULT_SCHEMA_CLASS

Set a project-wide default AutoSchema:

```python
# settings.py
REST_FRAMEWORK = {
    'DEFAULT_SCHEMA_CLASS': 'myapp.schema.CustomAutoSchema',
}

# myapp/schema.py
from rest_framework.schemas.openapi import AutoSchema

class CustomAutoSchema(AutoSchema):
    """Project-wide schema customizations."""

    def get_operation(self, path, method):
        operation = super().get_operation(path, method)
        operation['x-api-version'] = 'v1'
        return operation

# All views now use CustomAutoSchema by default
class ProductView(APIView):
    # schema = CustomAutoSchema() is implicit
    pass

# Override for specific views
class SpecialView(APIView):
    schema = SpecialAutoSchema()  # Use different schema
    pass
```

## Per-Method Docstrings

Use docstring sections for method-specific documentation:

```python
class ProductViewSet(viewsets.ModelViewSet):
    """
    Product management endpoints.

    This viewset provides CRUD operations for products.

    list:
    Return a list of all products in the system.
    Supports filtering by category, price range, and availability.

    retrieve:
    Return detailed information about a specific product.
    Includes related items and customer reviews.

    create:
    Create a new product.
    Requires admin permissions. Product will be marked as draft initially.

    update:
    Update an existing product.
    All fields are optional. Partial updates are supported via PATCH.

    destroy:
    Delete a product.
    This is a soft delete - the product is marked as inactive but not removed.
    """
    queryset = Product.objects.all()
    serializer_class = ProductSerializer
```

## Complete Custom AutoSchema Example

```python
from rest_framework.schemas.openapi import AutoSchema
from rest_framework import serializers
from myapp.fields import CustomField

class ProjectAutoSchema(AutoSchema):
    """
    Comprehensive custom AutoSchema for the project.

    Features:
    - Custom field mapping
    - Enhanced descriptions
    - Security annotations
    - Error response schemas
    - Custom tags
    """

    def get_operation(self, path, method):
        operation = super().get_operation(path, method)

        # Add security requirements
        if method in ('POST', 'PUT', 'PATCH', 'DELETE'):
            operation['security'] = [{'BearerAuth': []}]

        # Add rate limiting info
        operation['x-rate-limit'] = self.get_rate_limit(method)

        return operation

    def get_rate_limit(self, method):
        """Get rate limit based on method."""
        limits = {
            'GET': '1000/hour',
            'POST': '100/hour',
            'PUT': '100/hour',
            'PATCH': '100/hour',
            'DELETE': '50/hour',
        }
        return limits.get(method, '100/hour')

    def get_responses(self, path, method):
        responses = super().get_responses(path, method)

        # Add common error responses
        error_responses = {
            '400': {
                'description': 'Bad Request',
                'content': {
                    'application/json': {
                        'schema': {'$ref': '#/components/schemas/Error'}
                    }
                }
            },
            '401': {'description': 'Unauthorized'},
            '403': {'description': 'Forbidden'},
            '404': {'description': 'Not Found'},
            '500': {'description': 'Internal Server Error'},
        }

        # Add error responses based on method
        if method in ('GET', 'PUT', 'PATCH', 'DELETE'):
            responses['404'] = error_responses['404']

        if method in ('POST', 'PUT', 'PATCH'):
            responses['400'] = error_responses['400']

        responses['401'] = error_responses['401']
        responses['500'] = error_responses['500']

        return responses

    def get_tags(self, path, method):
        """Generate smart tags."""
        tags = []

        # Add model-based tag
        if hasattr(self.view, 'queryset'):
            model_name = self.view.queryset.model._meta.verbose_name_plural.title()
            tags.append(model_name)

        # Add operation type tag
        if method == 'GET':
            tags.append('Queries')
        elif method in ('POST', 'PUT', 'PATCH', 'DELETE'):
            tags.append('Mutations')

        return tags or super().get_tags(path, method)

    def map_field(self, field):
        """Handle custom fields."""
        if isinstance(field, CustomField):
            return {
                'type': 'string',
                'format': 'custom',
                'description': field.help_text or '',
            }

        schema = super().map_field(field)

        # Add examples
        if isinstance(field, serializers.EmailField):
            schema['example'] = 'user@example.com'
        elif isinstance(field, serializers.CharField) and field.max_length:
            schema['example'] = 'Sample text'

        return schema

    def get_description(self, path, method):
        description = super().get_description(path, method)

        # Add authentication note if required
        if hasattr(self.view, 'permission_classes'):
            for perm in self.view.permission_classes:
                if perm.__name__ != 'AllowAny':
                    description += '\n\n**Authentication Required**'
                    break

        return description
```

## Best Practices

1. **Keep customizations in AutoSchema** - Don't leak schema logic into views/serializers
2. **Use __init__ kwargs for simple cases** - Subclass only when needed
3. **Set DEFAULT_SCHEMA_CLASS** - Apply project-wide customizations
4. **Document with docstrings** - They become your API documentation
5. **Handle custom fields properly** - Override map_field() for custom field types
6. **Test schema generation** - Validate generated schemas regularly
7. **Use descriptive operation IDs** - Makes generated clients more usable
8. **Group with meaningful tags** - Organize documentation logically
9. **Add response codes** - Document all possible responses
10. **Include examples** - Help API consumers understand data formats

## Related Documentation

- [OpenAPI Generation](openapi-generation.md) - Schema generation basics
- [drf-spectacular](drf-spectacular.md) - Advanced alternative (recommended)
- [Code Examples](examples/documentation-patterns.py) - Working code examples
