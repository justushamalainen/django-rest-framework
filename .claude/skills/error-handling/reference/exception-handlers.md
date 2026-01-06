# Custom Exception Handlers

Learn how to implement custom exception handlers in Django REST Framework to transform exceptions into consistent, informative API responses.

## Table of Contents

- [Default Exception Handler](#default-exception-handler)
- [Creating Custom Exception Handlers](#creating-custom-exception-handlers)
- [Exception Handler Patterns](#exception-handler-patterns)
- [Handler Configuration](#handler-configuration)
- [Advanced Techniques](#advanced-techniques)
- [Testing Exception Handlers](#testing-exception-handlers)

## Default Exception Handler

DRF provides a default exception handler in `rest_framework.views.exception_handler`:

```python
def exception_handler(exc, context):
    """
    Returns the response that should be used for any given exception.

    By default we handle the REST framework `APIException`, and also
    Django's built-in `Http404` and `PermissionDenied` exceptions.

    Any unhandled exceptions may return `None`, which will cause a 500 error
    to be raised.
    """
    if isinstance(exc, Http404):
        exc = exceptions.NotFound(*(exc.args))
    elif isinstance(exc, PermissionDenied):
        exc = exceptions.PermissionDenied(*(exc.args))

    if isinstance(exc, exceptions.APIException):
        headers = {}
        if getattr(exc, 'auth_header', None):
            headers['WWW-Authenticate'] = exc.auth_header
        if getattr(exc, 'wait', None):
            headers['Retry-After'] = '%d' % exc.wait

        if isinstance(exc.detail, (list, dict)):
            data = exc.detail
        else:
            data = {'detail': exc.detail}

        set_rollback()
        return Response(data, status=exc.status_code, headers=headers)

    return None  # Unhandled exceptions return None
```

### What the Default Handler Does

1. **Converts Django exceptions** to DRF exceptions
2. **Extracts exception details** and formats them
3. **Sets appropriate headers** (WWW-Authenticate, Retry-After)
4. **Rolls back database transactions**
5. **Returns Response** or None for unhandled exceptions

## Creating Custom Exception Handlers

### Basic Custom Handler

```python
# myapp/exception_handlers.py
from rest_framework.views import exception_handler
from rest_framework.response import Response
from rest_framework import status
import logging

logger = logging.getLogger(__name__)

def custom_exception_handler(exc, context):
    """
    Custom exception handler that wraps DRF's default handler.

    Args:
        exc: The exception instance raised
        context: Dict containing:
            - 'view': The view that raised the exception
            - 'args': Positional args to the view
            - 'kwargs': Keyword args to the view
            - 'request': The request object

    Returns:
        Response object or None
    """
    # Call DRF's default handler first
    response = exception_handler(exc, context)

    # If response is None, exception is not handled by DRF
    if response is None:
        # Handle non-DRF exceptions
        logger.exception(f"Unhandled exception: {exc}")
        return Response(
            {
                'detail': 'Internal server error',
                'type': 'ServerError'
            },
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )

    # Customize the response data
    response.data['status_code'] = response.status_code
    response.data['error_type'] = exc.__class__.__name__

    # Log the error
    logger.warning(
        f"API Exception: {exc.__class__.__name__}",
        extra={
            'status_code': response.status_code,
            'path': context['request'].path,
            'method': context['request'].method,
        }
    )

    return response
```

### Configure in Settings

```python
# settings.py
REST_FRAMEWORK = {
    'EXCEPTION_HANDLER': 'myapp.exception_handlers.custom_exception_handler'
}
```

## Exception Handler Patterns

### Pattern 1: Adding Consistent Fields

Add standard fields to all error responses:

```python
def consistent_exception_handler(exc, context):
    response = exception_handler(exc, context)

    if response is not None:
        # Add timestamp
        from datetime import datetime
        response.data['timestamp'] = datetime.utcnow().isoformat()

        # Add status code
        response.data['status'] = response.status_code

        # Add request ID (if available)
        request = context.get('request')
        if request and hasattr(request, 'id'):
            response.data['request_id'] = request.id

        # Add path
        response.data['path'] = request.path if request else None

    return response

# Response format:
# {
#     "detail": "Not found.",
#     "timestamp": "2024-01-15T10:30:45.123456",
#     "status": 404,
#     "request_id": "abc123",
#     "path": "/api/users/999/"
# }
```

### Pattern 2: Error Code Hierarchy

Structure errors with hierarchical codes:

```python
def hierarchical_error_handler(exc, context):
    response = exception_handler(exc, context)

    if response is not None:
        # Extract error codes
        error_code = getattr(exc, 'default_code', 'unknown_error')

        # Build error response
        response.data = {
            'error': {
                'code': error_code,
                'message': str(exc.detail),
                'status': response.status_code,
                'details': exc.detail if isinstance(exc.detail, dict) else None
            }
        }

    return response

# Response format:
# {
#     "error": {
#         "code": "validation_error",
#         "message": "Invalid input.",
#         "status": 400,
#         "details": {
#             "email": ["Enter a valid email address"]
#         }
#     }
# }
```

### Pattern 3: User-Friendly Messages

Separate technical and user-facing messages:

```python
def user_friendly_handler(exc, context):
    response = exception_handler(exc, context)

    if response is not None:
        # Map error types to user-friendly messages
        user_messages = {
            'NotAuthenticated': 'Please log in to continue.',
            'PermissionDenied': 'You don\'t have access to this resource.',
            'NotFound': 'The requested resource was not found.',
            'ValidationError': 'Please check your input and try again.',
            'Throttled': 'Too many requests. Please slow down.',
        }

        error_type = exc.__class__.__name__
        user_message = user_messages.get(error_type, 'An error occurred.')

        response.data = {
            'user_message': user_message,
            'technical_message': str(exc.detail),
            'error_code': getattr(exc, 'default_code', None),
            'status_code': response.status_code
        }

    return response
```

### Pattern 4: Logging and Monitoring

Integrate with logging and monitoring services:

```python
import logging
import traceback
from django.conf import settings

logger = logging.getLogger(__name__)

def monitored_exception_handler(exc, context):
    response = exception_handler(exc, context)

    # Get request info
    request = context.get('request')
    view = context.get('view')

    # Build log context
    log_context = {
        'exception_type': exc.__class__.__name__,
        'path': request.path if request else None,
        'method': request.method if request else None,
        'user_id': getattr(request.user, 'id', None) if request else None,
        'view': view.__class__.__name__ if view else None,
    }

    if response is not None:
        # Log DRF exceptions
        log_context['status_code'] = response.status_code

        if response.status_code >= 500:
            logger.error(
                f"Server error: {exc}",
                extra=log_context,
                exc_info=True
            )
        elif response.status_code >= 400:
            logger.warning(
                f"Client error: {exc}",
                extra=log_context
            )

        # Add request ID for tracking
        if hasattr(request, 'id'):
            response.data['request_id'] = request.id

    else:
        # Unhandled exception - always log as error
        logger.exception(
            f"Unhandled exception: {exc}",
            extra=log_context
        )

        # Send to error tracking (e.g., Sentry)
        if hasattr(settings, 'SENTRY_DSN'):
            # Sentry SDK automatically captures unhandled exceptions
            pass

        # Return generic error response
        response = Response(
            {
                'detail': 'An unexpected error occurred',
                'request_id': getattr(request, 'id', None)
            },
            status=500
        )

    return response
```

### Pattern 5: Multi-Language Support

Return error messages in the user's language:

```python
from django.utils.translation import gettext as _
from rest_framework.views import exception_handler

def i18n_exception_handler(exc, context):
    response = exception_handler(exc, context)

    if response is not None:
        request = context.get('request')

        # Get user's preferred language
        if request and hasattr(request, 'LANGUAGE_CODE'):
            language = request.LANGUAGE_CODE
        else:
            language = 'en'

        # Translate error messages
        if isinstance(response.data, dict):
            if 'detail' in response.data:
                # Main error message is already translated by DRF
                pass

            # Add localized help text
            error_code = getattr(exc, 'default_code', None)
            if error_code:
                help_messages = {
                    'not_authenticated': _('Please log in to access this resource.'),
                    'permission_denied': _('You do not have the required permissions.'),
                    'not_found': _('The requested item does not exist.'),
                    'throttled': _('Please wait before making another request.'),
                }
                if error_code in help_messages:
                    response.data['help'] = help_messages[error_code]

    return response
```

### Pattern 6: Development vs Production

Different error details based on environment:

```python
from django.conf import settings
from rest_framework.views import exception_handler
import traceback

def environment_aware_handler(exc, context):
    response = exception_handler(exc, context)

    if response is None:
        # Unhandled exception
        if settings.DEBUG:
            # In development, show full traceback
            response = Response(
                {
                    'detail': 'Internal server error',
                    'exception': str(exc),
                    'exception_type': exc.__class__.__name__,
                    'traceback': traceback.format_exc()
                },
                status=500
            )
        else:
            # In production, show minimal info
            response = Response(
                {
                    'detail': 'Internal server error',
                    'request_id': getattr(context.get('request'), 'id', None)
                },
                status=500
            )
    elif settings.DEBUG:
        # In development, add extra debug info
        response.data['debug'] = {
            'exception_type': exc.__class__.__name__,
            'view': context['view'].__class__.__name__,
            'view_method': context['view'].request.method,
        }

    return response
```

## Handler Configuration

### Multiple Handlers for Different Apps

```python
# common/exception_handlers.py
from rest_framework.views import exception_handler as drf_handler

def api_v1_exception_handler(exc, context):
    """Handler for API v1 - maintains backward compatibility."""
    response = drf_handler(exc, context)
    if response:
        # V1 format
        response.data = {
            'error_message': str(exc.detail),
            'error_code': response.status_code
        }
    return response

def api_v2_exception_handler(exc, context):
    """Handler for API v2 - new format with more details."""
    response = drf_handler(exc, context)
    if response:
        # V2 format
        response.data = {
            'error': {
                'message': str(exc.detail),
                'code': getattr(exc, 'default_code', 'unknown'),
                'status': response.status_code,
                'timestamp': timezone.now().isoformat()
            }
        }
    return response

# Configure per ViewSet
class V1UserViewSet(viewsets.ModelViewSet):
    @property
    def settings(self):
        settings = super().settings
        settings['EXCEPTION_HANDLER'] = 'common.exception_handlers.api_v1_exception_handler'
        return settings

class V2UserViewSet(viewsets.ModelViewSet):
    @property
    def settings(self):
        settings = super().settings
        settings['EXCEPTION_HANDLER'] = 'common.exception_handlers.api_v2_exception_handler'
        return settings
```

### Conditional Handler Selection

```python
def smart_exception_handler(exc, context):
    """Select handler based on request context."""
    request = context.get('request')

    # Use different handlers based on conditions
    if request and request.path.startswith('/api/v1/'):
        return api_v1_exception_handler(exc, context)
    elif request and request.path.startswith('/api/v2/'):
        return api_v2_exception_handler(exc, context)
    elif request and request.accepted_renderer.format == 'xml':
        return xml_exception_handler(exc, context)
    else:
        return default_exception_handler(exc, context)
```

## Advanced Techniques

### Pattern Matching on Exception Types

```python
from rest_framework import exceptions
from myapp.exceptions import BusinessRuleViolation, ExternalServiceError

def pattern_matching_handler(exc, context):
    response = exception_handler(exc, context)

    # Handle specific exception types differently
    if isinstance(exc, exceptions.ValidationError):
        # Add validation-specific fields
        if response:
            response.data['validation_failed'] = True

    elif isinstance(exc, exceptions.NotAuthenticated):
        # Add authentication URL
        if response:
            response.data['login_url'] = '/api/auth/login/'

    elif isinstance(exc, BusinessRuleViolation):
        # Add rule-specific information
        if response:
            response.data['rule_name'] = exc.rule_name
            response.data['rule_description'] = exc.rule_description

    elif isinstance(exc, ExternalServiceError):
        # Add retry information
        if response:
            response.data['retry_after'] = 60
            response.data['service'] = exc.service_name

    return response
```

### Enriching Error Context

```python
def context_enriched_handler(exc, context):
    response = exception_handler(exc, context)

    if response is not None:
        request = context.get('request')

        # Add request context
        response.data['context'] = {
            'method': request.method,
            'path': request.path,
            'query_params': dict(request.query_params),
        }

        # Add user context (if authenticated)
        if request.user.is_authenticated:
            response.data['context']['user'] = {
                'id': request.user.id,
                'username': request.user.username,
            }

        # Add view context
        view = context.get('view')
        if view:
            response.data['context']['view'] = {
                'name': view.__class__.__name__,
                'action': getattr(view, 'action', None),
            }

    return response
```

### Error Response Transformers

```python
def transform_errors(data, transformer):
    """Recursively transform error structure."""
    if isinstance(data, dict):
        return {key: transform_errors(value, transformer) for key, value in data.items()}
    elif isinstance(data, list):
        return [transform_errors(item, transformer) for item in data]
    else:
        return transformer(data)

def camelcase_error_handler(exc, context):
    """Convert error keys to camelCase for JavaScript clients."""
    response = exception_handler(exc, context)

    if response:
        def to_camel_case(text):
            """Convert snake_case to camelCase."""
            if isinstance(text, str):
                components = text.split('_')
                return components[0] + ''.join(x.title() for x in components[1:])
            return text

        # Transform keys to camelCase
        def transform_dict(d):
            if isinstance(d, dict):
                return {
                    to_camel_case(key): transform_dict(value)
                    for key, value in d.items()
                }
            elif isinstance(d, list):
                return [transform_dict(item) for item in d]
            return d

        response.data = transform_dict(response.data)

    return response
```

## Testing Exception Handlers

### Unit Tests

```python
# tests/test_exception_handlers.py
from django.test import TestCase, RequestFactory
from rest_framework.exceptions import ValidationError, NotFound
from myapp.exception_handlers import custom_exception_handler

class ExceptionHandlerTests(TestCase):
    def setUp(self):
        self.factory = RequestFactory()

    def test_validation_error_response(self):
        """Test ValidationError is handled correctly."""
        request = self.factory.get('/api/test/')
        exc = ValidationError({'email': 'Invalid email'})
        context = {'request': request, 'view': None}

        response = custom_exception_handler(exc, context)

        self.assertEqual(response.status_code, 400)
        self.assertIn('email', response.data)
        self.assertIn('status_code', response.data)

    def test_not_found_error_response(self):
        """Test NotFound is handled correctly."""
        request = self.factory.get('/api/test/')
        exc = NotFound('Resource not found')
        context = {'request': request, 'view': None}

        response = custom_exception_handler(exc, context)

        self.assertEqual(response.status_code, 404)
        self.assertEqual(response.data['detail'], 'Resource not found')

    def test_unhandled_exception(self):
        """Test unhandled exceptions return 500."""
        request = self.factory.get('/api/test/')
        exc = ValueError('Something went wrong')
        context = {'request': request, 'view': None}

        response = custom_exception_handler(exc, context)

        self.assertEqual(response.status_code, 500)
        self.assertIn('detail', response.data)
```

### Integration Tests

```python
from rest_framework.test import APITestCase
from rest_framework import status

class ErrorHandlingIntegrationTests(APITestCase):
    def test_validation_error_format(self):
        """Test error response format for validation errors."""
        response = self.client.post('/api/users/', {
            'email': 'invalid-email',
            'password': 'short'
        })

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('status_code', response.data)
        self.assertIn('error_type', response.data)
        self.assertEqual(response.data['status_code'], 400)

    def test_not_found_includes_request_id(self):
        """Test that 404 errors include request ID."""
        response = self.client.get('/api/users/999999/')

        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
        if 'request_id' in response.data:
            self.assertIsNotNone(response.data['request_id'])
```

## Best Practices

1. **Always call the default handler first** - Don't reinvent the wheel
2. **Check if response is None** - Handle unhandled exceptions gracefully
3. **Don't leak sensitive information** - Be careful in production
4. **Log appropriately** - Different levels for different errors
5. **Add context carefully** - Balance between helpful and verbose
6. **Test thoroughly** - Unit and integration tests
7. **Document the format** - Clients need to know what to expect
8. **Version your error format** - Maintain backward compatibility
9. **Use consistent structure** - Make parsing easy for clients
10. **Consider internationalization** - Support multiple languages

## Common Pitfalls

### Don't Forget None Check

```python
# Bad
def bad_handler(exc, context):
    response = exception_handler(exc, context)
    response.data['custom'] = 'value'  # Crashes if response is None!
    return response

# Good
def good_handler(exc, context):
    response = exception_handler(exc, context)
    if response is not None:
        response.data['custom'] = 'value'
    return response
```

### Don't Modify Response Status

```python
# Bad
def bad_handler(exc, context):
    response = exception_handler(exc, context)
    if response:
        response.status_code = 200  # Don't change error status!
    return response

# Good - Status code should match the error type
def good_handler(exc, context):
    response = exception_handler(exc, context)
    # Don't modify response.status_code
    return response
```

### Don't Block Exception Propagation

```python
# Bad
def bad_handler(exc, context):
    try:
        response = exception_handler(exc, context)
        # ... processing ...
        return response
    except Exception:
        return None  # Swallows exceptions!

# Good
def good_handler(exc, context):
    response = exception_handler(exc, context)
    # Let exceptions propagate if handler itself fails
    return response
```

## Related Documentation

- [Built-in Exceptions](./builtin-exceptions.md)
- [Custom Exceptions](./custom-exceptions.md)
- [Error Responses](./error-responses.md)
- [Error Patterns](./examples/error-patterns.py)

## Source Reference

- `/home/user/django-rest-framework/rest_framework/views.py` - Default exception_handler implementation
