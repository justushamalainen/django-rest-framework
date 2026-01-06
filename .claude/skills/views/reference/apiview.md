# APIView - Base View Class

The foundation of all DRF views. Provides request/response cycle, policy handling, and exception management.

## Overview

**APIView** wraps Django's View class with REST framework enhancements:
- Converts Django HttpRequest to DRF Request (with parsing, auth)
- Enforces authentication, permissions, throttling
- Handles exceptions and converts them to Response objects
- Supports content negotiation (JSON, HTML, XML, etc.)

**Source:** `rest_framework/views.py` (528 lines)

## Basic Structure

```python
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status

class MyView(APIView):
    """
    APIView methods you can override:
    - get(), post(), put(), patch(), delete(), head(), options()
    - get_queryset(), get_object(), get_serializer()
    - check_permissions(), check_object_permissions()
    - initial(), finalize_response(), handle_exception()
    """

    def get(self, request, *args, **kwargs):
        """Handle GET requests"""
        return Response({'message': 'Hello, World!'})

    def post(self, request, *args, **kwargs):
        """Handle POST requests"""
        data = request.data  # Parsed request body
        return Response(data, status=status.HTTP_201_CREATED)
```

## Request/Response Cycle

When a request hits an APIView:

```
1. Django routing → calls MyView.as_view()
   ↓
2. dispatch(request, *args, **kwargs)
   ├─ initialize_request() → Wraps HttpRequest in DRF Request
   ├─ initial()
   │  ├─ perform_content_negotiation()
   │  ├─ determine_version()
   │  ├─ perform_authentication()  # Sets request.user
   │  ├─ check_permissions()        # Raises PermissionDenied if needed
   │  └─ check_throttles()          # Raises Throttled if rate exceeded
   ├─ Call handler method (get/post/put/delete)
   │  └─ Your code executes here
   └─ finalize_response() → Wraps Response with renderer
   ↓
3. Return HTTP response to client
```

## Policy Classes

APIView supports setting policy classes at class or view level:

```python
from rest_framework.views import APIView
from rest_framework.permissions import IsAuthenticated
from rest_framework.authentication import TokenAuthentication
from rest_framework.throttling import UserRateThrottle

class ProtectedView(APIView):
    # Authentication: Who is making the request?
    authentication_classes = [TokenAuthentication]

    # Permissions: Is the user allowed to access this?
    permission_classes = [IsAuthenticated]

    # Throttling: Has the user exceeded their rate limit?
    throttle_classes = [UserRateThrottle]

    # Parsers: How to parse request body?
    # parser_classes = [JSONParser, FormParser]

    # Renderers: How to render response?
    # renderer_classes = [JSONRenderer, BrowsableAPIRenderer]

    def get(self, request):
        # request.user is already authenticated here
        return Response({'user': request.user.username})
```

## Common Overrides

### 1. Custom Permissions Check

```python
class OwnerOnlyView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, pk):
        obj = get_object_or_404(Article, pk=pk)

        # Custom object-level permission check
        if obj.author != request.user:
            self.permission_denied(
                request,
                message="You don't own this article."
            )

        serializer = ArticleSerializer(obj)
        return Response(serializer.data)
```

### 2. Custom Exception Handling

```python
class CustomView(APIView):
    def handle_exception(self, exc):
        """Called when any exception is raised during dispatch"""
        if isinstance(exc, MyCustomException):
            return Response(
                {'error': 'Custom error occurred'},
                status=status.HTTP_400_BAD_REQUEST
            )
        # Fall back to default handling
        return super().handle_exception(exc)
```

### 3. Custom Initial Processing

```python
class LoggingView(APIView):
    def initial(self, request, *args, **kwargs):
        """Called before the handler method"""
        super().initial(request, *args, **kwargs)

        # Custom logic after auth/permissions
        logger.info(f"User {request.user} accessed {request.path}")
```

### 4. Custom Response Finalization

```python
class HeaderView(APIView):
    def finalize_response(self, request, response, *args, **kwargs):
        """Called after handler, before returning response"""
        response = super().finalize_response(request, response, *args, **kwargs)

        # Add custom headers
        response['X-Custom-Header'] = 'My Value'
        return response
```

## Available Attributes

```python
class MyView(APIView):
    # Policy classes (can also be set in settings.py)
    renderer_classes = [...]           # Response renderers
    parser_classes = [...]             # Request parsers
    authentication_classes = [...]    # Authentication methods
    throttle_classes = [...]          # Rate limiting
    permission_classes = [...]        # Access control
    content_negotiation_class = ...   # Content negotiation
    metadata_class = ...              # OPTIONS response metadata
    versioning_class = ...            # API versioning

    # Schema generation
    schema = DefaultSchema()           # Auto-generate OpenAPI schema
```

## Request Object

The DRF Request wraps Django's HttpRequest:

```python
def get(self, request):
    # DRF additions:
    request.data              # Parsed request body (any content type)
    request.query_params      # Same as request.GET (better name)
    request.user              # Set by authentication
    request.auth              # Auth token/session
    request.accepted_renderer # Selected renderer
    request.accepted_media_type

    # Django attributes still available:
    request.method            # 'GET', 'POST', etc.
    request.GET               # Query parameters
    request.POST              # Form data
    request.FILES             # Uploaded files
    request.META              # HTTP headers
```

## Response Object

Always return a Response (not Django HttpResponse):

```python
from rest_framework.response import Response
from rest_framework import status

def post(self, request):
    # Simple response
    return Response({'key': 'value'})

    # With status code
    return Response({'created': True}, status=status.HTTP_201_CREATED)

    # With headers
    return Response(
        {'key': 'value'},
        status=200,
        headers={'X-Custom': 'Header'}
    )

    # Error response
    return Response(
        {'error': 'Invalid data'},
        status=status.HTTP_400_BAD_REQUEST
    )
```

## HTTP Method Handlers

APIView dispatches to these methods based on request.method:

```python
class CRUDView(APIView):
    def get(self, request, *args, **kwargs):
        """Retrieve resource(s)"""
        pass

    def post(self, request, *args, **kwargs):
        """Create resource"""
        pass

    def put(self, request, *args, **kwargs):
        """Update resource (full replacement)"""
        pass

    def patch(self, request, *args, **kwargs):
        """Update resource (partial)"""
        pass

    def delete(self, request, *args, **kwargs):
        """Delete resource"""
        pass

    def head(self, request, *args, **kwargs):
        """Like GET but no response body"""
        pass

    def options(self, request, *args, **kwargs):
        """Metadata about resource (auto-implemented)"""
        pass
```

## Status Codes

Use REST framework's status constants:

```python
from rest_framework import status

# Success
status.HTTP_200_OK
status.HTTP_201_CREATED
status.HTTP_202_ACCEPTED
status.HTTP_204_NO_CONTENT

# Client errors
status.HTTP_400_BAD_REQUEST
status.HTTP_401_UNAUTHORIZED
status.HTTP_403_FORBIDDEN
status.HTTP_404_NOT_FOUND
status.HTTP_405_METHOD_NOT_ALLOWED
status.HTTP_409_CONFLICT

# Server errors
status.HTTP_500_INTERNAL_SERVER_ERROR
status.HTTP_503_SERVICE_UNAVAILABLE
```

## Exceptions

Raise DRF exceptions for proper error handling:

```python
from rest_framework.exceptions import (
    APIException,
    NotFound,
    PermissionDenied,
    ValidationError,
    NotAuthenticated,
    AuthenticationFailed,
    MethodNotAllowed,
    Throttled
)

def get(self, request, pk):
    try:
        obj = MyModel.objects.get(pk=pk)
    except MyModel.DoesNotExist:
        raise NotFound(detail="Object not found")

    if not obj.is_public:
        raise PermissionDenied(detail="This resource is private")

    return Response({'data': 'value'})
```

## Complete Example

```python
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticatedOrReadOnly
from rest_framework import status
from django.shortcuts import get_object_or_404
from .models import Article
from .serializers import ArticleSerializer

class ArticleDetailView(APIView):
    """
    Retrieve, update or delete an article instance.

    Authentication:
        - Read: Anyone
        - Write: Authenticated users only

    Permissions:
        - Update/Delete: Article owner only
    """
    permission_classes = [IsAuthenticatedOrReadOnly]

    def get_object(self, pk):
        """Helper to get object and check permissions"""
        obj = get_object_or_404(Article, pk=pk)
        self.check_object_permissions(self.request, obj)
        return obj

    def get(self, request, pk):
        """GET /api/articles/{pk}/"""
        article = self.get_object(pk)
        serializer = ArticleSerializer(article)
        return Response(serializer.data)

    def put(self, request, pk):
        """PUT /api/articles/{pk}/ - Full update"""
        article = self.get_object(pk)

        # Only owner can update
        if article.author != request.user:
            return Response(
                {'error': 'You can only edit your own articles'},
                status=status.HTTP_403_FORBIDDEN
            )

        serializer = ArticleSerializer(article, data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    def patch(self, request, pk):
        """PATCH /api/articles/{pk}/ - Partial update"""
        article = self.get_object(pk)

        if article.author != request.user:
            return Response(
                {'error': 'You can only edit your own articles'},
                status=status.HTTP_403_FORBIDDEN
            )

        serializer = ArticleSerializer(
            article,
            data=request.data,
            partial=True  # Allow partial updates
        )
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    def delete(self, request, pk):
        """DELETE /api/articles/{pk}/"""
        article = self.get_object(pk)

        if article.author != request.user:
            return Response(
                {'error': 'You can only delete your own articles'},
                status=status.HTTP_403_FORBIDDEN
            )

        article.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)
```

## When to Use APIView

Use APIView when you need:

1. **Full control** over the request/response cycle
2. **Multiple models** in a single endpoint
3. **Custom business logic** that doesn't fit CRUD patterns
4. **Non-standard HTTP behavior** (special headers, status codes)
5. **Complex permission logic** that varies by method

Use Generic Views or ViewSets for standard CRUD operations (simpler code).

## See Also

- **[generic-views.md](generic-views.md)** - Higher-level views for CRUD operations
- **[mixins.md](mixins.md)** - Composable behavior for views
- **[viewsets.md](viewsets.md)** - ViewSets for automatic routing
