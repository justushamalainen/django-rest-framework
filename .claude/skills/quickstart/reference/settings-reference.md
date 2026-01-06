# Django REST Framework Settings Reference

Complete reference for all Django REST Framework settings, organized by importance tier and category.

## Table of Contents

1. [Settings Tiers](#settings-tiers)
2. [Authentication Settings](#authentication-settings)
3. [Permission Settings](#permission-settings)
4. [Pagination Settings](#pagination-settings)
5. [Filtering Settings](#filtering-settings)
6. [Throttling Settings](#throttling-settings)
7. [Rendering Settings](#rendering-settings)
8. [Parsing Settings](#parsing-settings)
9. [Schema Settings](#schema-settings)
10. [Versioning Settings](#versioning-settings)
11. [Exception Handling](#exception-handling)
12. [Content Negotiation](#content-negotiation)
13. [Metadata Settings](#metadata-settings)
14. [Format Settings](#format-settings)
15. [View Settings](#view-settings)

---

## Settings Tiers

### TIER 1: Essential (Required for Production)

Must be explicitly configured for any production API:

```python
REST_FRAMEWORK = {
    'DEFAULT_AUTHENTICATION_CLASSES': [...],
    'DEFAULT_PERMISSION_CLASSES': [...],
    'DEFAULT_PAGINATION_CLASS': '...',
    'PAGE_SIZE': 20,
}
```

### TIER 2: Recommended (Should Configure)

Highly recommended for better performance, UX, and security:

```python
REST_FRAMEWORK = {
    'DEFAULT_THROTTLE_CLASSES': [...],
    'DEFAULT_THROTTLE_RATES': {...},
    'DEFAULT_FILTER_BACKENDS': [...],
    'DEFAULT_RENDERER_CLASSES': [...],
}
```

### TIER 3: Optional (Nice to Have)

For specific use cases and advanced features:

```python
REST_FRAMEWORK = {
    'DEFAULT_VERSIONING_CLASS': '...',
    'DEFAULT_SCHEMA_CLASS': '...',
    'EXCEPTION_HANDLER': '...',
    'NON_FIELD_ERRORS_KEY': '...',
}
```

---

## Authentication Settings

### DEFAULT_AUTHENTICATION_CLASSES (TIER 1)

**Description:** Classes used for authenticating requests.

**Default:**
```python
[
    'rest_framework.authentication.SessionAuthentication',
    'rest_framework.authentication.BasicAuthentication'
]
```

**Recommended Production:**
```python
'DEFAULT_AUTHENTICATION_CLASSES': [
    'rest_framework.authentication.TokenAuthentication',
    'rest_framework.authentication.SessionAuthentication',
]
```

**Options:**

1. **SessionAuthentication**
   - Browser-based authentication
   - Uses Django's session framework
   - Requires CSRF protection
   ```python
   'rest_framework.authentication.SessionAuthentication'
   ```

2. **BasicAuthentication**
   - Simple username/password
   - Sends credentials with each request
   - Only use over HTTPS
   ```python
   'rest_framework.authentication.BasicAuthentication'
   ```

3. **TokenAuthentication**
   - Token-based auth
   - Requires `rest_framework.authtoken` in INSTALLED_APPS
   - Good for mobile/SPA apps
   ```python
   'rest_framework.authentication.TokenAuthentication'
   ```

4. **JWTAuthentication (Third-party)**
   - JSON Web Tokens
   - Requires `djangorestframework-simplejwt`
   - Stateless authentication
   ```python
   'rest_framework_simplejwt.authentication.JWTAuthentication'
   ```

**Example:**
```python
REST_FRAMEWORK = {
    'DEFAULT_AUTHENTICATION_CLASSES': [
        'rest_framework.authentication.TokenAuthentication',
    ],
}

# Also add to INSTALLED_APPS:
INSTALLED_APPS = [
    # ...
    'rest_framework.authtoken',
]
```

### UNAUTHENTICATED_USER (TIER 3)

**Description:** User instance for unauthenticated requests.

**Default:** `django.contrib.auth.models.AnonymousUser`

**Usage:**
```python
'UNAUTHENTICATED_USER': 'django.contrib.auth.models.AnonymousUser'

# To disable:
'UNAUTHENTICATED_USER': None
```

### UNAUTHENTICATED_TOKEN (TIER 3)

**Description:** Token for unauthenticated requests.

**Default:** `None`

---

## Permission Settings

### DEFAULT_PERMISSION_CLASSES (TIER 1)

**Description:** Default permissions for views.

**Default:**
```python
['rest_framework.permissions.AllowAny']
```

**Recommended Production:**
```python
'DEFAULT_PERMISSION_CLASSES': [
    'rest_framework.permissions.IsAuthenticated',
]
```

**Built-in Options:**

1. **AllowAny** (Not recommended for production)
   - No restrictions
   ```python
   'rest_framework.permissions.AllowAny'
   ```

2. **IsAuthenticated** (Recommended)
   - Requires authentication
   ```python
   'rest_framework.permissions.IsAuthenticated'
   ```

3. **IsAdminUser**
   - Only admin users
   ```python
   'rest_framework.permissions.IsAdminUser'
   ```

4. **IsAuthenticatedOrReadOnly**
   - Authenticated for write, anyone for read
   ```python
   'rest_framework.permissions.IsAuthenticatedOrReadOnly'
   ```

5. **DjangoModelPermissions**
   - Based on Django's model permissions
   ```python
   'rest_framework.permissions.DjangoModelPermissions'
   ```

6. **DjangoObjectPermissions**
   - Object-level permissions
   - Requires third-party package like `django-guardian`
   ```python
   'rest_framework.permissions.DjangoObjectPermissions'
   ```

**Example:**
```python
REST_FRAMEWORK = {
    'DEFAULT_PERMISSION_CLASSES': [
        'rest_framework.permissions.IsAuthenticatedOrReadOnly',
    ],
}
```

---

## Pagination Settings

### DEFAULT_PAGINATION_CLASS (TIER 1)

**Description:** Default pagination style.

**Default:** `None` (no pagination)

**Recommended:**
```python
'DEFAULT_PAGINATION_CLASS': 'rest_framework.pagination.PageNumberPagination'
```

**Options:**

1. **PageNumberPagination** (Most common)
   - Standard page numbers: `?page=2`
   ```python
   'rest_framework.pagination.PageNumberPagination'
   ```

2. **LimitOffsetPagination**
   - SQL-style: `?limit=10&offset=20`
   ```python
   'rest_framework.pagination.LimitOffsetPagination'
   ```

3. **CursorPagination** (Best for large datasets)
   - Opaque cursor: `?cursor=cD0yMDIw...`
   - No random page access
   - Most efficient
   ```python
   'rest_framework.pagination.CursorPagination'
   ```

### PAGE_SIZE (TIER 1)

**Description:** Default page size.

**Default:** `None`

**Recommended:** `10-50` depending on data size

**Example:**
```python
REST_FRAMEWORK = {
    'DEFAULT_PAGINATION_CLASS': 'rest_framework.pagination.PageNumberPagination',
    'PAGE_SIZE': 20,
}
```

---

## Filtering Settings

### DEFAULT_FILTER_BACKENDS (TIER 2)

**Description:** Default filter classes for querysets.

**Default:** `[]`

**Recommended:**
```python
'DEFAULT_FILTER_BACKENDS': [
    'rest_framework.filters.SearchFilter',
    'rest_framework.filters.OrderingFilter',
]
```

**Built-in Options:**

1. **SearchFilter**
   - Full-text search: `?search=query`
   ```python
   'rest_framework.filters.SearchFilter'
   ```

2. **OrderingFilter**
   - Sort results: `?ordering=created_at`
   ```python
   'rest_framework.filters.OrderingFilter'
   ```

3. **DjangoFilterBackend** (Third-party)
   - Complex filtering
   - Requires `django-filter` package
   ```python
   'django_filters.rest_framework.DjangoFilterBackend'
   ```

**Example:**
```python
REST_FRAMEWORK = {
    'DEFAULT_FILTER_BACKENDS': [
        'django_filters.rest_framework.DjangoFilterBackend',
        'rest_framework.filters.SearchFilter',
        'rest_framework.filters.OrderingFilter',
    ],
}

INSTALLED_APPS = [
    # ...
    'django_filters',
]
```

### SEARCH_PARAM (TIER 3)

**Description:** Query parameter name for search.

**Default:** `'search'`

**Example:**
```python
'SEARCH_PARAM': 'q'  # Now use ?q=query
```

### ORDERING_PARAM (TIER 3)

**Description:** Query parameter name for ordering.

**Default:** `'ordering'`

**Example:**
```python
'ORDERING_PARAM': 'sort'  # Now use ?sort=created_at
```

---

## Throttling Settings

### DEFAULT_THROTTLE_CLASSES (TIER 2)

**Description:** Classes for rate limiting.

**Default:** `[]`

**Recommended:**
```python
'DEFAULT_THROTTLE_CLASSES': [
    'rest_framework.throttling.AnonRateThrottle',
    'rest_framework.throttling.UserRateThrottle',
]
```

**Options:**

1. **AnonRateThrottle**
   - Rate limit for anonymous users
   ```python
   'rest_framework.throttling.AnonRateThrottle'
   ```

2. **UserRateThrottle**
   - Rate limit for authenticated users
   ```python
   'rest_framework.throttling.UserRateThrottle'
   ```

3. **ScopedRateThrottle**
   - Per-view rate limiting
   ```python
   'rest_framework.throttling.ScopedRateThrottle'
   ```

### DEFAULT_THROTTLE_RATES (TIER 2)

**Description:** Default throttle rates.

**Default:** `{}`

**Recommended:**
```python
'DEFAULT_THROTTLE_RATES': {
    'anon': '100/day',
    'user': '1000/day',
}
```

**Format:** `{count}/{period}`
- Periods: `second`, `minute`, `hour`, `day`

**Example:**
```python
REST_FRAMEWORK = {
    'DEFAULT_THROTTLE_CLASSES': [
        'rest_framework.throttling.AnonRateThrottle',
        'rest_framework.throttling.UserRateThrottle',
    ],
    'DEFAULT_THROTTLE_RATES': {
        'anon': '100/hour',
        'user': '1000/hour',
        'burst': '60/minute',  # For ScopedRateThrottle
    },
}
```

---

## Rendering Settings

### DEFAULT_RENDERER_CLASSES (TIER 2)

**Description:** Default response renderers.

**Default:**
```python
[
    'rest_framework.renderers.JSONRenderer',
    'rest_framework.renderers.BrowsableAPIRenderer',
]
```

**Production (disable browsable API):**
```python
'DEFAULT_RENDERER_CLASSES': [
    'rest_framework.renderers.JSONRenderer',
]
```

**Options:**

1. **JSONRenderer** (Essential)
   - Renders to JSON
   ```python
   'rest_framework.renderers.JSONRenderer'
   ```

2. **BrowsableAPIRenderer** (Development only)
   - HTML interface
   ```python
   'rest_framework.renderers.BrowsableAPIRenderer'
   ```

3. **TemplateHTMLRenderer**
   - Custom HTML templates
   ```python
   'rest_framework.renderers.TemplateHTMLRenderer'
   ```

4. **StaticHTMLRenderer**
   - Pre-rendered HTML
   ```python
   'rest_framework.renderers.StaticHTMLRenderer'
   ```

5. **XMLRenderer** (Third-party)
   - XML format
   - Requires `djangorestframework-xml`
   ```python
   'rest_framework_xml.renderers.XMLRenderer'
   ```

6. **YAMLRenderer** (Third-party)
   - YAML format
   - Requires `djangorestframework-yaml`
   ```python
   'rest_framework_yaml.renderers.YAMLRenderer'
   ```

---

## Parsing Settings

### DEFAULT_PARSER_CLASSES (TIER 2)

**Description:** Default request parsers.

**Default:**
```python
[
    'rest_framework.parsers.JSONParser',
    'rest_framework.parsers.FormParser',
    'rest_framework.parsers.MultiPartParser',
]
```

**Options:**

1. **JSONParser**
   - Parse JSON content
   ```python
   'rest_framework.parsers.JSONParser'
   ```

2. **FormParser**
   - Parse HTML form data
   ```python
   'rest_framework.parsers.FormParser'
   ```

3. **MultiPartParser**
   - Parse file uploads
   ```python
   'rest_framework.parsers.MultiPartParser'
   ```

4. **FileUploadParser**
   - Raw file upload
   ```python
   'rest_framework.parsers.FileUploadParser'
   ```

---

## Schema Settings

### DEFAULT_SCHEMA_CLASS (TIER 3)

**Description:** Schema generation class.

**Default:** `'rest_framework.schemas.openapi.AutoSchema'`

**Options:**

1. **AutoSchema** (OpenAPI 3)
   ```python
   'rest_framework.schemas.openapi.AutoSchema'
   ```

2. **CoreAPI Schema** (Legacy)
   ```python
   'rest_framework.schemas.coreapi.AutoSchema'
   ```

**Example:**
```python
REST_FRAMEWORK = {
    'DEFAULT_SCHEMA_CLASS': 'rest_framework.schemas.openapi.AutoSchema',
}
```

---

## Versioning Settings

### DEFAULT_VERSIONING_CLASS (TIER 3)

**Description:** API versioning strategy.

**Default:** `None`

**Options:**

1. **URLPathVersioning**
   - Version in URL path: `/api/v1/users/`
   ```python
   'rest_framework.versioning.URLPathVersioning'
   ```

2. **NamespaceVersioning**
   - Version via URL namespace
   ```python
   'rest_framework.versioning.NamespaceVersioning'
   ```

3. **HostNameVersioning**
   - Version via subdomain: `v1.api.example.com`
   ```python
   'rest_framework.versioning.HostNameVersioning'
   ```

4. **QueryParameterVersioning**
   - Version in query: `?version=v1`
   ```python
   'rest_framework.versioning.QueryParameterVersioning'
   ```

5. **AcceptHeaderVersioning**
   - Version in Accept header
   ```python
   'rest_framework.versioning.AcceptHeaderVersioning'
   ```

### DEFAULT_VERSION (TIER 3)

**Description:** Default API version.

**Default:** `None`

**Example:**
```python
'DEFAULT_VERSION': 'v1'
```

### ALLOWED_VERSIONS (TIER 3)

**Description:** Valid API versions.

**Default:** `None`

**Example:**
```python
'ALLOWED_VERSIONS': ['v1', 'v2', 'v3']
```

### VERSION_PARAM (TIER 3)

**Description:** Query parameter for versioning.

**Default:** `'version'`

**Example:**
```python
'VERSION_PARAM': 'api-version'
```

---

## Exception Handling

### EXCEPTION_HANDLER (TIER 3)

**Description:** Custom exception handler.

**Default:** `'rest_framework.views.exception_handler'`

**Example Custom Handler:**

```python
# utils.py
from rest_framework.views import exception_handler

def custom_exception_handler(exc, context):
    response = exception_handler(exc, context)

    if response is not None:
        response.data['status_code'] = response.status_code

    return response

# settings.py
REST_FRAMEWORK = {
    'EXCEPTION_HANDLER': 'myapp.utils.custom_exception_handler',
}
```

### NON_FIELD_ERRORS_KEY (TIER 3)

**Description:** Key for non-field validation errors.

**Default:** `'non_field_errors'`

**Example:**
```python
'NON_FIELD_ERRORS_KEY': 'errors'
```

---

## Content Negotiation

### DEFAULT_CONTENT_NEGOTIATION_CLASS (TIER 3)

**Description:** Content negotiation strategy.

**Default:** `'rest_framework.negotiation.DefaultContentNegotiation'`

---

## Metadata Settings

### DEFAULT_METADATA_CLASS (TIER 3)

**Description:** Metadata generation for OPTIONS requests.

**Default:** `'rest_framework.metadata.SimpleMetadata'`

---

## Format Settings

### URL_FORMAT_OVERRIDE (TIER 3)

**Description:** Query parameter for format override.

**Default:** `'format'`

**Example:**
```python
'URL_FORMAT_OVERRIDE': 'format'  # Use ?format=json
```

### FORMAT_SUFFIX_KWARG (TIER 3)

**Description:** Keyword argument for format suffix.

**Default:** `'format'`

---

## View Settings

### VIEW_NAME_FUNCTION (TIER 3)

**Description:** Function to generate view names.

**Default:** `'rest_framework.views.get_view_name'`

### VIEW_DESCRIPTION_FUNCTION (TIER 3)

**Description:** Function to generate view descriptions.

**Default:** `'rest_framework.views.get_view_description'`

---

## Date and Time Settings

### DATE_FORMAT (TIER 3)

**Default:** `None` (ISO 8601)

**Example:**
```python
'DATE_FORMAT': '%Y-%m-%d'
```

### DATE_INPUT_FORMATS (TIER 3)

**Default:** `['iso-8601']`

### DATETIME_FORMAT (TIER 3)

**Default:** `None` (ISO 8601)

**Example:**
```python
'DATETIME_FORMAT': '%Y-%m-%d %H:%M:%S'
```

### DATETIME_INPUT_FORMATS (TIER 3)

**Default:** `['iso-8601']`

### TIME_FORMAT (TIER 3)

**Default:** `None` (ISO 8601)

### TIME_INPUT_FORMATS (TIER 3)

**Default:** `['iso-8601']`

---

## Encoding Settings

### UNICODE_JSON (TIER 3)

**Description:** Use Unicode in JSON responses.

**Default:** `True`

**Example:**
```python
'UNICODE_JSON': True
```

### COMPACT_JSON (TIER 3)

**Description:** Remove whitespace from JSON.

**Default:** `True`

**Example:**
```python
'COMPACT_JSON': False  # Pretty-print JSON
```

### COERCE_DECIMAL_TO_STRING (TIER 3)

**Description:** Convert Decimal to string in JSON.

**Default:** `True`

---

## Complete Example Configuration

```python
REST_FRAMEWORK = {
    # TIER 1: Essential
    'DEFAULT_AUTHENTICATION_CLASSES': [
        'rest_framework.authentication.TokenAuthentication',
        'rest_framework.authentication.SessionAuthentication',
    ],
    'DEFAULT_PERMISSION_CLASSES': [
        'rest_framework.permissions.IsAuthenticated',
    ],
    'DEFAULT_PAGINATION_CLASS': 'rest_framework.pagination.PageNumberPagination',
    'PAGE_SIZE': 20,

    # TIER 2: Recommended
    'DEFAULT_THROTTLE_CLASSES': [
        'rest_framework.throttling.AnonRateThrottle',
        'rest_framework.throttling.UserRateThrottle',
    ],
    'DEFAULT_THROTTLE_RATES': {
        'anon': '100/hour',
        'user': '1000/hour',
    },
    'DEFAULT_FILTER_BACKENDS': [
        'django_filters.rest_framework.DjangoFilterBackend',
        'rest_framework.filters.SearchFilter',
        'rest_framework.filters.OrderingFilter',
    ],
    'DEFAULT_RENDERER_CLASSES': [
        'rest_framework.renderers.JSONRenderer',
    ],

    # TIER 3: Optional
    'DEFAULT_VERSIONING_CLASS': 'rest_framework.versioning.URLPathVersioning',
    'DEFAULT_VERSION': 'v1',
    'ALLOWED_VERSIONS': ['v1', 'v2'],
    'EXCEPTION_HANDLER': 'myapp.utils.custom_exception_handler',
    'DATETIME_FORMAT': '%Y-%m-%d %H:%M:%S',
}
```

---

## Environment-Specific Settings

### Development
```python
REST_FRAMEWORK = {
    # ... base settings ...
    'DEFAULT_RENDERER_CLASSES': [
        'rest_framework.renderers.JSONRenderer',
        'rest_framework.renderers.BrowsableAPIRenderer',  # Enable browsable API
    ],
    'DEFAULT_THROTTLE_CLASSES': [],  # Disable throttling
    'DEFAULT_THROTTLE_RATES': {},
}
```

### Production
```python
REST_FRAMEWORK = {
    # ... base settings ...
    'DEFAULT_RENDERER_CLASSES': [
        'rest_framework.renderers.JSONRenderer',  # JSON only
    ],
    'DEFAULT_THROTTLE_CLASSES': [
        'rest_framework.throttling.AnonRateThrottle',
        'rest_framework.throttling.UserRateThrottle',
    ],
    'DEFAULT_THROTTLE_RATES': {
        'anon': '100/hour',
        'user': '1000/hour',
    },
}
```

---

## Best Practices

1. **Always set authentication and permissions** - Default `AllowAny` is dangerous
2. **Enable pagination** - Protect against large queries
3. **Use throttling in production** - Prevent abuse
4. **Disable browsable API in production** - Security and performance
5. **Use environment-specific settings** - Different configs for dev/prod
6. **Set explicit PAGE_SIZE** - Control response size
7. **Use token auth for APIs** - Better than session auth for clients
8. **Configure CORS properly** - Only allow trusted origins
9. **Add rate limiting** - Protect your API from abuse
10. **Use versioning** - Plan for API evolution

---

## Troubleshooting

### Issue: Settings Not Taking Effect

**Solution:** Ensure settings are in the `REST_FRAMEWORK` dictionary:
```python
# Wrong
DEFAULT_PERMISSION_CLASSES = [...]

# Correct
REST_FRAMEWORK = {
    'DEFAULT_PERMISSION_CLASSES': [...]
}
```

### Issue: Import Errors

**Solution:** Check app is in `INSTALLED_APPS`:
```python
INSTALLED_APPS = [
    'rest_framework',
    'rest_framework.authtoken',  # For token auth
]
```

### Issue: Throttling Not Working

**Solution:** Run migrations for throttling cache:
```bash
python manage.py migrate
```

---

## Resources

- [Official DRF Settings Documentation](https://www.django-rest-framework.org/api-guide/settings/)
- [Authentication Documentation](https://www.django-rest-framework.org/api-guide/authentication/)
- [Permissions Documentation](https://www.django-rest-framework.org/api-guide/permissions/)
- [Pagination Documentation](https://www.django-rest-framework.org/api-guide/pagination/)
