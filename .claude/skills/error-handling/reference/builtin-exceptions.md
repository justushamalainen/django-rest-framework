# Built-in DRF Exceptions

Django REST Framework provides a comprehensive set of exception classes for handling common API error scenarios. All exceptions inherit from `APIException` and return appropriate HTTP status codes.

## Exception Hierarchy

```
Exception (Python base)
└── APIException (DRF base)
    ├── ValidationError
    ├── ParseError
    ├── AuthenticationFailed
    ├── NotAuthenticated
    ├── PermissionDenied
    ├── NotFound
    ├── MethodNotAllowed
    ├── NotAcceptable
    ├── UnsupportedMediaType
    └── Throttled
```

## Base Exception: APIException

All DRF exceptions inherit from `APIException`.

### Properties

```python
class APIException(Exception):
    status_code = 500  # HTTP status code
    default_detail = 'A server error occurred.'
    default_code = 'error'
```

### Constructor

```python
APIException(detail=None, code=None)
```

- `detail`: Error message (string, dict, or list)
- `code`: Error code for programmatic handling

### Methods

```python
# Get error codes only
exc.get_codes()
# Example: {'field': ['required']}

# Get full details with messages and codes
exc.get_full_details()
# Example: {'field': [{'message': 'This field is required.', 'code': 'required'}]}
```

### Usage

```python
from rest_framework.exceptions import APIException

# Basic usage
raise APIException("Something went wrong")

# With custom code
raise APIException("Custom error", code='custom_error')

# With structured detail
raise APIException({
    'error': 'Operation failed',
    'reason': 'Insufficient resources'
})
```

## ValidationError (400 Bad Request)

Used for invalid input data and validation failures. This is the most commonly used exception.

### Properties

```python
status_code = 400
default_detail = 'Invalid input.'
default_code = 'invalid'
```

### Key Features

- Automatically coerces detail to a list if not already a dict or list
- Integrates seamlessly with serializer validation
- Supports field-level and non-field errors

### Usage Examples

```python
from rest_framework.exceptions import ValidationError

# Single error
raise ValidationError("Invalid data provided")

# Field-specific errors
raise ValidationError({
    'email': 'Enter a valid email address',
    'username': 'This username is already taken'
})

# List errors (for non-field errors)
raise ValidationError(['Error 1', 'Error 2'])

# With error codes
from rest_framework.exceptions import ErrorDetail

raise ValidationError({
    'email': ErrorDetail('Invalid email format', code='invalid_email'),
    'age': ErrorDetail('Must be 18 or older', code='min_age')
})

# In serializers
class UserSerializer(serializers.Serializer):
    email = serializers.EmailField()

    def validate_email(self, value):
        if User.objects.filter(email=value).exists():
            raise ValidationError("Email already registered")
        return value

    def validate(self, data):
        if data['password'] != data['password_confirm']:
            raise ValidationError({
                'password_confirm': 'Passwords do not match'
            })
        return data
```

### Response Format

```json
{
  "email": ["Enter a valid email address"],
  "username": ["This username is already taken"]
}
```

## ParseError (400 Bad Request)

Raised when request data cannot be parsed (malformed JSON, XML, etc.).

### Properties

```python
status_code = 400
default_detail = 'Malformed request.'
default_code = 'parse_error'
```

### Usage

```python
from rest_framework.exceptions import ParseError

# In custom parser
class CustomParser:
    def parse(self, stream, media_type=None, parser_context=None):
        try:
            data = json.loads(stream.read())
        except json.JSONDecodeError as e:
            raise ParseError(f"Invalid JSON: {e}")
        return data

# In view
@api_view(['POST'])
def process_data(request):
    if not isinstance(request.data, dict):
        raise ParseError("Expected JSON object, got array")
    # Process data...
```

### Response Format

```json
{
  "detail": "Malformed request."
}
```

## AuthenticationFailed (401 Unauthorized)

Raised when authentication credentials are provided but are invalid.

### Properties

```python
status_code = 401
default_detail = 'Incorrect authentication credentials.'
default_code = 'authentication_failed'
```

### Usage

```python
from rest_framework.exceptions import AuthenticationFailed

# In custom authentication
class CustomTokenAuth(BaseAuthentication):
    def authenticate(self, request):
        token = request.headers.get('Authorization')

        if not token:
            return None  # No auth attempted

        try:
            user = self.validate_token(token)
        except InvalidToken:
            raise AuthenticationFailed('Invalid or expired token')

        return (user, token)

# In view
@api_view(['GET'])
def protected_view(request):
    if not request.user.is_verified:
        raise AuthenticationFailed('Email verification required')
    # Process request...
```

### Response Format

```json
{
  "detail": "Incorrect authentication credentials."
}
```

### Headers

May include `WWW-Authenticate` header:

```python
exc = AuthenticationFailed()
exc.auth_header = 'Bearer realm="api"'
raise exc
```

## NotAuthenticated (401 Unauthorized)

Raised when authentication is required but not provided.

### Properties

```python
status_code = 401
default_detail = 'Authentication credentials were not provided.'
default_code = 'not_authenticated'
```

### Usage

```python
from rest_framework.exceptions import NotAuthenticated

# In custom permission
class IsAuthenticated(BasePermission):
    def has_permission(self, request, view):
        if not request.user or not request.user.is_authenticated:
            raise NotAuthenticated()
        return True

# In view
@api_view(['POST'])
def create_post(request):
    if not request.user.is_authenticated:
        raise NotAuthenticated('Login required to create posts')
    # Process request...
```

### Response Format

```json
{
  "detail": "Authentication credentials were not provided."
}
```

## PermissionDenied (403 Forbidden)

Raised when an authenticated user lacks permission to perform an action.

### Properties

```python
status_code = 403
default_detail = 'You do not have permission to perform this action.'
default_code = 'permission_denied'
```

### Usage

```python
from rest_framework.exceptions import PermissionDenied

# In custom permission
class IsOwnerOrReadOnly(BasePermission):
    def has_object_permission(self, request, view, obj):
        if request.method in SAFE_METHODS:
            return True

        if obj.owner != request.user:
            raise PermissionDenied('Only the owner can modify this resource')

        return True

# In view
@api_view(['DELETE'])
def delete_user(request, user_id):
    user = get_object_or_404(User, id=user_id)

    if not request.user.is_staff and user != request.user:
        raise PermissionDenied({
            'detail': 'You can only delete your own account',
            'contact': 'admin@example.com'
        })

    user.delete()
    return Response(status=204)
```

### Response Format

```json
{
  "detail": "You do not have permission to perform this action."
}
```

## NotFound (404 Not Found)

Raised when a resource does not exist.

### Properties

```python
status_code = 404
default_detail = 'Not found.'
default_code = 'not_found'
```

### Usage

```python
from rest_framework.exceptions import NotFound

# In view
@api_view(['GET'])
def get_article(request, article_id):
    try:
        article = Article.objects.get(id=article_id)
    except Article.DoesNotExist:
        raise NotFound(f'Article {article_id} not found')

    # Also handles Django's Http404
    article = get_object_or_404(Article, id=article_id)  # Works seamlessly

    serializer = ArticleSerializer(article)
    return Response(serializer.data)

# With suggestions
@api_view(['GET'])
def get_product(request, slug):
    try:
        product = Product.objects.get(slug=slug)
    except Product.DoesNotExist:
        similar = Product.objects.filter(slug__icontains=slug)[:3]
        raise NotFound({
            'detail': 'Product not found',
            'suggestions': [p.slug for p in similar]
        })

    return Response(ProductSerializer(product).data)
```

### Response Format

```json
{
  "detail": "Not found."
}
```

## MethodNotAllowed (405 Method Not Allowed)

Raised when an HTTP method is not allowed for an endpoint.

### Properties

```python
status_code = 405
default_detail = 'Method "{method}" not allowed.'
default_code = 'method_not_allowed'
```

### Constructor

```python
MethodNotAllowed(method, detail=None, code=None)
```

### Usage

```python
from rest_framework.exceptions import MethodNotAllowed

# Usually raised automatically by DRF
# But can be raised manually:

@api_view(['GET', 'POST'])
def article_list(request):
    if request.method == 'POST':
        if not request.user.is_staff:
            raise MethodNotAllowed(
                'POST',
                detail='Only staff can create articles'
            )
        # Create article...

    # List articles...
```

### Response Format

```json
{
  "detail": "Method \"DELETE\" not allowed."
}
```

## NotAcceptable (406 Not Acceptable)

Raised when the server cannot satisfy the Accept header.

### Properties

```python
status_code = 406
default_detail = 'Could not satisfy the request Accept header.'
default_code = 'not_acceptable'
```

### Constructor

```python
NotAcceptable(detail=None, code=None, available_renderers=None)
```

### Usage

```python
from rest_framework.exceptions import NotAcceptable

# Usually handled by DRF's content negotiation
# Raised when Accept header cannot be satisfied

class CustomView(APIView):
    renderer_classes = [JSONRenderer]  # Only JSON

    def get(self, request):
        # If client sends Accept: text/html, DRF raises NotAcceptable
        return Response({'data': 'value'})
```

### Response Format

```json
{
  "detail": "Could not satisfy the request Accept header."
}
```

## UnsupportedMediaType (415 Unsupported Media Type)

Raised when the Content-Type is not supported.

### Properties

```python
status_code = 415
default_detail = 'Unsupported media type "{media_type}" in request.'
default_code = 'unsupported_media_type'
```

### Constructor

```python
UnsupportedMediaType(media_type, detail=None, code=None)
```

### Usage

```python
from rest_framework.exceptions import UnsupportedMediaType

# Usually handled by DRF's parser classes
# Raised when Content-Type is not supported

class CustomView(APIView):
    parser_classes = [JSONParser]  # Only JSON

    def post(self, request):
        # If client sends Content-Type: application/xml, DRF raises this
        return Response(request.data)

# Manual usage
@api_view(['POST'])
def upload_file(request):
    content_type = request.content_type

    if content_type not in ['image/jpeg', 'image/png']:
        raise UnsupportedMediaType(
            content_type,
            detail=f'Only JPEG and PNG images are supported'
        )

    # Process file...
```

### Response Format

```json
{
  "detail": "Unsupported media type \"application/xml\" in request."
}
```

## Throttled (429 Too Many Requests)

Raised when a request is throttled due to rate limiting.

### Properties

```python
status_code = 429
default_detail = 'Request was throttled.'
default_code = 'throttled'
```

### Constructor

```python
Throttled(wait=None, detail=None, code=None)
```

- `wait`: Seconds until the request can be retried

### Usage

```python
from rest_framework.exceptions import Throttled

# Usually raised by throttle classes
# But can be raised manually:

@api_view(['POST'])
def expensive_operation(request):
    # Check custom rate limit
    if not check_custom_rate_limit(request.user):
        raise Throttled(
            wait=3600,  # 1 hour
            detail='Daily limit exceeded. Try again in 1 hour.'
        )

    # Process operation...
```

### Response Format

```json
{
  "detail": "Request was throttled. Expected available in 60 seconds."
}
```

### Headers

Includes `Retry-After` header:

```
Retry-After: 60
```

### Handling in Clients

```python
import time
import requests

try:
    response = requests.post('/api/endpoint/')
    response.raise_for_status()
except requests.HTTPError as e:
    if e.response.status_code == 429:
        retry_after = int(e.response.headers.get('Retry-After', 60))
        print(f"Rate limited. Waiting {retry_after} seconds...")
        time.sleep(retry_after)
        # Retry request
```

## Django Exception Compatibility

DRF's default exception handler automatically converts Django exceptions:

### Http404 → NotFound

```python
from django.http import Http404
from django.shortcuts import get_object_or_404

# These are automatically converted to NotFound (404)
raise Http404("Page not found")

# This also raises Http404, converted to NotFound
user = get_object_or_404(User, id=user_id)
```

### PermissionDenied → PermissionDenied

```python
from django.core.exceptions import PermissionDenied

# Converted to DRF's PermissionDenied (403)
raise PermissionDenied("Access denied")
```

## ErrorDetail Class

All exception details are wrapped in `ErrorDetail` objects that include error codes.

```python
from rest_framework.exceptions import ErrorDetail

# Create error with code
error = ErrorDetail('Invalid value', code='invalid')

# Access properties
str(error)  # 'Invalid value'
error.code  # 'invalid'

# Used in exceptions
raise ValidationError({
    'field': ErrorDetail('Error message', code='custom_code')
})
```

## Summary Table

| Exception | Status | Default Message | Default Code |
|-----------|--------|-----------------|--------------|
| APIException | 500 | A server error occurred. | error |
| ValidationError | 400 | Invalid input. | invalid |
| ParseError | 400 | Malformed request. | parse_error |
| AuthenticationFailed | 401 | Incorrect authentication credentials. | authentication_failed |
| NotAuthenticated | 401 | Authentication credentials were not provided. | not_authenticated |
| PermissionDenied | 403 | You do not have permission to perform this action. | permission_denied |
| NotFound | 404 | Not found. | not_found |
| MethodNotAllowed | 405 | Method "{method}" not allowed. | method_not_allowed |
| NotAcceptable | 406 | Could not satisfy the request Accept header. | not_acceptable |
| UnsupportedMediaType | 415 | Unsupported media type "{media_type}" in request. | unsupported_media_type |
| Throttled | 429 | Request was throttled. | throttled |

## Best Practices

1. **Use specific exceptions** instead of generic APIException
2. **Include error codes** for programmatic handling
3. **Provide helpful messages** that guide users to fix the issue
4. **Use structured details** (dicts/lists) for complex errors
5. **Don't expose sensitive information** in error messages
6. **Log exceptions** with proper context for debugging
7. **Document expected errors** in API documentation
8. **Test error scenarios** in unit and integration tests

## Related Files

- Source: `/home/user/django-rest-framework/rest_framework/exceptions.py`
- Default handler: `/home/user/django-rest-framework/rest_framework/views.py`
