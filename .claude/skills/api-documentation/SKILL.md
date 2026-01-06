---
skill: api-documentation
description: Master Django REST Framework's API documentation and schema generation - built-in OpenAPI, AutoSchema, drf-spectacular, Swagger UI, and ReDoc
dependencies:
  - drf_spectacular
tags:
  - openapi
  - documentation
  - drf-spectacular
related_skills:
  - viewsets
  - serializers
version: 1.0.0
---

# API Documentation with drf-spectacular

Generate interactive API documentation in 2 minutes. Just use drf-spectacular.

## Quick Start

### 1. Install

```bash
pip install drf-spectacular
```

### 2. Configure Settings

```python
# settings.py
INSTALLED_APPS = [
    'rest_framework',
    'drf_spectacular',
    # ...
]

REST_FRAMEWORK = {
    'DEFAULT_SCHEMA_CLASS': 'drf_spectacular.openapi.AutoSchema',
}

SPECTACULAR_SETTINGS = {
    'TITLE': 'My API',
    'DESCRIPTION': 'API Documentation',
    'VERSION': '1.0.0',
    'SERVE_INCLUDE_SCHEMA': False,
}
```

### 3. Add URLs

```python
# urls.py
from drf_spectacular.views import (
    SpectacularAPIView,
    SpectacularSwaggerView,
    SpectacularRedocView,
)

urlpatterns = [
    path('api/', include('myapp.urls')),

    # Schema + UI endpoints
    path('api/schema/', SpectacularAPIView.as_view(), name='schema'),
    path('api/docs/', SpectacularSwaggerView.as_view(url_name='schema'), name='swagger-ui'),
    path('api/redoc/', SpectacularRedocView.as_view(url_name='schema'), name='redoc'),
]
```

### 4. Done!

Visit http://localhost:8000/api/docs/ for interactive documentation.

## Customizing Descriptions

Use `@extend_schema` to add summaries and customize endpoints:

```python
from drf_spectacular.utils import extend_schema
from rest_framework.views import APIView
from rest_framework.response import Response

class ProductListView(APIView):
    @extend_schema(
        summary='List all products',
        description='Returns a paginated list of products. Supports filtering by category.',
        tags=['Products'],
    )
    def get(self, request):
        return Response([])

    @extend_schema(
        summary='Create a product',
        request=ProductSerializer,
        responses={201: ProductSerializer},
        tags=['Products'],
    )
    def post(self, request):
        return Response({}, status=201)
```

## Common Issues

**Missing schema endpoint?**
- Add `drf_spectacular` to `INSTALLED_APPS`
- Set `DEFAULT_SCHEMA_CLASS` in `REST_FRAMEWORK` settings

**Schema empty?**
- Ensure views have proper serializers
- Check that URLs are included in urlpatterns

**Need custom parameters?**
- Use `@extend_schema(parameters=[...])` decorator
- See [reference/drf-spectacular.md](reference/drf-spectacular.md) for examples

## Reference

- [drf-spectacular Details](reference/drf-spectacular.md) - Extended decorator options
- [Official docs](https://drf-spectacular.readthedocs.io/) - Complete drf-spectacular documentation
