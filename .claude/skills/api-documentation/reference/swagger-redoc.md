# Swagger UI & ReDoc

Interactive API documentation interfaces that render your OpenAPI schema as beautiful, testable documentation. Swagger UI allows live API testing, while ReDoc provides clean, responsive documentation.

## Overview

Both Swagger UI and ReDoc consume your OpenAPI schema to generate interactive documentation:

- **Swagger UI** - Interactive documentation with built-in API testing capabilities
- **ReDoc** - Clean, responsive, three-panel documentation layout

## Quick Setup with drf-spectacular

The easiest way to set up both UIs is with drf-spectacular:

```bash
# Install drf-spectacular with sidecar support
pip install drf-spectacular[sidecar]
```

```python
# settings.py
INSTALLED_APPS = [
    'rest_framework',
    'drf_spectacular',
]

REST_FRAMEWORK = {
    'DEFAULT_SCHEMA_CLASS': 'drf_spectacular.openapi.AutoSchema',
}

SPECTACULAR_SETTINGS = {
    'TITLE': 'My API',
    'VERSION': '1.0.0',
    'SWAGGER_UI_DIST': 'SIDECAR',  # Serve UI from package
    'SWAGGER_UI_FAVICON_HREF': 'SIDECAR',
    'REDOC_DIST': 'SIDECAR',
}

# urls.py
from drf_spectacular.views import (
    SpectacularAPIView,
    SpectacularSwaggerView,
    SpectacularRedocView,
)

urlpatterns = [
    path('api/schema/', SpectacularAPIView.as_view(), name='schema'),
    path('api/docs/', SpectacularSwaggerView.as_view(url_name='schema'), name='swagger-ui'),
    path('api/redoc/', SpectacularRedocView.as_view(url_name='schema'), name='redoc'),
]
```

Visit:
- **Swagger UI:** http://localhost:8000/api/docs/
- **ReDoc:** http://localhost:8000/api/redoc/

## Manual Swagger UI Setup

For more control, set up Swagger UI manually with a Django template:

### Create Template

```html
<!-- templates/swagger-ui.html -->
<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8"/>
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <title>{{ title }} - Swagger UI</title>
    <link rel="stylesheet" type="text/css" href="https://unpkg.com/swagger-ui-dist@5/swagger-ui.css">
    <style>
        body {
            margin: 0;
            padding: 0;
        }
    </style>
</head>
<body>
    <div id="swagger-ui"></div>

    <script src="https://unpkg.com/swagger-ui-dist@5/swagger-ui-bundle.js"></script>
    <script src="https://unpkg.com/swagger-ui-dist@5/swagger-ui-standalone-preset.js"></script>
    <script>
        window.onload = function() {
            const ui = SwaggerUIBundle({
                url: "{{ schema_url }}",
                dom_id: '#swagger-ui',
                deepLinking: true,
                presets: [
                    SwaggerUIBundle.presets.apis,
                    SwaggerUIStandalonePreset
                ],
                plugins: [
                    SwaggerUIBundle.plugins.DownloadUrl
                ],
                layout: "StandaloneLayout",

                // Request interceptor for CSRF token
                requestInterceptor: (request) => {
                    request.headers['X-CSRFToken'] = "{{ csrf_token }}";
                    return request;
                },

                // Response interceptor
                responseInterceptor: (response) => {
                    return response;
                },

                // Additional configuration
                persistAuthorization: true,
                displayOperationId: true,
                displayRequestDuration: true,
                filter: true,
                tryItOutEnabled: true,
            });

            window.ui = ui;
        };
    </script>
</body>
</html>
```

### Configure URLs

```python
# urls.py
from django.views.generic import TemplateView
from rest_framework.schemas import get_schema_view

urlpatterns = [
    # Schema endpoint
    path(
        'api/schema/',
        get_schema_view(
            title='My API',
            description='API Documentation',
            version='1.0.0',
        ),
        name='openapi-schema'
    ),

    # Swagger UI
    path(
        'api/docs/',
        TemplateView.as_view(
            template_name='swagger-ui.html',
            extra_context={
                'schema_url': 'openapi-schema',
                'title': 'My API',
            }
        ),
        name='swagger-ui'
    ),
]
```

## Manual ReDoc Setup

### Create Template

```html
<!-- templates/redoc.html -->
<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8"/>
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <title>{{ title }} - API Documentation</title>
    <link href="https://fonts.googleapis.com/css?family=Montserrat:300,400,700|Roboto:300,400,700" rel="stylesheet">
    <style>
        body {
            margin: 0;
            padding: 0;
        }
    </style>
</head>
<body>
    <redoc spec-url="{{ schema_url }}"></redoc>

    <script src="https://cdn.jsdelivr.net/npm/redoc@latest/bundles/redoc.standalone.js"></script>
    <script>
        // Optional: Initialize with options
        Redoc.init(
            "{{ schema_url }}",
            {
                scrollYOffset: 50,
                hideDownloadButton: false,
                disableSearch: false,
                expandResponses: "200,201",
                requiredPropsFirst: true,
                sortPropsAlphabetically: true,
                showExtensions: true,
                nativeScrollbars: false,
                pathInMiddlePanel: false,
                theme: {
                    colors: {
                        primary: {
                            main: '#32329f'
                        }
                    },
                    typography: {
                        fontSize: '15px',
                        lineHeight: '1.5',
                        fontFamily: '"Roboto", sans-serif',
                        headings: {
                            fontFamily: '"Montserrat", sans-serif'
                        }
                    }
                }
            },
            document.getElementById('redoc-container')
        );
    </script>
</body>
</html>
```

### Configure URLs

```python
# urls.py
from django.views.generic import TemplateView

urlpatterns = [
    # Schema endpoint
    path('api/schema/', get_schema_view(...), name='openapi-schema'),

    # ReDoc
    path(
        'api/redoc/',
        TemplateView.as_view(
            template_name='redoc.html',
            extra_context={
                'schema_url': 'openapi-schema',
                'title': 'My API',
            }
        ),
        name='redoc'
    ),
]
```

## Swagger UI Configuration

### Complete Configuration Options

```html
<script>
    const ui = SwaggerUIBundle({
        // Required
        url: "{{ schema_url }}",              // Schema URL
        dom_id: '#swagger-ui',                 // Container element

        // Display
        deepLinking: true,                     // Enable deep linking
        displayOperationId: true,              // Show operation IDs
        displayRequestDuration: true,          // Show request duration
        defaultModelsExpandDepth: 1,           // Model expansion depth
        defaultModelExpandDepth: 1,            // Default model depth
        docExpansion: 'list',                  // 'list', 'full', or 'none'
        filter: true,                          // Enable search/filter
        maxDisplayedTags: 50,                  // Max tags to display
        showExtensions: true,                  // Show x- extensions
        showCommonExtensions: true,            // Show common extensions

        // Try it out
        tryItOutEnabled: false,                // Enable by default
        requestSnippetsEnabled: true,          // Show code snippets
        supportedSubmitMethods: [              // Allowed HTTP methods
            'get', 'post', 'put', 'delete',
            'patch', 'options', 'head', 'trace'
        ],

        // Authorization
        persistAuthorization: true,            // Persist auth between refreshes

        // Presets and plugins
        presets: [
            SwaggerUIBundle.presets.apis,
            SwaggerUIStandalonePreset
        ],
        plugins: [
            SwaggerUIBundle.plugins.DownloadUrl
        ],
        layout: "StandaloneLayout",            // Layout preset

        // OAuth configuration
        oauth2RedirectUrl: window.location.origin + '/oauth2-redirect.html',

        // Request/Response interceptors
        requestInterceptor: (request) => {
            // Add headers
            request.headers['X-CSRFToken'] = "{{ csrf_token }}";
            request.headers['X-Custom-Header'] = 'value';
            return request;
        },
        responseInterceptor: (response) => {
            // Handle responses
            console.log('Response:', response);
            return response;
        },

        // Error handling
        onComplete: () => {
            console.log('Swagger UI loaded');
        },
        onFailure: (error) => {
            console.error('Swagger UI error:', error);
        },
    });
</script>
```

### Customizing Swagger UI Appearance

```html
<!-- Add custom CSS -->
<style>
    /* Custom color scheme */
    .swagger-ui .topbar {
        background-color: #2c3e50;
    }

    .swagger-ui .topbar .download-url-wrapper .download-url-button {
        background-color: #3498db;
        border-color: #3498db;
    }

    .swagger-ui .info .title {
        color: #2c3e50;
    }

    /* Custom button colors */
    .swagger-ui .btn.authorize {
        background-color: #27ae60;
        border-color: #27ae60;
    }

    .swagger-ui .btn.execute {
        background-color: #3498db;
        border-color: #3498db;
    }

    /* Hide elements */
    .swagger-ui .topbar {
        display: none;  /* Hide top bar */
    }

    .swagger-ui .information-container {
        margin: 50px 0;
    }
</style>
```

### Adding Authentication to Swagger UI

```html
<script>
    const ui = SwaggerUIBundle({
        url: "{{ schema_url }}",
        dom_id: '#swagger-ui',

        // Prefill authorization
        onComplete: () => {
            // Add Bearer token from localStorage
            const token = localStorage.getItem('api_token');
            if (token) {
                ui.preauthorizeApiKey('BearerAuth', token);
            }
        },

        // Custom auth
        requestInterceptor: (request) => {
            const token = localStorage.getItem('api_token');
            if (token) {
                request.headers['Authorization'] = `Bearer ${token}`;
            }
            return request;
        },
    });

    // Add token management UI
    document.addEventListener('DOMContentLoaded', () => {
        const tokenInput = document.createElement('input');
        tokenInput.type = 'text';
        tokenInput.placeholder = 'Enter API Token';
        tokenInput.style.margin = '20px';

        const saveButton = document.createElement('button');
        saveButton.textContent = 'Save Token';
        saveButton.onclick = () => {
            localStorage.setItem('api_token', tokenInput.value);
            location.reload();
        };

        document.body.insertBefore(saveButton, document.getElementById('swagger-ui'));
        document.body.insertBefore(tokenInput, saveButton);
    });
</script>
```

## ReDoc Configuration

### Complete Configuration Options

```html
<script>
    Redoc.init(
        "{{ schema_url }}",
        {
            // Display options
            scrollYOffset: 0,                  // Scroll offset for anchors
            hideDownloadButton: false,         // Hide "Download" button
            disableSearch: false,              // Disable search
            expandResponses: "200,201",        // Auto-expand responses
            expandSingleSchemaField: true,     // Expand single schema fields
            hideHostname: false,               // Hide hostname in operations
            hideLoading: false,                // Hide loading animation
            hideSingleRequestSampleTab: false, // Hide single sample tab
            menuToggle: true,                  // Enable menu toggle
            nativeScrollbars: false,           // Use custom scrollbars
            noAutoAuth: false,                 // Disable auto auth
            onlyRequiredInSamples: false,      // Only show required in samples
            pathInMiddlePanel: false,          // Show path in middle panel
            requiredPropsFirst: true,          // Show required props first
            sortPropsAlphabetically: true,     // Sort props alphabetically
            showExtensions: false,             // Show x- extensions
            suppressWarnings: false,           // Suppress warnings
            payloadSampleIdx: 0,               // Default sample index

            // Theme customization
            theme: {
                spacing: {
                    unit: 5,
                    sectionHorizontal: ({ spacing }) => spacing.unit * 8,
                    sectionVertical: ({ spacing }) => spacing.unit * 8,
                },
                breakpoints: {
                    small: '50rem',
                    medium: '75rem',
                    large: '105rem',
                },
                colors: {
                    primary: {
                        main: '#32329f',
                        light: '#5352d6',
                        dark: '#23296a',
                        contrastText: '#ffffff',
                    },
                    success: {
                        main: '#27ae60',
                        light: '#2ecc71',
                        dark: '#1e8449',
                        contrastText: '#ffffff',
                    },
                    warning: {
                        main: '#f39c12',
                        light: '#f1c40f',
                        dark: '#d68910',
                        contrastText: '#ffffff',
                    },
                    error: {
                        main: '#e74c3c',
                        light: '#ec7063',
                        dark: '#c0392b',
                        contrastText: '#ffffff',
                    },
                    gray: {
                        50: '#fafafa',
                        100: '#f5f5f5',
                    },
                    text: {
                        primary: '#263238',
                        secondary: '#546e7a',
                    },
                    border: {
                        dark: '#e1e1e1',
                        light: '#f5f5f5',
                    },
                },
                typography: {
                    fontSize: '14px',
                    lineHeight: '1.5em',
                    fontWeightRegular: '400',
                    fontWeightBold: '600',
                    fontWeightLight: '300',
                    fontFamily: '"Roboto", sans-serif',
                    smoothing: 'antialiased',
                    optimizeSpeed: true,
                    headings: {
                        fontFamily: '"Montserrat", sans-serif',
                        fontWeight: '700',
                    },
                    code: {
                        fontSize: '13px',
                        fontFamily: 'Courier, monospace',
                        fontWeight: '400',
                        color: '#e74c3c',
                        backgroundColor: '#f5f5f5',
                        wrap: false,
                    },
                    links: {
                        color: '#32329f',
                        visited: '#32329f',
                        hover: '#5352d6',
                    },
                },
                sidebar: {
                    width: '260px',
                    backgroundColor: '#fafafa',
                    textColor: '#333333',
                },
                rightPanel: {
                    backgroundColor: '#263238',
                    width: '40%',
                },
            },
        },
        document.querySelector('redoc')
    );
</script>
```

### Custom ReDoc Logo and Favicon

```html
<head>
    <link rel="icon" type="image/png" href="/static/favicon.png">
    <style>
        /* Add custom logo */
        redoc::before {
            content: '';
            display: block;
            background: url('/static/logo.png') no-repeat center;
            background-size: contain;
            width: 200px;
            height: 50px;
            margin: 20px auto;
        }
    </style>
</head>
```

## Hosting Static Files

For production, serve UI assets locally:

### Download Assets

```bash
# Swagger UI
mkdir -p static/swagger-ui
cd static/swagger-ui
wget https://unpkg.com/swagger-ui-dist@5/swagger-ui-bundle.js
wget https://unpkg.com/swagger-ui-dist@5/swagger-ui-standalone-preset.js
wget https://unpkg.com/swagger-ui-dist@5/swagger-ui.css

# ReDoc
mkdir -p static/redoc
cd static/redoc
wget https://cdn.jsdelivr.net/npm/redoc@latest/bundles/redoc.standalone.js
```

### Update Templates

```html
<!-- Use local assets -->
<link rel="stylesheet" type="text/css" href="{% static 'swagger-ui/swagger-ui.css' %}">
<script src="{% static 'swagger-ui/swagger-ui-bundle.js' %}"></script>
<script src="{% static 'redoc/redoc.standalone.js' %}"></script>
```

## Multi-Version Documentation

Support multiple API versions:

```python
# urls.py
from drf_spectacular.views import SpectacularSwaggerView

urlpatterns = [
    # V1 Documentation
    path(
        'api/v1/docs/',
        SpectacularSwaggerView.as_view(
            url_name='schema-v1',
            template_name='swagger-v1.html',
        ),
        name='swagger-ui-v1'
    ),

    # V2 Documentation
    path(
        'api/v2/docs/',
        SpectacularSwaggerView.as_view(
            url_name='schema-v2',
            template_name='swagger-v2.html',
        ),
        name='swagger-ui-v2'
    ),
]
```

## Comparison: Swagger UI vs ReDoc

| Feature | Swagger UI | ReDoc |
|---------|-----------|-------|
| **Interactive Testing** | ✅ Full support | ❌ View only |
| **UI Design** | Classic, functional | Modern, clean |
| **Mobile Responsive** | ⚠️ Limited | ✅ Excellent |
| **Performance** | Good | Excellent |
| **Customization** | High | High |
| **Code Examples** | Multiple languages | Multiple languages |
| **Search** | ✅ | ✅ |
| **Deep Linking** | ✅ | ✅ |
| **Authentication UI** | ✅ Built-in | ⚠️ Basic |
| **Best For** | Development, Testing | Public docs, Portals |

## Best Practices

1. **Use drf-spectacular** - Easiest setup with both UIs
2. **Enable CORS for testing** - Allow testing from docs UI
3. **Persist authentication** - Save tokens between sessions
4. **Customize branding** - Add your logo and colors
5. **Serve locally in production** - Don't depend on CDNs
6. **Enable HTTPS** - Especially for authentication testing
7. **Add request examples** - Help users understand API
8. **Document authentication** - Show how to get tokens
9. **Use both UIs** - Swagger for testing, ReDoc for docs
10. **Version your docs** - Maintain docs for each API version

## Security Considerations

```python
# Restrict access to documentation
from rest_framework.permissions import IsAuthenticated, IsAdminUser

urlpatterns = [
    # Public schema (limited)
    path('api/schema/', SpectacularAPIView.as_view(
        permission_classes=[AllowAny]
    ), name='schema'),

    # Internal docs (authenticated)
    path('api/docs/', SpectacularSwaggerView.as_view(
        url_name='schema',
        permission_classes=[IsAuthenticated]
    ), name='swagger-ui'),

    # Admin docs (admin only)
    path('api/admin/docs/', SpectacularSwaggerView.as_view(
        url_name='admin-schema',
        permission_classes=[IsAdminUser]
    ), name='admin-swagger-ui'),
]
```

## Troubleshooting

### CORS Issues

```python
# settings.py - Allow CORS for schema and docs
CORS_ALLOW_ALL_ORIGINS = False
CORS_ALLOWED_ORIGINS = [
    'http://localhost:8000',
    'https://yourdomain.com',
]

# Or install django-cors-headers
pip install django-cors-headers
```

### Assets Not Loading

```python
# Ensure static files are configured
STATIC_URL = '/static/'
STATIC_ROOT = os.path.join(BASE_DIR, 'staticfiles')

# Collect static files
python manage.py collectstatic
```

### Schema Not Found

```python
# Verify schema URL is accessible
from rest_framework.test import APIClient

client = APIClient()
response = client.get('/api/schema/')
assert response.status_code == 200
```

## Related Documentation

- [OpenAPI Generation](openapi-generation.md) - Schema generation basics
- [Schema Customization](schema-customization.md) - Customize your schema
- [drf-spectacular](drf-spectacular.md) - Advanced schema generation
- [Code Examples](examples/documentation-patterns.py) - Working examples
