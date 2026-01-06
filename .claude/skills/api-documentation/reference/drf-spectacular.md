# drf-spectacular Quick Reference

Essential decorator options and settings for drf-spectacular.

## @extend_schema Decorator

```python
from drf_spectacular.utils import extend_schema, OpenApiParameter, OpenApiExample
from drf_spectacular.types import OpenApiTypes

@extend_schema(
    # Basic metadata
    summary='Short description',
    description='Detailed multi-line description',
    tags=['Products'],

    # Request/response
    request=InputSerializer,
    responses={
        200: OutputSerializer,
        404: ErrorSerializer,
    },

    # Query parameters
    parameters=[
        OpenApiParameter(
            name='category',
            type=OpenApiTypes.STR,
            location=OpenApiParameter.QUERY,
            description='Filter by category',
            enum=['electronics', 'books'],
        ),
    ],

    # Examples
    examples=[
        OpenApiExample(
            'Example name',
            value={'field': 'value'},
        ),
    ],

    # Exclude from schema
    exclude=False,
)
```

## Common SPECTACULAR_SETTINGS

```python
SPECTACULAR_SETTINGS = {
    'TITLE': 'My API',
    'DESCRIPTION': 'API Description',
    'VERSION': '1.0.0',
    'SERVE_INCLUDE_SCHEMA': False,
    'COMPONENT_SPLIT_REQUEST': False,
}
```

## More Information

See [official drf-spectacular documentation](https://drf-spectacular.readthedocs.io/) for advanced features like polymorphism, authentication schemes, and custom hooks.
