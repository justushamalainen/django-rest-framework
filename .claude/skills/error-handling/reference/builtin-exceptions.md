# Built-in DRF Exceptions

Django REST Framework provides exception classes for common API errors. **Most of the time, you only need ValidationError, NotFound, and PermissionDenied.**

## The Workhorse: ValidationError (400)

**ValidationError is your go-to exception for 80% of error scenarios.** Use it whenever request data is invalid.

### Properties

```python
status_code = 400
default_detail = 'Invalid input.'
default_code = 'invalid'
```

### Basic Usage

```python
from rest_framework.exceptions import ValidationError

# Single error message
raise ValidationError("Invalid data provided")
# Response: {"detail": "Invalid data provided"}

# Field-specific errors (RECOMMENDED)
raise ValidationError({
    'email': 'Enter a valid email address',
    'username': 'This username is already taken'
})
# Response: {
#   "email": ["Enter a valid email address"],
#   "username": ["This username is already taken"]
# }

# Multiple errors for one field
raise ValidationError({
    'password': ['Password too short', 'Must contain a number']
})

# Non-field errors (use list)
raise ValidationError(['Error 1', 'Error 2'])
```

### With Error Codes

Error codes help clients handle errors programmatically:

```python
from rest_framework.exceptions import ErrorDetail

raise ValidationError({
    'email': ErrorDetail('Invalid email format', code='invalid_email'),
    'age': ErrorDetail('Must be 18 or older', code='min_age')
})
```

### In Serializers

ValidationError integrates seamlessly with serializers:

```python
from rest_framework import serializers
from rest_framework.exceptions import ValidationError

class UserSerializer(serializers.Serializer):
    email = serializers.EmailField()
    age = serializers.IntegerField()

    def validate_email(self, value):
        """Field-level validation."""
        if User.objects.filter(email=value).exists():
            raise ValidationError("Email already registered")
        return value

    def validate(self, data):
        """Object-level validation."""
        if data['age'] < 18:
            raise ValidationError({
                'age': 'Must be 18 or older'
            })
        return data

# In view
serializer = UserSerializer(data=request.data)
if not serializer.is_valid():
    # Returns ValidationError automatically
    raise ValidationError(serializer.errors)

# Or simpler:
serializer.is_valid(raise_exception=True)  # Auto-raises ValidationError
```

### Real-World Patterns

```python
from rest_framework.decorators import api_view
from rest_framework.exceptions import ValidationError

@api_view(['POST'])
def create_post(request):
    """Example showing common validation patterns."""
    errors = {}

    # Required fields
    if not request.data.get('title'):
        errors['title'] = 'This field is required'

    # Length validation
    title = request.data.get('title', '')
    if len(title) > 200:
        errors['title'] = 'Title too long (max 200 characters)'

    # Format validation
    email = request.data.get('author_email', '')
    if email and '@' not in email:
        errors['author_email'] = 'Enter a valid email address'

    # Range validation
    priority = request.data.get('priority', 0)
    if priority < 1 or priority > 10:
        errors['priority'] = 'Priority must be between 1 and 10'

    # Uniqueness validation
    slug = request.data.get('slug', '')
    if slug and Post.objects.filter(slug=slug).exists():
        errors['slug'] = 'This slug is already taken'

    # Raise all errors at once
    if errors:
        raise ValidationError(errors)

    # Create post...
    return Response({'id': post.id}, status=201)
```

### Debugging ValidationErrors

```python
try:
    serializer.is_valid(raise_exception=True)
except ValidationError as e:
    # Get error codes
    print(e.get_codes())
    # {'email': ['invalid']}

    # Get full details
    print(e.get_full_details())
    # {'email': [{'message': 'Enter a valid email address.', 'code': 'invalid'}]}
```

## NotFound (404)

Use when a requested resource doesn't exist.

```python
from rest_framework.exceptions import NotFound

@api_view(['GET'])
def get_article(request, article_id):
    try:
        article = Article.objects.get(id=article_id)
    except Article.DoesNotExist:
        raise NotFound('Article not found')

    return Response(ArticleSerializer(article).data)

# Django's Http404 also works (auto-converted)
from django.shortcuts import get_object_or_404

article = get_object_or_404(Article, id=article_id)  # Raises NotFound if not exists
```

**Properties:**
```python
status_code = 404
default_detail = 'Not found.'
default_code = 'not_found'
```

**Response:**
```json
{"detail": "Not found."}
```

## PermissionDenied (403)

Use when an authenticated user lacks permission.

```python
from rest_framework.exceptions import PermissionDenied

@api_view(['DELETE'])
def delete_post(request, post_id):
    post = get_object_or_404(Post, id=post_id)

    if post.author != request.user:
        raise PermissionDenied('Only the author can delete this post')

    post.delete()
    return Response(status=204)
```

**Properties:**
```python
status_code = 403
default_detail = 'You do not have permission to perform this action.'
default_code = 'permission_denied'
```

## NotAuthenticated (401)

Use when authentication is required but not provided. Usually auto-handled by authentication classes.

```python
from rest_framework.exceptions import NotAuthenticated

@api_view(['POST'])
def create_post(request):
    if not request.user.is_authenticated:
        raise NotAuthenticated('Login required to create posts')

    # Create post...
```

**Properties:**
```python
status_code = 401
default_detail = 'Authentication credentials were not provided.'
default_code = 'not_authenticated'
```

## Other Exceptions (Auto-Handled)

These are automatically raised by DRF - you rarely raise them manually:

### AuthenticationFailed (401)
Raised by authentication classes when credentials are invalid.
```python
from rest_framework.exceptions import AuthenticationFailed
# Usually raised by authentication classes, not views
```

### Throttled (429)
Raised by throttle classes when rate limit is exceeded.
```python
from rest_framework.exceptions import Throttled
# Auto-raised by DRF's throttling system
# Includes Retry-After header
```

### ParseError (400)
Raised by parsers when request data is malformed.
```python
from rest_framework.exceptions import ParseError
# Auto-raised when JSON/XML parsing fails
```

### MethodNotAllowed (405)
Raised when HTTP method is not supported.
```python
# Auto-raised by DRF when method not in allowed_methods
```

### NotAcceptable (406)
Raised when Accept header cannot be satisfied.
```python
# Auto-raised by content negotiation
```

### UnsupportedMediaType (415)
Raised when Content-Type is not supported.
```python
# Auto-raised by parser selection
```

## Base Class: APIException

All DRF exceptions inherit from `APIException`. You can create custom exceptions:

```python
from rest_framework.exceptions import APIException
from rest_framework import status

class ServiceUnavailable(APIException):
    status_code = status.HTTP_503_SERVICE_UNAVAILABLE
    default_detail = 'Service temporarily unavailable.'
    default_code = 'service_unavailable'

# Usage
raise ServiceUnavailable('Payment service is down')
```

## Django Exception Compatibility

DRF automatically converts Django exceptions:

```python
from django.http import Http404
from django.core.exceptions import PermissionDenied

# These are auto-converted to DRF exceptions:
raise Http404()  # → NotFound (404)
raise PermissionDenied()  # → PermissionDenied (403)
```

## ErrorDetail Class

All exception details are wrapped in `ErrorDetail` for consistent handling:

```python
from rest_framework.exceptions import ErrorDetail

error = ErrorDetail('Invalid value', code='invalid')
str(error)  # 'Invalid value'
error.code  # 'invalid'
```

## Summary Table

| Exception | Status | When to Use | Auto-Handled? |
|-----------|--------|-------------|---------------|
| **ValidationError** | 400 | Invalid input data | No - You raise it |
| **NotFound** | 404 | Resource doesn't exist | No - You raise it |
| **PermissionDenied** | 403 | User lacks permission | No - You raise it |
| NotAuthenticated | 401 | No authentication | Often auto-handled |
| AuthenticationFailed | 401 | Invalid credentials | Auto-handled |
| Throttled | 429 | Rate limited | Auto-handled |
| ParseError | 400 | Malformed data | Auto-handled |
| MethodNotAllowed | 405 | Wrong HTTP method | Auto-handled |
| NotAcceptable | 406 | Can't satisfy Accept | Auto-handled |
| UnsupportedMediaType | 415 | Wrong Content-Type | Auto-handled |

## Best Practices

1. **Use ValidationError for all input validation** - It's designed for this
2. **Use field-specific error dicts** - Better UX for clients
3. **Include helpful error messages** - Tell users how to fix the issue
4. **Don't expose sensitive info** - Keep error messages safe
5. **Use Django shortcuts** - `get_object_or_404()` is your friend
6. **Let DRF handle the rest** - Don't manually raise auto-handled exceptions

## Source Files

- `/home/user/django-rest-framework/rest_framework/exceptions.py` - All exception classes
- `/home/user/django-rest-framework/rest_framework/views.py` - Default exception handler
