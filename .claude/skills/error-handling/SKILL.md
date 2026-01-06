---
name: Error Handling
description: Master DRF exception handling, custom error responses, and debugging strategies
keywords: [exceptions, errors, APIException, validation, error responses, debugging]
version: 1.0.0
---

# DRF Error Handling Skill

Master Django REST Framework's comprehensive error handling system. Learn how to use built-in exceptions, create custom error types, implement sophisticated exception handlers, and format error responses for better API debugging and user experience.

## What You'll Learn

After completing this skill, you'll be able to:

- **Choose the right built-in exception** for any error scenario (ValidationError, NotFound, PermissionDenied, etc.)
- **Create custom exception classes** with appropriate status codes and error details
- **Implement custom exception handlers** to transform errors into consistent API responses
- **Format error responses** with proper structure, codes, and debugging information
- **Handle Django exceptions** (Http404, PermissionDenied) in DRF views
- **Use error codes** for programmatic error handling by API clients
- **Debug complex validation errors** with nested data structures
- **Implement retry logic** for throttled requests
- **Add context to errors** for better debugging and monitoring
- **Follow error handling best practices** for production APIs

## Quick Start

### Basic Exception Handling

```python
from rest_framework import status
from rest_framework.decorators import api_view
from rest_framework.exceptions import (
    NotFound, PermissionDenied, ValidationError,
    AuthenticationFailed, Throttled
)
from rest_framework.response import Response

@api_view(['GET'])
def get_user(request, user_id):
    """Raise appropriate exceptions based on the scenario."""
    try:
        user = User.objects.get(id=user_id)
    except User.DoesNotExist:
        # Returns 404 with {"detail": "User not found"}
        raise NotFound("User not found")

    # Check permissions
    if not request.user.has_perm('view_user', user):
        # Returns 403
        raise PermissionDenied("You cannot view this user")

    serializer = UserSerializer(user)
    return Response(serializer.data)
```

### Custom Exception Handler

```python
# myapp/exceptions.py
from rest_framework.views import exception_handler
from rest_framework.exceptions import APIException
import logging

logger = logging.getLogger(__name__)

def custom_exception_handler(exc, context):
    """
    Custom exception handler that adds extra context to error responses.

    Args:
        exc: The exception instance
        context: Dict with 'view' and 'request' keys

    Returns:
        Response object or None
    """
    # Call DRF's default handler first
    response = exception_handler(exc, context)

    if response is not None:
        # Add custom fields to all error responses
        response.data['status_code'] = response.status_code
        response.data['error_type'] = exc.__class__.__name__

        # Add request context for debugging
        if hasattr(context.get('request'), 'user'):
            user = context['request'].user
            if user.is_authenticated:
                response.data['user_id'] = user.id

        # Add view info
        if 'view' in context:
            response.data['path'] = context['request'].path

        # Log the error
        logger.error(
            f"API Error: {exc.__class__.__name__} at {context['request'].path}",
            exc_info=True,
            extra={
                'status_code': response.status_code,
                'user': getattr(context['request'].user, 'id', None),
                'method': context['request'].method,
            }
        )
    else:
        # Handle non-API exceptions (will result in 500)
        logger.exception(f"Unhandled exception: {exc}")

    return response

# settings.py
REST_FRAMEWORK = {
    'EXCEPTION_HANDLER': 'myapp.exceptions.custom_exception_handler'
}
```

### Creating Custom Exceptions

```python
# myapp/exceptions.py
from rest_framework import status
from rest_framework.exceptions import APIException

class ServiceUnavailable(APIException):
    """Raised when an external service is unavailable."""
    status_code = status.HTTP_503_SERVICE_UNAVAILABLE
    default_detail = 'Service temporarily unavailable, try again later.'
    default_code = 'service_unavailable'

class PaymentRequired(APIException):
    """Raised when payment is required to access a resource."""
    status_code = status.HTTP_402_PAYMENT_REQUIRED
    default_detail = 'Payment required to access this resource.'
    default_code = 'payment_required'

class ResourceConflict(APIException):
    """Raised when there's a conflict with the current state."""
    status_code = status.HTTP_409_CONFLICT
    default_detail = 'The request conflicts with the current state.'
    default_code = 'conflict'

# Usage in views
from myapp.exceptions import ServiceUnavailable, PaymentRequired

@api_view(['POST'])
def create_order(request):
    user = request.user

    # Check if user has active subscription
    if not user.has_active_subscription:
        raise PaymentRequired({
            'detail': 'Active subscription required',
            'upgrade_url': '/subscriptions/upgrade/'
        })

    # Try to process with external service
    try:
        result = payment_service.process(request.data)
    except ExternalServiceError:
        raise ServiceUnavailable(
            'Payment processing temporarily unavailable'
        )

    return Response(result, status=status.HTTP_201_CREATED)
```

## Decision Tree: Which Exception to Use?

Use this decision tree to choose the right exception type:

```
Is the request properly authenticated?
├─ NO → Is authentication provided but invalid?
│        ├─ YES → AuthenticationFailed (401)
│        └─ NO → NotAuthenticated (401)
│
└─ YES → Does the user have permission?
         ├─ NO → PermissionDenied (403)
         │
         └─ YES → Does the resource exist?
                  ├─ NO → NotFound (404)
                  │
                  └─ YES → Is the request method allowed?
                           ├─ NO → MethodNotAllowed (405)
                           │
                           └─ YES → Is the request data valid?
                                    ├─ NO → ValidationError (400)
                                    │
                                    └─ YES → Is the request properly formatted?
                                             ├─ NO → ParseError (400)
                                             │
                                             └─ YES → Is the rate limit exceeded?
                                                      ├─ YES → Throttled (429)
                                                      │
                                                      └─ NO → Is media type supported?
                                                               ├─ NO → UnsupportedMediaType (415)
                                                               │
                                                               └─ YES → Is Accept header satisfiable?
                                                                        ├─ NO → NotAcceptable (406)
                                                                        └─ YES → Process request normally
```

### Exception Type Reference

| Exception | Status Code | When to Use |
|-----------|-------------|-------------|
| `ValidationError` | 400 | Invalid input data, failed validation |
| `ParseError` | 400 | Malformed JSON/XML, parsing failure |
| `AuthenticationFailed` | 401 | Invalid credentials, expired token |
| `NotAuthenticated` | 401 | No authentication provided |
| `PermissionDenied` | 403 | User lacks required permissions |
| `NotFound` | 404 | Resource doesn't exist |
| `MethodNotAllowed` | 405 | HTTP method not supported for endpoint |
| `NotAcceptable` | 406 | Can't satisfy Accept header |
| `UnsupportedMediaType` | 415 | Content-Type not supported |
| `Throttled` | 429 | Rate limit exceeded |
| `APIException` | 500 | Generic server error (base class) |

## Common Mistakes

### 1. Using the Wrong Exception for Validation

**Wrong:**
```python
# Don't use generic APIException for validation errors
if not email_valid(data['email']):
    raise APIException("Invalid email")  # Returns 500!
```

**Right:**
```python
from rest_framework.exceptions import ValidationError

if not email_valid(data['email']):
    raise ValidationError({'email': 'Enter a valid email address'})
```

### 2. Not Providing Structured Error Details

**Wrong:**
```python
# String errors are hard for clients to parse
raise ValidationError("Email is invalid and username is too short")
```

**Right:**
```python
# Use dictionaries for field-specific errors
raise ValidationError({
    'email': 'Enter a valid email address',
    'username': 'Username must be at least 3 characters'
})
```

### 3. Forgetting Error Codes

**Wrong:**
```python
raise ValidationError("Invalid value")  # No error code
```

**Right:**
```python
from rest_framework.exceptions import ErrorDetail

raise ValidationError({
    'field': ErrorDetail('Invalid value', code='invalid_format')
})

# Or set default_code in custom exceptions
class CustomError(APIException):
    default_code = 'custom_error'
```

### 4. Not Returning None for Unhandled Exceptions

**Wrong:**
```python
def custom_exception_handler(exc, context):
    response = exception_handler(exc, context)
    # Always modifying response without checking if it's None
    response.data['custom'] = 'field'  # Crashes on unhandled exceptions!
    return response
```

**Right:**
```python
def custom_exception_handler(exc, context):
    response = exception_handler(exc, context)

    if response is not None:
        response.data['custom'] = 'field'

    return response  # Returns None for unhandled exceptions
```

### 5. Catching and Re-raising Without Context

**Wrong:**
```python
try:
    external_service.call()
except Exception as e:
    raise APIException("Service error")  # Lost original error!
```

**Right:**
```python
import logging
logger = logging.getLogger(__name__)

try:
    external_service.call()
except Exception as e:
    logger.exception("External service failed")
    raise ServiceUnavailable(
        f"External service error: {str(e)}"
    )
```

### 6. Not Using get_full_details() for Debugging

**Wrong:**
```python
# Only getting string details
try:
    serializer.is_valid(raise_exception=True)
except ValidationError as e:
    print(e.detail)  # Just the message
```

**Right:**
```python
try:
    serializer.is_valid(raise_exception=True)
except ValidationError as e:
    # Get full details including codes
    print(e.get_full_details())
    # {'field': [{'message': 'This field is required.', 'code': 'required'}]}
```

## Reference Documentation

- [Built-in Exceptions](./reference/builtin-exceptions.md) - Complete guide to all DRF exception classes
- [Custom Exceptions](./reference/custom-exceptions.md) - Creating and using custom exception types
- [Exception Handlers](./reference/exception-handlers.md) - Implementing custom exception handlers
- [Error Responses](./reference/error-responses.md) - Formatting and structuring error responses
- [Error Patterns](./reference/examples/error-patterns.py) - Working code examples

## Key Files in DRF Source

- `/home/user/django-rest-framework/rest_framework/exceptions.py` - All exception classes and error handling utilities
- `/home/user/django-rest-framework/rest_framework/views.py` - Default exception_handler implementation

## Related Skills

- **Serializers** - Understanding serializer validation and ValidationError
- **Views** - Implementing error handling in APIView and ViewSet classes
- **Authentication** - Working with authentication-related exceptions
- **Permissions** - Using PermissionDenied appropriately

## Next Steps

1. Read through [Built-in Exceptions](./reference/builtin-exceptions.md) to understand all available exception types
2. Review [Error Patterns](./reference/examples/error-patterns.py) for real-world examples
3. Implement a custom exception handler following [Exception Handlers](./reference/exception-handlers.md)
4. Study [Error Responses](./reference/error-responses.md) to format consistent API errors

## Pro Tips

- Always use specific exceptions instead of generic APIException
- Include error codes for programmatic error handling by clients
- Log exceptions with proper context for debugging
- Use structured error details (dicts/lists) for complex validations
- Test exception handling with unit tests and integration tests
- Document expected error responses in API documentation
- Consider internationalization (i18n) for error messages
- Add request IDs to error responses for tracking
- Use HTTP status codes correctly - they matter for API clients
- Implement exponential backoff hints for Throttled exceptions
