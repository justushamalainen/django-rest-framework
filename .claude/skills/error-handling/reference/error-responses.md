# Error Response Formatting

Learn how to structure, format, and debug error responses in Django REST Framework for better API usability and debugging.

## Table of Contents

- [Default Error Response Format](#default-error-response-format)
- [Error Response Structure](#error-response-structure)
- [Error Codes](#error-codes)
- [Field-Level Errors](#field-level-errors)
- [Non-Field Errors](#non-field-errors)
- [Nested Error Structures](#nested-error-structures)
- [Response Headers](#response-headers)
- [Debugging Error Responses](#debugging-error-responses)
- [Client-Side Error Handling](#client-side-error-handling)

## Default Error Response Format

DRF's default exception handler formats errors in a simple structure:

### Simple Error

```json
{
  "detail": "Not found."
}
```

### Field Errors

```json
{
  "email": ["Enter a valid email address"],
  "username": ["This field is required"]
}
```

### List Errors

```json
[
  "Error message 1",
  "Error message 2"
]
```

## Error Response Structure

### Standard Fields

Common fields in error responses:

| Field | Type | Description |
|-------|------|-------------|
| `detail` | string | Main error message |
| `code` | string | Machine-readable error code |
| `status` | integer | HTTP status code |
| `field_name` | array | Field-specific errors |

### Structured Error Format

```python
# Recommended structure for consistent errors
{
    "error": {
        "code": "validation_error",
        "message": "Invalid input data",
        "status": 400,
        "timestamp": "2024-01-15T10:30:00Z",
        "path": "/api/users/",
        "details": {
            "email": ["Enter a valid email address"],
            "age": ["Ensure this value is greater than or equal to 18"]
        }
    }
}
```

### Implementing Structured Format

```python
# myapp/exception_handlers.py
from rest_framework.views import exception_handler
from datetime import datetime

def structured_exception_handler(exc, context):
    response = exception_handler(exc, context)

    if response is not None:
        request = context.get('request')

        # Build structured error response
        error_data = {
            'error': {
                'code': getattr(exc, 'default_code', 'error'),
                'message': str(exc.detail) if not isinstance(exc.detail, (dict, list)) else 'Validation failed',
                'status': response.status_code,
                'timestamp': datetime.utcnow().isoformat() + 'Z',
                'path': request.path if request else None,
            }
        }

        # Add details if error is structured
        if isinstance(exc.detail, (dict, list)):
            error_data['error']['details'] = exc.detail

        # Add request ID if available
        if request and hasattr(request, 'id'):
            error_data['error']['request_id'] = request.id

        response.data = error_data

    return response
```

## Error Codes

Error codes enable programmatic error handling by API clients.

### Using Built-in Error Codes

```python
from rest_framework.exceptions import ValidationError, ErrorDetail

# Single error with code
raise ValidationError(
    ErrorDetail('Invalid email format', code='invalid_email')
)

# Field errors with codes
raise ValidationError({
    'email': ErrorDetail('Invalid email format', code='invalid_email'),
    'age': ErrorDetail('Must be 18 or older', code='min_age')
})

# Response:
# {
#     "email": ["Invalid email format"],
#     "age": ["Must be 18 or older"]
# }

# Get codes programmatically
try:
    # ... validation ...
except ValidationError as e:
    codes = e.get_codes()
    # {'email': ['invalid_email'], 'age': ['min_age']}
```

### Custom Error Codes

```python
# Define custom codes for your domain
class UserValidationCodes:
    INVALID_EMAIL = 'user.email.invalid'
    EMAIL_TAKEN = 'user.email.taken'
    PASSWORD_WEAK = 'user.password.weak'
    USERNAME_TAKEN = 'user.username.taken'
    AGE_TOO_YOUNG = 'user.age.too_young'

# Use in validation
from rest_framework.exceptions import ValidationError, ErrorDetail

def validate_user_registration(data):
    errors = {}

    # Email validation
    if not is_valid_email(data['email']):
        errors['email'] = ErrorDetail(
            'Enter a valid email address',
            code=UserValidationCodes.INVALID_EMAIL
        )
    elif User.objects.filter(email=data['email']).exists():
        errors['email'] = ErrorDetail(
            'This email is already registered',
            code=UserValidationCodes.EMAIL_TAKEN
        )

    # Password validation
    if not is_strong_password(data['password']):
        errors['password'] = ErrorDetail(
            'Password must contain uppercase, lowercase, digit, and special character',
            code=UserValidationCodes.PASSWORD_WEAK
        )

    # Age validation
    if data.get('age', 0) < 18:
        errors['age'] = ErrorDetail(
            'You must be at least 18 years old',
            code=UserValidationCodes.AGE_TOO_YOUNG
        )

    if errors:
        raise ValidationError(errors)
```

### Error Code Hierarchy

```python
# Organize codes hierarchically
class ErrorCodes:
    # Authentication
    AUTH_REQUIRED = 'auth.required'
    AUTH_INVALID = 'auth.invalid'
    AUTH_EXPIRED = 'auth.expired'

    # Authorization
    PERMISSION_DENIED = 'permission.denied'
    PERMISSION_INSUFFICIENT = 'permission.insufficient'

    # Validation
    VALIDATION_REQUIRED = 'validation.required'
    VALIDATION_INVALID = 'validation.invalid'
    VALIDATION_MIN_LENGTH = 'validation.min_length'
    VALIDATION_MAX_LENGTH = 'validation.max_length'

    # Resources
    RESOURCE_NOT_FOUND = 'resource.not_found'
    RESOURCE_CONFLICT = 'resource.conflict'
    RESOURCE_LOCKED = 'resource.locked'

    # Business logic
    BUSINESS_RULE_VIOLATION = 'business.rule_violation'
    INSUFFICIENT_FUNDS = 'business.insufficient_funds'
    QUOTA_EXCEEDED = 'business.quota_exceeded'

# Expose in API responses
{
    "error": {
        "code": "validation.invalid",
        "message": "Invalid input",
        "details": {
            "email": {
                "message": "Invalid email format",
                "code": "validation.invalid"
            }
        }
    }
}
```

## Field-Level Errors

### Single Field Error

```python
from rest_framework.exceptions import ValidationError

# Simple field error
raise ValidationError({
    'email': 'Enter a valid email address'
})

# Response:
# {
#     "email": ["Enter a valid email address"]
# }
```

### Multiple Errors Per Field

```python
# Multiple errors for one field
raise ValidationError({
    'password': [
        'Password must be at least 8 characters',
        'Password must contain at least one digit',
        'Password must contain at least one uppercase letter'
    ]
})

# Response:
# {
#     "password": [
#         "Password must be at least 8 characters",
#         "Password must contain at least one digit",
#         "Password must contain at least one uppercase letter"
#     ]
# }
```

### Multiple Field Errors

```python
# Errors across multiple fields
raise ValidationError({
    'email': 'Enter a valid email address',
    'username': 'Username is already taken',
    'password': 'Password is too weak',
    'age': 'Must be at least 18 years old'
})

# Response:
# {
#     "email": ["Enter a valid email address"],
#     "username": ["Username is already taken"],
#     "password": ["Password is too weak"],
#     "age": ["Must be at least 18 years old"]
# }
```

### Field Errors with Metadata

```python
# Add metadata to field errors
from rest_framework.exceptions import ValidationError

errors = {
    'username': {
        'message': 'Username must be 3-20 characters',
        'code': 'invalid_length',
        'min_length': 3,
        'max_length': 20,
        'current_length': len(username)
    },
    'email': {
        'message': 'Email domain is not allowed',
        'code': 'invalid_domain',
        'allowed_domains': ['example.com', 'example.org']
    }
}

raise ValidationError(errors)
```

## Non-Field Errors

Non-field errors apply to the entire object, not a specific field:

```python
from rest_framework.exceptions import ValidationError

# Using NON_FIELD_ERRORS key
from rest_framework.exceptions import ValidationError
from rest_framework import serializers

raise ValidationError({
    serializers.NON_FIELD_ERRORS: [
        'Start date must be before end date'
    ]
})

# Response:
# {
#     "non_field_errors": ["Start date must be before end date"]
# }

# In serializers
class EventSerializer(serializers.Serializer):
    start_date = serializers.DateField()
    end_date = serializers.DateField()

    def validate(self, data):
        if data['start_date'] > data['end_date']:
            raise ValidationError({
                serializers.NON_FIELD_ERRORS: [
                    'Start date must be before end date'
                ]
            })
        return data
```

### List Errors (Non-Field)

```python
# Simple list of errors
raise ValidationError([
    'Operation failed',
    'Insufficient permissions',
    'Resource is locked'
])

# Response:
# [
#     "Operation failed",
#     "Insufficient permissions",
#     "Resource is locked"
# ]
```

## Nested Error Structures

### Nested Field Errors

```python
# Errors in nested serializers
raise ValidationError({
    'profile': {
        'bio': 'Bio must be less than 500 characters',
        'avatar_url': 'Enter a valid URL'
    },
    'address': {
        'zip_code': 'Enter a valid ZIP code',
        'country': 'This field is required'
    }
})

# Response:
# {
#     "profile": {
#         "bio": ["Bio must be less than 500 characters"],
#         "avatar_url": ["Enter a valid URL"]
#     },
#     "address": {
#         "zip_code": ["Enter a valid ZIP code"],
#         "country": ["This field is required"]
#     }
# }
```

### List Item Errors

```python
# Errors in list items
raise ValidationError({
    'items': {
        0: {'quantity': 'Must be greater than 0'},
        2: {'price': 'Invalid price format'}
    }
})

# Response:
# {
#     "items": {
#         "0": {
#             "quantity": ["Must be greater than 0"]
#         },
#         "2": {
#             "price": ["Invalid price format"]
#         }
#     }
# }
```

### Complex Nested Structure

```python
# Real-world example: Order validation
raise ValidationError({
    'customer': {
        'email': 'Enter a valid email address'
    },
    'items': {
        0: {
            'product_id': 'Product not found',
            'quantity': 'Must be at least 1'
        },
        1: {
            'quantity': 'Insufficient stock'
        }
    },
    'shipping_address': {
        'street': 'This field is required',
        'zip_code': 'Invalid ZIP code format'
    },
    serializers.NON_FIELD_ERRORS: [
        'Total amount must be at least $10'
    ]
})
```

## Response Headers

### Standard Headers

DRF automatically sets appropriate headers based on exception type:

#### WWW-Authenticate (401 Unauthorized)

```python
from rest_framework.exceptions import AuthenticationFailed

exc = AuthenticationFailed('Invalid token')
exc.auth_header = 'Bearer realm="api", error="invalid_token"'
raise exc

# Response headers:
# HTTP/1.1 401 Unauthorized
# WWW-Authenticate: Bearer realm="api", error="invalid_token"
# Content-Type: application/json
```

#### Retry-After (429 Too Many Requests)

```python
from rest_framework.exceptions import Throttled

raise Throttled(wait=60)  # Wait 60 seconds

# Response headers:
# HTTP/1.1 429 Too Many Requests
# Retry-After: 60
# Content-Type: application/json
```

### Custom Headers in Exception Handler

```python
def custom_exception_handler(exc, context):
    response = exception_handler(exc, context)

    if response is not None:
        # Add custom headers
        response['X-Error-Code'] = getattr(exc, 'default_code', 'error')

        # Add request ID
        if hasattr(context['request'], 'id'):
            response['X-Request-ID'] = context['request'].id

        # Add rate limit info for throttled requests
        if response.status_code == 429:
            response['X-RateLimit-Limit'] = '100'
            response['X-RateLimit-Remaining'] = '0'
            response['X-RateLimit-Reset'] = str(int(time.time()) + 3600)

    return response
```

## Debugging Error Responses

### Getting Full Error Details

```python
from rest_framework.exceptions import ValidationError

try:
    serializer.is_valid(raise_exception=True)
except ValidationError as e:
    # Get simple string representation
    print(e.detail)
    # {'email': [ErrorDetail(string='Invalid email', code='invalid')]}

    # Get only error codes
    print(e.get_codes())
    # {'email': ['invalid']}

    # Get full details with messages and codes
    print(e.get_full_details())
    # {'email': [{'message': 'Invalid email', 'code': 'invalid'}]}
```

### Debug Mode Error Responses

```python
from django.conf import settings
from rest_framework.views import exception_handler
import traceback

def debug_exception_handler(exc, context):
    response = exception_handler(exc, context)

    if settings.DEBUG and response is not None:
        # Add debug information
        response.data['debug'] = {
            'exception_type': exc.__class__.__name__,
            'exception_module': exc.__class__.__module__,
            'view': context['view'].__class__.__name__,
            'view_method': getattr(context['view'], 'action', None),
        }

        # Add traceback for unhandled exceptions
        if response.status_code == 500:
            response.data['debug']['traceback'] = traceback.format_exc()

    return response

# Debug response:
# {
#     "detail": "Not found.",
#     "debug": {
#         "exception_type": "NotFound",
#         "exception_module": "rest_framework.exceptions",
#         "view": "UserViewSet",
#         "view_method": "retrieve"
#     }
# }
```

### Logging Error Details

```python
import logging
from rest_framework.views import exception_handler

logger = logging.getLogger(__name__)

def logged_exception_handler(exc, context):
    response = exception_handler(exc, context)

    if response is not None:
        # Build log message
        request = context.get('request')
        log_data = {
            'exception_type': exc.__class__.__name__,
            'status_code': response.status_code,
            'path': request.path if request else None,
            'method': request.method if request else None,
            'user': getattr(request.user, 'id', None) if request else None,
        }

        # Log error details
        if response.status_code >= 500:
            logger.error(
                f"Server error: {exc}",
                extra=log_data,
                exc_info=True
            )
        elif response.status_code >= 400:
            logger.warning(
                f"Client error: {exc}",
                extra=log_data
            )

            # Log full error details for validation errors
            if hasattr(exc, 'get_full_details'):
                logger.debug(
                    f"Validation details: {exc.get_full_details()}"
                )

    return response
```

### Error Response Testing

```python
from rest_framework.test import APITestCase
from rest_framework import status

class ErrorResponseTests(APITestCase):
    def test_validation_error_structure(self):
        """Test validation error response structure."""
        response = self.client.post('/api/users/', {
            'email': 'invalid',
            'age': -5
        })

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

        # Check error structure
        self.assertIn('email', response.data)
        self.assertIn('age', response.data)

        # Check error messages
        self.assertIsInstance(response.data['email'], list)
        self.assertIsInstance(response.data['age'], list)

    def test_error_codes_present(self):
        """Test that error codes are included."""
        response = self.client.post('/api/users/', {'email': 'invalid'})

        # Parse error to get codes
        from rest_framework.exceptions import ErrorDetail
        if isinstance(response.data['email'][0], ErrorDetail):
            self.assertIsNotNone(response.data['email'][0].code)

    def test_not_found_error(self):
        """Test 404 error response."""
        response = self.client.get('/api/users/999999/')

        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
        self.assertIn('detail', response.data)
```

## Client-Side Error Handling

### JavaScript/TypeScript Example

```typescript
// Type definitions
interface ApiError {
    error: {
        code: string;
        message: string;
        status: number;
        details?: Record<string, string[]>;
        timestamp?: string;
        request_id?: string;
    };
}

// Error handling function
async function apiCall(url: string, options: RequestInit): Promise<any> {
    try {
        const response = await fetch(url, options);

        if (!response.ok) {
            const error: ApiError = await response.json();

            // Handle specific error codes
            switch (error.error.code) {
                case 'not_authenticated':
                    // Redirect to login
                    window.location.href = '/login';
                    break;

                case 'validation_error':
                    // Display field errors
                    if (error.error.details) {
                        Object.entries(error.error.details).forEach(([field, messages]) => {
                            displayFieldError(field, messages[0]);
                        });
                    }
                    break;

                case 'throttled':
                    // Get retry-after header
                    const retryAfter = response.headers.get('Retry-After');
                    showMessage(`Rate limited. Retry in ${retryAfter} seconds.`);
                    break;

                default:
                    // Generic error
                    showMessage(error.error.message);
            }

            throw error;
        }

        return await response.json();
    } catch (error) {
        console.error('API Error:', error);
        throw error;
    }
}
```

### Python Client Example

```python
import requests
from typing import Dict, Any

class APIError(Exception):
    """Base API error."""
    def __init__(self, response: requests.Response):
        self.response = response
        self.status_code = response.status_code
        self.error_data = response.json() if response.content else {}

        # Extract error details
        if 'error' in self.error_data:
            self.code = self.error_data['error'].get('code')
            self.message = self.error_data['error'].get('message')
            self.details = self.error_data['error'].get('details')
        else:
            self.code = None
            self.message = self.error_data.get('detail', 'Unknown error')
            self.details = None

        super().__init__(self.message)

class APIClient:
    def __init__(self, base_url: str, token: str = None):
        self.base_url = base_url
        self.token = token

    def request(self, method: str, endpoint: str, **kwargs) -> Dict[Any, Any]:
        """Make API request with error handling."""
        url = f"{self.base_url}{endpoint}"

        headers = kwargs.pop('headers', {})
        if self.token:
            headers['Authorization'] = f'Bearer {self.token}'

        response = requests.request(method, url, headers=headers, **kwargs)

        # Handle errors
        if not response.ok:
            error = APIError(response)

            # Handle specific error codes
            if error.code == 'not_authenticated':
                raise AuthenticationError(response)
            elif error.code == 'permission_denied':
                raise PermissionError(response)
            elif error.code == 'validation_error':
                raise ValidationError(response)
            elif error.code == 'throttled':
                retry_after = response.headers.get('Retry-After')
                raise RateLimitError(response, retry_after=retry_after)
            else:
                raise error

        return response.json()

# Usage
client = APIClient('https://api.example.com', token='your-token')

try:
    user = client.request('POST', '/api/users/', json={
        'email': 'user@example.com',
        'username': 'johndoe'
    })
except ValidationError as e:
    print(f"Validation failed: {e.details}")
except RateLimitError as e:
    print(f"Rate limited. Retry in {e.retry_after} seconds")
```

## Best Practices

1. **Use consistent error structure** across all endpoints
2. **Include error codes** for programmatic handling
3. **Provide helpful messages** that guide users to fix issues
4. **Don't expose sensitive information** in error messages
5. **Use appropriate HTTP status codes** (400, 401, 403, 404, etc.)
6. **Include request IDs** for debugging and support
7. **Log errors with context** for debugging
8. **Document error responses** in API documentation
9. **Test error scenarios** thoroughly
10. **Consider internationalization** for error messages

## Anti-Patterns to Avoid

### Don't Use Generic Error Messages

```python
# Bad
raise ValidationError("Invalid data")

# Good
raise ValidationError({
    'email': 'Enter a valid email address',
    'password': 'Password must be at least 8 characters'
})
```

### Don't Expose Internal Details

```python
# Bad
raise APIException(f"Database error: {db_exception}")

# Good
logger.exception(f"Database error: {db_exception}")
raise ServiceUnavailable("Service temporarily unavailable")
```

### Don't Use Wrong Status Codes

```python
# Bad
raise APIException("User not found")  # Returns 500!

# Good
raise NotFound("User not found")  # Returns 404
```

## Related Documentation

- [Built-in Exceptions](./builtin-exceptions.md)
- [Custom Exceptions](./custom-exceptions.md)
- [Exception Handlers](./exception-handlers.md)
- [Error Patterns](./examples/error-patterns.py)

## Source Reference

- `/home/user/django-rest-framework/rest_framework/exceptions.py` - Exception classes and ErrorDetail
- `/home/user/django-rest-framework/rest_framework/views.py` - Default exception handler
