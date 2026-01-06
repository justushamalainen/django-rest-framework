# Custom Exception Handlers

**The default exception handler is excellent - don't customize unless you have a specific need.**

DRF's built-in exception handler covers 95% of use cases. Only create a custom handler if you need to add request IDs, integrate with logging/monitoring, or maintain a legacy error format.

## The Default Handler

DRF's default exception handler does everything you need:

```python
# From rest_framework.views
def exception_handler(exc, context):
    """
    Returns the response for any given exception.

    Handles:
    - All APIException subclasses
    - Django's Http404 → NotFound
    - Django's PermissionDenied → PermissionDenied
    """
    # Convert Django exceptions to DRF exceptions
    if isinstance(exc, Http404):
        exc = exceptions.NotFound(*(exc.args))
    elif isinstance(exc, PermissionDenied):
        exc = exceptions.PermissionDenied(*(exc.args))

    # Handle DRF exceptions
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

    return None  # Let Django handle non-API exceptions (500 error)
```

**What it does:**
1. Converts Django exceptions to DRF exceptions
2. Formats error responses consistently
3. Sets appropriate HTTP headers (WWW-Authenticate, Retry-After)
4. Rolls back database transactions
5. Returns None for unhandled exceptions (Django shows 500 error page)

## When to Customize

Only create a custom handler if you need to:

1. **Add request IDs** for error tracking
2. **Log errors** to monitoring services (Sentry, CloudWatch, etc.)
3. **Add timestamps** to all error responses
4. **Support legacy error format** for backward compatibility

**Don't customize** just to change error messages or status codes - use custom exception classes instead.

## Creating a Custom Handler

### Pattern: Adding Request ID

This is the most common customization - adding a request ID for tracking errors:

```python
# myapp/exception_handlers.py
from rest_framework.views import exception_handler
from rest_framework.response import Response
import logging
import uuid

logger = logging.getLogger(__name__)

def custom_exception_handler(exc, context):
    """
    Custom handler that adds request_id to all error responses.

    Args:
        exc: The exception instance
        context: Dict with 'view' and 'request' keys

    Returns:
        Response object or None
    """
    # Call DRF's default handler first
    response = exception_handler(exc, context)

    # Add request ID to all responses
    request = context.get('request')
    request_id = getattr(request, 'id', str(uuid.uuid4()))

    if response is not None:
        # Add request ID to error response
        response.data['request_id'] = request_id

        # Log the error
        logger.warning(
            f"API Error: {exc.__class__.__name__}",
            extra={
                'request_id': request_id,
                'status_code': response.status_code,
                'path': request.path,
                'method': request.method,
            }
        )
    else:
        # Unhandled exception - log as error
        logger.exception(
            f"Unhandled exception: {exc}",
            extra={
                'request_id': request_id,
                'path': request.path if request else None,
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

### Response Format

```json
{
  "email": ["Enter a valid email address"],
  "request_id": "abc123-def456-ghi789"
}
```

## Advanced: Logging Integration

If you need to integrate with monitoring services:

```python
from rest_framework.views import exception_handler
from rest_framework.response import Response
import logging

logger = logging.getLogger(__name__)

def monitored_exception_handler(exc, context):
    """Handler with monitoring integration."""
    response = exception_handler(exc, context)
    request = context.get('request')

    # Build logging context
    log_context = {
        'exception_type': exc.__class__.__name__,
        'path': request.path if request else None,
        'method': request.method if request else None,
        'user_id': getattr(request.user, 'id', None) if request else None,
    }

    if response is not None:
        # Log known API exceptions
        log_context['status_code'] = response.status_code

        if response.status_code >= 500:
            logger.error(f"Server error: {exc}", extra=log_context, exc_info=True)
        elif response.status_code >= 400:
            logger.warning(f"Client error: {exc}", extra=log_context)

        # Add request ID
        request_id = getattr(request, 'id', None)
        if request_id:
            response.data['request_id'] = request_id
    else:
        # Unhandled exception - log as error and return 500
        logger.exception(f"Unhandled exception: {exc}", extra=log_context)

        # Return generic 500 error
        response = Response(
            {
                'detail': 'Internal server error',
                'request_id': getattr(request, 'id', None)
            },
            status=500
        )

    return response
```

## Testing Custom Handlers

```python
# tests/test_exception_handlers.py
from django.test import TestCase, RequestFactory
from rest_framework.exceptions import ValidationError, NotFound
from myapp.exception_handlers import custom_exception_handler

class ExceptionHandlerTests(TestCase):
    def setUp(self):
        self.factory = RequestFactory()

    def test_adds_request_id(self):
        """Test that handler adds request_id to errors."""
        request = self.factory.get('/api/test/')
        request.id = 'test-123'
        exc = ValidationError({'email': 'Invalid email'})
        context = {'request': request, 'view': None}

        response = custom_exception_handler(exc, context)

        self.assertEqual(response.status_code, 400)
        self.assertIn('request_id', response.data)
        self.assertEqual(response.data['request_id'], 'test-123')

    def test_handles_unhandled_exceptions(self):
        """Test that unhandled exceptions don't crash."""
        request = self.factory.get('/api/test/')
        exc = ValueError('Something broke')
        context = {'request': request, 'view': None}

        response = custom_exception_handler(exc, context)

        # Handler should return None or handle gracefully
        self.assertIsNotNone(response)
```

## Common Mistakes

### 1. Not Checking if Response is None

```python
# WRONG - crashes on unhandled exceptions
def bad_handler(exc, context):
    response = exception_handler(exc, context)
    response.data['custom'] = 'value'  # CRASH if response is None!
    return response

# RIGHT - always check
def good_handler(exc, context):
    response = exception_handler(exc, context)
    if response is not None:  # Always check!
        response.data['custom'] = 'value'
    return response
```

### 2. Not Calling Default Handler First

```python
# WRONG - reimplementing everything
def bad_handler(exc, context):
    return Response({'error': str(exc)}, status=500)

# RIGHT - use default handler
def good_handler(exc, context):
    response = exception_handler(exc, context)  # Let DRF do the work
    if response is not None:
        # Add your customizations
        response.data['timestamp'] = timezone.now()
    return response
```

### 3. Modifying Status Codes

```python
# WRONG - changing status codes
def bad_handler(exc, context):
    response = exception_handler(exc, context)
    if response:
        response.status_code = 200  # Don't do this!
    return response

# Status codes should match exception types
# If you need different codes, create custom exception classes
```

## Best Practices

1. **Call the default handler first** - Don't reinvent the wheel
2. **Always check if response is None** - Handle unhandled exceptions
3. **Keep it simple** - Only add what you truly need
4. **Log appropriately** - Different levels for client vs server errors
5. **Test thoroughly** - Exception handling is critical
6. **Document the format** - Clients need to know what to expect

## Source Files

- `/home/user/django-rest-framework/rest_framework/views.py` - Default exception_handler
- `/home/user/django-rest-framework/rest_framework/exceptions.py` - Exception classes
